# D_visa_requirements — 비자 요건·절차·쿼터·변경이력 공유 마스터 테이블

`A_F-2-R`/`B_E-7-4R`/`C_D-2-common`이 비자유형별 전용 폴더인 것과 달리, 이 폴더의 6개 테이블은 `visa_code`(F-2-R/E-7-4R/F-4-R/F-5-6R/E-7-4-GENERAL/D-2-GWANGYEOK 등)를 하나의 파일에 함께 담는 공유 마스터 테이블이다. 여러 비자 담당자가 같은 CSV에 각자 비자의 행을 추가하는 구조이므로, PR을 올릴 때 다른 비자유형의 행을 건드리지 않았는지 diff를 확인한다.

F-4-R 12차 공고문(충청북도 공고 제2026-1158호) 분석 과정에서 확정된 설계 원칙이며, F-2-R·E-7-4R 등 다른 비자유형에도 그대로 적용되는지는 실제 공고문 확인 시 재검증이 필요하다.

## 왜 6개 테이블로 나눴는가

비자 하나를 둘러싼 정보는 변경 빈도가 서로 다른 여섯 가지로 나뉜다. 하나의 테이블에 담으면 "거의 안 바뀌는 값"과 "매달 바뀌는 값"이 섞여서, 갱신할 때마다 안 바뀐 값까지 같이 손대야 하는 문제가 생긴다.

| 파일 | 담는 정보 | 변경 빈도 | 성격 |
|------|-----------|-----------|------|
| `visa_requirements.csv` | 비자의 기본 정체성(요건 범위, 총 모집인원 등) | 거의 안 바뀜 | 마스터 |
| `visa_requirement_criteria.csv` | 합격 여부를 가르는 개별 조건 | 연 1회 내외(요건 개정 시) | 마스터(정규화) |
| `visa_process_stages.csv` | 신청 절차의 각 단계(누가·누구에게·언제까지) | 회차마다 재확인 필요 | 마스터(회차별 이력, 회차마다 새 행 추가) |
| `document_requirements.csv` | 특정 절차 단계에서 제출해야 하는 서류 목록 | 회차마다 재확인 필요 | 마스터(`visa_process_stages`에 종속) |
| `visa_quota_status.csv` | 잔여 인원 스냅샷 | 매달 | 로그(시계열) |
| `change_history.csv` | `visa_requirements`·`visa_requirement_criteria` 값이 회차 간 어떻게 바뀌었는지 | 값이 바뀔 때마다 | 로그(변경 diff) |

`visa_process_stages`·`visa_quota_status`는 애초에 회차별/시점별로 새 행을 쌓는 구조라 그 자체로 이력이다. 반면 `visa_requirements`·`visa_requirement_criteria`는 "현재 유효한 값"만 `valid_from`/`valid_to`로 관리하는 마스터라, 회차가 바뀔 때 무엇이 왜 바뀌었는지는 별도로 기록해야 한다 — 그 역할을 `change_history.csv`가 한다.

## 마스터 레코드 수명주기 (`visa_id` 안정성)

`visa_requirements`·`visa_requirement_criteria`는 회차마다 새 버전 행을 쌓지 않는 **스냅샷** 테이블이다(B_E-7-4R의 `current_requirements.csv`와 동일한 "현재값만 유지" 패턴). 이 문서 초안에 있던 "기존 행을 마감하고 새 행을 추가한다"는 표현은 부정확했다 — 실제 규칙은 다음과 같다.

