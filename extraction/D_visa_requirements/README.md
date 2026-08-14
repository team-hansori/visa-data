# D_visa_requirements — 비자 요건·절차·쿼터 공유 마스터 테이블

`A_F-2-R`/`B_E-7-4R`/`C_D-2-common`이 비자유형별 전용 폴더인 것과 달리, 이 폴더의 4개 테이블은 `visa_code`(F-2-R/E-7-4R/F-4-R/F-5-6R/E-7-4-GENERAL/D-2-GWANGYEOK 등)를 하나의 파일에 함께 담는 공유 마스터 테이블이다. 여러 비자 담당자가 같은 CSV에 각자 비자의 행을 추가하는 구조이므로, PR을 올릴 때 다른 비자유형의 행을 건드리지 않았는지 diff를 확인한다.

F-4-R 12차 공고문(충청북도 공고 제2026-1158호) 분석 과정에서 확정된 설계 원칙이며, F-2-R·E-7-4R 등 다른 비자유형에도 그대로 적용되는지는 실제 공고문 확인 시 재검증이 필요하다.

## 왜 4개 테이블로 나눴는가

비자 하나를 둘러싼 정보는 변경 빈도가 서로 다른 네 가지로 나뉜다. 하나의 테이블에 담으면 "거의 안 바뀌는 값"과 "매달 바뀌는 값"이 섞여서, 갱신할 때마다 안 바뀐 값까지 같이 손대야 하는 문제가 생긴다.

| 파일 | 담는 정보 | 변경 빈도 | 성격 |
|------|-----------|-----------|------|
| `visa_requirements.csv` | 비자의 기본 정체성(요건 범위, 총 모집인원 등) | 거의 안 바뀜 | 마스터 |
| `visa_requirement_criteria.csv` | 합격 여부를 가르는 개별 조건 | 연 1회 내외(요건 개정 시) | 마스터(정규화) |
| `visa_process_stages.csv` | 신청 절차의 각 단계(누가·누구에게·언제까지) | 회차마다 재확인 필요 | 마스터(회차별 이력) |
| `visa_quota_status.csv` | 잔여 인원 스냅샷 | 매달 | 로그(시계열) |

## 파일별 스펙

### `visa_requirements.csv`

| 필드 | 타입 | 설명 |
|------|------|------|
| `visa_id` | uuid (PK) | |
| `visa_code` | text | `F-2-R`/`E-7-4R`/`F-4-R`/`F-5-6R`/`E-7-4-GENERAL`/`D-2-GWANGYEOK` |
| `visa_name_kr` | text | 표시명 |
| `program_type` | text | `REGIONAL_SPECIALIZED`/`GENERAL`/`GWANGYEOK` |
| `target_region` | text[] | 대상 시군(전국이면 NULL) |
| `total_score_threshold` | integer, nullable | 점수제 합격선(점수제 아니면 NULL) |
| `residency_limit_years` | integer | 거주지 제한기간 |
| `allowed_industries` | text[], nullable | 업종 제한(제한 없으면 NULL) |
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
| `special_case_note` | text, nullable | 예외조건, OR조건 명시 |
| `valid_from`/`valid_to`/`source_document`/`source_page`/`last_verified_at` | — | 표준 버전관리 |

**이 테이블에 넣을지 판단하는 기준**은 아래 "판단 기준 5단계 질문"을 그대로 따른다 — 트래커가 자동으로 충족/미충족을 판정할 수 있는 조건만 행으로 만든다. "인정되는 경우"·"부득이한 경우" 같은 재량 판단 표현이 들어간 조건은 절대 여기 넣지 않는다(`admin_guide_corpus`로).

**OR 조건 처리**: F-4-R의 "기존거주자/국내전입자/해외전입자" 3갈래처럼 "이 중 하나만 충족하면 됨"은 각각 별도 행으로 만들고, `special_case_note`에 "N개 유형 중 하나만 충족하면 됨(OR)"이라고 명시한다.

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
