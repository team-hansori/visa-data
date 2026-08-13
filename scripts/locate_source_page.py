"""근거표 raw_text가 PDF의 몇 페이지에 있는지 찾아 source_page를 채운다.

PDF는 굵은 글씨(강조) 구간이 텍스트 레이어에서 아예 빠지는 문제가 있어(#5),
raw_text 전체가 아니라 첫 30자 남짓의 짧은 조각으로 페이지를 찾는다.
정확히 한 페이지에서만 일치하는 경우에만 채우고, 0개나 2개 이상 페이지에서
일치하면 값을 추측하지 않고 notes에 이유를 남긴다.

사용법: uv run python scripts/locate_source_page.py <PDF경로> <근거표CSV경로>
"""

from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path

import pdfplumber

LEADING_MARKER_PATTERN = re.compile(r"^[□❍※\-*①②③④⑤⑥⑦⑧⑨⑩\s]+")
WHITESPACE_PATTERN = re.compile(r"\s+")
SEARCH_FRAGMENT_LENGTH = 30
MIN_FRAGMENT_LENGTH = 8


def normalize(text: str) -> str:
    """공백(줄바꿈 포함)을 하나로 뭉쳐 PDF 텍스트와 비교 가능한 형태로 만든다."""
    return WHITESPACE_PATTERN.sub(" ", text).strip()


def build_search_fragment(raw_text: str) -> str:
    """raw_text 앞부분 기호(❍①- 등)를 떼고, 비교용 짧은 조각을 만든다."""
    without_marker = LEADING_MARKER_PATTERN.sub("", raw_text)
    normalized = normalize(without_marker)
    return normalized[:SEARCH_FRAGMENT_LENGTH]


def extract_page_texts(pdf_path: Path) -> list[str]:
    """PDF의 각 페이지 원문 텍스트를 순서대로 리스트로 반환한다."""
    with pdfplumber.open(pdf_path) as pdf:
        return [page.extract_text() or "" for page in pdf.pages]


def find_matching_pages(fragment: str, normalized_pages: list[str]) -> list[int]:
    """조각 문자열을 포함하는 페이지 번호(1부터 시작) 목록을 반환한다."""
    return [
        page_number
        for page_number, page_text in enumerate(normalized_pages, start=1)
        if fragment in page_text
    ]


def apply_source_page(rows: list[dict], normalized_pages: list[str]) -> tuple[int, int, int]:
    """행마다 source_page를 찾아 채운다. (채운 행 수, 못 찾은 행 수, 중복 매칭 행 수)를 반환한다."""
    filled = 0
    not_found = 0
    ambiguous = 0

    for row in rows:
        if row.get("source_page"):
            continue

        fragment = build_search_fragment(row["raw_text"])
        if len(fragment) < MIN_FRAGMENT_LENGTH:
            not_found += 1
            _append_note(row, "raw_text가 너무 짧아 페이지 검색 불가 - 직접 확인 필요")
            continue

        matches = find_matching_pages(fragment, normalized_pages)
        if len(matches) == 1:
            row["source_page"] = str(matches[0])
            filled += 1
        elif len(matches) == 0:
            not_found += 1
            _append_note(row, "PDF에서 일치하는 페이지를 못 찾음(굵은 글씨 누락 가능) - 직접 확인 필요")
        else:
            ambiguous += 1
            _append_note(row, f"{len(matches)}개 페이지에서 중복 발견 - 직접 확인 필요")

    return filled, not_found, ambiguous


def _append_note(row: dict, note: str) -> None:
    """이미 있는 notes를 덮어쓰지 않고 뒤에 이어붙인다(중복 방지)."""
    existing = row.get("notes", "")
    if note in existing:
        return
    row["notes"] = f"{existing} / {note}" if existing else note


def main() -> None:
    """CLI 진입점: PDF와 근거표 CSV를 받아 source_page를 채운 CSV를 같은 경로에 덮어쓴다."""
    parser = argparse.ArgumentParser(description="근거표 raw_text의 PDF 페이지 위치 찾기")
    parser.add_argument("pdf_path", type=Path, help="대조할 PDF 경로")
    parser.add_argument("csv_path", type=Path, help="source_page를 채울 근거표 CSV 경로")
    args = parser.parse_args()

    page_texts = extract_page_texts(args.pdf_path)
    normalized_pages = [normalize(text) for text in page_texts]
    print(f"PDF 총 {len(normalized_pages)}페이지 로드됨")

    with args.csv_path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)

    filled, not_found, ambiguous = apply_source_page(rows, normalized_pages)

    with args.csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"source_page 채움: {filled}행 / 못 찾음: {not_found}행 / 중복 매칭: {ambiguous}행")


if __name__ == "__main__":
    main()
