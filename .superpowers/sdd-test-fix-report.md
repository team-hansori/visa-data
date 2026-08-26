# tests/test_validate_fk_integrity.py — 신규 API 정합화 리포트

## 배경

`scripts/validate_fk_integrity.py`가 Task 5에서 리팩터링되면서
`tests/test_validate_fk_integrity.py`가 구 API 시그니처를 그대로 참조하고 있어
`uv run pytest tests/`가 수집(collection) 단계에서부터 실패하고 있었다. 두 검증기
스크립트를 직접 실행하는 방식으로만 리뷰가 진행되어 이 회귀가 5번의 태스크 리뷰와
1번의 전체 브랜치 리뷰를 통과했다.

## 무엇이 바뀌었나 (실제 코드 기준, ground truth)

1. `TableSpec.fks`: `dict[str, Path]` → `dict[str, tuple[Path, str]]`
   (FK 컬럼 → (부모 테이블 경로, 부모 조회 컬럼명)). 부모 조회 컬럼이 항상 부모의 PK는
   아니다(예: `agency_contacts.category_minor`).
2. `TableSpec`에 `nullable_fks: dict[str, tuple[str, str]]` 필드 신설. FK 값이
   비어 있고 `row[condition_column] == condition_value`이면 에러로 보지 않는다.
   조건이 성립하지 않으면(다른 값이거나 조건 컬럼 자체가 비어있으면) 기존과 동일하게
   "비어 있음" 에러. FK 값이 존재하면 nullable_fks와 무관하게 항상 부모 테이블 조회
   대상.
3. `collect_pk_sets(tables) -> dict[Path, set[str]]` → `collect_lookup_sets(tables) ->
   dict[tuple[Path, str], set[str]]`로 이름·시그니처 변경. 각 테이블의 `pk`가 아니라
   다른 테이블들의 `fks` 값에 등장하는 (부모 경로, 부모 컬럼) 조합을 기준으로 수집한다.
4. `check_fk_integrity(table, rows, lookup_sets)`의 3번째 인자 타입이
   `dict[tuple[Path, str], set[str]]`로 바뀌었고, `table.nullable_fks`를 검사하는
   분기가 추가됐다.
5. 신규 함수 `check_risk_message_coverage(routing_path, messages_path) ->
   list[str]` — `risk_routing_table.csv`의 (keyword_category, resolution_type)
   조합이 `risk_keyword_messages.csv`에 존재하는지, 그리고 messages 파일 자체에
   중복 조합이 없는지 검사. `validate()`에 `RISK_ROUTING_FILENAME`/
   `RISK_KEYWORD_MESSAGES_FILENAME` 상수로 파일명 매칭해 연결됨(기존
   `check_document_requirements_status`와 동일한 패턴).
6. `default_tables()`/`reference_tables()`가 새 `fks` 튜플 형태와
   `risk_routing_table.csv`의 `nullable_fks`를 사용.

실제 코드는 사전 요약과 정확히 일치했다 — 별도로 에스컬레이션할 불일치는 없었다.

## 변경 내용 (테스트별)

### 기계적 변경 (동일 동작, API 시그니처만 교체)

- import 목록: `collect_pk_sets` → `collect_lookup_sets`, `check_risk_message_coverage` 추가.
- `TestCheckFkIntegrity`의 3개 테스트: `fks={"parent_id": parent_path}` →
  `fks={"parent_id": (parent_path, "id")}`, `pk_sets = {parent_path: {"p1"}}` →
  `lookup_sets = {(parent_path, "id"): {"p1"}}`. 검증하던 행동(정상 FK/누락된 부모/빈 FK)은
  그대로.
- `TestValidateEndToEnd._build_chain`을 사용하는 2개 테스트: `fks={"visa_id":
  visa_requirements}` → `fks={"visa_id": (visa_requirements, "visa_id")}` 등, 실제
  `default_tables()`가 쓰는 PK 컬럼명을 그대로 부모 조회 컬럼으로 사용.
- `TestCheckRequiredColumns`의 2개 테스트, `TestValidateCatchesMissingColumns`의
  1개 테스트: `fks={"parent_id": Path(...)}` → `fks={"parent_id": (Path(...), "id")}`.
  검증 대상은 "필수 컬럼 누락 감지"이므로 튜플의 두 번째 요소 값 자체는 이 테스트들의
  주장에 영향 없음(단순히 fks 딕셔너리 값 형태만 맞춤).

### 비기계적 변경

