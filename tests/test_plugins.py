# tests/test_plugins.py

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from scenario.plugins.db.adapter import PostgresScenarioAdapter


@pytest.mark.asyncio
async def test_postgres_adapter_update_session_state(mock_db_handler):
    mock_loader = MagicMock()
    mock_loader.load_sql.return_value = "UPDATE table SET col = $1 WHERE id = $4"

    adapter = PostgresScenarioAdapter(db=mock_db_handler, loader=mock_loader)
    session_id = uuid4()

    await adapter.update_session_state(session_id, "act_1", "seq_1", {})

    mock_loader.load_sql.assert_called_once_with("update_session_state")
    mock_db_handler.execute.assert_called_once()
    # Check if arguments are passed correctly (ignoring the exact SQL string for now)
    args = mock_db_handler.execute.call_args[0]
    assert "act_1" in args
    assert "seq_1" in args
    assert session_id in args


@pytest.mark.asyncio
async def test_postgres_adapter_get_session_state():
    # Currently it's a placeholder
    mock_db = MagicMock()
    mock_db.fetchrow = AsyncMock(return_value={"id": 1, "current_act_id": "act_01"})

    adapter = PostgresScenarioAdapter(db=mock_db, loader=MagicMock())
    result = await adapter.get_session_state(uuid4())
    assert result["current_act_id"] == "act_01"
