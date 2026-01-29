# src/scenario/core/models/generation.py

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ScenarioInjectNPC(BaseModel):
    """NPC Template Data aligned with Injection Guide"""

    scenario_npc_id: str = Field(
        ..., description="Unique ID within the scenario (e.g., 'npc-001')"
    )
    master_id: Optional[str] = Field(
        None, description="Reference ID from Rule Engine Master Data"
    )
    name: str = Field(..., description="NPC Name")
    description: str = Field("", description="Brief biography or role")
    tags: List[str] = Field(
        default_factory=lambda: ["npc"], description="Searchable tags"
    )
    state: Dict[str, Any] = Field(
        default_factory=lambda: {
            "numeric": {"HP": 100, "MP": 50, "SAN": 10},
            "boolean": {},
        },
        description="Initial stats and flags",
    )


class ScenarioInjectEnemy(BaseModel):
    """Enemy Template Data aligned with Injection Guide"""

    scenario_enemy_id: str = Field(
        ..., description="Unique ID within the scenario (e.g., 'goblin-01')"
    )
    master_id: Optional[str] = Field(
        None, description="Reference ID from Rule Engine Master Data"
    )
    name: str = Field(..., description="Enemy Name")
    description: str = Field("", description="Lore or combat style")
    tags: List[str] = Field(
        default_factory=lambda: ["enemy"], description="Category tags"
    )
    state: Dict[str, Any] = Field(
        default_factory=lambda: {"numeric": {"HP": 100, "MP": 0}, "boolean": {}},
        description="Combat stats",
    )
    dropped_items: List[str] = Field(
        default_factory=list, description="List of Master Item IDs (UUID)"
    )


class ScenarioInjectItem(BaseModel):
    """Item Template Data aligned with Injection Guide"""

    item_id: str = Field(..., description="Fixed UUID for the Master Item")
    master_id: Optional[str] = Field(
        None, description="Reference ID from Rule Engine Master Data"
    )
    name: str = Field(..., description="Item Name")
    description: str = Field("", description="Function or flavor text")
    item_type: str = Field("misc", description="consumable, equipment, material, etc.")
    meta: Dict[str, Any] = Field(
        default_factory=dict, description="Custom properties like weight, price, etc."
    )


class ScenarioInjectRelation(BaseModel):
    """Relation (Edge) between Entities (Apache AGE)"""

    from_id: str = Field(
        ..., description="scenario_npc_id or scenario_enemy_id of the source"
    )
    to_id: str = Field(
        ..., description="scenario_npc_id or scenario_enemy_id of the target"
    )
    relation_type: str = Field("neutral", description="friend, foe, rival, etc.")
    affinity: int = Field(50, ge=0, le=100)
    meta: Dict[str, Any] = Field(default_factory=dict)


class ActPlan(BaseModel):
    id: str = Field(..., description="Act ID")
    name: str = Field(..., description="Act Name (Thematic)")
    region_name: str = Field(
        ..., description="The physical region/location this act takes place in"
    )
    region_description: str = Field(
        ..., description="Detailed description of the whole region"
    )
    goal: str = Field(..., description="Main objective of this act")
    exit_criteria: str = Field(
        ...,
        description="Condition to trigger transition to the next Act (Travel)",
    )
    sequences: List[str] = Field(
        ..., description="List of POI/Event sequences available in this region"
    )


class PlannerOutput(BaseModel):
    title: str = Field(..., description="Scenario Title")
    description: str = Field(..., description="Long summary of the scenario")
    difficulty: str = Field("normal", description="easy, normal, hard, nightmare")
    genre: str = Field(..., description="fantasy, sci-fi, horror, etc.")
    tags: List[str] = Field(default_factory=list, description="Scenario-level tags")
    total_acts: int = Field(..., description="Number of Acts (Regions)", ge=1)
    acts: List[ActPlan]
    total_summary: str = Field(..., description="Brief scenario summary")
    relations: List[ScenarioInjectRelation] = Field(
        default_factory=list,
        description="Global relations between major entities or factions",
    )


class SequenceDetail(BaseModel):
    id: str = Field(..., description="Sequence ID")
    name: str = Field(..., description="Sequence Name")
    sequence_type: str = Field(..., description="Type (Combat, Exploration, etc.)")
    location_name: str = Field(..., description="Location name")
    location_master_id: Optional[str] = Field(
        None, description="Reference ID from Rule Engine for the location"
    )
    location_theme: str = Field(..., description="Location theme")
    location_description: str = Field(..., description="Location description")
    danger_min: int = Field(default=1, description="Minimum danger level (1-10)")
    danger_max: int = Field(default=10, description="Maximum danger level (1-10)")
    description: str = Field(..., description="Narrative description")
    goal: str = Field(..., description="Sequence goal")
    exit_triggers: List[str] = Field(..., description="Exit conditions")

    npcs: List[ScenarioInjectNPC] = Field(default_factory=list)
    enemies: List[ScenarioInjectEnemy] = Field(default_factory=list)
    items: List[ScenarioInjectItem] = Field(default_factory=list)


class WriterOutput(BaseModel):
    sequences: List[SequenceDetail]


class ReviewerOutput(BaseModel):
    is_consistent: bool
    reviews: List[str]


class ValidationRequest(BaseModel):
    scenario_id: str
    current_act: ActPlan = Field(..., description="Details of the current act/region")
    current_sequence: SequenceDetail = Field(
        ..., description="Details of the sequence the player is currently in"
    )
    available_sequences: List[SequenceDetail] = Field(
        ..., description="All POIs available in this act for jumping"
    )
    user_input: str
    context: Dict[str, Any] = Field(
        default_factory=dict, description="Additional graph context (e.g., relations)"
    )


class ValidationOutput(BaseModel):
    is_triggered: bool = Field(
        ..., description="Whether the transition condition is met"
    )

    reason: str = Field(..., description="Reasoning for the decision")

    next_act_id: Optional[str] = None

    next_seq_id: Optional[str] = None

    suggested_narration: Optional[str] = Field(
        None, description="GM narration for the transition"
    )
