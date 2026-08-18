# Issue #37 공용 UUID 생성·중복 검증 유틸리티

## 요약

이슈 #29에서 확정한 UUID 규칙을 기존 extraction 파이프라인에 일관되게 적용한다. CSV 행 생성은 기존 추출 스크립트가 담당하고, 공용 UUID 유틸리티는 신규 행에 ID를 부여하고 중복을 검증하는 역할만 담당한다.

## 구현 계획

- `scripts/generate_uuids.py` 삭제
- `scripts/uuid_utils.py` 신규 추가
- 기존 추출 스크립트가 신규 행을 만든 뒤 공용 UUID 함수를 호출하도록 연결
- UUID 유틸리티는 CSV 행을 직접 생성하거나 append하지 않음
- 대상별 규칙:
  - `visa_id`: 같은 `visa_code`가 있으면 기존 UUID 재사용
  - 신규 비자 유형이면 UUID v4를 한 번 발급
  - `stage_id`: 신규 절차 단계마다 UUID v4 발급
  - `document_requirement_id`: 신규 제출서류 행마다 UUID v4 발급
- 기존 ID는 변경하지 않고 빈 ID에만 값을 부여
- 전체 D 테이블의 PK와 중복되는 UUID는 거부
- 필수 FK가 없거나 ID 규칙을 위반한 행은 오류 처리
- 행 생성·CSV 저장은 호출한 extraction 스크립트의 기존 책임으로 유지
- 생성 후 `scripts/validate_fk_integrity.py`로 FK 무결성을 확인

## 테스트 및 문서

- `tests/test_generate_uuids.py`를 `tests/test_uuid_utils.py`로 교체
- ID 유형별 신규 생성·기존 `visa_id` 재사용
- UUID v4 형식·전역 중복 검증
- 기존 ID 보존·빈 ID만 채우기·잘못된 입력 검증
- 기존 extraction 스크립트가 생성한 행에 UUID가 정상 부여되는지 검증
- UUID 유틸리티가 CSV 파일을 직접 변경하지 않는지 검증
- 실제 D CSV validator 통과
- `extraction/D_visa_requirements/README.md`에서 기존 CLI 사용법을 제거하고 공용 유틸리티 사용 규칙을 문서화

## 완료 기준

- [ ] `scripts/generate_uuids.py` 제거
- [ ] `scripts/uuid_utils.py` 공용 UUID 생성·검증 유틸리티 구현
- [ ] 기존 extraction 행 생성 흐름과 통합
- [ ] CSV 직접 append 로직 제거
- [ ] 회귀 테스트 추가
- [ ] 실제 D CSV validator 통과
- [ ] README 문서화
- [ ] PR 생성 및 #37 연결

## 결정된 가정

- 모든 UUID는 UUID v4를 사용한다.
- `visa_id`의 canonical key는 비자 코드·트랙이다.
- CSV 행 생성과 저장은 기존 extraction 스크립트가 담당한다.
- 기존 UUID를 일괄 재생성하거나 마이그레이션하지 않는다.
