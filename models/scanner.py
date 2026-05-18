"""模型目录扫描器 — 发现和分类模型。

该模块负责从 NVIDIA API 获取模型列表，并根据模型 ID 和名称自动分类。
支持的类别包括：LLM、多模态、图像、音频、专用模型等。
"""

import re
from dataclasses import dataclass, field
from typing import Optional

from utils.api_client import NIMClient


@dataclass
class ModelInfo:
    """单个模型的标准化元数据。
    
    Attributes:
        id: 模型 ID（例如 "nvidia/llama-3.3-nemotron-super-49b-v1"）
        name: 简短的人类可读名称
        category: 类别（llm, multimodal, image, audio, specialized）
        free_endpoint: 是否为免费端点
        downloadable: 是否可下载
        publisher: 发布者
        description: 描述
        tags: 标签列表
        max_tokens: 最大 token 数
    """

    id: str
    name: str
    category: str
    free_endpoint: bool = False
    downloadable: bool = False
    publisher: str = ""
    description: str = ""
    tags: list[str] = field(default_factory=list)
    max_tokens: Optional[int] = None

    @property
    def is_chat_model(self) -> bool:
        """启发式判断：大多数聊天模型包含 'instruct' 或缺少生成关键词。
        
        Returns:
            True 如果是聊天模型
        """
        return self.category in ("llm", "multimodal")


# ── 基于关键词的分类规则 ───────────────────────────────────────

_CATEGORY_RULES: list[tuple[str, str, set[str]]] = [
    # (类别, ID或名称中的关键词, 附加标签)
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
    """返回模型的 (类别, 标签)。
    
    Args:
        model_id: 模型 ID
        name: 模型名称
        
    Returns:
        元组 (类别, 标签列表)
    """
    combined = f"{model_id} {name}".lower()
    matched_tags: set[str] = set()

    for category, keyword, tags in _CATEGORY_RULES:
        if keyword in combined:
            matched_tags.update(tags)
            return category, list(matched_tags)

    # 默认：将未知的类聊天模型视为 LLM
    return "llm", ["text-generation"]


def _extract_name(model_id: str, raw: dict) -> str:
    """尽力提取人类可读的名称。
    
    Args:
        model_id: 模型 ID
        raw: 原始模型数据字典
        
    Returns:
        人类可读的模型名称
    """
    owner = raw.get("owned_by", model_id.split("/")[0] if "/" in model_id else "")
    short_id = model_id.split("/")[-1] if "/" in model_id else model_id
    # 清理短 ID
    short_id = re.sub(r"[-_](v\d+|it|instruct)$", "", short_id)
    parts = short_id.replace("-", " ").replace("_", " ").split()
    name = " ".join(p.capitalize() for p in parts[:4])
    return f"{owner}: {name}" if owner else name


# ── 公共 API ──────────────────────────────────────────────────


def discover_models(client: Optional[NIMClient] = None) -> list[ModelInfo]:
    """从 API 获取模型并返回分类后的元数据。
    
    Args:
        client: NIM 客户端实例，如果为 None 则创建新实例
        
    Returns:
        模型信息列表
    """
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
    """按类别分组模型。
    
    Args:
        models: 模型列表
        
    Returns:
        字典 {类别: [模型列表]}
    """
    groups: dict[str, list[ModelInfo]] = {}
    for m in models:
        groups.setdefault(m.category, []).append(m)
    return groups


def sample_models(
    models: list[ModelInfo], per_category: int = 3
) -> list[ModelInfo]:
    """选择代表性样本，每个类别最多 *per_category* 个模型。
    
    Args:
        models: 模型列表
        per_category: 每个类别的样本数量
        
    Returns:
        抽样后的模型列表
    """
    grouped = group_by_category(models)
    sampled: list[ModelInfo] = []
    for cat in sorted(grouped):
        sampled.extend(grouped[cat][:per_category])
    return sampled
