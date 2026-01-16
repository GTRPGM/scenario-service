# 계획

## 목적

> GTRPGM 프로젝트의 Scenario Writer 서비스를 구현

- 룰과 세계관을 기반으로 일관성 있는 시나리오를 생성
- 플레이 가능한 그래프 구조로 변환

## 현황

- **단계**: 프로젝트 초기화 및 MVP(S0) 개발 착수
- **환경**:
  - OS: Linux
  - Language: Python (3.11+)
  - Package Manager: uv
  - Frameworks: FastAPI, LangChain Core
  - Database: PostgreSQL (with Apache AGE)

---

## [Phase 0] MVP (Minimum Viable Product)

**목표**: 기초 인프라 구축 및 시나리오 생성-파싱-제공의 핵심 루프 완성

### 1. 공통 인프라 (Infrastructure)

- [ ] **DB 스키마 설계 및 적용**

  - [ ] 관계형 데이터 스키마 설계 (룰, 세계관 등)
  - [ ] 그래프 데이터 스키마 설계 (Apache AGE 기반 시나리오 그래프)
  - [ ] DB 초기화 스크립트 작성 및 적용

- [ ] **외부 쿼리 관리 체계 구축**

  - [ ] SQL(.sql) 및 Cypher(.cypher) 파일을 코드 외부에서 관리
  - [ ] 파일로부터 쿼리를 로드하여 실행하는 인터페이스 구현

- [ ] **DB 연결 인터페이스 구현**

  - [ ] `psycopg2` 기반 PostgreSQL 커넥션 핸들러 작성 (AGE 확장 지원 확인)
  - [ ] 커넥션 획득(get) 및 반환(release) 인터페이스 구현

- [ ] **LLM 호출 인터페이스 구현**
  - [ ] `langchain-core` 기반 BaseLLM 인터페이스 정의
  - [ ] ChatModel 호출 및 응답 파싱 표준화

### 2. 시나리오 생성 모듈 (Scenario Generator)

- [ ] **데이터 연동**

  - [ ] DB를 통해 룰 및 세계관 데이터 조회 기능

- [ ] **생성 로직**
  - [ ] LLM 기반 자연어 시나리오 초안 생성 프롬프트 설계

### 3. 시나리오 파서 (Scenario Parser)

- [ ] **도메인 모델**

  - [ ] `ScenarioNode`, `ScenarioEdge`, `ScenarioGraph` 정의

- [ ] **파싱 로직**
  - [ ] 자연어 텍스트 -> 구조화된 그래프 변환 로직 구현
  - [ ] 기본적인 분기(Branch) 식별 기능

### 4. 상태 관리 및 API (State & API)

- [ ] **인터페이스 구축**
  - [ ] FastAPI 기본 App 및 라우팅 설정
  - [ ] GM 서비스용 시나리오 제공 API 구현

---

## [Phase 1] S1 (Quality Improvement)

**목표**: 시나리오의 품질 고도화 및 시스템 안정성 확보

- [ ] **멀티 에이전트 도입**

  - [ ] 시나리오 기획, 검토, 파싱 에이전트 분리 및 협업 구조 설계

- [ ] **프롬프트 엔진리어링**

  - [ ] Few-shot 학습 및 CoT(Chain of Thought) 적용으로 생성 품질 향상

- [ ] **컨텍스트 관리 개선**

  - [ ] Redis 등을 활용한 컨텍스트 캐싱 및 효율화

- [ ] **파이프라인 최적화**
  - [ ] 생성부터 파싱까지의 워크플로우 자동화 및 에러 복구 로직

---

## [Phase 2] S2 (Scale & Advanced Features)

**목표**: 대규모 사용자 대응 및 시나리오 확장성 강화

- [ ] **시나리오 편집 UI 지원**

  - [ ] 그래프 수정을 위한 CRUD API 확장

- [ ] **다양한 세계관 확장**

  - [ ] 룰북별 데이터 스키마 범용화 및 멀티 룰북 지원

- [ ] **성능 최적화**
  - [ ] 동시 접속 및 트래픽 테스트 진행
  - [ ] LLM 호출 비용 및 레이턴시 개선
- [ ] **지표 모니터링**
  - [ ] 시나리오 품질 지표 수립 및 관측성(Observability) 확보
