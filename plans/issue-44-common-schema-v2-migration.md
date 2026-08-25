# Issue #44: 공통 스키마 v2 정의 및 비자 데이터 마이그레이션 계획

## 목표

공통 마스터의 v1 서비스 테이블 5개를 v2 서비스 테이블 10개로 확장하고,
출처·변경 추적·이관 지원 테이블 3개를 포함한 총 13개 테이블의 계약을 문서와 코드로
확정한다. 검수 완료된 F-4-R, E-7-4R, F-2-R 데이터를 같은 구조로 이관하고 D-2는
Lookup/Eligibility/Rule 구조를 유지한 채 공통 마스터 연결만 검증한다.

이 작업은 스키마와 데이터 마이그레이션까지를 범위로 한다. 점수 계산·자격 판정 서비스,
개인별 쿼터 미차감 판정, 미검수 데이터 소비, PR #23 월별 자동화의 v2 대응은 포함하지 않는다.

## 시작 상태

- 작업 브랜치: `feat/20260821_#44_공통_스키마_v2_정의_및_비자_데이터_마이그레이션`
- 기준 브랜치: 최신 `origin/main`
- PR #36과 PR #43은 `main`에 병합되어 있으므로 별도 cherry-pick 또는 재병합하지 않는다.
- PR #38(`scripts/uuid_utils.py`, 이슈 #37)은 아직 `main`에 병합되지 않았다(OPEN, mergeable).
  9단계에서 이 유틸리티를 재사용하므로, 그 전에 병합하거나 v2 브랜치로 가져와야 한다.
