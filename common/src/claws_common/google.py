"""Google API request helper with automatic retry on stale tokens.

When a cached token is invalidated by Google before its TTL expires,
this module detects the 401, clears the auth server cache, fetches
a fresh token, and retries the request once.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import httpx

from claws_common.client import ClawsClient

AUTH_PORT = 8301


def invalidate_token_cache(subject: str | None = None) -> dict:
    """Clear cached tokens on the auth server."""
    client = ClawsClient(service="google-auth", port=AUTH_PORT)
    params = {"subject": subject} if subject else None
    return client.delete("/cache", params=params)


def google_request(
    method: str,
    url: str,
    token_fn: Callable[[], str],
    *,
    raw: bool = False,
    extra_headers: dict[str, str] | None = None,
    **kwargs: Any,
) -> dict | httpx.Response:
    """Make a Google API request with automatic retry on 401.

    On 401: clears the auth server token cache, calls token_fn() for a
    fresh token, and retries once. A second 401 raises normally.

    Args:
        method: HTTP method (GET, POST, PATCH, DELETE, PUT).
        url: Full Google API URL.
        token_fn: Zero-arg callable that returns a fresh access token.
        raw: If True, return the httpx.Response instead of calling .json().
        extra_headers: Additional headers merged with the auth header.
        **kwargs: Passed to httpx.request (params, json, timeout, etc.).
    """
    token = token_fn()
    kwargs.setdefault("timeout", 30.0)

    for attempt in range(2):
        headers = {"Authorization": f"Bearer {token}"}
        if extra_headers:
            headers.update(extra_headers)
        resp = httpx.request(method, url, headers=headers, **kwargs)

        if resp.status_code == 401 and attempt == 0:
            invalidate_token_cache()
            token = token_fn()
            continue

        resp.raise_for_status()
        return resp if raw else resp.json()

    # Unreachable, but satisfies type checker
    raise httpx.HTTPStatusError(  # pragma: no cover
        "Unexpected retry exhaustion", request=resp.request, response=resp
    )
