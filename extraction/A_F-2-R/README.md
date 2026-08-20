# A_F-2-R — 지역특화 우수인재(F-2-R) 원천 근거표

이 폴더는 F-2-R 공고문과 안내·참고자료에서 직접 추출한 **비자별 원천 근거표**를 보존한다. 여러 비자유형을 합친 서비스용 공통 마스터는 `extraction/D_visa_requirements/`에서 별도 PR로 관리한다.

## 식별자

- `visa_id`: `78dca2d7-f771-553a-b788-46c9ff56d633`
- 위 `visa_id`는 F-2-R 비자 코드·트랙 자체를 식별하며 공고 차수나 지역이 달라져도 재사용한다.
- 공고 차수와 적용기간은 `announcement_round`, `valid_from`, `valid_to`, 변경 이력으로 구분한다.
- 원천 `group_id`는 이 폴더의 중첩 AND/OR 구조를 표현하는 UUID다. 공통 마스터의 `condition_group=G1` 같은 로컬 라벨과 동일한 식별자가 아니다.
- 공통 마스터로 정규화하는 각 criteria 행에는 원천 `criteria_id`를 복사하지 않고 새 `criteria_id` UUID를 발급한다.

## #39 공통 마스터 매핑 결과

- 상세 규칙: [`COMMON_MASTER_MAPPING.md`](COMMON_MASTER_MAPPING.md)
- 행 단위 매핑표: [`common_master_mapping.csv`](common_master_mapping.csv)
- 재생성 코드: [`../../scripts/build_f2r_common_mapping.py`](../../scripts/build_f2r_common_mapping.py)
- `common_master_mapping.csv`는 원천 14종에 추가된 **지원 파일**이며 원천 추출 행 수 934행에는 포함하지 않는다.
- `visa_requirements.csv`의 `target_region`은 D 공통 마스터와 같은 파이프 구분 배열 문자열을 사용한다.
- 매핑표 70행은 기본정보 1행과 criteria 69행을 정확히 한 번씩 다룬다. 결과는 `ready` 15행, `blocked` 44행, `not_applicable` 11행이다.
- #39에서는 D 공통 마스터 CSV를 수정하지 않는다. 실제 공통 행 추가는 열린 업무 검토와 통합 순서를 확인한 뒤 별도 PR에서 수행한다.

## CSV 데이터 사전

이 절은 원천 CSV 14종과 지원 파일 `common_master_mapping.csv`의 모든 컬럼을 설명한다. 표에 적힌 값은 현재 파일에서 실제로 사용하는 코드이며, 빈 문자열은 기본적으로 **0 또는 거짓이 아니라 값이 없거나 해당하지 않음**을 뜻한다. 날짜는 `YYYY-MM-DD`, 시각은 시간대가 포함된 ISO 8601 형식을 사용한다.

| 파일 | 행 수 | 역할 |
| --- | ---: | --- |
| `visa_requirements.csv` | 1 | F-2-R 트랙의 최신 기본정보 |
| `visa_criterion_groups.csv` | 23 | 자격조건의 중첩 AND/OR 구조 |
| `visa_requirement_criteria.csv` | 69 | 개별 자격·의무·예외 조건 |
| `visa_announcement_rounds.csv` | 10 | 8~17차 공고 기본정보 |
| `visa_required_documents.csv` | 45 | 신청 단계별 제출서류 |
| `visa_regional_quotas.csv` | 60 | 차수·시군별 배정·기추천·잔여 인원 |
| `visa_round_facts.csv` | 485 | 차수별 비교 가능한 원천 사실 |
| `visa_current_facts.csv` | 53 | 최신 차수 우선으로 선택한 현재 사실 |
| `visa_fact_coverage.csv` | 70 | 차수·영역별 추출 완전성 |
| `visa_change_history.csv` | 93 | 인접 차수 간 사실 변경 이력 |
| `visa_scoring_models.csv` | 1 | 추천 우선순위 점수 모델 |
| `visa_scoring_items.csv` | 12 | 점수 모델의 배점 구간 |
| `extraction_review_queue.csv` | 6 | 사람 검수가 필요한 차단 항목 |
| `ingestion_issues.csv` | 6 | 수집·원문 품질 이슈 |
| `common_master_mapping.csv` | 70 | A 원천 행의 D 공통 마스터 이관 판단 |

### 처음 보는 사람이 CSV 한 행을 읽는 순서

1. 먼저 이 README의 파일 설명에서 해당 CSV가 **현재값, 원천 사실, 변경 이력, 검토 로그 중 무엇인지** 확인한다.
2. `criteria_name`, `fact_name_kr`, `document_name`, `change_summary`처럼 사람이 읽는 이름으로 행의 주제를 파악한다.
3. 숫자 조건이면 `comparison_operator`·`value_number`·`unit`을 묶어서 읽고, 문자열 조건이면 `comparison_operator`·`value_text`·`threshold_value`를 묶어서 읽는다.
4. `group_id`가 있으면 `visa_criterion_groups.csv`를 따라가 상위·하위 AND/OR 관계를 확인한다. criteria 한 행만 보고 전체 신청자격이라고 판단하지 않는다.
5. `source_document_id`와 문단·표·페이지 위치에서 원문 근거를 확인하고, `source_text`가 정규화된 값과 같은 의미인지 대조한다.
6. 마지막으로 `extraction_status`, `review_status`, `consumption_gate`, 검토 큐를 확인한다. 값이 있어도 차단 상태면 서비스 판정에 사용하지 않는다.

### 여러 CSV에서 공통으로 쓰는 컬럼

| 컬럼 | 의미 | 값·표기 규칙 |
| --- | --- | --- |
| `visa_id` | F-2-R 비자 코드·트랙의 고정 식별자 | 모든 F-2-R 행에서 `78dca2d7-f771-553a-b788-46c9ff56d633` 재사용 |
| `visa_code` | 사람이 읽는 비자 코드 | `F-2-R` |
| `announcement_round` | 행이 설명하는 공고 차수 | 정수. 현재 수집 범위는 8~17차 |
| `source_round` | 해당 값이 실제로 추출된 원문 공고 차수 | 최신값은 `17`, 보완 점수표는 `9` |
| `is_current` | 현재 최신 공고 여부 | `1`=최신, `0`=과거 |
| `source_document_id` | 원천 문서 식별자 | 차수·문서유형·연도·해시 일부를 결합한 값. 예: `r17_announcement_2026_df1fdde9` |
| `source_section` | HWPX 내부 section 번호 | 0부터 시작하는 정수 |
| `source_block_index` | section 안의 문단·블록 위치 | 0부터 시작하는 정수. 표 근거만 있으면 비울 수 있음 |
| `source_table_index` | section 안의 표 위치 | 0부터 시작하는 정수. 문단 근거만 있으면 비울 수 있음 |
| `source_page` | 검수된 문서 페이지 번호 | 페이지 체계는 반드시 `source_page_basis`와 함께 해석 |
| `source_page_basis` | `source_page`가 어느 페이지 체계인지 설명 | 예: 변환 PDF 페이지, HWPX 레이아웃 페이지 |
| `source_text` | 행의 근거가 된 원문 텍스트 | 가능한 한 원문을 그대로 보존 |
| `raw_text` | 배점표 셀처럼 가공 전 형태를 별도로 보존한 원문 | 정규화된 `criterion`과 함께 사용 |
| `value_text` | 문자열로 표현한 값 | 날짜·상태·분류 코드 또는 텍스트 조건 |
| `value_number` | 계산·비교 가능한 숫자값 | 숫자로 표현할 수 없으면 비움 |
| `unit` | 숫자값의 단위 | `year`, `month`, `day`, `person`, `KRW`, `KRW/year`, `grade`, `level`, `count`, `date` 등 |
| `valid_from` | 해당 요건·모델이 적용되기 시작하는 날 | 행 자체 기간이 없으면 비어 있거나 마스터 접수기간을 이관 시 상속 |
| `valid_to` | 해당 요건·모델의 적용 종료일 | 종료일을 확인하지 못했으면 비울 수 있음 |
| `date_basis` | 날짜값을 선택한 근거 | 공고의 접수기간, 명시된 시행일, 시범기간 등 |
| `fill_strategy` | 최신값을 채운 방식 | `latest`=최신 원문, `backfilled`=이전 차수에서 제한적으로 보완 |
| `display_order` | 화면·문서에서의 정렬 순서 | 작은 숫자가 먼저 표시됨 |
| `related_source_document_ids_json` | 함께 대조한 원문 ID 목록 | JSON 문자열 배열 |
| `extracted_at` | 데이터 추출 실행 시각 | ISO 8601 타임스탬프 |
| `last_verified_at` | 사람이 마지막으로 확인한 날짜 | `YYYY-MM-DD` |
| `extraction_status` | 추출·검수 상태 | `auto_extracted`=자동 추출 결과, `reviewed`=사람 검토 반영 |
| `confidence` | 추출 신뢰도 | 0~1. 원문 정확성의 법적 보증이 아니라 추출 품질 참고값 |
| `created_at` | 검토·이슈 행을 생성한 시각 | ISO 8601 타임스탬프 |

