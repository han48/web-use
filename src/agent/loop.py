from __future__ import annotations

import hashlib
import json
from collections import Counter, deque

_EXEMPT = {'done_tool', 'wait_tool'}
_IGNORE_PARAMS = {'thought'}

_REPEAT_NUDGES = {
    3: 'You have repeated the same action {n} times — make sure it is actually making progress.',
    5: 'Same action repeated {n} times. If you are stuck, try a different approach.',
    8: 'Same action repeated {n} times. Stop and take a completely different strategy.',
}


class LoopGuard:
    """Watches for two signs that the agent is looping:

    - **Action repetition**: the same tool + params appearing too often
      in the last `window` steps.
    - **Page stagnation**: the page DOM and URL not changing across
      consecutive steps, meaning actions have no visible effect.

    Call ``check()`` before each LLM step to get a warning string (or
    None), ``record_action()`` after executing a tool, and
    ``record_page()`` after capturing browser state.
    """

    def __init__(self, window: int = 15) -> None:
        self._hashes: deque[str] = deque(maxlen=window)
        self._last_page: tuple[str, str] | None = None  # (url, content_hash)
        self._stagnant = 0

    def record_action(self, tool: str, params: dict) -> None:
        if tool in _EXEMPT:
            return
        filtered = {k: v for k, v in params.items() if k not in _IGNORE_PARAMS}
        normalised = {
            k: v.strip().lower() if isinstance(v, str) else v
            for k, v in filtered.items()
        }
        raw = json.dumps({tool: normalised}, sort_keys=True).encode()
        self._hashes.append(hashlib.sha256(raw).hexdigest()[:12])

    def record_page(self, url: str, dom_text: str) -> None:
        digest = hashlib.sha256(dom_text.encode('utf-8', errors='replace')).hexdigest()[:16]
        page = (url, digest)
        if page == self._last_page:
            self._stagnant += 1
        else:
            self._stagnant = 0
        self._last_page = page

    def check(self) -> str | None:
        warnings: list[str] = []

        if self._hashes:
            top = Counter(self._hashes).most_common(1)[0][1]
            for threshold in sorted(_REPEAT_NUDGES, reverse=True):
                if top >= threshold:
                    warnings.append(_REPEAT_NUDGES[threshold].format(n=top))
                    break

        if self._stagnant >= 4:
            warnings.append(
                f'The page has not changed for {self._stagnant} steps. '
                'Your actions may not be having any effect. '
                'If waiting for something external (OTP, email, slow load) '
                'use wait_tool first, then re-check.'
            )

        return '\n\n'.join(warnings) or None

    def reset(self) -> None:
        self._hashes.clear()
        self._last_page = None
        self._stagnant = 0
