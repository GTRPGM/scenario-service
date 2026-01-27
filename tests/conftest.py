# tests/conftest.py

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

# Mocking db_handler BEFORE importing app
with patch("scenario.core.deps.db_handler") as mock_db:
    mock_db.connect = AsyncMock()
    mock_db.close = AsyncMock()
    from scenario.main import app

from scenario.core.deps import get_scenario_engine
from scenario.core.engine.scenario_engine import ScenarioEngine
from scenario.interfaces.agent import ScenarioAgent


@pytest.fixture
def mock_db_handler():
    handler = MagicMock()
    handler.connect = AsyncMock()
    handler.close = AsyncMock()
    handler.execute = AsyncMock()
    handler.fetch = AsyncMock()
    handler.fetchrow = AsyncMock()
    handler.get_connection = MagicMock()
    return handler


@pytest.fixture
def mock_repository():
    repo = MagicMock()
    repo.get_session_state = AsyncMock()
    repo.update_session_state = AsyncMock()
    return repo


@pytest.fixture
def mock_llm():
    llm = MagicMock()
    llm.ainvoke = AsyncMock()
    llm.with_structured_output = MagicMock(return_value=AsyncMock())
    return llm


@pytest.fixture
def mock_agent():
    agent = MagicMock(spec=ScenarioAgent)
    agent.run = AsyncMock()
    return agent


@pytest.fixture
def client():
    mock_engine = MagicMock(spec=ScenarioEngine)
    mock_engine.check_progression = AsyncMock(return_value={"status": "active"})
    mock_engine.execute_transition = AsyncMock()
    mock_engine.generate_scenario = AsyncMock(return_value={"status": "completed"})

    app.dependency_overrides[get_scenario_engine] = lambda: mock_engine

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()
