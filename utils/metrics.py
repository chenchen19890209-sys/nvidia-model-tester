"""指标计算辅助模块。

该模块提供用于聚合和分析测试结果的各类指标类，包括：
- 计时指标（TTFT、总延迟、吞吐量）
- 可用性指标（成功率、失败率）
- 质量指标（场景评分）
- 成本指标（token 用量统计）
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class TimingMetrics:
    """跨多次运行聚合的模型计时指标。
    
    Attributes:
        ttft_ms: 首 token 时间列表（毫秒）
        total_ms: 总响应时间列表（毫秒）
        tokens_per_second: 每秒生成 token 数列表
    """

    ttft_ms: list[float] = field(default_factory=list)
    total_ms: list[float] = field(default_factory=list)
    tokens_per_second: list[float] = field(default_factory=list)
    _run_tokens: list[int] = field(default_factory=list)

    def add_run(self, ttft: float, total: float, output_tokens: int) -> None:
        """添加一次运行的计时数据。

        Args:
            ttft: 首 token 时间（毫秒）
            total: 总响应时间（毫秒）
            output_tokens: 输出的 token 数量
        """
        self.ttft_ms.append(ttft)
        self.total_ms.append(total)
        self._run_tokens.append(output_tokens)
        decode_ms = total - ttft
        if decode_ms > 0 and output_tokens > 0:
            self.tokens_per_second.append(output_tokens / (decode_ms / 1000))

    @property
    def avg_ttft_ms(self) -> Optional[float]:
        """平均首 token 时间（毫秒）。"""
        return _safe_mean(self.ttft_ms)

    @property
    def min_ttft_ms(self) -> Optional[float]:
        """最小首 token 时间（毫秒）。"""
        return _safe_min(self.ttft_ms)

    @property
    def p95_ttft_ms(self) -> Optional[float]:
        """P95 首 token 时间（毫秒）。"""
        return _safe_percentile(self.ttft_ms, 95)

    @property
    def avg_total_ms(self) -> Optional[float]:
        """平均总响应时间（毫秒）。"""
        return _safe_mean(self.total_ms)

    @property
    def avg_tokens_per_second(self) -> Optional[float]:
        """平均每秒生成 token 数。"""
        return _safe_mean(self.tokens_per_second)

    @property
    def total_output_tokens(self) -> int:
        """总输出 token 数。"""
        return sum(self._run_tokens)

    @property
    def run_count(self) -> int:
        """运行次数。"""
        return len(self.total_ms)


@dataclass
class AvailabilityMetrics:
    """API 可用性和错误指标。
    
    Attributes:
        success_count: 成功次数
        failure_count: 失败次数
        total_attempts: 总尝试次数
        errors: 错误消息列表
    """

    success_count: int = 0
    failure_count: int = 0
    total_attempts: int = 0
    errors: list[str] = field(default_factory=list)

    @property
    def success_rate(self) -> float:
        """成功率。"""
        if self.total_attempts == 0:
            return 0.0
        return self.success_count / self.total_attempts

    def record_success(self) -> None:
        """记录一次成功。"""
        self.success_count += 1
        self.total_attempts += 1

    def record_failure(self, error: str = "") -> None:
        """记录一次失败。
        
        Args:
            error: 错误消息
        """
        self.failure_count += 1
        self.total_attempts += 1
        if error:
            self.errors.append(error)

    @property
    def summary(self) -> str:
        """获取摘要字符串。"""
        return (
            f"{self.success_count}/{self.total_attempts} "
            f"({self.success_rate * 100:.1f}%)"
        )


@dataclass
class QualityMetrics:
    """跨测试场景的质量评分。
    
    Attributes:
        scenario_scores: 各场景的评分字典
        overall_score: 总体评分
    """

    scenario_scores: dict[str, float] = field(default_factory=dict)
    overall_score: Optional[float] = None

    def set_score(self, scenario_id: str, score: float) -> None:
        """设置某个场景的评分。
        
        Args:
            scenario_id: 场景 ID
            score: 评分（0-1）
        """
        self.scenario_scores[scenario_id] = score
        self._recompute_overall()

    def _recompute_overall(self) -> None:
        """重新计算总体评分。"""
        if self.scenario_scores:
            self.overall_score = statistics.mean(self.scenario_scores.values())
        else:
            self.overall_score = None


@dataclass
class CostMetrics:
    """Token 用量和成本跟踪。
    
    Attributes:
        total_prompt_tokens: 总输入 token 数
        total_completion_tokens: 总输出 token 数
        total_tokens: 总 token 数
    """

    total_prompt_tokens: int = 0
    total_completion_tokens: int = 0
    total_tokens: int = 0

    def add_usage(self, prompt: int, completion: int) -> None:
        """添加一次使用的 token 统计。
        
        Args:
            prompt: 输入 token 数
            completion: 输出 token 数
        """
        self.total_prompt_tokens += prompt
        self.total_completion_tokens += completion
        self.total_tokens += prompt + completion

    @property
    def avg_prompt_tokens(self) -> float:
        """平均输入 token 数。"""
        return _safe_float(self.total_prompt_tokens)

    @property
    def avg_completion_tokens(self) -> float:
        """平均输出 token 数。"""
        return _safe_float(self.total_completion_tokens)


# ── 辅助函数 ───────────────────────────────────────────────────


def _safe_mean(values: list[float]) -> Optional[float]:
    """安全地计算平均值，处理空列表情况。
    
    Args:
        values: 数值列表
        
    Returns:
        平均值，如果列表为空则返回 None
    """
    return statistics.mean(values) if values else None


def _safe_min(values: list[float]) -> Optional[float]:
    """安全地获取最小值，处理空列表情况。
    
    Args:
        values: 数值列表
        
    Returns:
        最小值，如果列表为空则返回 None
    """
    return min(values) if values else None


def _safe_percentile(values: list[float], p: int) -> Optional[float]:
    """安全地计算百分位数，处理空列表情况。
    
    Args:
        values: 数值列表
        p: 百分位（0-100）
        
    Returns:
        百分位数值，如果列表为空则返回 None
    """
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
    """安全地将整数转换为浮点数。
    
    Args:
        v: 整数值
        
    Returns:
        浮点数值，如果输入为 0 则返回 0.0
    """
    return float(v) if v else 0.0
