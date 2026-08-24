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
- v1 기준 데이터는 `extraction/D_visa_requirements/`에 그대로 보존한 상태에서 변환을 시작한다.
- F-2-R, E-7-4R의 원천 extraction과 검수 상태는 공통 테이블로 복사하지 않고 매핑 근거로 사용한다.

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

### 2. 공통 스키마 v2 명세 확정

`extraction/D_visa_requirements/README.md`를 v2 기준으로 개편하거나 별도 v2 명세를 먼저
작성한다. 각 테이블에 대해 다음을 빠짐없이 정의한다.

- 컬럼명, 자료형, nullable 여부, 기본값
- PK, FK, 유일성, 유효기간 규칙
- enum 허용값과 대소문자
- CSV 직렬화 규칙(JSON 배열, 날짜, null)
- 출처 문서와 페이지 연결 규칙
- 원천 레코드와 공통 레코드의 ID 수명주기
- v1 컬럼의 유지·이동·제거·분리 규칙

특히 아래 계약을 명시적으로 고정한다.

- eligibility 트리는 비자별 ROOT 하나와 `parent_group_id`, `AND/OR`로 표현한다.
- criteria는 `group_id`만으로 소속 비자를 찾고 `visa_id`를 중복 저장하지 않는다.
- `INFORMATIONAL` criteria는 판정에서 제외한다.
- 제출서류 첨부는 문자열이 아닌 관계 테이블로 표현한다.
- 점수 모델과 항목은 자격 criteria와 분리한다.
- 쿼터 정책과 시점별 스냅샷을 분리한다.
- `change_history`는 v1 헤더를 유지한다.

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

### 4. F-4-R v1 → v2 마이그레이션

가장 안정적인 기존 공통 데이터를 먼저 옮겨 변환기의 기준 동작을 확정한다.

- 기존 `visa_id`와 재사용 가능한 v1 공통 UUID를 유지한다.
- 비자별 eligibility ROOT 그룹을 생성하고 기존 평면 criteria를 원문 의미에 맞게 연결한다.
- `total_score_threshold`와 기존 쿼터 컬럼을 `visa_requirements`에서 제거한다.
- F-4-R은 `visa_quota_policies.quota_type=UNLIMITED`만 만들고 snapshot은 만들지 않는다.
- 절차와 제출서류의 기존 결과가 의미 손실 없이 유지되는지 행 단위로 대조한다.
- 기존 출처 문자열을 `source_documents` 행과 FK로 변환한다.

### 5. E-7-4R 마이그레이션

- 기본 신청 자격은 eligibility 트리와 criteria로 이관한다.
- 로컬 `G*` 묶음을 공통 논리 그룹으로 복사하지 않고 원문에서 확인된 AND/OR만 구성한다.
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

- PR #36에서 차단된 복합 조건을 ROOT/중간/말단 그룹으로 재구성한다.
- 일반 경로와 특례 경로를 같은 OR 그룹 아래에 배치하되 원문에서 확인되지 않은 관계는 만들지 않는다.
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

- 모든 변환 행의 대상 테이블, 논리 구조, 출처, 페이지, 유효기간을 먼저 검증한다.
- 검증 완료된 신규 행에만 UUIDv4를 발급한다.
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
- `AUTOMATED` criteria의 `field_identifier`와 `operator`를 필수로 검사한다.
- `INFORMATIONAL` criteria가 계산 대상에서 제외되는지 테스트한다.

### 점수표

- 모델과 항목 FK, 구간 경계, 포함 여부, 배점 자료형을 검사한다.
- 배타 그룹과 stacking 규칙의 허용값을 검사한다.
- 미확인 상한·동점 규칙이 임의 숫자로 채워지지 않았는지 fixture로 확인한다.
- 검수 미완료 점수 데이터가 서비스 대상 CSV에 들어오면 실패한다.

### 제출서류

- stage FK와 문서 FK를 검사한다.
- 자기 첨부와 간접 순환 첨부를 거부한다.
- `ALTERNATIVE` 행의 대체 그룹과 `CONDITIONAL` 행의 조건 설명을 검사한다.

### 쿼터

- `UNLIMITED` policy에 snapshot이 없음을 검사한다.
- nullable 숫자를 0으로 해석하지 않는다.
- 관련 네 값이 존재할 때 `consumed_quota = recommended_count - quota_exempt_count`를 검사한다.
- 관련 세 값이 존재할 때 `remaining_quota = allocated_quota - consumed_quota`를 검사한다.
- 모든 수량이 음수가 아닌지 검사한다.

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

- [ ] v2 명세에 13개 테이블의 컬럼·자료형·enum·null·PK/FK 규칙이 있다.
- [ ] 서비스 테이블 10개와 지원 테이블 3개의 실제 헤더가 명세와 일치한다.
- [ ] 모든 이관 대상 비자에 eligibility ROOT 그룹이 정확히 하나 있다.
- [ ] 조건 그룹에 부모 누락, 비자 불일치, 자기참조, 순환참조가 없다.
- [ ] F-2-R의 차단된 복합 조건이 논리 손실 없이 이관된다.
- [ ] E-7-4R의 기본 자격과 K-POINT 점수표가 분리된다.
- [ ] 점수 모델의 미확인 값은 null이며 검수 미완료 점수는 소비되지 않는다.
- [ ] 제출서류의 필수·선택·조건부·대체·첨부관계가 표현된다.
- [ ] 첨부관계에 자기참조나 순환참조가 없다.
- [ ] F-2-R 시군별 및 E-7-4R 광역별 쿼터 의미가 보존된다.
- [ ] E-7-4R 쿼터 집계 542/246/10/236/306이 검증된다.
- [ ] F-4-R 기존 UUID, 판정, 절차 결과가 유지된다.
- [ ] D-2 전용 구조와 공통 마스터의 연결 경계가 검증·문서화된다.
- [ ] 모든 공통 행에 필요한 출처·페이지·유효기간이 존재한다.
- [ ] 원천 ID와 공통 UUID가 분리되고 매핑표로 추적된다.
- [ ] FK·UUID·enum·헤더·쿼터·누락·순환 검증 테스트가 통과한다.
- [ ] v1→v2 변환 규칙과 비자별 이관 결과·보류 항목이 문서화된다.

## 보류·후속 작업

- #35 점수표의 최신 차수 승계 여부 확인
- E-7-4R 동점처리, 전체 가점 상한, 가점 포함 최종 상한 확인
- `--pdf-root` 기반 PDF 페이지 검증을 실제 사용하는 시점의 manifest 필수화 및 누락 PDF 실패 처리
- PR #23 월별 공고 자동화의 v2 비교 로직 갱신
- 개인별 쿼터 미차감 판정이 필요해질 경우 신청·심사 도메인에서 별도 설계

