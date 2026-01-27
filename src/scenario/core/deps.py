from scenario.core.config import settings
from scenario.core.engine.scenario_engine import ScenarioEngine
from scenario.core.engine.writer_graph import ScenarioWriterGraph
from scenario.infra.db.database import DatabaseHandler
from scenario.infra.db.prompt_loader import PromptLoader
from scenario.infra.db.query_loader import QueryLoader
from scenario.plugins.agent.scenario_agents import (
    PlannerAgent,
    ReviewerAgent,
    WriterAgent,
)
from scenario.plugins.db.adapter import PostgresScenarioAdapter
from scenario.plugins.llm.adapter import ScenarioChatModel

# Global Infrastructure
db_handler = DatabaseHandler(settings.database_dsn)
query_loader = QueryLoader()
prompt_loader = PromptLoader()
llm_model = ScenarioChatModel()


async def get_scenario_engine() -> ScenarioEngine:
    """Dependency provider that wires agents, graph, and engine."""
    repository = PostgresScenarioAdapter(db_handler, query_loader)

    # Instantiate Agents (Plugins)
    planner = PlannerAgent(llm_model, prompt_loader)
    writer = WriterAgent(llm_model, prompt_loader)
    reviewer = ReviewerAgent(llm_model, prompt_loader)

    # Create Graph (Core Engine)
    writer_graph = ScenarioWriterGraph(planner, writer, reviewer)

    return ScenarioEngine(repository, writer_graph)
