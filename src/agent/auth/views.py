import time
from dataclasses import dataclass, field


@dataclass
class OAuthConfig:
    client_id: str
    auth_url: str
    token_url: str
    scopes: list[str]
    redirect_uri: str = 'http://localhost:8765/callback'
    client_secret: str | None = None  # Not required when using PKCE


@dataclass
class TokenResponse:
    access_token: str
    token_type: str = 'Bearer'
    expires_in: int | None = None
    refresh_token: str | None = None
    scope: str | None = None
    obtained_at: float = field(default_factory=time.time)

    def is_expired(self, buffer_secs: int = 60) -> bool:
        if not self.expires_in:
            return False
        return time.time() > self.obtained_at + self.expires_in - buffer_secs
