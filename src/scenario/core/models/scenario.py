from dataclasses import dataclass, field
from typing import Dict, List
from uuid import UUID


@dataclass(frozen=True)
class EntityTemplate:
    id: str
    name: str
    entity_type: str
    metadata: Dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class Location:
    id: str
    name: str
    description: str


@dataclass(frozen=True)
class Sequence:
    id: str
    name: str
    sequence_type: str
    goal: str
    exit_triggers: List[str]
    location_id: str
    involved_entities: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class Act:
    id: str
    name: str
    order: int
    goal: str
    transition_condition: str
    sequences: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class ScenarioGraph:
    scenario_id: UUID
    acts: List[Act]
    sequences: List[Sequence]
    locations: List[Location]
    entities: List[EntityTemplate]
