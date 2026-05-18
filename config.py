"""Configuration for NVIDIA Model Tester."""

import os
from enum import Enum
from typing import Literal, Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ReportFormat(str, Enum):
    HTML = "html"
    JSON = "json"
    BOTH = "both"


class TestScope(str, Enum):
    """Which models to include in the test run."""

    ALL = "all"  # All discovered models
    LLM = "llm"  # Language models only
    MULTIMODAL = "multimodal"  # Vision + language
    IMAGE = "image"  # Image generation/editing
    AUDIO = "audio"  # Speech recognition / TTS
    SPECIALIZED = "specialized"  # Safety, rerank, OCR, etc.
    SAMPLE = "sample"  # A representative sample of each category


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        # env_prefix="NV_TEST_",  # 注释掉前缀，直接读取字段名
        case_sensitive=True,  # 保持大小写敏感
    )

    # ── NVIDIA API ──────────────────────────────────────────────
    NVIDIA_API_KEY: str = Field(
        default="",
        description="NVIDIA API key from build.nvidia.com",
    )
    NVIDIA_API_BASE: str = Field(
        default="https://integrate.api.nvidia.com/v1",
        description="Base URL for NVIDIA NIM API",
    )

    # ── Test scope ──────────────────────────────────────────────
    TEST_SCOPE: TestScope = Field(default=TestScope.ALL)
    MAX_MODELS: Optional[int] = Field(
        default=None,
        description="Cap the number of models tested (None = all)",
    )
    CONCURRENCY: int = Field(
        default=5,
        ge=1,
        le=50,
        description="Max concurrent API requests",
    )
    REQUEST_TIMEOUT: int = Field(
        default=120,
        ge=10,
        description="Per-request timeout in seconds",
    )
    MAX_RETRIES: int = Field(
        default=3,
        ge=0,
        le=10,
        description="Maximum number of retries on rate limit (429) or network errors",
    )
    RETRY_DELAY: float = Field(
        default=2.0,
        ge=0.1,
        description="Base delay in seconds between retries (uses exponential backoff)",
    )

    # ── Per-test settings ───────────────────────────────────────
    TEST_REPEAT: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Repeat each test N times for stable metrics",
    )
    MAX_TOKENS_GENERATE: int = Field(
        default=512,
        description="Default max_tokens for generation tasks",
    )
    MAX_TOKENS_LONG_CONTEXT: int = Field(
        default=4096,
        description="Max tokens for long-context tests",
    )

    # ── Output ──────────────────────────────────────────────────
    OUTPUT_DIR: str = Field(
        default="./output",
        description="Directory for test results and reports",
    )
    REPORT_FORMAT: ReportFormat = Field(default=ReportFormat.BOTH)
    REPORT_TITLE: str = Field(
        default="NVIDIA Model Test Report",
    )

    # ── Cost estimation ─────────────────────────────────────────
    COST_PER_1K_INPUT_TOKENS: float = Field(
        default=0.0001,
        description="Default cost per 1k input tokens (user can override)",
    )
    COST_PER_1K_OUTPUT_TOKENS: float = Field(
        default=0.0004,
        description="Default cost per 1k output tokens (user can override)",
    )

    # ── Quality evaluation ─────────────────────────────────────
    QUALITY_REFERENCE_MODEL: str = Field(
        default="nvidia/llama-3.3-nemotron-super-49b-v1",
        description="Strong model used as reference for quality scoring",
    )
    ENABLE_QUALITY_EVAL: bool = Field(
        default=True,
        description="Whether to run LLM-as-judge quality evaluation",
    )

    @property
    def api_key(self) -> str:
        key = self.NVIDIA_API_KEY or os.environ.get("NVIDIA_API_KEY", "")
        if not key:
            print(
                "WARNING: NVIDIA_API_KEY is not set. "
                "Set it via .env file or NVIDIA_API_KEY environment variable."
            )
        return key

    @property
    def headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }


# Global singleton
settings = Settings()
