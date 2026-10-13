import httpx
import pytest
import respx
from fastmcp.exceptions import ToolError
from fastmcp.server.auth import AccessToken

from babybuddy_mcp import client as client_module
from babybuddy_mcp.auth import BabyBuddyTokenVerifier
from babybuddy_mcp.client import (
    api_delete,
    api_get,
    api_get_raw,
    api_list,
    api_patch,
    api_patch_action,
    api_patch_multipart,
    api_post,
    api_post_multipart,
)
from babybuddy_mcp.config import settings

BASE = "http://test-babybuddy"


@pytest.fixture
def mock_api() -> respx.MockRouter:
    with respx.mock(base_url=BASE, assert_all_called=False) as router:
        yield router


async def test_api_get_returns_dict(mock_api: respx.MockRouter) -> None:
    mock_api.get("/api/children/1/").mock(
        return_value=httpx.Response(200, json={"id": 1, "first_name": "Alice"})
    )
    result = await api_get("children/1")
    assert result["id"] == 1
    assert result["first_name"] == "Alice"


async def test_api_get_raises_on_error(mock_api: respx.MockRouter) -> None:
    mock_api.get("/api/children/99/").mock(return_value=httpx.Response(404))
    with pytest.raises(httpx.HTTPStatusError):
        await api_get("children/99")


async def test_api_list_returns_flat_results(mock_api: respx.MockRouter) -> None:
    mock_api.get("/api/feedings/").mock(
        return_value=httpx.Response(
            200,
            json={
                "count": 2,
                "next": None,
                "previous": None,
                "results": [{"id": 1}, {"id": 2}],
            },
        )
    )
    result = await api_list("feedings")
    assert len(result) == 2
    assert result[0]["id"] == 1


async def test_api_list_follows_pagination(mock_api: respx.MockRouter) -> None:
    responses = [
        httpx.Response(
            200,
            json={
                "count": 3,
                "next": f"{BASE}/api/feedings/?limit=2&offset=2",
                "previous": None,
                "results": [{"id": 1}, {"id": 2}],
            },
        ),
        httpx.Response(
            200,
            json={
                "count": 3,
                "next": None,
                "previous": f"{BASE}/api/feedings/?limit=2",
                "results": [{"id": 3}],
            },
        ),
    ]
    mock_api.get("/api/feedings/").mock(side_effect=responses)
    result = await api_list("feedings")
    assert len(result) == 3
    assert [r["id"] for r in result] == [1, 2, 3]


async def test_api_post_sends_json(mock_api: respx.MockRouter) -> None:
    mock_api.post("/api/feedings/").mock(
        return_value=httpx.Response(201, json={"id": 5, "child": 1})
    )
    result = await api_post("feedings", {"child": 1, "type": "breast milk"})
    assert result["id"] == 5


async def test_api_patch_sends_to_correct_url(mock_api: respx.MockRouter) -> None:
    mock_api.patch("/api/feedings/5/").mock(
        return_value=httpx.Response(200, json={"id": 5, "notes": "updated"})
    )
    result = await api_patch("feedings", 5, {"notes": "updated"})
    assert result["notes"] == "updated"


async def test_api_delete_sends_to_correct_url(mock_api: respx.MockRouter) -> None:
    mock_api.delete("/api/feedings/5/").mock(return_value=httpx.Response(204))
    await api_delete("feedings", 5)  # should not raise


async def test_api_delete_raises_on_error(mock_api: respx.MockRouter) -> None:
    mock_api.delete("/api/feedings/99/").mock(return_value=httpx.Response(404))
    with pytest.raises(httpx.HTTPStatusError):
        await api_delete("feedings", 99)


async def test_api_patch_accepts_slug(mock_api: respx.MockRouter) -> None:
    mock_api.patch("/api/children/alice-smith/").mock(
        return_value=httpx.Response(200, json={"slug": "alice-smith"})
    )
    result = await api_patch("children", "alice-smith", {"first_name": "Alicia"})
    assert result["slug"] == "alice-smith"


