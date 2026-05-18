"""Quality test — LLM-as-judge evaluation using a reference model.

Uses a strong NVIDIA model to score the output quality of each tested model.
"""

from typing import Optional

from config import settings
from models.scanner import ModelInfo
from scenarios.prompts import prompts_for_category
from tests.base import BaseTester, TestResult
from utils.api_client import NIMClient
from utils.metrics import QualityMetrics

# ── Judge prompt template ─────────────────────────────────────

_JUDGE_SYSTEM_PROMPT = (
    "You are an expert AI evaluator. Your job is to rate the quality of a model's "
    "response to a given instruction on a scale of 1 to 10.\n\n"
    "Evaluate based on:\n"
    "1. **Correctness** — Is the response factually accurate and logically sound?\n"
    "2. **Completeness** — Does it fully address the instruction?\n"
    "3. **Clarity** — Is it well-structured and easy to understand?\n"
    "4. **Relevance** — Is every part of the response relevant to the query?\n\n"
    "Output ONLY a single integer score (1-10) and a one-sentence justification "
    "on the next line. Example:\n"
    "Score: 8\n"
    "Justification: The response is accurate and well-structured but could be more concise."
)

_JUDGE_USER_PROMPT = (
    "Instruction:\n{instruction}\n\n"
    "Model Response:\n{response}\n\n"
    "Rate this response from 1 to 10."
)


class QualityTester(BaseTester):
    """Uses a reference model to score response quality."""

    def __init__(self, client: Optional[NIMClient] = None) -> None:
        super().__init__(client)
        self.reference_model = settings.QUALITY_REFERENCE_MODEL
        self._quality: dict[str, QualityMetrics] = {}

    def name(self) -> str:
        return "quality"

    def description(self) -> str:
        return (
            f"LLM-as-judge quality evaluation using "
            f"{self.reference_model} as the reference"
        )

    def skip_reason(self, model: ModelInfo) -> Optional[str]:
        if not settings.ENABLE_QUALITY_EVAL:
            return "Quality evaluation disabled in config"
        if not model.is_chat_model:
            return "Non-chat model — skipping quality evaluation"
        if model.id == self.reference_model:
            # Can't judge itself — skip
            return "Model is the reference judge — skipping self-evaluation"
        return None

    def test_model(self, model: ModelInfo) -> TestResult:
        qm = QualityMetrics()
        errors: list[str] = []
        prompts = prompts_for_category(model.category)

        # Only evaluate a subset to avoid excessive API cost
        eval_prompts = prompts[:6]

        for prompt in eval_prompts:
            try:
                # 1. Get response from the model under test
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

                if not content:
                    qm.set_score(prompt.id, 0.0)
                    continue

                # 2. Get score from the judge model
                instruction = prompt.messages[-1]["content"]
                judge_messages = [
                    {"role": "system", "content": _JUDGE_SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": _JUDGE_USER_PROMPT.format(
                            instruction=instruction[:2000],
                            response=content[:4000],
                        ),
                    },
                ]

                judge_resp = self.client.chat_completion(
                    model=self.reference_model,
                    messages=judge_messages,
                    max_tokens=100,
                    temperature=0.0,
                )
                judge_content = (
                    judge_resp.get("choices", [{}])[0]
                    .get("message", {})
                    .get("content", "")
                )

                # Parse score
                score = self._parse_judge_score(judge_content)
                qm.set_score(prompt.id, score / 10.0)

            except Exception as e:
                errors.append(f"{prompt.id}: {e}")
                qm.set_score(prompt.id, 0.0)

        self._quality[model.id] = qm

        return TestResult(
            model_id=model.id,
            test_name=self.name(),
            passed=(qm.overall_score or 0.0) >= 0.4,
            score=qm.overall_score or 0.0,
            details={
                "scenario_scores": qm.scenario_scores,
                "overall_score": qm.overall_score,
                "reference_model": self.reference_model,
                "scenarios_evaluated": len(eval_prompts),
            },
            errors=errors,
        )

    @property
    def all_quality(self) -> dict[str, QualityMetrics]:
        return self._quality

    # ── Internal ───────────────────────────────────────────────

    @staticmethod
    def _parse_judge_score(text: str) -> float:
        """Extract the numeric score from judge output."""
        import re

        match = re.search(r"Score:\s*(\d+\.?\d*)", text)
        if match:
            try:
                score = float(match.group(1))
                return max(1.0, min(10.0, score))
            except ValueError:
                pass
        return 5.0  # Default middle score
