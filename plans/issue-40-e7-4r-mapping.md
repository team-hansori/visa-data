# Issue #40: E-7-4R 수동검수 및 공통 스키마 매핑 계획

## 목적

자동 생성된 E-7-4R draft 행을 원문과 수동 대조한 뒤, 각 행을 자격요건·절차·쿼터·서류·공고 메타데이터로 분류하고 공통 마스터에 반영한다.

## 작업 순서

1. `data/raw`의 E-7-4R 원본 공고·서식을 확보한다.
2. `_draft_current_requirements.csv` 135행을 원문과 대조한다.
3. `_review_current_requirements.csv`의 검토 필드를 채운다.
4. `unclassified` 행을 자동 삭제하지 않고 대상 테이블을 판정한다.
5. 분류 결과를 기준으로 추출·파싱 로직의 누락과 오류를 식별한다.
6. 원문 기호·표 구조·행 경계를 보존하도록 파싱 로직을 수정한다.
7. 점수표·자격요건·절차·쿼터·제출서류가 한 행에 섞인 경우 행을 분리하고, 추출 실패 행은 원문을 다시 대조해 정제한다.
8. 수정된 파싱 로직으로 원천 extraction 결과를 재생성하고, 기존 review 결과와 대조한다.
9. 정제·재검수 완료 행을 `current_requirements.csv` 또는 공통 마스터의 해당 테이블로 이관한다.
10. 공통 마스터 이관 과정에서 UUID/FK와 `condition_group`/`condition_operator`를 보완한다.
11. README와 매핑 기준을 갱신한다.
12. UUID/FK 검증과 원문 근거 검수를 수행한다.

## 분류 후 파싱·정제 단계

`target_table` 분류는 최종 데이터 생성이 아니라 후속 파싱·정제 작업의 기준이다. 분류 결과를
공용 테이블에 바로 복사하지 않고, 다음 순서로 원천 extraction을 먼저 보완한다.

- `❍`, `※`, `①` 등 원문 기호와 각주 표식을 보존한다.
- 표의 셀 병합·줄바꿈으로 여러 항목이 붙은 행은 원문 기준으로 행과 열을 복원한다.
- 하나의 행에 자격요건과 점수 계산이 함께 있으면 각각 `visa_requirement_criteria`와
  `scoring_items` 대상 행으로 분리한다.
- 신청 절차와 쿼터 정보가 함께 있으면 절차 행과 쿼터 행으로 분리한다.
- 제출서류 목록은 서류 단위로 분리하고, 서식 메타데이터와 실제 증빙서류를 구분한다.
- 하나의 부모 행이 여러 페이지에 걸쳐 있으면 하위 행별 실제 원문 위치를 확인해 `source_page`를
  개별 값으로 기록한다. 페이지 범위를 하위 행 전체에 기계적으로 복사하지 않는다.
- 행 분리와 페이지 분리가 끝난 뒤, 검수 메모에서 경로가 확정된 `record_id`만 명시적
  매핑으로 `source_section`을 정규화한다. 섹션명을 `raw_text` 검색으로 추론하지 않으며,
  미확정 행은 기존 값을 유지하고 수동 검토 대상으로 남긴다.
- `source_section` 정규화는 `raw_text`, `source_page`, `review_note`, 검수 판정값을
  변경하지 않는다. 분리된 자식 행은 자식의 실제 의미에 맞는 섹션 경로를 별도로 가진다.
- 동일한 원문 한 줄이 줄바꿈·표 셀 처리 오류로 여러 행에 나뉜 경우에는 원문이 확정된
  사례만 정제 규칙으로 병합한다. `REQ-030~REQ-033`은 대표 행 `REQ-030`의
  `raw_text`를 `* ①, ③, ④는 최근 10년 이내 사항만 해당`으로 복원하고,
  `REQ-031~REQ-033`은 중복 조각으로 `excluded/none` 처리한다. 기존 행을 삭제하지
  않고 대표 행의 `review_note`에 병합 사실을 기록해 원천 추적성을 유지한다.
- 행 병합 규칙은 `record_id`와 예상 원문 조각을 함께 확인하고, 일부 조각만 존재하거나
  내용이 다르면 자동 병합하지 않는다. 재실행해도 문장이 중복되거나 조각 행이 다시
  생성되지 않도록 멱등성 테스트를 추가한다.
- `target_table`은 행의 의미가 확정된 경우에만 보정한다. 분리된 점수 보충 행은
  `scoring_items`, 고용 조건 행은 `visa_requirement_criteria`, 신청·접수 안내 행은
  `visa_process_stages`로 매핑한다. 서류 목록·복합 추진표·법무부 심사 안내처럼
  추가 분리나 논의가 필요한 행은 `needs_review/none`으로 유지한다.
- 점수표의 `Ⓐ`~`Ⓙ` 표식은 review CSV에 사후 삽입하지 않고, 원문 초안 추출 단계에서
  행 경계로 인식하고 `raw_text`에 그대로 보존한다. 페이지 검색 시에는 선행 표식만
  검색용으로 제거하며 원문 데이터는 변경하지 않는다.
- `status=extraction_failed` 행은 의미를 추측해 확정하지 않고 원문을 다시 대조한 뒤 복원·재추출한다.
- 파싱 로직 수정 후 재생성한 결과가 기존 원문·페이지·섹션 정보와 일치하는지 다시 확인한다.
- 원문 추출 로직을 수정한 뒤에는 HWPX를 재추출하고 draft를 재생성한다. 기존 review CSV에는
  `scripts/merge_reextracted_review.py`로 병합하며, `review_decision`, `target_table`,
  `review_note`, 검수자·검수일·status는 보존한다. 사람이 이미 `raw_text`를 수정한 행은
  자동 덮어쓰지 않고 수동 수정 보존 행으로 출력한다.

정제 단계가 끝나기 전에는 공용 마스터에 UUID를 발급하거나 FK를 연결하지 않는다. 행 경계와
대상 테이블이 확정된 뒤에만 최종 레코드를 생성한다.

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
- [ ] 분류 결과에 따라 파싱 로직의 누락·오류가 보완됨
- [ ] 추출 실패·혼합 행이 원문 기준으로 복원되거나 수동 보류 사유가 기록됨
- [ ] 분리된 하위 행의 `source_page`가 실제 원문 페이지와 일치함
- [ ] 검수 메모로 확정된 행의 `source_section`이 공통 경로로 정규화됨
- [ ] 미확정 `source_section` 행이 자동 변경되지 않고 보류됨
- [ ] 정제 후 extraction 결과를 재생성하고 review 결과와 대조함
- [ ] 공통 마스터 매핑 대상의 UUID/FK가 검증됨
- [ ] scoring 데이터를 criteria로 잘못 이관하지 않음
- [ ] `uv run python scripts/validate_fk_integrity.py` 통과
- [ ] 팀원에게 상태값·수동검수·보류 항목을 공유함
