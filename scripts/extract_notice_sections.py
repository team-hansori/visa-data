"""공고 HWPX 문서를 최상위 챕터별로 쪼개 Claude가 읽을 텍스트 파일로 저장한다.

챕터 인식은 scripts/draft_requirements.py의 HEADING_DISCOVERY_PATTERN을 그대로
재사용한다("숫자 | | 제목" 형태 헤딩 - B_E-7-4R 근거표 초안 작업에서 이미 검증된
패턴이며, F-4-R 12차 공고문 HWPX에서도 8개 챕터가 정확히 인식됨을 확인했다).

PDF 변환본과 달리 HWPX는 강조 숫자도 그대로 텍스트로 남아있어 내용을 있는 그대로
잘라내기만 하면 된다 - visa_title_classifier.py 상단 주석 참고.

사용법: uv run python scripts/extract_notice_sections.py <HWPX경로>
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path

from draft_requirements import HEADING_DISCOVERY_PATTERN, discover_top_headings
from extract_hwpx import extract_section_texts

DEFAULT_OUTPUT_DIR = Path("data/interim")


@dataclass
class ChapterContent:
    chapter_number: int
    title: str
    text: str
    saved_path: str


def extract_full_text(hwpx_path: Path) -> str:
    """HWPX 내 모든 section 텍스트를 이어붙인 전체 원문을 반환한다."""
    return "\n".join(extract_section_texts(hwpx_path))


def split_into_chapters(text: str) -> list[tuple[int, str, str]]:
    """전체 원문을 최상위 챕터 단위로 잘라 (챕터번호, 제목, 본문) 목록을 반환한다.

    같은 제목이 본문 중에 우연히 다시 언급돼도(예: 붙임1에서 다른 챕터 재언급)
    discover_top_headings가 등장 순서대로 찾은 첫 매칭만 챕터 경계로 쓴다 -
    draft_requirements.py의 build_top_section_pattern과 동일한 전제.
    """
    top_headings = discover_top_headings(text)
    if not top_headings:
        return []

    boundaries: list[tuple[int, str]] = []
    seen_titles: set[str] = set()
    for match in HEADING_DISCOVERY_PATTERN.finditer(text):
        title = match.group(1)
        if title not in top_headings or title in seen_titles:
            continue
        seen_titles.add(title)
        boundaries.append((match.start(), title))

    chapters = []
    for i, (start, title) in enumerate(boundaries):
        end = boundaries[i + 1][0] if i + 1 < len(boundaries) else len(text)
        chapters.append((i + 1, title, text[start:end].strip()))
    return chapters


def save_chapters(
    chapters: list[tuple[int, str, str]], hwpx_path: Path, output_dir: Path
) -> list[ChapterContent]:
    """챕터별 본문을 output_dir에 파일로 저장하고 ChapterContent 목록을 반환한다."""
    output_dir.mkdir(parents=True, exist_ok=True)
    results = []
    for chapter_number, title, text in chapters:
        safe_title = title.replace(" ", "").replace("/", "_")
        out_path = output_dir / f"{hwpx_path.stem}_ch{chapter_number}_{safe_title}.txt"
        out_path.write_text(text, encoding="utf-8")
        results.append(
            ChapterContent(
                chapter_number=chapter_number,
                title=title,
                text=text,
                saved_path=str(out_path),
            )
        )
    return results


def main() -> None:
    """CLI 진입점: HWPX 경로를 받아 챕터별로 쪼갠 텍스트 파일을 저장하고 목록을 JSON으로 출력한다."""
    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8")  # Windows cp949 콘솔 출력 오류 방지

    parser = argparse.ArgumentParser(description="공고 HWPX를 최상위 챕터별 텍스트로 분리")
    parser.add_argument("hwpx_path", type=Path, help="분석할 HWPX 경로")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="챕터별 텍스트를 저장할 폴더 (기본: data/interim)",
    )
    args = parser.parse_args()

    text = extract_full_text(args.hwpx_path)
    chapters = split_into_chapters(text)
    if not chapters:
        print(
            json.dumps(
                {
                    "chapters": [],
                    "warning": "최상위 챕터 제목을 하나도 찾지 못함 - 문서 구조가 다를 수 있음, 사람이 직접 확인 필요",
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        raise SystemExit(1)

    saved = save_chapters(chapters, args.hwpx_path, args.output_dir)
    # text는 파일에 이미 저장했으니 요약 출력에서는 빼서 콘솔 출력을 짧게 유지한다.
    summary = [
        {"chapter_number": c.chapter_number, "title": c.title, "saved_path": c.saved_path}
        for c in saved
    ]
    print(json.dumps({"chapters": summary}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
