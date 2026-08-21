# B_E-7-4R — 지역특화 숙련기능인력 (E-7-4R)

8차 공고 기준 요건, K-POINT 점수표, 서식, 1~7차 변경 이력을 근거 페이지와 함께 정규화한다. `_draft_*` 파일은 자동 추출 중간 산출물이며, `requirements/current_requirements.csv`와 `documents/document_forms.csv`는 수동 검토를 거친 결과를 보관한다.

## 폴더 구조

| 폴더 | 역할 |
|------|------|
| `requirements/` | 비자 자격요건 원천 데이터와 수동검수 큐 |
| `documents/` | 공식 서식 메타데이터와 서식 검토 초안 |
| `scoring/` | K-POINT 점수 항목과 배점 |
| `history/` | 공고 회차 간 변경 이력 |

각 폴더의 파일별 규칙과 공통 스키마 이관 기준은 해당 폴더의 `README.md`에 기록한다.

## 파일

| 파일 | 내용 |
|------|------|
| `requirements/current_requirements.csv` | 8차 공고 기준 현재 적용 요건 (복합 조건은 행으로 분리) — 신청 자격을 AND/OR 불리언으로 가르는 조건만 |
| `scoring/scoring_items.csv` | K-POINT 점수 항목과 구간별 배점 — 자격을 충족한 사람 중 합격선(총점 임계치)을 가르는 합산 점수만. `current_requirements.csv`와의 경계 기준은 `D_visa_requirements/README.md`의 "`scoring_items.csv`와의 경계" 참고 |
| `documents/document_forms.csv` | 서식 메타데이터 (작성자/제출자/제출처/서명자 등, 자격요건 아님) |
| `history/change_history.csv` | 1~8차 인접 회차 비교로 확인한 변경 사항 기록 |
| `schema_mapping.csv` | 로컬 `REQ-*`/`CHG-*` 행과 공통 마스터 대상 테이블·기존 `SCORE-*`의 매핑 관계 |

### 초안·수동검수 파일

| 파일 | 역할 |
|------|------|
| `requirements/_draft_current_requirements.csv` | 원문을 기호 기준으로 자동 분리한 1차 초안. `not_checked` 행과 `unclassified` 조각을 포함하며 공통 마스터에 직접 적재하지 않는다. |
| `requirements/_review_current_requirements.csv` | 초안 각 행의 수동 판정 기록. 원문을 대조한 뒤 대상 테이블과 처리 사유를 기록한다. |
| `documents/_draft_document_forms.csv` | 서식 자동 추출 초안. 제출서류 요구사항과 서식 메타데이터를 사람이 구분한다. |
| `documents/_draft_document_forms_checklist.txt` | 서식 검토 시 확인할 항목 |

## 데이터 구조와 컬럼 설명

모든 CSV는 UTF-8 인코딩을 사용한다. `raw_text`처럼 줄바꿈을 포함할 수 있는 값은 CSV 인용부호 안에 보존하며, 행의 순서보다 ID와 출처 컬럼을 기준으로 연결한다.

### 자격요건: `requirements/current_requirements.csv`

| 컬럼 | 설명 |
|---|---|
| `record_id` | 원천 자격요건 ID (`REQ-*`) |
| `requirement_type` | 요건 유형: 자격, 거주, 고용, 행위, 절차 등 |
| `criterion_name` | 요건명 또는 판단 기준명 |
| `raw_text` | 원문 문장·표·각주 |
| `value_numeric` | 숫자로 구조화한 값 |
| `value_text` | 숫자로 바꾸기 어려운 값 또는 원문 값 |
| `unit` | 금액, 년, 명, 점 등 값의 단위 |
| `operator` | `>=`, `=`, `within` 등 비교·판정 연산자 |
| `measurement_window_value` / `measurement_window_unit` | 최근 10년, 2년 등 평가 기간 |
| `condition_group` / `condition_operator` | 실제 대체조건 그룹과 AND/OR 연산. 불확실하면 공란 |
| `status` | 원문 확인 상태 (`present`, `not_checked` 등) |
| `source_document` | 원본 문서 또는 추출 문서 식별자 |
| `source_page` | 원문 페이지 |
| `source_section` | 원문 장·절·표 섹션 |
| `notes` | 추출·검수 시 참고사항 |

