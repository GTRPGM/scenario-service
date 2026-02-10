# src/scenario/core/deps.py

from scenario.core.config import settings
from scenario.core.engine.scenario_engine import ScenarioEngine
from scenario.core.engine.writer_graph import ScenarioWriterGraph
from scenario.infra.db.database import DatabaseHandler
from scenario.infra.db.prompt_loader import PromptLoader
from scenario.infra.db.query_loader import QueryLoader
from scenario.plugins.agent.scenario_agents import (
    AssetReviewerAgent,
    AssetWriterAgent,
    PlannerAgent,
    PlanReviewerAgent,
    RelationAgent,
    ReviewerAgent,
    ValidatorAgent,
    WriterAgent,
    WriterReviewerAgent,
)
from scenario.plugins.db.adapter import PostgresScenarioAdapter
from scenario.plugins.llm.adapter import ScenarioChatModel
from scenario.plugins.rule_engine.adapter import HttpRuleEngineAdapter

# Global Infrastructure
db_handler = DatabaseHandler(settings.database_dsn)
query_loader = QueryLoader()
prompt_loader = PromptLoader()
llm_model = ScenarioChatModel()
rule_engine = HttpRuleEngineAdapter()


async def get_validator_agent() -> ValidatorAgent:
    """Dependency provider for the ValidatorAgent."""
    return ValidatorAgent(llm_model, prompt_loader)


async def get_scenario_engine() -> ScenarioEngine:
    """Dependency provider that wires agents, graph, and engine."""
    repository = PostgresScenarioAdapter(db_handler, query_loader)

    # Instantiate Agents (Plugins)
    planner = PlannerAgent(llm_model, prompt_loader)
    asset_writer = AssetWriterAgent(llm_model, prompt_loader)
    relation_manager = RelationAgent(llm_model, prompt_loader)
    writer = WriterAgent(llm_model, prompt_loader)
    reviewer = ReviewerAgent(llm_model, prompt_loader)

    # Stage-Gate Reviewers
    plan_reviewer = PlanReviewerAgent(llm_model, prompt_loader)
    asset_reviewer = AssetReviewerAgent(llm_model, prompt_loader)
    writer_reviewer = WriterReviewerAgent(llm_model, prompt_loader)

    # Create Graph (Core Engine)
    writer_graph = ScenarioWriterGraph(
        planner,
        writer,
        reviewer,
        asset_writer=asset_writer,
        relation_manager=relation_manager,
        plan_reviewer=plan_reviewer,
        asset_reviewer=asset_reviewer,
        writer_reviewer=writer_reviewer,
        rule_engine=rule_engine,
    )

    return ScenarioEngine(repository, writer_graph, rule_engine=rule_engine)
