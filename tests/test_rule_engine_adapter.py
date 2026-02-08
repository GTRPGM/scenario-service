from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from scenario.plugins.rule_engine.adapter import HttpRuleEngineAdapter


@pytest.fixture
def mock_httpx_client():
    with patch("httpx.AsyncClient") as mock:
        client_instance = mock.return_value.__aenter__.return_value
        client_instance.get = AsyncMock()
        client_instance.post = AsyncMock()
        yield client_instance


@pytest.mark.asyncio
async def test_search_master_data_success_and_non_200(mock_httpx_client):
    adapter = HttpRuleEngineAdapter(base_url="http://rule")

    ok = MagicMock(status_code=200)
    ok.json.return_value = {"results": [{"id": 1}]}
    fail = MagicMock(status_code=500)
    fail.json.return_value = {"results": [{"id": 9}]}
    mock_httpx_client.get.side_effect = [ok, fail]

    assert await adapter.search_master_data("NPC", "guard", limit=2) == [{"id": 1}]
    assert await adapter.search_master_data("NPC", "guard", limit=2) == []


@pytest.mark.asyncio
async def test_search_master_data_exception_returns_empty(mock_httpx_client):
    adapter = HttpRuleEngineAdapter(base_url="http://rule")
    mock_httpx_client.get.side_effect = RuntimeError("boom")
    assert await adapter.search_master_data("item", "potion") == []


@pytest.mark.asyncio
async def test_bulk_grounding_passthrough():
    adapter = HttpRuleEngineAdapter(base_url="http://rule")
    payload = {"acts": [1]}
    assert await adapter.bulk_grounding(payload) == payload


@pytest.mark.asyncio
async def test_get_all_assets_collects_partial_data(mock_httpx_client):
    adapter = HttpRuleEngineAdapter(base_url="http://rule")

    locales = MagicMock(status_code=200)
    locales.json.return_value = {"data": {"locales": [{"id": "loc-1"}]}}

    npcs_fail = RuntimeError("npcs unavailable")

    enemies = MagicMock(status_code=200)
    enemies.json.return_value = {"data": {"enemies": [{"id": "enemy-1"}]}}

    items = MagicMock(status_code=200)
    items.json.return_value = {"data": {"items": [{"id": "item-1"}]}}

    mock_httpx_client.get.side_effect = [locales]
    mock_httpx_client.post.side_effect = [npcs_fail, enemies, items]

    assets = await adapter.get_all_assets()

    assert assets["locations"] == [{"id": "loc-1"}]
    assert assets["npcs"] == []
    assert assets["enemies"] == [{"id": "enemy-1"}]
    assert assets["items"] == [{"id": "item-1"}]
