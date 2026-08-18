# requirements

E-7-4R의 자격요건 원천 데이터와 수동검수 결과를 보관한다.

## 파일

- `current_requirements.csv`: 검토가 끝난 현재 요건 데이터.
- `_draft_current_requirements.csv`: 원문에서 자동 분리한 초안. `not_checked`와 `unclassified` 행이 포함될 수 있다.
- `_review_current_requirements.csv`: 초안 행별 검수 판정 큐. 현재 135개 행이 수동검수 대상이다.

## 검수 규칙

`review_decision`은 `approved`, `reclassified`, `excluded`, `needs_review` 중 하나를 사용한다. `needs_review` 행은 공통 마스터에 이관하지 않는다. `unclassified`는 삭제하지 않고 자격요건, 절차, 쿼터, 서류, 공고 메타데이터 중 올바른 대상 테이블을 `target_table`에 기록한다.

`status`는 신청자의 상태가 아니라 원문 확인 상태다. `present`, `explicitly_none`, `not_mentioned`, `not_applicable`, `not_checked`, `extraction_failed`를 구분해 원천 파일에 보존한다.

## 공통 스키마 이관

검수 완료 후 자격요건 행만 공통 `visa_requirement_criteria`로 매핑한다. `condition_group`은 실제 대체 가능한 OR 조건에만 부여하고, 하위 조건이나 보충 설명은 별도 행의 원문·메모리로 보존한다. `record_id` 등 기존 로컬 식별자는 원천 추적용으로 보존하며 공통 마스터의 UUID를 임의로 대체하지 않는다.
