"""Shared HTTP transport used by adapters and dispatch tests."""

from limen.transport.client import HttpTransport, TimeoutConfig

__all__ = ["HttpTransport", "TimeoutConfig"]