#### 공통 상태 코드 읽는 법

| 컬럼·값 | 구체적인 의미 | 처리 방법 |
| --- | --- | --- |
| `is_current=1` | 이 행이 현재 최신 공고를 나타냄 | 최신 화면·현재값 계산에서 사용 |
| `is_current=0` | 과거 공고 행 | 삭제하지 않고 변경 이력과 차수 비교에 사용 |
| `extraction_status=auto_extracted` | 코드가 원문에서 자동으로 뽑은 값이며 사람의 의미 검토가 끝났다는 뜻은 아님 | `confidence`, 원문 위치, 검토 큐를 함께 확인 |
| `extraction_status=reviewed` | 자동 추출 후 사람이 원문과 대조해 정규화·검토를 반영함 | 그래도 `review_status`나 열린 검토 항목이 있으면 서비스 소비는 차단될 수 있음 |
| `fill_strategy=latest` | 가장 최신 차수 원문에 존재하는 값을 사용함 | `source_round`가 실제 최신 근거 차수인지 확인 |
| `fill_strategy=backfilled` | 최신 차수에 완전한 정보가 없어 이전 차수에서 일부만 보완함 | `inheritance_scope`, `applicability_assumption`, `review_status`를 반드시 함께 확인 |
| `value_status=present` | 원문에서 해당 값이나 문구가 실제로 확인됨 | “요건을 충족했다”가 아니라 “원문에 값이 존재한다”는 뜻 |
| `review_status=needs_review` | 업무상 현행성·적용범위 검수가 끝나지 않음 | 서비스·점수 엔진에서 사용 금지 |
| `review_status=reviewed` | 지정한 완료 기준에 따라 업무 검수가 끝남 | `consumption_gate`도 별도로 확인 |
| `consumption_gate=blocked_while_needs_review` | 검수 중인 동안 소비를 강제로 차단 | 데이터를 표시·계산에 사용하지 않음 |
| `consumption_gate=allowed` | 검수 완료 후 소비 허용 | `review_status=reviewed`와 동시에 만족해야 함 |
| 빈 문자열 | 값이 0이거나 거짓이라는 뜻이 아니라 미확인·해당 없음·다른 컬럼에서 관리 중이라는 뜻 | 컬럼 설명과 원문을 확인한 뒤 해석 |

### `visa_requirements.csv`

비자 트랙당 한 행만 유지하는 최신 기본정보다. 공통 컬럼으로 `visa_id`, `visa_code`, `announcement_round`, `is_current`, 적용기간, 출처 위치, 추출·검수 정보를 함께 사용한다.

| 컬럼 | 의미 | 값·표기 규칙 |
| --- | --- | --- |
| `visa_name_kr` | 서비스에 표시할 비자명 | `지역특화형 지역우수인재` |
| `program_type` | 사업 유형 | 현재 원천값 `지역특화형`; D 이관 시 `REGIONAL_SPECIALIZED`로 정규화 |
| `target_region` | 사업 대상 시군 목록 | 파이프 문자로 구분. 현재 제천시·보은군·옥천군·영동군·괴산군·단양군 |
| `total_score_threshold` | 자격 판정에 필요한 최저 총점 | 비어 있으면 최저 합격점이 확정되지 않았다는 뜻. 현재 점수표는 쿼터 초과 시 우선순위용 |
| `residency_limit_years` | 제도상 거주 제한기간의 연 단위 정규화 값 | 정수 |
| `allowed_industries_json` | 허용 업종 목록 | JSON 문자열 배열. 값이 확인되지 않았거나 별도 조건표로 관리하면 비움 |
| `application_method` | 신청·접수 방법 요약 | 현재 시·군 지역특화비자 담당부서 방문접수 |

### `visa_criterion_groups.csv`

개별 criteria를 중첩 논리식으로 묶는 원천 전용 그룹 테이블이다.

| 컬럼 | 의미 | 값·표기 규칙 |
| --- | --- | --- |
| `group_id` | 논리그룹 행의 UUID | A 폴더 내부에서만 사용하는 원천 그룹 ID |
| `visa_id` | 그룹이 속한 비자 | 공통 정의 참고 |
| `parent_group_id` | 상위 논리그룹 ID | 최상위 그룹이면 빈 값 |
| `group_key` | 코드·조인에 사용하는 사람이 읽을 수 있는 그룹 키 | 같은 비자 안에서 의미가 겹치지 않게 작성 |
| `group_name_kr` | 그룹의 한국어 표시명 | 예: 신청대상, 학력 또는 소득 |
| `boolean_operator` | 직접 연결된 criteria와 하위 그룹의 결합 방식 | `AND`=모두 충족, `OR`=하나 이상 충족 |
| `group_scope` | 그룹이 적용되는 업무 범위 | `eligibility`=최초 신청자격, `exception`=예외·특례, `procedure`=행정절차, `post_approval`=승인 후 의무, `dependent_family`=동반가족 |
| `applicability_note` | 그룹 적용 조건이나 해석상 주의사항 | 추가 설명이 없으면 빈 값 |
| `display_order` | 그룹 정렬 순서 | 공통 정의 참고 |

### `visa_requirement_criteria.csv`

원문에서 분리한 개별 조건 행이다. `group_id`와 `visa_criterion_groups.csv`를 함께 읽어야 전체 AND/OR 의미가 보존된다.

