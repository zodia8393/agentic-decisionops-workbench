"""JSONL tracing for DecisionOps runs."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class TraceEvent:
    event_type: str
    task_id: str
    payload: dict[str, Any]
    created_at_utc: str


class TraceRecorder:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def record(self, event_type: str, task_id: str, payload: dict[str, Any]) -> None:
        event = TraceEvent(
            event_type=event_type,
            task_id=task_id,
            payload=payload,
            created_at_utc=datetime.now(timezone.utc).isoformat(),
        )
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(event), ensure_ascii=False) + "\n")