- **`visa_id`는 `visa_code` 1개당 정확히 하나, 영구히 고정된 식별자다.** 새 공고 회차가 나와도 새 `visa_id`를 발급하지 않고, 다른 회차에도 재사용하지 않는다(재사용 금지 + 불변 = 안정적 논리 키).
- **`visa_requirements.csv`는 `visa_code`당 정확히 1행만 유지한다.** 새 회차 값으로 갱신할 때는 해당 행을 그 자리에서 덮어쓴다(필드 값 + `valid_from`/`valid_to`를 이번 회차 기준으로 갱신). 이전 회차 값은 이 테이블에 별도 행으로 남기지 않고 `change_history.csv`에 diff로만 보존한다.
- **`visa_requirement_criteria.csv`도 같은 원칙**을 요건 단위로 적용한다: 요건이 없어지면(`change_type=removed`) 해당 `criteria_id` 행을 삭제하고, 새로 생기면(`added`) 새 `criteria_id` 행을 추가하고, 값만 바뀌면(`value_changed`) 기존 `criteria_id` 행을 그 자리에서 갱신한다. 세 경우 모두 `change_history.csv`에 대응하는 diff 행을 반드시 같이 남긴다.
- **`visa_process_stages.csv`·`visa_quota_status.csv`는 반대로 append-only 로그다.** 회차마다 새 행을 추가하고 과거 행은 절대 지우거나 덮어쓰지 않는다 — `notice_round`/`as_of_date`가 사실상 버전 축 역할을 한다.
- **하위 테이블은 모두 `visa_id` 단일 컬럼 FK로 마스터를 참조한다.** `visa_requirements`가 회차별로 여러 버전 행을 갖지 않고 항상 "현재 값 1개"만 유지하므로, 특정 회차의 마스터 버전을 가리키는 복합 키(`visa_id`+`notice_round` 등)는 필요 없다 — `visa_id` 하나로 항상 최신 마스터 행을 가리킨다. 과거 회차 값이 필요하면 `change_history.csv`를 조회한다. (`document_requirements.csv`는 예외로 `visa_id`를 두지 않고 `stage_id` 하나로만 `visa_process_stages`를 참조한다 — 이유는 해당 절 참고.)

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
| `quota_type` | text | `LIMITED`(정원 있음)/`UNLIMITED`(원문에 무제한이라고 명시됨)/`UNKNOWN`(원문에서 쿼터 언급 자체를 아직 확인 못함) |
| `total_quota` | integer, nullable | `quota_type=LIMITED`일 때만 정원 숫자를 채운다. `UNLIMITED`/`UNKNOWN`이면 NULL |
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
| `criteria_type` | text | `binary` 고정. 구간별 배점(graduated/점수제)은 이 테이블이 아니라 `scoring_items.csv`가 다룬다 — 아래 "`scoring_items.csv`와의 경계" 참고 |
| `value_numeric` | numeric, nullable | 숫자로 비교 가능한 값("2년 이상", "60세 미만"의 2/60). SQL에서 `operator`와 함께 바로 비교하기 위한 필드 — 숫자로 못 뽑아내는 조건(재량판단 서술형 등)이면 비워두고 `value_text`만 채운다 |
| `operator` | text, nullable | `value_numeric`에 대한 비교연산자(`>=`/`>`/`<=`/`<`/`==`). 두 방향 범위("6세 이상 19세 미만")는 한 행에 담지 않고 하한·상한을 별도 행 2개로 분리해 각각 단일 연산자로 표현한다(묶이지 않은 두 행은 기본 AND) — "복합 조건" 절 참고 |
| `unit` | text, nullable | `value_numeric`의 단위(`년`/`세`/`회`/`만원` 등) |
| `value_text` | text, nullable | 조건 원문 설명. `value_numeric`이 있어도 맥락(어떤 신분·어떤 절차인지 등) 보존을 위해 항상 채운다 |
| `measurement_window_value`/`measurement_window_unit` | numeric/text, nullable | "최근 N년간" 같은 평가 범위. `B_E-7-4R/current_requirements.csv`와 동일한 필드 |
| `condition_group` | text, nullable | 서로 대체 가능한(OR) 조건 묶음 ID(`G1`, `G2`… 임의 라벨, 의미 없음). 유일성은 같은 `visa_id` 안에서만 보장하면 되고, 다른 비자유형 행과 번호가 겹쳐도 무방하다. 묶이지 않은 행은 다른 모든 criteria 행과 기본적으로 AND로 결합된다 |
| `condition_operator` | text, nullable | `condition_group`이 있는 행에만 채움. 현재는 `OR`만 쓴다(AND는 그룹 없이 표현되므로) |
| `special_case_note` | text, nullable | 예외조건 설명, 재량판단 단서 등 — 논리 연산 자체는 여기 적지 않고 `condition_group`/`condition_operator`로 표현 |
| `valid_from`/`valid_to`/`source_document`/`source_page`/`last_verified_at` | — | 표준 버전관리 |