| 컬럼 | 의미 | 값·표기 규칙 |
| --- | --- | --- |
| `criteria_id` | 개별 조건 행의 UUID | 원천 행 ID이며 D 공통 마스터 이관 시 새 UUID 발급 |
| `visa_id` | 조건이 속한 비자 | 공통 정의 참고 |
| `group_id` | 조건이 직접 속한 원천 논리그룹 | `visa_criterion_groups.group_id` 참조 |
| `requirement_type` | 조건의 업무 영역 | 아래 “업무 영역 코드” 표 참고 |
| `criteria_name` | 사람이 읽는 조건명 | 한 행이 판정하는 최소 단위로 작성 |
| `criteria_type` | 조건 성격 | `binary`=충족/미충족 판정, `informational`=자동판정용이 아닌 설명성 정보 |
| `comparison_operator` | `value_number` 또는 `value_text`를 신청자 값과 비교하는 방식 | 아래 “비교 연산자” 표처럼 다른 값 컬럼과 함께 읽음 |
| `value_number` | 비교 대상 숫자 | 숫자 조건이 아니면 빈 값 |
| `value_text` | 비교 대상 문자열 또는 정규화 코드 | 예: 특정 상태·지역·소득종류 코드 |
| `unit` | `value_number`의 단위 | 아래 “단위 코드” 표 참고 |
| `threshold_value` | 원문 의미를 사람이 읽을 수 있게 정리한 기준값 | 숫자·코드만으로 부족한 판정 맥락을 보존 |
| `point_value` | 조건 자체에 직접 붙는 점수 | 자격조건 테이블에서는 대체로 비움. 구간별 배점은 `visa_scoring_items.csv`에서 관리 |
| `special_case_note` | 예외·결합관계·수동검토 메모 | 중첩 AND/OR, 재량판단, 적용 제한 등을 기록 |
| `value_status` | 원문에서 값의 존재 상태 | 현재 `present`=원문에 값이 명시됨 |
| `display_order` | 조건 정렬 순서 | 공통 정의 참고 |
| `valid_from`, `valid_to` | 조건 자체의 명시적 적용기간 | 비어 있으면 D 이관 시 마스터 신청기간 상속 여부를 검토 |
| `source_document_id`~`source_text` | 조건 근거 문서와 HWPX 위치·원문 | 공통 정의 참고 |
| `source_round` | 조건을 추출한 차수 | 현재 최신 조건은 `17` |
| `fill_strategy` | 값 선택 방식 | 현재 `latest` |
| `date_basis` | 조건 적용기간 판단 근거 | `not_explicit_in_source`=원문에 별도 기간 없음, `explicit amendment effective date`=개정 시행일 명시, `explicit pilot period`=시범기간 명시, `2026 annual living-wage standard`=2026년 생활임금 기준 |
| `extracted_at`~`confidence` | 추출·검수 메타데이터 | 공통 정의 참고 |

#### 비교 연산자 코드

`comparison_operator`는 단독으로 읽지 않는다. 숫자 조건은 `value_number`와 `unit`, 문자열 조건은 `value_text`와 `threshold_value`를 함께 읽는다.

| 값 | 판정 의미 | 읽는 방법 | 실제 데이터 예시 |
| --- | --- | --- | --- |
| `=` | 신청자 값이 기준값과 같음 | 주로 상태·분류 코드의 일치 여부를 판단 | `value_text=continue_current_workplace`이면 “현 근무처에서 계속 근무 예정” 상태와 같아야 함 |
| `>=` | 기준값 이상 | 신청자 숫자 ≥ `value_number` | `2`, `year`이면 2년 이상 |
| `<=` | 기준값 이하 | 신청자 숫자 ≤ `value_number` | `30`, `day`이면 30일 이내 |
| `<` | 기준값 미만 | 신청자 숫자 < `value_number` | `3000000`, `KRW`이면 300만원 미만 |
| `IN` | 신청자 값이 허용 목록 안에 포함됨 | `value_text` 또는 원문에 정의된 목록 중 하나와 일치해야 함 | 인정 소득 종류나 허용 대상 범위에 포함되는지 판정 |
| `NOT_IN` | 신청자 값이 금지·제외 목록에 포함되지 않음 | 목록에 하나라도 해당하면 미충족 | 제한업종·결격 대상 목록에 속하지 않아야 함 |
| `EXISTS` | 필요한 사실·상태·서류가 존재함 | 값의 크기보다 존재 여부를 판정 | 필수 교육 이수 기록 또는 제출서류가 있어야 함 |
| `NOT_EXISTS` | 금지되는 사실·상태가 존재하지 않음 | 해당 사실이 발견되면 미충족 | `value_text=duplicate_local_government_application`이면 타 지자체 중복 추천 신청이 없어야 함 |

#### 업무 영역 코드

| 값 | 한국어 의미 | 포함되는 조건 예시 |
| --- | --- | --- |
| `applicant_status` | 신청 가능한 현재 체류자격·신분 | E-7-4 또는 E-7-4R 경로 |
| `education` | 학력 요건 | 국내 전문학사 이상 취득·졸업예정 |
| `income` | 소득 요건 | 생활임금, 소득 주체·기간·종류 |
| `language` | 한국어 능력 | TOPIK, 사회통합프로그램 단계 |
| `residence` | 거주지와 실거주 요건 | 추천지역 계속 거주, 전입 유예 |
| `employment` | 신청자의 취업 요건 | 근무지역, 급여, 계약기간 |
| `entrepreneurship` | 신청자의 창업 요건 | 사업체 소재지, 투자금액 |
| `conduct` | 신청자의 준법·범죄 관련 요건 | 범죄 전력, 벌금·범칙금, 교육 이수 |
| `employer` | 고용주의 기본 요건 | 고용주와 사용자 동일 여부 등 |
| `employer_capacity` | 고용 가능 인원 산정 | 내국인 고용인원별 외국인 허용 규모 |
| `employer_disqualification` | 고용기업 결격사유 | 세금 체납, 임금 체불 등 |
| `excluded_applicants` | 신청 제외 대상 | 중복 추천, 입국금지 등 |
| `restricted_industries` | 취업 제한 업종 | 허용·제한 업종 판단 |
| `small_business_exception` | 지역활력 소상공인 고용특례 | 대상기업, 기간, 허용인원 |
| `recommendation_procedure` | 지자체 추천서 발급 절차 | 신청·추천·제출 순서 |
| `post_approval_maintenance` | 승인 이후 유지의무 | 허가 후 거주·근무 유지 |
| `stay_period` | 체류기간 부여·연장 | 최초 부여기간, 최초·이후 연장기간 |
| `dependent_family` | 동반가족 요건 | 동일 주소 거주, 학령기 자녀 재학 |

#### 단위 코드

| 값 | 뜻 | 예시 |
| --- | --- | --- |
| `year` | 기간의 연 수 | 2년 이상 체류 |
| `month` | 기간의 개월 수 | 신청 후 3개월 이내 취업 시작 |
| `day` | 기간의 일 수 | 30일 이내 전입 |
| `lookback_year` | 과거를 조회하는 기간의 연 수 | 최근 10년간 기록 확인 |
| `person` | 사람 수 | F-2-R 1명 고용 허용 |
| `count` | 사건·처분·위반 횟수 | 범칙금 처분 3회 미만 |
| `KRW` | 원화 금액 | 벌금 300만원 미만 |
| `KRW/year` | 연간 원화 금액 | 연간 생활임금 이상 |
| `grade` | TOPIK 급수 | TOPIK 3급 이상 |
| `level` | 사회통합프로그램 단계 | 사전평가 4단계 이상 |

#### criteria 한 행 읽는 예시

- `E-7-4 체류기간`: `comparison_operator`=`>=`, `value_number`=`2`, `unit`=`year`이므로 **E-7-4 자격변경 후 2년 이상 경과해야 한다**는 뜻이다. 이 조건만으로 충분하지 않고 같은 그룹의 다른 AND/OR 조건도 확인한다.
- `실거주 유예`: `comparison_operator`=`<=`, `value_number`=`30`, `unit`=`day`이므로 **자격변경 후 30일 이내에 전입신고와 이사를 완료해야 실거주로 인정**한다는 뜻이다.
- `타 지자체 중복 추천 신청`: `comparison_operator`=`NOT_EXISTS`이므로 **타 지자체에 동시에 추천을 신청한 사실이 없어야 한다**는 뜻이다.

### `visa_announcement_rounds.csv`

8~17차 공고의 번호·공고일·접수기간·총정원을 차수별로 기록한다.

