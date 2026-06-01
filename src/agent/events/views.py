from dataclasses import dataclass
from enum import Enum
from typing import Any


class EventType(str, Enum):
    THOUGHT = "thought"
    REASONING = "reasoning"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    DONE = "done"
    ERROR = "error"


@dataclass
class AgentEvent:
    type: EventType
    data: dict[str, Any]