`threshold_value`(자유텍스트) + `point_value`(정수 하나)였던 이전 스키마는 폐기했다. 텍스트만으로는 SQL에서 값을 비교할 수 없었다 — `B_E-7-4R/current_requirements.csv`에 이미 검증된 숫자 비교 패턴(`value_numeric`/`operator`/`unit`/`measurement_window_*`)을 그대로 재사용해 위 필드로 대체했다.

**이 테이블에 넣을지 판단하는 기준**은 아래 "판단 기준 5단계 질문"을 그대로 따른다 — 트래커가 자동으로 충족/미충족을 판정할 수 있는 조건만 행으로 만든다. "인정되는 경우"·"부득이한 경우" 같은 재량 판단 표현이 들어간 조건은 절대 여기 넣지 않는다(`admin_guide_corpus`로).

**`scoring_items.csv`와의 경계**: 둘 다 "구간별로 값이 달라진다"는 점은 비슷해 보이지만 판정 방식이 다르다.

| | `visa_requirement_criteria.csv`(이 파일) | `scoring_items.csv`(예: `B_E-7-4R/scoring_items.csv`) |
|---|---|---|
| 판정 방식 | 행마다 참/거짓, 전체를 **AND/OR 불리언**으로 결합 | 행마다 점수, 전체를 **합산(SUM)**해 `total_score_threshold`와 비교 |
| 다루는 질문 | 신청 자격이 있는가 (충족/미충족) | 자격을 충족한 사람 중 몇 점인가 (순위/합격선) |
| 구간이 있을 때 | 구간 자체가 하나의 참/거짓 조건(예: "6세 이상 19세 미만") — `value_numeric`/`operator` | 구간마다 다른 점수가 붙는 배점표(예: "2,500만원~2,999만원=50점, 3,000만원~=65점") — `min_value`/`max_value`/`points` |
| 예시 | F-4-R 거주지 유지의무, 나이 요건 | E-7-4R K-POINT 평균소득·한국어능력·나이 배점 |

새 조건을 만났을 때 "이게 합격여부를 AND/OR로 가르는가, 점수 합산에 기여하는가"로 구분한다 — 후자면 `visa_requirement_criteria.csv`에 억지로 `min_value`/`max_value`/`point_value` 컬럼을 추가하지 않고 `scoring_items.csv` 쪽에 행을 추가한다. 지금은 E-7-4R만 점수제를 쓰므로 `scoring_items.csv`는 `B_E-7-4R/` 폴더 전용으로 둔다 — 두 번째 비자유형이 점수제 심사를 쓰게 되면 그때 `D_visa_requirements/visa_scoring_items.csv`(공유 `visa_id` FK)로 승격을 검토한다. 아직 소비자가 하나뿐인 상태에서 공유 테이블부터 만들지 않는다.

