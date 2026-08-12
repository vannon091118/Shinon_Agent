"""Failure classification unit tests for Phase 1."""

from __future__ import annotations

import pytest

from limen.resilience import (
    classify_http_failure,
    encode_failure_payload,
    parse_retry_after,
)
from limen.resilience.classifier import ProviderFailure


@pytest.mark.parametrize(
    ("status", "expected_type"),
    [
        (400, "request_invalid"),
        (401, "key_revoked"),
        (403, "key_revoked"),
        (404, "request_invalid"),
        (408, "provider_unreachable"),
        (413, "request_too_large"),
        (418, "request_invalid"),
        (429, "rate_limited"),
        (500, "provider_unreachable"),
        (502, "provider_unreachable"),
        (503, "provider_unreachable"),
    ],
)
def test_classify_http_failure_maps_status_to_type(
    status: int, expected_type: str,
) -> None:
    failure = classify_http_failure(status, body=b"unused")
    assert failure.failure_type == expected_type
    assert failure.http_code == status


def test_classify_429_parses_retry_after_in_seconds() -> None:
    failure = classify_http_failure(
        429, body=b"too many", headers={"retry-after": "12"}
    )
    assert failure.failure_type == "rate_limited"
    assert failure.retry_after_seconds == 12.0


def test_classify_429_handles_invalid_retry_after() -> None:
    failure = classify_http_failure(
        429, body=b"too many", headers={"retry-after": "soon"}
    )
    assert failure.retry_after_seconds is None


def test_classify_quota_token_recognises_quota_body() -> None:
    failure = classify_http_failure(
        200, body=b'{"error":{"message":"quota exceeded"}}'
    )
    assert failure.failure_type == "key_quota_exhausted"


def test_encode_failure_payload_redacts_body() -> None:
    failure = ProviderFailure(
        failure_type="rate_limited",
        message="slow down",
        http_code=429,
        raw_body="x" * 1024,
    )
    payload = encode_failure_payload(failure)
    assert payload["failure_type"] == "rate_limited"
    assert payload["http_code"] == 429
    assert isinstance(payload["body_preview"], str)
    assert len(payload["body_preview"]) <= 512


def test_parse_retry_after_validates_positive_seconds() -> None:
    assert parse_retry_after("0") is None
    assert parse_retry_after("") is None
    assert parse_retry_after("9.5") == 9.5
