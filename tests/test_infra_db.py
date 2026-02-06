# tests/test_infra_db.py

from unittest.mock import AsyncMock

import pytest

from scenario.infra.db.init_db import init_db


@pytest.mark.asyncio
async def test_init_db_logic(mock_db_handler):
    # Mocking the database connection context manager
    mock_conn = AsyncMock()
    mock_db_handler.get_connection.return_value.__aenter__.return_value = mock_conn

    # Mock settings indirectly via patch if needed, but here we check the flow
    # Case: Graph does not exist
    mock_conn.fetchval.return_value = 0

    await init_db(mock_db_handler)

    mock_conn.fetchval.assert_called_once()
    # Check if create_graph was called among other execute calls
    mock_conn.execute.assert_any_call("SELECT create_graph('scenario_graph');")
