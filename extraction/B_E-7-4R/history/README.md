# history

공고 회차 간 변경 이력을 보관한다.

`change_history.csv`는 1~7차와 8차를 비교한 변경 사항을 기록한다. `added`, `removed`, `value_changed`, `scope_changed`, `procedure_changed`, `document_changed`, `editorial_change` 유형을 사용하며, 단순 문구 수정은 별도 변경 행으로 만들지 않는다.

이력 행은 현재 요건의 대체물이 아니라 변경 근거다. 공통 스키마로 이관할 때는 원천 `change_id`를 전역 식별자로 간주하지 말고, 공통 UUID/FK 정책에 따라 새 식별자를 부여하면서 원천 ID와 출처를 함께 보존한다.
