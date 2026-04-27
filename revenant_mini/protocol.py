from __future__ import annotations

import json
import time
import uuid
from typing import Any


def now() -> float:
    return time.time()


def command_id() -> str:
    return f"cmd-{uuid.uuid4().hex[:12]}"


def message(message_type: str, payload: dict[str, Any] | None = None, worker_id: str | None = None) -> dict[str, Any]:
    data: dict[str, Any] = {
        "type": message_type,
        "timestamp": now(),
        "payload": payload or {},
    }
    if worker_id:
        data["worker_id"] = worker_id
    return data


def dumps(data: dict[str, Any]) -> str:
    return json.dumps(data, separators=(",", ":"), sort_keys=True)


def loads(raw: bytes | str) -> dict[str, Any]:
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8", errors="replace")
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("message is not a JSON object")
    return data