**OR 조건 처리**: `B_E-7-4R/current_requirements.csv`와 같은 구조를 그대로 쓴다 — 한 문장에 여러 조건이 섞여 있으면 개별 행으로 분리하고, `condition_group`은 서로 관련된(대체 가능한) 조건들의 묶음만 나타낸다. 논리적 결합 관계는 자동으로 정하지 않고 원문을 직접 읽고 `condition_operator`에 사람이 입력한다. F-4-R의 "기존거주자/국내전입자/해외전입자" 3갈래처럼 "이 중 하나만 충족하면 됨"은 세 행 모두 같은 `condition_group`(예: `G1`)과 `condition_operator=OR`을 준다. `condition_group`이 없는 행은 같은 `visa_id`의 다른 모든 행과 AND로 결합된다고 간주한다.

**`condition_group`은 OR 전용이다 — B_E-7-4R의 G번호를 그대로 복사하지 않는다**: `B_E-7-4R/current_requirements.csv`의 `condition_group`(G1~G8 등)은 "서로 관련된 조건들의 묶음"이라는 더 느슨한 정의로 쓰여서, 실제 대체조건(OR)뿐 아니라 하나의 `❍` 아래 딸린 하위조건·보충설명(`※`/`-`로 시작하는 문장)까지 같은 G번호로 묶여 있다 — 그 그룹들 대부분은 `condition_operator`가 비어 있고(AND 취급), OR로 확정된 건 일부뿐이다(`G32` 등). D 공통 스키마의 `condition_group`은 정의상 OR 전용이므로, B의 G번호를 그대로 복사해 오면 원래 AND였던 관계가 OR로 오해될 수 있다. 규칙:
- `condition_group`은 실제로 서로 대체 가능한(OR) 조건에만 부여한다. 하나의 `❍` 아래에 있다는 사실만으로 같은 그룹을 부여하지 않는다.
- B의 기존 데이터를 D로 옮길 때 G번호를 그대로 복사하지 말고, 공고 원문을 다시 읽고 실제 OR 관계만 새로 식별해서 그룹을 매긴다.
- 하위 설명·예외·보충 문장(원문의 `※`/`-` 등)은 논리 그룹으로 만들지 않고 `value_text` 또는 `special_case_note`에 서술로 남긴다.
- 원문의 논리 구조가 애매하면(OR인지 단순 부연설명인지 판단이 안 서면) 임의로 그룹을 부여하지 않고 `condition_group`을 비운 채 사람 검토 대상으로 남긴다(`special_case_note`에 "논리구조 확인 필요"라고 표시).
- `scripts/draft_requirements.py`로 D용 초안을 뽑을 때는 `--candidate-groups` 플래그를 써서 그룹을 `CANDIDATE_G1`처럼 미확정 상태로 받는다 — 이 스크립트는 `❍` 단위로 그룹을 순번 생성할 뿐 OR 여부를 판별하지 않으므로, 초안의 그룹 번호를 그대로 확정하지 않는다(스크립트 모듈 docstring 참고).

**복합 조건("A AND (B OR C)") 처리**: 하나의 필수 조건(A)과 그 조건을 만족하는 두 가지 대체 경로(B/C)가 섞인 경우, A는 `condition_group` 없이 독립 행으로 두고(전체와 AND), B·C만 같은 `condition_group`을 줘서 OR로 묶는다. 예: F-4-R "동반자녀 추가요건"은 "만 6세 이상 19세 미만(연령, AND)" + "① 재학중/입학예정 OR ② 질병·장애로 재학 곤란"이므로, 연령요건은 그룹 없이 하한·상한 2행("동반자녀 연령요건(하한)" `value_numeric=6,operator=>=` / "동반자녀 연령요건(상한)" `value_numeric=19,operator=<`), ①·②는 같은 그룹(`condition_operator=OR`)으로 2행 — 총 4행으로 분리한다. 하나의 행에 AND와 OR를 텍스트로 섞어 넣지 않는다(자동판정이 불가능해지므로).

