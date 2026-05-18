#!/usr/bin/env python3
"""NVIDIA Model Tester — Comprehensive evaluation framework for NVIDIA NIM models.

Usage:
    # Set your API key first (or use .env):
    set NVIDIA_API_KEY="nvapi-..."

    # Run full test on all models:
    python main.py

    # Test only LLM models:
    python main.py --scope llm

    # Test a sample (3 per category) with high concurrency:
    python main.py --scope sample --concurrency 10

    # Run with a specific output directory:
    python main.py --output ./my_reports
"""

from __future__ import annotations

import argparse
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Optional

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import ReportFormat, TestScope, settings
from models.scanner import (
    ModelInfo,
    discover_models,
    group_by_category,
    sample_models,
)
from reporters.html_reporter import HTMLReporter, ModelReportData
from tests.availability import AvailabilityTester
from tests.capability import CapabilityTester
from tests.performance import PerformanceTester
from tests.quality import QualityTester
from utils.api_client import NIMClient


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="NVIDIA Model Tester — Comprehensive evaluation framework",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--scope",
        choices=[s.value for s in TestScope],
        default=settings.TEST_SCOPE.value,
        help="Which models to include (default: %(default)s)",
    )
    parser.add_argument(
        "--max-models",
        type=int,
        default=settings.MAX_MODELS,
        help="Cap number of models tested (default: no cap)",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=settings.CONCURRENCY,
        help="Max concurrent API requests (default: %(default)s)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=settings.OUTPUT_DIR,
        help="Output directory for reports (default: %(default)s)",
    )
    parser.add_argument(
        "--no-quality",
        action="store_true",
        help="Skip LLM-as-judge quality evaluation",
    )
    parser.add_argument(
        "--api-key",
        type=str,
        default="",
        help="NVIDIA API key (or set NVIDIA_API_KEY env var)",
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    # ── Config ─────────────────────────────────────────────────
    if args.api_key:
        os.environ["NVIDIA_API_KEY"] = args.api_key
    if args.no_quality:
        settings.ENABLE_QUALITY_EVAL = False
    settings.CONCURRENCY = args.concurrency
    settings.OUTPUT_DIR = args.output

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"{'='*60}")
    print(f"  NVIDIA Model Tester")
    print(f"  Started: {timestamp}")
    print(f"{'='*60}")

    # ── Phase 1: Discover models ───────────────────────────────
    print("\n🔍 Phase 1: Discovering models from NVIDIA API...")
    client = NIMClient()

    try:
        all_models = discover_models(client)
    except Exception as e:
        print(f"  ❌ Failed to discover models: {e}")
        print("  Make sure your NVIDIA_API_KEY is set correctly.")
        sys.exit(1)

    print(f"  Found {len(all_models)} models")

    # Apply scope filter
    models = _filter_models(all_models, TestScope(args.scope), args.max_models)
    print(f"  After filter ({args.scope}): {len(models)} models")

    # Show category breakdown
    groups = group_by_category(models)
    for cat, items in sorted(groups.items()):
        print(f"    {cat}: {len(items)}")

    if not models:
        print("  No models to test. Try a broader scope.")
        sys.exit(0)

    # ── Phase 2: Run tests ─────────────────────────────────────
    print(f"\n🧪 Phase 2: Running tests (concurrency={args.concurrency})...")

    # Map from model_id → ModelReportData for incremental collection
    result_map: dict[str, ModelReportData] = {
        m.id: ModelReportData(model=m) for m in models
    }

    # Step 1: Quick connectivity check (availability test)
    print("\n  🔍 Step 1: Quick connectivity screening...")
    availability_tester = AvailabilityTester(client)
    suite_name = availability_tester.name()
    suite_desc = availability_tester.description()
    print(f"  📌 Test suite: {suite_name} ({suite_desc})")

    eligible_for_availability = [m for m in models if not availability_tester.skip_reason(m)]
    available_models = []  # Models that pass availability test

    with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
        future_to_model = {
            pool.submit(availability_tester.test_model, model): model
            for model in eligible_for_availability
        }

        for future in as_completed(future_to_model):
            model = future_to_model[future]
            try:
                result = future.result()
                status = "✅" if result.passed else "❌"
                print(
                    f"    {status} {model.id:<50} "
                    f"score={result.score:.3f}",
                )
                result_map[model.id].results[suite_name] = result
                
                # Track available models for further testing
                if result.passed:
                    available_models.append(model)
            except Exception as e:
                print(f"    💥 {model.id:<50} error={e}")

    print(f"\n  📊 Connectivity check complete: {len(available_models)}/{len(eligible_for_availability)} models available")
    
    if not available_models:
        print("  ⚠️  No models passed connectivity check. Skipping further tests.")
        all_results = list(result_map.values())
    else:
        # Step 2: Run remaining tests only on available models
        print(f"\n  🚀 Step 2: Running deep tests on {len(available_models)} available models...")
        
        remaining_testers = [
            PerformanceTester(client),
            CapabilityTester(client),
        ]
        if settings.ENABLE_QUALITY_EVAL:
            remaining_testers.append(QualityTester(client))

        for tester in remaining_testers:
            suite_name = tester.name()
            suite_desc = tester.description()
            print(f"\n  📌 Test suite: {suite_name} ({suite_desc})")

            # Only test models that passed availability check
            eligible = [m for m in available_models if not tester.skip_reason(m)]
            if not eligible:
                print("    (no eligible models)")
                continue

            with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
                future_to_model = {
                    pool.submit(tester.test_model, model): model
                    for model in eligible
                }

                for future in as_completed(future_to_model):
                    model = future_to_model[future]
                    try:
                        result = future.result()
                        status = "✅" if result.passed else "❌"
                        print(
                            f"    {status} {model.id:<50} "
                            f"score={result.score:.3f}",
                        )
                        result_map[model.id].results[suite_name] = result
                    except Exception as e:
                        print(f"    💥 {model.id:<50} error={e}")

        all_results = list(result_map.values())

    # ── Phase 3: Generate report ───────────────────────────────
    print(f"\n📝 Phase 3: Generating report...")

    reporter = HTMLReporter()
    report_path = reporter.generate(all_results)

    # Also generate JSON if requested
    if settings.REPORT_FORMAT in (ReportFormat.JSON, ReportFormat.BOTH):
        json_path = _generate_json(all_results, settings.OUTPUT_DIR)
        print(f"  📄 JSON report: {json_path}")

    # ── Summary ─────────────────────────────────────────────────
    _print_summary(all_results)

    print(f"\n✅ Done. Report: {report_path}")


