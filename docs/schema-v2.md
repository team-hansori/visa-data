# 공통 스키마 v2 명세

관련 이슈: [#44 — 공통 스키마 v2 정의 및 비자 데이터 마이그레이션](https://github.com/team-hansori/visa-data/issues/44)

이 문서는 이슈 #44 댓글에서 결정된 내용을 반영한 공통 스키마 v2 확정안이다. v1 공통 마스터는
`extraction/D_visa_requirements/README.md`에 그대로 유지하고, v2는 이 폴더에서 별도로 관리한다.

## 요약

#35와 #40 양쪽이 공통으로 사용하는 핵심은 아래 5개다.

1. `visa_requirements`
    - 비자 유형의 기본정보
2. `visa_requirement_criteria`
    - 개별 자격조건
    - v2에서는 `visa_criterion_groups`에 연결
3. `visa_process_stages`
    - 신청·추천·심사 등 절차 단계
4. `document_requirements`
    - 단계별 제출서류
5. `source_documents`
    - 각 데이터의 근거가 된 공고문·지침·첨부문서

관계는 이렇게 보면 된다.

```
source_documents
       │ 근거
       ▼
visa_requirements
 ├─ visa_criterion_groups
 │    └─ visa_requirement_criteria
 ├─ visa_process_stages
 │    └─ document_requirements
 ├─ visa_scoring_models / items    ← 점수제가 있을 때만
 └─ visa_quota_policies / snapshots ← 쿼터가 있을 때만
```

즉, v2의 실질적인 최소 코어는 다음 6개다.

```
source_documents
visa_requirements
visa_criterion_groups
visa_requirement_criteria
visa_process_stages
document_requirements
```

여기에 비자별 필요에 따라 점수표·첨부관계·쿼터가 붙는다. `change_history`와 `source_record_mappings`는
서비스 판정용 코어가 아니라 변경 추적·이관 관리용이다.

확정안은 **서비스 공통 테이블 10개 + 근거·이관용 테이블 3개**, 총 13개다.

댓글에서 결정된 내용을 우선 적용했다.

- 자격조건 트리: v2에 추가
- 제출서류 첨부관계: 관계 테이블 방식으로 진행
- 쿼터: 정책/스냅샷 2개로 분리
- 변경 이력: v1 구조 유지
- 별도 상태관리 테이블: 만들지 않음
- 점수표: #35의 모델 구조 + #40의 점수 데이터
- 공통 UUID: 실제 이관 마지막 단계에 발급

근거: 공통 스키마 v2 논의(#44)

## 기존 공통 스키마와의 차이

**기존 공통 스키마의 서비스 테이블은 5개**

1. `visa_requirements`
2. `visa_requirement_criteria`
3. `visa_process_stages`
4. `document_requirements`
5. `visa_quota_status`

**10개는 기존 5개에 v2 요구사항을 반영해 분리·추가한 결과**

| 기존 영역 | v2 구조 | 변화 |
| --- | --- | --- |
| 비자 기본정보 | `visa_requirements` | 유지 |
| 자격조건 | `visa_criterion_groups` + `visa_requirement_criteria` | 그룹 테이블 1개 추가 |
| 절차 | `visa_process_stages` | 유지 |
| 제출서류 | `document_requirements` + `document_attachment_relations` | 첨부 관계 1개 추가 |
| 쿼터 | `visa_quota_policies` + `visa_quota_snapshots` | 기존 1개를 2개로 재구성 |
| 점수표 | `visa_scoring_models` + `visa_scoring_items` | 2개 신규 추가 |

따라서 계산하면:

```
기존 5개
+ 자격조건 그룹 1개
+ 제출서류 첨부관계 1개
+ 점수표 2개
+ 쿼터 분리로 순증 1개
= 총 10개
```

여기에 서비스 테이블이 아닌 다음 3개를 별도로 계산해서 전체 13개.

- `source_documents`
- `change_history`
- `source_record_mappings`

즉, **기존 5개가 갑자기 13개가 된 것이 아니라 서비스 구조는 5개 → 10개이고, 나머지 3개는 관리·이관용**이다.

# 상세 설명

## 전체 테이블

| 영역 | 테이블 |
| --- | --- |
| 출처 | `source_documents` |
| 비자 기본정보 | `visa_requirements` |
| 자격조건 | `visa_criterion_groups`, `visa_requirement_criteria` |
| 점수표 | `visa_scoring_models`, `visa_scoring_items` |
| 절차·서류 | `visa_process_stages`, `document_requirements`, `document_attachment_relations` |
| 쿼터 | `visa_quota_policies`, `visa_quota_snapshots` |
| 변경 이력 | `change_history` |
| 원천→공통 이관 | `source_record_mappings` |

논리 테이블명에는 `.csv`를 붙이지 않는다. 실제 파일만 `visa_requirements.csv`처럼 저장한다.

---

## 1. `source_documents`

공고문·붙임·개정문을 공통적으로 식별하는 출처 목록이다.

| 컬럼 | 값·형식 |
| --- | --- |
| `source_document_id` | 공통 UUID, PK |
| `source_document_key` | 원천 식별값. 예: `r17_announcement_2026_df1fdde9` |
| `visa_id` | `visa_requirements.visa_id`, nullable |
| `document_type` | `ANNOUNCEMENT`, `ATTACHMENT`, `AMENDMENT`, `GUIDELINE`, `FORM`, `OTHER` |
| `document_name` | 공고문 파일명 또는 공식 문서명 |
| `notice_round` | `8`, `9`, `17` 등. 차수 없는 문서는 null |
| `published_at` | 공고일 |
| `source_location` | 저장 경로 또는 원문 URL |
| `file_hash_sha256` | 원문 파일 변경 확인용 |
| `page_basis` | `PDF`, `HWPX`, `CONVERTED_PDF`, `OTHER` |
| `last_verified_at` | 마지막 검증일 |

`source_text`, 블록 번호, 표 번호, 추출 상태는 공통 마스터에 반복하지 않고 각 원천·검수 계층에 유지한다.

---

## 2. `visa_requirements`

비자 유형당 한 행을 갖는 기본 마스터다.

| 컬럼 | 값·형식 |
| --- | --- |
| `visa_id` | 공통 UUID, PK |
| `visa_code` | `F-2-R`, `E-7-4R`, `F-4-R`, `D-2` |
| `visa_name_kr` | 비자 한글명 |
| `program_type` | `REGIONAL_SPECIALIZED`, `STUDENT`, `OTHER` |
| `target_regions_json` | 예: `["제천시","보은군"]` |
| `residency_limit_years` | `2`, `5` 등. 없으면 null |
| `allowed_industries_json` | 허용 업종 목록. 없으면 null |
| `application_method` | 방문접수 등 원문 기반 텍스트 |
| `next_visa_code` | 예: `F-5-6R`, 없으면 null |
| `valid_from` | 적용 시작일 |
| `valid_to` | 적용 종료일, 계속 유효하면 null |
| `source_document_id` | 출처 FK |
| `source_page` | 예: `2`, `2,5` |
| `last_verified_at` | 마지막 검증일 |

다음 v1 컬럼은 여기서 제거한다.

- `total_score_threshold` → `visa_scoring_models`
- `quota_type`, `total_quota`, `quota_shared_with` → 쿼터 테이블

---

## 3. `visa_criterion_groups`

비자 신청 자격조건을 중첩된 AND/OR 논리식으로 표현하는 테이블이다.

그룹은 단순한 업무 분류가 아니라, 직속 criteria와 자식 그룹의 판정 결과를 결합하는 **논리 괄호**다.

비자마다 ROOT 그룹을 정확히 하나 생성한다. 일반적인 필수조건은 ROOT에 직접 연결하고, 명확한 대체조건이나
경로가 있을 때만 하위 `OR` 그룹을 추가한다.

### 컬럼

| 컬럼 | 값·형식 | 필수 | 설명 |
| --- | --- | --- | --- |
| `group_id` | UUID, PK | O | 공통 그룹 식별자 |
| `visa_id` | UUID, FK → `visa_requirements.visa_id` | O | 그룹이 속한 비자. ROOT와 모든 자식 그룹에 저장 |
| `parent_group_id` | UUID, FK → `visa_criterion_groups.group_id` | ROOT 제외 O | 상위 그룹. ROOT만 `NULL` |
| `group_key` | text | O | 사람이 읽을 수 있는 그룹 슬러그 |
| `group_name_kr` | text | O | 화면에 표시할 그룹명 |
| `boolean_operator` | enum(`AND`, `OR`) | O | 직속 criteria와 자식 그룹 결과의 결합 방식 |
| `applicability_note` | text |  | 그룹 적용 조건과 해석상 주의사항 |
| `display_order` | int | O | 같은 부모 아래 표시·평가 순서 |
| `valid_from` | date | O | 논리구조 적용 시작일 |
| `valid_to` | date |  | 적용 종료일. 계속 유효하면 `NULL` |
| `source_document_id` | UUID, FK → `source_documents.source_document_id` | O | AND/OR 관계를 확인한 근거 문서 |
| `source_page` | text | O | 논리관계 근거 페이지 |
| `last_verified_at` | date 또는 timestamp | O | 마지막 검증일 |

### 제거한 컬럼

#### `group_scope`

`visa_criterion_groups`는 eligibility 전용 테이블로 제한하므로 제거한다.

기존 scope는 다음처럼 처리한다.

| 기존 값 | v2 처리 |
| --- | --- |
| `ELIGIBILITY` | `visa_criterion_groups`에 유지 |
| `EXCEPTION` | 일반 조건과 특례 조건을 `OR` 경로로 표현 |
| `PROCEDURE` | `visa_process_stages`로 이동 |
| `POST_APPROVAL` | 안내 데이터로 보존하고 자동 자격판정에서 제외 |
| `DEPENDENT_FAMILY` | 해당 F-3 계열 비자의 별도 자격 트리로 구성 |

#### `is_exception_of`

사용하지 않는다.

특례가 어떤 일반 조건을 대체하는지는 별도 FK 명령으로 표현하지 않고, 일반 경로와 특례 경로를 같은
`OR` 그룹 아래에 배치한다.

### 무결성 규칙

- 비자별 ROOT 그룹은 정확히 하나여야 한다.
- ROOT 그룹만 `parent_group_id=NULL`이어야 한다.
- 모든 자식 그룹에도 `visa_id`를 저장한다.
- 부모 그룹과 자식 그룹의 `visa_id`는 같아야 한다.
- `(visa_id, group_key)`는 유일해야 한다.
- `group_id=parent_group_id`는 허용하지 않는다.
- `parent_group_id` 연결에 순환참조가 없어야 한다.
- `OR` 그룹은 판정에 참여하는 자식 그룹 또는 직속 criteria가 두 개 이상이어야 한다.
- 원문에서 확인되지 않은 AND/OR 관계를 추정해서 만들지 않는다.
- 비자 최초 자격판정에 사용하지 않는 절차·설명은 그룹 트리에 넣지 않는다.

### 그룹 계산 규칙

한 그룹의 판정값은 다음을 모두 모아 `boolean_operator`로 결합한 결과다.

- 해당 그룹에 직접 연결된 criteria
- 해당 그룹의 자식 그룹 판정 결과
- AND: FAIL > REVIEW_REQUIRED > PASS
- OR: PASS > REVIEW_REQUIRED > FAIL
- INFORMATIONAL: excluded from calculation

예:

```
ROOT (AND)
├─ 체류기간 >= 2년
├─ 현재 합법적으로 근로 중
└─ language_paths (OR)
   ├─ TOPIK 3급 이상
   ├─ 사회통합프로그램 3단계 이상
   └─ 사전평가 4단계 이상
```

계산식:

```
체류기간 >= 2년
AND 현재 합법적으로 근로 중
AND
(
  TOPIK 3급 이상
  OR 사회통합프로그램 3단계 이상
  OR 사전평가 4단계 이상
)
```

### F-2-R 소상공인 특례 예시

```
employer (AND)
├─ 국세·지방세 체납 없음
├─ 고용주 결격사유 없음
└─ employment_capacity_paths (OR)
   ├─ standard_employment_capacity (AND)
   │  └─ 일반 고용인원 기준
   └─ small_business_exception (AND)
      ├─ 소상공인 또는 농업법인
      ├─ 허용 업종
      ├─ 사업 운영기간 3년 이상
      └─ 매출액 기준 충족
```

계산식:

```
국세·지방세 체납 없음
AND 고용주 결격사유 없음
AND
(
  일반 고용인원 기준
  OR
  소상공인 특례 기준
)
```

### 그룹 행 예시

| group_id | visa_id | parent_group_id | group_key | group_name_kr | boolean_operator |
| --- | --- | --- | --- | --- | --- |
| `G-EMPLOYER` | `F-2-R_UUID` | `G-ROOT` | `employer` | 고용주·고용기업 요건 | `AND` |
| `G-CAPACITY` | `F-2-R_UUID` | `G-EMPLOYER` | `employment_capacity_paths` | 고용 허용인원 경로 | `OR` |
| `G-STANDARD` | `F-2-R_UUID` | `G-CAPACITY` | `standard_employment_capacity` | 일반 고용인원 기준 | `AND` |
| `G-SMALL` | `F-2-R_UUID` | `G-CAPACITY` | `small_business_exception` | 지역활력 소상공인 고용특례 | `AND` |

실제 공통 데이터에서는 `G-SMALL` 같은 예시 문자열이 아니라 검증 후 발급한 UUIDv4를 사용한다.

---

## 4. `visa_requirement_criteria`

자격 여부를 판정하는 원자적 조건을 저장한다.

criteria는 트리의 최말단 그룹에만 연결되는 것이 아니다. 실제 조건이라면 ROOT나 중간 그룹에도 직접
연결할 수 있다.

`visa_id`는 criteria에 중복 저장하지 않는다. 소속 비자는 다음 경로로 확인한다.

```
criteria.group_id
→ visa_criterion_groups.group_id
→ visa_criterion_groups.visa_id
```

### 컬럼

| 컬럼 | 값·형식 | 필수 | 설명 |
| --- | --- | --- | --- |
| `criteria_id` | UUID, PK | O | 공통 조건 식별자 |
| `group_id` | UUID, FK → `visa_criterion_groups.group_id` | O | 조건이 직접 속한 논리 그룹 |
| `criteria_name` | text | O | 조건 표시명 |
| `field_identifier` | text | `AUTOMATED`일 때 O | 사용자 데이터에서 읽을 필드 식별자 |
| `criteria_type` | enum(`NUMERIC`, `TEXT`, `BOOLEAN`, `LIST`, `EXISTENCE`) | O | 비교 대상 값의 자료형 |
| `evaluation_mode` | enum(`AUTOMATED`, `MANUAL`, `INFORMATIONAL`) | O | 조건 처리 방식 |
| `operator` | 공통 operator enum | `AUTOMATED`일 때 O | 비교 연산자 |
| `value_numeric` | numeric |  | 숫자 기준값 |
| `value_text` | text | O | 조건 원문 또는 사람이 이해할 수 있는 판정 기준 |
| `unit` | text |  | `YEAR`, `MONTH`, `KRW`, `PERSON`, `AGE`, `LEVEL` 등 |
| `measurement_window_value` | numeric |  | 최근 N년 등 측정기간 숫자 |
| `measurement_window_unit` | enum(`YEAR`, `MONTH`, `DAY`) |  | 측정기간 단위 |
| `special_case_note` | text |  | 예외·재량판단·구조화하지 못한 단서 |
| `display_order` | int | O | 같은 그룹 안에서 표시·평가 순서 |
| `valid_from` | date | O | 조건 적용 시작일 |
| `valid_to` | date |  | 조건 적용 종료일 |
| `source_document_id` | UUID, FK → `source_documents.source_document_id` | O | 조건 근거 문서 |
| `source_page` | text | O | 조건 근거 페이지 |
| `last_verified_at` | date 또는 timestamp | O | 마지막 검증일 |

### `evaluation_mode`

| 값 | 내부 의미 | 서비스 처리 |
| --- | --- | --- |
| `AUTOMATED` | 사용자 입력과 연산자로 자동 계산 가능 | `PASS` 또는 `FAIL` 계산 |
| `MANUAL` | 자동 판정 범위 밖이라 별도 확인 필요 | `REVIEW_REQUIRED` 반환 |
| `INFORMATIONAL` | 판정조건이 아닌 보충설명 | 계산에서 제외하고 안내만 표시 |

`MANUAL`은 우리 관리자가 법적 자격을 확정한다는 의미가 아니다.

내부 데이터에는 단순히:

```
evaluation_mode=MANUAL
```

로 저장하고, UI에서는 다음처럼 표시할 수 있다.

```
추가 확인이 필요한 조건입니다.
최종 판단은 관련 기관의 심사 결과에 따라 달라질 수 있습니다.
```

### 공통 operator enum

```
EQ
GT
GTE
LT
LTE
IN
NOT_IN
EXISTS
NOT_EXISTS
WITHIN
```

공통 데이터에는 다음 기호를 직접 저장하지 않는다.

```
=
==
>=
<=
```

변환 예:

| 원천 표현 | 공통 operator |
| --- | --- |
| `=` 또는 `==` | `EQ` |
| `>` | `GT` |
| `>=` | `GTE` |
| `<` | `LT` |
| `<=` | `LTE` |
| 목록 중 하나 | `IN` |
| 목록에 포함되지 않음 | `NOT_IN` |
| 존재함 | `EXISTS` |
| 존재하지 않음 | `NOT_EXISTS` |
| 특정 기간 이내 | `WITHIN` |

### 값 저장 규칙

#### 숫자 조건

```
criteria_type=NUMERIC
operator=GTE
value_numeric=2
unit=YEAR
```

#### 목록 조건

CSV에서는 `value_text`에 JSON 배열 문자열을 저장한다.

```
criteria_type=LIST
operator=IN
value_text=["E-9","E-10","H-2"]
```

Supabase/PostgreSQL 적재 시 배열 또는 JSONB로 변환할지는 서비스 구현 단계에서 결정할 수 있다.

#### 존재 여부 조건

```
criteria_type=EXISTENCE
operator=NOT_EXISTS
field_identifier=employer.tax_arrears
value_text=국세·지방세 체납 사실이 없어야 함
```

#### 자동 판정이 어려운 조건

```
evaluation_mode=MANUAL
operator=NULL
value_numeric=NULL
value_text=현재 근무처에서 합법적으로 근로 중인지 확인
```

#### 보충설명

```
evaluation_mode=INFORMATIONAL
operator=NULL
value_text=체류기간은 허용된 체류자격별 기간을 합산하여 계산
```

### 무결성 규칙

- `criteria.group_id`는 반드시 존재하는 그룹을 참조해야 한다.
- `AUTOMATED requires field_identifier and operator`
- `MANUAL`이면 `operator`는 `NULL`일 수 있지만 `value_text`는 필수다.
- `INFORMATIONAL`은 자격 판정 결과에 포함하지 않는다.
- `NUMERIC`이면 일반적으로 `value_numeric`이 필요하다.
- `LIST`이면 `value_text`에 유효한 목록 형식이 필요하다.
- `EXISTENCE`는 `EXISTS` 또는 `NOT_EXISTS`를 사용한다.
- 조건의 유효기간은 소속 그룹의 유효기간을 벗어나면 안 된다.
- 공통 마스터에는 검수 완료된 조건만 적재한다.
- 원천 `REQ-*`나 #35의 criteria UUID를 공통 `criteria_id`로 복사하지 않는다.
- 원천 ID와 공통 UUID의 관계는 `source_record_mappings`에 기록한다.

---

## 실제 F-2-R criteria 예시

### 국세·지방세 체납 없음

```
criteria_id=C-TAX
group_id=G-EMPLOYER
criteria_name=국세·지방세 체납 없음
field_identifier=employer.tax_arrears
criteria_type=EXISTENCE
evaluation_mode=AUTOMATED
operator=NOT_EXISTS
value_numeric=NULL
value_text=고용업체의 국세·지방세 체납 사실이 없어야 함
unit=NULL
display_order=90
valid_from=공고 적용 시작일
valid_to=NULL
source_document_id=공통 출처 UUID
source_page=6
last_verified_at=2026-08-18
```

### 소상공인 특례 사업기간

```
criteria_id=C-SMALL-DURATION
group_id=G-SMALL
criteria_name=사업 운영기간
field_identifier=employer.business_operation_years
criteria_type=NUMERIC
evaluation_mode=AUTOMATED
operator=GTE
value_numeric=3
value_text=사업 운영기간 3년 이상
unit=YEAR
display_order=103
valid_from=2026-05-18
valid_to=2027-12-31
source_document_id=공통 출처 UUID
source_page=6
last_verified_at=2026-08-18
```

### 소상공인 특례 매출액

원문은 다음 두 경로 중 하나를 허용한다.

```
전년도 매출액 1억원 이상
OR
최근 2년 평균 매출액 1억원 이상
```

그룹은 다음처럼 구성한다.

```
small_business_exception (AND)
└─ sales_paths (OR)
   ├─ previous_year_sales (AND)
   │  └─ 전년도 매출액 >= 1억원
   └─ two_year_average_sales (AND)
      └─ 최근 2년 평균 매출액 >= 1억원
```

두 criteria 행:

```
criteria_name=전년도 매출액
field_identifier=employer.previous_year_revenue
criteria_type=NUMERIC
evaluation_mode=AUTOMATED
operator=GTE
value_numeric=100000000
unit=KRW
```

```
criteria_name=최근 2년 평균 매출액
field_identifier=employer.average_revenue
criteria_type=NUMERIC
evaluation_mode=AUTOMATED
operator=GTE
value_numeric=100000000
unit=KRW
measurement_window_value=2
measurement_window_unit=YEAR
```

원문 의미나 입력 필드를 확정하지 못했다면 두 행을 억지로 자동화하지 않고 하나의 criteria로 보존한다.

```
criteria_name=소상공인 특례 매출액
evaluation_mode=MANUAL
operator=NULL
value_text=전년도 매출액 1억원 이상. 미달 시 최근 2년 평균액 1억원 이상도 허용
```

---

## 5. `visa_scoring_models`

"이 점수표가 무엇을 위한 것인지"와 전체 상한·합격선·동점처리를 저장한다.

| 컬럼 | 값·형식 |
| --- | --- |
| `score_model_id` | 공통 UUID, PK |
| `visa_id` | 비자 FK |
| `model_name_kr` | 점수표 명칭 |
| `model_purpose` | `PASS_THRESHOLD`, `QUOTA_RANKING`, `BOTH`, `UNKNOWN` |
| `applies_when` | `ALWAYS`, `APPLICATIONS_EXCEED_QUOTA`, `UNKNOWN` |
| `selection_rule` | `HIGHEST_TOTAL_SCORE_FIRST`, `THRESHOLD_ONLY` 등 |
| `tie_breaker_rule` | 동점처리 규칙. 없거나 미확인이면 null |
| `base_maximum_points` | 기본항목 만점 |
| `minimum_required_points` | 합격 최소점수 |
| `final_maximum_points` | 가점 포함 최종 상한. 미확인이면 null |
| `bonus_cap_points` | 전체 가점 상한. 미확인이면 null |
| `penalty_cap_points` | 전체 감점 상한의 절댓값 |
| `from_round` | 적용 시작 차수 |
| `to_round` | 적용 종료 차수, 계속이면 null |
| `valid_from`, `valid_to` | 적용 기간 |
| `source_document_id`, `source_page` | 출처 |
| `notes` | 조사상 주의사항 |

예시:

```
F-2-R
model_purpose       = QUOTA_RANKING
applies_when        = APPLICATIONS_EXCEED_QUOTA
base_maximum_points = 100
tie_breaker_rule    = YOUNGER_APPLICANT_FIRST
```

다만 현재 #35 점수표는 9차 자료가 17차에도 유지되는지 미검증이므로, 검증 전에는 공통 마스터에 넣지 않는다.

```
E-7-4R
model_purpose          = PASS_THRESHOLD
base_maximum_points    = 300
minimum_required_points = 200
penalty_cap_points     = 50
final_maximum_points   = null  # 가점 포함 최종 상한 미확인
bonus_cap_points       = null  # 전체 가점 상한 미확인
tie_breaker_rule       = null  # 조사되지 않음
```

숫자가 불명확할 때 임의로 `300` 등을 넣지 않고 null로 둔다.

---

## 6. `visa_scoring_items`

점수표의 실제 구간·항목·가점·감점을 저장한다.

| 컬럼 | 값·형식 |
| --- | --- |
| `scoring_item_id` | 공통 UUID, PK |
| `score_model_id` | 점수 모델 FK |
| `score_group` | `BASE`, `BONUS`, `PENALTY` |
| `category` | `INCOME`, `LANGUAGE`, `AGE`, `RECOMMENDATION`, `TENURE` 등 |
| `criterion` | 점수 조건 설명 |
| `min_value`, `max_value` | 구간 하한·상한 |
| `min_inclusive`, `max_inclusive` | 포함 여부 boolean |
| `value_text` | 숫자로 표현하기 어려운 조건 |
| `unit` | `KRW`, `AGE`, `YEAR`, `TOPIK_GRADE` 등 |
| `measurement_window_value` | 예: 최근 `2`년 |
| `measurement_window_unit` | `YEAR`, `MONTH` |
| `points` | 배점. 감점은 `-5`, `-10` |
| `maximum_points` | 해당 항목군 상한 |
| `is_mandatory` | 필수 평가항목 여부 |
| `minimum_required_points` | 항목별 최저점 |
| `exclusive_group` | 중복 불가 그룹. 예: `RECOMMENDATION_SOURCE` |
| `stacking_rule` | `STACK`, `ONE_OF`, `MAX_SCORE_ONLY`, `UNKNOWN` |
| `evidence_document` | 필요한 증빙서류명 |
| `display_order` | 표시 순서 |
| `valid_from`, `valid_to` | 적용 기간 |
| `source_document_id`, `source_page` | 출처 |

#40의 중앙부처 추천 30점과 광역지자체 추천 50점은 다음처럼 저장한다.

```
exclusive_group = RECOMMENDATION_SOURCE
stacking_rule    = MAX_SCORE_ONLY
```

즉 두 추천 점수를 합산하지 않는다.

---

## 7. `visa_process_stages`

v1 절차 구조를 유지하되 상태관리 컬럼은 제거한다.

| 컬럼 | 값·형식 |
| --- | --- |
| `stage_id` | 공통 UUID, PK |
| `visa_id` | 비자 FK |
| `stage_order` | `1`, `2`, `3` |
| `stage_code` | `NOTICE_PUBLICATION`, `APPLICATION_SUBMISSION` 등 |
| `stage_name_kr` | 한글 단계명 |
| `actor_from` | 수행 주체 |
| `actor_to` | 전달 대상 |
| `stage_start_date`, `stage_end_date` | 단계 기간 |
| `notice_round` | 적용 차수 |
| `notes` | 세부 절차 |
| `valid_from`, `valid_to` | 유효기간 |
| `source_document_id`, `source_page` | 출처 |
| `last_verified_at` | 검증일 |

v1의 `document_requirements_status`는 공통 마스터에서 제거한다.

---

## 8. `document_requirements`

#35·#40·기존 공통 구조를 합친 제출서류 테이블이다.

| 컬럼 | 값·형식 |
| --- | --- |
| `document_requirement_id` | 공통 UUID, PK |
| `stage_id` | 제출 절차 단계 FK |
| `document_name` | 서류명 |
| `document_category` | `APPLICATION`, `IDENTITY`, `EDUCATION`, `INCOME`, `EMPLOYMENT`, `RESIDENCE`, `RECOMMENDATION`, `FAMILY`, `OTHER` |
| `filled_by` | 작성자 |
| `submitted_by` | 제출자 |
| `submission_target` | 제출처 |
| `signer` | 서명자 |
| `requirement_status` | `REQUIRED`, `OPTIONAL`, `CONDITIONAL`, `ALTERNATIVE` |
| `alternative_group` | 예: `EMPLOYMENT_PROOF` |
| `condition_note` | 조건 설명 |
| `display_order` | 표시 순서 |
| `valid_from`, `valid_to` | 적용 기간 |
| `source_document_id`, `source_page` | 출처 |
| `last_verified_at` | 검증일 |
| `notes` | 기타 설명 |

`is_mandatory`와 `required_attachments`는 제거한다.

- `is_mandatory` → `requirement_status`
- `required_attachments` → 아래 관계 테이블

---

## 9. `document_attachment_relations`

어떤 서류에 무엇을 첨부하는지 저장한다.

| 컬럼 | 값·형식 |
| --- | --- |
| `relation_id` | 공통 UUID, PK |
| `parent_document_id` | 첨부를 요구하는 서류 FK |
| `attachment_document_id` | 첨부되는 서류 FK |
| `requirement_status` | `REQUIRED`, `OPTIONAL`, `CONDITIONAL`, `ALTERNATIVE` |
| `alternative_group` | 대체 첨부 그룹 |
| `condition_note` | 예: `취업자인 경우` |
| `display_order` | 첨부 표시 순서 |
| `valid_from`, `valid_to` | 적용 기간 |
| `source_document_id`, `source_page` | 관계 근거 |

제약조건:

```
parent_document_id != attachment_document_id
순환 첨부관계 금지
```

---

## 10. `visa_quota_policies`

비자에 쿼터가 존재하는지 관리한다.

| 컬럼 | 값·형식 |
| --- | --- |
| `quota_policy_id` | 공통 UUID, PK |
| `visa_id` | 비자 FK |
| `quota_type` | `LIMITED`, `UNLIMITED`, `UNKNOWN` |
| `quota_unit` | `PERSON`, `CASE`, `SEAT`, `OTHER` |
| `valid_from`, `valid_to` | 정책 유효기간 |
| `source_document_id`, `source_page` | 출처 |

값 적용:

```
F-2-R   = LIMITED
E-7-4R  = LIMITED
F-4-R   = UNLIMITED
D-2     = 조사 전에는 행 없음
```

D-2를 조사했지만 공식 자료에서 확인할 수 없을 때만 `UNKNOWN`을 사용한다.

---

## 11. `visa_quota_snapshots`

차수·지역·기관별 실제 배정, 추천, 차감 및 잔여 수량을 저장한다.

| 컬럼 | 값·형식 |
| --- | --- |
| `quota_snapshot_id` | 공통 UUID, PK |
| `quota_policy_id` | 쿼터 정책 FK |
| `notice_round` | 공고 차수 |
| `as_of_date` | 해당 수량의 기준일 |
| `scope_type` | `NATIONAL`, `PROVINCE`, `MUNICIPALITY`, `INSTITUTION`, `DEPARTMENT`, `OTHER` |
| `scope_name` | 충청북도, 제천시, 화학과 등 |
| `parent_scope_name` | 상위 지역·기관 |
| `allocated_quota` | 전체 배정 인원 |
| `recommended_count` | 전체 추천 인원, nullable |
| `quota_exempt_count` | 추천됐지만 쿼터에서 미차감된 인원, nullable |
| `consumed_quota` | 실제 쿼터 차감 인원 |
| `remaining_quota` | 잔여 인원 |
| `consumption_exception` | 쿼터 미소모 대상과 사유에 관한 원문 설명 |
| `valid_from`, `valid_to` | 스냅샷 적용기간 |
| `source_document_id`, `source_page` | 출처 |
| `recorded_at` | 적재 시각 |

`recommended_count`와 `quota_exempt_count`는 모든 비자에 공통으로 발생하는 값이 아니므로 nullable로
둔다. 공식 자료에서 확인되지 않은 값을 `0`으로 채우지 않는다.

### F-2-R 예시

| 컬럼 | 값 |
| --- | --- |
| `scope_type` | `MUNICIPALITY` |
| `scope_name` | 제천시 |
| `parent_scope_name` | 충청북도 |
| `allocated_quota` | 75 |
| `recommended_count` | `null` |
| `quota_exempt_count` | `null` |
| `consumed_quota` | 42 |
| `remaining_quota` | 33 |
| `consumption_exception` | `null` |

### E-7-4R 예시

| 컬럼 | 값 |
| --- | --- |
| `scope_type` | `PROVINCE` |
| `scope_name` | 충청북도 |
| `allocated_quota` | 542 |
| `recommended_count` | 246 |
| `quota_exempt_count` | 10 |
| `consumed_quota` | 236 |
| `remaining_quota` | 306 |
| `consumption_exception` | 직전 자격이 E-7-4인 E-7-4R 추천 대상자는 쿼터 미소모 |

### 확정 규칙

| 컬럼 | 정의 |
| --- | --- |
| `allocated_quota` | 최초 배정량 |
| `recommended_count` | 추천된 전체 인원 |
| `quota_exempt_count` | 추천 인원 중 쿼터 미차감 인원 |
| `consumed_quota` | 실제 쿼터 차감 인원 |
| `remaining_quota` | 남은 쿼터 |

관련 값이 **모두 존재할 때만** 다음 검증식을 적용한다.

```
consumed_quota
= recommended_count - quota_exempt_count

remaining_quota
= allocated_quota - consumed_quota
```

### 추가 적용 원칙

- `recommended_count`, `quota_exempt_count`는 nullable이다.
- `NULL`은 `0`을 의미하지 않는다.
- 공식 공고 또는 집계 자료에서 확인된 숫자만 저장한다.
- `consumption_exception`은 개인별 자동 판정 규칙이 아니라 원문 설명 보존용이다.
- 개인의 쿼터 미소모 여부와 심사 결과는 공통 스키마 v2에 저장하지 않는다.
- 모든 관련 수치가 확인되지 않았다면 위 검증식을 강제하지 않는다.

---

## 12. `change_history`

댓글 결정대로 현재 v1 헤더를 그대로 유지한다.

| 컬럼 | 값·형식 |
| --- | --- |
| `change_id` | UUID, PK |
| `visa_id` | 비자 FK |
| `table_name` | 확장자 없는 이름. 예: `visa_requirements` |
| `field_identifier` | 변경된 컬럼명 |
| `from_round`, `to_round` | 비교 차수 |
| `old_value`, `new_value` | 변경 전·후 값 |
| `change_type` | `ADDED`, `REMOVED`, `MODIFIED`, `VALUE_CHANGED`, `SCOPE_CHANGED`, `PROCEDURE_CHANGED`, `DOCUMENT_CHANGED` |
| `old_source_page`, `new_source_page` | 이전·신규 근거 페이지 |
| `description` | 변경 설명 |

본문에 제안됐던 `old_source_document_id`, `new_source_document_id`는 이번 v2에 추가하지 않는다.
"v1 그대로"라는 댓글 결정을 따른다.

---

## 13. `source_record_mappings`

원천 행 ID와 공통 UUID를 분리하기 위한 이관 장부다.

| 컬럼 | 값·형식 |
| --- | --- |
| `mapping_id` | 매핑 UUID |
| `visa_id` | 공통 비자 FK |
| `source_dataset` | `A_F-2-R`, `B_E-7-4R`, `D_visa_requirements` |
| `source_table` | 확장자 없는 원천 테이블명 |
| `source_record_id` | `REQ-*`, `SCORE-*`, 원천 UUID 등 |
| `source_group_path` | #35 조건 트리 경로, nullable |
| `source_document_id`, `source_page` | 원천 근거 |
| `valid_from`, `valid_to` | 원천 행 유효기간 |
| `target_table` | 확장자 없는 공통 테이블명 |
| `target_record_id` | 공통 UUID. 발급 전에는 null |
| `mapping_action` | `COPY`, `TRANSFORM`, `MERGE`, `SKIP`, `MANUAL_REVIEW` |
| `mapping_status` | `PENDING`, `READY`, `MAPPED`, `BLOCKED` |
| `blocking_reason` | 차단 사유 |
| `mapped_at` | 이관 시각 |
| `mapping_note` | 변환 설명 |

핵심 ID 규칙은 다음과 같다.

- 기존 v1 공통 레코드는 기존 공통 UUID 유지
- 새 공통 레코드는 공통 계층에서 UUIDv4 생성
- `REQ-*`, `SCORE-*`, #35 criteria UUID는 공통 PK로 복사하지 않음
- 원천 ID는 `source_record_mappings.source_record_id`에 보존
- `target_record_id`는 검증이 끝난 마지막 단계에 발급

## 제외되는 것

다음은 공통 서비스 스키마로 올리지 않는다.

- 별도 상태관리 테이블
- `visa_round_facts`
- `visa_current_facts`
- `visa_fact_coverage`
- `extraction_status`
- `review_status`
- `consumption_gate`
- `confidence`

이 정보들은 원천·검수 계층에 유지한다. 공통 마스터에는 검수 완료된 데이터만 적재한다.

특히 현재 #35 점수표는 `needs_review`이고 소비가 차단된 상태이므로, 점수 스키마는 만들되 해당 점수
데이터는 현행성 검증 후 이관해야 한다.

이 구조로 가면 **스키마는 지금 확정할 수 있고**, 남은 조사 결과는 테이블 구조 변경 없이 null 값을
채우거나 새 행을 추가하는 방식으로 처리할 수 있다.
