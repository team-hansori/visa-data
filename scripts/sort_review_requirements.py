"""review CSV를 부모 행 다음 자식 행 순서로 정렬한다."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path


def read_rows(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader), reader.fieldnames or []


def sort_parent_children(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    """기존 순서를 유지하면서 부모 직후에 연결된 자식 행을 배치한다."""
    children_by_parent: dict[str, list[dict[str, str]]] = {}
    record_ids = {row["record_id"] for row in rows}
    for row in rows:
        parent_id = row.get("parent_record_id", "")
        if parent_id:
            children_by_parent.setdefault(parent_id, []).append(row)

    output: list[dict[str, str]] = []
    emitted: set[str] = set()
    for row in rows:
        record_id = row["record_id"]
        if record_id in emitted:
            continue
        parent_id = row.get("parent_record_id", "")
        if parent_id and parent_id in record_ids and parent_id not in emitted:
            # 자식이 원본에서 부모보다 먼저 있어도 부모를 만날 때까지 보류한다.
            continue
        output.append(row)
        emitted.add(record_id)
        for child in children_by_parent.get(record_id, []):
            child_id = child["record_id"]
            if child_id not in emitted:
                output.append(child)
                emitted.add(child_id)
    return output


def write_rows(path: Path, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="review CSV의 부모·자식 행을 인접하게 정렬")
    parser.add_argument("review_csv", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    rows, fieldnames = read_rows(args.review_csv)
    sorted_rows = sort_parent_children(rows)
    output_path = args.output or args.review_csv
    write_rows(output_path, sorted_rows, fieldnames)
    print(f"정렬 완료: {output_path} ({len(sorted_rows)}행)")


if __name__ == "__main__":
    main()
