"""재생성한 draft를 기존 review CSV에 안전하게 병합한다."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path


REVIEW_ONLY_FIELDS = {
    "status", "source_page", "review_decision", "target_table", "review_note",
    "reviewer", "reviewed_at", "parent_record_id",
}


def read_rows(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader), reader.fieldnames or []


def merge_rows(review_rows, draft_rows, baseline_rows, *, append_new=False):
    """draft를 review에 병합한다.

    draft 재생성으로 record_id 순서가 바뀐 경우를 대비해, 새 행은 기본적으로
    자동 추가하지 않는다. ``append_new=True``는 ID 대응을 사람이 확인한 뒤에만 사용한다.
    """
    baseline_by_id = {row["record_id"]: row for row in baseline_rows}
    draft_by_id = {row["record_id"]: row for row in draft_rows}
    output = [row.copy() for row in review_rows]
    review_ids = {row["record_id"] for row in review_rows}
    skipped = []

    for row in output:
        record_id = row["record_id"]
        draft = draft_by_id.get(record_id)
        baseline = baseline_by_id.get(record_id)
        if draft is None or baseline is None:
            continue
        if row.get("raw_text", "") != baseline.get("raw_text", ""):
            skipped.append(record_id)
            continue
        row["raw_text"] = draft.get("raw_text", "")

    fieldnames = list(review_rows[0].keys()) if review_rows else list(draft_rows[0].keys())
    if append_new:
        for draft in draft_rows:
            if draft["record_id"] in review_ids:
                continue
            new_row = {field: draft.get(field, "") for field in fieldnames}
            for field in REVIEW_ONLY_FIELDS:
                if field in new_row:
                    new_row[field] = ""
            output.append(new_row)
    return output, skipped


def write_rows(path: Path, rows, fieldnames) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="재추출 draft를 기존 review CSV에 안전하게 병합")
    parser.add_argument("review_csv", type=Path)
    parser.add_argument("draft_csv", type=Path)
    parser.add_argument("baseline_csv", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--append-new",
        action="store_true",
        help="새 draft 행을 추가한다. record_id 대응을 사람이 확인한 경우에만 사용",
    )
    args = parser.parse_args()
    review_rows, fieldnames = read_rows(args.review_csv)
    draft_rows, _ = read_rows(args.draft_csv)
    baseline_rows, _ = read_rows(args.baseline_csv)
    merged, skipped = merge_rows(
        review_rows, draft_rows, baseline_rows, append_new=args.append_new
    )
    output_path = args.output or args.review_csv
    write_rows(output_path, merged, fieldnames)
    print(f"병합 완료: {output_path} ({len(merged)}행)")
    if skipped:
        print("수동 수정 보존 행: " + ", ".join(skipped))


if __name__ == "__main__":
    main()
