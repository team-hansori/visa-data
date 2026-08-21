# history

공고 회차 간 변경 이력을 보관한다.

`change_history.csv`는 1~7차와 8차를 비교한 변경 사항을 기록한다. `added`, `removed`, `value_changed`, `scope_changed`, `procedure_changed`, `document_changed`, `editorial_change` 유형을 사용하며, 단순 문구 수정은 별도 변경 행으로 만들지 않는다.

`round_coverage.csv`는 1~8차 원본 공고 확보 상태와 인접 차수별 대조(`1→2`부터 `7→8`) 진행 상태를 기록한다. 비교가 끝나기 전까지 `comparison_status=pending`을 유지하며, 원본 미확보를 변경 없음으로 해석하지 않는다.

`round_comparison_audit.md`와 `manual_validation.csv`는 CHG-001~012의 원문 PDF 페이지·변경 유형 수동 검증 결과를 기록한다. 본문과 붙임 서식의 기준이 다른 경우에는 팀 결정 기준을 적용하고, 불일치 문구를 `notes`에 보존한다.

`schema_mapping.csv`가 로컬 `CHG-*`를 공통 `change_history`에 이관하기 위한 단일 의미 매핑표다. `target_record_id`는 UUID/FK 정책 확정 전까지 비워 두며, 변경 전·후 원문은 `history/change_history.csv`의 `old_value`·`new_value`를 기준으로 보존한다. 페이지·섹션·원문 참조는 `schema_mapping.csv`의 `source_page`·`source_section`·`notes`에 기록한다.

이력 행은 현재 요건의 대체물이 아니라 변경 근거다. 공통 스키마로 이관할 때는 원천 `change_id`를 전역 식별자로 간주하지 말고, 공통 UUID/FK 정책에 따라 새 식별자를 부여하면서 원천 ID와 출처를 함께 보존한다.
