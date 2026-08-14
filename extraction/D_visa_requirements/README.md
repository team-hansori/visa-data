# D_visa_requirements — 비자 요건·절차·쿼터·변경이력 공유 마스터 테이블

`A_F-2-R`/`B_E-7-4R`/`C_D-2-common`이 비자유형별 전용 폴더인 것과 달리, 이 폴더의 4개 테이블은 `visa_code`(F-2-R/E-7-4R/F-4-R/F-5-6R/E-7-4-GENERAL/D-2-GWANGYEOK 등)를 하나의 파일에 함께 담는 공유 마스터 테이블이다. 여러 비자 담당자가 같은 CSV에 각자 비자의 행을 추가하는 구조이므로, PR을 올릴 때 다른 비자유형의 행을 건드리지 않았는지 diff를 확인한다.

F-4-R 12차 공고문(충청북도 공고 제2026-1158호) 분석 과정에서 확정된 설계 원칙이며, F-2-R·E-7-4R 등 다른 비자유형에도 그대로 적용되는지는 실제 공고문 확인 시 재검증이 필요하다.

## 왜 5개 테이블로 나눴는가

비자 하나를 둘러싼 정보는 변경 빈도가 서로 다른 다섯 가지로 나뉜다. 하나의 테이블에 담으면 "거의 안 바뀌는 값"과 "매달 바뀌는 값"이 섞여서, 갱신할 때마다 안 바뀐 값까지 같이 손대야 하는 문제가 생긴다.

| 파일 | 담는 정보 | 변경 빈도 | 성격 |
|------|-----------|-----------|------|
| `visa_requirements.csv` | 비자의 기본 정체성(요건 범위, 총 모집인원 등) | 거의 안 바뀜 | 마스터 |
| `visa_requirement_criteria.csv` | 합격 여부를 가르는 개별 조건 | 연 1회 내외(요건 개정 시) | 마스터(정규화) |
| `visa_process_stages.csv` | 신청 절차의 각 단계(누가·누구에게·언제까지) | 회차마다 재확인 필요 | 마스터(회차별 이력, 회차마다 새 행 추가) |
| `visa_quota_status.csv` | 잔여 인원 스냅샷 | 매달 | 로그(시계열) |
| `change_history.csv` | `visa_requirements`·`visa_requirement_criteria` 값이 회차 간 어떻게 바뀌었는지 | 값이 바뀔 때마다 | 로그(변경 diff) |

`visa_process_stages`·`visa_quota_status`는 애초에 회차별/시점별로 새 행을 쌓는 구조라 그 자체로 이력이다. 반면 `visa_requirements`·`visa_requirement_criteria`는 "현재 유효한 값"만 `valid_from`/`valid_to`로 관리하는 마스터라, 회차가 바뀔 때 무엇이 왜 바뀌었는지는 별도로 기록해야 한다 — 그 역할을 `change_history.csv`가 한다.

## 파일별 스펙

### `visa_requirements.csv`

| 필드 | 타입 | 설명 |
|------|------|------|
| `visa_id` | uuid (PK) | |
| `visa_code` | text | `F-2-R`/`E-7-4R`/`F-4-R`/`F-5-6R`/`E-7-4-GENERAL`/`D-2-GWANGYEOK` |
| `visa_name_kr` | text | 표시명 |
| `program_type` | text | `REGIONAL_SPECIALIZED`/`GENERAL`/`GWANGYEOK` |
| `target_region` | text[] | 대상 시군(전국이면 NULL). 배열 직렬화 규칙은 "배열 필드 표기" 참고 |
| `total_score_threshold` | integer, nullable | 점수제 합격선(점수제 아니면 NULL) |
| `residency_limit_years` | integer | 거주지 제한기간 |
| `allowed_industries` | text[], nullable | 업종 제한(제한 없으면 NULL). 배열 직렬화 규칙은 "배열 필드 표기" 참고 |
| `application_method` | text | 신청 방법 요약 |
| `total_quota` | integer, nullable | 총 모집인원. NULL = 무제한 |
| `quota_shared_with` | text, nullable | 쿼터 공유 비자코드 |
| `next_visa_code` | text, nullable | 전환 가능한 다음 비자(F-4-R→F-5-6R 등) |
| `valid_from`/`valid_to`/`source_document`/`source_page`/`last_verified_at` | — | 표준 버전관리 |

