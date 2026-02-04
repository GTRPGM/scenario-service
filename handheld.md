# Scenario Service Handheld Guide

## 1. 개요

GTRPGM 시나리오 서비스는 자연어 기획 초안을 바탕으로 구조화된 RPG 시나리오 데이터를 생성하고 검증합니다.

## 2. 생성 아키텍처 (Writer Graph)

시나리오는 LangGraph를 이용한 3단계 파이프라인으로 생성됩니다.

### Step 1: Planner (기획)

- 역할: 전체 서사 구조 잡기
- 출력: 시나리오 요약, 액트 계획, 아이템/NPC/에너미 목록

### Step 2: AssetWriter (자산 상세 설계)

- 역할: Planner가 제안한 자산들의 상세 속성 정의
- 출력: 상세 능력치, 아이템 타입, 설명 등이 포함된 카탈로그

### Step 3: SequenceWriter (시퀀스 집필 및 배치)

- 역할: 각 액트별 시퀀스 내용 집필 및 자산 배치
- **규칙**: 새로운 자산을 생성하지 않고, 카탈로그에 정의된 자산만 사용

## 3. 데이터 정규화 및 정합성

### ID 타입 정의 (중요)

- **아이템 정의 (Definition)**: `item_id`는 **정수(int)**여야 합니다. (Catalog 요구사항)
- **NPC/에너미 정의**: `scenario_npc_id`, `scenario_enemy_id`는 **문자열(str)**입니다.
- **참조 (Reference)**: 시퀀스나 액트에서 이들을 참조할 때는 모두 **문자열**로 변환하여 리스트에 담습니다.

### 핵심 보존 필드

- `master_id`: 룰 엔진의 마스터 데이터 참조용 (외부 연동 시 사용)
- `state_manager_id`: 상태 관리 서비스에서 부여한 고유 식별자

## 4. 로컬 개발 환경

### 의존성 설치

```bash
uv sync
```

### 환경 변수

- `LLM_GATEWAY_HOST`: LLM API 서버 주소
- `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`: PostgreSQL/AGE 연결 정보

## 5. 테스트 및 검증

### 테스트 실행

```bash
uv run pytest
```

- `tests/test_deps_integrity.py`: 모델 간 ID 타입 일관성 검증
- `tests/test_infra_db_real.py`: 실제 DB(Apache AGE) 저장 및 조회 검증

### 텍스트 정문화

- 위치: `src/scenario/core/utils/text.py`
- 기능: LLM이 생성한 불규칙한 ID(예: `npc_01`, `NPC-1`)를 `npc-1` 형태로 정규화하여 그래프 매칭 오류 방지

## 6. 상태 관리자(State Manager) 주입

- 모든 식별자는 전송 직전 `ScenarioInjectSchema`를 통해 검증됩니다.
- 주입 성공 시 `state_manager_id`가 로컬 DB에 역으로 기록되어 동기화됩니다.
