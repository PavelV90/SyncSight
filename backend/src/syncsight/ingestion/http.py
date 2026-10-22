"""HTTP client with an identifying User-Agent and retries for transient failures."""

import time
from collections.abc import Callable
from typing import Any

import httpx2

from syncsight import __version__

USER_AGENT = f"SyncSight/{__version__} (+https://github.com/PavelV90/SyncSight)"
RETRY_STATUS = frozenset({429, 500, 502, 503, 504})


def make_client(timeout: float = 120.0) -> httpx2.Client:
    return httpx2.Client(headers={"User-Agent": USER_AGENT}, timeout=timeout, follow_redirects=True)


def request(
    client: httpx2.Client,
    method: str,
    url: str,
    *,
    attempts: int = 4,
    backoff: float = 2.0,
    sleep: Callable[[float], None] = time.sleep,
    **kwargs: Any,
) -> httpx2.Response:
    """Send a request; retry connection errors and 429/5xx with exponential backoff."""
    for attempt in range(1, attempts + 1):
        try:
            response = client.request(method, url, **kwargs)
        except httpx2.TransportError:
            if attempt == attempts:
                raise
        else:
            if response.status_code not in RETRY_STATUS or attempt == attempts:
                response.raise_for_status()
                return response
        sleep(backoff * 2 ** (attempt - 1))
    raise AssertionError("unreachable")
