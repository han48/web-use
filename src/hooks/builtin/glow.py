from __future__ import annotations
from typing import TYPE_CHECKING

from src.hooks.base import BaseHook

if TYPE_CHECKING:
    from src.agent.browser import Browser
    from src.agent.views import AgentResult

_GLOW_JS = (
    "(function(){"
    "function _wu_inject(){"
    "if(document.getElementById('__wu_glow__'))return;"
    "var el=document.createElement('div');"
    "el.id='__wu_glow__';"
    "el.style.cssText='position:fixed;top:0;left:0;width:100%;height:100%;"
    "pointer-events:none;z-index:2147483647;"
    "box-shadow:inset 0 0 30px 2px rgba(30,110,255,0.25);';"
    "(document.body||document.documentElement).appendChild(el);"
    "}"
    "if(document.body){_wu_inject();}"
    "else{document.addEventListener('DOMContentLoaded',_wu_inject);}"
    "})()"
)

_REMOVE_GLOW_JS = (
    "(function(){var el=document.getElementById('__wu_glow__');if(el)el.remove();})()"
)


class GlowHook(BaseHook):
    """Shows a blue viewport glow while the agent is working and removes it when done."""

    async def on_agent_start(self, task: str, browser: 'Browser') -> None:
        await browser.show_glow()

    async def on_agent_done(self, result: 'AgentResult', browser: 'Browser') -> None:
        await browser.hide_glow()

    async def on_agent_error(self, error: str, step: int, browser: 'Browser') -> None:
        await browser.hide_glow()

    async def on_navigate(self, url: str, browser: 'Browser') -> None:
        if browser._glow_active:
            try:
                await browser.execute_script(_GLOW_JS)
            except Exception:
                pass

    async def on_new_tab(self, url: str, browser: 'Browser') -> None:
        if browser._glow_active:
            try:
                await browser.execute_script(_GLOW_JS)
            except Exception:
                pass
