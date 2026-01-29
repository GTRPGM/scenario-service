# Scenario Injection Guide (Hand-held)

This document provides the Pydantic model structures and JSON examples required to inject a new scenario into the GTRPGM State Manager, including Apache AGE graph relations.

## Endpoint
- **POST** `/state/scenario/inject`

## 1. Data Structure (Pydantic Models)

```python
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class ScenarioInjectNPC(BaseModel):
    """NPC Template Data"""
    scenario_npc_id: str = Field(..., description="Unique ID within the scenario (e.g., 'npc-001')")
    name: str = Field(..., description="NPC Name")
    description: str = Field("", description="Brief biography or role")
    tags: List[str] = Field(default=["npc"], description="Searchable tags")
    state: Dict[str, Any] = Field(
        default={
            "numeric": {"HP": 100, "MP": 50, "SAN": 10},
            "boolean": {}
        },
        description="Initial stats and flags"
    )

class ScenarioInjectEnemy(BaseModel):
    """Enemy Template Data"""
    scenario_enemy_id: str = Field(..., description="Unique ID within the scenario (e.g., 'goblin-01')")
    name: str = Field(..., description="Enemy Name")
    description: str = Field("", description="Lore or combat style")
    tags: List[str] = Field(default=["enemy"], description="Category tags")
    state: Dict[str, Any] = Field(
        default={
            "numeric": {"HP": 100, "MP": 0},
            "boolean": {}
        },
        description="Combat stats"
    )
    dropped_items: List[str] = Field(default_factory=list, description="List of Master Item IDs (UUID)")

class ScenarioInjectItem(BaseModel):
    """Item Template Data"""
    item_id: str = Field(..., description="Fixed UUID for the Master Item")
    name: str = Field(..., description="Item Name")
    description: str = Field("", description="Function or flavor text")
    item_type: str = Field("misc", description="consumable, equipment, material, etc.")
    meta: Dict[str, Any] = Field(default_factory=dict, description="Custom properties like weight, price, etc.")

class ScenarioInjectRelation(BaseModel):
    """Relation (Edge) between Entities (Apache AGE)"""
    from_id: str = Field(..., description="scenario_npc_id or scenario_enemy_id of the source")
    to_id: str = Field(..., description="scenario_npc_id or scenario_enemy_id of the target")
    relation_type: str = Field("neutral", description="friend, foe, rival, etc.")
    affinity: int = Field(50, ge=0, le=100)
    meta: Dict[str, Any] = Field(default_factory=dict)

class ScenarioInjectRequest(BaseModel):
    """Top-level Injection Request"""
    title: str = Field(..., description="Scenario Title")
    description: Optional[str] = Field(None, description="Long summary of the scenario")
    author: Optional[str] = Field(None, description="Author's name or ID")
    version: str = Field("1.0.0", description="Semantic versioning")
    difficulty: str = Field("normal", description="easy, normal, hard, nightmare")
    genre: Optional[str] = Field(None, description="fantasy, sci-fi, horror, etc.")
    tags: List[str] = Field(default_factory=list, description="Scenario-level tags")
    total_acts: int = Field(3, description="Number of Acts in this scenario", ge=1)

    npcs: List[ScenarioInjectNPC] = Field(default_factory=list)
    enemies: List[ScenarioInjectEnemy] = Field(default_factory=list)
    items: List[ScenarioInjectItem] = Field(default_factory=list)
    relations: List[ScenarioInjectRelation] = Field(default_factory=list)
```

## 2. Complete JSON Example

```json
{
  "title": "The Whispering Caves",
  "description": "A deep dive into the forgotten mines of Moria.",
  "author": "Legendary DM",
  "version": "1.2.0",
  "difficulty": "hard",
  "genre": "dark-fantasy",
  "tags": ["dungeon-crawl", "mystery"],
  "total_acts": 3,
  "items": [
    {
      "item_id": "550e8400-e29b-41d4-a716-446655440001",
      "name": "Dim-lit Lantern",
      "description": "A lantern that flickers when spirits are near.",
      "item_type": "equipment",
      "meta": {"range": 10, "fuel": 100}
    }
  ],
  "npcs": [
    {
      "scenario_npc_id": "npc-guide-01",
      "name": "Eldrin the Wise",
      "description": "An old dwarf who knows the cave's secrets.",
      "tags": ["guide", "merchant"],
      "state": {
        "numeric": {"HP": 80, "MP": 200, "SAN": 100},
        "boolean": {"is_immortal": false}
      }
    }
  ],
  "enemies": [
    {
      "scenario_enemy_id": "mob-shadow-stalker",
      "name": "Shadow Stalker",
      "description": "A creature that merges with the cave walls.",
      "tags": ["undead", "stealth"],
      "state": {
        "numeric": {"HP": 120, "MP": 0},
        "boolean": {"can_fly": false}
      },
      "dropped_items": ["550e8400-e29b-41d4-a716-446655440001"]
    }
  ],
  "relations": [
    {
      "from_id": "npc-guide-01",
      "to_id": "mob-shadow-stalker",
      "relation_type": "hostile",
      "affinity": 0,
      "meta": {"reason": "Ancient grudge"}
    }
  ]
}
```

## 3. Important Notes
1. **Session 0**: All data injected via this API will be assigned to `session_id = '00000000-0000-0000-0000-000000000000'`.
2. **Auto-Cloning**: When a real session starts, all NPCs, Enemies, Items, and **Apache AGE Relations** will be automatically deep-copied into the new session.
3. **Graph Labels**: Entities are labeled as `:npc` or `:enemy` in Apache AGE. Edges are labeled as `:RELATION`.
