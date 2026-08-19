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
| `history/change_history.csv` | 1~7차 대비 8차의 변경 사항만 기록 |

### 초안·수동검수 파일

| 파일 | 역할 |
|------|------|
| `requirements/_draft_current_requirements.csv` | 원문을 기호 기준으로 자동 분리한 1차 초안. `not_checked` 행과 `unclassified` 조각을 포함하며 공통 마스터에 직접 적재하지 않는다. |
| `requirements/_review_current_requirements.csv` | 초안 각 행의 수동 판정 기록. 원문을 대조한 뒤 대상 테이블과 처리 사유를 기록한다. |
| `documents/_draft_document_forms.csv` | 서식 자동 추출 초안. 제출서류 요구사항과 서식 메타데이터를 사람이 구분한다. |
| `documents/_draft_document_forms_checklist.txt` | 서식 검토 시 확인할 항목 |

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
uv run python scripts/classify_review_rows.py \
  extraction/B_E-7-4R/requirements/_review_current_requirements.csv
```

기존 `review_decision`과 `target_table`에 확신도 높은 제안만 반영하려면 다음처럼 실행한다. `status`, 출처, 메모, 검토자 정보는 유지하고, 애매한 행은 `needs_review/none`으로 남긴다.

```bash
uv run python scripts/classify_review_rows.py \
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
