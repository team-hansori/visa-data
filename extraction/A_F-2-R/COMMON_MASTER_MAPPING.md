# F-2-R 원천 근거표 → 공통 마스터 매핑 명세 (#39)

이 문서는 `extraction/A_F-2-R/`의 비자별 원천 근거표를 `extraction/D_visa_requirements/`의 공통 스키마로 옮길 때 사용하는 변환 기준이다. #39에서는 매핑 규칙과 검수 결과만 A 폴더에 남기며, D 공통 마스터의 실제 CSV 행은 수정하지 않는다. 실제 이관은 검수 완료 후 별도 통합 PR에서 순차적으로 수행한다.

## 검토 결과

- 원천 CSV는 14종, 총 934행이다.
- 공통 마스터 매핑 대상은 `visa_requirements.csv` 1행과 `visa_requirement_criteria.csv` 69행, 총 70행이다.
- 원본 HWPX의 SHA-256을 파싱 manifest와 대조했고, 변환 PDF의 문서별 페이지 범위 안에서 근거 페이지를 확인했다.
- 70행 모두 `(source_document_id, source_page)` 복합 근거 키, 페이지 체계, 유효기간을 갖는다.
- 구조상 바로 변환 가능한 행은 마스터 1행과 criteria 14행이다.
- 중첩 논리를 공통 스키마가 손실 없이 표현하지 못하는 criteria 44행은 `blocked`다.
- 최초 신청 자격 계산 대상이 아닌 승인 이후 의무·동반가족·절차 관련 criteria 11행은 `not_applicable`이다.
- 이 결과는 `common_master_mapping.csv`에 기록한다. `mapping_status=ready`는 **열·논리·출처 형식상 변환 가능**하다는 뜻이며, 별도의 업무영역 검토가 끝났다는 뜻은 아니다. `extraction_review_queue.csv`의 열린 검토 범위는 계속 소비를 차단한다.

## 식별자 발급 규칙

| 식별자 | 원천 → 공통 규칙 |
| --- | --- |
| `visa_id` | F-2-R 트랙의 고정 UUID `78dca2d7-f771-553a-b788-46c9ff56d633`를 모든 차수에서 재사용한다. 지역·공고 차수별로 새로 발급하지 않는다. |
| `criteria_id` | 원천 `criteria_id`는 A 폴더 안에서만 사용한다. 공통 마스터에 실제 행을 만들 때 UUID v4를 새로 발급한다. 매핑표가 이미 있으면 재실행 시 기존 공통 후보 ID를 보존한다. |
| `condition_group` | 원천 `group_id` UUID를 복사하지 않는다. 같은 F-2-R 안의 실제 OR 대체조건에만 `G1`, `G2` 같은 로컬 라벨을 새로 부여한다. 조인 키는 `(visa_id, condition_group)`이다. |
| `stage_id` | 공통 절차를 확정할 때 `(visa_id, notice_round, stage_order, stage_name)`별 UUID v4를 새로 발급한다. 원천 `submission_stage` 문자열이나 공고 ID를 ID로 재사용하지 않는다. |
| `document_requirement_id` | 공통 `stage_id`가 확정된 뒤 문서별 UUID v4를 새로 발급한다. 원천 ID는 추적용으로만 남기고 공통 PK로 복사하지 않는다. |
| `quota_status_id` | 시점별 쿼터 스냅샷을 실제 적재할 때 UUID v4를 새로 발급한다. |
| `change_id` | 공통 마스터의 필드 단위 인접 차수 diff가 확정될 때 UUID v4를 새로 발급한다. 원천 change ID를 복사하지 않는다. |
| `mapping_id` | 동일 원천 행의 매핑 기록을 재현할 수 있도록 `(비자, 원천 테이블, 원천 행 ID)` 기반 UUID v5를 사용한다. 공통 마스터의 업무 PK가 아니다. |

## 14종 원천 파일의 목적지

