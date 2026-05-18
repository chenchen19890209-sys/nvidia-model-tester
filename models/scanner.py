"""Model catalog scanner — discovers and categorises models."""

import re
from dataclasses import dataclass, field
from typing import Optional

from utils.api_client import NIMClient


@dataclass
class ModelInfo:
    """Normalised metadata about a single model."""

    id: str  # e.g. "nvidia/llama-3.3-nemotron-super-49b-v1"
    name: str  # Short human-readable name
    category: str  # llm, multimodal, image, audio, specialized
    free_endpoint: bool = False
    downloadable: bool = False
    publisher: str = ""
    description: str = ""
    tags: list[str] = field(default_factory=list)
    max_tokens: Optional[int] = None

    @property
    def is_chat_model(self) -> bool:
        """Heuristic: most chat models contain 'instruct' or lack generation keywords."""
        return self.category in ("llm", "multimodal")


# ── Keyword-based classification ────────────────────────────────

_CATEGORY_RULES: list[tuple[str, str, set[str]]] = [
    # (category, keyword_in_id_or_name, additional_tags)
    ("image", "image", {"text-to-image", "image-generation", "image-edit"}),
    ("image", "stable-diffusion", {"text-to-image"}),
    ("image", "flux", {"text-to-image"}),
    ("image", "sdxl", {"text-to-image"}),
    ("image", "qwen-image", {"text-to-image", "image-edit"}),
    ("audio", "voicechat", {"voice"}),
    ("audio", "asr", {"speech-recognition"}),
    ("audio", "riva", {"speech", "translation"}),
    ("audio", "tts", {"text-to-speech"}),
    ("multimodal", "vlm", {"vision"}),
    ("multimodal", "vision", {"vision"}),
    ("multimodal", "image-to-text", {"image-to-text"}),
    ("multimodal", "omni", {"multimodal"}),
    ("multimodal", "kimi", {"multimodal"}),
    ("multimodal", "qwen-vl", {"vision"}),
    ("multimodal", "nvlm", {"vision"}),
    ("specialized", "safety", {"content-safety", "guard"}),
    ("specialized", "guard", {"safety"}),
    ("specialized", "rerank", {"retrieval", "rerank"}),
    ("specialized", "ocr", {"ocr", "text-extraction"}),
    ("specialized", "content-safety", {"safety"}),
    ("specialized", "topic-control", {"safety"}),
    ("specialized", "jailbreak", {"safety"}),
    ("specialized", "gliner", {"ner", "pii"}),
    ("specialized", "usdcode", {"3d", "usd"}),
    ("specialized", "relighting", {"image", "video"}),
    ("specialized", "lip", {"video"}),
    ("specialized", "synthetic-video", {"video"}),
    ("specialized", "active-speaker", {"video"}),
    ("specialized", "ising", {"quantum"}),
    ("specialized", "calibration", {"quantum"}),
    ("specialized", "bio", {"healthcare"}),
    ("specialized", "drug", {"healthcare"}),
    ("specialized", "molecule", {"healthcare"}),
    ("specialized", "proteina", {"healthcare"}),
    ("llm", "llama", {"text-generation"}),
    ("llm", "nemotron", {"text-generation"}),
    ("llm", "mistral", {"text-generation"}),
    ("llm", "deepseek", {"text-generation"}),
    ("llm", "qwen", {"text-generation"}),
    ("llm", "gemma", {"text-generation"}),
    ("llm", "minimax", {"text-generation"}),
    ("llm", "glm", {"text-generation"}),
    ("llm", "mixtral", {"text-generation"}),
    ("llm", "phi", {"text-generation"}),
    ("llm", "code", {"code-generation"}),
    ("llm", "translation", {"translation"}),
    ("llm", "translate", {"translation"}),
]


def _classify(model_id: str, name: str) -> tuple[str, list[str]]:
    """Return (category, tags) for a model."""
    combined = f"{model_id} {name}".lower()
    matched_tags: set[str] = set()

    for category, keyword, tags in _CATEGORY_RULES:
        if keyword in combined:
            matched_tags.update(tags)
            return category, list(matched_tags)

    # Default: treat unknown chat-like models as LLM
    return "llm", ["text-generation"]


def _extract_name(model_id: str, raw: dict) -> str:
    """Best-effort human-readable name."""
    owner = raw.get("owned_by", model_id.split("/")[0] if "/" in model_id else "")
    short_id = model_id.split("/")[-1] if "/" in model_id else model_id
    # Clean up short id
    short_id = re.sub(r"[-_](v\d+|it|instruct)$", "", short_id)
    parts = short_id.replace("-", " ").replace("_", " ").split()
    name = " ".join(p.capitalize() for p in parts[:4])
    return f"{owner}: {name}" if owner else name


# ── Public API ──────────────────────────────────────────────────


def discover_models(client: Optional[NIMClient] = None) -> list[ModelInfo]:
    """Fetch models from the API and return classified metadata."""
    client = client or NIMClient()
    raw_models = client.list_models()

    results: list[ModelInfo] = []
    seen_ids: set[str] = set()

    for rm in raw_models:
        model_id: str = rm.get("id", rm.get("model", ""))
        if not model_id or model_id in seen_ids:
            continue
        seen_ids.add(model_id)

        name = _extract_name(model_id, rm)
        category, tags = _classify(model_id, name)

        info = ModelInfo(
            id=model_id,
            name=name,
            category=category,
            free_endpoint=rm.get("free_endpoint", False),
            downloadable=rm.get("downloadable", False),
            publisher=rm.get("owned_by", rm.get("publisher", "")),
            description=rm.get("description", rm.get("summary", "")),
            tags=tags,
        )
        results.append(info)

    return results


def group_by_category(models: list[ModelInfo]) -> dict[str, list[ModelInfo]]:
    """Return {category: [models]}."""
    groups: dict[str, list[ModelInfo]] = {}
    for m in models:
        groups.setdefault(m.category, []).append(m)
    return groups


def sample_models(
    models: list[ModelInfo], per_category: int = 3
) -> list[ModelInfo]:
    """Select a representative sample, at most *per_category* per category."""
    grouped = group_by_category(models)
    sampled: list[ModelInfo] = []
    for cat in sorted(grouped):
        sampled.extend(grouped[cat][:per_category])
    return sampled
