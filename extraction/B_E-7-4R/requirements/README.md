# requirements

E-7-4R의 자격요건 원천 데이터와 수동검수 결과를 보관한다.

## 파일

- `current_requirements.csv`: 검토가 끝난 현재 요건 데이터.
- `_draft_current_requirements.csv`: 원문에서 자동 분리한 초안. `not_checked`와 `unclassified` 행이 포함될 수 있다.
- `_review_current_requirements.csv`: 초안 행별 검수 판정 큐. 복합 행을 분리한 하위 행도 함께 보관한다.

## 복합 행 분리

`scripts/normalize_review_requirements.py`는 표나 복합 문장처럼 한 행에 여러 의미가 붙은
경우, 분리 기준이 확정된 행만 하위 행으로 추가한다. 기본 실행은 분리 결과를 별도 파일로
생성하고, 검토 결과를 원본 review CSV에 반영할 때만 `--in-place`를 사용한다.

행 분리 후에는 검수 메모에서 경로가 확정된 `record_id`에 한해 `source_section`도
정규화한다. 규칙에 등록되지 않은 행은 자동 추론하지 않고 기존 값을 보존한다.
`raw_text`, `source_page`, `review_note`, `review_decision`, `target_table`은
`source_section` 정규화 과정에서 변경하지 않는다.

```bash
uv run python scripts/normalize_review_requirements.py \
  extraction/B_E-7-4R/requirements/_review_current_requirements.csv \
  --dry-run

uv run python scripts/normalize_review_requirements.py \
  extraction/B_E-7-4R/requirements/_review_current_requirements.csv \
  --in-place
```

`--dry-run`에서는 추가되는 하위 행과 변경되는 `source_section`의 기존·신규 경로를
출력한다.

## 추출 로직 수정 후 review 반영

HWPX 추출 로직을 수정한 뒤에는 원본을 다시 추출하고 draft를 재생성한다. 기존 review CSV를
새 draft로 덮어쓰지 말고, 검수 필드를 보존하는 병합 스크립트를 사용한다.

```bash
uv run python scripts/extract_hwpx.py <원본.hwpx> --output-dir <임시추출폴더>
uv run python scripts/draft_requirements.py <임시추출폴더>/<section0.txt> \
  extraction/B_E-7-4R/requirements/_draft_current_requirements.csv
uv run python scripts/merge_reextracted_review.py \
  extraction/B_E-7-4R/requirements/_review_current_requirements.csv \
  <새로생성한_draft.csv> \
  extraction/B_E-7-4R/requirements/_draft_current_requirements.csv
```

이 병합은 `review_decision`, `target_table`, `review_note`, `reviewer`, `reviewed_at`,
`status`를 덮어쓰지 않는다. 사람이 이미 `raw_text`를 수정한 행도 보존하고, 새로 추출된
행만 검수 필드를 빈 값으로 추가한다.

분리된 행은 `REQ-018-01`처럼 하위 ID를 가지며, `parent_record_id`로 원본 행을 추적한다.
하위 행은 실제 원문 위치에 맞는 개별 `source_page`를 갖고, 부모 행에 있던 페이지 범위를
그대로 복사하지 않는다. 부모 행의 원문은 삭제하지 않고 `excluded/none`으로 남겨 중복
이관을 방지한다. 구조가 애매하거나 `extraction_failed`인 행은 자동 분리하지 않고 수동
검토 대상으로 유지한다.
- `source_section`은 검수 메모로 확정된 ID별 규칙만 적용한다. 미확정 행은 수동 검토
  대상으로 남긴다.
- 원문 한 줄이 여러 행으로 잘린 것이 확정된 경우에는 예상 조각이 모두 일치할 때만
  대표 행으로 병합한다. 현재 `REQ-030~REQ-033`은 `REQ-030`에
  `* ①, ③, ④는 최근 10년 이내 사항만 해당`을 복원하고 나머지 조각 행은
  `excluded/none`으로 보존한다. 조각이 다르면 자동 병합하지 않는다.
- 행 분리 후 의미가 확정된 절차 행(`REQ-116~REQ-119`)은
  `reclassified/visa_process_stages`로 정규화한다. `REQ-120`, `REQ-124~REQ-126`,
  `REQ-128`처럼 추가 분리나 논의가 필요한 행은 `needs_review/none`으로 유지한다.

## 검수 규칙

`review_decision`은 `approved`, `reclassified`, `excluded`, `needs_review` 중 하나를 사용한다. `needs_review` 행은 공통 마스터에 이관하지 않는다. `unclassified`는 삭제하지 않고 자격요건, 절차, 쿼터, 서류, 공고 메타데이터 중 올바른 대상 테이블을 `target_table`에 기록한다.

`status`는 신청자의 상태가 아니라 원문 확인 상태다. `present`, `explicitly_none`, `not_mentioned`, `not_applicable`, `not_checked`, `extraction_failed`를 구분해 원천 파일에 보존한다.

## 공통 스키마 이관

검수 완료 후 자격요건 행만 공통 `visa_requirement_criteria`로 매핑한다. `condition_group`은 실제 대체 가능한 OR 조건에만 부여하고, 하위 조건이나 보충 설명은 별도 행의 원문·메모리로 보존한다. `record_id` 등 기존 로컬 식별자는 원천 추적용으로 보존하며 공통 마스터의 UUID를 임의로 대체하지 않는다.
