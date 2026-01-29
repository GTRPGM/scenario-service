# src/scenario/plugins/agent/scenario_agents.py

from typing import Any, Dict

from langchain_core.messages import HumanMessage, SystemMessage

from scenario.core.models.generation import PlannerOutput, ReviewerOutput, WriterOutput
from scenario.infra.db.prompt_loader import PromptLoader
from scenario.interfaces.agent import ScenarioAgent
from scenario.interfaces.llm import LLMPort


class BaseScenarioAgent(ScenarioAgent):
    """Base implementation for agents using LLM and PromptLoader."""

    def __init__(
        self, llm: LLMPort, loader: PromptLoader, agent_name: str, output_schema: Any
    ):
        self.llm = llm
        self.system_message = loader.load_prompt(agent_name)
        # Bind the structured output schema to the model
        self.structured_llm = llm.with_structured_output(output_schema)

    async def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        messages = [
            SystemMessage(content=self.system_message),
            HumanMessage(content=f"Current Progress/Data: {input_data}"),
        ]
        response = await self.structured_llm.ainvoke(messages)
        return response.model_dump()


class PlannerAgent(BaseScenarioAgent):
    def __init__(self, llm: LLMPort, loader: PromptLoader):
        super().__init__(llm, loader, "planner", PlannerOutput)


class WriterAgent(BaseScenarioAgent):
    def __init__(self, llm: LLMPort, loader: PromptLoader):
        super().__init__(llm, loader, "writer", WriterOutput)


class ReviewerAgent(BaseScenarioAgent):
    def __init__(self, llm: LLMPort, loader: PromptLoader):
        super().__init__(llm, loader, "reviewer", ReviewerOutput)


class ValidatorAgent(BaseScenarioAgent):
    def __init__(self, llm: LLMPort, loader: PromptLoader):
        from scenario.core.models.generation import ValidationOutput

        super().__init__(llm, loader, "validator", ValidationOutput)
