"""HWP(구버전 바이너리) 공고문에서 원문 텍스트를 추출한다.

.hwp는 zip 구조인 .hwpx와 달리 OLE 바이너리 형식이라 extract_hwpx.py로는
못 읽는다. pyhwp의 hwp5html로 먼저 XHTML로 변환한 뒤 표 구조(행/칸)를
보존하며 텍스트를 뽑는다. pyhwp가 같이 제공하는 hwp5txt는 표 내용을
통째로 "<표>"로 뭉개버리는 문제가 있어(PDF의 굵은 글씨 누락과 비슷한
성격의 한계) 이 방식을 쓴다.

사용법: uv run python scripts/extract_hwp.py <hwp경로>
"""

from __future__ import annotations

import argparse
import subprocess
import tempfile
from pathlib import Path

from lxml import etree

XHTML_NS = "http://www.w3.org/1999/xhtml"
TABLE_TAG = f"{{{XHTML_NS}}}table"
ROW_TAG = f"{{{XHTML_NS}}}tr"
CELL_TAG = f"{{{XHTML_NS}}}td"
SECTION_DIV_TAG = f"{{{XHTML_NS}}}div"
SECTION_CLASS_PREFIX = "Section Section-"

DEFAULT_OUTPUT_DIR = Path("data/interim")


def convert_to_xhtml(hwp_path: Path, work_dir: Path) -> Path:
    """hwp5html로 hwp 파일을 work_dir/index.xhtml로 변환한다."""
    subprocess.run(
        ["hwp5html", "--output", str(work_dir), str(hwp_path)],
        check=True,
        capture_output=True,
    )
    return work_dir / "index.xhtml"


def extract_table_text(table: etree._Element) -> str:
    """<table> 요소를 행마다 칸을 ' | '로 구분한 문자열로 변환한다 (extract_hwpx.py와 같은 방식)."""
    rows = []
    for tr in table.findall(ROW_TAG):  # findall(직계 자식만) - 중첩 표 중복 방지
        cells = [extract_node_text(td).strip() for td in tr.findall(CELL_TAG)]
        rows.append(" | ".join(cells))
    return "\n".join(rows)


def extract_node_text(node: etree._Element) -> str:
    """노드 하나를 받아 그 아래 텍스트를 추출한다. <table>을 만나면 행/칸 구분을 보존한다."""
    if node.tag == TABLE_TAG:
        return f"\n{extract_table_text(node)}\n"
    text_parts = [node.text or ""]
    for child in node:
        text_parts.append(extract_node_text(child))
        text_parts.append(child.tail or "")
    return "".join(text_parts)


def find_section_divs(root: etree._Element) -> list[etree._Element]:
    """최상위 'Section Section-N' div들을 문서에 나온 순서대로 찾는다."""
    return [
        div
        for div in root.iter(SECTION_DIV_TAG)
        if div.get("class", "").startswith(SECTION_CLASS_PREFIX)
    ]


def normalize_paragraph_breaks(text: str) -> str:
    """HWP 문단 끝마다 들어가는 \\r(캐리지리턴)을 공백으로 바꾼다.

    \\r은 hwp5html이 각 문단 끝에 넣는 구분자일 뿐 실제 줄바꿈이 아닌데,
    그대로 두면 HWPX 추출 결과보다 훨씬 잘게 줄이 쪼개져서 diff가 실제
    변경 없는 부분까지 전부 다르다고 표시한다. 표 행 구분에 쓰는 '\\n'은
    건드리지 않는다.
    """
    return text.replace("\r\n", " ").replace("\r", " ")


def extract_section_texts(hwp_path: Path) -> list[str]:
    """hwp 파일을 섹션별 원문 텍스트 리스트로 반환한다 (extract_hwpx.py의 hwpx 버전과 같은 인터페이스)."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        xhtml_path = convert_to_xhtml(hwp_path, Path(tmp_dir))
        root = etree.parse(str(xhtml_path)).getroot()
        return [
            normalize_paragraph_breaks(extract_node_text(div)) for div in find_section_divs(root)
        ]


def save_section_texts(section_texts: list[str], hwp_path: Path, output_dir: Path) -> list[Path]:
    """구역별 텍스트를 output_dir에 파일로 저장하고 저장된 경로 목록을 반환한다."""
    output_dir.mkdir(parents=True, exist_ok=True)
    saved_paths = []
    for i, text in enumerate(section_texts):
        out_path = output_dir / f"{hwp_path.stem}_section{i}.txt"
        out_path.write_text(text, encoding="utf-8")
        saved_paths.append(out_path)
    return saved_paths


def main() -> None:
    """CLI 진입점: hwp 경로를 받아 섹션별 텍스트를 추출해 저장한다."""
    parser = argparse.ArgumentParser(description="HWP(구버전) 공고문 텍스트 추출")
    parser.add_argument("hwp_path", type=Path, help="추출할 .hwp 파일 경로")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="추출한 텍스트를 저장할 폴더 (기본: data/interim)",
    )
    args = parser.parse_args()

    section_texts = extract_section_texts(args.hwp_path)
    print(f"총 {len(section_texts)}개 섹션 추출됨")
    saved_paths = save_section_texts(section_texts, args.hwp_path, args.output_dir)
    for path in saved_paths:
        print(f"저장됨: {path}")


if __name__ == "__main__":
    main()