**지원하지 않는 논리식**: 이 스키마는 "그룹 없는 행끼리 AND" + "같은 그룹 안에서만 OR" 두 가지만 표현한다. `(A AND B) OR C`처럼 AND로 묶인 덩어리끼리 OR로 결합하는 조건이나, 서로 다른 `condition_group` 두 개를 OR로 잇는 조건(`G1 OR G2`)은 이 스키마로 표현할 수 없다 — 지금까지 확인된 공고문 조건 중 그런 사례는 없었고, 나오면 억지로 행을 쪼개 넣지 말고 원문 그대로 `special_case_note`에 남긴 뒤 `admin_guide_corpus`로 보내거나 수동 검토로 넘긴다.

**`condition_group` 채운 뒤 검증 체크리스트**: 새 비자유형의 criteria를 채우고 나면 PR 올리기 전에 아래를 확인한다.
- [ ] `condition_group`이 있는 행은 `condition_operator=OR`인가 (그룹은 있는데 연산자가 비어 있으면 잘못 채운 것)
- [ ] 같은 그룹에 실제 대체조건이 2개 이상 있는가 (그룹 소속이 1개뿐이면 그룹을 만들 이유가 없다 — 그룹 해제)
- [ ] 그룹 없는 행과 그룹 조건 사이의 AND 관계가 원문 의미와 맞는가
- [ ] B_E-7-4R(또는 다른 기존 근거표)의 G번호를 검토 없이 그대로 복사하지 않았는가 — 새 비자유형 공고 원문을 기준으로 OR 관계를 다시 판단했는가

핵심은 기존 근거표의 G번호를 재사용하는 게 아니라, 비자유형별 공고 원문에서 실제 OR 관계만 새로 식별하는 것이다.

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
| `document_requirements_status` | text | `present`(이 단계에 필요한 서류 목록이 `document_requirements.csv`에 이 `stage_id`로 연결돼 있음)/`explicitly_none`(공고문이 이 단계엔 제출서류가 없다고 명시)/`not_checked`(아직 확인 안 함) |
| `valid_from`/`valid_to`/`source_document`/`source_page`/`last_verified_at` | — | 표준 버전관리 |

비자마다 절차 단계 개수 자체가 다르므로(F-4-R 4단계, D-2-GWANGYEOK 5단계) 고정 컬럼이 아니라 행으로 관리한다. `actor_from`이 신청자 유형(재외동포·외국인 등)인 단계만 리마인더가 사용자에게 알림을 준다 — 행정기관끼리 처리하는 단계는 "지금은 기다리는 중"이라고만 안내한다. 매달 새 공고(회차↑)가 나오면 기존 행을 덮어쓰지 않고 새 행을 추가한다.

### `document_requirements.csv`

| 필드 | 타입 | 설명 |
|------|------|------|
| `document_requirement_id` | uuid (PK) | |
| `stage_id` | uuid (FK → `visa_process_stages.stage_id`) | 이 서류가 필요한 절차 단계 |
| `document_name` | text | 서류명 원문 |
| `document_category` | text | `FORM`(공고문 붙임 번호가 있는 공식 양식)/`EVIDENCE`(정해진 양식 없는 증빙서류, 예: 여권사본·소득금액증명원) |
| `filled_by` | text, nullable | `FORM`일 때만 채움: 누가 작성하는지 |
| `submitted_by` | text, nullable | 누가 제출하는지 |
| `submission_target` | text, nullable | 제출처 |
| `signer` | text, nullable | `FORM`일 때만 채움: 서명자 |
| `required_attachments` | text[], nullable | 이 서류 자체에 딸린 첨부. 배열 직렬화 규칙은 "배열 필드 표기" 참고 |
| `is_mandatory` | text | `TRUE`/`FALSE`/`조건부`(조건은 `notes`에 서술) |
| `valid_from`/`valid_to`/`source_document`/`source_page`/`last_verified_at` | — | 표준 버전관리 |
| `notes` | text, nullable | 조건부 사유, 특이사항 |