비자 하나당 값이 딱 하나뿐인 정보만 여기 들어간다. 여러 개가 나올 수 있는 값(요건 여러 개, 절차 여러 단계, 매달 바뀌는 쿼터)은 전부 다른 테이블로 뺀다.

### `visa_requirement_criteria.csv`

| 필드 | 타입 | 설명 |
|------|------|------|
| `criteria_id` | uuid (PK) | |
| `visa_id` | uuid (FK) | |
| `criteria_name` | text | "거주기간", "신청자격(기존거주자)" 등 |
| `criteria_type` | text | `binary`/`graduated` |
| `threshold_value` | text | 기준값 |
| `point_value` | integer, nullable | 점수제만 |
| `condition_group` | text, nullable | 서로 대체 가능한(OR) 조건 묶음 ID(`G1`, `G2`… 임의 라벨, 의미 없음). 유일성은 같은 `visa_id` 안에서만 보장하면 되고, 다른 비자유형 행과 번호가 겹쳐도 무방하다. 묶이지 않은 행은 다른 모든 criteria 행과 기본적으로 AND로 결합된다 |
| `condition_operator` | text, nullable | `condition_group`이 있는 행에만 채움. 현재는 `OR`만 쓴다(AND는 그룹 없이 표현되므로) |
| `special_case_note` | text, nullable | 예외조건 설명, 재량판단 단서 등 — 논리 연산 자체는 여기 적지 않고 `condition_group`/`condition_operator`로 표현 |
| `valid_from`/`valid_to`/`source_document`/`source_page`/`last_verified_at` | — | 표준 버전관리 |

**이 테이블에 넣을지 판단하는 기준**은 아래 "판단 기준 5단계 질문"을 그대로 따른다 — 트래커가 자동으로 충족/미충족을 판정할 수 있는 조건만 행으로 만든다. "인정되는 경우"·"부득이한 경우" 같은 재량 판단 표현이 들어간 조건은 절대 여기 넣지 않는다(`admin_guide_corpus`로).

**OR 조건 처리**: `B_E-7-4R/current_requirements.csv`와 같은 구조를 그대로 쓴다 — 한 문장에 여러 조건이 섞여 있으면 개별 행으로 분리하고, `condition_group`은 서로 관련된(대체 가능한) 조건들의 묶음만 나타낸다. 논리적 결합 관계는 자동으로 정하지 않고 원문을 직접 읽고 `condition_operator`에 사람이 입력한다. F-4-R의 "기존거주자/국내전입자/해외전입자" 3갈래처럼 "이 중 하나만 충족하면 됨"은 세 행 모두 같은 `condition_group`(예: `G1`)과 `condition_operator=OR`을 준다. `condition_group`이 없는 행은 같은 `visa_id`의 다른 모든 행과 AND로 결합된다고 간주한다.

**복합 조건("A AND (B OR C)") 처리**: 하나의 필수 조건(A)과 그 조건을 만족하는 두 가지 대체 경로(B/C)가 섞인 경우, A는 `condition_group` 없이 독립 행으로 두고(전체와 AND), B·C만 같은 `condition_group`을 줘서 OR로 묶는다. 예: F-4-R "동반자녀 추가요건"은 "만 6~19세(연령, AND)" + "① 재학중/입학예정 OR ② 질병·장애로 재학 곤란"이므로, 연령요건은 그룹 없이 1행, ①·②는 같은 그룹(`condition_operator=OR`)으로 2행 — 총 3행으로 분리한다. 하나의 행에 AND와 OR를 텍스트로 섞어 넣지 않는다(자동판정이 불가능해지므로).

### `visa_process_stages.csv`

| 필드 | 타입 | 설명 |
|------|------|------|
| `stage_id` | uuid (PK) | |
| `visa_id` | uuid (FK) | |
| `stage_order` | integer | 진행 순서 |
| `stage_name` | text | 영어 코드(`APPLICATION_SUBMISSION` 등) |
| `stage_name_kr` | text | 화면 표시용 |
| `actor_from` | text | 이 단계를 시작하는 주체 |
| `actor_to` | text | 이 단계를 받는 주체 |
| `stage_start_date` | date | 시작일 |
| `stage_end_date` | date | 마감일(단일 발표일이면 시작일과 동일) |
| `notes` | text, nullable | 반복 주기 등 추가 설명 |
| `notice_round` | integer | 몇 차 공고 기준 |
| `valid_from`/`valid_to`/`source_document`/`source_page`/`last_verified_at` | — | 표준 버전관리 |

