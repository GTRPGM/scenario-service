import json
from typing import Any, Dict

from langchain_core.messages import HumanMessage, SystemMessage

from scenario.core.models.generation import (
    PlannerOutput,
    RelationManagerOutput,
    ReviewerOutput,
    WriterOutput,
)
from scenario.infra.db.prompt_loader import PromptLoader
from scenario.interfaces.agent import ScenarioAgent
from scenario.interfaces.llm import LLMPort


class BaseScenarioAgent(ScenarioAgent):
    def __init__(
        self, llm: LLMPort, loader: PromptLoader, agent_name: str, output_schema: Any
    ):
        self.llm = llm
        self.system_message = loader.load_prompt(agent_name)
        self.structured_llm = llm.with_structured_output(output_schema)

    async def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        payload_text = json.dumps(input_data, ensure_ascii=False, indent=2, default=str)
        messages = [
            SystemMessage(content=self.system_message),
            HumanMessage(
                content=f"다음 입력 데이터를 바탕으로 지정된 스키마에 맞춰 결과를 생성하십시오.\n\nINPUT_DATA:\n{payload_text}"
            ),
        ]

        # Invoke LLM with structured output
        response = await self.structured_llm.ainvoke(messages)

        # If response is a Pydantic model instance, dump it to dict
        if hasattr(response, "model_dump"):
            return response.model_dump()
        return response if isinstance(response, dict) else {}


class PlannerAgent(BaseScenarioAgent):
    def __init__(self, llm: LLMPort, loader: PromptLoader):
        super().__init__(llm, loader, "planner", PlannerOutput)


class WriterAgent(BaseScenarioAgent):
    def __init__(self, llm: LLMPort, loader: PromptLoader):
        super().__init__(llm, loader, "writer", WriterOutput)


class RelationAgent(BaseScenarioAgent):
    def __init__(self, llm: LLMPort, loader: PromptLoader):
        super().__init__(llm, loader, "relation_manager", RelationManagerOutput)


class AssetWriterAgent(BaseScenarioAgent):
    def __init__(self, llm: LLMPort, loader: PromptLoader):
        from scenario.core.models.generation import AssetWriterOutput

        super().__init__(llm, loader, "asset_writer", AssetWriterOutput)


class ReviewerAgent(BaseScenarioAgent):
    def __init__(self, llm: LLMPort, loader: PromptLoader):
        super().__init__(llm, loader, "reviewer", ReviewerOutput)


class PlanReviewerAgent(BaseScenarioAgent):
    def __init__(self, llm: LLMPort, loader: PromptLoader):
        super().__init__(llm, loader, "plan_reviewer", ReviewerOutput)


class AssetReviewerAgent(BaseScenarioAgent):
    def __init__(self, llm: LLMPort, loader: PromptLoader):
        super().__init__(llm, loader, "asset_reviewer", ReviewerOutput)


class WriterReviewerAgent(BaseScenarioAgent):
    def __init__(self, llm: LLMPort, loader: PromptLoader):
        super().__init__(llm, loader, "writer_reviewer", ReviewerOutput)


class ValidatorAgent(BaseScenarioAgent):
    def __init__(self, llm: LLMPort, loader: PromptLoader):
        from scenario.core.models.generation import ValidationOutput

        super().__init__(llm, loader, "validator", ValidationOutput)
