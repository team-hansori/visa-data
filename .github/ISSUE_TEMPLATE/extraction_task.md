---
name: 🚀 추출 작업 — 비자유형 근거표 채우기
about: 공고문·심사표·서식을 특정 비자유형의 근거표(CSV)로 옮기는 작업
labels: [extraction, 작업전]
assignees: []
---

<!--
제목 형식:
🚀 [추출][비자유형] 무슨 문서/파일 채우기
🔥 [긴급]
⌛ [~월/일]

예시:
🚀 [추출][B_E-7-4R] 8차 공고 current_requirements.csv 채우기
🚀 [추출][A_F-2-R] 심사표 scoring_items.csv 채우기
-->

🎯 작업 대상
---

- **비자유형**: (예: B_E-7-4R)
- **원본 문서**: (공고문 / 심사표 / 서식, 문서명·차수)
- **원본 위치**: (`data/raw/...` 상대경로 또는 공유 저장소 링크. 아직 저장소에 없다면 실제 위치)
- **채울 파일**: (`extraction/<비자유형>/` 아래 `current_requirements.csv` / `scoring_items.csv` / `document_forms.csv` / `change_history.csv` 중)

📋 작업 범위
---
<!-- 이번 이슈에서 어디까지 채울지 (문서 전체 vs 특정 조항/페이지 구간) -->

✅ 완료 기준
---

- [ ] 대상 행의 `status`가 `present`/`explicitly_none`/`not_mentioned`/`not_applicable` 중 하나로 채워짐 (`not_checked`로 남은 행 없음)
- [ ] 한 문장에 섞인 복합 조건은 개별 행으로 분리됨
- [ ] `raw_text`에 문서 원문이 그대로 보존됨
- [ ] 모든 값에 출처 문서·페이지 근거가 남음
- [ ] 공고문·심사표 간 값이 다르면 하나를 임의로 고르지 않고 둘 다 기록한 뒤 `notes`에 불일치 표시함

📋 참고 자료
---

- 근거표 작성 규칙: `extraction/<비자유형>/README.md`
- 상태 코드·작성 원칙: `CLAUDE.md`

🙋‍♂️ 담당자
---

- **추출담당**:
