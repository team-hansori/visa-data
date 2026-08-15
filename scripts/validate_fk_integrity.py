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


def read_fieldnames(path: Path) -> list[str] | None:
    """CSV 헤더를 읽어 컬럼명 리스트를 반환한다. 파일이 없으면 None, 빈 파일이면 빈 리스트."""
    if not path.exists():
        return None
    with path.open(newline="", encoding="utf-8") as f:
        return next(csv.reader(f), [])


def check_required_columns(table: TableSpec, fieldnames: list[str]) -> list[str]:
    """PK/FK로 쓰는 컬럼이 실제 헤더에 있는지 검사한다.

    여기서 걸러내지 않으면 이후 row[column] 접근에서 KeyError가 나거나,
    row.get(column)이 조용히 빈 값으로 처리돼 "값이 비어 있음"이라는 오해를
    주는 대량의 행별 에러로 원인이 묻힌다 — 컬럼 자체가 없다는 걸 파일당
    하나의 명확한 에러로 먼저 보고한다.
    """
    required = ([table.pk] if table.pk else []) + list(table.fks.keys())
    return [
        f"{table.path} - 필수 컬럼 '{column}'이 헤더에 없음"
        for column in required
        if column not in fieldnames
    ]


def collect_pk_sets(tables: list[TableSpec]) -> dict[Path, set[str]]:
    """각 테이블의 PK 값 집합을 미리 모아둔다 (다른 테이블의 FK 검사에서 참조용으로 씀).

    호출 전에 check_required_columns로 PK 컬럼 존재가 확인된 테이블만 넘겨야 한다.
    """
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


STAGES_FILENAME = "visa_process_stages.csv"
DOCUMENT_REQUIREMENTS_FILENAME = "document_requirements.csv"
STAGE_STATUS_COLUMN = "document_requirements_status"


def check_document_requirements_status(
    stages_path: Path, document_requirements_path: Path
) -> list[str]:
    """visa_process_stages.document_requirements_status가 document_requirements의
    실제 행 존재 여부와 맞는지 검사한다: `present`는 해당 stage_id 행이 1개 이상,
    `explicitly_none`은 0개여야 한다 ("이 단계엔 서류가 없다"고 명시했는데 실제로
    행이 있으면 모순이므로).
    """
    stage_rows = read_rows(stages_path)
    if not stage_rows:
        return []
    document_rows = read_rows(document_requirements_path)
    stage_ids_with_documents = {
        row["stage_id"] for row in document_rows if row.get("stage_id")
    }

    errors: list[str] = []
    for i, row in enumerate(stage_rows, start=2):
        status = row.get(STAGE_STATUS_COLUMN, "")
        stage_id = row.get("stage_id", "")
        has_documents = stage_id in stage_ids_with_documents
        if status == "present" and not has_documents:
            errors.append(
                f"{stages_path}:{i} - {STAGE_STATUS_COLUMN}=present이지만 "
                f"{document_requirements_path}에 stage_id={stage_id}인 행이 없음"
            )
        elif status == "explicitly_none" and has_documents:
            errors.append(
                f"{stages_path}:{i} - {STAGE_STATUS_COLUMN}=explicitly_none이지만 "
                f"{document_requirements_path}에 stage_id={stage_id}인 행이 있음"
            )
    return errors


def validate(tables: list[TableSpec]) -> list[str]:
    """모든 테이블에 대해 필수 컬럼 존재, PK 유일성, FK 참조 무결성을 검사하고 에러 목록을 반환한다."""
    errors: list[str] = []

    # 헤더에 PK/FK로 쓰는 컬럼이 있는지 먼저 확인한다 — 없는 테이블은 이후 단계에서
    # KeyError로 죽거나 row.get()이 조용히 빈 값 처리하는 걸 막기 위해 여기서 걸러낸다.
    checkable_tables: list[TableSpec] = []
    for table in tables:
        fieldnames = read_fieldnames(table.path)
        if fieldnames is None:  # 파일 자체가 없음 - 기존 동작대로 조용히 건너뜀
            continue
        column_errors = check_required_columns(table, fieldnames)
        if column_errors:
            errors.extend(column_errors)
            continue
        checkable_tables.append(table)

    pk_sets = collect_pk_sets(checkable_tables)
    for table in checkable_tables:
        rows = read_rows(table.path)
        if not rows:
            continue
        errors.extend(check_pk_uniqueness(table, rows))
        errors.extend(check_fk_integrity(table, rows, pk_sets))

    stages_table = next(
        (t for t in checkable_tables if t.path.name == STAGES_FILENAME), None
    )
    documents_table = next(
        (t for t in checkable_tables if t.path.name == DOCUMENT_REQUIREMENTS_FILENAME), None
    )
    if stages_table is not None and documents_table is not None:
        errors.extend(
            check_document_requirements_status(stages_table.path, documents_table.path)
        )

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
