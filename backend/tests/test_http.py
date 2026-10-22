import httpx2
import pytest

from syncsight.ingestion import http


def _client(statuses: list[int]) -> tuple[httpx2.Client, list[int]]:
    calls: list[int] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        calls.append(1)
        return httpx2.Response(statuses[len(calls) - 1], text="ok")

    return httpx2.Client(transport=httpx2.MockTransport(handler)), calls


def test_retries_transient_errors_with_backoff() -> None:
    client, calls = _client([503, 429, 200])
    waits: list[float] = []

    response = http.request(client, "GET", "https://example.test", sleep=waits.append)

    assert response.status_code == 200
    assert len(calls) == 3
    assert waits == [2.0, 4.0]


def test_gives_up_after_last_attempt() -> None:
    client, calls = _client([500, 500])

    with pytest.raises(httpx2.HTTPStatusError):
        http.request(client, "GET", "https://example.test", attempts=2, sleep=lambda _: None)
    assert len(calls) == 2


def test_does_not_retry_client_errors() -> None:
    client, calls = _client([404])

    with pytest.raises(httpx2.HTTPStatusError):
        http.request(client, "GET", "https://example.test", sleep=lambda _: None)
    assert len(calls) == 1
