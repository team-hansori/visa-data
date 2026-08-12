# B_E-7-4R — 지역특화 숙련기능인력 (E-7-4R)

8차 공고 기준 요건, K-POINT 점수표, 서식, 1~7차 변경 이력을 근거 페이지와 함께 정규화한다. 아래 4개 파일은 아직 헤더만 있는 빈 템플릿이며, 실제 PDF 원문 내용은 채워지지 않았다.

## 파일

| 파일 | 내용 |
|------|------|
| `current_requirements.csv` | 8차 공고 기준 현재 적용 요건 (복합 조건은 행으로 분리) |
| `scoring_items.csv` | K-POINT 점수 항목과 구간별 배점 |
| `document_forms.csv` | 서식 메타데이터 (작성자/제출자/제출처/서명자 등, 자격요건 아님) |
| `change_history.csv` | 1~7차 대비 8차의 변경 사항만 기록 |

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

## 변경 유형 (`change_history.csv`의 `change_type`)

`added` · `removed` · `value_changed` · `scope_changed` · `procedure_changed` · `document_changed` · `editorial_change`(단순 문구 수정은 새 행으로 만들지 않음)

## 작성 규칙

- `raw_text`에는 문서 원문을 그대로 남긴다.
- 한 문장에 여러 요건이 섞여 있으면 개별 행으로 분리한다. `condition_group`은 서로 관련된 조건들의 묶음만 나타낸다 — 논리적 결합 관계(AND/OR)는 자동으로 정하지 않고, 원문을 직접 읽고 `condition_operator`에 사람이 입력한다.
- "최근 N년간" 같은 평가 범위는 `measurement_window_value`/`measurement_window_unit`에 따로 기록한다.
- 확인되지 않은 값은 추측하지 않는다.
- 공고문과 심사표의 값이 다르면 하나를 임의로 고르지 않고 두 값을 각각 근거와 함께 남긴 뒤 `notes`에 불일치를 표시한다.
- 원본 PDF는 이 저장소에 올리지 않고 `data/raw/`의 상대 경로로 참조한다 (PDF 자체가 아직 이 저장소에 없다면 실제 위치를 `source_document`에 남긴다).

## 다음 단계

1. 8차 공고 PDF를 페이지 순서대로 읽으며 `current_requirements.csv`를 채운다.
2. K-POINT 표는 텍스트 추출 결과만 믿지 말고 페이지 이미지와 대조해 `scoring_items.csv`를 채운다 (셀 병합으로 점수가 다른 행에 붙는 경우 주의).
3. 고용기업 추천양식 등에서 기업 자격요건은 `current_requirements.csv`로, 서식 자체 메타데이터는 `document_forms.csv`로 분리해 넣는다.
4. 8차 기준이 끝나면 7차부터 역순으로 비교해 `change_history.csv`를 채운다.
