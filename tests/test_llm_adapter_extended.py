import json
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from langchain_core.messages import AIMessage, ChatMessage, HumanMessage, SystemMessage
from pydantic import BaseModel

from scenario.plugins.llm.adapter import ScenarioChatModel


@pytest.fixture
def mock_httpx_client():
    with patch("httpx.AsyncClient") as mock:
        client_instance = mock.return_value.__aenter__.return_value
        client_instance.post = AsyncMock()
        client_instance.get = AsyncMock()
        yield client_instance


def _response(status: int, body: dict):
    resp = MagicMock()
    resp.status_code = status
    resp.json.return_value = body
    resp.request = httpx.Request("POST", "http://llm/api/v1/chat/completions")
    if status >= 400:
        resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "error", request=resp.request, response=resp
        )
    else:
        resp.raise_for_status.return_value = None
    return resp


def test_convert_message_roles_and_sync_not_supported():
    model = ScenarioChatModel()

    assert (
        model._convert_message_to_schema(SystemMessage(content="sys")).role == "system"
    )
    assert model._convert_message_to_schema(AIMessage(content="ai")).role == "assistant"
    assert (
        model._convert_message_to_schema(ChatMessage(role="tool", content="x")).role
        == "tool"
    )
    assert model._convert_message_to_schema(HumanMessage(content="user")).role == "user"

    with pytest.raises(NotImplementedError):
        model._generate([HumanMessage(content="hi")])


@pytest.mark.asyncio
async def test_agenerate_retry_then_success_json_response_format(mock_httpx_client):
    model = ScenarioChatModel(llm_retry_attempts=2, llm_retry_base_delay=0.01)
    first = _response(500, {"choices": []})
    second = _response(
        200,
        {
            "id": "1",
            "object": "chat.completion",
            "created": 1,
            "model": "x",
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": json.dumps({"a": 1})},
                    "finish_reason": "stop",
                }
            ],
        },
    )
    mock_httpx_client.post.side_effect = [first, second]

    result = await model._agenerate(
        [HumanMessage(content="hi")],
        response_format={"type": "json_object"},
    )

    assert mock_httpx_client.post.await_count == 2
    content = result.generations[0].message.content
    assert isinstance(content, list)
    assert content[0] == {"a": 1}
    assert result.generations[0].message.additional_kwargs["parsed"] == {"a": 1}


@pytest.mark.asyncio
async def test_agenerate_empty_choices_and_check_health_false(mock_httpx_client):
    model = ScenarioChatModel()
    mock_httpx_client.post.return_value = _response(
        200,
        {
            "id": "1",
            "object": "chat.completion",
            "created": 1,
            "model": "x",
            "choices": [],
        },
    )
    result = await model._agenerate([HumanMessage(content="hi")])
    assert result.generations == []

    mock_httpx_client.get.side_effect = RuntimeError("down")
    assert await model.check_health() is False


class _StructuredOut(BaseModel):
    title: str


@pytest.mark.asyncio
async def test_with_structured_output_parses_string_json():
    model = ScenarioChatModel()
    with patch.object(
        ScenarioChatModel,
        "ainvoke",
        new=AsyncMock(return_value=AIMessage(content='{"title": "ok"}')),
    ):
        runnable = model.with_structured_output(_StructuredOut)
        out = await runnable.ainvoke([HumanMessage(content="make json")])
        assert out.title == "ok"


@pytest.mark.asyncio
async def test_with_structured_output_invalid_json_raises():
    model = ScenarioChatModel()
    with patch.object(
        ScenarioChatModel,
        "ainvoke",
        new=AsyncMock(return_value=AIMessage(content="not-json")),
    ):
        runnable = model.with_structured_output(_StructuredOut)

        with pytest.raises(ValueError):
            await runnable.ainvoke([HumanMessage(content="x")])


@pytest.mark.asyncio
async def test_agenerate_invalid_json_and_tool_calls_paths(mock_httpx_client):
    model = ScenarioChatModel()
    mock_httpx_client.post.return_value = _response(
        200,
        {
            "id": "1",
            "object": "chat.completion",
            "created": 1,
            "model": "x",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": "{invalid-json",
                        "tool_calls": [
                            {"id": "call-1", "type": "function", "function": {}}
                        ],
                    },
                    "finish_reason": "tool_calls",
                }
            ],
        },
    )
    result = await model._agenerate(
        [HumanMessage(content="run")],
        response_format={"type": "json_schema"},
    )
    msg = result.generations[0].message
    assert msg.content == "{invalid-json"
    assert "parsed" not in msg.additional_kwargs
    assert msg.additional_kwargs["tool_calls"][0]["id"] == "call-1"


@pytest.mark.asyncio
async def test_agenerate_raises_runtime_when_retry_count_zero():
    model = ScenarioChatModel(llm_retry_attempts=0)
    with pytest.raises(RuntimeError, match="without response"):
        await model._agenerate([HumanMessage(content="hi")])
