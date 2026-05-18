#!/usr/bin/env python3
"""NVIDIA 模型测试器 — NVIDIA NIM 模型的综合评估框架。

该工具用于全面测试和评估 NVIDIA NIM API 上可用的各种 AI 模型，包括：
- 语言模型（LLM）
- 多模态模型（视觉 + 语言）
- 图像生成/编辑模型
- 音频模型（语音识别 / TTS）
- 专用模型（安全、重排序、OCR等）

使用方法:
    # 首先设置 API 密钥（或使用 .env 文件）:
    set NVIDIA_API_KEY="nvapi-..."

    # 运行所有模型的完整测试:
    python main.py

    # 仅测试 LLM 模型:
    python main.py --scope llm

    # 测试样本（每个类别 3 个）并使用高并发:
    python main.py --scope sample --concurrency 10

    # 使用特定的输出目录:
    python main.py --output ./my_reports
"""

from __future__ import annotations

import argparse
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Optional

# 确保项目根目录在路径中
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
    """解析命令行参数。
    
    Returns:
        包含所有解析后的命令行参数的命名空间对象
    """
    parser = argparse.ArgumentParser(
        description="NVIDIA 模型测试器 — 综合评估框架",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--scope",
        choices=[s.value for s in TestScope],
        default=settings.TEST_SCOPE.value,
        help="要包含的模型范围（默认: %(default)s）",
    )
    parser.add_argument(
        "--max-models",
        type=int,
        default=settings.MAX_MODELS,
        help="限制测试的模型数量（默认: 无限制）",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=settings.CONCURRENCY,
        help="最大并发 API 请求数（默认: %(default)s）",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=settings.OUTPUT_DIR,
        help="报告的输出目录（默认: %(default)s）",
    )
    parser.add_argument(
        "--no-quality",
        action="store_true",
        help="跳过 LLM-as-judge 质量评估",
    )
    parser.add_argument(
        "--api-key",
        type=str,
        default="",
        help="NVIDIA API 密钥（或设置 NVIDIA_API_KEY 环境变量）",
    )

    return parser.parse_args()


def main() -> None:
    """主函数，执行完整的测试流程。
    
    测试流程分为三个阶段：
    1. 从 NVIDIA API 发现模型
    2. 运行各种测试（连通性、性能、能力、质量）
    3. 生成报告
    """
    args = parse_args()

    # ── 配置初始化 ────────────────────────────────────────────────
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

    # ── 阶段 1: 发现模型 ───────────────────────────────────────
    print("\n🔍 阶段 1: 从 NVIDIA API 发现模型...")
    client = NIMClient()

    try:
        all_models = discover_models(client)
    except Exception as e:
        print(f"  ❌ 模型发现失败: {e}")
        print("  请确保您的 NVIDIA_API_KEY 设置正确。")
        sys.exit(1)

    print(f"  找到 {len(all_models)} 个模型")

    # 应用范围过滤器
    models = _filter_models(all_models, TestScope(args.scope), args.max_models)
    print(f"  过滤后 ({args.scope}): {len(models)} 个模型")

    # 显示类别分解
    groups = group_by_category(models)
    for cat, items in sorted(groups.items()):
        print(f"    {cat}: {len(items)}")

    if not models:
        print("  没有要测试的模型。请尝试更广泛的范围。")
        sys.exit(0)

    # ── 阶段 2: 运行测试 ────────────────────────────────────────
    print(f"\n🧪 阶段 2: 运行测试 (并发数={args.concurrency})...")

    # 建立 model_id → ModelReportData 的映射，用于增量收集结果
    result_map: dict[str, ModelReportData] = {
        m.id: ModelReportData(model=m) for m in models
    }

    # 步骤 1: 快速连通性检查（可用性测试）
    print("\n  🔍 步骤 1: 快速连通性筛查...")
    availability_tester = AvailabilityTester(client)
    suite_name = availability_tester.name()
    suite_desc = availability_tester.description()
    print(f"  📌 测试套件: {suite_name} ({suite_desc})")

    eligible_for_availability = [m for m in models if not availability_tester.skip_reason(m)]
    available_models = []  # 通过可用性测试的模型

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
                
                # 跟踪通过测试的模型以进行进一步测试
                if result.passed:
                    available_models.append(model)
            except Exception as e:
                print(f"    💥 {model.id:<50} error={e}")

    print(f"\n  📊 连通性检查完成: {len(available_models)}/{len(eligible_for_availability)} 个模型可用")
    
    if not available_models:
        print("  ⚠️  没有模型通过连通性检查。跳过后续测试。")
        all_results = list(result_map.values())
    else:
        # 步骤 2: 仅对可用的模型运行剩余测试
        print(f"\n  🚀 步骤 2: 对 {len(available_models)} 个可用模型运行深度测试...")
        
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

            # 仅测试通过可用性检查的模型
            eligible = [m for m in available_models if not tester.skip_reason(m)]
            if not eligible:
                print("    （没有符合条件的模型）")
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

    # ── 阶段 3: 生成报告 ───────────────────────────────────────
    print(f"\n📝 阶段 3: 生成报告...")

    reporter = HTMLReporter()
    report_path = reporter.generate(all_results)

    # 如果请求，也生成 JSON 格式
    if settings.REPORT_FORMAT in (ReportFormat.JSON, ReportFormat.BOTH):
        json_path = _generate_json(all_results, settings.OUTPUT_DIR)
        print(f"  📄 JSON 报告: {json_path}")

    # ── 摘要 ────────────────────────────────────────────────────
    _print_summary(all_results)

    print(f"\n✅ 完成。报告: {report_path}")


# ── 辅助函数 ───────────────────────────────────────────────────


def _filter_models(
    models: list[ModelInfo],
    scope: TestScope,
    max_models: Optional[int],
) -> list[ModelInfo]:
    """根据测试范围过滤模型。
    
    Args:
        models: 所有模型的列表
        scope: 测试范围枚举值
        max_models: 最大模型数量限制
        
    Returns:
        过滤后的模型列表
    """
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

    # 按类别排序以保持一致的顺序
    models.sort(key=lambda m: (m.category, m.id))
    return models


def _generate_json(data: list[ModelReportData], output_dir: str) -> str:
    """生成 JSON 格式的报告文件。
    
    Args:
        data: 模型报告数据列表
        output_dir: 输出目录路径
        
    Returns:
        生成的 JSON 文件路径
    """
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
    """在控制台打印摘要表格。
    
    Args:
        data: 模型报告数据列表
    """
    print(f"\n{'='*60}")
    print("  摘要")
    print(f"{'='*60}")

    ranked = sorted(data, key=lambda m: m.overall_score, reverse=True)

    print(f"  {'排名':<5} {'模型':<50} {'分数':<8}")
    print(f"  {'-'*63}")
    for i, m in enumerate(ranked[:10]):
        print(f"  {i + 1:<5} {m.model.id:<50} {m.overall_score:.3f}")

    print(f"\n  测试执行完成。")


if __name__ == "__main__":
    main()
