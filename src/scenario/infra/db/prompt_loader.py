# src/scenario/infra/db/prompt_loader.py

import os
from functools import lru_cache


@lru_cache(maxsize=32)
def _read_prompt(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


class PromptLoader:
    """Infrastructure: Loads agent prompts from external text files."""

    def __init__(self, base_path: str = None):
        if base_path is None:
            base_path = os.path.join(
                os.path.dirname(os.path.dirname(__file__)), "prompts"
            )
        self.base_path = os.path.abspath(base_path)

    def load_prompt(self, agent_name: str) -> str:
        path = os.path.join(self.base_path, f"{agent_name}.txt")
        return _read_prompt(path)
