"""공통 CSV 신규 행에 UUID를 발급하고 중복을 검사한다.

사용법:
    uv run python scripts/generate_uuids.py \\
        --table visa_process_stages \\
        --row-json '{"visa_id":"...", "stage_order":1}' \\
        --write

기본값은 미리보기이며, ``--write``를 지정해야 대상 CSV를 수정한다.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import uuid
from dataclasses import dataclass
from pathlib import Path
from tempfile import NamedTemporaryFile

D_DIR = Path("extraction/D_visa_requirements")


@dataclass(frozen=True)
class EntitySpec:
    filename: str
    id_column: str
    identity_column: str | None = None
    required_columns: tuple[str, ...] = ()


ENTITY_SPECS = {
    "visa_requirements": EntitySpec(
        "visa_requirements.csv",
        "visa_id",
        identity_column="visa_code",
        required_columns=("visa_code",),
    ),
    "visa_process_stages": EntitySpec(
        "visa_process_stages.csv",
        "stage_id",
        required_columns=("visa_id",),
    ),
    "document_requirements": EntitySpec(
        "document_requirements.csv",
        "document_requirement_id",
        required_columns=("stage_id",),
    ),
}


class UUIDGenerationError(ValueError):
    """입력 행을 안전하게 추가할 수 없을 때 발생하는 오류."""


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    """CSV 헤더와 행을 읽는다."""
    if not path.exists():
        raise UUIDGenerationError(f"CSV 파일이 없음: {path}")
    with path.open(encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        if reader.fieldnames is None:
            raise UUIDGenerationError(f"CSV 헤더가 없음: {path}")
        return list(reader.fieldnames), list(reader)


def validate_uuid4(value: str, label: str) -> None:
    """값이 UUID v4 문자열인지 확인한다."""
    try:
        parsed = uuid.UUID(value)
    except (ValueError, AttributeError) as exc:
        raise UUIDGenerationError(f"{label}가 UUID 형식이 아님: {value!r}") from exc
    if parsed.version != 4:
        raise UUIDGenerationError(f"{label}가 UUID v4가 아님: {value!r}")


def new_uuid(existing_ids: set[str]) -> str:
    """기존 ID와 겹치지 않는 UUID v4를 생성한다."""
    while True:
        candidate = str(uuid.uuid4())
        if candidate not in existing_ids:
            return candidate


def collect_existing_ids(base_dir: Path) -> set[str]:
    """공통 스키마 대상 테이블의 모든 기존 PK를 수집한다."""
    ids: set[str] = set()
    for spec in ENTITY_SPECS.values():
        path = base_dir / spec.filename
        if not path.exists():
            continue
        _, rows = read_csv(path)
        ids.update(row[spec.id_column] for row in rows if row.get(spec.id_column))
    return ids


def normalize_row(row: dict[str, object], fieldnames: list[str], path: Path) -> dict[str, str]:
    """JSON 행을 CSV 헤더에 맞는 문자열 행으로 변환한다."""
    unknown = set(row) - set(fieldnames)
    if unknown:
        names = ", ".join(sorted(unknown))
        raise UUIDGenerationError(f"{path}에 없는 컬럼: {names}")
    return {
        field: "" if row.get(field) is None else str(row.get(field, "")) for field in fieldnames
    }


def append_row(
    path: Path, fieldnames: list[str], rows: list[dict[str, str]], row: dict[str, str]
) -> None:
    """행을 원자적으로 CSV에 추가한다."""
    with NamedTemporaryFile(
        "w", encoding="utf-8", newline="", dir=path.parent, delete=False
    ) as temp:
        temp_path = Path(temp.name)
        writer = csv.DictWriter(temp, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
        writer.writerow(row)
    temp_path.replace(path)


def prepare_row(
    table: str,
    row_input: dict[str, object],
    base_dir: Path = D_DIR,
    csv_path: Path | None = None,
) -> tuple[Path, dict[str, str], bool]:
    """신규 행에 ID를 채운다.

    반환값은 ``(대상 경로, 완성 행, 실제 신규 행인지)``다. 기존 비자 코드를
    찾은 경우에는 기존 ``visa_id``를 넣고 신규 행이 아님을 반환한다.
    """
    try:
        spec = ENTITY_SPECS[table]
    except KeyError as exc:
        choices = ", ".join(ENTITY_SPECS)
        raise UUIDGenerationError(f"지원하지 않는 table: {table!r} ({choices})") from exc

    path = csv_path or base_dir / spec.filename
    fieldnames, rows = read_csv(path)
    missing = [
        column for column in (spec.id_column, *spec.required_columns) if column not in fieldnames
    ]
    if missing:
        raise UUIDGenerationError(f"{path}에 필수 컬럼이 없음: {', '.join(missing)}")

    row = normalize_row(row_input, fieldnames, path)
    for column in spec.required_columns:
        if not row[column]:
            raise UUIDGenerationError(f"신규 행의 필수 값이 비어 있음: {column}")

    existing_ids = collect_existing_ids(base_dir)
    if table == "visa_requirements":
        for existing in rows:
            if existing.get("visa_code") == row["visa_code"]:
                existing_id = existing[spec.id_column]
                if row[spec.id_column] and row[spec.id_column] != existing_id:
                    raise UUIDGenerationError(
                        f"{row['visa_code']}에 이미 발급된 visa_id와 입력값이 다름: "
                        f"{existing_id} != {row[spec.id_column]}"
                    )
                row[spec.id_column] = existing_id
                return path, row, False

    provided_id = row[spec.id_column]
    if provided_id:
        validate_uuid4(provided_id, spec.id_column)
        if provided_id in existing_ids:
            raise UUIDGenerationError(f"이미 사용 중인 {spec.id_column}: {provided_id}")

    row[spec.id_column] = provided_id or new_uuid(existing_ids)
    return path, row, True


def parse_row_json(value: str) -> dict[str, object]:
    """JSON object 입력을 파싱한다."""
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as exc:
        raise UUIDGenerationError(f"--row-json이 올바른 JSON이 아님: {exc.msg}") from exc
    if not isinstance(parsed, dict):
        raise UUIDGenerationError("--row-json은 JSON object여야 함")
    return parsed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="공통 CSV 신규 행에 UUID를 발급하고 중복 검사")
    parser.add_argument("--table", required=True, choices=sorted(ENTITY_SPECS))
    parser.add_argument("--row-json", required=True, help="추가할 신규 행 JSON object")
    parser.add_argument("--base-dir", type=Path, default=D_DIR, help="공통 CSV 폴더")
    parser.add_argument(
        "--csv", dest="csv_path", type=Path, help="대상 CSV 경로(테스트·별도 폴더용)"
    )
    parser.add_argument("--write", action="store_true", help="검증 후 대상 CSV에 실제로 추가")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        path, row, is_new = prepare_row(
            args.table,
            parse_row_json(args.row_json),
            base_dir=args.base_dir,
            csv_path=args.csv_path,
        )
        if is_new and args.write:
            fieldnames, rows = read_csv(path)
            append_row(path, fieldnames, rows, row)
            print(f"행 추가 완료: {path}")
        elif is_new:
            print("미리보기(변경 없음): 신규 행에 발급할 ID")
        else:
            print("기존 visa_id 재사용(변경 없음)")
        print(json.dumps(row, ensure_ascii=False))
        return 0
    except UUIDGenerationError as error:
        print(f"UUID 생성 실패: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
