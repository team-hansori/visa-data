"""Validate and transactionally upsert common-schema-v2 CSVs into PostgreSQL."""

from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import sys
from collections.abc import Iterable
from pathlib import Path
from urllib.parse import urlsplit

from scripts.schema_v2 import ColumnKind, SCHEMA_V2, TABLE_ORDER, TableSpec

DEFAULT_DATA_DIR = Path("extraction/common_v2")


def read_rows(data_dir: Path, table: TableSpec) -> list[dict[str, str]]:
    with (data_dir / table.filename).open(newline="", encoding="utf-8-sig") as stream:
        return list(csv.DictReader(stream))


def convert_value(value: str, kind: ColumnKind):
    if value == "":
        return None
    if kind == ColumnKind.JSON_ARRAY:
        return json.dumps(json.loads(value), ensure_ascii=False)
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
    updates = ", ".join(
        f'"{column}" = EXCLUDED."{column}"' for column in columns if column != table.pk
    )
    return (
        f'INSERT INTO public."{table.name}" ({quoted}) VALUES ({placeholders}) '
        f'ON CONFLICT ("{table.pk}") DO UPDATE SET {updates}'
    )


def run_preflight(data_dir: Path, baseline: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    commands = [
        [
            sys.executable,
            str(root / "scripts/validate_common_schema_v2.py"),
            "--base-dir",
            str(data_dir),
            "--baseline",
            str(baseline),
        ],
        [
            sys.executable,
            str(root / "scripts/validate_source_record_mappings.py"),
            "--v2-dir",
            str(data_dir),
            "--source-root",
            str(root),
        ],
    ]
    for command in commands:
        subprocess.run(command, cwd=root, check=True)


def safe_target(database_url: str) -> str:
    parsed = urlsplit(database_url)
    return f"{parsed.hostname or '<unknown>'}:{parsed.port or 5432}/{parsed.path.lstrip('/')}"


def import_data(database_url: str, data_dir: Path) -> dict[str, int]:
    try:
        import psycopg
    except ImportError as exc:  # pragma: no cover - environment-specific guidance
        raise RuntimeError("psycopg is required: uv sync") from exc

    counts: dict[str, int] = {}
    with psycopg.connect(database_url) as connection:
        with connection.transaction():
            connection.execute("SET CONSTRAINTS ALL DEFERRED")
            with connection.cursor() as cursor:
                for name in TABLE_ORDER:
                    table = SCHEMA_V2[name]
                    rows = read_rows(data_dir, table)
                    if rows:
                        cursor.executemany(upsert_sql(table), prepared_rows(rows, table))
                    counts[name] = len(rows)
            verify_database(connection, data_dir)
    return counts


def verify_database(connection, data_dir: Path) -> None:
    """Verify imported UUID sets, FK integrity, mapping links, arithmetic, and smoke visas."""
    for name in TABLE_ORDER:
        table = SCHEMA_V2[name]
        expected = {row[table.pk] for row in read_rows(data_dir, table)}
        total = connection.execute(f'SELECT count(*) FROM public."{name}"').fetchone()[0]
        if total != len(expected):
            raise RuntimeError(f"{name}: CSV rows={len(expected)}, database rows={total}")
        actual = {
            str(row[0])
            for row in connection.execute(
                f'SELECT "{table.pk}" FROM public."{name}" WHERE "{table.pk}" = ANY(%s::uuid[])',
                (list(expected),),
            ).fetchall()
        }
        if actual != expected:
            raise RuntimeError(f"{name}: CSV UUID set and database UUID set differ")

    bad_quota = connection.execute(
        """SELECT count(*) FROM public.visa_quota_snapshots
        WHERE consumed_quota <> coalesce(recommended_count, 0) - coalesce(quota_exempt_count, 0)
           OR remaining_quota <> allocated_quota - consumed_quota"""
    ).fetchone()[0]
    if bad_quota:
        raise RuntimeError(f"quota arithmetic validation failed for {bad_quota} rows")

    broken_mappings = connection.execute(
        """SELECT count(*) FROM public.source_record_mappings m
        WHERE m.mapping_status = 'MAPPED' AND (
          m.target_record_id IS NULL OR NOT CASE m.target_table
            WHEN 'source_documents' THEN EXISTS (SELECT 1 FROM public.source_documents t WHERE t.source_document_id=m.target_record_id)
            WHEN 'visa_requirements' THEN EXISTS (SELECT 1 FROM public.visa_requirements t WHERE t.visa_id=m.target_record_id)
            WHEN 'visa_criterion_groups' THEN EXISTS (SELECT 1 FROM public.visa_criterion_groups t WHERE t.group_id=m.target_record_id)
            WHEN 'visa_requirement_criteria' THEN EXISTS (SELECT 1 FROM public.visa_requirement_criteria t WHERE t.criteria_id=m.target_record_id)
            WHEN 'visa_scoring_models' THEN EXISTS (SELECT 1 FROM public.visa_scoring_models t WHERE t.score_model_id=m.target_record_id)
            WHEN 'visa_scoring_items' THEN EXISTS (SELECT 1 FROM public.visa_scoring_items t WHERE t.scoring_item_id=m.target_record_id)
            WHEN 'visa_process_stages' THEN EXISTS (SELECT 1 FROM public.visa_process_stages t WHERE t.stage_id=m.target_record_id)
            WHEN 'document_requirements' THEN EXISTS (SELECT 1 FROM public.document_requirements t WHERE t.document_requirement_id=m.target_record_id)
            WHEN 'document_attachment_relations' THEN EXISTS (SELECT 1 FROM public.document_attachment_relations t WHERE t.relation_id=m.target_record_id)
            WHEN 'visa_quota_policies' THEN EXISTS (SELECT 1 FROM public.visa_quota_policies t WHERE t.quota_policy_id=m.target_record_id)
            WHEN 'visa_quota_snapshots' THEN EXISTS (SELECT 1 FROM public.visa_quota_snapshots t WHERE t.quota_snapshot_id=m.target_record_id)
            WHEN 'change_history' THEN EXISTS (SELECT 1 FROM public.change_history t WHERE t.change_id=m.target_record_id)
            ELSE false END)"""
    ).fetchone()[0]
    if broken_mappings:
        raise RuntimeError(f"target UUID validation failed for {broken_mappings} mappings")

    found = {
        row[0]
        for row in connection.execute(
            "SELECT visa_code FROM public.visa_requirements WHERE visa_code = ANY(%s)",
            (["F-4-R", "F-2-R", "E-7-4R", "D-2"],),
        ).fetchall()
    }
    missing = {"F-4-R", "F-2-R", "E-7-4R", "D-2"} - found
    if missing:
        raise RuntimeError(f"visa smoke test failed; missing: {', '.join(sorted(missing))}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument(
        "--baseline",
        type=Path,
        default=DEFAULT_DATA_DIR / "known_validation_gaps.txt",
    )
    parser.add_argument("--database-url", default=os.getenv("DATABASE_URL"))
    parser.add_argument("--apply", action="store_true", help="Commit the validated upsert")
    args = parser.parse_args()

    run_preflight(args.data_dir, args.baseline)
    counts = {name: len(read_rows(args.data_dir, SCHEMA_V2[name])) for name in TABLE_ORDER}
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