| 컬럼 | 의미 | 값·표기 규칙 |
| --- | --- | --- |
| `announcement_id` | 공고 차수 행의 UUID | `visa_regional_quotas.announcement_id`가 참조 |
| `visa_code` | 대상 비자 | 공통 정의 참고 |
| `announcement_round` | 공고 차수 | 8~17 |
| `notice_number` | 충청북도 공고번호 | `연도-번호` 형식 |
| `announcement_date` | 해당 차수의 게시일 | `YYYY-MM-DD` |
| `application_start_date` | 공고 안에 적힌 접수 시작일 | 현재 모든 차수에 반복된 사업 전체 시작일 `2025-03-07` |
| `application_end_date` | 공고 안에 적힌 접수 종료일 | 현재 모든 차수에 반복된 사업 전체 종료일 `2026-09-18` |
| `application_period_scope` | 접수기간이 적용되는 범위 | `program`=개별 차수만의 기간이 아니라 사업 전체 기간 |
| `total_quota` | 해당 공고에 표시된 전체 정원 | 현재 `311`명 |
| `is_current` | 최신 차수 여부 | 공통 정의 참고 |
| `value_status` | 값이 원문에 명시됐는지 | `present` |
| `source_document_id`~`source_text` | 접수기간 근거 문서와 위치·원문 | 공통 정의 참고 |
| `date_basis` | 접수기간 해석 근거 | `program-wide period repeated in each rolling notice`=각 차수에 반복된 사업 전체 기간 |
| `extracted_at`~`last_verified_at` | 추출·검수 메타데이터 | 공통 정의 참고 |

### `visa_required_documents.csv`

17차 기준으로 신청 단계별 제출서류를 한 행에 한 종류씩 기록한다.

| 컬럼 | 의미 | 값·표기 규칙 |
| --- | --- | --- |
| `document_requirement_id` | 제출서류 요건 행의 UUID | 원천 행 ID |
| `visa_id` | 서류가 속한 비자 | 공통 정의 참고 |
| `submission_stage` | 서류 제출 단계 | `city_county`=시·군 추천 신청, `immigration_office`=출입국·외국인관서 체류자격 신청 |
| `submitted_by` | 서류를 제출하는 주체 | 외국인 신청자, 고용기업, 취업·창업 신청자 등 |
| `document_category` | 서류의 원천 업무 분류 | `application` 신청서, `identity` 신원, `education` 학력, `language` 언어, `residence` 거주, `employment` 취업, `entrepreneurship` 창업, `investment` 투자, `sales` 매출, `employer` 고용주, `family` 가족, `conduct` 준법·범죄, `eligibility` 자격, `recommendation` 추천, `pledge` 서약, `receipt` 접수·수령, `dossier` 서류묶음, `small_business_exception` 소상공인 특례 |
| `alternative_group` | 서로 대체 가능한 서류 묶음 | 같은 값의 행 중 하나를 제출하는 구조. 대체관계가 없으면 빈 값 |
| `document_name` | 제출서류명 | 원문 명칭을 보존하되 명백한 원문 오탈자는 이슈 기록 후 정규화 가능 |
| `required_status` | 제출 필요 방식 | `required`=필수, `conditional`=조건부, `alternative`=같은 대체그룹에서 택일 |
| `condition_note` | 조건부·대체 제출의 적용 조건 | 조건이 없으면 빈 값 |
| `display_order` | 서류 정렬 순서 | 공통 정의 참고 |
| `valid_from`, `valid_to` | 서류 자체의 명시적 적용기간 | 개정 시행일·시범기간이 있는 경우만 별도 입력 가능 |
| `source_document_id`~`source_text` | 서류 목록 근거 문서와 위치·원문 | 공통 정의 참고 |
| `source_round` | 서류를 추출한 공고 차수 | 현재 `17` |
| `fill_strategy` | 값 선택 방식 | 현재 `latest` |
| `date_basis` | 적용기간 근거 | `round-17 document list`=17차 서류목록 기준, `explicit amendment effective date`=개정 시행일 기준, `explicit pilot period`=원문에 명시된 시범기간 기준 |
| `extracted_at`~`confidence` | 추출·검수 메타데이터 | 공통 정의 참고 |

### `visa_regional_quotas.csv`

각 공고 차수의 6개 시군별 정원 현황을 기록한다.

| 컬럼 | 의미 | 값·표기 규칙 |
| --- | --- | --- |
| `quota_id` | 지역 쿼터 행의 UUID | 차수와 지역 조합별 원천 행 ID |
| `announcement_id` | 해당 쿼터가 속한 공고 행 | `visa_announcement_rounds.announcement_id` 참조 |
| `region` | 대상 시군 | 제천시, 보은군, 옥천군, 영동군, 괴산군, 단양군 |
| `allocated_quota` | 시군에 배정된 총인원 | 정수, 단위는 명 |
| `previously_recommended` | 해당 시점까지 이미 추천된 인원 | 정수, 단위는 명 |
| `remaining_quota` | 공고에 표시된 잔여 추천 가능 인원 | 정수. `allocated_quota - previously_recommended`와 대조 가능 |
| `source_document_id` | 쿼터표가 있는 공고 문서 | 공통 정의 참고 |
| `source_section` | 쿼터표의 HWPX section | 공통 정의 참고 |
| `source_table_index` | 쿼터표 위치 | 공통 정의 참고 |
| `source_text` | 해당 지역의 표 행 원문 | 지역·배정·기추천·잔여 값 보존 |
| `extracted_at`~`confidence` | 추출 메타데이터 | 현재 `auto_extracted` |

**한 행 읽는 예시:** 제천시 행의 `allocated_quota=75`, `previously_recommended=42`, `remaining_quota=33`은 **제천시 배정 75명 중 42명이 이미 추천되어 33명이 남았다**는 뜻이다. 이 수치는 `announcement_id`로 연결된 특정 공고 시점의 스냅샷이지 현재 실시간 잔여인원은 아니다.

### `visa_round_facts.csv`

차수 간 비교와 최신값 선택을 위해 공고별 사실을 동일한 키로 펼친 중간 테이블이다.

| 컬럼 | 의미 | 값·표기 규칙 |
| --- | --- | --- |
| `fact_id` | 차수별 사실 행의 UUID | 같은 사실이라도 차수가 다르면 다른 행 |
| `visa_code` | 대상 비자 | 공통 정의 참고 |
| `announcement_round` | 사실이 속한 공고 차수 | 8~17 |
| `fact_domain` | 사실의 큰 영역 | `application` 접수, `regional_quota` 지역쿼터, `requirement` 요건, `attachment_form` 붙임서식, `attachment_content` 붙임내용 |
| `fact_key` | 차수 간 같은 사실을 연결하는 안정적인 기계 키 | 변경 비교와 최신값 선택의 조인 키 |
| `fact_name_kr` | 사실의 한국어 표시명 | 사람이 읽는 이름 |
| `value_text` | 텍스트 형태의 사실값 | 문자열 값에 사용. 공통 정의 참고 |
| `value_number` | 숫자 형태의 사실값 | 계산·비교 가능한 값. 공통 정의 참고 |
| `unit` | 값의 단위 | `date`, `person`, `KRW`, `KRW/year`, `year`, `month`, `grade`, `level` |
| `source_document_id`~`source_text` | 해당 사실의 문서·위치·원문 | 공통 정의 참고 |
| `extraction_status`, `confidence` | 추출 상태와 신뢰도 | 현재 `auto_extracted` |

### `visa_current_facts.csv`

각 `fact_key`에 대해 최신 차수에서 확인된 값을 선택한 현재값 테이블이다.

