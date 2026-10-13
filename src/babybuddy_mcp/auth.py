import time
from urllib.parse import parse_qs

import httpx
from fastmcp.server.auth import AccessToken, TokenVerifier
from starlette.middleware import Middleware
from starlette.types import ASGIApp, Receive, Scope, Send

from .client import get_client

VERIFIED_TOKEN_TTL_SECONDS = 60.0
QUERY_TOKEN_PARAM = "token"


class QueryTokenMiddleware:
    """For clients that can't set headers: treats ?token=<key> as `Authorization: Bearer <key>`."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http":
            headers = scope["headers"]
            if not any(name.lower() == b"authorization" for name, _ in headers):
                tokens = parse_qs(scope.get("query_string", b"").decode()).get(QUERY_TOKEN_PARAM)
                if tokens:
                    scope = {**scope, "headers": [*headers, (b"authorization", f"Bearer {tokens[0]}".encode())]}
        await self.app(scope, receive, send)


class BabyBuddyTokenVerifier(TokenVerifier):
    """Accepts a bearer token only if Baby Buddy accepts it as an API key."""

    def __init__(self) -> None:
        super().__init__()
        self._verified: dict[str, tuple[float, AccessToken]] = {}

    def get_middleware(self) -> list[Middleware]:
        return [Middleware(QueryTokenMiddleware), *super().get_middleware()]

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
