"""Lifespan-managed httpx transport for LIMEN providers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import httpx

from limen import __version__

if TYPE_CHECKING:
    from limen.config import LimenConfig


@dataclass(frozen=True)
class TimeoutConfig:
    """Provider-call timeout bundle in seconds."""

    connect: float = 5.0
    write: float = 30.0
    read: float = 120.0
    pool: float = 5.0


class HttpTransport:
    """Own one httpx AsyncClient shared by all provider adapters."""

    def __init__(self, config: LimenConfig) -> None:
        self._client: httpx.AsyncClient | None = None
        self._timeouts = TimeoutConfig(
            connect=float(config.raw.get("timeouts", {}).get("connect_seconds", 5)),
            write=float(config.raw.get("timeouts", {}).get("write_seconds", 30)),
            read=float(config.raw.get("timeouts", {}).get("read_seconds", 120)),
            pool=float(config.raw.get("timeouts", {}).get("pool_seconds", 5)),
        )

    @property
    def client(self) -> httpx.AsyncClient:
        """Return the open AsyncClient or fail explicitly."""
        if self._client is None:
            raise RuntimeError("HttpTransport is not open")
        return self._client

    async def open(self) -> None:
        """Create the AsyncClient."""
        if self._client is not None:
            return
        timeout = httpx.Timeout(
            connect=self._timeouts.connect,
            read=self._timeouts.read,
            write=self._timeouts.write,
            pool=self._timeouts.pool,
        )
        self._client = httpx.AsyncClient(
            timeout=timeout,
            headers={"user-agent": f"limen/{__version__}"},
        )

    async def close(self) -> None:
        """Close the AsyncClient."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def request(
        self,
        method: str,
        url: str,
        *,
        json: object | None = None,
        headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        """Issue a request and return the raw response.

        Errors are surfaced as exceptions by httpx; discrimination between
        transport and HTTP failures happens in the adapter layer.
        """
        return await self.client.request(method, url, json=json, headers=headers)
