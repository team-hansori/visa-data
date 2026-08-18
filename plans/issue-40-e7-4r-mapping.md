# Issue #40: E-7-4R 수동검수 및 공통 스키마 매핑 계획

## 목적

자동 생성된 E-7-4R draft 행을 원문과 수동 대조한 뒤, 각 행을 자격요건·절차·쿼터·서류·공고 메타데이터로 분류하고 공통 마스터에 반영한다.

## 작업 순서

1. `data/raw`의 E-7-4R 원본 공고·서식을 확보한다.
2. `_draft_current_requirements.csv` 135행을 원문과 대조한다.
3. `_review_current_requirements.csv`의 검토 필드를 채운다.
4. `unclassified` 행을 자동 삭제하지 않고 대상 테이블을 판정한다.
5. 검수 완료 행을 `current_requirements.csv` 또는 공통 마스터의 해당 테이블로 이관한다.
6. README와 매핑 기준을 갱신한다.
7. UUID/FK 검증과 원문 근거 검수를 수행한다.

## 검토 필드

`_review_current_requirements.csv`에는 다음 필드를 사용한다.

| 필드 | 허용값·의미 |
|---|---|
| `review_decision` | `approved`, `reclassified`, `excluded`, `needs_review` |
| `target_table` | `visa_requirement_criteria`, `visa_process_stages`, `visa_quota_status`, `document_requirements`, `visa_requirements`, `change_history`, `none` |
| `review_note` | 원문 대조 결과와 판정 사유 |
| `reviewer` | 검토자 |
| `reviewed_at` | 검토일 |

## 매핑 기준

- 자격요건은 새 `criteria_id` UUID를 발급하고 원천 `record_id`는 원천 계층에서만 유지한다.
- `condition_group`은 실제 OR 대체조건에만 사용한다. 같은 `❍` 아래 있다는 이유만으로 그룹을 복사하지 않는다.
- 추진 체계는 #30 기준으로 `visa_process_stages.csv`에 매핑한다.
- 모집 규모·지역별 쿼터는 `visa_quota_status.csv` 매핑 대상으로 검토한다.
- 제출서류와 서식 메타데이터를 구분하여 `document_requirements.csv` 대상만 선별한다.
- 변경 이력은 공통 이력용 UUID를 새로 발급한다.
- `scoring_items.csv`는 #31에 따라 E-7-4R 전용으로 유지한다.
- 공통 criteria에는 현재 `status`를 추가하지 않는다. 상태와 검수 이력은 B 원천·검토 파일에 보존하고, 공통 마스터 반영은 수동검수 승인 결과를 기준으로 한다.

## 완료 기준

- [ ] 원본 문서가 작업 환경에 연결됨
- [ ] draft 135행 전체에 수동검수 판정이 기록됨
- [ ] 모든 `unclassified` 행의 처리 결과가 기록됨
- [ ] 원본 문서·페이지·논리관계가 확인됨
- [ ] 공통 마스터 매핑 대상의 UUID/FK가 검증됨
- [ ] scoring 데이터를 criteria로 잘못 이관하지 않음
- [ ] `uv run python scripts/validate_fk_integrity.py` 통과
- [ ] 팀원에게 상태값·수동검수·보류 항목을 공유함
