"""재추출로 분리된 점수표 조각을 기존 review CSV에 하위 행으로 추가한다."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path


# 기존 review의 복합 부모 ID와 새 draft의 record_id 대응.
REEXTRACTED_CHILD_MAP = {
    "REQ-034": ("REQ-034", "REQ-035", "REQ-036"),
    "REQ-035": ("REQ-037",),
    "REQ-036": ("REQ-038", "REQ-039"),
}


def read_rows(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader), reader.fieldnames or []


def add_children(
    review_rows: list[dict[str, str]], draft_rows: list[dict[str, str]]
) -> tuple[list[dict[str, str]], list[str]]:
    """명시된 대응표에 따라 draft 조각을 review 하위 행으로 추가한다."""
    draft_by_id = {row["record_id"]: row for row in draft_rows}
    output = [row.copy() for row in review_rows]
    existing_ids = {row["record_id"] for row in review_rows}
    added: list[str] = []

    for parent_id, source_ids in REEXTRACTED_CHILD_MAP.items():
        for index, source_id in enumerate(source_ids, start=1):
            child_id = f"{parent_id}-{index:02d}"
            if child_id in existing_ids:
                continue
            source = draft_by_id[source_id]
            child = {field: source.get(field, "") for field in review_rows[0]}
            child["record_id"] = child_id
            child["parent_record_id"] = parent_id
            child["status"] = "not_checked"
            child["source_page"] = "3"
            child["review_decision"] = "needs_review"
            child["target_table"] = "none"
            child["review_note"] = (
                f"재추출 결과 반영: 기존 {parent_id}에서 분리된 하위 행; "
                "원문·source_section·target_table 재검토 필요"
            )
            child["reviewer"] = ""
            child["reviewed_at"] = ""
            output.append(child)
            existing_ids.add(child_id)
            added.append(child_id)

    return output, added


def write_rows(path: Path, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="재추출 점수표 조각을 review 하위 행으로 추가")
    parser.add_argument("review_csv", type=Path)
    parser.add_argument("draft_csv", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    review_rows, fieldnames = read_rows(args.review_csv)
    draft_rows, _ = read_rows(args.draft_csv)
    merged, added = add_children(review_rows, draft_rows)
    output_path = args.output or args.review_csv
    write_rows(output_path, merged, fieldnames)
    print(f"추가 완료: {output_path} ({len(merged)}행)")
    print("추가된 하위 행: " + (", ".join(added) if added else "없음"))


if __name__ == "__main__":
    main()