- v1 기준 데이터는 `extraction/D_visa_requirements/`에 그대로 보존한 상태에서 변환을 시작한다.
- F-2-R, E-7-4R의 원천 extraction과 검수 상태는 공통 테이블로 복사하지 않고 매핑 근거로 사용한다.
- 공통 스키마 v2 명세는 `docs/schema-v2.md`에 확정되어 있다(이슈 #44 댓글 결정 반영). 아래 모든
  단계는 이 문서를 1차 근거로 삼는다 — 컬럼·enum 정의가 필요하면 여기 요약이 아니라
  `docs/schema-v2.md` 원문을 확인한다.

## 목표 테이블

### 서비스 공통 테이블 10개

1. `visa_requirements`
2. `visa_criterion_groups`
3. `visa_requirement_criteria`
4. `visa_scoring_models`
5. `visa_scoring_items`
6. `visa_process_stages`
7. `document_requirements`
8. `document_attachment_relations`
9. `visa_quota_policies`
10. `visa_quota_snapshots`

### 근거·이관 지원 테이블 3개

1. `source_documents`
2. `change_history`
3. `source_record_mappings`

## 확정된 enum (schema.py·검증기에 그대로 반영)

`docs/schema-v2.md`에서 확정된 값이다. 구현 중 다른 값을 추가로 발견하면 이 표와 명세 문서를
같이 갱신한다.

| 테이블.컬럼 | 허용값 |
| --- | --- |
| `visa_criterion_groups.boolean_operator` | `AND`, `OR` |
| `visa_requirement_criteria.criteria_type` | `NUMERIC`, `TEXT`, `BOOLEAN`, `LIST`, `EXISTENCE` |
| `visa_requirement_criteria.evaluation_mode` | `AUTOMATED`, `MANUAL`, `INFORMATIONAL` |
| `visa_requirement_criteria.operator` | `EQ`, `GT`, `GTE`, `LT`, `LTE`, `IN`, `NOT_IN`, `EXISTS`, `NOT_EXISTS`, `WITHIN` |
| `visa_scoring_models.model_purpose` | `PASS_THRESHOLD`, `QUOTA_RANKING`, `BOTH`, `UNKNOWN` |
| `visa_scoring_items.score_group` | `BASE`, `BONUS`, `PENALTY` |
| `visa_scoring_items.stacking_rule` | `STACK`, `ONE_OF`, `MAX_SCORE_ONLY`, `UNKNOWN` |
| `document_requirements.requirement_status`, `document_attachment_relations.requirement_status` | `REQUIRED`, `OPTIONAL`, `CONDITIONAL`, `ALTERNATIVE` |
| `visa_quota_policies.quota_type` | `LIMITED`, `UNLIMITED`, `UNKNOWN` |
| `visa_quota_snapshots.scope_type` | `NATIONAL`, `PROVINCE`, `MUNICIPALITY`, `INSTITUTION`, `DEPARTMENT`, `OTHER` |
| `source_documents.document_type` | `ANNOUNCEMENT`, `ATTACHMENT`, `AMENDMENT`, `GUIDELINE`, `FORM`, `OTHER` |
| `source_record_mappings.mapping_action` | `COPY`, `TRANSFORM`, `MERGE`, `SKIP`, `MANUAL_REVIEW` |
| `source_record_mappings.mapping_status` | `PENDING`, `READY`, `MAPPED`, `BLOCKED` |

원천 기호(`=`, `==`, `>`, `>=`, `<`, `<=`)를 위 `operator` enum으로 바꾸는 변환표는
`docs/schema-v2.md`의 "공통 operator enum" 절에 있다. `schema.py`나 마이그레이션 스크립트에
같은 변환표를 하드코딩할 때는 이 문서를 그대로 옮기고 임의로 새 매핑을 추가하지 않는다.

## 공통 마스터에 절대 만들지 않는 컬럼·테이블

`docs/schema-v2.md`의 "제외되는 것" 절 그대로다. `schema.py` 작성 시 아래 이름이 13개 테이블
어디에도 없는지 3단계 검증기에서 확인한다.

- 별도 상태관리 테이블 전반
- `visa_round_facts`, `visa_current_facts`, `visa_fact_coverage`
- `extraction_status`, `review_status`, `consumption_gate`, `confidence`

이 값들은 원천·검수 계층(`extraction/`)에만 유지하고 공통 마스터에는 검수 완료 여부만 걸러진
결과 데이터로 올린다.

## 구현 원칙

- 명세를 먼저 확정하고 CSV 헤더, 코드, 데이터가 명세를 따르게 한다.
- A/B/C 원천 extraction의 구조와 원천 ID는 변경하지 않는다.
- 논리 테이블명은 `.csv` 확장자 없이 저장한다.
- 기존 v1 공통 UUID는 유지한다.
- 신규 공통 UUID는 매핑과 데이터 검증이 끝난 마지막 단계에 UUIDv4로 발급한다.
- 발급 전 `source_record_mappings.target_record_id`는 비워 둔다.
- 공통 마스터에는 검수 완료된 데이터만 적재하며 원천의 상태·confidence를 중복 저장하지 않는다.
- 확인되지 않은 값은 추정하거나 `0`으로 채우지 않고 nullable 필드로 유지한다.
- 마이그레이션 도중 v1 파일을 덮어쓰지 않는다. v2 임시 출력과 검증을 완료한 뒤 명시적으로 전환한다.

## 작업 단계

### 1. 입력 데이터와 v1 기준선 고정

- `extraction/D_visa_requirements/`의 6개 v1 CSV 헤더, 행 수, PK/FK, UUID를 스냅샷으로 기록한다.
- F-4-R은 v1 공통 마스터와 이슈 #42 검증 결과를 기준으로 한다.
- E-7-4R은 `extraction/B_E-7-4R/`과 PR #43의 검수·매핑 결과를 기준으로 한다.
- F-2-R은 `extraction/A_F-2-R/`과 PR #36의 원천·검수·매핑 결과를 기준으로 한다.
- D-2는 `extraction/C_D-2-common/`과 이슈 #41의 연결 결과를 기준으로 한다.
- 각 원천 데이터의 검수 완료·보류 범위를 목록화하고 보류 행은 이관 대상에서 제외한다.

산출물:

- v1 기준선과 비자별 입력 범위를 설명하는 v2 명세의 마이그레이션 전제 절
- 원천 레코드별 초기 `source_record_mappings` 초안(`target_record_id`는 null)

### 2. 공통 스키마 v2 명세 확정 — 완료

`docs/schema-v2.md`로 확정했다(v1 `extraction/D_visa_requirements/README.md`는 그대로 두고
별도 문서로 분리). 아래 항목이 모두 문서에 포함되어 있음을 확인했다.

- 컬럼명, 자료형, nullable 여부, 기본값
- PK, FK, 유일성, 유효기간 규칙
- enum 허용값(위 "확정된 enum" 표로 요약)
- CSV 직렬화 규칙(JSON 배열, 날짜, null)
- 출처 문서와 페이지 연결 규칙
- 원천 레코드와 공통 레코드의 ID 수명주기
- v1 컬럼의 유지·이동·제거·분리 규칙(`total_score_threshold`, `quota_type` 등 `visa_requirements`
  이탈 컬럼, `is_mandatory`/`required_attachments` 대체 등)

고정된 계약:

- eligibility 트리는 비자별 ROOT 하나와 `parent_group_id`, `AND/OR`로 표현한다.
- criteria는 `group_id`만으로 소속 비자를 찾고 `visa_id`를 중복 저장하지 않는다.
- `INFORMATIONAL` criteria는 판정에서 제외하고, `MANUAL` criteria는 `REVIEW_REQUIRED`로 반환한다.
- 제출서류 첨부는 문자열이 아닌 관계 테이블로 표현한다.
- 점수 모델과 항목은 자격 criteria와 분리한다.
- 쿼터 정책과 시점별 스냅샷을 분리하고, `visa_quota_snapshots.consumption_exception`은 개인별
  자동 판정 규칙이 아니라 원문 설명 보존 전용 텍스트로만 다룬다(코드에서 판정 로직에 참조하지 않는다).
- `change_history`는 v1 헤더를 유지한다.

남은 것은 이 명세를 기준으로 3단계(`schema.py`) 이후 코드·데이터를 맞추는 작업뿐이다.

### 3. 스키마 코드와 빈 v2 CSV 골격 구현

- 13개 테이블의 헤더와 계약을 한 곳에서 정의하는 `schema.py`를 추가한다.
- 스키마 정의에서 빈 CSV 골격을 재현할 수 있게 하여 문서와 실제 헤더의 드리프트를 줄인다.
- v1 파일을 입력으로 읽고 v2 임시 디렉터리에 쓰는 마이그레이션 진입점을 추가한다.
- 기존 `validate_fk_integrity.py`를 바로 삭제하지 않고 v1 기준선 검증에 유지한다.
- v2 전용 검증기는 별도 진입점으로 만들고 13개 테이블을 모두 검사한다.

검증 항목:

- 파일 존재와 헤더 순서
- PK 공백·중복과 UUID 버전
- FK 존재 여부
- enum, 날짜, 숫자, JSON 형식
- nullable/필수 필드 계약
- 유효기간 역전 여부
- 논리 테이블명에 `.csv`가 없는지 여부

### 3.5. v1 조건 그룹 → v2 그룹 트리 변환 규칙 (F-4-R/E-7-4R/F-2-R 공통)

v1 `visa_requirement_criteria.csv`(및 `B_E-7-4R`의 `condition_group` 방식)는 "그룹 없는 행끼리
AND" + "같은 `condition_group` 안에서만 단일 단계 OR"만 표현한다. `(A AND B) OR C`나
서로 다른 그룹끼리의 OR(`G1 OR G2`)는 v1 스키마가 애초에 지원하지 않으므로, 실제 v1 데이터에도
그런 형태는 존재하지 않는다 — 즉 v2의 중첩 트리는 v1을 그대로 옮기는 게 아니라 **원문을 다시 읽고
새로 설계**해야 한다.

실제 F-4-R v1 데이터(`extraction/D_visa_requirements/visa_requirement_criteria.csv`, 10행)로
변환 절차를 확정한다.

| v1 원본 | 값 |
| --- | --- |
| `condition_group=G1`(3행): 신청자격(기존거주자·국내전입자·해외전입자) | `condition_operator=OR` |
| `condition_group` 없음(2행): 동반자녀 연령요건 하한(`>=6`)·상한(`<19`) | 그룹 없음 → AND |
| `condition_group=G2`(2행): 동반자녀 재학요건(원칙·질병장애 예외) | `condition_operator=OR` |
| `condition_group` 없음(3행): 허가조건, 결격사유, 취업활동 지역 제한 | 그룹 없음 → AND |

변환 절차:

1. 비자별 ROOT 그룹(`boolean_operator=AND`, `parent_group_id=NULL`)을 하나 만든다.
2. `condition_group`이 비어 있는 v1 행은 ROOT에 직접 연결한다(위 예시의 허가조건·결격사유·
   취업활동 지역 제한).
3. 같은 `condition_group` 값을 가진 v1 행들은 그 그룹 전용 v2 하위 그룹(`boolean_operator=OR`,
   `parent_group_id=ROOT`)을 새로 만들어 그 아래에 연결한다(`G1` → `eligibility_paths` 그룹 3행,
   `G2` → `dependent_child_school_paths` 그룹 2행).
4. README "복합 조건" 절의 "동반자녀 연령요건(AND) + 재학요건(OR)"처럼 그룹 없는 AND 조건과
   OR 그룹이 원문에서 하나의 상위 조건으로 묶여 있다면, 그 상위 개념을 나타내는 중간 그룹을
   ROOT 아래에 새로 만들고 연령요건 2행과 `G2` 그룹을 그 아래로 옮긴다 — v1에는 이 상위 묶음이
   컬럼으로 존재하지 않으므로 원문을 다시 읽고 사람이 그룹을 설계한다.
5. "동반자녀" 조건이 `docs/schema-v2.md`의 `group_scope` 처리표에서 말하는 `DEPENDENT_FAMILY`에
   해당하는지(별도 자격 트리로 분리해야 하는지), 아니면 F-4-R 본인 자격 트리의 한 가지에
   불과한지는 원문 재확인이 필요하다 — 이관 시 임의로 결정하지 않고 열린 질문으로 남긴다.
6. v1에는 없는 "일반조건–특례조건 대체관계"(F-2-R 소상공인 특례 등)는 `docs/schema-v2.md`의
   F-2-R 예시가 목표 형태이며, v1 데이터에서 자동으로 유도하지 않고 원문을 다시 읽어 그룹을
   설계한다.
7. v1 `condition_group`이 비어 있지만 `special_case_note`에 "논리구조 확인 필요"가 남아있는
   행은 이관 대상에서 제외하고 `source_record_mappings.mapping_status=BLOCKED`로 남긴다.

operator·criteria_type 변환:

- v1 `operator`(`>=`/`>`/`<=`/`<`/`==`)는 위 "확정된 enum" 표의 변환 규칙대로
  `GTE`/`GT`/`LTE`/`LT`/`EQ`로 바꾼다.
- v1은 `criteria_type`이 전부 `binary`로 고정되어 있었다. v2에서는 `value_numeric`+`operator`가
  있으면 `NUMERIC`, 서술형 존재 조건(결격사유·지역 제한처럼 `value_numeric`이 비어 있는 행)이면
  `EXISTENCE`+`EXISTS`/`NOT_EXISTS`로, 목록 비교면 `LIST`로 재분류한다.
- v1 README의 "판단 기준 5단계 질문"은 재량판단 조건을 애초에 이 테이블에 넣지 않는 규칙이었으므로,
  기존 v1 criteria 행은 원칙적으로 `evaluation_mode=AUTOMATED`로 이관한다. `MANUAL`/
  `INFORMATIONAL`은 v2 신규 조건(예: `docs/schema-v2.md`의 소상공인 특례 매출액 예시)에만 붙인다.
  단, 원문이 "허가일로부터"/"자격변경 후"/"승인 후"처럼 허가·자격변경 **이후**의 유지의무임을
  명시하는 조건(예: F-4-R "허가조건(거주지 유지의무)")은 원천이 PENDING/READY든 상관없이
  `INFORMATIONAL`로 이관한다 — 최초 신청 시점에는 그 값 자체가 존재하지 않아 `AUTOMATED`로 두면
  최초 신청자를 항상 FAIL 처리하게 되기 때문이다.

### 4. F-4-R v1 → v2 마이그레이션

가장 안정적인 기존 공통 데이터를 먼저 옮겨 변환기의 기준 동작을 확정한다.

- 기존 `visa_id`와 재사용 가능한 v1 공통 UUID를 유지한다.
- 비자별 eligibility ROOT 그룹을 만들고, 위 "3.5" 변환 절차대로 `G1`/`G2`와 그룹 없는 행을
  ROOT/중간/말단 그룹으로 재구성한다. 10행 전체를 실제 변환해 회귀 테스트 fixture로 남긴다.
- `total_score_threshold`와 기존 쿼터 컬럼을 `visa_requirements`에서 제거한다.
- F-4-R은 `visa_quota_policies.quota_type=UNLIMITED`만 만들고 snapshot은 만들지 않는다.
- 절차와 제출서류의 기존 결과가 의미 손실 없이 유지되는지 행 단위로 대조한다.
- 기존 출처 문자열을 `source_documents` 행과 FK로 변환한다.

### 5. E-7-4R 마이그레이션

- 기본 신청 자격은 "3.5" 변환 절차대로 eligibility 트리와 criteria로 이관한다.
- 로컬 `G*` 묶음을 공통 논리 그룹으로 복사하지 않고 원문에서 확인된 AND/OR만 구성한다. F-4-R과
  달리 `B_E-7-4R`의 G번호는 OR 전용이 아니라 느슨한 묶음이므로(README 90번째 줄 참고), 그룹당
  실제 대체관계 여부를 다시 판단한 뒤에만 v2 OR 그룹으로 옮긴다.
- K-POINT 데이터를 `visa_scoring_models`와 `visa_scoring_items`로 이관한다.
- 동점처리, 최종 상한, 전체 가점 상한처럼 미확인인 값은 null로 둔다.
- 중앙부처·광역지자체 추천 점수는 같은 배타 그룹과 `MAX_SCORE_ONLY` 규칙으로 표현한다.
- 충북 8차 쿼터 snapshot은 다음 집계 의미를 보존한다.

```text
allocated_quota        = 542
recommended_count      = 246
quota_exempt_count     = 10
consumed_quota         = 236
remaining_quota        = 306
```

- 관련 값이 모두 존재할 때만 두 쿼터 계산식을 검증한다.
- 검수 완료되지 않은 점수·행은 공통 서비스 데이터로 이관하지 않는다.

### 6. F-2-R 마이그레이션

- PR #36에서 차단된 복합 조건을 "3.5" 변환 절차대로 ROOT/중간/말단 그룹으로 재구성한다.
  `docs/schema-v2.md`의 소상공인 특례 예시(`employer` AND → `employment_capacity_paths` OR →
  `standard_employment_capacity`/`small_business_exception`)를 목표 트리 형태로 삼는다.
- 일반 경로와 특례 경로를 같은 OR 그룹 아래에 배치하되 원문에서 확인되지 않은 관계는 만들지 않는다.
  매출액처럼 두 조건(전년도/최근 2년 평균) 중 어느 것을 자동 판정할지 원문에서 확정하지 못했다면
  분리하지 않고 `evaluation_mode=MANUAL` 단일 criteria로 보존한다(명세 예시 그대로).
- criteria를 ROOT나 중간 그룹에도 직접 연결할 수 있도록 한다.
- 기존 매핑 원장의 원천 ID와 문서 근거를 `source_record_mappings`로 변환한다.
- #35 점수표는 최신 차수 승계가 검증되기 전까지 공통 서비스 데이터에 넣지 않거나 명시적인
  이관 보류 상태로 매핑 장부에 남긴다.
- 시군별 쿼터를 policy/snapshot 구조로 변환한다.

### 7. 제출서류·첨부관계 통합

- F-4-R, E-7-4R, F-2-R 제출서류를 공통 `document_requirements` 계약으로 변환한다.
- `is_mandatory`를 `requirement_status`로 변환한다.
- `required_attachments` 문자열을 문서 행과 `document_attachment_relations` 행으로 분해한다.
- 대체서류는 `alternative_group`, 조건부 서류는 `condition_note`로 보존한다.
- 동일 서류명만으로 자동 병합하지 않고 단계·출처·유효기간을 함께 비교한다.

### 8. D-2 연결 검증

- D-2 Lookup/Eligibility/Rule 데이터를 공통 eligibility 트리로 억지로 평탄화하지 않는다.
- 공통 `visa_requirements`와 연결 가능한 식별자·출처·유효기간만 검증한다.
- 공식 정원 숫자가 확인되지 않은 상태에서는 quota policy/snapshot 행을 생성하지 않는다.
- 공통 마스터가 D-2 전용 구조를 참조하는 경계와 서비스 소비 제외 범위를 문서화한다.

### 9. 공통 UUID 최종 발급과 매핑 확정

- PR #38(`scripts/uuid_utils.py`, 이슈 #37)의 UUID 생성·검증 유틸리티를 재사용한다. 현재
  main에 병합되지 않은 상태이므로 먼저 병합하거나 v2 통합 브랜치로 가져온다. 새로 구현하지 않는다
  (`CLAUDE.md`의 재발명 금지 원칙).
  - `generate_uuid4()`, `validate_uuid4()`는 수정 없이 그대로 쓴다.
  - `get_or_create_visa_id()`는 v2 `visa_requirements.visa_id` 재사용 로직(같은 `visa_code`면
    기존 ID 유지)에 그대로 맞으므로 그대로 쓴다.
  - `UUID_ID_COLUMNS`가 현재 `{"visa_id", "stage_id", "document_requirement_id"}`로 하드코딩되어
    있어 `assign_new_id`/`ensure_new_id_is_unique`가 다른 컬럼을 거부한다. v2의 나머지 PK
    (`group_id`, `criteria_id`, `score_model_id`, `scoring_item_id`, `relation_id`,
    `quota_policy_id`, `quota_snapshot_id`, `source_document_id`, `mapping_id`, `change_id`)를
    이 집합에 추가하는 작업을 이 단계에 포함한다.
- 모든 변환 행의 대상 테이블, 논리 구조, 출처, 페이지, 유효기간을 먼저 검증한다.
- 검증 완료된 신규 행에만 `uuid_utils`로 UUIDv4를 발급한다.
- 기존 v1 공통 레코드는 기존 UUID를 유지한다.
- `REQ-*`, `SCORE-*`, 원천 criteria UUID는 공통 PK로 사용하지 않는다.
- 발급 결과를 `source_record_mappings.target_record_id`에 기록한다.
- `COPY`, `TRANSFORM`, `MERGE`, `SKIP`, `MANUAL_REVIEW`별 커버리지를 집계하고 원천 행 누락을 검사한다.

### 10. 통합·회귀 검증과 전환

- 비자별 마이그레이션 전후 행 수와 의미 커버리지를 비교한다.
- F-4-R 기존 판정·절차가 유지되는지 회귀 검증한다.
- F-2-R 중첩 논리와 E-7-4R 점수·쿼터 예시를 고정 테스트로 추가한다.
- 첨부관계와 그룹 트리의 자기참조·순환참조를 실패 사례로 테스트한다.
- v2 13개 CSV를 깨끗한 디렉터리에서 재생성해 결과가 결정적인지 확인한다.
- 전체 테스트와 lint를 통과한 뒤 v1→v2 전환 결과와 남은 보류 항목을 README에 기록한다.

## 검증기 세부 계약

### 자격조건

- 비자별 ROOT 그룹이 정확히 하나인지 검사한다.
- ROOT만 `parent_group_id=NULL`인지 검사한다.
- 부모·자식의 `visa_id`가 같은지 검사한다.
- 부모 누락, 자기참조, 간접 순환을 거부한다.
- OR 그룹의 판정 참여 자식/criteria가 2개 이상인지 검사한다.
- `boolean_operator`가 `AND`/`OR`, `criteria_type`이 `NUMERIC`/`TEXT`/`BOOLEAN`/`LIST`/
  `EXISTENCE`, `evaluation_mode`가 `AUTOMATED`/`MANUAL`/`INFORMATIONAL`, `operator`가
  `EQ`/`GT`/`GTE`/`LT`/`LTE`/`IN`/`NOT_IN`/`EXISTS`/`NOT_EXISTS`/`WITHIN` 중 하나인지 검사한다.
- `AUTOMATED` criteria의 `field_identifier`와 `operator`를 필수로 검사한다.
- `MANUAL` criteria는 `operator`가 비어 있어도 되지만 `value_text`가 필수인지 검사한다.
- `INFORMATIONAL` criteria가 계산 대상에서 제외되는지 테스트한다.
- AND 그룹은 `FAIL > REVIEW_REQUIRED > PASS`, OR 그룹은 `PASS > REVIEW_REQUIRED > FAIL` 우선순위로
  자식/criteria 판정을 결합하는지 계산 로직을 fixture로 검증한다.

### 점수표

- 모델과 항목 FK, 구간 경계, 포함 여부, 배점 자료형을 검사한다.
- 배타 그룹과 stacking 규칙의 허용값을 검사한다.
- 미확인 상한·동점 규칙이 임의 숫자로 채워지지 않았는지 fixture로 확인한다.
- 검수 미완료 점수 데이터가 서비스 대상 CSV에 들어오면 실패한다.

### 제출서류

- stage FK와 문서 FK를 검사한다.
- `requirement_status`가 `REQUIRED`/`OPTIONAL`/`CONDITIONAL`/`ALTERNATIVE` 중 하나인지 검사한다.
- 자기 첨부와 간접 순환 첨부를 거부한다.
- `ALTERNATIVE` 행의 대체 그룹과 `CONDITIONAL` 행의 조건 설명을 검사한다.

### 쿼터

- `quota_type`이 `LIMITED`/`UNLIMITED`/`UNKNOWN`, `scope_type`이 `NATIONAL`/`PROVINCE`/
  `MUNICIPALITY`/`INSTITUTION`/`DEPARTMENT`/`OTHER` 중 하나인지 검사한다.
- `UNLIMITED` policy에 snapshot이 없음을 검사한다.
- nullable 숫자를 0으로 해석하지 않는다.
- 관련 네 값이 존재할 때 `consumed_quota = recommended_count - quota_exempt_count`를 검사한다.
- 관련 세 값이 존재할 때 `remaining_quota = allocated_quota - consumed_quota`를 검사한다.
- 모든 수량이 음수가 아닌지 검사한다.
- `consumption_exception`은 자유 텍스트로만 취급하고, 코드(검증기·서비스 로직 어디에도)가 이
  값을 파싱해 개인별 자동 판정에 쓰지 않는지 확인한다.

### 출처·매핑

- 공통 행의 필수 `source_document_id`, `source_page`, 유효기간을 검사한다.
- `source_record_mappings`의 원천 테이블·행이 실제로 존재하는지 검사한다.
- mapping action/status 조합과 대상 테이블 계약을 검사한다.
- 원천 레코드와 대상 레코드의 출처·그룹 경로·유효기간이 일치하는지 독립적으로 검증한다.
- 신규 target UUID가 UUIDv4이고 원천 ID와 다름을 검사한다.

## 테스트 전략

- 단위 테스트: enum, 자료형, UUID, FK, 트리/첨부 순환, 쿼터 계산식
- 변환 테스트: v1 fixture와 각 비자 원천 fixture를 v2 행으로 변환
- 부정 테스트: 부모 누락, 잘못된 대상 테이블, 미확인 값의 0 대체, 원천 UUID 복사
- 회귀 테스트: 기존 F-4-R 결과, E-7-4R 542/246/10/236/306, F-2-R 중첩 OR 경로
- 통합 테스트: 13개 CSV 전체 생성 후 스키마·FK·커버리지 검증

권장 실행 순서:

```bash
uv run python scripts/validate_fk_integrity.py
uv run pytest
uv run python scripts/validate_common_schema_v2.py
```

마지막 명령의 파일명은 구현 단계에서 확정하되 README와 CI에서는 하나의 공식 진입점만 사용한다.

## 권장 커밋 단위

1. `docs: 공통 스키마 v2 명세 확정 (#44)`
2. `schema: v2 CSV 헤더와 schema.py 추가 (#44)`
3. `test: v2 스키마 및 무결성 검증기 추가 (#44)`
4. `migrate: F-4-R v2 이관 (#44)`
5. `migrate: E-7-4R v2 이관 (#44)`
6. `migrate: F-2-R v2 이관 (#44)`
7. `migrate: 제출서류와 D-2 연결 정리 (#44)`
8. `test: 전체 회귀와 원천 매핑 검증 (#44)`
9. `docs: v1에서 v2로의 변환 결과 문서화 (#44)`

## 완료 체크리스트

- [x] v2 명세에 13개 테이블의 컬럼·자료형·enum·null·PK/FK 규칙이 있다.
- [x] 서비스 테이블 10개와 지원 테이블 3개의 실제 헤더가 명세와 일치한다.
- [x] 모든 이관 대상 비자에 eligibility ROOT 그룹이 정확히 하나 있다.
- [x] 조건 그룹에 부모 누락, 비자 불일치, 자기참조, 순환참조가 없다.
- [x] F-2-R의 차단된 복합 조건이 논리 손실 없이 이관된다.
- [x] E-7-4R의 기본 자격과 K-POINT 점수표가 분리된다.
- [x] 점수 모델의 미확인 값은 null이며 검수 미완료 점수는 소비되지 않는다.
- [x] 제출서류의 필수·선택·조건부·대체·첨부관계가 표현된다.
- [x] 첨부관계에 자기참조나 순환참조가 없다.
- [x] F-2-R 시군별 및 E-7-4R 광역별 쿼터 의미가 보존된다.
- [x] E-7-4R 쿼터 집계 542/246/10/236/306이 검증된다.
- [x] F-4-R 기존 UUID, 판정, 절차 결과가 유지된다.
- [x] D-2 전용 구조와 공통 마스터의 연결 경계가 검증·문서화된다.
- [ ] 모든 공통 행에 필요한 출처·페이지·유효기간이 존재한다.
- [x] 원천 ID와 공통 UUID가 분리되고 매핑표로 추적된다.
- [x] FK·UUID·enum·헤더·쿼터·누락·순환 검증 테스트가 통과한다.
- [x] v1→v2 변환 규칙과 비자별 이관 결과·보류 항목이 문서화된다.

미완료 체크 1건은 D-2 부트스트랩 행의 필수 본문·출처 8개가 비어 있기 때문이다. 정확한 목록은
`extraction/common_v2/known_validation_gaps.txt`에서 관리한다.

## 보류·후속 작업

- E-7-4R `REQ-041` 표 조각의 점수 항목 귀속 확인
- F-2-R 학교장 추천 대상범위의 원문 페이지 간 충돌 해소
- D-2 부트스트랩 필수값 8건의 공통 마스터 처리 방향 결정
- #35 점수표의 최신 차수 승계 여부 확인
- E-7-4R 동점처리, 전체 가점 상한, 가점 포함 최종 상한 확인
- `--pdf-root` 기반 PDF 페이지 검증을 실제 사용하는 시점의 manifest 필수화 및 누락 PDF 실패 처리
- PR #23 월별 공고 자동화의 v2 비교 로직 갱신
- 개인별 쿼터 미차감 판정이 필요해질 경우 신청·심사 도메인에서 별도 설계
