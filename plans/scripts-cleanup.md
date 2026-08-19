# scripts 정리 계획

## 목표

`scripts/`에 흩어진 review CSV 처리 명령을 하나의 진입점에서 실행할 수 있게 만들고,
파일 형식별 추출기와 데이터 검증기는 독립적으로 유지한다.

## 정리 범위

### 통합 대상: review 처리

- `classify_review_rows.py`
- `normalize_review_requirements.py`
- `merge_reextracted_review.py`
- `add_reextracted_children.py`
- `sort_review_requirements.py`

공통 진입점은 `scripts/review_requirements.py`로 둔다.

```bash
uv run python scripts/review_requirements.py classify ...
uv run python scripts/review_requirements.py normalize ...
uv run python scripts/review_requirements.py merge ...
uv run python scripts/review_requirements.py add-children ...
uv run python scripts/review_requirements.py sort ...
```

1차에서는 기존 모듈의 함수를 통합 진입점에서 호출해 동작을 보존한다. 기존 직접 실행
스크립트는 README와 테스트가 새 진입점을 사용하도록 바꾼 뒤 제거하거나 호환 래퍼로
정리한다.

### 독립 유지

- `extract_hwp.py`, `extract_hwpx.py`, `extract_pdf.py`: 파일 형식별 추출기
- `draft_requirements.py`, `draft_document_forms.py`: 서로 다른 산출물 초안 생성기
- `locate_source_page.py`: 원문 위치 보강
- `diff_announcement_rounds.py`: 차수 비교
- `extract_values.py`: 값 후보 추출
- `filter_by_section.py`: 섹션 필터
- `validate_fk_integrity.py`: 무결성 검증

## 진행 순서

1. 기존 CLI·테스트·README 참조를 조사한다.
2. 통합 진입점과 각 하위 명령의 인자 전달을 구현한다.
3. 기존 기능과 통합 기능의 결과가 같은지 회귀 테스트한다.
4. README와 plan의 명령을 통합 진입점 기준으로 갱신한다.
5. 기존 중복 스크립트의 삭제 또는 호환 래퍼 전환을 별도 커밋 단위로 처리한다.
6. 전체 테스트와 lint를 실행한다.

## 원칙

- 통합 과정에서 CSV 데이터와 검수 필드는 변경하지 않는다.
- review 관련 명령은 기존처럼 명시적 출력 경로를 지원한다.
- `normalize`처럼 큰 모듈은 통합 CLI에 억지로 복사하지 않고 함수 모듈로 유지한다.
- 일회성 데이터 매핑은 코드에 영구 누적하지 않고 별도 설정·plan으로 추적한다.
