"""근거표 초안에서 지정한 source_section들만 골라 별도 파일로 뽑는다.

사용법: uv run python scripts/filter_by_section.py <초안CSV경로> <섹션1,섹션2,...>
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path


def filter_rows_by_section(rows: list[dict], sections: set[str]) -> list[dict]:
    """source_section이 sections 목록에 있는 행만 골라 반환한다."""
    return [row for row in rows if row.get("source_section") in sections]


def resolve_output_path(csv_path: Path) -> Path:
    """입력 경로에서 '_draft_'를 '_review_'로 바꾼 출력 경로를 만든다.

    입력 파일명에 '_draft_'가 없으면 출력 경로가 입력 경로와 같아져 원본을
    덮어쓰게 되므로, 이 경우 예외를 발생시켜 중단한다.
    """
    output_path = csv_path.with_name(csv_path.name.replace("_draft_", "_review_"))
    if output_path == csv_path:
        raise ValueError(
            f"입력 파일명에 '_draft_'가 없어 출력 경로가 입력 경로와 같습니다: {csv_path} "
            "(원본을 덮어쓰지 않도록 중단함)"
        )
    return output_path


def main() -> None:
    """CLI 진입점: 초안 CSV와 섹션 목록을 받아 필터링한 결과를 별도 파일로 저장한다."""
    parser = argparse.ArgumentParser(description="근거표 초안에서 특정 섹션만 필터링")
    parser.add_argument("csv_path", type=Path, help="필터링할 초안 CSV 경로")
    parser.add_argument("sections", help="쉼표로 구분한 source_section 목록")
    args = parser.parse_args()

    try:
        output_path = resolve_output_path(args.csv_path)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    sections = {s.strip() for s in args.sections.split(",")}

    with args.csv_path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)

    filtered = filter_rows_by_section(rows, sections)

    with output_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(filtered)

    print(f"{len(filtered)}행 필터링됨 -> {output_path}")


if __name__ == "__main__":
    main()
