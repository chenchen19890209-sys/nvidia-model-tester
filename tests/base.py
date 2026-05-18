"""基础测试运行器接口。

该模块定义了所有测试类的抽象基类和标准结果容器。
每个具体的测试类都应该继承 BaseTester 并实现其抽象方法。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional

from models.scanner import ModelInfo
from utils.api_client import NIMClient


@dataclass
class TestResult:
    """任何测试的标准结果容器。
    
    Attributes:
        model_id: 被测试的模型 ID
        test_name: 测试名称
        passed: 是否通过测试
        score: 评分（0.0 - 1.0）
        details: 详细结果字典
        errors: 错误消息列表
        warnings: 警告消息列表
    """

    model_id: str
    test_name: str
    passed: bool
    score: float  # 0.0 - 1.0
    details: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class BaseTester(ABC):
    """抽象测试器 — 每个子类实现一个测试维度。
    
    所有具体的测试类都应该继承此基类并实现以下抽象方法：
    - name(): 返回测试套件的简短标识符
    - description(): 返回人类可读的描述
    - test_model(): 对单个模型运行所有测试并返回结果
    """

    def __init__(self, client: Optional[NIMClient] = None) -> None:
        """初始化测试器。
        
        Args:
            client: NIM 客户端实例，如果为 None 则创建新实例
        """
        self.client = client or NIMClient()

    @abstractmethod
    def name(self) -> str:
        """返回此测试套件的简短标识符。
        
        Returns:
            测试套件名称
        """
        ...

    @abstractmethod
    def description(self) -> str:
        """返回人类可读的描述。
        
        Returns:
            测试描述
        """
        ...

    @abstractmethod
    def test_model(self, model: ModelInfo) -> TestResult:
        """对单个模型运行所有测试并返回结果。
        
        Args:
            model: 要测试的模型信息
            
        Returns:
            测试结果对象
        """
        ...

    def skip_reason(self, model: ModelInfo) -> Optional[str]:
        """如果应该跳过此模型，返回原因字符串，否则返回 None。
        
        Args:
            model: 模型信息
            
        Returns:
            跳过原因，如果不应该跳过则返回 None
        """
        return None
