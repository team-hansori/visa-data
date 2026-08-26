"""Validate and transactionally upsert reference/ (agency_contacts, risk_routing_table,
risk_keyword_messages) CSVs into PostgreSQL. extraction/common_v2/ 13개 표를 다루는
import_common_v2.py와 책임을 분리한다. 설계 근거는 docs/map-agency-schema.md 참고.

CSV에서 사라진 행을 자동 삭제하지 않는다 — 기관 폐쇄는 agency_contacts.is_active=false로
표현하는 설계와 일치시키기 위함이다. 그래서 사후 검증도 "DB 행 수 == CSV 행 수"가 아니라
"CSV의 모든 PK가 DB에 존재하는가"만 확인한다.
"""

from __future__ import annotations

import argparse
import csv
import os
import subprocess
import sys
from collections.abc import Iterable
from pathlib import Path

from scripts.import_common_v2 import safe_target
from scripts.reference_schema import REFERENCE_SCHEMA, TABLE_ORDER, ColumnKind, TableSpec

DEFAULT_DATA_DIR = Path("reference")


def read_rows(data_dir: Path, table: TableSpec) -> list[dict[str, str]]:
    with (data_dir / table.filename).open(newline="", encoding="utf-8-sig") as stream:
        return list(csv.DictReader(stream))


def convert_value(value: str, kind: ColumnKind):
    if value == "":
        return None
    if kind == ColumnKind.BOOLEAN:
        return value.lower() == "true"
    return value


def prepared_rows(rows: Iterable[dict[str, str]], table: TableSpec) -> list[tuple[object, ...]]:
    return [
        tuple(convert_value(row[column.name], column.kind) for column in table.columns)
        for row in rows
    ]


def upsert_sql(table: TableSpec) -> str:
    columns = table.header
    quoted = ", ".join(f'"{column}"' for column in columns)
    placeholders = ", ".join(["%s"] * len(columns))
    pk_quoted = ", ".join(f'"{column}"' for column in table.pk)
    updates = ", ".join(
        f'"{column}" = EXCLUDED."{column}"' for column in columns if column not in table.pk
    )
    return (
        f'INSERT INTO public."{table.name}" ({quoted}) VALUES ({placeholders}) '
        f"ON CONFLICT ({pk_quoted}) DO UPDATE SET {updates}"
    )


def run_preflight() -> None:
    root = Path(__file__).resolve().parents[1]
    subprocess.run(
        [sys.executable, str(root / "scripts/validate_fk_integrity.py")], cwd=root, check=True
    )


def import_data(database_url: str, data_dir: Path) -> dict[str, int]:
    try:
        import psycopg
    except ImportError as exc:  # pragma: no cover - environment-specific guidance
        raise RuntimeError("psycopg is required: uv sync") from exc

    counts: dict[str, int] = {}
    with psycopg.connect(database_url) as connection:
        with connection.transaction():
            with connection.cursor() as cursor:
                for name in TABLE_ORDER:
                    table = REFERENCE_SCHEMA[name]
                    rows = read_rows(data_dir, table)
                    if rows:
                        cursor.executemany(upsert_sql(table), prepared_rows(rows, table))
                    counts[name] = len(rows)
            verify_database(connection, data_dir)
    return counts


def verification_query(table: TableSpec, expected: set[tuple[str, ...]]) -> tuple[str, list[str]]:
    """CSV의 모든 PK가 DB에 존재하는지 확인하는 쿼리와 플랫튼된 파라미터 목록을 만든다.
    실제 DB 연결 없이 단위 테스트하기 위해 SQL 생성 로직을 분리했다."""
    pk_columns_sql = ", ".join(f'"{c}"' for c in table.pk)
    row_placeholders = "(" + ", ".join(["%s"] * len(table.pk)) + ")"
    placeholders = ", ".join([row_placeholders] * len(expected))
    flat_params = [value for pk_tuple in expected for value in pk_tuple]
    sql = f'SELECT count(*) FROM public."{table.name}" WHERE ({pk_columns_sql}) IN ({placeholders})'
    return sql, flat_params


def verify_database(connection, data_dir: Path) -> None:
    """CSV의 모든 PK가 DB에 존재하는지만 확인한다(삭제 정책이 없어 행 수 동일성은
    가정하지 않는다)."""
    for name in TABLE_ORDER:
        table = REFERENCE_SCHEMA[name]
        rows = read_rows(data_dir, table)
        if not rows:
            continue
        expected = {tuple(row[c] for c in table.pk) for row in rows}
        sql, flat_params = verification_query(table, expected)
        found = connection.execute(sql, flat_params).fetchone()[0]
        if found != len(expected):
            raise RuntimeError(f"{name}: CSV {len(expected)}건 중 {found}건만 DB에서 확인됨")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--database-url", default=os.getenv("DATABASE_URL"))
    parser.add_argument("--apply", action="store_true", help="Commit the validated upsert")
    args = parser.parse_args()

    run_preflight()
    counts = {name: len(read_rows(args.data_dir, REFERENCE_SCHEMA[name])) for name in TABLE_ORDER}
    print("Validated rows: " + ", ".join(f"{name}={count}" for name, count in counts.items()))
    if not args.apply:
        print("Dry run only; pass --apply with DATABASE_URL to write data.")
        return 0
    if not args.database_url:
        parser.error("--apply requires DATABASE_URL or --database-url")
    print(f"Applying to {safe_target(args.database_url)} (credentials hidden)")
    import_data(args.database_url, args.data_dir)
    print("Import and post-import validation completed in one transaction.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