### 수동검수: `requirements/_review_current_requirements.csv`

위 자격요건 컬럼을 기본으로 사용하며 다음 검수 컬럼을 추가한다.

| 컬럼 | 설명 |
|---|---|
| `review_decision` | `approved`, `reclassified`, `excluded`, `needs_review` |
| `target_table` | 최종 대상 공통 테이블 또는 `none` |
| `review_note` | 판정 근거와 추가 검수 메모 |
| `reviewer` / `reviewed_at` | 검수자와 검수일 |
| `parent_record_id` | 복합 행에서 파생된 부모 `REQ-*` |

### 점수표: `scoring/scoring_items.csv`

| 컬럼 | 설명 |
|---|---|
| `score_id` | 점수 항목 ID (`SCORE-*`) |
| `score_group` | 평균소득, 한국어능력, 나이 등 점수 그룹 |
| `category` / `criterion` | 점수 대분류와 세부 기준 |
| `min_value` / `max_value` | 점수 구간의 최소·최대값 |
| `unit` | 만원, 급, 점 등 구간 단위 |
| `points` / `maximum_points` | 해당 구간 배점과 항목 최대점수 |
| `is_mandatory` | 해당 점수 항목의 필수 여부 |
| `minimum_required_points` | 자격 판정에 필요한 최소점수 |
| `evidence_document` | 점수 증빙서류 |
| `source_document` / `source_page` | 원문 문서와 페이지 |
| `raw_text` | 점수표 원문 |
| `notes` | 병합 셀·예외·검수 메모 |

### 서식: `documents/document_forms.csv`

| 컬럼 | 설명 |
|---|---|
| `form_id` | 서식 ID |
| `form_name` | 서식명 |
| `raw_text` | 서식 관련 원문 |
| `filled_by` / `submitted_by` | 작성자와 제출자 |
| `submission_target` | 제출 기관·담당 부서 |
| `signer` | 서명 또는 직인 주체 |
| `required_attachments` | 서식에 필요한 첨부서류 |
| `is_mandatory` | 필수 서식 여부 |
| `source_document` / `source_page` | 원문 문서와 페이지 |
| `notes` | 서식 메타데이터 검수 메모 |

### 변경 이력: `history/change_history.csv`

| 컬럼 | 설명 |
|---|---|
| `change_id` | 로컬 변경 ID (`CHG-*`). 공통 UUID가 아님 |
| `from_round` / `to_round` | 변경 전·후 공고 차수 |
| `requirement_type` | 변경 대상 유형 |
| `criterion_name` | 변경 기준명 |
| `old_value` / `new_value` | 변경 전·후 원문 또는 구조화 값 |
| `change_type` | `added`, `removed`, `value_changed`, `scope_changed` 등 |
| `old_source_page` / `new_source_page` | 변경 전·후 원문 페이지 |
| `description` | 변경 요약과 해석 메모 |

`history/manual_validation.csv`는 `change_id`, 검증 상태, 전·후 페이지, 근거, 후속 조치를 기록한다. `history/round_coverage.csv`는 차수 원본 확보(`round_source`)와 인접 차수 비교(`comparison`)의 진행 상태를 기록한다.

### 공통 매핑: `schema_mapping.csv`

| 컬럼 | 설명 |
|---|---|
| `source_file` | 매핑 원천 CSV |
| `local_record_id` | 원천 `REQ-*` 또는 `CHG-*` |
| `parent_record_id` | 원천 부모 행 ID |
| `review_decision` / `source_status` | 원천 검수 결정과 확인 상태 |
| `target_table` | 공통 이관 대상 테이블 |
| `target_record_id` | 공통 대상 ID. UUID 확정 전에는 공란 가능 |
| `mapping_action` | `insert`, `reuse`, `exclude` |
| `mapping_status` | `verified` 또는 `pending_target_id` |
| `source_document` / `source_page` / `source_section` | 매핑 근거 문서·페이지·섹션 |
| `notes` | 원문 참조, 매핑 사유, 보류 사유 |

