"""
Scenario Injection Models Reference
This file contains the Pydantic model definitions for scenario injection.
Matches state-manager's ScenarioInjectRequest.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ScenarioActInject(BaseModel):
    """시나리오 주입용 Act 정보"""

    id: str = Field(..., description="액트 식별자 (예: act-1)")
    name: str = Field(..., description="액트 이름")
    description: Optional[str] = Field(default=None, description="액트 설명")
    exit_criteria: Optional[str] = Field(default=None, description="탈출 조건")
    sequences: List[str] = Field(
        default_factory=list, description="소속 시퀀스 ID 리스트"
    )


class ScenarioInjectNPC(BaseModel):
    """주입용 NPC 정보"""

    scenario_npc_id: str = Field(..., description="NPC 식별자 (예: npc-elder)")
    rule_id: Optional[int] = Field(default=None, description="Rule Engine ID")
    name: str = Field(..., description="NPC 이름")
    description: str = Field(default="", description="NPC 설명")
    tags: List[str] = Field(default_factory=list, description="태그")
    state: Dict[str, Any] = Field(default_factory=dict, description="상태 데이터")
    is_departed: bool = Field(default=False, description="퇴장 여부")


class ScenarioInjectEnemy(BaseModel):
    """주입용 적 정보"""

    scenario_enemy_id: str = Field(..., description="적 식별자 (예: enemy-goblin)")
    rule_id: Optional[int] = Field(default=None, description="Rule Engine ID")
    name: str = Field(..., description="적 이름")
    description: str = Field(default="", description="적 설명")
    tags: List[str] = Field(default_factory=list, description="태그")
    state: Dict[str, Any] = Field(default_factory=dict, description="상태")
    dropped_items: List[int] = Field(
        default_factory=list, description="드롭 아이템 Rule ID 리스트"
    )


class ScenarioInjectItem(BaseModel):
    """주입용 아이템 정보"""

    scenario_item_id: str = Field(..., description="아이템 식별자 (예: item-potion)")
    rule_id: Optional[int] = Field(default=None, description="아이템 Rule ID")
    name: str = Field(..., description="아이템 이름")
    description: str = Field(default="", description="아이템 설명")
    item_type: str = Field(default="misc", description="아이템 타입")
    meta: Dict[str, Any] = Field(default_factory=dict, description="추가 메타데이터")


class ScenarioInjectRelation(BaseModel):
    """주입용 관계 정보"""

    from_id: str = Field(..., description="관계 시작 엔티티 ID")
    to_id: str = Field(..., description="관계 대상 엔티티 ID")
    relation_type: str = Field(default="neutral", description="관계 타입")
    affinity: int = Field(default=50, description="호감도 (0-100)")
    meta: Dict[str, Any] = Field(default_factory=dict, description="추가 메타데이터")


class ScenarioSequenceInject(BaseModel):
    """시나리오 주입용 Sequence 정보"""

    id: str = Field(..., description="시퀀스 식별자 (예: seq-1)")
    name: str = Field(..., description="시퀀스 이름")
    location_name: Optional[str] = Field(default=None, description="위치명")
    description: Optional[str] = Field(default=None, description="시퀀스 설명")
    goal: Optional[str] = Field(default=None, description="목표")
    exit_triggers: List[str] = Field(default_factory=list, description="탈출/전환 조건")
    npcs: List[str] = Field(default_factory=list, description="소속 NPC ID 리스트")
    enemies: List[str] = Field(default_factory=list, description="소속 적 ID 리스트")
    items: List[str] = Field(default_factory=list, description="소속 아이템 ID 리스트")


class ScenarioInjectRequest(BaseModel):
    """최종 시나리오 주입 규격"""

    scenario_id: Optional[str] = Field(
        default=None, description="기존 시나리오 업데이트 시 UUID"
    )
    title: str = Field(..., description="시나리오 제목")
    description: Optional[str] = Field(default=None, description="시나리오 설명")
    acts: List[ScenarioActInject] = Field(default_factory=list, description="Act 목록")
    sequences: List[ScenarioSequenceInject] = Field(
        default_factory=list, description="Sequence 목록"
    )
    npcs: List[ScenarioInjectNPC] = Field(default_factory=list, description="NPC 목록")
    enemies: List[ScenarioInjectEnemy] = Field(
        default_factory=list, description="Enemy 목록"
    )
    items: List[ScenarioInjectItem] = Field(
        default_factory=list, description="Item 목록"
    )
    relations: List[ScenarioInjectRelation] = Field(
        default_factory=list, description="관계 목록"
    )
