from __future__ import annotations
from abc import ABC, abstractmethod
from datetime import datetime
import os
from pathlib import Path
from src.agent.events.views import AgentEvent, EventType


def _format_tool_name(tool_name: str) -> str:
    if not tool_name:
        return ""
    if " Tool" in tool_name:
        return tool_name.replace(" Tool", "")
    name = tool_name.removesuffix("_tool") if tool_name.endswith("_tool") else tool_name
    return " ".join(word.capitalize() for word in name.split("_"))


class BaseEventSubscriber(ABC):
    @abstractmethod
    def invoke(self, event: AgentEvent) -> None: ...

    def __call__(self, event: AgentEvent) -> None:
        self.invoke(event)

    def close(self) -> None:
        pass


class ConsoleEventSubscriber(BaseEventSubscriber):
    def invoke(self, event: AgentEvent) -> None:
        match event.type:
            case EventType.REASONING:
                r = event.data.get("reasoning", "")
                if r:
                    print(f"[Agent] 🤔 Reasoning: {r}")
            case EventType.THOUGHT:
                t = event.data.get("thought", "")
                if t:
                    print(f"[Agent] 💭 Thought: {t}")
            case EventType.TOOL_CALL:
                n = _format_tool_name(event.data.get("tool_name", ""))
                p = event.data.get("tool_params", {})
                # Filter out 'thought' from params for display
                filtered_p = {k: v for k, v in p.items() if k != 'thought'}
                params = ", ".join(f"{k}={repr(v)}" for k, v in filtered_p.items())
                print(f"[Agent] 🛠️  Calling: {n}({params})")
            case EventType.TOOL_RESULT:
                n = _format_tool_name(event.data.get("tool_name", ""))
                s = event.data.get("is_success", True)
                c = event.data.get("content", "")
                if not s:
                    print(f"[Agent] ❌ Tool '{n}' failed:")
                    print(f"  └─ Error: {c}")
                else:
                    print(f"[Agent] ✅ Tool result from {n}:")
                    # Truncate very long outputs
                    if isinstance(c, str) and len(c) > 500:
                        print(f"  └─ {c[:500]}...")
                    else:
                        print(f"  └─ {c}")
            case EventType.DONE:
                c = event.data.get("content", "")
                print(f"[Agent] ✨ Final Answer:")
                print(f"  └─ {c}")
            case EventType.ERROR:
                e = event.data.get("error", "")
                print(f"[Agent] 🚨 Error: {e}")


class FileEventSubscriber(BaseEventSubscriber):
    def __init__(self, log_path: Path | None = None) -> None:
        log_dir = "logs"
        os.makedirs(log_dir, exist_ok=True)
        if log_path is None:
            log_path = f"{log_dir}/{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.log"    
        self._log_file = open(log_path, "a", encoding="utf-8")

    def invoke(self, event: AgentEvent) -> None:
        ts = datetime.now().strftime("%H:%M:%S")
        match event.type:
            case EventType.REASONING:
                r = event.data.get("reasoning", "")
                if r:
                    self._write(ts, f"Reasoning: {r}")
            case EventType.THOUGHT:
                t = event.data.get("thought", "")
                if t:
                    self._write(ts, f"Thought: {t}")
            case EventType.TOOL_CALL:
                n = _format_tool_name(event.data.get("tool_name", ""))
                p = event.data.get("tool_params", {})
                filtered_p = {k: v for k, v in p.items() if k != 'thought'}
                params = ", ".join(f"{k}={v}" for k, v in filtered_p.items())
                self._write(ts, f"Tool Call: {n}({params})")
            case EventType.TOOL_RESULT:
                n = _format_tool_name(event.data.get("tool_name", ""))
                s = event.data.get("is_success", True)
                c = event.data.get("content", "")
                status = "Success" if s else "Failed"
                self._write(ts, f"Tool Result [{status}]: {n} -> {c}")
            case EventType.DONE:
                c = event.data.get("content", "")
                self._write(ts, f"Final Answer: {c}")
            case EventType.ERROR:
                e = event.data.get("error", "")
                self._write(ts, f"Error: {e}")

    def _write(self, ts: str, msg: str) -> None:
        self._log_file.write(f"[{ts}] {msg}\n")
        self._log_file.flush()

    def close(self) -> None:
        self._log_file.close()
