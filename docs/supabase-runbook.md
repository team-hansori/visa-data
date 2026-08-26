# Supabase 공통 스키마 v2 배포 runbook

## 준비와 안전 원칙

- 대상 프로젝트와 환경(개발/스테이징/운영)을 재확인한다.
- 운영 반영 전 Dashboard의 Database Backups에서 PITR 또는 최신 백업 상태를 확인한다.
- Access Token, DB 비밀번호, service-role key와 `DATABASE_URL`은 커밋하지 않는다.
- 운영 DB에서 `supabase db reset --linked`를 실행하지 않는다.
- 최초 배포는 스테이징에서 아래 전 과정을 통과한 동일 커밋으로 수행한다.

## 스키마 배포

```bash
supabase login
supabase link --project-ref <PROJECT_REF>
supabase db pull  # 원격에 기존 스키마가 있을 때만 baseline을 먼저 리뷰
supabase db push --dry-run
supabase db push
```

`db pull`이 migration을 만들면 현재 migration과 충돌 여부를 먼저 리뷰한다. dry-run 결과가
13개 테이블 이외의 기존 객체를 삭제하거나 변경하면 중단한다.

## 데이터 검증과 적재

dry-run은 DB에 연결하지 않고 두 CSV 검증기와 예상 행 수를 확인한다.

```bash
uv run python scripts/import_common_v2.py
```

대상을 다시 확인한 뒤 비밀번호를 셸 기록에 직접 넣지 않고 환경 변수로 주입한다.

```bash
read -s DATABASE_URL
export DATABASE_URL
uv run python scripts/import_common_v2.py --apply
unset DATABASE_URL
```

importer는 FK를 지연 검사하는 단일 트랜잭션에서 UUID PK 기준 upsert한 뒤 CSV/DB 행 수와
UUID, PostgreSQL FK, 그룹·첨부 순환참조, 쿼터 산술, 684개 원천 매핑 대상, F-4-R/F-2-R/
E-7-4R/D-2 대표 조회를 검사하고 모두 성공해야 commit한다.

같은 명령을 두 번 실행해도 행 수가 늘어나지 않는다. 이후 CSV 변경도 동일한 UUID를 유지한
상태로 같은 명령으로 재동기화한다. CSV에서 삭제된 행은 자동 삭제하지 않으므로 별도 migration과
리뷰로 처리한다.

## 실패와 복구

- importer 실패: 트랜잭션 전체가 자동 rollback된다. 오류를 수정하고 다시 실행한다.
- migration 실패: `supabase migration list`로 적용 여부를 확인한다. 일부 DDL이 적용됐거나
  운영 데이터가 훼손됐으면 임의 DROP/RESET 대신 백업의 PITR 복구 또는 Supabase 지원 절차를
  사용한다.
- 배포 후 회귀: 쓰기를 중지하고 배포 시각과 오류를 기록한 뒤 역방향 migration 또는 사전
  확인한 백업 복구를 선택한다. 복구도 먼저 스테이징에서 검증한다.