`B_E-7-4R/document_forms.csv`(서식 전용, E-7-4R 단일 비자용)의 컬럼 어휘를 재사용하되, 공식 서식뿐 아니라 일반 증빙서류까지 다루도록(`document_category`) 넓히고, 특정 절차 단계에 연결되도록(`stage_id`) 확장했다. `visa_process_stages.document_requirements_status=present`인 단계는 이 테이블에 같은 `stage_id`로 연결된 행이 최소 1개 있어야 한다.

**FK 설계: `visa_id`를 중복 저장하지 않는 이유**: 이 테이블은 다른 D 테이블과 달리 `visa_id` 컬럼을 두지 않고 `stage_id` 하나로만 `visa_process_stages`(→ `visa_requirements`)를 참조한다. 다른 D 테이블들은 조회 편의를 위해 `visa_id`를 직접 갖고 있지만, CSV는 FK 제약이 없는 평문 파일이라 같은 값을 두 곳(`document_requirements.visa_id`와, `stage_id`로 조인했을 때 나오는 `visa_process_stages.visa_id`)에 저장하면 둘이 어긋나도 아무것도 막아주지 않는다 — 여러 담당자가 나눠서 편집하는 구조에서 실제로 발생할 수 있는 리스크다. `visa_id`가 필요하면 `stage_id`로 `visa_process_stages`를 조인해서 구한다. `scripts/validate_fk_integrity.py`가 이 폴더 전체의 PK 유일성과 FK 참조 무결성(이 테이블의 `stage_id`가 실제 `visa_process_stages.stage_id`를 가리키는지 포함)을 검사한다 — PR 올리기 전에 실행한다.

### 제출서류 상태값 및 무결성 검증

CSV는 데이터베이스처럼 enum·PK·FK 제약을 자동으로 강제하지 않으므로, D 데이터 변경 후 PR을 올리기 전에 다음 검증을 실행한다.

```bash
uv run python scripts/validate_fk_integrity.py
```

검증 스크립트는 각 테이블의 PK 공백·중복, FK 미참조, `stage_id` 연결, 그리고 `document_requirements_status`와 실제 제출서류 행의 일관성을 확인한다. `stage_id`는 전체 `visa_process_stages.csv`에서 유일한 UUID(PK)이며, `stage_order`와 달리 비자별로만 유일하면 되는 값이 아니다. `document_requirements.csv`는 이 전역적으로 유일한 `stage_id`를 FK로 사용한다.

`document_requirements_status`의 허용값은 다음 세 가지뿐이다.

| 값 | 의미 | 검증 기준 |
| --- | --- | --- |
| `not_checked` | 제출서류 존재 여부를 아직 확인하지 않음 | 제출서류 행의 유무와 관계없이 통과 |
| `present` | 제출서류가 있음 | 같은 `stage_id`의 `document_requirements.csv` 행이 1개 이상이어야 함 |
| `explicitly_none` | 공고문에 제출서류가 없다고 명시됨 | 같은 `stage_id`의 제출서류 행이 없어야 함 |

빈 값, 오타, `unknown` 등 허용 목록에 없는 값은 오류다. 검증 성공 시 종료 코드 0, 오류가 있으면 종료 코드 1을 반환한다.

### 공용 UUID 유틸리티 (`scripts/uuid_utils.py`)

이슈 #29의 UUID 규칙은 CSV를 직접 수정하는 별도 CLI가 아니라, extraction 스크립트가 신규 행을 만든 뒤 공용 유틸리티를 호출하는 방식으로 적용한다. 유틸리티는 CSV를 읽거나 쓰지 않고 ID만 생성·재사용·검증한다.

```python
from scripts.uuid_utils import assign_new_id, get_or_create_visa_id

# visa_id: 같은 visa_code가 있으면 기존 ID를 재사용하고, 없으면 새 UUID v4 발급
visa_row = get_or_create_visa_id(
    {"visa_code": "F-2-R", "visa_name_kr": "지역특화형 우수인재"},
    existing_visa_rows,
    existing_ids,
)

# stage_id/document_requirement_id: 신규 행의 빈 ID에만 UUID v4 발급
stage_row = assign_new_id(
    {"stage_id": "", "visa_id": visa_row["visa_id"], "stage_name": "신청 접수"},
    "stage_id",
    existing_ids,
)
```

