# tests/conftest.py

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from testcontainers.postgres import PostgresContainer

from scenario.infra.db.database import DatabaseHandler
from scenario.infra.db.init_db import init_db

# Mocking db_handler BEFORE importing app for API tests
with patch("scenario.core.deps.db_handler") as mock_db:
    mock_db.connect = AsyncMock()
    mock_db.close = AsyncMock()
    from scenario.main import app

from scenario.core.deps import get_scenario_engine
from scenario.core.engine.scenario_engine import ScenarioEngine
from scenario.interfaces.agent import ScenarioAgent


@pytest.fixture(scope="session")
def postgres_container():
    """
    Starts a postgres-ex container (with Apache AGE) for the entire test session.
    """
    container = PostgresContainer("postgres-ex:latest", driver=None)
    with container:
        host = container.get_container_host_ip()
        port = container.get_exposed_port(5432)
        user = container.username
        password = container.password
        dbname = container.dbname
        dsn = f"postgresql://{user}:{password}@{host}:{port}/{dbname}"
        yield dsn


@pytest.fixture(scope="session")
async def real_db_handler(postgres_container):
    """
    Provides a real DatabaseHandler connected to the test container.
    """
    handler = DatabaseHandler(postgres_container)
    await handler.connect()

    # Initialize AGE and Schema
    await init_db(handler)

    yield handler
    await handler.close()


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
    mock_engine.generate_scenario = AsyncMock(return_value={"status": "completed"})
    mock_engine.generate_pure = AsyncMock(return_value={"status": "completed"})
    mock_engine.generate_grounded = AsyncMock(return_value={"status": "completed"})
    mock_engine.generate_informed = AsyncMock(return_value={"status": "completed"})

    mock_engine.validate_progression = AsyncMock(
        return_value={
            "status": "active",
            "reason": "Test validation",
            "next_act_id": "act_2",
            "next_seq_id": "seq_2",
            "suggested_narration": "You move forward.",
        }
    )

    mock_engine.get_session_state = AsyncMock(
        return_value={
            "scenario_id": "00000000-0000-0000-0000-000000000000",
            "current_act_id": "act_1",
            "current_sequence_id": "seq_1",
        }
    )

    app.dependency_overrides[get_scenario_engine] = lambda: mock_engine

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()