| A 원천 파일 | 공통 목적지 또는 처리 | #39 상태와 이유 |
| --- | --- | --- |
| `visa_requirements.csv` | D `visa_requirements.csv` | 1행 변환 준비 완료. 고정 `visa_id` 재사용. |
| `visa_requirement_criteria.csv` | D `visa_requirement_criteria.csv` | 14행 직접 매핑, 중첩 논리 44행 차단, 비자 최초 자격 밖 11행 제외. |
| `visa_criterion_groups.csv` | 직접 적재하지 않음 | 원천 중첩 논리 해석과 `condition_group` 변환 근거로만 사용. |
| `visa_announcement_rounds.csv` | D `visa_process_stages.csv` 및 기본정보·쿼터의 근거 | 회차별 단계 설계와 `stage_id` 발급 후 별도 이관. 현재 17차 총정원은 기본정보의 `total_quota=311` 근거로 사용. |
| `visa_required_documents.csv` | D `document_requirements.csv` | `submission_stage`를 공통 `stage_id`로 매핑한 뒤 이관. 단계가 없으면 FK를 만들 수 없으므로 현재 직접 적재하지 않음. |
| `visa_regional_quotas.csv` | 향후 지역별 쿼터 로그 | D `visa_quota_status.csv`에는 지역 컬럼이 없어 6개 시군별 값을 그대로 넣으면 지역 정보가 소실된다. #24 또는 팀 스키마 결정 전 차단. |
| `visa_change_history.csv` | D `change_history.csv` | 인접 차수 비교 원칙은 일치하나 공통 `table_name`·`field_identifier`와 이전/이후 양쪽 페이지를 보강한 뒤 이관. |
| `visa_scoring_models.csv` | A 폴더 유지 | D에 공통 점수표 테이블이 없고 9차 보완 자료가 `needs_review`이므로 이관·소비 금지. |
| `visa_scoring_items.csv` | A 폴더 유지 | 위 점수 모델과 동일. `reviewed` 및 `allowed`가 되기 전 scoring engine 소비 금지. |
| `visa_round_facts.csv` | 직접 적재하지 않음 | 차수별 원천 사실과 변경 계산용 중간 계층. |
| `visa_current_facts.csv` | 직접 적재하지 않음 | 최신 우선 보완값 계산과 QA용 파생 계층. |
| `visa_fact_coverage.csv` | 직접 적재하지 않음 | 차수·영역별 수집 완전성 QA용. |
| `extraction_review_queue.csv` | 직접 적재하지 않음 | 공통 이관 및 서비스 소비의 검수 게이트. |
| `ingestion_issues.csv` | 직접 적재하지 않음 | 중복·오탈자·문서 간 불일치 등 수집 품질 로그. |

## 필드 변환 규칙

### 기본정보

| A 원천 | D 공통 | 변환 |
| --- | --- | --- |
| `visa_id` | `visa_id` | 그대로 재사용 |
| `visa_code` | `visa_code` | `F-2-R` |
| `visa_name_kr` | `visa_name_kr` | 원천 현재값 |
| `program_type` | `program_type` | `REGIONAL_SPECIALIZED` enum으로 정규화 |
| `target_regions_json` | `target_region` | JSON 배열을 `|` 구분 문자열로 변환 |
| `allowed_industries_json` | `allowed_industries` | JSON 배열을 `|` 구분 문자열로 변환 |
| 현재 17차 `total_quota` | `quota_type`, `total_quota` | `LIMITED`, `311` |
| `valid_from`, `valid_to` | 같은 이름 | 공고 게시기간이 아니라 원천에 확정된 신청 접수기간 사용 |

### 자격조건

| A 원천 | D 공통 | 변환 |
| --- | --- | --- |
| `criteria_name` | `criteria_name` | 원천 의미 보존 |
| `criteria_type` | `criteria_type` | 공통 자격 판정 행은 `binary` |
| `value_number` | `value_numeric` | 숫자로 비교 가능한 경우만 숫자 보존 |
| `comparison_operator` | `operator` | `>=`, `>`, `<=`, `<`, `==` 중 해당값 |
| `unit` | `unit` | 원천 단위 보존 |
| `value_text`, `source_text` | `value_text` | 판정 맥락은 정규화하고 원문은 근거 계층에 보존 |
| `special_case_note` | `special_case_note` | 예외·부분 범위·검토 필요사항 보존 |
| `group_id` 및 그룹 경로 | `condition_group` | 실제 OR로 확정된 경우만 새 로컬 G번호 부여 |
| `valid_from`, `valid_to` | 같은 이름 | 원천 행에 값이 있으면 사용하고, 없으면 F-2-R 마스터 신청기간 상속 |

