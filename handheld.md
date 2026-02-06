# Scenario Service Handheld Guide (Updated 2026-02-06)

## 1. 개요

GTRPGM 시나리오 서비스는 자연어 기획 초안을 바탕으로 구조화된 RPG 시나리오 데이터를 생성하고, **State Manager**의 규격에 맞춰 주입(Injection)하는 핵심 엔진입니다.

## 2. 생성 아키텍처 (Writer Graph)

시나리오는 LangGraph 기반의 파이프라인으로 생성되며, 최종적으로 `ScenarioEngine`에서 데이터 정규화 과정을 거칩니다.

### 데이터 흐름

1. **Planner**: 서사 구조 및 자산(NPC, Item, Enemy) 리스트 계획.
2. **Asset/Sequence Writer**: 상세 묘사 집필 및 자산 배치.
3. **Packaging (Engine)**: LLM의 불규칙한 데이터를 **State Manager 규격**으로 변환 및 ID 정규화.

## 3. 데이터 규격 및 ID 체계 (State Manager 호환)

### ID 정의 및 분리 규칙 (중요)

- **시나리오 식별자 (Scenario-specific ID)**:
  - NPC: `scenario_npc_id` (예: `"npc-1"`)
  - Enemy: `scenario_enemy_id` (예: `"enemy-1"`)
  - Item: `scenario_item_id` (예: `"item-101"`)
  - *모든 참조(Reference)는 이 시나리오 식별자를 사용하여 문자열로 이루어집니다.*
- **룰 식별자 (Rule Engine ID)**:
  - 필드명: `rule_id` (Integer)
  - 특징: 시나리오 식별자와는 **완전히 독립적**이며, 룰 엔진 자산과 매핑되지 않은 경우 반드시 **`null`**로 처리합니다.

### 엔티티별 핵심 스키마

| 엔티티 | 식별자 필드 | 룰 참조 필드 | 추가 필수 필드 |
| :--- | :--- | :--- | :--- |
| **NPC** | `scenario_npc_id` | `rule_id` (Optional) | `is_departed` (bool) |
| **Enemy** | `scenario_enemy_id` | `rule_id` (Optional) | `dropped_items` (List[int]) |
| **Item** | `scenario_item_id` | `rule_id` (Optional) | `item_type`, `meta` |

## 4. 데이터 정규화 로직 (ScenarioEngine)

### ID 클리닝 (`clean_id`)

- LLM이 생성한 `item-101`, `Item_101`, `101` 등을 모두 동일한 키로 인식하도록 접두어와 특수문자를 제거하여 정규화합니다.
- 정규화된 키를 기반으로 시퀀스와 관계도(Relations)의 참조 무결성을 보장합니다.

### 관계도(Relations) 매핑

- **NPC, 적, 아이템 간의 모든 조합**을 지원합니다. (예: NPC-NPC, NPC-Item)
- 모든 주체와 대상 ID는 최종적으로 시나리오 표준 ID(`npc-1`, `item-101` 등)로 치환되어 주입됩니다.

## 5. 테스트 및 스크립트

### 검증 도구

- **Unit Tests**: `uv run pytest` (37개 테스트를 통해 정합성 검증)
- **Integration Test**: `uv run python scripts/test_generation_integration.py` (실제 LLM 연동 및 스키마 호환성 체크)
- **JSON Export**: `uv run python scripts/export_injection_json.py` (임시 DB를 사용하여 실제 주입용 페이로드 생성)

## 6. 개발 원칙 (Rules)

1. **State Manager 우선**: 시나리오 서비스의 출력은 항상 `state-manager`의 수신 스키마 및 SQL 스키마와 일치해야 합니다.
2. **ID 독립성**: 시나리오 내부 식별자(문자열)에서 숫자를 추출하여 룰 ID로 사용하는 등의 유추 로직은 엄격히 금지합니다.
3. **Null-Safety**: 룰 엔진 데이터가 없는 경우 `0`이 아닌 `null`을 사용하여 명시적으로 미매핑 상태를 표현합니다.
