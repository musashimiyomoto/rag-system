import json
from typing import Any, Iterable, Iterator

import httpx

from ui.exceptions import ApiClientError
from ui.models import ApiResult


class ApiClient:
    def __init__(self, base_url: str, timeout: float = 30.0):
        """Initialize the API client.

        Args:
            base_url: Base URL of the backend API.
            timeout: Default timeout in seconds for non-stream requests.

        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _request(self, method: str, path: str, **kwargs: Any) -> ApiResult:
        """Send an HTTP request and map the response to `ApiResult`.

        Args:
            method: HTTP method.
            path: API path relative to the configured base URL.
            **kwargs: Extra arguments forwarded to `httpx.Client.request`.

        Returns:
            API result wrapper with parsed payload or error detail.

        """
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
        """Parse streamed NDJSON lines.

        Args:
            lines: Text lines yielded from the streaming HTTP response.

        Yields:
            Parsed JSON objects for valid dictionary payloads.

        """
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
        """Check API liveness.

        Returns:
            Liveness endpoint response.

        """
        return self._request("GET", "/health/liveness")

    def readiness(self) -> ApiResult:
        """Check API readiness.

        Returns:
            Readiness endpoint response.

        """
        return self._request("GET", "/health/readiness")

    def create_source(self, filename: str, file_content: bytes) -> ApiResult:
        """Upload a source file.

        Args:
            filename: Source filename.
            file_content: Raw file bytes.

        Returns:
            Source creation response.

        """
        return self._request(
            "POST",
            "/source",
            files={"file": (filename, file_content)},
        )

    def introspect_db_source(
        self, source_type: str, credentials: dict[str, Any], schema: str | None = None
    ) -> ApiResult:
        """Introspect available tables and columns for DB source.

        Args:
            source_type: Source type identifier (postgres or clickhouse).
            credentials: Source DB credentials.
            schema: Optional schema/database filter.

        Returns:
            Introspection response.

        """
        payload: dict[str, Any] = {
            "type": source_type,
            "credentials": credentials,
        }
        if schema:
            payload["schema"] = schema

        return self._request("POST", "/source/db/introspect", json=payload)

    def create_db_source(
        self,
        source_type: str,
        credentials: dict[str, Any],
        schema_name: str,
        table_name: str,
        id_field: str,
        search_field: str,
        filter_fields: list[str],
        name: str | None = None,
    ) -> ApiResult:
        """Create a DB-backed source.

        Args:
            source_type: Source type identifier (postgres or clickhouse).
            credentials: Source DB credentials.
            schema_name: Schema or database name.
            table_name: Table name.
            id_field: Stable row ID field.
            search_field: Text field used for vectorization.
            filter_fields: Metadata fields for filtering.
            name: Optional source name.

        Returns:
            Source creation response.

        """
        payload: dict[str, Any] = {
            "type": source_type,
            "credentials": credentials,
            "schema_name": schema_name,
            "table_name": table_name,
            "id_field": id_field,
            "search_field": search_field,
            "filter_fields": filter_fields,
        }
        if name:
            payload["name"] = name

        return self._request("POST", "/source/db", json=payload)

    def list_sources(self) -> ApiResult:
        """Fetch all sources.

        Returns:
            Source list response.

        """
        return self._request("GET", "/source/list")

    def list_source_types(self) -> ApiResult:
        """Fetch supported source types.

        Returns:
            Supported source type list response.

        """
        return self._request("GET", "/source/type/list")

    def get_source(self, source_id: int) -> ApiResult:
        """Fetch a source by ID.

        Args:
            source_id: Source ID.

        Returns:
            Source response.

        """
        return self._request("GET", f"/source/{source_id}")

    def delete_source(self, source_id: int) -> ApiResult:
        """Delete a source by ID.

        Args:
            source_id: Source ID.

        Returns:
            Source deletion response.

        """
        return self._request("DELETE", f"/source/{source_id}")

    def create_session(self, source_ids: list[int]) -> ApiResult:
        """Create a chat session.

        Args:
            source_ids: Source IDs linked to the session.

        Returns:
            Session creation response.

        """
        return self._request("POST", "/session", json={"source_ids": source_ids})

    def list_sessions(self) -> ApiResult:
        """Fetch all chat sessions.

        Returns:
            Session list response.

        """
        return self._request("GET", "/session/list")

    def update_session(self, session_id: int, source_ids: list[int]) -> ApiResult:
        """Update source links for a session.

        Args:
            session_id: Session ID.
            source_ids: New source IDs for the session.

        Returns:
            Session update response.

        """
        return self._request(
            "PATCH", f"/session/{session_id}", json={"source_ids": source_ids}
        )

    def list_messages(self, session_id: int) -> ApiResult:
        """Fetch message history for a session.

        Args:
            session_id: Session ID.

        Returns:
            Message list response.

        """
        return self._request("GET", f"/session/{session_id}/message/list")

    def delete_session(self, session_id: int) -> ApiResult:
        """Delete a session by ID.

        Args:
            session_id: Session ID.

        Returns:
            Session deletion response.

        """
        return self._request("DELETE", f"/session/{session_id}")

    def create_provider(self, name: str, api_key: str) -> ApiResult:
        """Create a provider.

        Args:
            name: Provider name.
            api_key: Provider API key.

        Returns:
            Provider creation response.

        """
        payload = {"name": name, "api_key": api_key}
        return self._request("POST", "/provider", json=payload)

    def list_providers(self) -> ApiResult:
        """Fetch all configured providers.

        Returns:
            Provider list response.

        """
        return self._request("GET", "/provider/list")

    def update_provider(
        self, provider_id: int, api_key: str | None, is_active: bool | None
    ) -> ApiResult:
        """Update provider credentials or status.

        Args:
            provider_id: Provider ID.
            api_key: New API key, if provided.
            is_active: New activation status, if provided.

        Returns:
            Provider update response.

        """
        payload: dict[str, Any] = {}
        if api_key:
            payload["api_key"] = api_key
        if is_active is not None:
            payload["is_active"] = is_active
        return self._request("PATCH", f"/provider/{provider_id}", json=payload)

    def delete_provider(self, provider_id: int) -> ApiResult:
        """Delete a provider by ID.

        Args:
            provider_id: Provider ID.

        Returns:
            Provider deletion response.

        """
        return self._request("DELETE", f"/provider/{provider_id}")

    def provider_models(self, provider_id: int) -> ApiResult:
        """Fetch available models for a provider.

        Args:
            provider_id: Provider ID.

        Returns:
            Provider model list response.

        """
        return self._request("GET", f"/provider/{provider_id}/models")

    def list_tools(self) -> ApiResult:
        """Fetch tool definitions.

        Returns:
            Tool list response.

        """
        return self._request("GET", "/tool/list")

    def stream_chat(
        self,
        session_id: int,
        message: str,
        provider_id: int,
        model_name: str,
        tools: list[dict[str, Any]],
    ) -> Iterator[dict[str, Any]]:
        """Send a chat prompt and stream response chunks.

        Args:
            session_id: Session ID.
            message: User prompt text.
            provider_id: Provider ID.
            model_name: Model name.
            tools: Tools enabled for this request.

        Yields:
            Streamed chat chunks as dictionaries.

        Raises:
            ApiClientError: If request or stream handling fails.

        """
        url = f"{self.base_url}/chat/stream"
        payload = {
            "session_id": session_id,
            "message": message,
            "provider_id": provider_id,
            "model_name": model_name,
            "tools": tools,
        }

        try:
            timeout = httpx.Timeout(connect=30.0, write=30.0, read=600.0, pool=30.0)
            with (
                httpx.Client(timeout=timeout) as client,
                client.stream("POST", url, json=payload) as response,
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
