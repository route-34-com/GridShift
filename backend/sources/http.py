"""Small HTTP helper with timeouts and retries."""

import time

import httpx


class SourceError(RuntimeError):
    """Raised when an external data source cannot be reached or parsed."""


def get_json(url: str, params: dict, client: httpx.Client | None = None, retries: int = 3) -> object:
    """Fetch JSON from a URL, retrying transient failures."""
    owned = client is None
    client = client or httpx.Client(timeout=30)
    last: Exception | None = None
    try:
        for attempt in range(retries):
            try:
                response = client.get(url, params=params)
                if response.status_code == 404:
                    raise SourceError(f"{url} returned 404")
                response.raise_for_status()
                return response.json()
            except SourceError:
                raise
            except (httpx.HTTPError, ValueError) as exc:
                last = exc
                if attempt < retries - 1:
                    time.sleep(0.5 * 2**attempt)
        raise SourceError(f"{url} failed after {retries} attempts: {last}")
    finally:
        if owned:
            client.close()
