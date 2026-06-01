from __future__ import annotations
import json
from datetime import datetime
from pathlib import Path
from typing import Any
from src.agent.events.views import AgentEvent


class JSONEventSubscriber:
    """Write AgentEvent objects to a JSON file as a list of events.

    Each event is appended as a JSON object with fields: ts, type, data.
    The file is created if missing. Writes are flushed immediately.
    """

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        # Ensure file exists and is a valid JSON array
        if not self.path.exists() or self.path.stat().st_size == 0:
            self.path.write_text('[]', encoding='utf-8')

    def _read_events(self) -> list[dict[str, Any]]:
        try:
            return json.loads(self.path.read_text(encoding='utf-8') or '[]')
        except Exception:
            return []

    def invoke(self, event: AgentEvent) -> None:
        ev = {
            'ts': datetime.utcnow().isoformat() + 'Z',
            'type': event.type.name if hasattr(event.type, 'name') else str(event.type),
            'data': event.data,
        }
        events = self._read_events()
        events.append(ev)
        # Write back atomically
        tmp = self.path.with_suffix('.tmp')
        tmp.write_text(json.dumps(events, ensure_ascii=False, indent=2), encoding='utf-8')
        tmp.replace(self.path)

    def __call__(self, event: AgentEvent) -> None:
        self.invoke(event)

    def close(self) -> None:
        pass