비자마다 절차 단계 개수 자체가 다르므로(F-4-R 4단계, D-2-GWANGYEOK 5단계) 고정 컬럼이 아니라 행으로 관리한다. `actor_from`이 신청자 유형(재외동포·외국인 등)인 단계만 리마인더가 사용자에게 알림을 준다 — 행정기관끼리 처리하는 단계는 "지금은 기다리는 중"이라고만 안내한다. 매달 새 공고(회차↑)가 나오면 기존 행을 덮어쓰지 않고 새 행을 추가한다.

### `visa_quota_status.csv`

| 필드 | 타입 | 설명 |
|------|------|------|
| `quota_status_id` | uuid (PK) | |
| `visa_id` | uuid (FK) | |
| `notice_round` | integer | 몇 차 공고 기준 |
| `remaining_quota` | integer, nullable | 잔여 인원. NULL = 무제한 |
| `as_of_date` | date | 공고일 기준 |
| `source_document`/`source_page` | — | 표준 |
| `recorded_at` | date | 팀이 기록한 날짜 |

**표준 5필드에서 벗어난 이유**: "현재 유효한 값"이 아니라 시점별 기록을 영구히 쌓는 로그다. `valid_from`/`valid_to`(언제까지 유효했는지) 개념이 안 맞아서 `as_of_date`+`recorded_at`으로 대체했다. `total_quota` 자체가 NULL(무제한)인 비자는 이 테이블에 행을 만들지 않는다.

### `change_history.csv`

| 필드 | 타입 | 설명 |
|------|------|------|
| `change_id` | uuid (PK) | |
| `visa_id` | uuid (FK) | |
| `table_name` | text | `visa_requirements`/`visa_requirement_criteria` — 변경이 어느 테이블에서 났는지 |
| `field_identifier` | text | `table_name=visa_requirements`면 컬럼명(`total_quota` 등), `visa_requirement_criteria`면 `criteria_name` |
| `from_round` | integer | 변경 전 회차(공고 차수) |
| `to_round` | integer | 변경 후 회차 |
| `old_value` | text, nullable | 변경 전 값 (`added`면 비움) |
| `new_value` | text, nullable | 변경 후 값 (`removed`면 비움) |
| `change_type` | text | `added`/`removed`/`value_changed`/`scope_changed`/`procedure_changed`/`document_changed`/`editorial_change`(단순 문구 수정은 새 행으로 만들지 않음) |
| `old_source_page` | text, nullable | |
| `new_source_page` | text | |
| `description` | text | 무엇이 왜 바뀌었는지 서술 |

`B_E-7-4R/change_history.csv`와 같은 패턴이되, 이 폴더는 여러 비자유형·테이블이 한 파일을 공유하므로 `visa_id`와 `table_name`으로 어느 비자의 어느 테이블 변경인지 구분한다. `visa_requirements`·`visa_requirement_criteria`에 새 회차 값을 반영할 때마다(기존 행의 `valid_to`를 마감하고 새 행을 추가할 때) 이 테이블에도 diff 행을 같이 남긴다.

## 판단 기준 5단계 질문

새 정보를 발견할 때마다 이 순서로 어느 테이블에 넣을지(또는 스키마화하지 않을지) 정한다.

```
① 트래커가 이 값으로 합격여부를 계산하는가?
   Yes → visa_requirement_criteria
   No ↓

② 재량 판단 표현("인정되는 경우" 등)이 들어있는가?
   Yes → admin_guide_corpus (criteria 후보에서 애초에 제외)
   No ↓

③ 리마인더가 이 값으로 알림 시점을 판단하는가?
   Yes → visa_process_stages
   No ↓

④ 매달/수시로 바뀌는 시점별 기록(로그)인가?
   Yes → visa_quota_status류 별도 로그 테이블
   No ↓

⑤ 사용자가 읽고 이해하면 충분한가?
   Yes → admin_guide_corpus
   No → 단순 서식·옵션 등 → 스키마화하지 않음(document_url 링크 또는 skip)
```

