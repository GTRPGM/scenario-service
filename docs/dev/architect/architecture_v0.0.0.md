# Architecture v0.0.0

## Summary

- LLM과 LangGraph를 이용한 시나리오 생성 서비스의 초기 아키텍처

## Context

- TRPG 게임의 방대한 시나리오와 에셋(아이템, NPC, 적)을 일관성 있게 자동 생성해야 함
- 멀티 에이전트 협업을 통한 품질 향상 및 검증 루프 필요

## System overview

- **FastAPI Layer**: 클라이언트 요청 처리 및 시나리오 관리 API 제공
- **Engine (LangGraph)**:
  - `Planner`: 시나리오 컨셉을 바탕으로 전체적인 계획 및 에셋 리스트 작성
  - `Asset Writer`: 계획된 아이템, NPC, 적의 상세 스펙 생성
  - `Sequence Writer`: 시나리오의 흐름(Sequence) 기술
  - `Reviewer`: 결과물의 일관성 검토 및 재시도 결정
- **Infra Layer**:
  - `PostgreSQL`: 세션 상태 및 관리 데이터 저장
  - `Apache AGE (PostgreSQL Extension)`: 시나리오의 인과 관계 및 에셋 관계를 그래프로 저장 (Cypher 쿼리 사용)

## Data flow

1. 사용자가 컨셉과 함께 생성 요청 (API)
2. 시나리오 엔진이 LangGraph 워크플로우 실행
3. 각 에이전트가 LLM을 호출하여 데이터 생성 및 보정
4. 최종 생성된 시나리오 데이터를 DB에 영속화
5. 사용자에게 생성된 시나리오 ID 또는 결과 반환

## Decisions

- **Decision**: LangGraph 기반 상태 머신 사용
- **Reason**: 에이전트 간의 복잡한 조건부 흐름과 루프(Review-Fix)를 효과적으로 관리하기 위함
- **Impact**: 시나리오 생성 과정의 투명성과 제어 가능성 향상

## Compatibility / migration notes

- 초기 버전으로 해당 없음
