from __future__ import annotations

import httpx
from fastmcp.exceptions import ToolError
from fastmcp.server.dependencies import get_access_token

from .config import settings

_client: httpx.AsyncClient | None = None

QueryParams = dict[str, str | int | float | bool | None]

__all__ = [
    "api_delete",
    "api_get",
    "api_get_raw",
    "api_list",
    "api_patch",
    "api_patch_action",
    "api_patch_multipart",
    "api_post",
    "api_post_multipart",
    "QueryParams",
]


def get_client() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(
            base_url=settings.babybuddy_url.rstrip("/"),
            timeout=settings.request_timeout,
        )
    return _client


def auth_headers() -> dict[str, str]:
    """Baby Buddy auth for the current caller: their verified bearer token, else BABYBUDDY_TOKEN."""
    access_token = get_access_token()
    token = access_token.token if access_token else settings.babybuddy_token
    if not token:
        raise ToolError("No Baby Buddy API token: send it as a bearer token or set BABYBUDDY_TOKEN.")
    return {"Authorization": f"Token {token}"}


async def api_get(path: str, params: QueryParams | None = None) -> dict[str, object]:
    client = get_client()
    response = await client.get(f"/api/{path}/", params=params, headers=auth_headers())
    response.raise_for_status()
    result = response.json()
    assert isinstance(result, dict)
    return result


async def api_get_raw(path: str, params: QueryParams | None = None) -> dict[str, object]:
    """GET a path without appending a trailing slash (e.g. /api/profile)."""
    client = get_client()
    response = await client.get(f"/api/{path}", params=params, headers=auth_headers())
    response.raise_for_status()
    result = response.json()
    assert isinstance(result, dict)
    return result


async def api_list(
    path: str,
    params: QueryParams | None = None,
) -> list[dict[str, object]]:
    """GET a list endpoint, optionally following DRF pagination.
    
    Only follows pagination if no explicit limit is provided in params.
    This prevents infinite loops when the API ignores the limit parameter.
    """
    client = get_client()
    headers = auth_headers()
    all_results: list[dict[str, object]] = []
    url = f"/api/{path}/"
    query: QueryParams = dict(params or {})
    
    # Check if user explicitly provided a limit
    has_limit = "limit" in query

    while url:
        response = await client.get(url, params=query, headers=headers)
        response.raise_for_status()
        data = response.json()
        results = data.get("results", [])
        all_results.extend(results)
        
        # Stop if user provided a limit - they asked for specific number of results
        if has_limit:
            break
            
        # After the first request params are encoded in the next URL
        query = {}
        url = data.get("next") or ""

    return all_results


async def api_post(path: str, data: dict[str, object]) -> dict[str, object]:
    client = get_client()
    response = await client.post(f"/api/{path}/", json=data, headers=auth_headers())
    response.raise_for_status()
    result = response.json()
    assert isinstance(result, dict)
    return result


async def api_patch(
    path: str, record_id: int | str, data: dict[str, object]
) -> dict[str, object]:
    client = get_client()
    response = await client.patch(f"/api/{path}/{record_id}/", json=data, headers=auth_headers())
    response.raise_for_status()
    result = response.json()
    assert isinstance(result, dict)
    return result


async def api_patch_action(
    path: str, record_id: int | str, action: str
) -> dict[str, object]:
    """PATCH a detail sub-route (e.g. /api/timers/{id}/restart/) with an empty body."""
    client = get_client()
    response = await client.patch(f"/api/{path}/{record_id}/{action}/", headers=auth_headers())
    response.raise_for_status()
    result = response.json()
    assert isinstance(result, dict)
    return result


async def api_delete(path: str, record_id: int | str) -> None:
    client = get_client()
    response = await client.delete(f"/api/{path}/{record_id}/", headers=auth_headers())
    response.raise_for_status()


async def api_post_multipart(
    path: str,
    data: dict[str, object],
    files: dict[str, tuple[str, bytes]],
) -> dict[str, object]:
    """POST a multipart/form-data body (JSON fields + file uploads)."""
    client = get_client()
    response = await client.post(f"/api/{path}/", data=data, files=files, headers=auth_headers())
    response.raise_for_status()
    result = response.json()
    assert isinstance(result, dict)
    return result


async def api_patch_multipart(
    path: str,
    record_id: int | str,
    data: dict[str, object],
    files: dict[str, tuple[str, bytes]],
) -> dict[str, object]:
    """PATCH a multipart/form-data body (JSON fields + file uploads)."""
    client = get_client()
    response = await client.patch(
        f"/api/{path}/{record_id}/", data=data, files=files, headers=auth_headers()
    )
    response.raise_for_status()
    result = response.json()
    assert isinstance(result, dict)
    return result
