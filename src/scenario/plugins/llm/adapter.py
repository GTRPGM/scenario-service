# src/scenario/plugins/llm/adapter.py

import json
from typing import Any, List, Optional

import httpx
from langchain_core.callbacks import (
    AsyncCallbackManagerForLLMRun,
    CallbackManagerForLLMRun,
)
from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    ChatMessage,
    SystemMessage,
)
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.runnables import RunnableLambda
from pydantic import Field

from scenario.core.config import settings
from scenario.core.models.llm import (
    ChatCompletionRequest,
    ChatCompletionResponse,
)
from scenario.core.models.llm import (
    ChatMessage as SchemaChatMessage,
)
from scenario.interfaces.llm import LLMPort


class ScenarioChatModel(LLMPort):
    """
    Custom LangChain ChatModel adapter for the LLM Gateway.
    Matches the pattern used in the GM service.
    """

    base_url: str = Field(default_factory=lambda: settings.LLM_GATEWAY_URL)

    # Use a long timeout for LLM generation
    timeout: float = 600.0

    @property
    def _llm_type(self) -> str:
        return "scenario_llm_gateway"

    def _convert_message_to_schema(self, message: BaseMessage) -> SchemaChatMessage:
        """Converts LangChain message to our Pydantic schema."""
        role = "user"
        if isinstance(message, SystemMessage):
            role = "system"
        elif isinstance(message, AIMessage):
            role = "assistant"
        elif isinstance(message, ChatMessage):
            role = message.role

        return SchemaChatMessage(role=role, content=str(message.content))

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        raise NotImplementedError(
            "Sync generation not implemented. Use ainvoke/agenerate."
        )

    async def _agenerate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[AsyncCallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        schema_messages = [self._convert_message_to_schema(m) for m in messages]

        request_body = ChatCompletionRequest(
            model=settings.LLM_MODEL_NAME,
            messages=schema_messages,
            temperature=kwargs.get("temperature", 0.7),
            max_tokens=kwargs.get("max_tokens"),
            response_format=kwargs.get("response_format"),
            tools=kwargs.get("tools"),
            tool_choice=kwargs.get("tool_choice"),
        )

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url.rstrip('/')}/api/v1/chat/completions",
                json=request_body.model_dump(exclude_none=True),
            )
            response.raise_for_status()

            chat_response = ChatCompletionResponse(**response.json())

            if not chat_response.choices:
                return ChatResult(generations=[])

            choice = chat_response.choices[0]
            msg_kwargs = {}
            if choice.message.tool_calls:
                msg_kwargs["tool_calls"] = choice.message.tool_calls

            raw_content = choice.message.content or ""
            parsed_content = None
            response_format = kwargs.get("response_format")

            if response_format and isinstance(raw_content, str):
                fmt_type = response_format.get("type")
                if fmt_type in ("json_object", "json_schema"):
                    try:
                        parsed_content = json.loads(raw_content)
                    except json.JSONDecodeError:
                        parsed_content = None

            final_content: Any
            if parsed_content is not None:
                final_content = (
                    parsed_content
                    if isinstance(parsed_content, list)
                    else [parsed_content]
                )
                msg_kwargs["parsed"] = parsed_content
            else:
                final_content = raw_content

            generation = ChatGeneration(
                message=AIMessage(
                    content=final_content,
                    additional_kwargs=msg_kwargs,
                ),
                generation_info={"finish_reason": choice.finish_reason},
            )

            return ChatResult(generations=[generation])

    def with_structured_output(
        self,
        schema: Any,
        *,
        method: str = "json_object",
        **kwargs: Any,
    ) -> RunnableLambda:
        async def _call(messages: List[BaseMessage]) -> Any:
            # When using json_object, we should ideally remind the model
            # about the schema in the prompt but for now let's see
            # if the existing prompts are enough.
            result = await self.ainvoke(
                messages,
                response_format={"type": "json_object"},
            )

            content = result.content
            # Handle cases where result.content might be a string or a list/dict
            if isinstance(content, list) and len(content) > 0:
                data = content[0]
            else:
                data = content

            if isinstance(data, str):
                try:
                    data = json.loads(data)
                except json.JSONDecodeError as e:
                    raise ValueError(f"Failed to parse JSON response: {data}") from e

            return schema.model_validate(data)

        return RunnableLambda(_call)

    async def check_health(self) -> bool:
        """Check if LLM Gateway is reachable."""
        async with httpx.AsyncClient(timeout=3.0) as client:
            try:
                resp = await client.get(f"{self.base_url.rstrip('/')}/health")
                return resp.status_code == 200
            except Exception:
                return False