| 컬럼 | 의미 | 값·표기 규칙 |
| --- | --- | --- |
| `current_fact_id` | 현재 사실 행의 UUID | 현재값 단위 식별자 |
| `visa_code` | 대상 비자 | 공통 정의 참고 |
| `fact_domain` | 사실 영역 | `application`, `regional_quota`, `requirement`, `attachment_form`, `attachment_content` |
| `fact_key` | 차수 간 동일 사실을 식별하는 키 | `visa_round_facts.fact_key`와 같은 의미 |
| `fact_name_kr` | 사실의 한국어 표시명 | 원천 사실의 표시명 |
| `value_text`, `value_number`, `unit` | 선택된 현재 사실값 | 공통 정의 참고 |
| `source_round` | 현재값을 제공한 원문 차수 | 값이 발견된 가장 최신 차수 |
| `source_document_id` | 현재값의 근거 문서 | 공통 정의 참고 |
| `fill_strategy` | 현재값 선택 방법 | 현재 `latest`=최신 차수에서 직접 선택 |
| `backfilled_from_round` | 최신 차수에 값이 없어 이전 차수에서 보완한 경우의 원본 차수 | 보완하지 않았으면 빈 값 |
| `source_fact_id` | 선택된 원천 사실 행 | `visa_round_facts.fact_id` 참조 |

### `visa_fact_coverage.csv`

각 차수와 사실 영역에서 필요한 정보가 얼마나 추출됐는지를 기록하는 QA 테이블이다.

| 컬럼 | 의미 | 값·표기 규칙 |
| --- | --- | --- |
| `coverage_id` | 커버리지 행의 UUID | 차수·영역별 식별자 |
| `visa_code` | 대상 비자 | 공통 정의 참고 |
| `announcement_round` | 점검 대상 공고 차수 | 8~17 |
| `fact_domain` | 점검 영역 | `application`, `regional_quota`, `requirement`, `attachment_form`, `attachment_content`, `applicant_status`, `employer_capacity` |
| `coverage_status` | 추출 완전성 | `complete`=필요 사실이 모두 확인됨, `partial`=일부만 확인돼 추가 검수 필요 |
| `fact_count` | 해당 차수·영역에서 추출된 사실 행 수 | 0 이상의 정수 |
| `source_document_id` | 커버리지 판단에 사용한 대표 원문 | 공통 정의 참고 |
| `note` | 누락 범위·부분 추출 이유 등 QA 메모 | 추가 설명이 없으면 빈 값 |

### `visa_change_history.csv`

`visa_round_facts.csv`를 인접 차수끼리 비교해 만든 변경 이력이다. 15→17처럼 중간 차수를 건너뛴 비교는 만들지 않는다.

| 컬럼 | 의미 | 값·표기 규칙 |
| --- | --- | --- |
| `change_id` | 변경 행의 UUID | 하나의 사실 변경당 한 행 |
| `visa_code` | 대상 비자 | 공통 정의 참고 |
| `announcement_round` | 변경이 반영된 차수 | 일반적으로 `to_round`와 동일 |
| `requirement_type` | 변경 사실의 영역 | `requirement`, `regional_quota`, `attachment_form`, `attachment_content` |
| `change_summary` | 변경 내용을 사람이 읽는 한 문장으로 요약 | 이전값과 이후값을 포함할 수 있음 |
| `old_value` | 이전 차수 값 | `added`이면 빈 값 |
| `new_value` | 이후 차수 값 | `removed`이면 빈 값 |
| `effective_date` | 변경 적용일 또는 이후 차수 공고일 | `date_basis`와 함께 해석 |
| `from_round` | 비교 기준이 된 이전 차수 | `to_round - 1` |
| `to_round` | 변경을 확인한 이후 차수 | 인접 차수만 허용 |
| `fact_key` | 변경된 사실의 안정적인 기계 키 | `visa_round_facts.fact_key`와 연결 |
| `change_type` | 변경 유형 | `added`=추가, `modified`=값 변경, `removed`=삭제 |
| `change_scope` | 변경 범위 | `requirement`, `regional_quota`, `attachment_form`, `attachment_content` |
| `comparison_method` | 비교 방식 | `adjacent_round_only`=인접 차수만 비교 |
| `date_basis` | `effective_date`의 근거 | `to_round_publication_date` 또는 `explicit_pilot_start_date` |
| `source_document_id` | 변경 후 값을 확인한 원문 | 공통 정의 참고 |
| `source_section`, `source_block_index`, `source_table_index` | 변경 후 근거의 HWPX 위치 | 공통 정의 참고 |
| `source_locator_type` | 근거 위치의 종류 | `paragraph`=문단, `table`=표 |
| `source_text` | 변경 후 값의 근거 원문 | 공통 정의 참고 |
| `extracted_at`~`confidence` | 변경 추출 메타데이터 | 현재 `auto_extracted` |

**한 행 읽는 예시:** `from_round=8`, `to_round=9`, `fact_key=quota:단양군:recommended`, `old_value=20 person`, `new_value=22 person`, `change_type=modified`는 **8차에서 9차로 넘어가며 단양군 기추천 인원이 20명에서 22명으로 바뀌었다**는 뜻이다. `comparison_method=adjacent_round_only`이므로 8차와 10차를 직접 비교한 결과가 아니다.

### `visa_scoring_models.csv`

추천 신청자가 남은 쿼터보다 많을 때 사용하는 우선순위 점수표의 모델 정의다. 현재 9차 자료에서 보완한 잠정 모델이므로 소비가 차단되어 있다.

| 컬럼 | 의미 | 값·표기 규칙 |
| --- | --- | --- |
| `score_model_id` | 점수 모델 UUID | `visa_scoring_items.score_model_id`가 참조 |
| `visa_id`, `visa_code` | 모델이 속한 비자 | 공통 정의 참고 |
| `model_name_kr` | 점수표 표시명 | `추천서 발급 우선순위 점수표` |
| `maximum_points` | 모델 전체 최고점 | 현재 100점 |
| `minimum_required_points` | 최저 통과점수 | 빈 값이면 최저 합격선이 없고 순위 결정에만 사용 |
| `applies_when` | 점수표 적용 조건 | `applications_exceed_available_quota`=신청자가 가용 쿼터를 초과할 때 |
| `selection_rule` | 선발 순서 | `highest_total_score_first`=총점 높은 순 |
| `tie_breaker` | 동점자 우선순위 | `younger_applicant_first`=연소자 우선 |
| `source_round` | 배점표 원문 차수 | 현재 `9` |
| `source_document_id`, `source_section`, `source_table_index` | 배점표 원문과 HWPX 위치 | 공통 정의 참고 |
| `source_page` | 배점표 페이지 | 현재 6 |
| `source_page_basis` | 페이지 검수 방식 | 9차 HWPX 레이아웃 페이지이며 19번 표의 pageBreak·줄 배치로 확인 |
| `source_text` | 모델 전체 배점표 원문 | 표의 항목·구간·배점·판정기준을 보존 |
| `valid_from`, `valid_to` | 파일에 기록된 사업 접수기간 | 점수표의 17차 현행성을 입증하는 기간은 아님 |
| `date_basis` | 위 기간의 해석 근거 | 9차 공고에 반복된 사업 전체 접수기간이라는 주의문 포함 |
| `assumed_target_round` | 점수표를 적용한다고 가정한 최신 차수 | 현재 `17` |
| `related_source_document_ids_json` | 현행성 검수에 대조할 원문 목록 | 9차 공고와 17차 공고·붙임·개정사항 ID 배열 |
| `inheritance_scope` | 이전 차수에서 가져온 정보 범위 | 배점 항목·구간·점수·최대점수·동점기준만 보완 |
| `applicability_assumption` | 아직 확인되지 않은 적용 가정 | 9차 완전 배점표가 17차에도 유지된다는 가정 |
| `consumption_gate` | 서비스 소비 허용 여부 | `blocked_while_needs_review`=검수 전 소비 금지 |
| `review_completion_criteria` | 차단을 해제하기 위한 완료 조건 | 17차 공식자료·담당기관 확인, 적용기간·페이지 확정, 전체 행 검수 필요 |
| `fill_strategy` | 값 보완 방식 | `backfilled` |
| `review_status` | 업무 검수 상태 | `needs_review`=수동 검수 필요 |
| `notes` | 모델 해석 메모 | 최저점 부재, 우선순위용 점수라는 설명 등 |
| `extracted_at`, `extraction_status`, `confidence` | 추출 메타데이터 | 현재 자동 추출, 신뢰도 참고값 |

