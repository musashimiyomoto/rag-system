from dataclasses import dataclass
from typing import Any


@dataclass
class ApiResult:
    """Result wrapper returned by UI API client calls."""

    ok: bool
    status_code: int
    data: Any | None = None
    detail: str | None = None