- **`TestCollectPkSets` → `TestCollectLookupSets`** (`test_collects_pk_values_across_tables`
  → `test_collects_lookup_values_referenced_by_other_tables`): 구 버전은 `pk`만 있는
  단일 테이블을 넣고 `collect_pk_sets`가 `{path: {"p1", "p2"}}`를 반환하는지 확인했다.
  신 버전 `collect_lookup_sets`는 각 테이블의 `pk`를 보지 않고 다른 테이블들의 `fks` 값에
  등장하는 (경로, 컬럼) 조합만 수집하므로, 부모 테이블 하나만으로는 아무것도 모으지
  못한다. 그래서 `fks={"parent_id": (parent_path, "id")}`를 가진 자식 테이블을 함께
  넣어 `collect_lookup_sets([parent_table, child_table])`를 호출하고
  `lookup_sets[(parent_path, "id")] == {"p1", "p2"}`를 확인하도록 재작성했다 — "부모
  테이블의 지정 컬럼 값들을 모아 조회 가능하게 만든다"는 원래 의도는 그대로 유지.

## 신규 테스트

### `TestNullableFks` (check_fk_integrity의 nullable_fks 분기, 커버리지 0 → 3케이스)

- `test_no_error_when_empty_and_condition_met`: FK 빈 값 + 조건 컬럼이 조건 값과
  일치 → 에러 없음.
- `test_flags_empty_when_condition_not_met`: FK 빈 값 + 조건 컬럼이 다른 값
  (`IN_DOMAIN` vs 조건값 `EXTERNAL`) → 일반 FK와 동일하게 "비어 있음" 에러 1건.
- `test_flags_invalid_value_regardless_of_nullable_fks`: FK 값이 존재하지만 부모
  lookup set에 없음(조건은 충족됨에도) → nullable_fks와 무관하게 "존재하지 않음" 에러
  1건 — nullable_fks가 빈 값 케이스에만 작동하고 잘못된 값 케이스에는 영향을 주지
  않음을 확인.

### `TestCheckRiskMessageCoverage` (check_risk_message_coverage, 커버리지 0 → 3케이스)

- `test_no_errors_when_every_combination_is_covered`: routing의 조합이 messages에
  존재 → 에러 없음.
- `test_flags_routing_combination_missing_from_messages`: routing의 조합이
  messages에 없음 → 에러 1건, 조합 값(`visa`, `IN_DOMAIN`)과 messages 파일 경로가
  모두 에러 메시지에 포함되는지 확인.
- `test_flags_duplicate_combination_within_messages`: messages 파일 자체에 동일
  (keyword_category, resolution_type) 조합이 2행 → 에러 1건, "중복" 문자열과 파일
  경로 포함 확인.

## pytest 결과

- **변경 전**: `uv run pytest tests/` — `tests/test_validate_fk_integrity.py`에서
  `ImportError: cannot import name 'collect_pk_sets'` 등으로 수집 자체가 실패(0건
  실행).
- **변경 후 (대상 파일만)**: `uv run pytest tests/test_validate_fk_integrity.py -v`
  → **36 passed** (구 30개 테스트 + 신규 6개: NullableFks 3 + CheckRiskMessageCoverage 3).
- **변경 후 (전체 스위트)**: `uv run pytest tests/ -v --tb=short` → **410 passed**,
  0 failed, 0 errors, 수집 에러 없음.

## 변경 파일

- `tests/test_validate_fk_integrity.py` (유일한 변경 파일, 151 insertions / 22 deletions)

## 린트

- `uv run ruff check tests/test_validate_fk_integrity.py` → All checks passed.
- `uv run ruff format --check tests/test_validate_fk_integrity.py` → 최초 실행 시
  1개 파일 재포맷 필요(긴 한 줄 호출을 여러 줄로 나눈 부분을 ruff가 한 줄로 되돌림).
  `ruff format`으로 적용 후 재확인하여 clean 상태 확인.

## 실제 검증기 스크립트 (repo 실데이터 기준)

- `uv run python scripts/validate_fk_integrity.py` → `FK/PK 검증 통과: 문제 없음`, exit 0.
- `uv run python scripts/validate_reference_delimiters.py` → `OK: 모든 다중값 컬럼이
  파이프 구분자를 사용합니다.`, exit 0.

## 셀프 리뷰

- 기존 테스트는 모두 "무엇을 검증하는지"가 그대로 유지된 채 호출 형태만 새 API에
  맞췄다. 어떤 assert도 약화하거나 삭제하지 않았다.
- `nullable_fks` 신규 테스트는 3케이스(빈값+조건충족/빈값+조건불충족/값존재+오류) 모두
  실제로 실행되고 통과함을 확인.
- `check_risk_message_coverage` 신규 테스트는 3케이스(정상/누락 조합/중복 조합) 모두
  실행되고 통과함을 확인.
- `uv run pytest tests/ -v --tb=short` → 0 failed, 0 errors, 테스트 개수는 구
  30개(대상 파일 기준) → 신 36개로 증가(삭제된 테스트 없음).
- `ruff check`/`ruff format --check` 모두 clean.
- 두 실제 검증기 스크립트 모두 repo 실데이터에 대해 exit 0.

## 우려 사항

- 없음. `reference_tables()`의 실제 `risk_routing_table.csv` nullable_fks 조건
  (`resolution_type == "EXTERNAL"`)을 테스트에서 그대로 재사용해 실제 사용 맥락과
  일치하게 작성했다.
