from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from testcontainers.postgres import PostgresContainer

from scenario.infra.db.database import DatabaseHandler
from scenario.infra.db.init_db import init_db

# Patch db_handler BEFORE any other imports that might use it
mock_db = MagicMock()
mock_db.connect = AsyncMock()
mock_db.close = AsyncMock()

with patch("scenario.core.deps.db_handler", mock_db):
    from scenario.core.deps import (
        get_scenario_engine,
        get_scenario_repository,
        get_validator_agent,
    )
    from scenario.core.engine.scenario_engine import ScenarioEngine
    from scenario.core.engine.writer_graph import ScenarioWriterGraph
    from scenario.interfaces.agent import ScenarioAgent
    from scenario.main import app


@pytest.fixture(scope="session")
def postgres_container():
    import os

    image = os.getenv("TEST_CONTAINER_IMAGE", "postgres-ex:latest")
    dbname = os.getenv("TEST_CONTAINER_DB", "gtrpgm")
    container = PostgresContainer(image, driver=None, dbname=dbname)
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
    handler = DatabaseHandler(postgres_container)
    await handler.connect()
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
    repo.save_scenario = AsyncMock(return_value=uuid4())
    repo.list_scenarios = AsyncMock(return_value=[])
    repo.get_session_state = AsyncMock(return_value={})
    repo.update_session_state = AsyncMock()
    repo.get_act_context = AsyncMock(return_value={})
    repo.get_scenario_full_graph = AsyncMock(return_value={})
    repo.create_generation_run = AsyncMock(return_value=uuid4())
    repo.count_generation_requests_for_stage = AsyncMock(return_value=0)
    repo.save_generation_step = AsyncMock()
    repo.log_generation_request = AsyncMock(return_value=uuid4())
    repo.get_generation_run_report = AsyncMock(
        return_value={"run": {"id": uuid4()}, "steps": [], "logs": []}
    )
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
def client(mock_repository):
    # Instead of mocking the entire ScenarioEngine, we use a real one
    # but with mocked repository and writer graph.
    mock_writer_graph = MagicMock(spec=ScenarioWriterGraph)
    # Set up default return for writer graph to avoid crashes in basic tests
    mock_writer_graph.run = AsyncMock(
        return_value={
            "plan": {"title": "Test", "acts": [], "relations": []},
            "items": [],
            "npcs": [],
            "enemies": [],
            "content": {"sequences": []},
        }
    )

    real_engine = ScenarioEngine(repository=mock_repository, writer=mock_writer_graph)

    mock_validator = AsyncMock(spec=ScenarioAgent)
    mock_validator.run.return_value = {
        "is_triggered": False,
        "reason": "Test validation",
        "next_act_id": "act_2",
        "next_seq_id": "seq_2",
        "suggested_narration": "You move forward.",
    }
    app.dependency_overrides[get_scenario_engine] = lambda: real_engine
    app.dependency_overrides[get_scenario_repository] = lambda: mock_repository
    app.dependency_overrides[get_validator_agent] = lambda: mock_validator

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()
