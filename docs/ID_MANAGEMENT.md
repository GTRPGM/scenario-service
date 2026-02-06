# 시나리오 ID 관리 체계 (Scenario ID Management)

이 문서는 시나리오 서비스 내에서 생성되는 시나리오와 그 하위 요소들의 식별자(ID) 관리 규칙 및 외부 서비스(State Manager)와의 연동 방식을 설명합니다.

---

## 1. 시나리오 고유 식별자 (System UUID)

시나리오가 생성되어 DB에 저장될 때 부여되는 최상위 고유 식별자입니다.

- **형식**: UUID v4 (예: `550e8400-e29b-41d4-a716-446655440000`)
- **생성 시점**: 시나리오 생성(Generation) 완료 후 DB 저장 단계
- **역할**:
  - 시나리오 서비스 데이터베이스(PostgreSQL/AGE) 내의 Primary Key
  - 시나리오 목록 조회 및 상세 정보 추출을 위한 고유 키

---

## 2. 내부 구성 요소 식별자 (Canonical ID)

하나의 시나리오 내부 구조를 정의하는 세부 요소들은 사람이 읽기 쉽고 구조적으로 일관된 'Canonical ID' 형식을 사용합니다.

### ID 명명 규칙

시나리오 서비스의 `ScenarioEngine`에서 패키징 시점에 부여됩니다.

| 요소 구분 | ID 형식 | 예시 | 비고 |
| :--- | :--- | :--- | :--- |
| **막 (Act)** | `act-{n}` | `act-1`, `act-2` | 시나리오 진행 순서에 따른 번호 부여 |
| **시퀀스 (Sequence)** | `seq-{n}` | `seq-1`, `seq-2` | 전체 시나리오 내 시퀀스 순서대로 부여 |
| **NPC** | `npc-{n}` | `npc-1`, `npc-2` | 등장 NPC 카탈로그 순서 |
| **적 (Enemy)** | `enemy-{n}` | `enemy-1`, `enemy-2` | 등장 적 카탈로그 순서 |
| **아이템 (Item)** | `item-{n}` | `item-101`, `item-102` | 기본 101번부터 시작하여 부여 |

- **장점**: 서비스 간 데이터 전송 시 참조 관계를 명확하게 유지하며, 로그 분석 및 디버깅 시 가독성이 높습니다.

---

## 3. 외부 서비스 연동 식별자 (Mapping)

시나리오가 실제 게임 엔진인 **State Manager**에 주입(Inject)될 때, 두 서비스 간의 상호 참조를 위한 매핑이 이루어집니다.

### State Manager ID

- **발급 주체**: State Manager
- **특징**: State Manager의 자체 데이터베이스 규격에 따라 새로 생성되는 ID입니다.
- **저장**: 시나리오 서비스는 주입 성공 후 반환받은 ID를 `state_manager_id` 컬럼에 기록하여 관리합니다.

### ID 보존 규칙 (Structural Consistency)

- 시나리오의 루트 ID는 서비스별로 각자 생성하지만, **내부 구성 요소의 Canonical ID(`npc-1`, `seq-1` 등)는 그대로 유지**됩니다.
- 스테이트 매니저는 주입된 페이로드의 ID를 `scenario_npc_id` 등의 컬럼에 그대로 저장하여, 시나리오 서비스에서 정의한 참조 구조를 깨뜨리지 않습니다.

---

## 4. ID 추적 워크플로우 (Summary)

1. **Generation**: LLM을 통해 시나리오 데이터 생성.
2. **Packaging**: `ScenarioEngine`이 내부 요소들에 `act-1`, `npc-1` 등 **Canonical ID** 부여.
3. **Internal Save**: 시나리오 서비스 DB에 고유 **UUID**와 함께 저장.
4. **Injection**: State Manager API 호출 (페이로드에 Canonical ID 구조 포함).
5. **Mapping**: State Manager가 생성한 **자체 ID**를 응답받아 시나리오 서비스 DB의 `state_manager_id` 필드 업데이트.

---

### 최종 갱신일

2026-02-06
