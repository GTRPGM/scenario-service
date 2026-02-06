# Handheld

<!-- PROJ_UNDERSTANDING_BEGIN -->

## Project Understanding

### What this project is

- TRPG 시나리오 생성을 위한 백엔드 서비스 (FastAPI 기반)
- LangGraph를 활용한 멀티 에이전트(Planner, Writer, Reviewer 등) 워크플로우 엔진 탑재F
- 생성된 시나리오의 무결성 검증 및 데이터 저장 (PostgreSQL + Apache AGE)

### Architecture link

- <!-- PROJ_ARCH_LINK -->docs/dev/architect/architecture_v0.0.0.md

### How to run

- 로컬 실행: `bin/project run` (Port: 8040)
- Docker 실행: `bin/project up` (LLM 모델: `gpt-4o-mini`)

### How to test (unit)

- `uv run pytest tests`

### How to run e2e

- `bin/project ci-dev` (act를 이용한 CI 워크플로우 시뮬레이션)

### Conventions / gotchas

- `uv` 패키지 매니저 사용 권장
- `src/` 디렉토리에 소스 코드가 위치하는 layout
- 에이전트 프롬프트는 `src/scenario/infra/prompts/`에서 관리
<!-- PROJ_UNDERSTANDING_END -->

<!-- PROJ_WORKNOTES_BEGIN -->

## Work Notes by Detail

### ref_0001 - DB 어댑터 리팩토링 및 쿼리 외부화 반영

- Work (brief):
  - DB 어댑터 내 하드코딩된 쿼리를 외부 파일로 분리하고, 에셋 유실 방지를 위한 저장 로직 및 프롬프트를 강화함.
- Actions taken (detailed):
  - `src/scenario/infra/db/queries/` 하위에 SQL 및 Cypher 파일을 구축하고 `QueryLoader`를 통한 동적 로드 패턴 적용.
  - 시퀀스에 배치되지 않은(unplaced) 엔티티들을 `HAS_UNPLACED_ENTITY` 관계로 그래프 DB에 보존하도록 `save_scenario` 로직 수정.
  - LLM 에이전트 프롬프트에 최소 엔티티 수량(각 4종 이상) 및 시퀀스 배치 강제 규칙을 추가하여 생성 품질 고도화.
  - `master_id` 도입 및 아이템 ID 체계 정규화(정수형 추출)를 통해 외부 서비스 연동 규격 사전 확보.
- What I learned / updated understanding:
  - Apache AGE 사용 시 Cypher 쿼리에서 발생하는 타입 접미사(`::agtype` 등) 처리의 중요성 및 정규화 필요성을 확인.
  - 시나리오 데이터의 원형을 보존하기 위해 '배치(Placement)'와 '카탈로그(Catalog)' 데이터를 분리하여 관리하는 구조가 확장성에 유리함.

### ref_0002 - 테스트 코드의 아이템 ID 체계 동기화 및 잔여 실패 수정

- Work (brief):
  - 아이템 ID 체계 변경에 맞춰 모든 유닛/통합 테스트를 업데이트하고 실제 LLM 연동 검증을 완료함.
- Actions taken (detailed):
  - `tests/` 내 5개 파일의 아이템 ID 기대값(`item-101` -> `101`) 및 필드명(`rule_id` -> `master_id`) 전수 수정.
  - `ScenarioEngine` 및 Pydantic 모델(`EntityPlan`)에 `model_validator`를 추가하여 LLM의 가변적인 ID 필드명 출력에 유연하게 대응하도록 보정 로직 구현.
  - 실제 LLM 게이트웨이(`gemini-2.0-flash-lite`)를 통한 시나리오 생성 및 DB 저장 프로세스 엔드투엔드 검증 성공.
- What I learned / updated understanding:
  - **LLM 모델 가용성**: 현재 인프라 게이트웨이에서는 `gpt-4o-mini`가 아닌 `gemini-2.0-flash-lite` 모델이 정상 작동함을 확인.
  - **방어적 파싱(Defensive Parsing)**: LLM이 JSON 스키마를 준수하더라도 필드명 변동성(예: `id` vs `scenario_item_id`)이 있을 수 있으므로, Pydantic의 validator를 활용한 보정 레이어가 시스템 안정성에 필수적임.

### plan_0001 - GPT 모델 생성 확인 및 scripts/test_generation.py 검증

- Work (brief):
  - `docker-compose.local.yml` 환경을 구축하여 로컬 서비스 및 DB(Apache AGE) 실행을 검증하고 시나리오 생성 스크립트(`scripts/test_generation.py`)를 테스트함.
- Actions taken (detailed):
  - `scripts/test_generation.py`의 기본 포트를 `8040`으로 수정하여 `bin/project run` 및 로컬 컴포즈 환경과 동기화.
  - `docker-compose.local.yml`에서 `LLM_GATEWAY_HOST` 환경 변수가 누락되어 네임 레졸루션 에러가 발생하던 문제를 외부 IP(`35.216.98.244`) 명시적 지정으로 해결.
  - LLM 호출 시 게이트웨이로부터 `OPENAI_API_KEY is not set.` 응답(400 Bad Request)을 받는 것을 확인하여 인프라 측 키 설정 필요성을 식별함.
- What I learned / updated understanding:
  - 현재 시나리오 서비스의 `Settings`는 `LLM_GATEWAY_HOST`와 `PORT`를 분리하여 URL을 구성하므로, 환경 변수 주입 시 URL 전체가 아닌 호스트명을 전달해야 함.
  - 인프라 게이트웨이의 모델 지원 현황이나 API 키 설정 상태에 따라 서비스 생성이 중단될 수 있으므로, 에이전트 레이어에서의 예외 처리 강화가 필요함.
  <!-- PROJ_WORKNOTES_END -->
