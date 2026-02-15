import json
from typing import Any, Iterable, Iterator


def parse_stream_lines(lines: Iterable[str]) -> Iterator[dict[str, Any]]:
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
