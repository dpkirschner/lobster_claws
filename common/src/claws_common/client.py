"""HTTP client wrapper for skill-to-server communication."""

import httpx

from claws_common.host import resolve_host


class ClawsClient:
    """HTTP client for skill-to-server communication.

    Wraps httpx with service-aware error messages and configurable timeouts.
    """

    def __init__(self, service: str, port: int, timeout: float = 30.0):
        self.service = service
        self.port = port
        host = resolve_host()
        self.base_url = f"http://{host}:{port}"
        self.timeout = timeout

    def get(self, path: str, params: dict | None = None) -> dict:
        """GET request with error handling."""
        url = f"{self.base_url}{path}"
        try:
            resp = httpx.get(url, params=params, timeout=self.timeout)
            resp.raise_for_status()
            return resp.json()
        except httpx.ConnectError:
            raise ConnectionError(
                f"Cannot connect to {self.service} server at {url}. "
                f"Is the server running? Check: curl {self.base_url}/health"
            )
        except httpx.TimeoutException:
            raise TimeoutError(
                f"Request to {self.service} timed out after {self.timeout}s ({url})"
            )

    def post_json(self, path: str, data: dict) -> dict:
        """POST JSON data with error handling."""
        url = f"{self.base_url}{path}"
        try:
            resp = httpx.post(url, json=data, timeout=self.timeout)
            resp.raise_for_status()
            return resp.json()
        except httpx.ConnectError:
            raise ConnectionError(
                f"Cannot connect to {self.service} server at {url}. "
                f"Is the server running? Check: curl {self.base_url}/health"
            )
        except httpx.TimeoutException:
            raise TimeoutError(
                f"Request to {self.service} timed out after {self.timeout}s ({url})"
            )

    def post_file(self, path: str, file_path: str, **params) -> dict:
        """POST a file with multipart upload."""
        url = f"{self.base_url}{path}"
        try:
            with open(file_path, "rb") as f:
                resp = httpx.post(
                    url,
                    files={"file": f},
                    params=params,
                    timeout=self.timeout,
                )
            resp.raise_for_status()
            return resp.json()
        except httpx.ConnectError:
            raise ConnectionError(
                f"Cannot connect to {self.service} server at {url}. "
                f"Is the server running? Check: curl {self.base_url}/health"
            )
        except httpx.TimeoutException:
            raise TimeoutError(
                f"Request to {self.service} timed out after {self.timeout}s ({url})"
            )