### `visa_scoring_items.csv`

점수 모델을 구성하는 12개 배점 구간이다. 모델과 동일하게 9차 보완 자료이며 검수 전 소비 금지다.

| 컬럼 | 의미 | 값·표기 규칙 |
| --- | --- | --- |
| `scoring_item_id` | 개별 배점 행의 UUID | 한 구간당 한 행 |
| `score_model_id` | 소속 점수 모델 | `visa_scoring_models.score_model_id` 참조 |
| `visa_id` | 배점이 속한 비자 | 공통 정의 참고 |
| `score_group` | 점수표의 상위 묶음 | 현재 `추천 우선순위` |
| `category` | 배점 영역 | `language`=한국어 능력, `education_income`=학력 또는 소득, `residence_duration`=충청북도 거주기간 |
| `criterion` | 해당 구간의 사람이 읽는 조건 | 원문의 구간 문구를 정규화 |
| `min_value` | 구간 하한값 | 하한이 없거나 숫자로 표현하기 어려우면 빈 값 |
| `max_value` | 구간 상한값 | 상한이 없거나 숫자로 표현하기 어려우면 빈 값 |
| `min_inclusive` | 하한 포함 여부 | `1`=포함, `0`=미포함, 하한이 없으면 빈 값 |
| `max_inclusive` | 상한 포함 여부 | `1`=포함, `0`=미포함, 상한이 없으면 빈 값. 현재 숫자 상한은 미포함 |
| `unit` | 구간값의 단위·복합 판정 유형 | `year`=거주 연수, `TOPIK grade / KIIP completion level`=TOPIK 급수 또는 사회통합프로그램 이수단계, `degree_or_income`=학위와 연소득을 함께 해석하는 복합조건 |
| `points` | 구간 충족 시 부여 점수 | 정수 |
| `maximum_points` | 해당 배점 영역의 최고점 | 언어·학력/소득 30점, 거주기간 40점 |
| `is_mandatory` | 필수 득점항목 여부 | `1`=필수, `0`=필수 아님. 현재 모두 0 |
| `minimum_required_points` | 항목별 최소 필요점수 | 별도 최저점이 없으면 빈 값 |
| `evidence_document` | 점수 확인에 사용하는 증빙 | TOPIK·KIIP, 학력·소득, 외국인등록사실증명 등 |
| `display_order` | 배점표 표시 순서 | 공통 정의 참고 |
| `source_round` | 배점 원문 차수 | 현재 `9` |
| `source_document_id`, `source_section`, `source_table_index` | 배점 원문과 표 위치 | 공통 정의 참고 |
| `source_page`, `source_page_basis` | 검수된 근거 페이지와 페이지 체계 | 현재 9차 HWPX 레이아웃 6쪽 |
| `raw_text` | 해당 배점 구간 원문 | 조건과 점수를 가공 전 형태로 보존 |
| `valid_from`, `valid_to`, `date_basis` | 기록된 기간과 해석상 주의 | 17차 현행성 입증기간이 아님 |
| `assumed_target_round` | 적용 가정 대상 차수 | 현재 `17` |
| `related_source_document_ids_json` | 현행성 대조 원문 목록 | 공통 정의 참고 |
| `inheritance_scope` | 9차에서 보완한 정보 범위 | 배점 관련 정보만 상속 |
| `applicability_assumption` | 미검증 적용 가정 | 9차 배점표가 17차에도 유지된다는 가정 |
| `consumption_gate` | 서비스 소비 허용 여부 | `blocked_while_needs_review` |
| `review_completion_criteria` | 소비 허용 전 완료해야 할 검수 | 모델과 12개 항목 전체를 함께 확인 |
| `fill_strategy` | 값 보완 방식 | `backfilled` |
| `review_status` | 업무 검수 상태 | `needs_review` |
| `notes` | 항목별 해석·불확실성 메모 | 학력 구간의 반복 소득기준 등 |
| `extracted_at`, `extraction_status`, `confidence` | 추출 메타데이터 | 현재 자동 추출, 신뢰도 0~1 |

**배점 행 읽는 예시:** `category=language`, `min_value=5`, `min_inclusive=1`, `points=30`인 행은 **TOPIK 5급 이상 또는 사회통합프로그램 5단계 이수 시 30점**이라는 뜻이다. 다만 이 배점은 `source_round=9`, `assumed_target_round=17`, `review_status=needs_review`, `consumption_gate=blocked_while_needs_review`이므로 17차 현행 점수로 사용하면 안 된다.

### `extraction_review_queue.csv`

자동 처리를 중단하고 사람 확인을 요구하는 검토 게이트다.

| 컬럼 | 의미 | 값·표기 규칙 |
| --- | --- | --- |
| `review_id` | 검토 항목 UUID | 하나의 검토 범위당 한 행 |
| `visa_code` | 대상 비자 | 공통 정의 참고 |
| `announcement_round` | 검토 기준 최신 차수 | 현재 `17` |
| `requirement_type` | 검토 대상 영역 | `applicant_status`=전체 신청 가능 체류자격, `employer_capacity`=고용가능인원 표, `excluded_applicants`=전체 제외대상, `scoring_model`=9차 배점표의 17차 현행성, `common_condition_group_mapping`=원천 중첩논리의 D 변환, `common_source_page_mapping`=HWPX 위치의 공식 페이지 변환 |
| `reason` | 검토가 필요한 이유 | 누락·불명확성·이전 차수 보완·매핑 위험 등을 서술 |
| `source_document_id` | 대표 원문 | 공통 정의 참고 |
| `related_source_document_ids_json` | 함께 대조할 문서 목록 | JSON 문자열 배열 |
| `blocking_scope` | 검토 전 사용을 막는 시스템 범위 | `eligibility_engine.*`=자격판정 기능, `scoring_engine`=점수 계산, `common_master_export.condition_group`=공통 논리그룹 이관, `common_master_export.source_page`=공통 출처페이지 이관 |
| `completion_criteria` | `resolved`로 바꾸기 위한 구체적 완료 조건 | 필요한 원문·담당기관 확인과 데이터 수정 범위를 명시 |
| `status` | 검토 진행 상태 | `open`=미해결·차단 유지, `resolved`=완료 |
| `created_at` | 검토 항목 생성 시각 | 공통 정의 참고 |

### `ingestion_issues.csv`

파싱 과정에서 발견한 중복·오탈자·문서 간 불일치를 기록한다. 경고가 있다고 해서 항상 원본 오류라는 뜻은 아니다.

| 컬럼 | 의미 | 값·표기 규칙 |
| --- | --- | --- |
| `issue_id` | 수집 이슈 UUID | 한 이슈당 한 행 |
| `issue_type` | 이슈 유형 | `duplicate_content`=파일 해시 동일, `equivalent_extracted_text`=추출 텍스트 동일, `source_typo`=원문 오탈자, `cross_document_conflict`=문서 간 기준 불일치 |
| `severity` | 검토 우선순위 | `info`=안내성, `warning`=확인 필요 |
| `document_id` | 이슈의 기준 문서 | 원천 `source_document_id` |
| `related_document_id` | 비교 대상 문서 | 단일 문서 이슈면 빈 값 |
| `message` | 이슈 내용과 처리 판단 | 동일본 보존, 정규화 근거, 현재값 선택 이유 등을 서술 |
| `created_at` | 이슈 생성 시각 | 공통 정의 참고 |

