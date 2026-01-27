# 시나리오 생성 로직 설계서

본 문서는 GTRPGM 시나리오 서비스의 핵심 기능인 **멀티 에이전트 기반 시나리오 생성 및 그래프 DB 영속화** 로직을 기술한다.

## 1. 시스템 아키텍처 개요

본 서비스는 **Core-Plugin-Infrastructure** 계층 구조를 따르며, 관심사를 명확히 분리한다.

- **Core (핵심 로직)**: 도메인 모델(`Act`, `Sequence`), 에이전트 인터페이스, LangGraph 워크플로우 엔진.
- **Plugin (구현체)**: Core의 인터페이스를 실제 기술(PostgreSQL, LLM Gateway)로 구현한 어댑터 레이어.
- **Infrastructure (기술 드라이버)**: `asyncpg` 기반 DB 핸들러, 파일 기반 쿼리/프롬프트 로더 등 순수 기술 도구.

## 2. 멀티 에이전트 워크플로우 (LangGraph)

시나리오 생성은 세 단계의 에이전트가 협력하는 순환 구조로 이루어진다.

### 2.1 에이전트 구성
1.  **Planner (기획자)**: 사용자의 컨셉을 분석하여 전체 시나리오의 뼈대(Act)를 설계한다.
2.  **Writer (작가)**: 기획된 각 액트 내부의 세부 시퀀스(상세 묘사, 장소, 목표, 트리거)를 한국어로 집필한다.
3.  **Reviewer (검수자)**: 전체 시나리오의 논리적 개연성과 설정 충돌을 검토하며 루프(Loop)를 제어한다.

### 2.2 프로세스 흐름
1.  `Concept Input` -> **Planner** (Act/Sequence ID 기획)
2.  **Writer** (상세 데이터 집필 및 구조화)
3.  **Reviewer** (정합성 검사)
    - 충돌 발생 시: Planner 단계로 되돌아가 수정 (최대 3회 반복)
    - 통과 시: 최종 정형 데이터 확정

## 3. 데이터 모델링 및 구조화 (Structured Output)

LLM의 자연어 응답은 **Pydantic V2** 모델을 통해 즉시 정형 객체로 변환된다.

- `PlannerOutput`: 액트 목록 및 전체 시나리오 요약.
- `WriterOutput`: 장소명, 묘사, 목표, 종료 트리거가 포함된 시퀀스 상세 정보.
- `ReviewerOutput`: 검수 통과 여부 및 피드백 메시지.

## 4. 그래프 DB 영속화 (Apache AGE)

생성된 정형 데이터는 **Apache AGE**를 사용하여 그래프 구조로 저장된다. AGE의 안정성을 고려하여 **원자적 순차 저장(Atomic Sequential Persistence)** 방식을 채택한다.

### 4.1 그래프 계층 구조
- **Scenario Node**: 전체 시나리오의 루트.
- **Act Node**: 시나리오 하위의 서사적 장(Chapter). `[:HAS_ACT]` 관계로 연결.
- **Sequence Node**: 실제 플레이가 일어나는 의미 단위. `[:HAS_SEQUENCE]` 관계로 액트와 연결.
- **Location Node**: 시퀀스가 발생하는 물리적/논리적 공간. `[:LOCATED_AT]` 관계로 시퀀스와 연결.

### 4.2 영속화 단계
1.  **Root 생성**: `Scenario` 노드 생성.
2.  **Act 생성**: 루프를 돌며 각 `Act` 노드 생성 및 부모 연결.
3.  **Sequence/Location 생성**: 각 액트 내 시퀀스와 장소를 개별적으로 생성하여 관계 설정.

## 5. 실행 및 검증 로직

- **지연 연결(Lazy Connection)**: 서비스 기동 시 DB가 없어도 서버는 즉시 실행(Health Check 가능)되며, 실제 요청 시점에 DB 연결을 수행한다.
- **시각화 검증**: `scripts/view_scenario_graph.py`를 통해 저장된 그래프의 계층 구조를 트리 형태로 조회하여 데이터 무결성을 확인한다.
