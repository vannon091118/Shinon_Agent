"""
LIMEN Backend — Async client for the LIMEN API Gateway.

Provides a clean interface for pipeline components to make LLM calls
through LIMEN instead of direct provider calls. LIMEN handles:
  - KeyPool rotation (claim/release)
  - Rate limiting (429 → cooldown → next key)
  - Provider routing (model=auto → best available provider)
  - Health monitoring (error rates, latency tracking)

Usage:
    backend = LIMENBackend(base_url="http://127.0.0.1:8001")
    response = await backend.chat(
        messages=[{"role": "user", "content": "Hello"}],
        model="auto",
        temperature=0.3,
        max_tokens=500,
    )
    # → {"choices": [{"message": {"content": "..."}}], "model": "llama-3.3-70b-versatile", ...}
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class LIMENBackend:
    """Async HTTP client for the LIMEN API Gateway.

    Drops all KeyPool/claim/release logic — LIMEN owns key management.
    Pipeline components just call this instead of direct provider APIs.
    """

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:8001",
        timeout: float = 60.0,
        default_model: str = "auto",
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.default_model = default_model
        self._calls: int = 0
        self._errors: int = 0
        self._total_tokens: int = 0
        self._total_latency_ms: float = 0.0

    @property
    def stats(self) -> Dict[str, Any]:
        return {
            "calls": self._calls,
            "errors": self._errors,
            "total_tokens": self._total_tokens,
            "avg_latency_ms": round(self._total_latency_ms / max(self._calls, 1), 1),
            "base_url": self.base_url,
        }

    async def chat(
        self,
        messages: List[Dict[str, str]],
        *,
        model: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 500,
        response_format: Optional[Dict[str, str]] = None,
        system: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Send a chat completion request through LIMEN.

        Args:
            messages: List of {"role": "user"|"assistant", "content": "..."}
            model: Model ID or "auto" (default)
            temperature: Sampling temperature
            max_tokens: Max completion tokens
            response_format: Optional {"type": "json_object"}
            system: System prompt (added as system message)

        Returns:
            Parsed response dict with keys: choices, model, usage

        Raises:
            RuntimeError: On HTTP error or LIMEN error response
        """
        import time as _time

        t0 = _time.monotonic()

        # Build request payload
        payload_messages: List[Dict[str, str]] = []
        if system:
            payload_messages.append({"role": "system", "content": system})
        payload_messages.extend(messages)

        payload: Dict[str, Any] = {
            "model": model or self.default_model,
            "messages": payload_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if response_format:
            payload["response_format"] = response_format

        url = f"{self.base_url}/v1/chat/completions"

        try:
            import httpx

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    url,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                )

            if response.status_code != 200:
                self._errors += 1
                self._calls += 1
                error_body = response.text[:500]
                raise RuntimeError(
                    f"LIMEN returned {response.status_code}: {error_body}"
                )

            data = response.json()
            self._calls += 1

            # Track tokens
            usage = data.get("usage", {})
            tokens = usage.get("total_tokens", 0)
            self._total_tokens += tokens

            latency = (_time.monotonic() - t0) * 1000
            self._total_latency_ms += latency

            logger.debug(
                "LIMEN chat: model=%s tokens=%d latency=%.0fms",
                data.get("model", "?"), tokens, latency,
            )

            return data

        except httpx.HTTPError as exc:
            self._errors += 1
            self._calls += 1
            raise RuntimeError(f"LIMEN connection failed: {exc}") from exc

    async def health(self) -> Dict[str, Any]:
        """Check LIMEN server health."""
        import httpx

        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{self.base_url}/health")
            return response.json()

    async def models(self) -> List[Dict[str, Any]]:
        """List available models from LIMEN."""
        import httpx

        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{self.base_url}/v1/models")
            data = response.json()
            return data.get("data", [])

    async def keys(self) -> Dict[str, Any]:
        """Get key health status from LIMEN dashboard endpoint."""
        import httpx

        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{self.base_url}/v1/dashboard/keys")
            return response.json()
