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
