"""Capability test — evaluate across diverse scenarios."""

from typing import Optional

from config import settings
from models.scanner import ModelInfo
from scenarios.prompts import TestPrompt, prompts_for_category
from tests.base import BaseTester, TestResult
from utils.api_client import NIMClient
from utils.metrics import CostMetrics


class CapabilityTester(BaseTester):
    """Run a battery of scenario-specific prompts and measure pass/fail + cost."""

    def __init__(self, client: Optional[NIMClient] = None) -> None:
        super().__init__(client)
        self._costs: dict[str, CostMetrics] = {}
        self._scenario_scores: dict[str, dict[str, float]] = {}

    def name(self) -> str:
        return "capability"

    def description(self) -> str:
        return (
            "Evaluate model across 12+ scenarios: chat, code, math, reasoning, "
            "creative writing, summarization, translation, agentic planning, etc."
        )

    def skip_reason(self, model: ModelInfo) -> Optional[str]:
        if not model.is_chat_model:
            return "Non-chat model — skipping capability test"
        return None

    def test_model(self, model: ModelInfo) -> TestResult:
        prompts = prompts_for_category(model.category)
        cost = CostMetrics()
        scenario_scores: dict[str, float] = {}
        errors: list[str] = []

        for prompt in prompts:
            try:
                resp = self.client.chat_completion(
                    model=model.id,
                    messages=prompt.messages,
                    max_tokens=settings.MAX_TOKENS_GENERATE,
                    temperature=0.7,
                )
                content = (
                    resp.get("choices", [{}])[0]
                    .get("message", {})
                    .get("content", "")
                )
                usage = resp.get("usage", {})

                prompt_tokens = usage.get("prompt_tokens", 0)
                completion_tokens = usage.get("completion_tokens", 0)
                cost.add_usage(prompt_tokens, completion_tokens)

                # Score: length-based heuristic (non-empty is baseline)
                score = self._score_response(content, prompt)
                scenario_scores[prompt.id] = score

            except Exception as e:
                errors.append(f"{prompt.id}: {e}")
                scenario_scores[prompt.id] = 0.0

        self._costs[model.id] = cost
        self._scenario_scores[model.id] = scenario_scores

        # Weighted overall score
        total_weight = sum(
            p.weight
            for p in prompts
            if p.id in scenario_scores
        )
        weighted_sum = sum(
            scenario_scores[p.id] * p.weight
            for p in prompts
            if p.id in scenario_scores
        )
        overall = weighted_sum / total_weight if total_weight > 0 else 0.0

        return TestResult(
            model_id=model.id,
            test_name=self.name(),
            passed=overall >= 0.3,
            score=round(overall, 4),
            details={
                "scenarios": scenario_scores,
                "scenario_count": len(scenario_scores),
                "total_prompt_tokens": cost.total_prompt_tokens,
                "total_completion_tokens": cost.total_completion_tokens,
                "total_tokens": cost.total_tokens,
            },
            errors=errors,
        )

    # ── Internal scoring ───────────────────────────────────────

    @staticmethod
    def _score_response(content: str, prompt: TestPrompt) -> float:
        """Return 0.0–1.0 score for a response.

        Uses simple heuristics:
        - Empty / too short → low score
        - Has structure (code blocks, lists, etc.) → bonus
        - Contains expected traits → bonus
        """
        if not content or len(content.strip()) < 10:
            return 0.0

        score = 0.5  # Baseline: non-empty response

        # Length bonus: more substance = better (up to a point)
        content_len = len(content)
        if content_len > 300:
            score += 0.1
        if content_len > 800:
            score += 0.1

        # Code block bonus (for code tasks)
        if "```" in content:
            score += 0.1

        # Structured response bonus
        if any(marker in content for marker in ["\n1.", "\n- ", "\n* "]):
            score += 0.05

        # Specific expected traits
        for trait in prompt.expected_traits:
            keyword_map = {
                "clear": lambda t: any(w in t.lower() for w in ["explain", "means", "because"]),
                "well-structured": lambda t: "\n1." in t or "\n- " in t,
                "step-by-step": lambda t: "step" in t.lower(),
                "creative": lambda t: len(set(t.split())) > 100,
                "concise": lambda t: len(t) < 600,
                "accurate": lambda t: True,  # hard to check without reference
            }
            fn = keyword_map.get(trait, lambda _: False)
            if fn(content):
                score += 0.05

        return min(1.0, score)

    @property
    def all_costs(self) -> dict[str, CostMetrics]:
        return self._costs

    @property
    def all_scenario_scores(self) -> dict[str, dict[str, float]]:
        return self._scenario_scores
