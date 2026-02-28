import json
from typing import Any, Iterable, Iterator

import httpx

from ui.exceptions import ApiClientError
from ui.models import ApiResult


class ApiClient:
    def __init__(self, base_url: str, timeout: float = 30.0):
        """Initialize API client with base URL and default timeout."""
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _request(self, method: str, path: str, **kwargs: Any) -> ApiResult:
        """Perform a single HTTP request and map response to `ApiResult`."""
        url = f"{self.base_url}{path}"
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.request(method=method, url=url, **kwargs)
        except httpx.HTTPError as exc:
            return ApiResult(ok=False, status_code=0, detail=str(exc))

        payload: Any
        try:
            payload = response.json()
        except ValueError:
            payload = response.text or None

        if response.is_success:
            return ApiResult(ok=True, status_code=response.status_code, data=payload)

        detail = (
            payload.get("detail", "Unknown error")
            if isinstance(payload, dict)
            else str(payload)
        )
        return ApiResult(
            ok=False, status_code=response.status_code, detail=detail, data=payload
        )

    @staticmethod
    def _parse_stream_lines(lines: Iterable[str]) -> Iterator[dict[str, Any]]:
        """Parse newline-delimited JSON chunks from /chat/stream."""
        for line in lines:
            if not line:
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict):
                yield payload

    def liveness(self) -> ApiResult:
        """Check API liveness endpoint."""
        return self._request("GET", "/health/liveness")

    def readiness(self) -> ApiResult:
        """Check API readiness endpoint."""
        return self._request("GET", "/health/readiness")

    def create_source(self, filename: str, file_content: bytes) -> ApiResult:
        """Upload a new source file."""
        return self._request(
            "POST",
            "/source",
            files={"file": (filename, file_content)},
        )

    def list_sources(self) -> ApiResult:
        """Fetch all sources."""
        return self._request("GET", "/source/list")

    def get_source(self, source_id: int) -> ApiResult:
        """Fetch source by ID."""
        return self._request("GET", f"/source/{source_id}")

    def delete_source(self, source_id: int) -> ApiResult:
        """Delete source by ID."""
        return self._request("DELETE", f"/source/{source_id}")

    def create_session(self, source_ids: list[int]) -> ApiResult:
        """Create chat session linked to source IDs."""
        return self._request("POST", "/session", json={"source_ids": source_ids})

    def list_sessions(self) -> ApiResult:
        """Fetch all chat sessions."""
        return self._request("GET", "/session/list")

    def update_session(self, session_id: int, source_ids: list[int]) -> ApiResult:
        """Update source links for an existing session."""
        return self._request(
            "PATCH", f"/session/{session_id}", json={"source_ids": source_ids}
        )

    def list_messages(self, session_id: int) -> ApiResult:
        """Fetch message history for a session."""
        return self._request("GET", f"/session/{session_id}/message/list")

    def delete_session(self, session_id: int) -> ApiResult:
        """Delete a session by ID."""
        return self._request("DELETE", f"/session/{session_id}")

    def create_provider(self, name: str, api_key: str) -> ApiResult:
        """Create provider with credentials."""
        payload = {"name": name, "api_key": api_key}
        return self._request("POST", "/provider", json=payload)

    def list_providers(self) -> ApiResult:
        """Fetch all configured providers."""
        return self._request("GET", "/provider/list")

    def update_provider(
        self, provider_id: int, api_key: str | None, is_active: bool | None
    ) -> ApiResult:
        """Update provider credentials or activation status."""
        payload: dict[str, Any] = {}
        if api_key:
            payload["api_key"] = api_key
        if is_active is not None:
            payload["is_active"] = is_active
        return self._request("PATCH", f"/provider/{provider_id}", json=payload)

    def delete_provider(self, provider_id: int) -> ApiResult:
        """Delete provider by ID."""
        return self._request("DELETE", f"/provider/{provider_id}")

    def provider_models(self, provider_id: int) -> ApiResult:
        """Fetch available models for a provider."""
        return self._request("GET", f"/provider/{provider_id}/models")

    def list_tools(self) -> ApiResult:
        """Fetch all available tool definitions."""
        return self._request("GET", "/tool/list")

    def stream_chat(
        self,
        session_id: int,
        message: str,
        provider_id: int,
        model_name: str,
        tool_ids: list[str],
    ) -> Iterator[dict[str, Any]]:
        """Send chat prompt and yield streamed JSON chunks."""
        url = f"{self.base_url}/chat/stream"
        payload = {"session_id": session_id, "message": message}
        params: dict[str, Any] = {
            "provider_id": provider_id,
            "model_name": model_name,
        }
        if tool_ids:
            params["tool_ids"] = tool_ids

        try:
            timeout = httpx.Timeout(connect=30.0, write=30.0, read=600.0, pool=30.0)
            with (
                httpx.Client(timeout=timeout) as client,
                client.stream("POST", url, json=payload, params=params) as response,
            ):
                if not response.is_success:
                    raw_content = response.read()
                    try:
                        data = json.loads(raw_content.decode("utf-8"))
                    except (UnicodeDecodeError, json.JSONDecodeError):
                        data = None

                    if isinstance(data, dict):
                        detail = str(data.get("detail", "Unknown error"))
                    else:
                        detail = raw_content.decode("utf-8", errors="ignore")
                        if not detail:
                            detail = "Unknown error"
                    raise ApiClientError(response.status_code, detail)

                yield from self._parse_stream_lines(lines=response.iter_lines())
        except httpx.HTTPError as exc:
            raise ApiClientError(0, str(exc)) from exc
