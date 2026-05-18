"""Base test runner interface."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional

from models.scanner import ModelInfo
from utils.api_client import NIMClient


@dataclass
class TestResult:
    """Standard result container for any test."""

    model_id: str
    test_name: str
    passed: bool
    score: float  # 0.0 - 1.0
    details: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class BaseTester(ABC):
    """Abstract tester — each subclass implements a single test dimension."""

    def __init__(self, client: Optional[NIMClient] = None) -> None:
        self.client = client or NIMClient()

    @abstractmethod
    def name(self) -> str:
        """Short identifier for this test suite."""
        ...

    @abstractmethod
    def description(self) -> str:
        """Human-readable description."""
        ...

    @abstractmethod
    def test_model(self, model: ModelInfo) -> TestResult:
        """Run all tests for a single model and return results."""
        ...

    def skip_reason(self, model: ModelInfo) -> Optional[str]:
        """Return a string if this model should be skipped, else None."""
        return None
