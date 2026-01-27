# src/scenario/infra/db/query_loader.py

import os
from functools import lru_cache


@lru_cache(maxsize=256)
def _read_query(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


class QueryLoader:
    """Infrastructure: Low-level file system query loader."""

    def __init__(self, base_path: str = None):
        if base_path is None:
            # Default to the sibling queries directory
            base_path = os.path.join(os.path.dirname(__file__), "queries")
        self.base_path = os.path.abspath(base_path)

    def load_sql(self, filename: str) -> str:
        path = os.path.join(self.base_path, "sql", f"{filename}.sql")
        return _read_query(path)

    def load_cypher(self, filename: str) -> str:
        path = os.path.join(self.base_path, "cypher", f"{filename}.cypher")
        return _read_query(path)
