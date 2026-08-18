# Issue #37 공용 UUID 생성·중복 검증 스크립트

## 요약

이슈 #29에서 확정한 UUID 규칙을 자동화한다. `visa_id`는 비자 코드·트랙당 한 번만 발급해 재사용하고, `stage_id`와 `document_requirement_id`는 신규 행마다 발급한다. 기존 ID를 보호하면서 JSON으로 전달한 신규 행만 안전하게 CSV에 추가한다.

## 구현 계획

- `scripts/generate_uuids.py` 추가
- JSON 형태의 신규 행을 입력받아 대상 CSV에 추가
- 기본 동작은 미리보기이며 `--write`를 지정할 때만 CSV 수정
- 대상별 규칙:
  - `visa_id`: 같은 `visa_code`가 있으면 기존 UUID 재사용
  - 신규 비자 유형이면 UUID v4를 한 번 발급
  - `stage_id`: 신규 절차 단계마다 UUID v4 발급
  - `document_requirement_id`: 신규 제출서류 행마다 UUID v4 발급
- 기존 ID는 변경하지 않고, 전체 D 테이블의 PK와 중복되는 UUID는 거부
- 입력 오류나 중복 발생 시 CSV를 부분적으로 수정하지 않음
- 생성 후 `scripts/validate_fk_integrity.py`로 FK 무결성을 확인

## 테스트 및 문서

- ID 유형별 신규 생성·기존 `visa_id` 재사용
- UUID v4 형식·전역 중복 검증
- 기존 행 불변성·잘못된 입력·부분 쓰기 방지
- 실제 D CSV validator 통과
- `extraction/D_visa_requirements/README.md`에 사용법과 규칙 추가

## 완료 기준

- [ ] 공용 UUID 생성 스크립트 구현
- [ ] 회귀 테스트 추가
- [ ] 실제 D CSV validator 통과
- [ ] README 문서화
- [ ] PR 생성 및 #37 연결

## 결정된 가정

- 모든 UUID는 UUID v4를 사용한다.
- `visa_id`의 canonical key는 비자 코드·트랙이다.
- CSV 직접 수정은 `--write` 옵션을 사용할 때만 허용한다.
- 기존 UUID를 일괄 재생성하거나 마이그레이션하지 않는다.