`visa_requirement_criteria`로 갈지 판단할 때는 추가로: 최초 신청 요건인지 승인 이후 유지의무 위반 사례인지 구분한다(위반 사례는 `admin_guide_corpus`로, 위험감지 키워드로 활용). 해당자가 극소수인데 새 사용자 입력값이 필요한 예외 규칙은 지금은 `special_case_note` 텍스트로만 남기고, 실사용자 비율이 높아지면 그때 필드로 승격한다.

## `admin_guide_corpus`로 가는 정보 (스키마화하지 않음)

계산도 알림 판단도 필요 없이 읽어주기만 하면 되는 정보는 이 폴더에 CSV로 만들지 않는다. 예: 취업제한범위 비교표, 허가조건 위반 사유, 재량판단 예외조항 서술, 정착지원 프로그램 소개(→ 기존 `support_programs`에 행만 추가), 붙임서식 원본(→ `required_documents.document_url`에 링크만), 설문조사지 등 앱 기능과 무관한 옵션.

## 배열 필드 표기

`target_region`/`allowed_industries`처럼 `text[]` 타입인 필드는 CSV 셀(하나의 컬럼) 안에 `|`(파이프)로 원소를 구분해서 넣는다. 예: `제천시|보은군|옥천군|영동군|괴산군|단양군`. 값이 없으면(NULL) 빈 문자열로 둔다.

- **원소 구분자**: `|` 앞뒤에 공백을 두지 않는다(`A|B`, `A |B` 아님).
- **원소 자체에 `|`가 들어가면 안 된다**: 시군명·업종명에 파이프 문자가 나올 일이 없으므로 이 표기법을 쓴다. 원문에 파이프가 포함된 값이 나오면 이 컬럼에 그대로 넣지 말고 별도 필드(예: `notes`)에 원문을 남기고 이슈로 공유한다.
- **콤마·큰따옴표는 CSV 표준 이스케이프를 그대로 따른다**: `|` 구분은 셀 *내부*의 배열 표기일 뿐, 셀 자체의 CSV 이스케이프(RFC 4180)와는 별개 레이어다. 원소 중 하나에 콤마가 들어가면(예: `제조업, 도소매업` 같은 업종명) 셀 전체를 큰따옴표로 감싸고(`"제조업, 도소매업|건설업"`), 원소 안에 큰따옴표가 있으면 두 번 겹쳐 이스케이프한다(`""`). 엑셀·Python `csv` 모듈 등 CSV 인식 도구로 저장하면 이 처리가 자동으로 이루어지므로, 텍스트 에디터로 셀 값을 직접 이어붙이지 않는다.

## 원본 문서

원본 PDF는 이 저장소에 올리지 않고 `data/raw/<비자코드>/`의 상대 경로로 참조한다 (예: `data/raw/F-4-R/`). PDF 자체가 아직 이 저장소에 없다면 실제 위치를 `source_document`에 남긴다.

## 작성 규칙

- 모든 값에는 출처 문서·페이지 근거를 남긴다.
- 확인되지 않은 값은 추측하지 않는다.
- 공고문과 심사표 등 문서 간 값이 다르면 임의로 하나를 선택하지 않고 두 근거를 모두 남긴 뒤 `special_case_note`/`notes`에 검토 표시를 한다.
- 다른 비자유형 담당자가 이미 채운 행은 건드리지 않는다 — PR diff에서 본인이 담당하는 `visa_code`의 행만 추가/수정됐는지 확인한다.

## 다음 단계

1. `data/raw/F-4-R/`에 12차 공고문 PDF를 추가한다.
2. `visa_requirements.csv`에 F-4-R 1행을 채운다.
3. `visa_requirement_criteria.csv`에 F-4-R 요건을 5단계 질문 기준으로 분류해 채운다(신청자격 3갈래 OR, 거주지 유지의무, 결격사유, 동반자녀 추가요건, 취업지역 제한 등).
4. `visa_process_stages.csv`에 12차 공고 기준 절차 단계를 채운다.
5. `visa_quota_status.csv`는 F-4-R의 `total_quota`가 NULL(무제한)이면 행을 만들지 않는다.
6. F-2-R·E-7-4R 등 다른 비자유형 담당자가 공고문을 확인할 때 이 설계 원칙이 그대로 적용되는지 재검증한다.
