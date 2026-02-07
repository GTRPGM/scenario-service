from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ScenarioInjectNPC(BaseModel):
    """NPC entity definition (Catalog)"""

    scenario_npc_id: str
    rule_id: int = 0
    name: str
    description: str = ""
    tags: List[str] = Field(default_factory=list)
    state: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    @field_validator("scenario_npc_id", mode="before")
    @classmethod
    def ensure_str_id(cls, v: Any) -> str:
        return str(v)

    @field_validator("rule_id", mode="before")
    @classmethod
    def coerce_rule_id(cls, v: Any) -> int:
        if isinstance(v, int):
            return v
        if v is None:
            return 0
        text = str(v).strip()
        if text == "":
            return 0
        if text.isdigit():
            return int(text)
        digits = "".join(ch for ch in text if ch.isdigit())
        return int(digits) if digits else 0

    @model_validator(mode="before")
    @classmethod
    def alias_legacy_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "rule_id" not in data and data.get("master_id") is not None:
                data["rule_id"] = data.get("master_id")
        return data


class ScenarioInjectItem(BaseModel):
    """Item entity definition"""

    scenario_item_id: str
    rule_id: int = 0
    name: str
    description: str = ""
    item_type: str = "misc"
    meta: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    @field_validator("scenario_item_id", mode="before")
    @classmethod
    def ensure_item_id_str(cls, v: Any) -> str:
        return str(v)

    @field_validator("rule_id", mode="before")
    @classmethod
    def coerce_rule_id(cls, v: Any) -> int:
        if isinstance(v, int):
            return v
        if v is None:
            return 0
        text = str(v).strip()
        if text == "":
            return 0
        if text.isdigit():
            return int(text)
        digits = "".join(ch for ch in text if ch.isdigit())
        return int(digits) if digits else 0

    @model_validator(mode="before")
    @classmethod
    def alias_legacy_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "scenario_item_id" not in data and data.get("item_id") is not None:
                data["scenario_item_id"] = data.get("item_id")
            if "rule_id" not in data and data.get("master_id") is not None:
                data["rule_id"] = data.get("master_id")
        return data


class ScenarioInjectEnemy(BaseModel):
    """Enemy entity definition (Catalog)"""

    scenario_enemy_id: str
    rule_id: int = 0
    name: str
    description: str = ""
    tags: List[str] = Field(default_factory=list)
    state: Dict[str, Any] = Field(default_factory=dict)
    dropped_items: List[str] = Field(default_factory=list)

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    @field_validator("scenario_enemy_id", mode="before")
    @classmethod
    def ensure_str_id(cls, v: Any) -> str:
        return str(v)

    @field_validator("rule_id", mode="before")
    @classmethod
    def coerce_rule_id(cls, v: Any) -> int:
        if isinstance(v, int):
            return v
        if v is None:
            return 0
        text = str(v).strip()
        if text == "":
            return 0
        if text.isdigit():
            return int(text)
        digits = "".join(ch for ch in text if ch.isdigit())
        return int(digits) if digits else 0

    @model_validator(mode="before")
    @classmethod
    def alias_legacy_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "rule_id" not in data and data.get("master_id") is not None:
                data["rule_id"] = data.get("master_id")
        return data


class ScenarioInjectRelation(BaseModel):
    """Global relations between entities"""

    from_id: str
    to_id: str
    relation_type: str = "neutral"
    affinity: int = 50
    meta: Dict[str, Any] = Field(default_factory=dict)


class ActInject(BaseModel):
    """Act structure matching state-manager ScenarioActInject"""

    id: str
    name: str
    region_name: str
    region_description: str = ""
    description: Optional[str] = None
    goal: str
    exit_criteria: str
    sequences: List[str] = Field(default_factory=list)


class SequenceInject(BaseModel):
    """Sequence structure matching state-manager ScenarioSequenceInject"""

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
    exit_triggers: List[str] = Field(default_factory=list)
    npcs: List[str] = Field(default_factory=list)
    enemies: List[str] = Field(default_factory=list)
    items: List[str] = Field(default_factory=list)


class ScenarioInjectSchema(BaseModel):
    """Final structure for State Manager (Matches ScenarioInjectRequest)"""

    scenario_id: Optional[str] = None
    title: str
    summary: str = ""
    description: Optional[str] = None
    difficulty: str = "normal"
    genre: str = "fantasy"
    tags: List[str] = Field(default_factory=list)
    total_acts: int = 1
    acts: List[ActInject] = Field(default_factory=list)
    sequences: List[SequenceInject] = Field(default_factory=list)
    npcs: List[ScenarioInjectNPC] = Field(default_factory=list)
    enemies: List[ScenarioInjectEnemy] = Field(default_factory=list)
    items: List[ScenarioInjectItem] = Field(default_factory=list)
    relations: List[ScenarioInjectRelation] = Field(default_factory=list)


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
    concept: str = ""

    @field_validator("id", mode="before")
    @classmethod
    def extract_id(cls, v: Any, info: Any) -> str:
        if isinstance(v, str):
            return v
        if isinstance(v, dict):
            # LLM이 객체 전체를 id 자리에 넣었을 경우를 대비
            return str(
                v.get("id")
                or v.get("scenario_npc_id")
                or v.get("scenario_enemy_id")
                or v.get("scenario_item_id")
                or ""
            )
        return str(v)

    @model_validator(mode="before")
    @classmethod
    def alias_ids(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # id 필드가 없고 다른 명칭이 있는 경우 복사
            if "id" not in data:
                val = (
                    data.get("scenario_npc_id")
                    or data.get("scenario_enemy_id")
                    or data.get("scenario_item_id")
                )
                if val:
                    data["id"] = val
        return data


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

    should_end: bool = False

    suggested_narration: Optional[str] = None
