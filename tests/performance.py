"""Performance test — latency, TTFT, and throughput metrics."""

from typing import Optional

from config import settings
from models.scanner import ModelInfo
from tests.base import BaseTester, TestResult
from utils.api_client import NIMClient
from utils.metrics import TimingMetrics


class PerformanceTester(BaseTester):
    """Measure TTFT (time-to-first-token), total latency, and tokens/sec.

    Uses streaming to get precise timing for both metrics.
    """

    def __init__(self, client: Optional[NIMClient] = None) -> None:
        super().__init__(client)
        self._metrics: dict[str, TimingMetrics] = {}

    def name(self) -> str:
        return "performance"

    def description(self) -> str:
        return (
            "Measure TTFT (time-to-first-token), total response latency, "
            "and token throughput via streaming"
        )

    def skip_reason(self, model: ModelInfo) -> Optional[str]:
        if not model.is_chat_model:
            return "Non-chat model — skipping performance test"
        return None

    def test_model(self, model: ModelInfo) -> TestResult:
        timing = TimingMetrics()
        errors: list[str] = []

        for i in range(settings.TEST_REPEAT):
            try:
                result = self.client.timed_chat(
                    model=model.id,
                    messages=[
                        {
                            "role": "user",
                            "content": (
                                "Write a short paragraph (3-4 sentences) about "
                                "the benefits of parallel computing."
                            ),
                        }
                    ],
                    max_tokens=settings.MAX_TOKENS_GENERATE,
                    temperature=0.7,
                )
                content = result.get("content", "")
                usage = result.get("usage", {})
                timing_info = result.get("timing_ms", {})

                output_tokens = usage.get("completion_tokens", 0)
                if not output_tokens and content:
                    # Approximate if usage not returned
                    output_tokens = max(1, len(content) // 4)

                timing.add_run(
                    ttft=timing_info.get("ttft", 0),
                    total=timing_info.get("total", 0),
                    output_tokens=output_tokens,
                )
            except Exception as e:
                errors.append(f"Run {i + 1}: {e}")

        # Composite score: weight TTFT (40%), total latency (30%), throughput (30%)
        score = 0.0
        weight_total = 0

        if timing.avg_ttft_ms is not None:
            # TTFT score: lower is better. <500ms = 1.0, >10s = 0.0
            ttft_score = max(0.0, 1.0 - timing.avg_ttft_ms / 10000)
            score += ttft_score * 0.4
            weight_total += 0.4

        if timing.avg_total_ms is not None:
            # Total latency score: <5s = 1.0, >30s = 0.0
            lat_score = max(0.0, 1.0 - timing.avg_total_ms / 30000)
            score += lat_score * 0.3
            weight_total += 0.3

        if timing.avg_tokens_per_second is not None:
            # Throughput score: >100 tok/s = 1.0, <5 tok/s = 0.0
            tp_score = min(1.0, timing.avg_tokens_per_second / 100)
            score += tp_score * 0.3
            weight_total += 0.3

        final_score = score / weight_total if weight_total > 0 else 0.0

        self._metrics[model.id] = timing

        return TestResult(
            model_id=model.id,
            test_name=self.name(),
            passed=final_score >= 0.3,
            score=round(final_score, 4),
            details={
                "avg_ttft_ms": timing.avg_ttft_ms,
                "min_ttft_ms": timing.min_ttft_ms,
                "p95_ttft_ms": timing.p95_ttft_ms,
                "avg_total_ms": timing.avg_total_ms,
                "avg_tokens_per_second": timing.avg_tokens_per_second,
                "runs": len(timing.total_ms),
                "score_components": {
                    "ttft": timing.avg_ttft_ms,
                    "total_latency": timing.avg_total_ms,
                    "throughput": timing.avg_tokens_per_second,
                },
            },
            errors=errors,
        )

    @property
    def all_metrics(self) -> dict[str, TimingMetrics]:
        return self._metrics
