# Development Plan

<!-- PROJ_ARCH_BEGIN -->

## Architecture

- current: v0.0.0
- docs/dev/architect/architecture_v0.0.0.md
<!-- PROJ_ARCH_END -->

<!-- PROJ_DASHBOARD_BEGIN -->

## Feature Dashboard

| ID        | Feature                                               | Detail                             | Status |
| --------- | ----------------------------------------------------- | ---------------------------------- | ------ |
| GEN-01    | Scenario Generation                                   | LangGraph 기반 시나리오 생성 엔진  | done   |
| API-01    | Generation API                                        | `/api/v1/generation` 엔드포인트    | done   |
| INFRA-01  | Database Mapping                                      | PostgreSQL & Neo4j(Cypher) 연동    | done   |
| AGENT-01  | Multi-Agent Setup                                     | Planner, Writer, Reviewer 에이전트 | done   |
| TEST-01   | Test Suite                                            | Unit & Integration & E2E 테스트    | done   |
| plan_0001 | GPT 모델 생성 확인 및 scripts/test_generation.py 검증 | docs/dev/detail/plan_0001.md       | done   |
| plan_0002 | 생성-주입 정합성 회귀 테스트 베이스 구축              | docs/dev/detail/plan_0002.md       | doing  |

<!-- PROJ_DASHBOARD_END -->

<!-- PROJ_TODO_BEGIN -->

## TODO (Undone detail plans)

- [x] docs/dev/detail/plan_0001.md
- [ ] docs/dev/detail/plan_0002.md
<!-- PROJ_TODO_END -->
