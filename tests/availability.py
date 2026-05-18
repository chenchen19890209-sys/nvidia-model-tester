"""Availability test — checks if the model endpoint is reachable."""

from typing import Optional

from models.scanner import ModelInfo
from tests.base import BaseTester, TestResult
from utils.api_client import NIMClient
from utils.metrics import AvailabilityMetrics


class AvailabilityTester(BaseTester):
    """Test whether a model's API endpoint is accessible and responsive.

    Sends a minimal chat completion to confirm the model is ready.
    """

    def __init__(self, client: Optional[NIMClient] = None) -> None:
        super().__init__(client)
        self._metrics: dict[str, AvailabilityMetrics] = {}

    def name(self) -> str:
        return "availability"

    def description(self) -> str:
        return "Check API reachability, authentication, and basic responsiveness"

    def skip_reason(self, model: ModelInfo) -> Optional[str]:
        if not model.is_chat_model:
            return "Non-chat model — skipping chat-based availability check"
        return None

    def test_model(self, model: ModelInfo) -> TestResult:
        metrics = AvailabilityMetrics()
        errors: list[str] = []

        # 1. API health check
        try:
            ok, elapsed = self.client.health_check()
            if ok:
                metrics.record_success()
            else:
                metrics.record_failure(f"Health check failed ({elapsed:.0f}ms)")
                errors.append(f"API health check returned non-OK status")
        except Exception as e:
            metrics.record_failure(str(e))
            errors.append(f"Health check exception: {e}")

        # 2. Minimal chat completion
        try:
            resp = self.client.chat_completion(
                model=model.id,
                messages=[{"role": "user", "content": "Respond with exactly 'OK'"}],
                max_tokens=10,
                temperature=0.0,
            )
            content = (
                resp.get("choices", [{}])[0]
                .get("message", {})
                .get("content", "")
            )
            if content.strip():
                metrics.record_success()
            else:
                metrics.record_failure("Empty response content")
                errors.append("Model returned empty content")
        except Exception as e:
            metrics.record_failure(str(e))
            errors.append(f"Chat completion error: {e}")

        # 3. Second run to confirm consistency
        try:
            resp2 = self.client.chat_completion(
                model=model.id,
                messages=[{"role": "user", "content": "Say 'hello'"}],
                max_tokens=10,
                temperature=0.0,
            )
            content2 = (
                resp2.get("choices", [{}])[0]
                .get("message", {})
                .get("content", "")
            )
            if content2.strip():
                metrics.record_success()
            else:
                metrics.record_failure("Second attempt empty")
        except Exception as e:
            metrics.record_failure(str(e))
            errors.append(f"Second attempt error: {e}")

        self._metrics[model.id] = metrics

        return TestResult(
            model_id=model.id,
            test_name=self.name(),
            passed=metrics.success_rate >= 0.5,
            score=metrics.success_rate,
            details={
                "success_count": metrics.success_count,
                "failure_count": metrics.failure_count,
                "total_attempts": metrics.total_attempts,
                "success_rate": metrics.success_rate,
                "summary": metrics.summary,
            },
            errors=errors,
        )

    @property
    def all_metrics(self) -> dict[str, AvailabilityMetrics]:
        return self._metrics