`schema_mapping.csv`는 원천 행과 공통 테이블을 연결하는 단일 매핑표다. 공통 UUID가 발급되기 전에는 `target_record_id`를 임의로 만들지 않고 `mapping_status=pending_target_id`로 둔다.

매핑 상태와 이관 규칙은 위 컬럼 설명을 기준으로 한다. 현재 `history/change_history.csv`의 `CHG-001~017`도 실제 `source_document`·`source_page`·`source_section`과 원문 참조를 포함해 공통 `change_history` 대상으로 매핑되어 있다.

현재 `_review_current_requirements.csv`의 `G1~G44`는 원문 섹션·추출 묶음이므로 공통 논리 그룹으로 사용하지 않는다. 실제 OR 대체조건이 여러 행으로 확정된 경우에만 새 `condition_group`과 `condition_operator=OR`를 부여하며, 그 전까지는 `condition_group`과 `condition_operator`를 비워 둔다.

UUID/FK는 최종 공통 마스터 레코드 생성과 참조 검증에 필요하지만, 원문 의미 분석·OR 관계 판정·`schema_mapping.csv` 작성은 UUID 발급 전에 수행할 수 있다. `pending_target_id`는 의미 매핑이 미완료라는 뜻이 아니라, 공통 ID 발급만 보류된 상태를 나타낸다.

`requirements/_draft_current_requirements.csv`의 `unclassified`는 원문이 무의미하다는 뜻이 아니다. 공고 제목·섹션·쿼터·사업지역처럼 자격요건 외 테이블로 이동해야 하는 조각이거나, 자동 분류기가 의미를 판정하지 못한 조각이다. 모든 행은 수동검수 파일에서 처리 결과를 남긴 뒤 최종 파일 또는 공통 마스터에 반영한다.

## 값이 없을 때 (`status` 컬럼)

| 코드 | 의미 |
|------|------|
| `present` | 값 확인됨 |
| `explicitly_none` | 문서가 명시적으로 해당 없음이라고 규정 |
| `not_mentioned` | 8차 공고를 끝까지 확인했으나 언급 없음 |
| `not_applicable` | E-7-4R에 적용되지 않는 항목 |
| `not_checked` | 아직 확인하지 않음 (문서 확인 전 기본값) |
| `extraction_failed` | 표/글자를 판독하지 못함 |

`not_mentioned`은 문서를 끝까지 확인한 뒤에만 쓴다. 확인 전에는 항상 `not_checked`.

`status`는 비자 신청자의 상태가 아니라 원문 확인·추출 상태다. 현재 확정본 `requirements/current_requirements.csv`는 확인된 행을 `present`로 기록하고, 자동 초안은 검토 전이므로 `not_checked`로 기록한다. `status`가 `present`라고 해서 모든 구조화 컬럼이 자동으로 완성되었다는 뜻은 아니며, 원문 페이지와 논리관계는 별도로 검수한다.

## 수동검수 절차

1. `requirements/_draft_current_requirements.csv`의 각 행을 원본 문서와 대조한다.
2. `requirements/_review_current_requirements.csv`에 다음 판정 필드를 작성한다.
   - `review_decision`: `approved`, `reclassified`, `excluded`, `needs_review` 중 하나
   - `target_table`: `visa_requirement_criteria`, `visa_process_stages`, `visa_quota_status`, `document_requirements`, `visa_requirements`, `change_history`, `scoring_items`, `none` 중 하나
   - `review_note`: 판정 근거와 원문 대조 결과
   - `reviewer`, `reviewed_at`: 검토자와 검토일