async def test_api_delete_accepts_slug(mock_api: respx.MockRouter) -> None:
    mock_api.delete("/api/tags/milestone/").mock(return_value=httpx.Response(204))
    await api_delete("tags", "milestone")  # should not raise


async def test_api_get_raw_no_trailing_slash(mock_api: respx.MockRouter) -> None:
    route = mock_api.get("/api/profile").mock(
        return_value=httpx.Response(200, json={"timezone": "UTC"})
    )
    result = await api_get_raw("profile")
    assert route.called
    assert result["timezone"] == "UTC"


async def test_api_patch_action_hits_subroute(mock_api: respx.MockRouter) -> None:
    route = mock_api.patch("/api/timers/1/restart/").mock(
        return_value=httpx.Response(200, json={"id": 1})
    )
    result = await api_patch_action("timers", 1, "restart")
    assert route.called
    assert result["id"] == 1


async def test_api_post_multipart_sends_files(mock_api: respx.MockRouter) -> None:
    route = mock_api.post("/api/notes/").mock(
        return_value=httpx.Response(201, json={"id": 1})
    )
    result = await api_post_multipart(
        "notes", {"child": 1, "note": "hi"}, {"image": ("pic.png", b"bytes")}
    )
    assert result["id"] == 1
    request = route.calls[0].request
    assert request.headers["content-type"].startswith("multipart/form-data")
    assert b"pic.png" in request.content


async def test_api_patch_multipart_sends_files(mock_api: respx.MockRouter) -> None:
    route = mock_api.patch("/api/notes/1/").mock(
        return_value=httpx.Response(200, json={"id": 1})
    )
    await api_patch_multipart(
        "notes", 1, {"note": "hi"}, {"image": ("pic.png", b"bytes")}
    )
    request = route.calls[0].request
    assert request.headers["content-type"].startswith("multipart/form-data")


async def test_client_sends_auth_header(mock_api: respx.MockRouter) -> None:
    route = mock_api.get("/api/children/").mock(
        return_value=httpx.Response(
            200, json={"count": 0, "next": None, "previous": None, "results": []}
        )
    )
    await api_list("children")
    assert route.called
    request = route.calls[0].request
    assert request.headers["Authorization"] == "Token test-token"


async def test_client_prefers_caller_bearer_token(
    mock_api: respx.MockRouter, monkeypatch: pytest.MonkeyPatch
) -> None:
    caller = AccessToken(token="caller-token", client_id="alice", scopes=[])
    monkeypatch.setattr(client_module, "get_access_token", lambda: caller)
    route = mock_api.get("/api/children/1/").mock(return_value=httpx.Response(200, json={"id": 1}))
    await api_get("children/1")
    assert route.calls[0].request.headers["Authorization"] == "Token caller-token"


async def test_client_errors_without_any_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "babybuddy_token", "")
    with pytest.raises(ToolError, match="bearer token"):
        await api_get("children/1")


async def test_verifier_accepts_token_babybuddy_accepts(mock_api: respx.MockRouter) -> None:
    route = mock_api.get("/api/profile").mock(
        return_value=httpx.Response(200, json={"user": {"username": "alice"}})
    )
    verifier = BabyBuddyTokenVerifier()
    access_token = await verifier.verify_token("good")
    assert access_token is not None
    assert access_token.client_id == "alice"
    assert route.calls[0].request.headers["Authorization"] == "Token good"
    await verifier.verify_token("good")
    assert route.call_count == 1


async def test_verifier_rejects_token_babybuddy_rejects(mock_api: respx.MockRouter) -> None:
    mock_api.get("/api/profile").mock(return_value=httpx.Response(401))
    assert await BabyBuddyTokenVerifier().verify_token("bad") is None


async def test_reset_client_fixture_works() -> None:
    """Confirm autouse reset_client fixture resets singleton between tests."""
    assert client_module._client is None
