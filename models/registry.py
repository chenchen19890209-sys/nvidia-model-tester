"""模型元数据注册表 — 提供 API 中不可用的额外模型信息。

某些模型具有特殊参数或端点要求，这些信息不会通过标准的 /v1/models 
端点暴露。此注册表提供补充元数据以确保正确测试。
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ModelCapabilities:
    """模型的已知能力和特性。
    
    Attributes:
        model_id: 模型 ID
        supports_chat: 是否支持聊天模式
        supports_streaming: 是否支持流式输出
        supports_vision: 是否支持视觉输入
        supports_tools: 是否支持工具调用
        max_tokens_limit: 最大 token 限制
        recommended_temperature: 推荐温度参数
        requires_system_prompt: 是否需要系统提示
        notes: 备注信息
    """

    model_id: str
    supports_chat: bool = True
    supports_streaming: bool = True
    supports_vision: bool = False
    supports_tools: bool = False
    max_tokens_limit: Optional[int] = None
    recommended_temperature: float = 0.7
    requires_system_prompt: bool = False
    notes: str = ""


# 已知模型规格注册表
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
    """获取已知能力，如果未知则返回默认值。
    
    Args:
        model_id: 模型 ID
        
    Returns:
        模型能力对象
    """
    return _MODEL_REGISTRY.get(
        model_id,
        ModelCapabilities(model_id=model_id),
    )
