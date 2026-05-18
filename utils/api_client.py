"""OpenAI-compatible API client for NVIDIA NIM."""

import time
import asyncio
from typing import Any, Optional
from collections import deque
from threading import Lock

import httpx

from config import settings


class RateLimiter:
    """Rate limiter to avoid hitting API rate limits.
    
    NVIDIA NIM API limits: 40 requests per minute.
    This limiter uses a sliding window algorithm to track requests.
    """
    
    def __init__(self, max_requests: int = 38, window_seconds: float = 60.0):
        """Initialize rate limiter.
        
        Args:
            max_requests: Maximum requests allowed in the window (set to 38 to leave buffer)
            window_seconds: Time window in seconds (60 seconds = 1 minute)
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: deque = deque()
        self.lock = Lock()
    
    def _cleanup_old_requests(self, current_time: float):
        """Remove requests outside the current window."""
        cutoff = current_time - self.window_seconds
        while self.requests and self.requests[0] < cutoff:
            self.requests.popleft()
    
    def can_make_request(self) -> bool:
        """Check if we can make a request without hitting the rate limit."""
        with self.lock:
            current_time = time.time()
            self._cleanup_old_requests(current_time)
            return len(self.requests) < self.max_requests
    
    def wait_for_slot(self, timeout: float = 120.0) -> bool:
        """Wait until we can make a request.
        
        Args:
            timeout: Maximum time to wait in seconds
            
        Returns:
            True if slot available, False if timeout
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            if self.can_make_request():
                return True
            time.sleep(0.5)  # Wait half a second before checking again
        return False
    
    def record_request(self):
        """Record that a request was made."""
        with self.lock:
            self.requests.append(time.time())


class NIMClient:
    """Thin, stateless HTTP client for the NVIDIA NIM API."""

    # Shared rate limiter across all client instances
    _rate_limiter = RateLimiter(max_requests=38, window_seconds=60.0)

    def __init__(self) -> None:
        self.base_url = settings.NVIDIA_API_BASE.rstrip("/")
        self.timeout = settings.REQUEST_TIMEOUT
        self.max_retries = settings.MAX_RETRIES
        self.retry_delay = settings.RETRY_DELAY

    def _headers(self) -> dict[str, str]:
        return settings.headers

    def _make_request(self, func, *args, **kwargs):
        """Make an API request with rate limiting and retry logic.
        
        Args:
            func: The HTTP request function to call
            *args, **kwargs: Arguments to pass to the function
            
        Returns:
            Response from the API
            
        Raises:
            Exception: If all retries fail
        """
        last_error = None
        
        for attempt in range(self.max_retries + 1):
            try:
                # Wait for rate limit slot
                if not self._rate_limiter.wait_for_slot(timeout=120.0):
                    raise Exception("Rate limit timeout - could not get a slot")
                
                # Record this request
                self._rate_limiter.record_request()
                
                # Make the actual request
                return func(*args, **kwargs)
                
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:
                    # Rate limited - wait and retry
                    wait_time = self.retry_delay * (2 ** attempt)  # Exponential backoff
                    print(f"    ⚠️  Rate limited (429), retrying in {wait_time:.1f}s (attempt {attempt + 1}/{self.max_retries})")
                    time.sleep(wait_time)
                    last_error = e
                else:
                    # Other HTTP errors - don't retry
                    raise
            except Exception as e:
                last_error = e
                if attempt < self.max_retries:
                    wait_time = self.retry_delay * (2 ** attempt)
                    print(f"    ⚠️  Request failed, retrying in {wait_time:.1f}s: {str(e)[:50]}")
                    time.sleep(wait_time)
                else:
                    raise
        
        raise last_error

    # ── Health ──────────────────────────────────────────────────

    def health_check(self) -> tuple[bool, float]:
        """Check if the API is reachable. Returns (ok, elapsed_ms)."""
        start = time.perf_counter()
        try:
            def _check():
                with httpx.Client(timeout=self.timeout) as client:
                    resp = client.get(
                        f"{self.base_url}/health/ready",
                        headers=self._headers(),
                    )
                return resp
            
            resp = self._make_request(_check)
            elapsed = (time.perf_counter() - start) * 1000
            return resp.is_success, elapsed
        except Exception:
            elapsed = (time.perf_counter() - start) * 1000
            return False, elapsed

    # ── Models list ─────────────────────────────────────────────

    def list_models(self) -> list[dict[str, Any]]:
        """GET /v1/models — returns the raw model list."""
        def _get_models():
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.get(
                    f"{self.base_url}/models",
                    headers=self._headers(),
                )
            resp.raise_for_status()
            return resp.json()
        
        data = self._make_request(_get_models)
        # The response may wrap models under a "data" key (OpenAI-style)
        return data.get("data", data)

    # ── Chat completion ─────────────────────────────────────────

    def chat_completion(
        self,
        model: str,
        messages: list[dict[str, str]],
        max_tokens: int = 512,
        temperature: float = 0.7,
        top_p: float = 0.95,
        extra_body: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """POST /v1/chat/completions — returns the full response JSON.

        Raises httpx.HTTPStatusError on non-2xx.
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

    # ── Timed chat completion ───────────────────────────────────

    def timed_chat(
        self,
        model: str,
        messages: list[dict[str, str]],
        max_tokens: int = 512,
        temperature: float = 0.7,
        top_p: float = 0.95,
        extra_body: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Like chat_completion but also measures TTFT and total latency."""
        
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
                            import json

                            chunk = json.loads(chunk_str)
                            if first_chunk_time is None:
                                first_chunk_time = time.perf_counter()

                            delta = chunk.get("choices", [{}])[0].get("delta", {})
                            content = delta.get("content", "")
                            if content:
                                collected_content.append(content)

                            # Usage may appear in the last chunk
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

    # ── Simple completion (non-chat) ────────────────────────────

    def completion(
        self,
        model: str,
        prompt: str,
        max_tokens: int = 512,
    ) -> dict[str, Any]:
        """POST /v1/completions — for non-chat models."""
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
