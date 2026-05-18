"""Configuration for NVIDIA Model Tester.

This module defines all test-related configuration items, including:
- NVIDIA API connection settings
- Test scope and concurrency control
- Output format and report settings
- Cost estimation parameters
- Quality evaluation options
"""

import os
from enum import Enum
from typing import Literal, Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ReportFormat(str, Enum):
    """报告输出格式枚举。"""
    HTML = "html"      # HTML 格式，适合浏览器查看
    JSON = "json"      # JSON 格式，适合程序处理
    BOTH = "both"      # 同时生成两种格式


class TestScope(str, Enum):
    """测试范围枚举，定义要包含哪些类型的模型。"""

    ALL = "all"                    # 所有发现的模型
    LLM = "llm"                    # 仅语言模型
    MULTIMODAL = "multimodal"      # 视觉 + 语言多模态模型
    IMAGE = "image"                # 图像生成/编辑模型
    AUDIO = "audio"                # 语音识别 / 文本转语音模型
    SPECIALIZED = "specialized"    # 专用模型（安全、重排序、OCR等）
    SAMPLE = "sample"              # 每个类别的代表性样本


class Settings(BaseSettings):
    """全局配置类，管理所有测试设置。
    
    使用 Pydantic Settings 从环境变量和 .env 文件加载配置。
    支持类型验证和默认值。
    """
    model_config = SettingsConfigDict(
        env_file=".env",              # 从 .env 文件读取配置
        env_file_encoding="utf-8",    # 文件编码
        # env_prefix="NV_TEST_",     # 注释掉前缀，直接读取字段名
        case_sensitive=True,          # 保持大小写敏感
    )

    # ── NVIDIA API 配置 ──────────────────────────────────────────────
    NVIDIA_API_KEY: str = Field(
        default="",
        description="从 build.nvidia.com 获取的 NVIDIA API 密钥",
    )
    NVIDIA_API_BASE: str = Field(
        default="https://integrate.api.nvidia.com/v1",
        description="NVIDIA NIM API 的基础 URL",
    )

    # ── 测试范围配置 ──────────────────────────────────────────────
    TEST_SCOPE: TestScope = Field(default=TestScope.ALL)
    MAX_MODELS: Optional[int] = Field(
        default=None,
        description="限制测试的模型数量（None 表示测试所有模型）",
    )
    CONCURRENCY: int = Field(
        default=5,
        ge=1,
        le=50,
        description="最大并发 API 请求数",
    )
    REQUEST_TIMEOUT: int = Field(
        default=120,
        ge=10,
        description="单个请求的超时时间（秒）",
    )
    MAX_RETRIES: int = Field(
        default=3,
        ge=0,
        le=10,
        description="速率限制（429）或网络错误时的最大重试次数",
    )
    RETRY_DELAY: float = Field(
        default=2.0,
        ge=0.1,
        description="重试之间的基础延迟时间（秒），使用指数退避策略",
    )

    # ── 单次测试设置 ───────────────────────────────────────────────
    TEST_REPEAT: int = Field(
        default=3,
        ge=1,
        le=10,
        description="每个测试重复执行的次数，以获得稳定的指标",
    )
    MAX_TOKENS_GENERATE: int = Field(
        default=512,
        description="生成任务的默认最大 token 数",
    )
    MAX_TOKENS_LONG_CONTEXT: int = Field(
        default=4096,
        description="长上下文测试的最大 token 数",
    )

    # ── 输出配置 ──────────────────────────────────────────────────
    OUTPUT_DIR: str = Field(
        default="./output",
        description="测试结果和报告的输出目录",
    )
    REPORT_FORMAT: ReportFormat = Field(default=ReportFormat.BOTH)
    REPORT_TITLE: str = Field(
        default="NVIDIA 模型测试报告",
    )

    # ── 成本估算 ─────────────────────────────────────────────────
    COST_PER_1K_INPUT_TOKENS: float = Field(
        default=0.0001,
        description="每 1000 个输入 token 的默认成本（用户可以覆盖）",
    )
    COST_PER_1K_OUTPUT_TOKENS: float = Field(
        default=0.0004,
        description="每 1000 个输出 token 的默认成本（用户可以覆盖）",
    )

    # ── 质量评估 ─────────────────────────────────────────────────
    QUALITY_REFERENCE_MODEL: str = Field(
        default="nvidia/llama-3.3-nemotron-super-49b-v1",
        description="用作质量评分参考的强模型",
    )
    ENABLE_QUALITY_EVAL: bool = Field(
        default=True,
        description="是否运行 LLM-as-judge 质量评估",
    )

    @property
    def api_key(self) -> str:
        """获取 API 密钥。
        
        优先从配置中获取，如果未设置则从环境变量读取。
        如果两者都未设置，会打印警告信息。
        
        Returns:
            API 密钥字符串
        """
        key = self.NVIDIA_API_KEY or os.environ.get("NVIDIA_API_KEY", "")
        if not key:
            print(
                "WARNING: NVIDIA_API_KEY is not set. "
                "Set it via .env file or NVIDIA_API_KEY environment variable."
            )
        return key

    @property
    def headers(self) -> dict[str, str]:
        """获取 HTTP 请求头。
        
        包含授权令牌和内容类型，用于所有 API 请求。
        
        Returns:
            包含 Authorization 和 Content-Type 的字典
        """
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }


# 全局单例配置对象
settings = Settings()
