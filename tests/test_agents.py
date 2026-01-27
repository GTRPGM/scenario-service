# tests/test_agents.py

from unittest.mock import AsyncMock, MagicMock

import pytest

from scenario.plugins.agent.scenario_agents import (
    PlannerAgent,
    ReviewerAgent,
    WriterAgent,
)


@pytest.fixture
def mock_prompt_loader():
    loader = MagicMock()
    loader.load_prompt.return_value = "System instruction"
    return loader


@pytest.mark.asyncio
async def test_planner_agent(mock_llm, mock_prompt_loader):
    # Setup mock chain
    mock_chain = MagicMock()
    mock_chain.ainvoke = AsyncMock()
    # Return an object that has .model_dump()
    mock_output = MagicMock()
    mock_output.model_dump.return_value = {"plan": "some plan"}
    mock_chain.ainvoke.return_value = mock_output

    mock_llm.with_structured_output.return_value = mock_chain

    agent = PlannerAgent(mock_llm, mock_prompt_loader)
    result = await agent.run({"concept": "test"})
    assert "plan" in result
    mock_prompt_loader.load_prompt.assert_called_with("planner")


@pytest.mark.asyncio
async def test_writer_agent(mock_llm, mock_prompt_loader):
    # Setup mock chain
    mock_chain = MagicMock()
    mock_chain.ainvoke = AsyncMock()
    mock_output = MagicMock()
    mock_output.model_dump.return_value = {"content": "story content"}
    mock_chain.ainvoke.return_value = mock_output

    mock_llm.with_structured_output.return_value = mock_chain

    agent = WriterAgent(mock_llm, mock_prompt_loader)
    result = await agent.run({"plan": {}})
    assert "content" in result
    mock_prompt_loader.load_prompt.assert_called_with("writer")


@pytest.mark.asyncio
async def test_reviewer_agent(mock_llm, mock_prompt_loader):
    # Setup mock chain
    mock_chain = MagicMock()
    mock_chain.ainvoke = AsyncMock()
    mock_output = MagicMock()
    mock_output.model_dump.return_value = {"is_consistent": True}
    mock_chain.ainvoke.return_value = mock_output

    mock_llm.with_structured_output.return_value = mock_chain

    agent = ReviewerAgent(mock_llm, mock_prompt_loader)
    result = await agent.run({"content": []})
    assert result["is_consistent"] is True
    mock_prompt_loader.load_prompt.assert_called_with("reviewer")
