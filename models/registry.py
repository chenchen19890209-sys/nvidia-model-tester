"""Model metadata registry — additional known model info not available from API.

Some models have special parameters or endpoint requirements that aren't
exposed through the standard /v1/models endpoint. This registry provides
supplementary metadata for correct testing.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ModelCapabilities:
    """Known capabilities and quirks for a model."""

    model_id: str
    supports_chat: bool = True
    supports_streaming: bool = True
    supports_vision: bool = False
    supports_tools: bool = False
    max_tokens_limit: Optional[int] = None
    recommended_temperature: float = 0.7
    requires_system_prompt: bool = False
    notes: str = ""


# Registry of known model specifications
_MODEL_REGISTRY: dict[str, ModelCapabilities] = {
    "nvidia/nemotron-3-super-120b-a12b": ModelCapabilities(
        "nvidia/nemotron-3-super-120b-a12b",
        max_tokens_limit=1024000,
        supports_tools=True,
        recommended_temperature=0.6,
        notes="Hybrid Mamba-Transformer MoE, 1M context",
    ),
    "nvidia/nemotron-3-nano-30b-a3b": ModelCapabilities(
        "nvidia/nemotron-3-nano-30b-a3b",
        max_tokens_limit=128000,
        recommended_temperature=0.6,
        notes="Small MoE, good for low-latency tasks",
    ),
    "nvidia/llama-3.3-nemotron-super-49b-v1": ModelCapabilities(
        "nvidia/llama-3.3-nemotron-super-49b-v1",
        max_tokens_limit=128000,
        supports_tools=True,
        recommended_temperature=0.6,
        notes="Strong all-rounder, recommended reference model",
    ),
    "nvidia/llama-3.1-nemotron-ultra-253b-v1": ModelCapabilities(
        "nvidia/llama-3.1-nemotron-ultra-253b-v1",
        max_tokens_limit=128000,
        supports_tools=True,
        recommended_temperature=0.6,
        notes="Largest Nemotron model, high quality but slower",
    ),
}


def get_capabilities(model_id: str) -> ModelCapabilities:
    """Return known capabilities, falling back to defaults."""
    return _MODEL_REGISTRY.get(
        model_id,
        ModelCapabilities(model_id=model_id),
    )
