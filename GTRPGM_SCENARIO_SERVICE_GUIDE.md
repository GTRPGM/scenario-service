# GTRPGM Scenario Service Hand-held Guide

이 문서는 GTRPGM 시나리오 서비스의 아키텍처, 핵심 로직 및 개발 현황을 정리한 가이드입니다.

## 1. 프로젝트 개요
본 서비스는 TRPG 시나리오의 **생성(Generation)**, **관리(Management)**, 그리고 **진행 판정(Progression Validation)**을 담당하는 핵심 컴포넌트입니다.

- **핵심 목표**: 사용자의 컨셉을 바탕으로 논리적 구조(Act-Sequence)를 갖춘 시나리오를 자동 생성하고, 플레이어의 행동이 시나리오 전이 조건을 충족하는지 판정합니다.
- **철학**: 아키텍처 우선(Architecture First). 코어와 플러그인을 엄격히 분리하여 LLM 모델이나 DB 엔진의 교체가 용이하도록 설계되었습니다.

## 2. 기술 스택
- **Language**: Python 3.11+
- **Package Manager**: [uv](https://github.com/astral-sh/uv) (성능 및 의존성 관리 최적화)
- **Framework**: FastAPI (Async-first)
- **Agent Orchestration**: LangChain, LangGraph
- **Database**: PostgreSQL + **Apache AGE** (Graph DB extension)
- **Testing**: pytest + **testcontainers** (실제 DB 컨테이너 기반 통합 테스트)

## 3. 핵심 아키텍처

### Core-Plugin 구조
- `src/scenario/core`: 비즈니스 로직 및 인터페이스 정의. 외부 라이브러리에 의존하지 않는 순수 로직 지향.
- `src/scenario/plugins`: LLM(Gemini 2.0), DB(Postgres/AGE) 등 외부 시스템과의 구체적인 연동 구현.
- `src/scenario/infra`: DB 연결 설정, SQL/Cypher 쿼리, LLM 프롬프트 관리.

### 시나리오 생성 워크플로우 (LangGraph)
`ScenarioWriterGraph`는 다음 세 에이전트의 협력으로 시나리오를 완성합니다:
1. **Planner**: 시나리오 전체 구조(Act, Sequence) 및 전역 관계(Relations) 기획.
2. **Writer**: 각 시퀀스의 세부 묘사, 장소, 엔티티(NPC, Enemy, Item) 데이터 작성.
3. **Reviewer**: 기획안과 세부 내용의 일관성 검토 및 피드백.
*최대 3회 반복 개선 루프를 통해 품질을 보장합니다.*

## 4. 데이터 모델 (Act-Sequence-Entity)
시나리오는 계층형 그래프 구조로 저장됩니다.
- **Act**: 대단원 (목표 및 전환 조건 포함)
- **Sequence**: 소단원 (특정 장소에서의 사건 및 엔티티 포함)
- **Entity**: NPC, Enemy, Item (상태값 `state` 및 메타데이터 `meta` 포함)
- **Relation**: 엔티티 간의 서사적 관계 (Apache AGE Edge로 구현)

## 5. 주요 API 및 엔드포인트

### 시나리오 생성 및 주입
- `POST /api/v1/scenario/generate`: 자연어 컨셉으로 시나리오 생성 및 로컬 DB 저장.
- `POST /api/v1/scenario/{scenario_id}/inject`: 생성된 시나리오를 `State Manager`에 표준 포맷으로 주입.

### 시나리오 진행 판정
- `POST /api/v1/scenario/validate-progression`:
  - **Input**: 현재 시퀀스 정보, 사용자 입력, 그래프 컨텍스트.
  - **Output**: 전이 발생 여부(`is_triggered`), 판정 이유, 다음 시퀀스 제안, GM 내레이션 가이드.

## 6. 개발자 가이드

### 의존성 설치 및 서버 실행
```bash
uv sync
uv run uvicorn scenario.main:app --host 0.0.0.0 --port 8000
```

### 테스트 수행
본 프로젝트는 `testcontainers`를 사용하여 실제 Apache AGE 환경에서 DB 테스트를 수행합니다. 로컬에 `postgres-ex:latest` 이미지가 필요합니다.
```bash
# 전체 테스트 실행
uv run pytest

# 실제 DB 통합 테스트만 실행
uv run pytest tests/test_infra_db_real.py
```

## 7. 주요 변경 및 해결 사항 (2026-01-29)
1. **Injection Schema 정렬**: `SCENARIO_INJECTION_GUIDE.md`의 최신 규격에 맞춰 엔티티 리스트 평탄화 및 관계(Relation) 데이터 지원 추가.
2. **세션 로직 분리**: 시나리오 서비스에서 세션 관리 기능을 제거하고, 시나리오 템플릿의 생성과 주입에 집중하도록 아키텍처 단순화.
3. **LLM 400 에러 해결**: Gemini API의 JSON Schema 제약 사항(`additionalProperties` 미지원)을 `json_object` 모드 전환과 수동 파싱 로직으로 해결.
4. **DB 정합성 보장**: Apache AGE의 `agtype` 반환 데이터를 파이썬 객체로 변환하는 `_clean_agtype` 헬퍼 도입.

---
*GTRPGM Scenario Service - Maintainer: Senior Python Developer*
