"""Metrics calculation helpers."""

from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class TimingMetrics:
    """Per-model timing measurements aggregated across runs."""

    ttft_ms: list[float] = field(default_factory=list)
    total_ms: list[float] = field(default_factory=list)
    tokens_per_second: list[float] = field(default_factory=list)

    def add_run(self, ttft: float, total: float, output_tokens: int) -> None:
        self.ttft_ms.append(ttft)
        self.total_ms.append(total)
        decode_ms = total - ttft
        if decode_ms > 0 and output_tokens > 0:
            self.tokens_per_second.append(output_tokens / (decode_ms / 1000))

    @property
    def avg_ttft_ms(self) -> Optional[float]:
        return _safe_mean(self.ttft_ms)

    @property
    def min_ttft_ms(self) -> Optional[float]:
        return _safe_min(self.ttft_ms)

    @property
    def p95_ttft_ms(self) -> Optional[float]:
        return _safe_percentile(self.ttft_ms, 95)

    @property
    def avg_total_ms(self) -> Optional[float]:
        return _safe_mean(self.total_ms)

    @property
    def avg_tokens_per_second(self) -> Optional[float]:
        return _safe_mean(self.tokens_per_second)

    @property
    def total_output_tokens(self) -> int:
        return len(self.total_ms)  # approx based on run count


@dataclass
class AvailabilityMetrics:
    """API availability and error metrics."""

    success_count: int = 0
    failure_count: int = 0
    total_attempts: int = 0
    errors: list[str] = field(default_factory=list)

    @property
    def success_rate(self) -> float:
        if self.total_attempts == 0:
            return 0.0
        return self.success_count / self.total_attempts

    def record_success(self) -> None:
        self.success_count += 1
        self.total_attempts += 1

    def record_failure(self, error: str = "") -> None:
        self.failure_count += 1
        self.total_attempts += 1
        if error:
            self.errors.append(error)

    @property
    def summary(self) -> str:
        return (
            f"{self.success_count}/{self.total_attempts} "
            f"({self.success_rate * 100:.1f}%)"
        )


@dataclass
class QualityMetrics:
    """Quality scores across tested scenarios."""

    scenario_scores: dict[str, float] = field(default_factory=dict)
    overall_score: Optional[float] = None

    def set_score(self, scenario_id: str, score: float) -> None:
        self.scenario_scores[scenario_id] = score
        self._recompute_overall()

    def _recompute_overall(self) -> None:
        if self.scenario_scores:
            self.overall_score = statistics.mean(self.scenario_scores.values())
        else:
            self.overall_score = None


@dataclass
class CostMetrics:
    """Token and cost tracking."""

    total_prompt_tokens: int = 0
    total_completion_tokens: int = 0
    total_tokens: int = 0

    def add_usage(self, prompt: int, completion: int) -> None:
        self.total_prompt_tokens += prompt
        self.total_completion_tokens += completion
        self.total_tokens += prompt + completion

    @property
    def avg_prompt_tokens(self) -> float:
        return _safe_float(self.total_prompt_tokens)

    @property
    def avg_completion_tokens(self) -> float:
        return _safe_float(self.total_completion_tokens)


# ── Helpers ───────────────────────────────────────────────────


def _safe_mean(values: list[float]) -> Optional[float]:
    return statistics.mean(values) if values else None


def _safe_min(values: list[float]) -> Optional[float]:
    return min(values) if values else None


def _safe_percentile(values: list[float], p: int) -> Optional[float]:
    if not values:
        return None
    sorted_v = sorted(values)
    k = (len(sorted_v) - 1) * p / 100
    f = int(k)
    c = f + 1
    if c >= len(sorted_v):
        return sorted_v[-1]
    return sorted_v[f] * (c - k) + sorted_v[c] * (k - f)


def _safe_float(v: int) -> float:
    return float(v) if v else 0.0
