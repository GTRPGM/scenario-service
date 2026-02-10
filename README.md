# Scenario Service (시나리오 서비스)

## 📖 개요 (Overview)

**Scenario Service**는 LLM 기반의 에이전트 파이프라인을 통해 게임의 시나리오(Act, Sequence)를 자동으로 생성하고 검증하는 서비스입니다.  
사용자가 입력한 모호한 개념(Concept)을 구체적인 게임 구조(Act-Sequence-Entity)로 변환하며, 자체적인 리뷰 및 수정 루프를 통해 논리적 완결성을 확보합니다.

## 🏗️ 아키텍처 및 기술 스택 (Architecture & Tech Stack)

### 기술 스택 (Tech Stack)

- **Language**: Python 3.11+
- **Framework**: FastAPI
- **LLM Orchestration**: LangChain, LangGraph
- **Database**: PostgreSQL (AsyncPG)
- **Key Libraries**: Pydantic

### 주요 아키텍처 (Core Architecture)

이 서비스는 **LangGraph**를 활용한 상태 머신(`ScenarioWriterGraph`)으로 구현되어 있습니다.

#### 1. 에이전트 (Agents)

각 단계별로 전문화된 에이전트가 협업합니다.

- **Planner (기획자)**: 전체적인 Act와 Sequence 구조를 설계하고, 목표(Goal)와 종료 조건(Exit Criteria)을 정의합니다.
- **Asset Writer (설정 담당)**: 시나리오에 필요한 NPC, 적(Enemy), 아이템(Item)의 명세(Manifest)를 생성합니다.
- **Writer (작가)**: 기획된 구조와 자산을 바탕으로 각 시퀀스의 구체적인 내용과 배치(Entity Placement)를 작성합니다.
- **Reviewer (검수자)**: 생성된 시나리오의 정합성(Entity 참조 오류, 필수 필드 누락, 최소 수량 등)을 검사하고 피드백을 제공합니다.

#### 2. 상태 전이 및 워크플로우 (Workflow)

그래프는 다음과 같은 순환 구조를 가집니다:

1. **Planner**: 시나리오 개요 수립
2. **Writer**: 시퀀스 상세 작성
3. **Asset Writer**: 자산 생성 (시퀀스 맥락 반영)
4. **Grounder**: 데이터 정규화
5. **Reviewer**: 결함 검사
   - **Pass**: 종료
   - **Fail**: 피드백과 함께 **Planner**로 회귀 (최대 3회 반복)

## 💡 주요 로직 및 설계 중점 (Key Logic & Design Focus)

### 1. 자가 수정 루프 (Self-Correction Loop)

LLM이 생성한 결과물이 게임 로직에 위배될 경우(예: 존재하지 않는 NPC ID 참조, 적이 없는 전투 시퀀스 등), **Reviewer** 노드가 이를 감지하여 구체적인 피드백을 생성합니다. 이 피드백은 다시 Planner와 Writer에게 전달되어 시나리오를 수정하게 만듭니다.

### 2. 엔티티 최소 수량 보장

게임의 재미와 상호작용을 위해 Writer 단계에서 강제적인 로직이 적용됩니다:

- 모든 시퀀스는 최소 1명 이상의 상호작용 대상(**NPC 또는 Enemy**)을 포함해야 합니다.
- `Combat` 시퀀스는 반드시 1명 이상의 적(**Enemy**)을 포함해야 합니다.
- 전체 시나리오는 최소 4종 이상의 NPC/Enemy/Item을 포함하도록 유도합니다.

### 3. 구조적 정합성 (Structural Integrity)

생성된 JSON 데이터는 State Manager가 즉시 로드하여 사용할 수 있도록 엄격한 스키마(Schema)를 준수합니다.