### `common_master_mapping.csv`

A 원천 기본정보 1행과 criteria 69행을 D 공통 마스터로 어떻게 처리할지 기록한 지원 파일이다. 원천 934행 집계에는 포함하지 않는다.

| 컬럼 | 의미 | 값·표기 규칙 |
| --- | --- | --- |
| `mapping_id` | 매핑 행의 결정론적 UUID | 같은 원천 행을 재생성해도 유지되는 지원 ID |
| `visa_id` | 매핑 대상 비자 | 공통 정의 참고 |
| `source_table` | 원천 CSV 이름 | `visa_requirements.csv` 또는 `visa_requirement_criteria.csv` |
| `source_row_id` | 원천 행 ID | 기본정보는 `visa_id`, criteria는 원천 `criteria_id` |
| `source_group_id` | criteria가 속한 원천 논리그룹 | 기본정보는 빈 값 |
| `source_group_path` | 최상위부터 현재 그룹까지의 경로 | 중첩 AND/OR를 사람이 검수하기 위한 문자열 |
| `target_table` | 권장 D 공통 테이블 | 이관하지 않는 행은 비어 있을 수 있음 |
| `target_row_id` | 준비된 공통 대상 행 UUID | `ready` 행만 값이 있으며 criteria는 원천 ID와 다른 UUID v4 |
| `mapping_action` | 변환 방법 | `direct`=구조상 직접 이관 가능, `transform`=필드값 변환 필요, `manual_review`=사람 판단 필요, `not_applicable`=공통 자격테이블 대상 아님 |
| `target_condition_group` | D에 사용할 OR 그룹 라벨 | 현재 언어요건 3행만 F-2-R 로컬 `G1` |
| `target_condition_operator` | 공통 그룹 연산자 | 현재 `OR` |
| `source_document_id` | 근거 원문 ID | 공통 정의 참고 |
| `source_document_name` | 변환 PDF 파일명 | 문서 ID와 페이지를 사람이 대조할 때 사용 |
| `source_page` | D 이관용으로 확인한 근거 페이지 | 공통 정의 참고 |
| `source_page_basis` | 페이지 체계 | 현재 `converted_pdf_page` |
| `page_mapping_method` | HWPX 위치를 페이지로 변환·검수한 방식 | `manual_verified_section_page`=기본정보의 section 위치를 사람이 페이지와 대조, `manual_verified_criteria_page_rule`=criteria의 블록·표 위치 규칙을 적용한 뒤 사람이 페이지를 확인 |
| `valid_from`, `valid_to` | 공통 이관 시 사용할 적용기간 | 원천 행 기간 또는 마스터 접수기간 |
| `validity_mapping_method` | 적용기간을 선택한 방식 | `source_application_period`=원천 기본정보의 접수기간 사용, `source_row_interval`=criteria 행 자체의 명시기간 사용, `inherited_master_application_period`=행에 기간이 없어 마스터 접수기간 상속 |
| `mapping_status` | 이관 준비 상태 | `ready`=형식상 이관 가능, `blocked`=손실 없는 표현 불가, `not_applicable`=해당 공통 테이블 대상 아님 |
| `blocking_reason` | 이관 차단 사유 코드 | `flat_schema_cannot_represent_nested_and_or`=D의 평면 그룹으로 중첩 AND/OR를 손실 없이 표현할 수 없음, `outside_initial_eligibility`=최초 신청자격이 아니라 승인 후 의무·절차·동반가족 정보임 |
| `recommended_destination` | 최종 권장 저장 위치 | 기본정보·criteria·절차·향후 안내 corpus 또는 팀 결정 후 criteria 등 |
| `mapping_note` | 매핑 판단을 설명하는 메모 | AND/OR, 변환값, 제외 이유 등을 서술 |

**매핑 행 읽는 예시:** `mapping_action=manual_review`, `mapping_status=blocked`, `blocking_reason=flat_schema_cannot_represent_nested_and_or`인 행은 **원천 데이터가 잘못됐다는 뜻이 아니라, 현재 D 공통 스키마로 옮기면 논리 의미가 달라질 수 있어 이관을 중단했다**는 뜻이다. `target_row_id`가 빈 것도 이 때문에 의도적으로 공통 행을 만들지 않았다는 표시다.

## 원천 논리그룹 해석

`visa_criterion_groups.csv`는 `parent_group_id`로 중첩 그룹을 구성한다. 각 그룹은 직접 연결된 criteria와 하위 그룹의 결과를 `boolean_operator`로 결합한다.

### 신청 대상 경로

```text
applicant_status (OR)
├─ e74_path (AND)
│  ├─ E-7-4 체류기간
│  └─ e74_status_options (OR)
│     ├─ 현 근무처 계속 근무
│     ├─ 계약 종료 또는 3개월 이내 종료 예정
│     └─ E-7-4 체류 후 D-10
└─ e74r_path (AND)
   ├─ E-7-4R 체류기간
   └─ 인구감소지역 거주
```

### 학력 또는 소득 경로

```text
education_or_income (OR)
├─ education_path (AND)
│  ├─ 국내 교육과정 2년 이상 체류·이수
│  └─ education_degree_status (OR)
│     ├─ 국내 전문학사 이상 학위 취득
│     └─ education_expected_path (AND)
│        ├─ 국내 전문대학 이상 졸업 예정
│        └─ 신청일부터 6개월 이내 학위 취득 예정
└─ income_path (AND)
   ├─ 연간 생활임금 이상
   ├─ 신청인 본인 소득
   ├─ 소득 산정기간
   └─ 인정 소득 종류
```

상위 OR 그룹에 세부 조건을 직접 평탄화하여 연결하지 않는다. 평탄화하면 경로별 필수조건이 누락된 것으로 해석될 수 있다.

## 공통 마스터 매핑 규칙

`extraction/D_visa_requirements/visa_requirement_criteria.csv`로 이관할 때 다음 규칙을 적용한다.

1. 원천 `group_id` UUID를 공통 `condition_group`에 복사하지 않는다.
2. 공통 `condition_group`은 실제로 서로 대체 가능한 OR 조건에만 `G1`, `G2`처럼 새로 부여한다.
3. `G1`, `G2`는 전역 ID가 아니라 비자별 로컬 라벨이다. 그룹 식별·조인에는 `(visa_id, condition_group)`을 사용한다.
4. AND 조건은 공통 테이블에서 기본적으로 그룹 없이 표현한다.
5. `A AND (B OR C)`는 A를 그룹 없이 두고 B와 C에만 같은 `condition_group`과 `condition_operator=OR`을 부여한다.
6. `(A AND B) OR (C AND D)`처럼 공통 스키마가 손실 없이 표현하지 못하는 중첩식은 임의로 평탄화하지 않는다. `special_case_note`에 원식을 남기고 `extraction_review_queue.csv`의 수동 매핑 대상으로 유지한다.
7. 하위 설명·예외·보충문은 논리그룹으로 만들지 않고 `value_text` 또는 `special_case_note`에 보존한다.

## 출처 위치 변환

- 원천 계층에서는 HWPX의 `source_section`, `source_block_index`, `source_table_index`, `source_text`를 근거 위치로 사용한다.
- 공통 마스터에는 `source_page`가 필요하므로, 이관 전에 블록·표 위치를 PDF 또는 팀이 합의한 공식 문서 페이지와 대조한다.
- 페이지를 확정하지 못한 행은 공통 마스터에 넣지 않고 `extraction_review_queue.csv`의 `common_source_page_mapping` 항목으로 관리한다.
- 공통 이관 전 `visa_id`, 새 `criteria_id`, `condition_group`, `condition_operator`, `source_page`, `valid_from`, `valid_to`를 함께 검수한다.