# ── Helpers ────────────────────────────────────────────────────


def _filter_models(
    models: list[ModelInfo],
    scope: TestScope,
    max_models: Optional[int],
) -> list[ModelInfo]:
    if scope == TestScope.LLM:
        models = [m for m in models if m.category == "llm"]
    elif scope == TestScope.MULTIMODAL:
        models = [m for m in models if m.category == "multimodal"]
    elif scope == TestScope.IMAGE:
        models = [m for m in models if m.category == "image"]
    elif scope == TestScope.AUDIO:
        models = [m for m in models if m.category == "audio"]
    elif scope == TestScope.SPECIALIZED:
        models = [m for m in models if m.category == "specialized"]
    elif scope == TestScope.SAMPLE:
        models = sample_models(models, per_category=3)

    if max_models and len(models) > max_models:
        models = models[:max_models]

    # Sort by category for consistent ordering
    models.sort(key=lambda m: (m.category, m.id))
    return models


def _generate_json(data: list[ModelReportData], output_dir: str) -> str:
    import json

    os.makedirs(output_dir, exist_ok=True)
    path = os.path.join(
        output_dir,
        f"nvidia_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
    )

    serialisable = []
    for m in data:
        results = {}
        for name, r in m.results.items():
            results[name] = {
                "passed": r.passed,
                "score": r.score,
                "details": r.details,
                "errors": r.errors,
            }

        serialisable.append({
            "model_id": m.model.id,
            "category": m.model.category,
            "name": m.model.name,
            "overall_score": m.overall_score,
            "results": results,
        })

    with open(path, "w", encoding="utf-8") as f:
        json.dump(serialisable, f, ensure_ascii=False, indent=2)
    return path


def _print_summary(data: list[ModelReportData]) -> None:
    """Print a console summary table."""
    print(f"\n{'='*60}")
    print("  SUMMARY")
    print(f"{'='*60}")

    ranked = sorted(data, key=lambda m: m.overall_score, reverse=True)

    print(f"  {'Rank':<5} {'Model':<50} {'Score':<8}")
    print(f"  {'-'*63}")
    for i, m in enumerate(ranked[:10]):
        print(f"  {i + 1:<5} {m.model.id:<50} {m.overall_score:.3f}")

    print(f"\n  Test execution complete.")


if __name__ == "__main__":
    main()
