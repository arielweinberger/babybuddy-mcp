import time

import httpx
from fastmcp.server.auth import AccessToken, TokenVerifier

from .client import get_client

VERIFIED_TOKEN_TTL_SECONDS = 60.0


class BabyBuddyTokenVerifier(TokenVerifier):
    """Accepts a bearer token only if Baby Buddy accepts it as an API key."""

    def __init__(self) -> None:
        super().__init__()
        self._verified: dict[str, tuple[float, AccessToken]] = {}

    async def verify_token(self, token: str) -> AccessToken | None:
        cached = self._verified.get(token)
        if cached and cached[0] > time.monotonic():
            return cached[1]

        try:
            response = await get_client().get("/api/profile", headers={"Authorization": f"Token {token}"})
        except httpx.HTTPError:
            return None
        if response.status_code != 200:
            self._verified.pop(token, None)
            return None

        user = response.json().get("user") or {}
        access_token = AccessToken(token=token, client_id=str(user.get("username", "babybuddy")), scopes=[])
        self._verified[token] = (time.monotonic() + VERIFIED_TOKEN_TTL_SECONDS, access_token)
        return access_token