## AND/OR 변환 결과

공통 criteria는 “그룹 없는 행끼리 AND”와 “같은 그룹 안의 OR”까지만 표현할 수 있다.

- `language`의 3개 대체조건만 F-2-R 로컬 `G1`, `condition_operator=OR`로 변환한다.
- `residence` 3행과 `conduct` 7행, `excluded_applicants`의 확인된 1행은 그룹 없이 두어 다른 조건과 AND로 결합한다.
- `applicant_status`, `education_or_income`, `economic_activity` 아래 44행은 `(A AND B) OR (C AND D)` 형태의 중첩식을 포함한다. 이를 평탄화하면 필수조건이 빠지므로 공통 행 ID를 발급하지 않고 `blocked`로 둔다.
- `recommendation`, `post_approval`, `dependent_family` 아래 11행은 최초 신청 자격 criteria가 아니므로 공통 criteria에 넣지 않는다. 절차 단계 또는 향후 `admin_guide_corpus`로 보낸다.
- `excluded_applicants`의 현재 1행은 구조상 직접 변환 가능하지만 전체 제외대상 목록의 완전성 검토가 열려 있으므로, 서비스가 이 1행만을 완전한 목록으로 해석해서는 안 된다.

## 출처 페이지와 유효기간

- 공통 근거 키는 페이지 번호 단독이 아니라 `(source_document_id, source_page)`다.
- `source_document_name`에는 변환 PDF 파일명을, `source_page_basis`에는 `converted_pdf_page`를 기록한다.
- 공고문과 붙임자료는 서로 다른 문서이므로 같은 페이지 번호라도 다른 근거다.
- 공고문 자격요건은 변환 PDF 3~8쪽, 붙임자료 근거는 2~4쪽·8쪽·16쪽에서 대조했다.
- `build_f2r_common_mapping.py`를 manifest와 PDF 루트 인자와 함께 실행하면 원본 HWPX SHA-256과 변환 PDF 페이지 범위를 다시 검증한다.
- criteria 자체의 유효기간이 있으면 그 기간을 우선 사용하고, 없으면 F-2-R 마스터의 신청기간 `2025-03-07`~`2026-09-18`을 상속한다. 상속 여부는 `validity_mapping_method`에 기록한다.

## 매핑 상태와 이관 게이트

| 상태 | 의미 | 이관 처리 |
| --- | --- | --- |
| `ready` | 공통 열·출처·유효기간·평면 논리로 표현 가능 | 별도 D 통합 PR의 후보. 열린 업무영역 검토도 함께 확인해야 함. |
| `blocked` | 공통 스키마로 손실 없이 표현 불가 | 공통 행 생성 금지. 스키마 또는 팀 결정 후 재매핑. |
| `not_applicable` | 최초 신청 자격 공통 criteria 대상이 아님 | 표의 `recommended_destination`으로 라우팅. |

#39로 해결된 검토는 `common_condition_group_mapping`과 `common_source_page_mapping`이다. 다음 네 범위는 계속 `open`이다.

- `applicant_status`: 법무부 운영지침과 전체 허용 체류자격 대조
- `employer_capacity`: HWPX 표·도형의 구간별 허용 비율 확인
- `excluded_applicants`: 전체 제외대상과 예외의 완전성 확인
- `scoring_model`: 9차 점수표가 17차에도 유효한지 확인

## 재생성 및 검증

```bash
uv run python scripts/build_f2r_common_mapping.py \
  --manifest "/원본/parsed/manifest.csv" \
  --pdf-root "/변환PDF/지역특화_우수인재_F-2-R_pdf"

uv run python scripts/validate_f2r_extraction.py
uv run python scripts/validate_fk_integrity.py
```

첫 번째 명령을 다시 실행해도 기존 `ready` criteria의 공통 후보 UUID는 유지된다. 두 검증 명령이 모두 통과하고, `git diff -- extraction/D_visa_requirements/`가 비어 있어야 #39의 작업 경계를 지킨 것이다.
