import re
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, field_validator


class ScenarioInjectNPC(BaseModel):
    """NPC entity definition (Catalog)"""

    scenario_npc_id: str
    master_id: Optional[str] = None
    name: str
    description: str = ""
    tags: List[str] = []
    state: Dict[str, Any] = {}

    @field_validator("scenario_npc_id", mode="before")
    @classmethod
    def ensure_str_id(cls, v: Any) -> str:
        return str(v)


class ScenarioInjectItem(BaseModel):
    """Item entity definition - item_id is INT in catalog"""

    item_id: int
    master_id: Optional[str] = None
    name: str
    description: str = ""
    item_type: str = "misc"
    meta: Dict[str, Any] = {}

    @field_validator("item_id", mode="before")
    @classmethod
    def ensure_int_id(cls, v: Any) -> int:
        if isinstance(v, str):
            nums = re.findall(r"\d+", v)
            return int(nums[0]) if nums else 0
        return int(v)


class ScenarioInjectEnemy(BaseModel):
    """Enemy entity definition (Catalog)"""

    scenario_enemy_id: str
    master_id: Optional[str] = None
    name: str
    description: str = ""
    tags: List[str] = []
    state: Dict[str, Any] = {}
    dropped_items: List[int] = []

    @field_validator("scenario_enemy_id", mode="before")
    @classmethod
    def ensure_str_id(cls, v: Any) -> str:
        return str(v)

    @field_validator("dropped_items", mode="before")
    @classmethod
    def ensure_list_int(cls, v: Any) -> List[int]:
        if isinstance(v, list):
            res = []
            for i in v:
                if isinstance(i, str):
                    nums = re.findall(r"\d+", i)
                    if nums:
                        res.append(int(nums[0]))
                else:
                    res.append(int(i))
            return res
        return []


class ScenarioInjectRelation(BaseModel):
    """Global relations between entities"""

    from_id: str
    to_id: str
    relation_type: str = "neutral"
    affinity: int = 50
    meta: Dict[str, Any] = {}


class ActInject(BaseModel):
    """Act structure"""

    id: str
    name: str
    region_name: str
    region_description: str = ""
    goal: str
    exit_criteria: str
    sequences: List[str] = []


class SequenceInject(BaseModel):
    """Sequence structure - REFS ARE STRICT STRINGS"""

    id: str
    name: str
    sequence_type: str = "Exploration"
    location_name: str
    location_master_id: Optional[str] = None
    location_theme: str = ""
    location_description: str = ""
    danger_min: int = 1
    danger_max: int = 10
    description: str
    goal: str
    exit_triggers: List[str] = []
    npcs: List[str] = []
    enemies: List[str] = []
    items: List[str] = []


class ScenarioInjectSchema(BaseModel):
    """Final structure for State Manager (Flat & Strictly Typed)"""

    scenario_id: Optional[str] = None
    state_manager_id: Optional[str] = None
    title: str
    summary: str = ""
    description: str = ""
    difficulty: str = "normal"
    genre: str = "fantasy"
    tags: List[str] = []
    total_acts: int = 1
    acts: List[ActInject] = []
    sequences: List[SequenceInject] = []
    npcs: List[ScenarioInjectNPC] = []
    enemies: List[ScenarioInjectEnemy] = []
    items: List[ScenarioInjectItem] = []
    relations: List[ScenarioInjectRelation] = []


# --- Agent Generation Models (Restored with clear structure) ---


class ActPlan(BaseModel):
    id: str
    name: str
    region_name: str
    description: str
    goal: str
    exit_criteria: str
    sequences: List[str]


class EntityPlan(BaseModel):
    id: str
    name: str
    concept: str


class PlannerOutput(BaseModel):
    title: str
    description: str
    difficulty: str = "normal"
    genre: str = "fantasy"
    tags: List[str] = []
    total_acts: int
    acts: List[ActPlan]
    item_manifest: List[EntityPlan] = []
    npc_manifest: List[EntityPlan] = []
    enemy_manifest: List[EntityPlan] = []
    total_summary: str
    relations: List[ScenarioInjectRelation] = []


class AssetWriterOutput(BaseModel):
    items: List[Dict[str, Any]] = []
    npcs: List[Dict[str, Any]] = []
    enemies: List[Dict[str, Any]] = []


class ReviewerOutput(BaseModel):
    is_consistent: bool
    reviews: List[str]


class SequenceWriteDetail(BaseModel):
    id: str
    name: str
    sequence_type: str
    location_name: str
    location_theme: str
    location_description: str
    danger_min: int = 1
    danger_max: int = 10
    description: str
    goal: str
    exit_triggers: List[str]
    npcs: List[str]
    enemies: List[str]
    items: List[str]


class WriterOutput(BaseModel):
    sequences: List[SequenceWriteDetail]


class ValidationOutput(BaseModel):
    is_triggered: bool

    reason: str

    session_id: Optional[str] = None

    next_act_id: Optional[str] = None

    next_seq_id: Optional[str] = None

    suggested_narration: Optional[str] = None
