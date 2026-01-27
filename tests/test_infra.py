# tests/test_infra.py

import os

from scenario.infra.db.prompt_loader import PromptLoader
from scenario.infra.db.query_loader import QueryLoader, _read_query


def test_query_loader_initialization(tmp_path):
    loader = QueryLoader(base_path=str(tmp_path))
    assert loader.base_path == os.path.abspath(str(tmp_path))


def test_query_loader_load_sql(tmp_path):
    sql_dir = tmp_path / "sql"
    sql_dir.mkdir()
    sql_file = sql_dir / "test_query.sql"
    content = "SELECT * FROM users;"
    sql_file.write_text(content)

    loader = QueryLoader(base_path=str(tmp_path))
    loaded_content = loader.load_sql("test_query")
    assert loaded_content == content


def test_query_loader_load_cypher(tmp_path):
    cypher_dir = tmp_path / "cypher"
    cypher_dir.mkdir()
    cypher_file = cypher_dir / "test_graph.cypher"
    content = "MATCH (n) RETURN n;"
    cypher_file.write_text(content)

    loader = QueryLoader(base_path=str(tmp_path))
    loaded_content = loader.load_cypher("test_graph")
    assert loaded_content == content


def test_read_query_caching(tmp_path):
    test_file = tmp_path / "cache_unique_test.txt"
    test_file.write_text("v1")

    # First read
    content1 = _read_query(str(test_file))
    assert content1 == "v1"

    # Change file content
    test_file.write_text("v2")

    # Second read (should be from cache)
    content2 = _read_query(str(test_file))
    assert content2 == "v1"


def test_prompt_loader(tmp_path):
    prompt_file = tmp_path / "planner.txt"
    prompt_file.write_text("Planner prompt")

    loader = PromptLoader(base_path=str(tmp_path))
    content = loader.load_prompt("planner")
    assert content == "Planner prompt"
