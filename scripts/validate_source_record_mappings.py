"""v2 source_record_mappings 원천·대상 연결을 검증한다.

공통 스키마 형식 검증기와 분리해, 원천 파일에 실제 source_record_id가 있는지와
MAPPED 행의 target_record_id가 실제 v2 PK를 가리키는지를 확인한다.
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

from scripts import schema_v2

DEFAULT_SOURCE_ROOT = Path(".")
DEFAULT_V2_DIR = Path("extraction/common_v2")


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as stream:
        return list(csv.DictReader(stream))


def _source_table_paths(source_root: Path, dataset: str, table: str) -> list[Path]:
    dataset_root = source_root / "extraction" / dataset
    if not dataset_root.exists():
        return []
    return sorted(dataset_root.rglob(f"{table}.csv"))


def _load_source_index(source_root: Path, dataset: str, table: str) -> tuple[set[str], list[Path]]:
    paths = _source_table_paths(source_root, dataset, table)
    values: set[str] = set()
    for path in paths:
        for row in _read_rows(path):
            values.update(value for value in row.values() if isinstance(value, str) and value)
    return values, paths


def _load_target_ids(v2_dir: Path) -> dict[str, set[str]]:
    ids: dict[str, set[str]] = {}
    for table_name in schema_v2.TABLE_ORDER:
        table = schema_v2.SCHEMA_V2[table_name]
        path = v2_dir / table.filename
        if not path.exists():
            ids[table_name] = set()
            continue
        ids[table_name] = {row[table.pk] for row in _read_rows(path) if row.get(table.pk)}
    return ids


def validate_mappings(
    source_root: Path = DEFAULT_SOURCE_ROOT,
    v2_dir: Path = DEFAULT_V2_DIR,
) -> list[str]:
    """source_record_mappings.csv의 원천·대상·상태 정합성을 반환한다."""
    mapping_path = v2_dir / "source_record_mappings.csv"
    if not mapping_path.exists():
        return [f"{mapping_path} - 파일이 없음"]

    mappings = _read_rows(mapping_path)
    target_ids = _load_target_ids(v2_dir)
    errors: list[str] = []
    source_cache: dict[tuple[str, str], tuple[set[str], list[Path]]] = {}

    for line, row in enumerate(mappings, start=2):
        dataset = row["source_dataset"]
        source_table = row["source_table"]
        key = (dataset, source_table)
        if key not in source_cache:
            source_cache[key] = _load_source_index(source_root, dataset, source_table)
        source_values, source_paths = source_cache[key]

        if not source_paths:
            errors.append(
                f"source_record_mappings.csv:{line} - 원천 테이블 파일이 없음: {dataset}/{source_table}.csv"
            )
        elif row["source_record_id"] not in source_values:
            errors.append(
                f"source_record_mappings.csv:{line} - 원천 source_record_id가 없음: "
                f"{dataset}/{source_table}/{row['source_record_id']}"
            )

        status = row["mapping_status"]
        action = row["mapping_action"]
        target_table = row["target_table"]
        target_id = row["target_record_id"]

        if status == "MAPPED":
            if target_table == "NONE" or not target_id:
                errors.append(f"source_record_mappings.csv:{line} - MAPPED 행에 target 연결이 없음")
            elif target_id not in target_ids.get(target_table, set()):
                errors.append(
                    f"source_record_mappings.csv:{line} - target_record_id가 대상 PK에 없음: "
                    f"{target_table}/{target_id}"
                )
        elif status in {"PENDING", "READY", "BLOCKED"} and target_id:
            errors.append(
                f"source_record_mappings.csv:{line} - {status} 행에 target_record_id가 채워짐"
            )

        if action == "SKIP" and target_table != "NONE":
            errors.append(
                f"source_record_mappings.csv:{line} - SKIP 행의 target_table은 NONE이어야 함"
            )
        if action != "SKIP" and target_table == "NONE" and status == "MAPPED":
            errors.append(
                f"source_record_mappings.csv:{line} - SKIP 아닌 MAPPED 행의 target_table이 NONE임"
            )

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="source_record_mappings 원천·대상 연결 검증")
    parser.add_argument("--source-root", type=Path, default=DEFAULT_SOURCE_ROOT)
    parser.add_argument("--v2-dir", type=Path, default=DEFAULT_V2_DIR)
    args = parser.parse_args()
    errors = validate_mappings(args.source_root, args.v2_dir)
    if errors:
        print(f"source_record_mappings 검증 실패: {len(errors)}건")
        for error in errors:
            print(f"  - {error}")
        return 1
    print("source_record_mappings 검증 통과: 문제 없음")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
