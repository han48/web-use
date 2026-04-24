from src.messages import SystemMessage, HumanMessage, ImageMessage
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING
import platform
import io

try:
    from PIL import Image as _PILImage
except ImportError:
    _PILImage = None

if TYPE_CHECKING:
    from src.agent.browser import Browser

_template_cache: dict[str, str] = {}

def _load_template(filename: str) -> str:
    if filename not in _template_cache:
        _template_cache[filename] = Path(f'./src/agent/context/prompt/{filename}').read_text(encoding='utf-8')
    return _template_cache[filename]


class Context:
    """Builds prompt messages (system, state, task) for the agent loop."""

    def __init__(self, session: 'Browser'):
        self.session = session

    def system(self, instructions: list[str] = [], max_steps: int = 25) -> SystemMessage:
        browser = self.session
        template = _load_template('system.md')
        content = template.format(**{
            'datetime':      datetime.now().strftime('%A, %B %d, %Y'),
            'os':            platform.system(),
            'browser':       browser.config.resolved_browser().capitalize(),
            'home_dir':      Path.home().as_posix(),
            'downloads_dir': browser.config.downloads_dir,
            'max_steps':     max_steps,
            'instructions':  '\n'.join(f'{i+1}. {ins}' for i, ins in enumerate(instructions)) if instructions else '',
        })
        return SystemMessage(content=content)

    async def state(self, query: str, step: int, max_steps: int,
                    tool_result: str = 'No previous action.',
                    use_vision: bool = False,
                    nudge: str = '') -> HumanMessage | ImageMessage:
        browser_state = await self.session.get_state(use_vision=use_vision)

        try:
            pos = await self.session.get_scroll_position()
            scroll_y  = pos.get('scrollY', 0)
            max_scroll = pos.get('scrollHeight', 0) - pos.get('innerHeight', 0)
        except Exception:
            scroll_y = max_scroll = 0

        THRESHOLD = 10
        pct = round(scroll_y / max_scroll * 100) if max_scroll > THRESHOLD else 0
        if max_scroll <= THRESHOLD:
            scroll_top = scroll_bottom = ''
        elif scroll_y <= THRESHOLD:
            scroll_top    = 'Top of page\n\n'
            scroll_bottom = '\n\n↓ Scroll down to see more content'
        elif scroll_y >= max_scroll - THRESHOLD:
            scroll_top    = f'↑ Scroll up to see previous content — {pct}% scrolled\n\n'
            scroll_bottom = '\n\nReached the bottom of the page'
        else:
            scroll_top    = f'↑ Scroll up to see previous content — {pct}% scrolled\n\n'
            scroll_bottom = '\n\n↓ Scroll down to see more content'

        template = _load_template('state.md')
        content = template.format(**{
            'step':           step,
            'max_steps':      max_steps,
            'current_tab':    browser_state.current_tab.to_string() if browser_state.current_tab else 'None',
            'tabs':           browser_state.tabs_to_string(),
            'scroll_top':     scroll_top,
            'page_structure': browser_state.dom_state.semantic_tree_to_string(),
            'scroll_bottom':  scroll_bottom,
            'tool_result':    tool_result,
            'query':          query,
        })
        if nudge:
            content += f'\n\n⚠️ LOOP DETECTED:\n{nudge}'
        if use_vision and browser_state.screenshot and _PILImage:
            img = _PILImage.open(io.BytesIO(browser_state.screenshot))
            return ImageMessage(content=content, images=[img])
        return HumanMessage(content=content)

    def task(self, task: str) -> HumanMessage:
        return HumanMessage(content=f'TASK: {task}')
