# src/scenario/interfaces/llm.py

from abc import ABC, abstractmethod

from langchain_core.language_models.chat_models import BaseChatModel


class LLMPort(BaseChatModel, ABC):
    """Abstract base class for LLM implementations, compatible with LangChain."""

    @abstractmethod
    async def check_health(self) -> bool:
        """Check if LLM service is reachable."""
        pass
