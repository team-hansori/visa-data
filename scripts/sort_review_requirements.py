"""review CSV를 부모 행 다음 자식 행 순서로 정렬한다."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path


def read_rows(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader), reader.fieldnames or []


def _emit_with_descendants(
    row: dict[str, str],
    children_by_parent: dict[str, list[dict[str, str]]],
    output: list[dict[str, str]],
    emitted: set[str],
) -> None:
    """행을 출력에 추가하고, 그 자식·손자 등 모든 하위 행을 재귀적으로 뒤이어 배치한다."""
    record_id = row["record_id"]
    if record_id in emitted:
        return
    output.append(row)
    emitted.add(record_id)
    for child in children_by_parent.get(record_id, []):
        _emit_with_descendants(child, children_by_parent, output, emitted)


def sort_parent_children(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    """기존 순서를 유지하면서 조상 행 직후에 모든 자손 행을 재귀적으로 배치한다."""
    children_by_parent: dict[str, list[dict[str, str]]] = {}
    record_ids = {row["record_id"] for row in rows}
    for row in rows:
        record_id = row["record_id"]
        parent_id = row.get("parent_record_id", "")
        # 자기 참조 행은 자식 목록에 넣지 않고 최상위 행으로 취급해 무한 재귀를 막는다.
        if parent_id and parent_id != record_id:
            children_by_parent.setdefault(parent_id, []).append(row)

    output: list[dict[str, str]] = []
    emitted: set[str] = set()
    for row in rows:
        record_id = row["record_id"]
        parent_id = row.get("parent_record_id", "")
        # 부모가 존재하고 아직 방출되지 않았다면, 이 행은 부모(또는 그 조상)를 통해
        # 재귀적으로 방출될 것이므로 여기서는 건너뛴다. 부모가 없거나(최상위) 부모가
        # rows에 존재하지 않거나(끊어진 참조) 자기 참조인 경우에는 최상위 행으로 방출한다.
        has_known_parent = bool(parent_id) and parent_id != record_id and parent_id in record_ids
        if has_known_parent:
            continue
        _emit_with_descendants(row, children_by_parent, output, emitted)

    if len(output) != len(rows):
        raise ValueError(
            f"정렬 후 행 수가 일치하지 않습니다 (입력 {len(rows)}행, 출력 {len(output)}행). "
            "데이터 유실 가능성이 있어 중단합니다."
        )
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