기존 ID는 보존하고, 신규 ID가 전체 공통 테이블의 기존 PK와 중복되면 오류다. 행 생성과 CSV 저장은 호출한 extraction 스크립트가 담당하며, 저장 후에는 반드시 `uv run python scripts/validate_fk_integrity.py`로 FK 연결을 확인한다.

### `visa_quota_status.csv`

| 필드 | 타입 | 설명 |
|------|------|------|
| `quota_status_id` | uuid (PK) | |
| `visa_id` | uuid (FK) | |
| `notice_round` | integer | 몇 차 공고 기준 |
| `remaining_quota` | integer, nullable | 잔여 인원. 이 테이블은 `quota_type=LIMITED`인 비자만 대상이므로 원칙적으로 숫자가 채워진다. NULL은 "무제한"이 아니라 "이번 회차 공고에 잔여인원 수치가 발표되지 않음"을 뜻한다 |
| `as_of_date` | date | 공고일 기준 |
| `source_document`/`source_page` | — | 표준 |
| `recorded_at` | date | 팀이 기록한 날짜 |

**표준 5필드에서 벗어난 이유**: "현재 유효한 값"이 아니라 시점별 기록을 영구히 쌓는 로그다. `valid_from`/`valid_to`(언제까지 유효했는지) 개념이 안 맞아서 `as_of_date`+`recorded_at`으로 대체했다.

**행을 만드는 기준**: `visa_requirements.quota_type=UNLIMITED`로 **확정된** 비자만 이 테이블에 행을 만들지 않는다. `quota_type=UNKNOWN`(원문에서 쿼터 여부 자체를 아직 확인 못한 상태)인 비자는 무제한으로 단정하지 않는다 — `total_quota`가 NULL이라고 자동으로 "쿼터 없음"으로 해석해 이 테이블을 건너뛰면 안 된다. 확인 전까지는 `visa_requirements.quota_type=UNKNOWN`으로 남겨 두고, 공고문에서 정원 여부가 확인되는 대로 `LIMITED`/`UNLIMITED`로 갱신한다.

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

`B_E-7-4R/change_history.csv`와 같은 패턴이되, 이 폴더는 여러 비자유형·테이블이 한 파일을 공유하므로 `visa_id`와 `table_name`으로 어느 비자의 어느 테이블 변경인지 구분한다. `visa_requirements`·`visa_requirement_criteria`는 "마스터 레코드 수명주기"에서 설명한 대로 스냅샷이라 옛 값이 테이블 안에 남지 않으므로, 새 회차 값으로 그 자리에서 갱신할 때마다 이 테이블에 diff 행을 반드시 같이 남긴다 — 그래야 이전 값을 조회할 유일한 경로가 생긴다.

## 판단 기준 5단계 질문

새 정보를 발견할 때마다 이 순서로 어느 테이블에 넣을지(또는 스키마화하지 않을지) 정한다.

```text
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
5. `visa_quota_status.csv`는 F-4-R처럼 `quota_type=UNLIMITED`로 확정된 비자면 행을 만들지 않는다.
6. F-2-R·E-7-4R 등 다른 비자유형 담당자가 공고문을 확인할 때 이 설계 원칙이 그대로 적용되는지 재검증한다.
7. `document_requirements.csv`는 아직 헤더만 있다 — 12차 공고문 p.4(신청 접수 단계 제출서류 목록) 등 실제 내용이 확인되는 대로 채우고, 해당 `visa_process_stages` 행의 `document_requirements_status`를 `not_checked`에서 `present`로 갱신한다.
