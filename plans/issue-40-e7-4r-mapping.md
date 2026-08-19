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
| `target_table` | `visa_requirement_criteria`, `visa_process_stages`, `visa_quota_status`, `document_requirements`, `visa_requirements`, `change_history`, `scoring_items`, `none` |
| `review_note` | 원문 대조 결과와 판정 사유 |
| `reviewer` | 검토자 |
| `reviewed_at` | 검토일 |

## `target_table` 검토 기준

`target_table`은 원문 행을 최종적으로 어느 공통·전용 테이블에 저장할지 나타낸다. 제목이나
상위 섹션만 보고 결정하지 말고, 해당 행의 실제 의미와 판정 방식을 기준으로 분류한다.

### 판정 순서

1. 원문 행이 섹션 제목·표 제목·문의처·단순 안내인지 확인한다. 이에 해당하고 공통 마스터에
   저장할 구조화된 값이 없으면 `excluded/none`으로 둔다.
2. 한 행에 서로 다른 의미가 섞여 있는지 확인한다. 절차와 쿼터, 자격요건과 점수처럼 의미가
   섞여 있으면 임의로 한 테이블에 넣지 말고 행을 분리하거나 `needs_review/none`으로 둔다.
3. 남은 행의 의미와 판정 방식을 아래 표에 대조한다.
4. 원문만으로 확정할 수 없으면 `needs_review/none`으로 남기고 `review_note`에 확인할 내용을
   기록한다.

| 원문 행의 의미 | `review_decision` | `target_table` |
|---|---|---|
| 신청 자격·필수 조건(나이, 학력, 경력, 소득, 거주·체류 요건 등) | `approved` | `visa_requirement_criteria` |
| 가점·감점·점수 구간·총점·합격선 등 점수 계산 항목 | `reclassified` | `scoring_items` |
| 신청·추천·접수·심사·결과 통보 등 진행 단계 | `reclassified` | `visa_process_stages` |
| 모집 규모·지역별 배정·잔여 인원·쿼터 소진 상태 | `reclassified` | `visa_quota_status` |
| 신청자가 실제로 제출할 증빙서류 목록 | `reclassified` | `document_requirements` |
| 비자 제도 자체의 요약·현재 적용 정보 | `reclassified` | `visa_requirements` |
| 차수 간 요건·절차·쿼터의 추가·삭제·변경 내역 | `reclassified` | `change_history` |
| 제목·문의처·단순 안내·판정 불가 행 | `excluded` 또는 `needs_review` | `none` |

### 경계 사례

- `자격 요건` 섹션에 있어도 점수 합산이나 감점 기준이면 `visa_requirement_criteria`가
  아니라 `scoring_items`로 분류한다.
- 신청 방법에 제출서류가 함께 있으면 절차 설명은 `visa_process_stages`, 실제 서류 목록은
  `document_requirements`로 분리한다.
- 서식의 파일명·작성자·서명란 같은 메타데이터는 `document_requirements`로 자동 해석하지
  않는다. 실제 제출 증빙서류인지 불명확하면 `needs_review/none`으로 둔다.
- 쿼터 범위 내 추천처럼 절차와 쿼터가 한 행에 섞이면 행을 분리하거나 수동 검토로 보류한다.
- `approved`는 일반적으로 `visa_requirement_criteria`에, `reclassified`는 다른 대상 테이블에
  매핑한다. `excluded`와 `needs_review`는 공통 마스터로 이관하지 않고 `target_table=none`으로
  둔다.

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
