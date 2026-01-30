# GTRPGM 시나리오 시스템 연동 및 상태 관리 가이드 (Updated)

이 문서는 시나리오 서비스와 상태 관리자(State Manager) 간의 데이터 흐름, 상태 추적 방식, 그리고 **최신 시나리오 주입 규격(Scenario Injection Schema)**을 정의합니다.

---

## 1. 아키텍처 개요: 템플릿 vs 인스턴스

- **시나리오 서비스 (Template Store)**: 시나리오의 '설계도'를 관리합니다. 액트(지역), 시퀀스(지점), 엔티티 템플릿의 정적인 구조를 가집니다.
- **상태 관리자 (Session Instance)**: 실제 플레이 중인 '현재 상태'를 기록합니다. 특정 세션에서 어떤 액트와 시퀀스가 활성화되어 있는지, NPC의 현재 HP는 얼마인지 등을 추적합니다.

---

## 2. 시나리오 주입 스키마 (Injection Schema)

상태 관리자의 `POST /state/scenario/inject` 엔드포인트로 전달되는 데이터 구조입니다.
**Pydantic 모델 기반의 Flat 구조**를 가지며, ID 참조를 통해 관계를 맺습니다.

### 2.1 전체 구조 (JSON)

```json
{
  "title": "시나리오 제목",
  "description": "시나리오 전체 설명 (선택)",
  "acts": [ ... ],
  "sequences": [ ... ],
  "npcs": [ ... ],
  "enemies": [ ... ],
  "items": [ ... ],
  "relations": [ ... ]
}
```

### 2.2 상세 필드 명세

#### 1. Acts (Act: 대규모 지역/챕터)

| 필드명        | 타입         | 설명                                             |
| :------------ | :----------- | :----------------------------------------------- |
| `id`          | String       | 액트 식별자 (예: `act-1`)                        |
| `name`        | String       | 액트 이름 (예: `시작의 마을`)                    |
| `description` | String       | 액트 설명                                        |
| `sequences`   | List[String] | 소속된 시퀀스 ID 목록 (예: `["seq-1", "seq-2"]`) |

#### 2. Sequences (Sequence: 구체적 장소/장면)

| 필드명          | 타입         | 설명                                         |
| :-------------- | :----------- | :------------------------------------------- |
| `id`            | String       | 시퀀스 식별자 (예: `seq-1`)                  |
| `name`          | String       | 시퀀스 이름 (예: `주점 내부`)                |
| `location_name` | String       | 실제 장소명 (플레이어에게 보여질 이름)       |
| `description`   | String       | 장면/장소 묘사                               |
| `npcs`          | List[String] | 배치된 NPC ID 목록 (`scenario_npc_id` 참조)  |
| `enemies`       | List[String] | 배치된 적 ID 목록 (`scenario_enemy_id` 참조) |
| `items`         | List[String] | 배치된 아이템 ID 목록                        |

#### 3. Entities (NPC, Enemy, Item)

엔티티들은 시퀀스 내부에 중첩되지 않고, 최상위 리스트에 정의된 후 참조됩니다.

- **NPC (`npcs`)**
  - `scenario_npc_id`: 고유 식별자 (예: `npc-merchant`)
  - `name`: 이름
  - `state`: 초기 상태 (예: `{"numeric": {"HP": 100}}`)

- **Enemy (`enemies`)**
  - `scenario_enemy_id`: 고유 식별자
  - `state`: 초기 상태 (HP, 공격력 등)

### 2.3 예시 데이터 (Payload Example)

```json
{
  "title": "어둠의 숲 탐험",
  "description": "초보 모험가를 위한 튜토리얼 시나리오",
  "acts": [
    {
      "id": "act-1",
      "name": "시작의 마을",
      "description": "평화로운 마을입니다.",
      "sequences": ["seq-tavern", "seq-square"]
    }
  ],
  "sequences": [
    {
      "id": "seq-tavern",
      "name": "낡은 주점",
      "location_name": "달빛 주점",
      "description": "시끌벅적한 모험가들의 쉼터입니다.",
      "npcs": ["npc-barkeep"],
      "enemies": [],
      "items": ["item-beer"],
      "exit_triggers": ["광장으로 이동"]
    },
    {
      "id": "seq-square",
      "name": "마을 광장",
      "location_name": "중앙 광장",
      "description": "분수대가 있는 넓은 광장입니다.",
      "npcs": [],
      "enemies": ["enemy-rat"],
      "items": []
    }
  ],
  "npcs": [
    {
      "scenario_npc_id": "npc-barkeep",
      "name": "주점 주인",
      "description": "친절하지만 외상값엔 엄격합니다.",
      "state": {
        "numeric": { "HP": 100, "affinity": 50 }
      }
    }
  ],
  "enemies": [
    {
      "scenario_enemy_id": "enemy-rat",
      "name": "거대 쥐",
      "state": {
        "numeric": { "HP": 30, "ATK": 5 }
      }
    }
  ],
  "items": [
    {
      "item_id": "item-beer",
      "name": "시원한 맥주",
      "item_type": "consumable",
      "meta": { "heal": 5 }
    }
  ]
}
```

---

## 3. 상태 추적 및 조회 프로세스

상태 관리자는 세션별로 다음 정보를 실시간으로 추적하고 조회 가능해야 합니다.

### 3.1 세션 상태 추적 (State Manager의 역할)

세션 테이블(`sessions`)은 다음의 외래키를 통해 시나리오 진행도를 관리합니다.

- `current_act`: 현재 진행 중인 Act 번호 (순서).
- `current_sequence`: 현재 진행 중인 Sequence 번호 (순서).
- `current_act_id`: (Optional) 현재 Act의 String ID.
- `current_sequence_id`: (Optional) 현재 Sequence의 String ID.

### 3.2 상태 조회 흐름

사용자나 GM 서비스가 "지금 어디야?" (`GET /state/session/{session_id}/location`)라고 물으면 상태 관리자는 다음을 반환합니다.

1. `session.location`: 현재 세션에 기록된 장소명.
2. `current_sequence` 정보를 기반으로 해당 시퀀스에 소속된 엔티티(`npcs`, `enemies`)들의 **현재(Deep Copied)** 상태값을 `GET /state/session/{session_id}/npcs` 등으로 조회 가능.

---

## 4. 시나리오 전이(Transition) 동작 과정

플레이어의 행동에 따라 상태가 변하는 표준 워크플로우입니다.

1. **사용자 입력**: 플레이어가 "주점에서 나와서 광장으로 갈래"라고 입력.
2. **판정 (GM/LLM)**: LLM이 입력을 분석하여 다음 시퀀스가 `seq-square`임을 판단.
3. **상태 업데이트 (GM → State Manager)**:
   - 호출: `PUT /state/session/{session_id}/sequence`
   - 전달: `{ "new_sequence": 2 }` (또는 ID 기반 매핑 로직 사용)
   - 호출: `PUT /state/session/{session_id}/location`
   - 전달: `{ "new_location": "중앙 광장" }`
4. **결과 반영**: 상태 관리자는 DB 내의 `current_sequence`와 `location`을 업데이트하고, 해당 장소에 맞는 NPC/적 리스트를 활성화합니다.
