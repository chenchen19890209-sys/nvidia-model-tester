# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

NVIDIA Model Tester is an automated evaluation framework for NVIDIA NIM API models. It discovers models via the API, classifies them into 5 categories (llm, multimodal, image, audio, specialized), runs 4 test dimensions, and generates a self-contained HTML report with rankings, charts, and per-model detail cards.

## Commands

```bash
# Quick sample test (3 models per category)
python main.py --scope sample

# Full test on all models
python main.py

# Test specific category with high concurrency, skipping quality eval
python main.py --scope llm --concurrency 10 --no-quality

# Limit number of models, custom output directory
python main.py --max-models 20 --output ./my_reports
```

No test suite (`pytest`, etc.) exists for this project.

## Architecture

### Execution flow (main.py)

Three phases orchestrated in `main()`:
1. **Discover** — calls `discover_models()` from `models/scanner.py`, then filters by scope
2. **Test** — runs `AvailabilityTester` first; only models that pass proceed to `PerformanceTester`, `CapabilityTester`, and optionally `QualityTester`. Each tester runs via `ThreadPoolExecutor` with configurable concurrency.
3. **Report** — `HTMLReporter.generate()` writes a self-contained HTML file to `./output/`

Results accumulate in a `dict[str, ModelReportData]` keyed by model ID. `ModelReportData.overall_score` is the mean of all test dimension scores.

### Key modules

- **`config.py`** — Singleton `Settings` (Pydantic BaseSettings). Reads from `.env` directly (no prefix — `NV_TEST_` prefix is commented out). Field names are case-sensitive. Config values are mutable at runtime (e.g., `settings.CONCURRENCY = args.concurrency`).
- **`utils/api_client.py`** — `NIMClient` wraps the OpenAI-compatible NVIDIA NIM API. Key methods: `list_models()`, `chat_completion()`, `timed_chat()` (streaming with TTFT/total latency measurement). All methods create a new `httpx.Client` per call.
- **`models/scanner.py`** — `discover_models()` fetches from API and classifies using `_classify()` which does keyword matching against `_CATEGORY_RULES`. The first matching rule wins; unknown models default to `"llm"`.
- **`models/registry.py`** — Static `_MODEL_REGISTRY` dict with known model capabilities (max tokens, tool support, recommended temperature). `get_capabilities()` returns defaults for unknown models.
- **`tests/base.py`** — `BaseTester(ABC)` with abstract `name()`, `description()`, `test_model()`, and optional `skip_reason()`. `TestResult` is a dataclass with `passed`, `score` (0-1), `details`, `errors`, `warnings`.
- **`tests/availability.py`** — 3 checks: health endpoint, minimal chat completion, second consistency call. Passes if `success_rate >= 0.5`.
- **`tests/performance.py`** — Runs `timed_chat()` repeatedly (`TEST_REPEAT` times). Composite score: TTFT 40% + latency 30% + throughput 30%.
- **`tests/capability.py`** — Runs scenario prompts from `scenarios/prompts.py`. Scoring is heuristic (length, structure markers, expected traits) — not LLM-based. Also tracks token usage via `CostMetrics`.
- **`tests/quality.py`** — LLM-as-judge: sends model responses to `QUALITY_REFERENCE_MODEL` for 1-10 scoring. Only evaluates first 6 prompts. Skips self-evaluation if model is the reference model.
- **`scenarios/prompts.py`** — 12 `TestPrompt` dataclass instances in `ALL_PROMPTS`. `prompts_for_category()` filters by tags. Prompts include general_chat, code_generation, math_reasoning, logical_reasoning (Einstein riddle), etc.
- **`reporters/html_reporter.py`** — `HTMLReporter.generate()` builds a single HTML file with embedded CSS, JS, and Canvas-based bar chart. Zero external dependencies. Supports dark theme, responsive design, collapsible model cards, scenario suitability matrix.
- **`utils/metrics.py`** — Dataclasses: `TimingMetrics` (ttft/total/tps lists with avg/min/p95), `AvailabilityMetrics`, `QualityMetrics`, `CostMetrics`.

### Classification rules

Category assignment in `_CATEGORY_RULES` is order-dependent and keyword-based on `"{model_id} {name}".lower()`. Add new rules carefully — earlier rules take precedence. Categories: `image`, `audio`, `multimodal`, `specialized`, `llm` (default fallback).

### Test skip logic

Each tester's `skip_reason()` gates which models run:
- `AvailabilityTester`, `PerformanceTester`, `CapabilityTester`, `QualityTester` all skip non-chat models (`model.is_chat_model` checks for `llm` or `multimodal` category).
- `QualityTester` additionally skips when `ENABLE_QUALITY_EVAL` is `False` or when the model is the reference judge.

### Concurrency model

`main.py` uses `concurrent.futures.ThreadPoolExecutor` with `as_completed()` for both availability screening (Phase 2 Step 1) and deep tests (Phase 2 Step 2). Each tester is instantiated once and shared across threads — `NIMClient` is stateless, but tester metric dicts (`self._metrics`, `self._costs`, etc.) are mutated from multiple threads via `test_model()` called in thread pool. This works because each model ID is a distinct dict key.

### Configuration priority

Command-line args > runtime mutation of `settings` fields > `.env` file > `Field(default=...)`. The `.env` file uses raw field names like `NVIDIA_API_KEY=...` (no `NV_TEST_` prefix).