3. `unclassified` 조각은 자동 삭제하지 않고 자격요건·절차·쿼터·서류·공고 메타데이터 중 어디에 해당하는지 판정한다.
4. `needs_review` 행은 원문 근거가 확보될 때까지 공통 마스터에 반영하지 않는다.
5. 검수 완료 행만 `requirements/current_requirements.csv` 또는 공통 마스터의 해당 테이블로 이관한다.

공통 `visa_requirement_criteria.csv`에는 현재 `status` 컬럼이 없으므로, 상태 컬럼을 공통 스키마에 추가할지는 별도 팀 설계 이슈에서 결정한다. 그 전까지 상태와 검수 이력은 이 폴더의 원천·검토 파일에서 보존한다.

## 자동 1차 분류 제안

다음 명령으로 원본 review CSV를 덮어쓰지 않고 자동 분류 제안 파일을 생성한다.

```bash
uv run python scripts/review_requirements.py classify \
  extraction/B_E-7-4R/requirements/_review_current_requirements.csv
```

기존 `review_decision`과 `target_table`에 확신도 높은 제안만 반영하려면 다음처럼 실행한다. `status`, 출처, 메모, 검토자 정보는 유지하고, 애매한 행은 `needs_review/none`으로 남긴다.

```bash
uv run python scripts/review_requirements.py classify \
  extraction/B_E-7-4R/requirements/_review_current_requirements.csv \
  --in-place
```

출력 파일은 `_review_current_requirements_proposed.csv`이며 `auto_review_decision`, `auto_target_table`, `auto_confidence`, `auto_reason` 컬럼을 추가한다. 제안값은 키워드와 섹션 기반의 1차 결과이므로, 원본 review CSV의 `review_decision`·`target_table`에 바로 복사하지 않고 사람이 확인한다. 원문 복원이 필요한 행과 한 행에 여러 의미가 섞인 행은 자동으로 `needs_review`로 남긴다. `scoring_items`는 E-7-4R 전용 점수표 대상이며 공통 criteria와 구분한다.

## 변경 유형 (`history/change_history.csv`의 `change_type`)

`added` · `removed` · `value_changed` · `scope_changed` · `procedure_changed` · `document_changed` · `editorial_change`(단순 문구 수정은 새 행으로 만들지 않음)

## 작성 규칙

- `raw_text`에는 문서 원문을 그대로 남긴다.
- 한 문장에 여러 요건이 섞여 있으면 개별 행으로 분리한다. `condition_group`은 서로 관련된 조건들의 묶음만 나타낸다 — 논리적 결합 관계(AND/OR)는 자동으로 정하지 않고, 원문을 직접 읽고 `condition_operator`에 사람이 입력한다.
- "최근 N년간" 같은 평가 범위는 `measurement_window_value`/`measurement_window_unit`에 따로 기록한다.
- 확인되지 않은 값은 추측하지 않는다.
- 공고문과 심사표의 값이 다르면 하나를 임의로 고르지 않고 두 값을 각각 근거와 함께 남긴 뒤 `notes`에 불일치를 표시한다.
- 원본 PDF는 이 저장소에 올리지 않고 `data/raw/`의 상대 경로로 참조한다 (PDF 자체가 아직 이 저장소에 없다면 실제 위치를 `source_document`에 남긴다).

## 다음 단계

1. 8차 공고 PDF를 페이지 순서대로 읽으며 `requirements/current_requirements.csv`를 채운다.
2. K-POINT 표는 텍스트 추출 결과만 믿지 말고 페이지 이미지와 대조해 `scoring/scoring_items.csv`를 채운다 (셀 병합으로 점수가 다른 행에 붙는 경우 주의).
3. 고용기업 추천양식 등에서 기업 자격요건은 `requirements/current_requirements.csv`로, 서식 자체 메타데이터는 `documents/document_forms.csv`로 분리해 넣는다.
4. 8차 기준이 끝나면 7차부터 역순으로 비교해 `history/change_history.csv`를 채운다.
