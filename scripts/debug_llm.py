# scripts/debug_llm.py

import asyncio

from langchain_core.messages import HumanMessage, SystemMessage

from scenario.core.models.generation import PlannerOutput
from scenario.plugins.llm.adapter import ScenarioChatModel


async def debug():
    llm = ScenarioChatModel()
    structured_llm = llm.with_structured_output(PlannerOutput)

    messages = [
        SystemMessage(content="You are a TRPG planner."),
        HumanMessage(content="concept: A dark forest with a mysterious tower."),
    ]

    try:
        print("Sending request to LLM Gateway...")
        response = await structured_llm.ainvoke(messages)
        print("Success!")
        print(response)
    except Exception as e:
        print(f"Failed with error: {e}")


if __name__ == "__main__":
    asyncio.run(debug())
