# tests/test_llm_plugin.py

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.messages import HumanMessage

from scenario.plugins.llm.adapter import ScenarioChatModel


@pytest.fixture
def mock_httpx_client():
    with patch("httpx.AsyncClient") as mock:
        client_instance = mock.return_value.__aenter__.return_value
        client_instance.post = AsyncMock()
        client_instance.get = AsyncMock()
        yield client_instance


def test_llm_adapter_convert_message():
    model = ScenarioChatModel()
    msg = HumanMessage(content="hello")
    schema_msg = model._convert_message_to_schema(msg)
    assert schema_msg.role == "user"
    assert schema_msg.content == "hello"


@pytest.mark.asyncio
async def test_llm_adapter_check_health(mock_httpx_client):
    model = ScenarioChatModel()

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_httpx_client.get.return_value = mock_response

    is_healthy = await model.check_health()
    assert is_healthy is True


@pytest.mark.asyncio
async def test_llm_adapter_agenerate(mock_httpx_client):
    model = ScenarioChatModel()

    mock_resp_json = {
        "id": "test_id",
        "object": "chat.completion",
        "created": 123,
        "model": "test",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": "AI"},
                "finish_reason": "stop",
            }
        ],
    }

    mock_response = MagicMock()
    mock_response.json.return_value = mock_resp_json
    mock_response.status_code = 200
    mock_httpx_client.post.return_value = mock_response

    messages = [HumanMessage(content="hi")]
    result = await model._agenerate(messages)

    assert result.generations[0].message.content == "AI"
