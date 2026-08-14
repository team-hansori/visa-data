"""두 차수 공고문(HWPX/HWP 우선, 필요하면 PDF)의 텍스트를 비교해 달라진 부분을 보여준다.

change_history.csv를 채울 때 문서 두 개를 처음부터 끝까지 눈으로 대조하는
대신, 텍스트 차이가 나는 부분만 빠르게 찾아내는 용도다. HWPX/HWP가 기준
문서(#7 결정)라 우선 쓰고, 둘 다 없을 때만 PDF로 대체한다 - PDF는 굵은
글씨가 텍스트 추출에서 빠지는 문제(#5)가 있어 그 구간 diff는 특히 더
사람이 원문(페이지 이미지)으로 재확인해야 한다.

HWPX와 HWP는 같은 내용이어도 줄바꿈을 서로 다르게 넣어서(#7 확인),
페이지/섹션의 원문을 그대로 줄 단위로 비교하면 실제 변경이 아닌 부분까지
전부 다르다고 나온다. 그래서 draft_requirements.py의 문서 기호(❍□-※①…)
기준 조각 나누기를 재사용해, 추출기 종류에 상관없이 같은 단위(조각)로
쪼갠 뒤 그 조각을 비교한다 - 페이지/섹션 경계가 아니라 "조각"이 diff의
한 줄이 된다.

표시된 diff는 실제로 값이 바뀐 건지 판단하는 출발점일 뿐이다.

사용법: uv run python scripts/diff_announcement_rounds.py <이전 차수 문서> <이후 차수 문서>
       (경로 확장자로 .hwpx/.hwp/.pdf 추출기를 자동으로 고름)
"""

from __future__ import annotations

import argparse
import difflib
from pathlib import Path

from scripts.draft_requirements import build_split_pattern, split_into_chunks
from scripts.extract_hwp import extract_section_texts as extract_hwp_section_texts
from scripts.extract_hwpx import extract_section_texts as extract_hwpx_section_texts
from scripts.extract_pdf import extract_page_texts
from scripts.locate_source_page import normalize


def extract_document_units(doc_path: Path) -> list[str]:
    """확장자에 따라 HWPX/HWP는 섹션별, PDF는 페이지별로 텍스트를 뽑는다."""
    suffix = doc_path.suffix.lower()
    if suffix == ".hwpx":
        return extract_hwpx_section_texts(doc_path)
    if suffix == ".hwp":
        return extract_hwp_section_texts(doc_path)
    if suffix == ".pdf":
        return extract_page_texts(doc_path)
    raise ValueError(f"지원하지 않는 확장자: {doc_path.suffix} (.hwpx/.hwp/.pdf만 가능)")


def chunk_units(units: list[str]) -> list[str]:
    """페이지/섹션 텍스트를 문서 기호(❍□-※①…) 기준 조각으로 나누고, 조각 안 줄바꿈은
    공백으로 정규화한다 - 추출기가 달라도(HWPX/HWP) 같은 내용이면 같은 조각으로 비교되게 한다."""
    full_text = "\n".join(units)
    pattern = build_split_pattern(())
    return [normalize(chunk) for chunk in split_into_chunks(full_text, pattern)]


def diff_rounds(old_units: list[str], new_units: list[str]) -> str:
    """두 차수를 문서 기호 기준 조각 단위로 나눠 unified diff 형식으로 비교한다."""
    old_chunks = chunk_units(old_units)
    new_chunks = chunk_units(new_units)
    diff = difflib.unified_diff(
        old_chunks, new_chunks, fromfile="이전 차수", tofile="이후 차수", lineterm=""
    )
    return "\n".join(diff)


def main() -> None:
    """CLI 진입점: 이전/이후 차수 문서 경로를 받아 diff를 표준출력에 찍는다."""
    parser = argparse.ArgumentParser(
        description="두 차수 공고문 텍스트 비교 (HWPX/HWP 우선, PDF 대체)"
    )
    parser.add_argument("old_doc", type=Path, help="이전 차수 문서 경로 (.hwpx/.hwp/.pdf)")
    parser.add_argument("new_doc", type=Path, help="이후 차수 문서 경로 (.hwpx/.hwp/.pdf)")
    args = parser.parse_args()

    old_units = extract_document_units(args.old_doc)
    new_units = extract_document_units(args.new_doc)
    print(
        f"이전({args.old_doc.suffix}): {len(old_units)}개 / 이후({args.new_doc.suffix}): {len(new_units)}개"
    )

    diff_text = diff_rounds(old_units, new_units)
    if not diff_text:
        print("텍스트 차이 없음 (굵은 글씨 변경은 이 방식으로 못 잡을 수 있음)")
        return
    print(diff_text)


if __name__ == "__main__":
    main()
