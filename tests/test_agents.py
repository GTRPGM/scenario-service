# tests/test_agents.py

from unittest.mock import MagicMock

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
    agent = PlannerAgent(mock_llm, mock_prompt_loader)
    result = await agent.run({"concept": "test"})
    assert "plan" in result
    mock_prompt_loader.load_prompt.assert_called_with("planner")


@pytest.mark.asyncio
async def test_writer_agent(mock_llm, mock_prompt_loader):
    agent = WriterAgent(mock_llm, mock_prompt_loader)
    result = await agent.run({"plan": {}})
    assert "content" in result
    mock_prompt_loader.load_prompt.assert_called_with("writer")


@pytest.mark.asyncio
async def test_reviewer_agent(mock_llm, mock_prompt_loader):
    agent = ReviewerAgent(mock_llm, mock_prompt_loader)
    result = await agent.run({"content": []})
    assert result["is_consistent"] is True
    mock_prompt_loader.load_prompt.assert_called_with("reviewer")
