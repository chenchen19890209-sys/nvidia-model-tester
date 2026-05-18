"""OpenAI 兼容的 NVIDIA NIM API 客户端。

该模块提供了与 NVIDIA NIM API 交互的核心功能，包括：
- 速率限制控制（避免触发 429 错误）
- 自动重试机制（指数退避策略）
- 健康检查、模型列表获取
- 聊天完成和流式响应
- 性能计时（TTFT、总延迟等）
"""

import json
import time
from typing import Any, Optional
from collections import deque
from threading import Lock

import httpx

from config import settings


class RateLimiter:
    """速率限制器，用于避免触发 API 速率限制。

    NVIDIA NIM API 限制：每分钟 40 次请求。
    使用线程安全的滑动窗口算法，acquire_slot() 原子化完成
    检查 + 预留，消除 check-then-act 竞态条件。
    """

    def __init__(self, max_requests: int = 38, window_seconds: float = 60.0):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: deque[float] = deque()
        self.lock = Lock()

    def acquire_slot(self, timeout: float = 120.0) -> bool:
        """原子化检查并预留一个速率限制槽位。

        同时完成过期清理、容量检查和槽位预留，
        调用者之间不会出现 TOCTOU 竞态条件。

        Args:
            timeout: 最大等待时间（秒）

        Returns:
            True 如果成功预留槽位，False 如果超时
        """
        start = time.monotonic()
        while True:
            with self.lock:
                now = time.time()
                cutoff = now - self.window_seconds
                while self.requests and self.requests[0] < cutoff:
                    self.requests.popleft()

                if len(self.requests) < self.max_requests:
                    self.requests.append(now)
                    return True

                oldest_expiry = self.requests[0] + self.window_seconds
                wait = oldest_expiry - now

            elapsed = time.monotonic() - start
            if elapsed >= timeout:
                return False
            time.sleep(max(0.05, min(wait, timeout - elapsed, 0.5)))


