# src/scenario/core/models/generation.py

from typing import List, Optional

from pydantic import BaseModel, Field


class EntityDetail(BaseModel):
    id: str = Field(..., description="Unique ID for the entity")
    name: str = Field(..., description="Name of the entity")
    entity_category: str = Field(..., description="Category: NPC, ITEM, or ENEMY")
    description: str = Field(..., description="Detailed description")
    interaction_guide: str = Field(..., description="Interaction guideline for GM")

    # NPC specific (Aligned with 'npcs' table)
    disposition: Optional[str] = Field(
        None, description="Attitude (Friendly, Neutral, Hostile)"
    )
    occupation: Optional[str] = Field(None, description="NPC's job")
    dialogue_style: Optional[str] = Field(None, description="Way of speaking")

    # Item specific (Aligned with 'items' table)
    item_type: Optional[str] = Field(
        None, description="Item category (Weapon, Potion, etc.)"
    )
    grade: Optional[str] = Field(None, description="Item grade")
    base_price: Optional[int] = Field(None, description="Standard price")
    weight: Optional[int] = Field(None, description="Item weight")
    effect_value: Optional[int] = Field(
        None, description="Numerical effect (e.g. Damage, Healing)"
    )

    # Enemy specific (Aligned with 'enemies' table)
    enemy_type: Optional[str] = Field(None, description="Enemy race or class")
    base_difficulty: Optional[int] = Field(None, description="Difficulty level (1-20)")
    combat_description: Optional[str] = Field(None, description="Combat behavior")


class ActPlan(BaseModel):
    id: str = Field(..., description="Act ID")
    name: str = Field(..., description="Act Name")
    goal: str = Field(..., description="Act Goal")
    sequences: List[str] = Field(..., description="Sequence IDs in this act")


class PlannerOutput(BaseModel):
    acts: List[ActPlan]
    total_summary: str = Field(..., description="Scenario summary")


class SequenceDetail(BaseModel):
    id: str = Field(..., description="Sequence ID")
    name: str = Field(..., description="Sequence Name")
    sequence_type: str = Field(..., description="Type (Combat, Exploration, etc.)")
    location_name: str = Field(..., description="Location name")
    location_theme: str = Field(..., description="Location theme")
    location_description: str = Field(..., description="Location description")
    danger_min: int = Field(default=1, description="Minimum danger level (1-10)")
    danger_max: int = Field(default=10, description="Maximum danger level (1-10)")
    description: str = Field(..., description="Narrative description")
    goal: str = Field(..., description="Sequence goal")
    exit_triggers: List[str] = Field(..., description="Exit conditions")
    entities: List[EntityDetail] = Field(default_factory=list)


class WriterOutput(BaseModel):
    sequences: List[SequenceDetail]


class ReviewerOutput(BaseModel):
    is_consistent: bool
    reviews: List[str]