### 문서 범위 페이지 키

`source_page`는 전체 저장소에서 단독으로 식별자로 사용하지 않는다. 같은 페이지 번호가 공고문·붙임자료·개정자료에서 반복될 수 있으므로 근거 페이지는 반드시 다음 복합 키로 식별한다.

```text
(source_document_id, source_page)
```

- `source_document_id`는 `r09_announcement_2025~2026_a483f5df`처럼 공고 차수, 문서 유형, 기준 연도, SHA-256 앞 8자리를 포함한다.
- 공통 이관 시에도 문서명만 남기지 않고 원천 `source_document_id`, 문서 유형, 차수, 공고일·개정일 또는 해시를 추적할 수 있게 보존한다.
- HWPX 페이지, PDF 페이지처럼 페이지 번호 체계가 다를 수 있으므로 `source_page_basis`에 사용한 체계를 기록한다.
- 페이지를 확정하지 못한 행은 빈 페이지를 임의로 채우지 않고 `common_source_page_mapping` 검토 상태를 유지한다.
- 현재 9차 보완 점수표의 근거 키는 `(r09_announcement_2025~2026_a483f5df, 6)`이며, `source_page_basis`에 HWPX 레이아웃 페이지임을 기록했다.

## 점수표 상태

`visa_scoring_models.csv`와 `visa_scoring_items.csv`는 최신 17차 공고에 완전한 배점표가 없어 9차 자료에서 보완한 잠정 데이터다.

- `fill_strategy=backfilled`
- `review_status=needs_review`
- `source_round=9`, `assumed_target_round=17`
- `source_page=6`이며 문서 범위 키는 `(r09_announcement_2025~2026_a483f5df, 6)`
- `valid_from=2025-03-07`, `valid_to=2026-09-18`은 9차 공고문에 반복 기재된 **사업 전체 접수기간**이다. 이 기간 자체가 9차 점수표의 17차 현행성을 입증하지는 않는다.
- 상속 범위는 9차의 배점 항목·구간·배점·최대점수·동점기준으로 제한한다. 9차의 자격요건과 유효기간은 17차에 상속하지 않는다.
- 대조 원문 목록은 9차 공고문과 17차 공고문·붙임자료·개정사항이며 `related_source_document_ids_json`에 저장한다.
- `applicability_assumption`에는 “9차의 완전한 배점표가 17차에도 유지된다”는 미검증 가정을 명시한다.
- `consumption_gate=blocked_while_needs_review`인 행은 서비스와 scoring engine이 소비하면 안 된다.

점수 소비 조건은 다음 두 조건을 모두 만족하는 경우로 제한한다.

```text
review_status == "reviewed"
AND consumption_gate == "allowed"
```

수동 검수로 17차에도 같은 점수표가 유효하다고 확인되기 전에는 공통 마스터나 scoring engine에 반영하지 않는다. 검수 완료 시 17차 공고문·붙임자료·개정사항과 담당기관 확인으로 동일 배점표의 현행성 및 적용기간을 확정하고, 모델 1행과 항목 12행을 모두 `review_status=reviewed`, `consumption_gate=allowed`로 전환한다. 이 조건은 `extraction_review_queue.csv`의 `scoring_model` 행에도 기록한다.

## 작업·PR 경계

- 이 폴더의 PR: F-2-R 원문 추출, 정규화, 중첩 논리 보존, 검수 상태 관리
- #39 매핑 PR: 원천→공통 열·ID·논리·페이지·유효기간 변환 규칙과 매핑표만 A 폴더에 기록
- 공통 마스터 PR: 검수 완료된 원천 행만 `extraction/D_visa_requirements/` 스키마로 별도 매핑
- 여러 담당자가 D 공통 마스터를 동시에 수정하지 않도록 통합 PR은 순차적으로 진행한다.

## 검수 체크 및 PR 완료 기준

다음 자동 검사는 `uv run python scripts/validate_f2r_extraction.py`로 재현한다. 성공 시 JSON의 `result`가 `PASS`이고 종료코드가 0이어야 한다.

- [x] **논리그룹 무결성** — 예상 결과: 모든 `parent_group_id`가 같은 `visa_id`의 존재하는 그룹을 참조하고, 모든 OR 그룹에 실제 대체조건이 2개 이상 있으며, 상위 OR 그룹에 경로별 AND 조건이 직접 평탄화되지 않는다.
- [x] **14종 원천 CSV 파일·스키마 완전성** — 예상 결과: 원천 CSV 14종은 중복 헤더·열 수 불일치·필수 컬럼 누락 없이 총 934행이며, 별도 지원 파일 `common_master_mapping.csv` 70행이 존재한다.
- [x] **원천 위치 완전성** — 예상 결과: 원천 근거를 직접 저장하는 776행에 `source_document_id`, `source_section`, 블록 또는 표 위치, `source_text`/`raw_text`가 있고 변경 이력 93행은 모두 `source_block_index`를 가진다.
- [x] **검토 큐 완전성** — 예상 결과: 6개 검토 대상마다 `status`, 대조 원문 목록, `blocking_scope`, `completion_criteria`가 존재한다. #39로 `common_condition_group_mapping`과 `common_source_page_mapping` 2개는 `resolved`, 업무영역 검토 4개는 `open`이다.
- [x] **수집 오류 기록** — 예상 결과: `ingestion_issues.csv` 6행이 유효한 심각도와 유형을 사용하고, 잘못 수정된 `suspicious_filename` 오류는 남아 있지 않는다.
- [x] **공고문·안내자료 불일치 보존** — 예상 결과: 17차 붙임의 언어기준과 공고문·개정사항의 완화 기준 불일치가 `cross_document_conflict`로 남고 현재값 선택 근거가 메시지에 기록된다.
- [x] **인접 차수 변경 이력** — 예상 결과: 변경 이력 93행은 모두 `to_round-from_round=1`이며 15→16, 16→17 비교는 존재하고 15→17 직접 비교는 존재하지 않는다.
- [x] **잠정 점수표 소비 차단** — 예상 결과: 9차 모델 1행과 항목 12행은 `needs_review` 및 `blocked_while_needs_review`이고 소비 가능한 행은 0개다.
- [x] **공통 매핑표 무결성** — 예상 결과: 70개 원천 행이 중복 없이 매핑되고, 새 공통 criteria 후보 ID는 UUID v4이며 원천 ID와 다르고, 공통 OR 그룹은 언어요건 3행의 로컬 `G1`만 사용한다.
- [x] **공통 출처 페이지·유효기간 검수** — 예상 결과: 매핑 70행 모두 `(source_document_id, source_page)`, `converted_pdf_page` 체계, 유효기간과 변환 방식을 가지며 HWPX hash·PDF 페이지 범위 검증을 통과한다.

다음 항목은 사람 검수가 끝나야 체크할 수 있으며, 완료 전에는 해당 범위를 PR 완료 또는 서비스 사용 가능 상태로 표시하지 않는다.

- [ ] **9차 보완 점수표의 17차 현행성 검수** — 완료 결과: 담당기관 또는 공식 17차 자료로 적용 범위와 시작·종료일을 확정하고 모델·항목 전체를 `reviewed`/`allowed`로 변경한 뒤 `scoring_model` 검토를 `resolved`로 변경한다.
- [ ] **신청대상·고용규모·제외대상 검수** — 완료 결과: 관련 운영지침과 표·도형을 확인하여 `applicant_status`, `employer_capacity`, `excluded_applicants` 검토 항목을 모두 `resolved`로 변경한다.
