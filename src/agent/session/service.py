from __future__ import annotations

from src.agent.browser import Browser
from src.agent.dom.views import DOMElementNode


class Session:
    """Compatibility wrapper over the browser-owned session model."""

    def __init__(self, browser: Browser):
        self.browser = browser

    async def init_session(self):
        await self.browser.ensure_open()

    async def close_session(self):
        await self.browser.close()

    def __getattr__(self, name):
        return getattr(self.browser, name)

    async def get_element_by_index(self, index: int) -> DOMElementNode:
        browser_state = self.browser._browser_state or await self.browser.get_state()
        selector_map = browser_state.dom_state.selector_map
        if index not in selector_map:
            raise Exception(f'Element at index {index} not found in selector map')
        return selector_map[index]
