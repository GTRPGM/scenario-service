# 시나리오 서비스 개발 계획

## 목적

> GTRPGM 프로젝트의 시나리오 서비스(Scenario Manager & Writer) 구현

- 액션-시퀀스-액트 계층 구조 기반의 시나리오 관리
- GM 서비스에 대한 정합성 가드 및 제안(Proposal) 제공
- LLM 기반 시나리오 생성 및 구조화된 그래프 데이터 변환

## 현황

- **단계**: 프로젝트 초기화 및 계층 구조 설계 단계
- **환경**:
  - Language: Python 3.11+
  - Package Manager: uv
  - Frameworks: FastAPI, LangChain Core
  - Database: PostgreSQL (with Apache AGE)

---

## [Phase 0] Core Runtime (Scenario Manager)

**목표**: 액션-시퀀스-액트 구조를 처리하는 핵심 엔진 및 DB 스키마 구축

### 1. 계층형 시나리오 데이터 모델링

- [x] **PostgreSQL/AGE 스키마 설계**
  - [x] `Act`, `Sequence`, `Location`, `Entity` 도메인 모델 정의

  - [x] 관계형 DB 초기 스키마 및 쿼리 관리 체계(QueryLoader) 구축

- [x] **데이터 접근 레이어**
  - [x] `asyncpg` 기반의 비동기 DatabaseHandler 구현 및 Apache AGE 연동

### 2. GM 인터페이스 및 비즈니스 로직

- [x] **정합성 판정 (Consistency Check)**
  - [x] 현재 상태 및 자연어 전이 조건을 반환하는 `check_progression` 인터페이스 설계

- [x] **진행 관리 (Progression)**
  - [x] 시퀀스 종료 및 액트 전환(Transition) 비동기 처리 로직 구현

- [x] **API 서버 구현**
  - [x] FastAPI 기반 GM 연동 엔드포인트(`check`, `transition`) 구현

---

## [Phase 1] Scenario Writer & Parsing

**목표**: 자연어 초안으로부터 계층 구조를 가진 그래프 데이터 생성

### 1. 구조화된 시나리오 생성 (Writer)

- [ ] **계층형 프롬프트 엔지니어링**
  - [ ] 액트 단위 기획 -> 시퀀스 분할 -> 세부 노드 구성의 단계적 생성 루프
  - [ ] 각 시퀀스별 서술 슬롯(Narrative Slots) 추출 로직
- [ ] **LLM Gateway 연동**

### 2. 그래프 변환 및 검증 (Parser)

- [ ] **구조화 파서**
  - [ ] LLM 출력(JSON/Markdown)을 `Act-Sequence-Location` 그래프로 변환
- [ ] **논리 검증기**
  - [ ] 끊어진 경로 또는 도달 불가능한 시퀀스 종료 조건 체크

---

## [Phase 2] Quality & Intelligence

**목표**: 서사적 완성도 및 동적 대응 강화

- [ ] **멀티 에이전트 서사 검토**
  - [ ] 인과관계 및 개연성 검토 에이전트 도입
- [ ] **고도화된 판정 제안**
  - [ ] 시나리오적 긴장감을 고려한 수치 보정 범위(Envelope) 제안 로직
- [ ] **운영 모니터링**
  - [ ] 세션별 시나리오 이행률 및 분기 통계 수집
