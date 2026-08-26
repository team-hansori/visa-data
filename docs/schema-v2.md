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
| `published_at` | 공고일. nullable(단일 게시일로 특정되지 않는 문서, 예: 웹 목록형 출처) |
| `source_location` | 저장 경로 또는 원문 URL |
| `file_hash_sha256` | 원문 파일 변경 확인용. nullable(원본 PDF는 이 저장소에 올리지 않으므로 대부분 계산 불가) |
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

`INFORMATIONAL`의 `operator`는 비워도 되고(F-4-R "허가조건(거주지 유지의무)"/"취업활동 지역
제한", F-2-R "최초 추천지역 실거주"/"실거주 유예" 등), 원천 데이터가 이미 `EXISTS`처럼 서술적인
값을 갖고 있었다면 그 값을 그대로 보존해도 된다(F-2-R "준법시민교육" — v1 원천 값을 그대로
옮긴 것이며 조작이 아니다). 계산에서 제외된다는 원칙(위 표)은 두 경우 모두 동일하게 적용된다.

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
| `parent_scope_name` | 상위 지역·기관. nullable(`NATIONAL`/`PROVINCE`처럼 상위 범위 자체가 없는 스냅샷은 비움) |
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
| `source_document_id` | 원천 근거 문서 FK |
| `source_page` | 원천 근거 페이지. nullable(웹 목록 등 페이지 번호가 없는 원천은 비움) |
| `valid_from` | 원천 행 유효기간 시작. nullable(원문이 "미확인"으로 명시한 경우 등) |
| `valid_to` | 원천 행 유효기간 종료. nullable(계속 유효 시) |
| `target_table` | 확장자 없는 공통 테이블명 |
| `target_record_id` | 공통 UUID. 발급 전에는 null |
| `mapping_action` | `COPY`, `TRANSFORM`, `MERGE`, `SKIP`, `MANUAL_REVIEW` |
| `mapping_status` | `PENDING`, `READY`, `MAPPED`, `BLOCKED` |
| `blocking_reason` | 차단 사유 |
| `mapped_at` | 이관 시각. 매핑 전(초안, `PENDING`/`BLOCKED`)에는 null |
| `mapping_note` | 변환 설명 |

핵심 ID 규칙은 다음과 같다.

- 기존 v1 공통 레코드는 기존 공통 UUID 유지
- 새 공통 레코드는 공통 계층에서 UUIDv4 생성
- `REQ-*`, `SCORE-*`, #35 criteria UUID는 공통 PK로 복사하지 않음
- 원천 ID는 `source_record_mappings.source_record_id`에 보존
- `target_record_id`는 검증이 끝난 마지막 단계에 발급

## 마이그레이션 전제 — v1/원천 기준선

이슈 #44 작업 단계 "1. 입력 데이터와 v1 기준선 고정"의 산출물이다. 이관 대상 4개 비자유형이
어떤 원천·검수 결과를 기준으로 이관되는지, 그리고 `extraction/common_v2/source_documents.csv`·
`source_record_mappings.csv` 초안이 어떤 범위를 다루는지 이 문서 자체에서 추적할 수 있게 남긴다.
아래 스냅샷은 커밋 시점 기준이며 원천 폴더가 갱신되면 재조사가 필요하다.

### `extraction/D_visa_requirements/` 6개 CSV 스냅샷

| 파일 | 헤더 컬럼(순서대로) | 행 수 | PK | FK | PK UUIDv4 비율 |
| --- | --- | --- | --- | --- | --- |
| `visa_requirements.csv` | `visa_id, visa_code, visa_name_kr, program_type, target_region, total_score_threshold, residency_limit_years, allowed_industries, application_method, quota_type, total_quota, quota_shared_with, next_visa_code, valid_from, valid_to, source_document, source_page, last_verified_at` | 1 | `visa_id` | 없음 | 1/1 (100%) |
| `visa_requirement_criteria.csv` | `criteria_id, visa_id, criteria_name, criteria_type, value_numeric, operator, unit, value_text, measurement_window_value, measurement_window_unit, condition_group, condition_operator, special_case_note, valid_from, valid_to, source_document, source_page, last_verified_at` | 10 | `criteria_id` | `visa_id` → `visa_requirements.visa_id` | 10/10 (100%) |
| `visa_process_stages.csv` | `stage_id, visa_id, stage_order, stage_name, stage_name_kr, actor_from, actor_to, stage_start_date, stage_end_date, notes, notice_round, document_requirements_status, valid_from, valid_to, source_document, source_page, last_verified_at` | 4 | `stage_id` | `visa_id` → `visa_requirements.visa_id` | 4/4 (100%) |
| `document_requirements.csv` | `document_requirement_id, stage_id, document_name, document_category, filled_by, submitted_by, submission_target, signer, required_attachments, is_mandatory, valid_from, valid_to, source_document, source_page, last_verified_at, notes` | 0 | `document_requirement_id` | `stage_id` → `visa_process_stages.stage_id` | 0/0 (해당 없음) |
| `visa_quota_status.csv` | `quota_status_id, visa_id, notice_round, remaining_quota, as_of_date, source_document, source_page, recorded_at` | 0 | `quota_status_id` | `visa_id` → `visa_requirements.visa_id` | 0/0 (해당 없음) |
| `change_history.csv` | `change_id, visa_id, table_name, field_identifier, from_round, to_round, old_value, new_value, change_type, old_source_page, new_source_page, description` | 0 | `change_id` | `visa_id` → `visa_requirements.visa_id` | 0/0 (해당 없음) |

6개 파일 합계 15행, PK 전부 유효한 UUIDv4다(플래그할 위반 없음). `document_requirements.csv`·
`visa_quota_status.csv`·`change_history.csv`는 F-4-R이 `UNLIMITED`·상시접수·무변경 이력이라 v1
단계에서부터 행이 0개였다 — 원천 조사 누락이 아니라 실제로 빈 파일이다.

### 비자유형별 입력 기준

- **F-4-R**: `extraction/D_visa_requirements/`의 v1 공통 마스터 6개 CSV를 그대로 기준으로 삼는다.
  이슈 #42가 이미 이 폴더를 검증했으므로 별도 검수 없이 이관 후보로 취급한다.
- **E-7-4R**: `extraction/B_E-7-4R/`(특히 `schema_mapping.csv`, `requirements/_review_current_requirements.csv`,
  `scoring/scoring_items.csv`, `documents/document_forms.csv`, `history/change_history.csv`)와 PR #43의
  검수·매핑 결과를 기준으로 삼는다. `schema_mapping.csv`의 `mapping_status=pending_target_id`는
  README가 명시하듯 "의미 매핑 미완료"가 아니라 "공통 UUID 발급 대기"이므로 이관 후보에 포함한다.
- **F-2-R**: `extraction/A_F-2-R/`(특히 `common_master_mapping.csv`)와 PR #36의 원천·검수·매핑 결과를
  기준으로 삼는다. `mapping_status=ready`는 열·논리·출처 형식상 변환 가능하다는 뜻일 뿐 업무영역
  재검토가 끝났다는 뜻이 아니므로(`COMMON_MASTER_MAPPING.md` 참고), 이후 단계에서도 재확인이 필요하다.
- **D-2**: `extraction/C_D-2-common/`(3개 CSV: `parttime_work_rules.csv`, `certified_universities.csv`,
  `gwangyeok_eligible_departments.csv`)를 기준으로 삼는다. 이슈 #41의 연결 결과에 따라 D-2는
  Lookup/Rule 구조를 그대로 유지하고 공통 자격조건 트리로 평탄화하지 않는다(plan 8단계).

### D-2 연결 검증 (plan 8단계)

D-2는 공통 마스터로 이관하지 않으므로, 이 절은 "무엇을 옮겼는가"가 아니라 "`extraction/C_D-2-common/`이
공통 `visa_requirements`와 실제로 연결 가능한 상태인가"만 확인한다.

**식별자 검증 결과 — 불일치 발견, 원천 파일은 수정하지 않음**

`gwangyeok_eligible_departments.csv`(71행)에는 자체 `visa_id` 컬럼이 있고 71행 전부 동일한 값
(`41f2d169-e38f-4e76-8047-1d4964815ee4`, 형식상 유효한 UUIDv4)을 쓴다. 이 값은 v2 공통 마스터가
1단계에서 D-2용으로 발급한 `visa_id`(`8a295d32-46dd-43a8-8a9d-b3713251bf1f`)와 다르다.

두 값이 다른 게 버그가 아니라고 판단한 근거: D-2는 F-4-R과 달리 `extraction/` 안에 자체
`visa_requirements.csv`(공통 마스터에 준하는 단일 정체성 행)가 존재한 적이 없다 — 이 비자유형의
"기존 v1 공통 UUID"라는 게 애초에 없었다. `41f2d169-...`는 저장소 전체에서
`gwangyeok_eligible_departments.csv` 한 파일에서만 등장하며(검색 확인 완료), 다른 어떤 D-2 관련
파일에도 참조되지 않는다 — 즉 공통 정체성으로 의도된 값이라기보다 그 파일을 만들 때 내부적으로
생성된 값으로 보인다. 그래서 "기존 v1 공통 UUID는 유지한다" 원칙이 적용될 대상 자체가 없었고,
1단계에서 새 UUIDv4를 발급한 것은 맞는 처리였다고 본다. 실무적으로도, 이 문서를 쓰는 시점에
`8a295d32-...`는 이미 `extraction/common_v2/`(`visa_requirements.csv` 1행,
`source_documents.csv` 3행, `source_record_mappings.csv` 99행 — 총 약 103곳)에 퍼져 있어서,
지금 `41f2d169-...`로 되돌리는 쪽이 `gwangyeok_eligible_departments.csv` 71행을 고치는 것보다
수정 범위가 더 크다 — 이 편의성도 "원천 파일을 고치지 않는다"는 판단을 뒷받침한다.

다만 이 불일치는 실제로 존재하므로 여기 기록해둔다 — 나중에 D-2가 실제로 공통 마스터와 연결되는
단계에 들어가면(예: `visa_requirements`와의 FK를 만드는 경우), `gwangyeok_eligible_departments.csv`의
`visa_id` 컬럼을 `8a295d32-...`로 정정하거나, 애초에 이 컬럼이 왜 필요했는지(같은 파일 안에서
D-2 외 다른 값이 나온 적이 없으므로 사실상 상수) 재검토하는 게 좋다. 이번 검증에서는 원천 파일을
고치지 않았다 — `extraction/`의 검수 완료 데이터를 이 이슈 범위에서 임의로 수정하지 않는다는 원칙을
따른다.

**출처·유효기간 검증 결과 — 전부 원문에 근거, 추가 조치 불필요**

- `parttime_work_rules.csv`(10행): 전체 행의 `valid_from`이 문자열 `"UNKNOWN — PDF·웹페이지 모두
  시행일 미기재, 확인 필요"`다. 값이 빠진 게 아니라 원문 자체에 시행일이 없다는 사실을 CSV 셀에
  직접 상태 문자열로 명시해둔 것이다(`extraction/C_D-2-common/README.md`는 이 컬럼의 관례를
  별도로 설명하지 않는다 — `UNKNOWN` 표기 자체가 유일한 근거이며, 관련된 일반 규칙은 본 문서
  759-773번째 줄 참고). 이 이슈에서 임의로 날짜를 채우지 않는다.
- `certified_universities.csv`(18행): 전체 행에 `source_page`가 없다. 출처가 PDF가 아니라 두 개의
  웹페이지(충북지역대학혁신지원센터, 한국유학종합시스템)라 페이지 번호 자체가 존재하지 않는 게
  정상이다 — 결측이 아니라 구조적으로 해당 없음.
- `gwangyeok_eligible_departments.csv`(71행): `source_document`/`source_page`/`valid_from`/`valid_to`
  전부 채워져 있다. 위 식별자 불일치를 빼면 이 파일은 완전하다.

**쿼터 미생성 확인**

D-2 공식 정원 숫자는 아직 확인되지 않았다(1단계 시점 기준). `extraction/common_v2/
visa_quota_policies.csv`·`visa_quota_snapshots.csv` 어디에도 D-2 행이 없음을 확인했다 — plan
8단계의 "공식 정원 숫자가 확인되지 않은 상태에서는 quota policy/snapshot 행을 생성하지 않는다"
원칙대로 유지한다.

**서비스 소비 경계**

- `extraction/C_D-2-common/`의 3개 CSV는 원래 스키마 그대로 남고, 서비스 판정용 10개 테이블
  어디로도 옮기지 않는다 — `visa_criterion_groups`/`visa_requirement_criteria`로 평탄화하지 않는다.
  예외는 `source_record_mappings`뿐이다: 이 3개 CSV의 원천 행 99개(F-2-R·E-7-4R과 같은 방식으로)
  전부 `SKIP`/`BLOCKED` 상태로 추적만 기록돼 있다 — 이건 실제 내용 이관이 아니라 "이 원천 행을
  검토했고 지금은 이관하지 않기로 했다"는 감사 기록이다.
- v2 공통 마스터가 D-2에 대해 갖는 건 `visa_requirements`의 정체성 행(`visa_id`+`visa_code`만
  채워진 1단계 부트스트랩) 하나뿐이다 — 자격조건·절차·서류·쿼터 등 나머지 내용은 공통 마스터에
  없다.
- 따라서 어떤 v2 서비스 테이블도 현재 D-2 Lookup/Rule 데이터를 소비하지 않는다. 나중에 추천
  시스템이 D-2를 다뤄야 하면, `extraction/C_D-2-common/`을 직접 읽는 별도 조회 경로가 필요하며,
  이는 이 이슈의 범위가 아니다.

### 검수 완료 범위 vs 보류 범위

2026-08-26 통합 스냅샷의 `source_record_mappings.csv` 684행을 기준으로 집계했다.

| 비자유형 | 원장 행 | `MAPPED` | 의도적 `SKIP/BLOCKED` | 실제 `MANUAL_REVIEW/BLOCKED` |
| --- | ---: | ---: | ---: | ---: |
| F-4-R | 16 | 16 | 0 | 0 |
| E-7-4R | 318 | 289 | 29 | 0 |
| F-2-R | 251 | 240 | 11 | 0 |
| D-2 | 99 | 0 | 99 | 0 |
| 합계 | 684 | 545 | 139 | 0 |

`PENDING`과 `READY`는 0건이다. 여기서 `BLOCKED`는 두 의미로 사용되므로 반드시
`mapping_action`과 함께 읽는다.

- `mapping_action=SKIP`, `target_table=NONE`: 제목·분할 전 부모 행·병합 조각·이관 범위 밖 원천을
  검토한 뒤 의도적으로 공통 행을 만들지 않은 감사 기록이다.
- `mapping_action=MANUAL_REVIEW`: 원문만으로 대상 레코드를 확정하지 못한 실제 보류다. 현재는 0건이다.

D-2 99행은 검수 부족으로 버린 것이 아니라 Lookup/Rule 구조를 유지한다는 plan 8단계 결정에 따라
서비스 공통 테이블로 평탄화하지 않은 것이다.

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

## 이관 결과 요약 및 완료 체크리스트

이슈 #44의 마지막 태스크(10. 통합·회귀 검증과 전환) 산출물이다. 여기서는 두 가지만 한다:
`plans/issue-44-common-schema-v2-migration.md` "완료 체크리스트"의 17개 항목을 실제
`extraction/common_v2/` 데이터를 다시 읽어 하나씩 정직하게 판정하고, 아직 이관되지 않은 항목을
한곳에 모아 다음 작업이 어디서부터 시작해야 하는지 남긴다. 이 문서를 신뢰하고 이어받을 다음
작업을 위해, 실제보다 낙관적으로 "완료"라고 적지 않는다.

### `migrate_to_v2.py` 재생성 계약

`scripts/migrate_to_v2.py`는 더 이상 헤더만 생성하는 스텁이 아니다. 검수 완료된
`extraction/common_v2/` 13개 CSV를 읽어 다음 계약으로 `build/common_v2/`에 재생성한다.

1. 원본 헤더와 전체 무결성 결과가 `known_validation_gaps.txt`와 정확히 일치해야 한다.
2. 행 순서를 유지하고 UTF-8/LF로 결정적으로 직렬화한다.
3. 임시 디렉터리에서 13개 파일을 모두 만든 뒤 같은 검증기를 통과한 경우에만 출력으로 교체한다.
4. 원본과 출력 경로가 같거나 서로 포함되면 `--force`여도 거부한다.
5. 기존 출력은 `--force`가 있을 때만, 새 스냅샷 검증이 끝난 뒤 교체한다.

```bash
uv run python scripts/migrate_to_v2.py
uv run python scripts/validate_common_schema_v2.py \
  --base-dir build/common_v2 \
  --baseline extraction/common_v2/known_validation_gaps.txt
```

이 빌더가 재현하는 대상은 **사람이 원문 대조를 마친 검수 스냅샷**이다. 원천 v1/HWPX/PDF만으로
AND/OR 구조와 분할·병합 판단을 다시 자동 추론하는 도구는 아니다. 그 의미 결정의 추적 근거는
`source_record_mappings.csv`, 원천 검수 CSV, 이 문서에 남긴다.

### 17개 완료 체크리스트 판정

plan 문서의 체크리스트는 17개 항목이다(브리프는 "16개"라고 적었으나 실제로는 17개 — plan
원문의 항목 수를 그대로 따른다). 각 항목을 이 스냅샷 시점의 실제 `extraction/common_v2/` 내용
기준으로 판정한다.

1. **v2 명세에 13개 테이블의 컬럼·자료형·enum·null·PK/FK 규칙이 있다.** — 완료. 이 문서
   1~13번 절 + `scripts/schema_v2.py`가 단일 진실 공급원이다.
2. **서비스 테이블 10개와 지원 테이블 3개의 실제 헤더가 명세와 일치한다.** — 완료.
   `validate_directory()`가 13개 파일의 헤더 순서를 스키마와 대조하며, 현재 알려진
   검증 실패는 0건이다.
3. **모든 이관 대상 비자에 eligibility ROOT 그룹이 정확히 하나 있다.** — 완료. F-4-R,
   E-7-4R, F-2-R에 각각 ROOT가 하나 있고 전체 그룹은 4/17/22행이다. D-2는 plan 8단계
   결정에 따라 Lookup/Rule 구조를 유지하므로 eligibility 트리 이관 대상이 아니다.
4. **조건 그룹에 부모 누락, 비자 불일치, 자기참조, 순환참조가 없다.** — 완료. 실제 43개
   그룹 전체를 검증했고 위반은 0건이다. 합성 fixture에서도 부모 누락·자기참조·간접 순환을
   거부한다.
5. **F-2-R의 차단된 복합 조건이 논리 손실 없이 이관된다.** — 완료(확정 범위). 22개 그룹과
   58개 criteria로 일반 경로·특례·언어 OR 조건을 보존했다. 이관 원장 251행 중 240행은
   `MAPPED`, 독립 공통 행이 아닌 11행은 `SKIP`이다. 학교장 추천서는 p.8의 상세 조건을 따라
   국내 대학 졸업생의 조건부 필수서류로 이관하고 p.16의 출입국 제출서류 목록을 보조 근거로 연결했다.
6. **E-7-4R의 기본 자격과 K-POINT 점수표가 분리된다.** — 완료. 기본 자격은 17개 그룹·
   43개 criteria, 점수표는 1개 모델·29개 항목으로 분리돼 있다.
7. **점수 모델의 미확인 값은 null이며 검수 미완료 점수는 소비되지 않는다.** — 완료. E-7-4R
   `visa_scoring_models`의 `final_maximum_points`/`bonus_cap_points`/`tie_breaker_rule`은
   모두 null(미확인 값을 임의로 채우지 않음, 이번 태스크에서 재확인). #35(F-2-R) 점수표는
   현행성 미검증 상태라 아예 공통 마스터에 넣지 않았다 — "검수 미완료 점수는 소비되지 않는다"는
   원칙을 데이터를 만들지 않는 방식으로 지킨 것.
8. **제출서류의 필수·선택·조건부·대체·첨부관계가 표현된다.** — 완료. E-7-4R 32행과
   F-2-R 44행을 이관했다. F-2-R은 REQUIRED 19 / CONDITIONAL 13 / ALTERNATIVE 12행이며,
   전체 첨부관계는 37행이다. 원문에 없는 OPTIONAL 행을 임의 생성하지 않았다.
9. **첨부관계에 자기참조나 순환참조가 없다.** — 완료. 실제 37행 전체에서 위반 0건이며,
   합성 fixture에서도 자기참조와 간접 순환을 거부한다.
10. **F-2-R 시군별 및 E-7-4R 광역별 쿼터 의미가 보존된다.** — 완료. F-2-R은 8~17차마다
    6개 시군씩 총 60개 MUNICIPALITY 스냅샷, E-7-4R은 충청북도 PROVINCE 스냅샷 1개다.
11. **E-7-4R 쿼터 집계 542/246/10/236/306이 검증된다.** — 완료. 이 값들은 실제
    `visa_quota_snapshots.csv`에 그대로 있고, 이번 태스크(Deliverable 2)에서
    `tests/test_v2_migration_regression.py::TestE7_4RQuotaSnapshot`로 고정했다.
12. **F-4-R 기존 UUID, 판정, 절차 결과가 유지된다.** — 완료. `visa_id=606d8651-...`가 v1 UUID
    그대로 재사용됐고(Task 4), 그룹 트리(4개 그룹·10개 조건)가 기존 판정 로직을 반영하며,
    절차 4단계가 이관됐다. 이번 태스크(Deliverable 2)에서
    `tests/test_v2_migration_regression.py::TestF4RUuidLifecycle`로 UUID 재사용을 고정했다.
13. **D-2 전용 구조와 공통 마스터의 연결 경계가 검증·문서화된다.** — 완료. 이 문서의
    "D-2 연결 검증(plan 8단계)" 절(Task 1)이 식별자 불일치, 출처·유효기간 완전성, 쿼터
    미생성, 서비스 소비 경계까지 상세히 검증·기록했다.
14. **모든 공통 행에 필요한 출처·페이지·유효기간이 존재한다.** — 완료. D-2의
    정체성·지역·프로그램 유형은 2025년 충청북도 안내자료로 확인했고,
    신청 방법은 충북보건과학대학교 2026학년도 모집요강 p.1의 광역비자 제출 절차를 근거로
    `application_method`에 반영했다. `valid_from`은 충청북도 선정 결과 통보일인
    2025-04-02로 확정했다. `source_documents.csv`의
    `f4r_r12_announcement` 원본 파일(`.hwpx`, 12차 공고문)은 taeeunni가 확보해 로컬
    저장소(`data/raw/지역특화_재외동포_F-4-R/`)에 추가했고, `source_location`을 채워
    이 항목의 위반은 닫혔다.
    `uv run python scripts/validate_common_schema_v2.py`의 알려진 검증 실패는 0건이다.
15. **원천 ID와 공통 UUID가 분리되고 매핑표로 추적된다.** — 완료.
    `source_record_mappings.csv` 684행(A_F-2-R 251, B_E-7-4R 318,
    C_D-2-common 99, D_visa_requirements 16)이 원천 ID와 공통 UUID를 분리해 추적한다.
    현재 상태는 MAPPED 545 / BLOCKED 139이며 PENDING·READY는 0이다. BLOCKED 139행은
    모두 의도적 SKIP이며 실제 MANUAL_REVIEW는 0건이다.
    원천 파일의 실제 레코드 존재 여부와 MAPPED target UUID 연결은
    `scripts/validate_source_record_mappings.py`에서 별도로 검증한다.
16. **FK·UUID·enum·헤더·쿼터·누락·순환 검증 테스트가 통과한다.** — 완료. 13개 테이블의
    구조·FK·UUID·트리·첨부·쿼터와 684개 원천 매핑을 검사한다. 독립 검증기는 알려진 오류가
    없는 상태에서 새 오류가 생기면 baseline 모드에서 실패한다. 스냅샷 빌더도 생성 전후에
    같은 검증 결과를 강제한다.
17. **v1→v2 변환 규칙과 비자별 이관 결과·보류 항목이 문서화된다.** — 완료. 이 문서의
    "마이그레이션 전제" 절(Task 1)이 변환 규칙과 비자별 기준을 이미 문서화했고, 이번 태스크가
    최종 체크리스트 판정과 아래 "완전히 이관되지 않은 항목" 전체 목록으로 마무리한다.

### 완전히 이관되지 않은 항목 (한곳에 모음)

다음은 2026-08-25 스냅샷에서 실제로 남아 있는 보류·경계 항목이다.

- **F-4-R 그룹 4행의 직접 원천 매핑 부재**: v1에 그룹 테이블이 없고 flat criteria에서 v2 논리
  구조를 구성했기 때문에 각 그룹에 대응하는 단일 원천 행을 억지로 만들지 않았다. 10개 criteria의
  실제 v1 근거와 그룹 자체의 `source_document_id`·페이지는 보존돼 있다.
- **원천에서 의미 결정을 다시 만드는 자동 변환기**: 현재 빌더는 검수 완료 스냅샷을 결정적으로
  재생성하지만, 원천 v1/HWPX/PDF만으로 사람의 분할·병합·AND/OR 판단을 다시 수행하지는 않는다.
  의미 결정은 이관 원장과 검수 자료를 기준으로 변경한다.

F-2-R 제출서류 44행·첨부관계 35행, 시군별 쿼터 60행, E-7-4R 자격 트리와 변경이력 17행은
이미 이관됐다. E-7-4R `REQ-041`도 표 번호 파싱 잔재로 확정해 의도적 SKIP으로 닫았으므로
더 이상 보류 목록에 포함하지 않는다.
