"""
D_visa_requirements 공유 마스터 테이블 간 PK 유일성과 FK 참조 무결성을 검사한다.
CSV는 DB가 아니라 FK 제약이 걸려있지 않으므로, 여러 담당자가 나눠서 편집하다 참조가
어긋나는 문제를 이 스크립트가 대신 잡아낸다.

사용법: uv run python scripts/validate_fk_integrity.py
"""

from __future__ import annotations

import csv
import sys
from dataclasses import dataclass, field
from pathlib import Path

D_DIR = Path("extraction/D_visa_requirements")


@dataclass(frozen=True)
class TableSpec:
    """검사 대상 테이블 하나의 정의."""

    path: Path
    pk: str | None  # PK 컬럼명. 없으면 None(PK 유일성 검사를 건너뜀)
    fks: dict[str, Path] = field(default_factory=dict)  # {FK 컬럼명: 참조할 부모 테이블 경로}


def default_tables(base_dir: Path = D_DIR) -> list[TableSpec]:
    """D_visa_requirements 폴더의 기본 테이블·FK 구성. 새 공유 테이블이 생기면 여기에 추가한다."""
    visa_requirements = base_dir / "visa_requirements.csv"
    visa_process_stages = base_dir / "visa_process_stages.csv"
    return [
        TableSpec(visa_requirements, pk="visa_id"),
        TableSpec(
            base_dir / "visa_requirement_criteria.csv",
            pk="criteria_id",
            fks={"visa_id": visa_requirements},
        ),
        TableSpec(
            visa_process_stages,
            pk="stage_id",
            fks={"visa_id": visa_requirements},
        ),
        TableSpec(
            base_dir / "document_requirements.csv",
            pk="document_requirement_id",
            fks={"stage_id": visa_process_stages},
        ),
        TableSpec(
            base_dir / "visa_quota_status.csv",
            pk="quota_status_id",
            fks={"visa_id": visa_requirements},
        ),
        TableSpec(
            base_dir / "change_history.csv",
            pk="change_id",
            fks={"visa_id": visa_requirements},
        ),
    ]


def read_rows(path: Path) -> list[dict[str, str]]:
    """CSV를 읽어 행 딕셔너리 리스트로 반환한다. 파일이 없으면 빈 리스트."""
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def collect_pk_sets(tables: list[TableSpec]) -> dict[Path, set[str]]:
    """각 테이블의 PK 값 집합을 미리 모아둔다 (다른 테이블의 FK 검사에서 참조용으로 씀)."""
    pk_sets: dict[Path, set[str]] = {}
    for table in tables:
        if table.pk is None:
            continue
        rows = read_rows(table.path)
        pk_sets[table.path] = {row[table.pk] for row in rows if row.get(table.pk)}
    return pk_sets


def check_pk_uniqueness(table: TableSpec, rows: list[dict[str, str]]) -> list[str]:
    """PK가 비어있거나 같은 값이 두 번 이상 나오면 에러로 기록한다."""
    if table.pk is None:
        return []
    errors: list[str] = []
    seen: dict[str, int] = {}
    for i, row in enumerate(rows, start=2):  # 1행은 헤더이므로 데이터는 2행부터
        value = row.get(table.pk, "")
        if not value:
            errors.append(f"{table.path}:{i} - {table.pk}가 비어 있음")
            continue
        seen[value] = seen.get(value, 0) + 1
    for value, count in seen.items():
        if count > 1:
            errors.append(f"{table.path} - {table.pk}={value} 중복 {count}회")
    return errors


def check_fk_integrity(
    table: TableSpec, rows: list[dict[str, str]], pk_sets: dict[Path, set[str]]
) -> list[str]:
    """FK 컬럼 값이 참조 테이블의 PK 집합에 실제로 존재하는지 검사한다."""
    errors: list[str] = []
    for fk_column, parent_path in table.fks.items():
        parent_ids = pk_sets.get(parent_path, set())
        for i, row in enumerate(rows, start=2):
            value = row.get(fk_column, "")
            if not value:
                errors.append(f"{table.path}:{i} - {fk_column}가 비어 있음")
                continue
            if value not in parent_ids:
                errors.append(
                    f"{table.path}:{i} - {fk_column}={value}가 {parent_path}에 존재하지 않음"
                )
    return errors


def validate(tables: list[TableSpec]) -> list[str]:
    """모든 테이블에 대해 PK 유일성과 FK 참조 무결성을 검사하고 에러 목록을 반환한다."""
    pk_sets = collect_pk_sets(tables)
    errors: list[str] = []
    for table in tables:
        rows = read_rows(table.path)
        if not rows:
            continue
        errors.extend(check_pk_uniqueness(table, rows))
        errors.extend(check_fk_integrity(table, rows, pk_sets))
    return errors


def main() -> int:
    errors = validate(default_tables())

    if errors:
        print(f"FK/PK 검증 실패: {len(errors)}건")
        for error in errors:
            print(f"  - {error}")
        return 1

    print("FK/PK 검증 통과: 문제 없음")
    return 0


if __name__ == "__main__":
    sys.exit(main())
