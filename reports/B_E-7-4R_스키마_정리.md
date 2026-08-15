# B_E-7-4R 근거표 스키마 정리 — 2026-08-15

## `current_requirements.csv` — 8차 공고 기준 자격요건

| 컬럼 | 설명 |
|---|---|
| `record_id` | 행 식별자 (`REQ-001` 형식) |
| `requirement_type` | 요건 분류 (`applicant_status`/`employment`/`conduct`/`residence`/`income`) |
| `criterion_name` | 요건 이름(사람이 읽는 라벨), 필요한 경우만 채움 |
| `raw_text` | 문서 원문 그대로 |
| `value_numeric` | 수치 기준값 |
| `value_text` | 수치로 안 떨어지는 값(구간 서술 등) |
| `unit` | 단위(년/개월/명/만원 등) |
| `operator` | 비교연산자(`>=`/`<=`/`>`/`<`/`=`) |
| `measurement_window_value` / `measurement_window_unit` | "최근 N년" 같은 평가 범위 |
| `condition_group` | 서로 관련된(대체 가능한) 조건 묶음 ID |
| `condition_operator` | 묶음 내 논리 결합(`OR`, AND는 그룹 없이 표현) — 사람이 직접 입력, 자동 판정 안 함 |
| `status` | `present`/`explicitly_none`/`not_mentioned`/`not_applicable`/`not_checked`/`extraction_failed` |
| `source_document` / `source_page` / `source_section` | 출처 근거 |
| `notes` | 불일치·확인 필요 사항 등 |

## `scoring_items.csv` — K-POINT 점수제 배점표

| 컬럼 | 설명 |
|---|---|
| `score_id` | 행 식별자 (`SCORE-XXX`) |
| `score_group` | `총점기준`/`기본항목`/`가점항목`/`감점항목` |
| `category` | `income`/`language`/`age`/`recommendation`/`employment`/`tenure`/`residence`/`credential`/`penalty`/`threshold` |
| `criterion` | 세부 기준 설명 |
| `min_value` / `max_value` | 구간 하한/상한 |
| `unit` | 단위 |
| `points` | 배점(감점은 음수) |
| `maximum_points` | 해당 항목/구간의 상한 |
| `is_mandatory` | 필수 여부 |
| `minimum_required_points` | 최소 득점 기준 |
| `evidence_document` | 증빙서류 |
| `source_document` / `source_page` | 출처 근거 |
| `raw_text` | 문서 원문 |
| `notes` | 불일치·확인 필요 사항 등 |

## `document_forms.csv` — 서식 메타데이터

| 컬럼 | 설명 |
|---|---|
| `form_id` | 서식 번호 (`서식1`, `서식1-2` 등) |
| `form_name` | 서식 실제 제목 (원문 라벨과 다르면 실제 제목 기준) |
| `raw_text` | 문서 원문 |
| `filled_by` | 작성자 |
| `submitted_by` | 제출자 |
| `submission_target` | 제출처 |
| `signer` | 서명자 |
| `required_attachments` | 필수 첨부물 |
| `is_mandatory` | 필수/조건부 여부 |
| `source_document` / `source_page` | 출처 근거 |
| `notes` | 원본 오타, 불일치 등 |

## `change_history.csv` — 1~7차 대비 8차 변경사항

| 컬럼 | 설명 |
|---|---|
| `change_id` | 행 식별자 (`CHG-XXX`) |
| `from_round` / `to_round` | 비교 차수 |
| `requirement_type` | 변경된 요건의 분류 |
| `criterion_name` | 변경된 요건 이름 |
| `old_value` / `new_value` | 변경 전/후 값 |
| `change_type` | `added`/`removed`/`value_changed`/`scope_changed`/`procedure_changed`/`document_changed`/`editorial_change`(행으로 안 만듦) |
| `old_source_page` / `new_source_page` | 변경 전/후 근거 페이지 |
| `description` | 변경 설명, 판단 근거 |
