---
name: 🔍 검수 요청 — 근거표
about: 채워진 근거표(CSV)의 검수를 요청
labels: [review, 작업전]
assignees: []
---

<!--
제목 형식:
🔍 [검수][비자유형] 무슨 파일 검수
🔥 [긴급]

예시:
🔍 [검수][B_E-7-4R] current_requirements.csv 8차 공고 검수
🔍 [검수][B_E-7-4R] change_history.csv 1~7차 대비 변경사항 검수
-->

🔗 관련 이슈 / PR
---
<!-- "- #번호" 형식으로 작성 -->

- 관련 이슈:
- 관련 PR:

🧩 검수 대상
---

- **비자유형**:
- **파일**:
- **원본 문서**:

📋 검수 체크리스트
---

- [ ] `raw_text`에 문서 원문이 그대로 보존되어 있는가
- [ ] 복합 조건이 개별 행으로 분리되어 있는가 (`condition_group`/`condition_operator` 사용 여부)
- [ ] 모든 값에 출처 문서·페이지 근거가 남아있는가
- [ ] `status` 값이 적절한가 (`not_mentioned`와 `not_checked`를 혼동하지 않았는가)
- [ ] 공고문·심사표 불일치가 임의로 하나만 선택되지 않고 둘 다 기록되었는가
- [ ] 측정 기간(`measurement_window_value`/`measurement_window_unit`)이 조건과 분리되어 기록되었는가
- [ ] `change_history.csv`의 `change_type`이 규칙(added/removed/value_changed/scope_changed/procedure_changed/document_changed/editorial_change)에 맞게 쓰였는가

📊 주요 확인 사항
---
<!-- 검수 중 발견한 특이사항, 판단이 필요한 항목 -->

🙋‍♂️ 담당자
---

- **검수담당**:
- **추출담당**:
