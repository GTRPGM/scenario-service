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
  - Port: 8040 (Main Service)

---

## [Phase 0] Core Runtime (Scenario Manager) - Done

**목표**: 액션-시퀀스-액트 구조를 처리하는 핵심 엔진 및 DB 스키마 구축

### 1. 계층형 시나리오 데이터 모델링

- [x] **PostgreSQL/AGE 스키마 설계**
- [x] **데이터 접근 레이어**

---

## [Phase 1] Scenario Writer & Parsing - In Progress

**목표**: 자연어 초안으로부터 계층 구조를 가진 그래프 데이터 생성

### 1. 구조화된 시나리오 생성 (Writer)

- [x] **계층형 프롬프트 엔지니어링**
- [x] **LLM Gateway 연동**

### 2. 마스터 데이터 기반 정합성 강화 (Grounding) - Next

- [ ] **Rule Engine 검색 연동**
  - [ ] 시나리오 내 NPC, 아이템, 장소를 룰 엔진의 마스터 데이터와 매칭
  - [ ] `master_id` 부여 및 기존 속성 덮어쓰기 로직
- [ ] **하이브리드 생성 로직**
  - [ ] 유사도 기반 교체(Replace) 및 신규 생성(New) 비율 관리

---

## [Phase 2] Quality & Intelligence

**목표**: 서사적 완성도 및 동적 대응 강화

- [ ] **멀티 에이전트 서사 검토**
  - [ ] 인과관계 및 개연성 검토 에이전트 도입
- [ ] **고도화된 판정 제안**
  - [ ] 시나리오적 긴장감을 고려한 수치 보정 범위(Envelope) 제안 로직
- [ ] **운영 모니터링**
  - [ ] 세션별 시나리오 이행률 및 분기 통계 수집
