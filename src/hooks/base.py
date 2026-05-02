from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.agent.browser import Browser
    from src.agent.views import AgentResult


class BaseHook:
    """Base class for agent and browser lifecycle hooks.

    Subclass and override any methods you care about — unoverridden
    methods are silent no-ops.  Every method receives the browser
    instance so hooks can drive the browser directly.
    """

    # ------------------------------------------------------------------
    # Agent lifecycle
    # ------------------------------------------------------------------

    async def on_agent_start(self, task: str, browser: 'Browser') -> None:
        """Called once before the agent loop begins."""

    async def on_agent_done(self, result: 'AgentResult', browser: 'Browser') -> None:
        """Called when the agent finishes successfully (done_tool fired)."""

    async def on_agent_error(self, error: str, step: int, browser: 'Browser') -> None:
        """Called when the agent aborts due to an unrecoverable error."""

    async def on_thought(self, step: int, thought: str, browser: 'Browser') -> None:
        """Called each time the LLM emits a reasoning thought."""

    async def on_tool_call(self, step: int, tool_name: str, params: dict, browser: 'Browser') -> None:
        """Called just before a tool is executed."""

    async def on_tool_result(self, step: int, tool_name: str, success: bool, content: str, browser: 'Browser') -> None:
        """Called after a tool returns, whether successful or not."""

    # ------------------------------------------------------------------
    # Browser navigation
    # ------------------------------------------------------------------

    async def on_navigate(self, url: str, browser: 'Browser') -> None:
        """Called after any navigation settles (navigate, go_back, go_forward)."""

    async def on_new_tab(self, url: str, browser: 'Browser') -> None:
        """Called when a new browser tab/target is attached."""

    async def on_tab_closed(self, browser: 'Browser') -> None:
        """Called when a browser tab/target is detached."""

    # ------------------------------------------------------------------
    # Browser interactions
    # ------------------------------------------------------------------

    async def on_click(self, x: int, y: int, browser: 'Browser') -> None:
        """Called after the agent performs a click."""

    async def on_type(self, text: str, browser: 'Browser') -> None:
        """Called after the agent types text."""

    async def on_key_press(self, keys: str, browser: 'Browser') -> None:
        """Called after the agent presses a key combination."""

    async def on_scroll(self, direction: str, amount: int, browser: 'Browser') -> None:
        """Called after the agent scrolls."""

    async def on_screenshot(self, data: bytes, browser: 'Browser') -> None:
        """Called each time a screenshot is captured."""