class NIMClient:
    """NVIDIA NIM API 的轻量级、无状态 HTTP 客户端。
    
    提供所有必要的 API 调用方法，内置速率限制和重试机制。
    """

    # 所有客户端实例共享的速率限制器
    _rate_limiter = RateLimiter(max_requests=38, window_seconds=60.0)

    def __init__(self) -> None:
        """初始化 NIM 客户端。
        
        从全局配置中读取基础 URL、超时时间和重试设置。
        """
        self.base_url = settings.NVIDIA_API_BASE.rstrip("/")
        self.timeout = settings.REQUEST_TIMEOUT
        self.max_retries = settings.MAX_RETRIES
        self.retry_delay = settings.RETRY_DELAY

    def _headers(self) -> dict[str, str]:
        """获取 HTTP 请求头。
        
        Returns:
            包含授权令牌和内容类型的字典
        """
        return settings.headers

    def _make_request(self, func, *args, **kwargs):
        """发起 API 请求，包含速率限制和重试逻辑。

        仅在首次尝试时获取速率限制槽位（原子操作）。
        重试时不重复获取槽位，避免失败请求浪费配额。

        Args:
            func: 要调用的 HTTP 请求函数
            *args, **kwargs: 传递给函数的参数

        Returns:
            API 响应结果

        Raises:
            Exception: 如果所有重试都失败
        """
        last_error = None

        for attempt in range(self.max_retries + 1):
            if attempt == 0:
                if not self._rate_limiter.acquire_slot(timeout=120.0):
                    raise Exception("速率限制超时 - 无法获取槽位")
            elif attempt > 0:
                # 指数退避等待
                wait_time = self.retry_delay * (2 ** (attempt - 1))
                time.sleep(wait_time)

            try:
                return func(*args, **kwargs)

            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:
                    print(
                        f"    ⚠️  速率限制 (429)，"
                        f"尝试 {attempt + 1}/{self.max_retries + 1}"
                    )
                    last_error = e
                else:
                    raise
            except Exception as e:
                last_error = e
                if attempt < self.max_retries:
                    print(
                        f"    ⚠️  请求失败，重试 (尝试 {attempt + 1}/{self.max_retries + 1}): "
                        f"{str(e)[:80]}"
                    )
                else:
                    raise

        raise last_error

    # ── 健康检查 ────────────────────────────────────────────────

    def health_check(self) -> tuple[bool, float]:
        """检查 API 是否可达（通过 models 端点做连通性探测）。

        NVIDIA NIM 云端 API 没有 /health/ready 端点，
        改用 GET /models 作为轻量级连通性检查。

        Returns:
            元组 (是否成功, 耗时毫秒)
        """
        start = time.perf_counter()
        try:
            def _check():
                with httpx.Client(timeout=self.timeout) as client:
                    resp = client.get(
                        f"{self.base_url}/models",
                        headers=self._headers(),
                    )
                return resp

            resp = self._make_request(_check)
            elapsed = (time.perf_counter() - start) * 1000
            return resp.is_success, elapsed
        except Exception:
            elapsed = (time.perf_counter() - start) * 1000
            return False, elapsed

    # ── 模型列表 ────────────────────────────────────────────────

    def list_models(self) -> list[dict[str, Any]]:
        """GET /v1/models — 获取原始模型列表。
        
        Returns:
            模型信息字典列表
        """
        def _get_models():
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.get(
                    f"{self.base_url}/models",
                    headers=self._headers(),
                )
            resp.raise_for_status()
            return resp.json()
        
        data = self._make_request(_get_models)
        # 响应可能将模型包装在 "data" 键下（OpenAI 风格）
        return data.get("data", data)

    # ── 聊天完成 ────────────────────────────────────────────────

    def chat_completion(
        self,
        model: str,
        messages: list[dict[str, str]],
        max_tokens: int = 512,
        temperature: float = 0.7,
        top_p: float = 0.95,
        extra_body: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """POST /v1/chat/completions — 返回完整的响应 JSON。
        
        Args:
            model: 模型 ID
            messages: 消息列表，每个消息包含 role 和 content
            max_tokens: 最大生成 token 数
            temperature: 温度参数，控制随机性
            top_p: 核采样参数
            extra_body: 额外的请求体参数
            
        Returns:
            API 响应字典
            
        Raises:
            httpx.HTTPStatusError: 非 2xx 状态码时抛出
        """
        body: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "top_p": top_p,
        }
        if extra_body:
            body.update(extra_body)

        def _chat():
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(
                    f"{self.base_url}/chat/completions",
                    headers=self._headers(),
                    json=body,
                )
            resp.raise_for_status()
            return resp.json()
        
        return self._make_request(_chat)  # type: ignore[no-any-return]

    # ── 计时聊天完成 ───────────────────────────────────────────

    def timed_chat(
        self,
        model: str,
        messages: list[dict[str, str]],
        max_tokens: int = 512,
        temperature: float = 0.7,
        top_p: float = 0.95,
        extra_body: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """类似 chat_completion，但同时测量 TTFT 和总延迟。
        
        Args:
            model: 模型 ID
            messages: 消息列表
            max_tokens: 最大生成 token 数
            temperature: 温度参数
            top_p: 核采样参数
            extra_body: 额外的请求体参数
            
        Returns:
            包含内容、用量和计时信息的字典：
            - content: 生成的文本内容
            - usage: token 用量统计
            - timing_ms: 计时信息（TTFT、总时间、首 token 后时间）
        """
        
        def _timed_chat():
            start = time.perf_counter()
            first_chunk_time: Optional[float] = None

            body: dict[str, Any] = {
                "model": model,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "top_p": top_p,
                "stream": True,
            }
            if extra_body:
                body.update(extra_body)

            collected_content: list[str] = []
            usage: dict[str, int] = {}

            with httpx.Client(timeout=self.timeout) as client:
                with client.stream(
                    "POST",
                    f"{self.base_url}/chat/completions",
                    headers=self._headers(),
                    json=body,
                ) as resp:
                    resp.raise_for_status()
                    for line in resp.iter_lines():
                        if not line or line.startswith(":"):
                            continue
                        if line.startswith("data: "):
                            chunk_str = line[6:]
                            if chunk_str.strip() == "[DONE]":
                                break

                            chunk = json.loads(chunk_str)
                            if first_chunk_time is None:
                                first_chunk_time = time.perf_counter()

                            choices = chunk.get("choices") or []
                            first_choice = choices[0] if choices else None
                            delta = first_choice.get("delta", {}) if isinstance(first_choice, dict) else {}
                            content = delta.get("content", "") if isinstance(delta, dict) else ""
                            if content:
                                collected_content.append(content)

                            # 用量信息可能出现在最后一个 chunk 中
                            if "usage" in chunk:
                                usage = chunk["usage"]

            total_elapsed = (time.perf_counter() - start) * 1000
            ttft = (
                (first_chunk_time - start) * 1000
                if first_chunk_time
                else total_elapsed
            )

            return {
                "content": "".join(collected_content),
                "usage": usage,
                "timing_ms": {
                    "ttft": round(ttft, 1),
                    "total": round(total_elapsed, 1),
                    "after_first": round(total_elapsed - ttft, 1),
                },
            }
        
        return self._make_request(_timed_chat)

    # ── 简单完成（非聊天） ──────────────────────────────────────

    def completion(
        self,
        model: str,
        prompt: str,
        max_tokens: int = 512,
    ) -> dict[str, Any]:
        """POST /v1/completions — 用于非聊天模型。
        
        Args:
            model: 模型 ID
            prompt: 提示文本
            max_tokens: 最大生成 token 数
            
        Returns:
            API 响应字典
        """
        body = {
            "model": model,
            "prompt": prompt,
            "max_tokens": max_tokens,
        }
        
        def _completion():
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(
                    f"{self.base_url}/completions",
                    headers=self._headers(),
                    json=body,
                )
            resp.raise_for_status()
            return resp.json()
        
        return self._make_request(_completion)  # type: ignore[no-any-return]
