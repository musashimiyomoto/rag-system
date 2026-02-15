import json
from typing import Any, Iterator

import httpx

from ui.exceptions import ApiClientError
from ui.models import ApiResult
from ui.stream_parser import parse_stream_lines


class ApiClient:
    def __init__(self, base_url: str, timeout: float = 30.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _request(self, method: str, path: str, **kwargs: Any) -> ApiResult:
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

    def liveness(self) -> ApiResult:
        return self._request("GET", "/health/liveness")

    def readiness(self) -> ApiResult:
        return self._request("GET", "/health/readiness")

    def create_source(self, filename: str, file_content: bytes) -> ApiResult:
        return self._request(
            "POST",
            "/source",
            files={"file": (filename, file_content)},
        )

    def list_sources(self) -> ApiResult:
        return self._request("GET", "/source/list")

    def get_source(self, source_id: int) -> ApiResult:
        return self._request("GET", f"/source/{source_id}")

    def delete_source(self, source_id: int) -> ApiResult:
        return self._request("DELETE", f"/source/{source_id}")

    def create_session(self, source_ids: list[int]) -> ApiResult:
        return self._request("POST", "/session", json={"source_ids": source_ids})

    def list_sessions(self) -> ApiResult:
        return self._request("GET", "/session/list")

    def update_session(self, session_id: int, source_ids: list[int]) -> ApiResult:
        return self._request(
            "PATCH", f"/session/{session_id}", json={"source_ids": source_ids}
        )

    def list_messages(self, session_id: int) -> ApiResult:
        return self._request("GET", f"/session/{session_id}/message/list")

    def delete_session(self, session_id: int) -> ApiResult:
        return self._request("DELETE", f"/session/{session_id}")

    def create_provider(self, name: str, api_key: str) -> ApiResult:
        payload = {"name": name, "api_key": api_key}
        return self._request("POST", "/provider", json=payload)

    def list_providers(self) -> ApiResult:
        return self._request("GET", "/provider/list")

    def update_provider(
        self, provider_id: int, api_key: str | None, is_active: bool | None
    ) -> ApiResult:
        payload: dict[str, Any] = {}
        if api_key:
            payload["api_key"] = api_key
        if is_active is not None:
            payload["is_active"] = is_active
        return self._request("PATCH", f"/provider/{provider_id}", json=payload)

    def delete_provider(self, provider_id: int) -> ApiResult:
        return self._request("DELETE", f"/provider/{provider_id}")

    def provider_models(self, provider_id: int) -> ApiResult:
        return self._request("GET", f"/provider/{provider_id}/models")

    def list_tools(self) -> ApiResult:
        return self._request("GET", "/tool/list")

    def stream_chat(
        self,
        session_id: int,
        message: str,
        provider_id: int,
        model_name: str,
        tool_ids: list[str],
    ) -> Iterator[dict[str, Any]]:
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

                yield from parse_stream_lines(response.iter_lines())
        except httpx.HTTPError as exc:
            raise ApiClientError(0, str(exc)) from exc
