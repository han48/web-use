from __future__ import annotations
import asyncio
import logging
from typing import TYPE_CHECKING

from src.hooks.base import BaseHook

if TYPE_CHECKING:
    from src.agent.browser import Browser
    from src.agent.views import AgentResult

logger = logging.getLogger(__name__)


class Hook:
    """Dispatches lifecycle events to a list of BaseHook instances.

    All hooks are called in registration order.  Exceptions in any
    individual hook are caught and logged so they never interrupt the
    agent loop.
    """

    def __init__(self, hooks: list[BaseHook] | None = None) -> None:
        self._hooks: list[BaseHook] = list(hooks or [])

    def add(self, hook: BaseHook) -> None:
        self._hooks.append(hook)

    # ------------------------------------------------------------------
    # Agent lifecycle
    # ------------------------------------------------------------------

    async def on_agent_start(self, task: str, browser: 'Browser') -> None:
        await self._run('on_agent_start', task=task, browser=browser)

    async def on_agent_done(self, result: 'AgentResult', browser: 'Browser') -> None:
        await self._run('on_agent_done', result=result, browser=browser)

    async def on_agent_error(self, error: str, step: int, browser: 'Browser') -> None:
        await self._run('on_agent_error', error=error, step=step, browser=browser)

    async def on_thought(self, step: int, thought: str, browser: 'Browser') -> None:
        await self._run('on_thought', step=step, thought=thought, browser=browser)

    async def on_tool_call(self, step: int, tool_name: str, params: dict, browser: 'Browser') -> None:
        await self._run('on_tool_call', step=step, tool_name=tool_name, params=params, browser=browser)

    async def on_tool_result(self, step: int, tool_name: str, success: bool, content: str, browser: 'Browser') -> None:
        await self._run('on_tool_result', step=step, tool_name=tool_name, success=success, content=content, browser=browser)

    # ------------------------------------------------------------------
    # Browser navigation
    # ------------------------------------------------------------------

    async def on_navigate(self, url: str, browser: 'Browser') -> None:
        await self._run('on_navigate', url=url, browser=browser)

    async def on_new_tab(self, url: str, browser: 'Browser') -> None:
        await self._run('on_new_tab', url=url, browser=browser)

    async def on_tab_closed(self, browser: 'Browser') -> None:
        await self._run('on_tab_closed', browser=browser)

    # ------------------------------------------------------------------
    # Browser interactions
    # ------------------------------------------------------------------

    async def on_click(self, x: int, y: int, browser: 'Browser') -> None:
        await self._run('on_click', x=x, y=y, browser=browser)

    async def on_type(self, text: str, browser: 'Browser') -> None:
        await self._run('on_type', text=text, browser=browser)

    async def on_key_press(self, keys: str, browser: 'Browser') -> None:
        await self._run('on_key_press', keys=keys, browser=browser)

    async def on_scroll(self, direction: str, amount: int, browser: 'Browser') -> None:
        await self._run('on_scroll', direction=direction, amount=amount, browser=browser)

    async def on_screenshot(self, data: bytes, browser: 'Browser') -> None:
        await self._run('on_screenshot', data=data, browser=browser)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    async def _run(self, method: str, **kwargs) -> None:
        for hook in self._hooks:
            fn = getattr(hook, method, None)
            if fn is None:
                continue
            try:
                result = fn(**kwargs)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as exc:
                logger.warning('Hook %s.%s raised: %s', type(hook).__name__, method, exc)
