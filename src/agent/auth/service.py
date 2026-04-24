from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import secrets
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import urlencode, urlparse, parse_qsl

import httpx

from src.agent.auth.views import OAuthConfig, TokenResponse

if TYPE_CHECKING:
    from src.agent.browser import Browser

_DEFAULT_TOKEN_DIR = Path.home() / '.web-use' / 'oauth'


class OAuth:
    def __init__(self, browser: 'Browser', token_dir: Path = _DEFAULT_TOKEN_DIR):
        self._browser = browser
        self._token: TokenResponse | None = None
        self._config: OAuthConfig | None = None
        self._token_dir = token_dir

    # ------------------------------------------------------------------ #
    # Public API                                                           #
    # ------------------------------------------------------------------ #

    async def load(self, config: OAuthConfig) -> TokenResponse | None:
        """Load a previously saved token for this client_id.

        Returns the token (refreshing it first if expired) so the caller
        can skip authorize() entirely on subsequent runs.  Returns None if
        no saved token exists.
        """
        token = self._load(config.client_id)
        if token is None:
            return None
        self._token = token
        self._config = config
        if token.is_expired():
            try:
                await self._refresh()
            except Exception:
                self._token = None
                self._delete(config.client_id)
                return None
        await self._inject(self._token)
        return self._token

    async def authorize(self, config: OAuthConfig) -> TokenResponse:
        """Run the full Authorization Code + PKCE flow.

        Navigates the browser to the provider's login page, waits up to
        120 seconds for the user to complete authentication, then exchanges
        the code for tokens and injects the Bearer header into every active
        tab session.
        """
        verifier, challenge = self._pkce()
        state = secrets.token_urlsafe(16)
        port = urlparse(config.redirect_uri).port or 8765

        params = {
            'response_type': 'code',
            'client_id': config.client_id,
            'redirect_uri': config.redirect_uri,
            'scope': ' '.join(config.scopes),
            'state': state,
            'code_challenge': challenge,
            'code_challenge_method': 'S256',
        }
        auth_url = f"{config.auth_url}?{urlencode(params)}"

        code = await self._callback_flow(port, state, auth_url)
        token = await self._exchange(config, code, verifier)
        self._token = token
        self._config = config
        self._save(token, config.client_id)
        await self._inject(token)
        return token

    async def get_token(self) -> str:
        """Return a valid access token, refreshing automatically if expired."""
        if not self._token:
            raise RuntimeError('Not authenticated. Call authorize() first.')
        if self._token.is_expired():
            await self._refresh()
        return self._token.access_token

    async def revoke(self) -> None:
        """Clear stored tokens and remove the Authorization header from all sessions."""
        if self._config:
            self._delete(self._config.client_id)
        self._token = None
        self._config = None
        await self._clear_headers()

    # ------------------------------------------------------------------ #
    # Internal helpers                                                     #
    # ------------------------------------------------------------------ #

    def _pkce(self) -> tuple[str, str]:
        verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).rstrip(b'=').decode()
        digest = hashlib.sha256(verifier.encode()).digest()
        challenge = base64.urlsafe_b64encode(digest).rstrip(b'=').decode()
        return verifier, challenge

    async def _callback_flow(self, port: int, expected_state: str, auth_url: str) -> str:
        """Start a local HTTP server, navigate to auth_url, return the code."""
        loop = asyncio.get_event_loop()
        code_future: asyncio.Future[str] = loop.create_future()

        async def _handle(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
            params: dict[str, str] = {}
            try:
                data = await asyncio.wait_for(reader.read(8192), timeout=10.0)
                first_line = data.decode('utf-8', errors='replace').split('\n')[0]
                # "GET /callback?code=XXX&state=YYY HTTP/1.1"
                parts = first_line.split(' ')
                path = parts[1] if len(parts) > 1 else ''
                params = dict(parse_qsl(urlparse(path).query))

                body = b'<html><body><h2>Authorization successful. You may close this tab.</h2></body></html>'
                response = (
                    b'HTTP/1.1 200 OK\r\n'
                    b'Content-Type: text/html\r\n'
                    + f'Content-Length: {len(body)}\r\n'.encode()
                    + b'Connection: close\r\n\r\n'
                    + body
                )
                writer.write(response)
                await writer.drain()
            except Exception:
                pass
            finally:
                writer.close()

            if code_future.done():
                return
            if params.get('state') == expected_state and 'code' in params:
                code_future.set_result(params['code'])
            elif 'error' in params:
                msg = params.get('error_description') or params['error']
                code_future.set_exception(RuntimeError(f'OAuth error: {msg}'))

        server = await asyncio.start_server(_handle, '127.0.0.1', port)
        await self._browser.navigate(auth_url)
        try:
            return await asyncio.wait_for(code_future, timeout=120.0)
        except asyncio.TimeoutError:
            raise TimeoutError('OAuth authorization timed out. Complete login within 120 seconds.')
        finally:
            server.close()
            await server.wait_closed()

    async def _exchange(self, config: OAuthConfig, code: str, verifier: str) -> TokenResponse:
        data: dict = {
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': config.redirect_uri,
            'client_id': config.client_id,
            'code_verifier': verifier,
        }
        if config.client_secret:
            data['client_secret'] = config.client_secret

        async with httpx.AsyncClient() as client:
            resp = await client.post(config.token_url, data=data, timeout=30.0)
            resp.raise_for_status()
            body = resp.json()

        return TokenResponse(
            access_token=body['access_token'],
            token_type=body.get('token_type', 'Bearer'),
            expires_in=body.get('expires_in'),
            refresh_token=body.get('refresh_token'),
            scope=body.get('scope'),
        )

    async def _refresh(self) -> None:
        if not self._config or not self._token or not self._token.refresh_token:
            raise RuntimeError('No refresh token available. Re-authorize.')

        data: dict = {
            'grant_type': 'refresh_token',
            'refresh_token': self._token.refresh_token,
            'client_id': self._config.client_id,
        }
        if self._config.client_secret:
            data['client_secret'] = self._config.client_secret

        async with httpx.AsyncClient() as client:
            resp = await client.post(self._config.token_url, data=data, timeout=30.0)
            resp.raise_for_status()
            body = resp.json()

        self._token = TokenResponse(
            access_token=body['access_token'],
            token_type=body.get('token_type', 'Bearer'),
            expires_in=body.get('expires_in'),
            refresh_token=body.get('refresh_token') or self._token.refresh_token,
            scope=body.get('scope'),
        )
        self._save(self._token, self._config.client_id)
        await self._inject(self._token)

    def _token_path(self, client_id: str) -> Path:
        safe = ''.join(c if c.isalnum() else '_' for c in client_id)
        return self._token_dir / f'{safe}.json'

    def _save(self, token: TokenResponse, client_id: str) -> None:
        self._token_dir.mkdir(parents=True, exist_ok=True)
        path = self._token_path(client_id)
        path.write_text(json.dumps({
            'access_token':  token.access_token,
            'token_type':    token.token_type,
            'expires_in':    token.expires_in,
            'refresh_token': token.refresh_token,
            'scope':         token.scope,
            'obtained_at':   token.obtained_at,
        }), encoding='utf-8')

    def _load(self, client_id: str) -> TokenResponse | None:
        path = self._token_path(client_id)
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding='utf-8'))
            return TokenResponse(**data)
        except Exception:
            return None

    def _delete(self, client_id: str) -> None:
        try:
            self._token_path(client_id).unlink(missing_ok=True)
        except Exception:
            pass

    async def _inject(self, token: TokenResponse) -> None:
        header = {'Authorization': f'{token.token_type} {token.access_token}'}
        for session_id in self._browser._sessions.values():
            try:
                await self._browser.send(
                    'Network.setExtraHTTPHeaders',
                    {'headers': header},
                    session_id=session_id,
                )
            except Exception:
                pass

    async def _clear_headers(self) -> None:
        for session_id in self._browser._sessions.values():
            try:
                await self._browser.send(
                    'Network.setExtraHTTPHeaders',
                    {'headers': {}},
                    session_id=session_id,
                )
            except Exception:
                pass
