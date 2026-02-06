# 시나리오 서비스 개발 계획

## 목적

> GTRPGM 프로젝트의 시나리오 서비스(Scenario Manager & Writer) 구현

- 액션-시퀀스-액트 계층 구조 기반의 시나리오 관리
- GM 서비스에 대한 정합성 가드 및 제안(Proposal) 제공
- LLM 기반 시나리오 생성 및 구조화된 그래프 데이터 변환

## 현황

- **단계**: Phase 1 진행 중 (Scenario Writer 연동 및 환경 최적화)
- **이슈**:
  - `pytest`가 모킹된 데이터로만 성공하고 실제 LLM/DB 연동 시의 데이터 정합성을 잡지 못함 (conftest.py에서 Engine이 통째로 모킹됨)
  - `ScenarioEngine._package_scenario`에서 `relations`의 ID를 클리닝하지 않아 그래프 DB 저장 시 노드 매칭 실패 (npc-01 vs 01)
  - `planner.txt`에서 생성된 ID와 `AssetWriter`가 정규화한 ID 간의 불일치 가능성
  - **[CRITICAL]** 시나리오 저장 시 Apache AGE Cypher 쿼리에서 `Scenario ID`로 앵커링(Anchoring)하지 않아, 기존에 저장된 모든 시나리오의 노드들과 매칭되어 기하급수적으로 관계(Relation) 및 노드가 생성되는 문제 발견 (디스크 급증 및 프로세스 다운의 원인)
- **조치**:
  - `ScenarioEngine`의 패키징 로직 보완 (Relation ID 클리닝 추가)
  - ID 정문화 규칙을 `_clean_id` 유틸리티로 통합 및 강화
  - 테스트 코드에서 실제 엔진 로직을 검증할 수 있도록 모킹 범위 조정
  - **[FIX]** 모든 Cypher 쿼리에 `scenario_id` 기반의 매칭 가드 추가하여 현재 시나리오 범위 내에서만 노드 매칭 및 생성되도록 수정

---

## [Phase 1] Scenario Writer & Parsing - In Progress

**목표**: 자연어 초안으로부터 계층 구조를 가진 그래프 데이터 생성

### 1. 구조화된 시나리오 생성 (Writer)

- [x] **계층형 프롬프트 엔지니어링**
- [x] **LLM Gateway 연동**
- [x] **ID 정합성 및 패키징 로직 수정 (Done)**
  - [x] Relation 및 Act 내 ID 참조 클리닝 로직 추가
  - [x] Item ID의 정수/문자열 변환 일관성 확보
  - [x] API 엔드포인트용 핵심 엔진 메서드 구현

### 2. 마스터 데이터 기반 정합성 강화 (Grounding) - Next

- [ ] **Rule Engine 검색 연동**
  - [ ] 시나리오 내 NPC, 아이템, 장소를 룰 엔진의 마스터 데이터와 매칭
  - [ ] `master_id` 부여 및 기존 속성 덮어쓰기 로직
- [ ] **하이브리드 생성 로직**
  - [ ] 유사도 기반 교체(Replace) 및 신규 생성(New) 비율 관리

---

## [Phase 2] Quality & Intelligence

**목표**: 서사적 완성도 및 동적 대응 강화

### 1. 시나리오 진행 검증 (Check) - In Progress

- [x] **GM 통신 정합성 강화**
  - [x] `ValidationOutput` 모델에 `session_id` 필드 추가
  - [x] `SessionCheckRequest`에 `scenario_id` 추가하여 GM 요청 구조와 일치
  - [x] `session_id` 기반 세션 상태(Act, Sequence) 자동 조회 로직 보완
  - [ ] `scenario_id` 조회 시 내부 ID와 State Manager ID 동시 지원 로직 강화
- [ ] **멀티 에이전트 서사 검토**
  - [ ] 인과관계 및 개연성 검토 에이전트 도입
