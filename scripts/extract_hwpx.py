"""
HWPX 공고문에서 원문 텍스트를 추출한다.
"""

from __future__ import annotations

import argparse
import zipfile
from pathlib import Path
import xml.etree.ElementTree as ET

HWP_PARAGRAPH_NS = "http://www.hancom.co.kr/hwpml/2011/paragraph"

# 상수 추가 
HWP_TABLE_TAG = f"{{{HWP_PARAGRAPH_NS}}}tbl" # 표 전체 -> 지금 보고 있는게 표인지 판단할 때 사용
HWP_ROW_TAG = f"{{{HWP_PARAGRAPH_NS}}}tr" # 행 -> 표 하나 안에서 행들을 하나씩 순회할 때 사용 
HWP_CELL_TAG = f"{{{HWP_PARAGRAPH_NS}}}tc" # 칸 -> 행 하나 안에서 칸들을 하나씩 찾을 때 사용 
HWP_TEXT_TAG = f"{{{HWP_PARAGRAPH_NS}}}t" # 글자 -> 칸 안의 글자를 찾을 때 

DEFAULT_OUTPUT_DIR = Path("data/interim")

def extract_table_text(tbl: ET.ElementTree) -> str:
  """<hp:tbl> 요소를 행마다 칸을 | 으로 구분한 문자열로 변환한다."""
  rows = []
  for tr in tbl.iter(HWP_ROW_TAG):
    cells = [
      "".join("".join(t.itertext()) for t in tc.iter(HWP_TEXT_TAG)).strip() 
      for tc in tr.findall(HWP_CELL_TAG) # 표 안의 행(tr) 마다 칸(tc)을 찾음
    ]

    rows.append(" | ".join(cells))
  return "\n".join(rows)

def extract_node_text(node: ET.Element) -> str: 
  """XML 노드(태그) 하나를 받아서 그 아래 텍스트를 문자열로 추출한다. 표(<hp:tbl>)를 만나면 행/칸 구분을 보존한다."""
  if node.tag == HWP_TABLE_TAG: # 표를 만나면 extract_table_text로 넘김
    return extract_table_text(node)
  if node.tag == HWP_TEXT_TAG: # 표가 아닌 글자 태그면 그 안의 글자를 다 모아서 돌려줌 
    return "".join(node.itertext()) 
  return "".join(extract_node_text(child) for child in node) # 두 경우를 만날 때까지 재귀 호출 


def extract_section_texts(hwpx_path: Path) -> list[str]:
  """hwpx 내부 Contents/section*.xml 각각에서 원문 텍스트를 추출해 리스트로 반환한다. """
  with zipfile.ZipFile(hwpx_path) as archive: 
    section_names = sorted(
      name for name in archive.namelist()
      if name.startswith("Contents/section") and name.endswith(".xml")
    )

    section_texts = []
    for name in section_names:
      root = ET.fromstring(archive.read(name))
      # runs = root.iter(f"{{{HWP_PARAGRAPH_NS}}}t") # <hp:fwSpace/> 같은 빈 태그 뒤의 글자가 .text가 아니라 자식의 .tail에 있어서 누락
      # section_texts.append("".join("".join(run.itertext()) for run in runs)) # itertext()로 태그 밑 모든 글자 순서대로 모음 
      section_texts.append(extract_node_text(root))
    return section_texts

def save_section_texts(
    section_texts: list[str], hwpx_path: Path, output_dir: Path
) -> list[Path]:
  """구역별 텍스트를 output_dir에 파일로 저장하고 저장된 경로 목록을 반환한다. """
  output_dir.mkdir(parents=True, exist_ok=True)
  saved_paths = []
  for i, text in enumerate(section_texts):
    out_path = output_dir / f"{hwpx_path.stem}_section{i}.txt"
    out_path.write_text(text, encoding="utf-8")
    saved_paths.append(out_path)
  return saved_paths


def main() -> None:
    """CLI 진입점: hwpx 경로를 받아 섹션별 텍스트를 추출해 미리보기를 출력한다."""
    parser = argparse.ArgumentParser(description="HWPX 자격요건/공고 텍스트 추출")
    parser.add_argument("hwpx_path", type=Path, help="추출할 HWPX 파일 경로")
    parser.add_argument(
      "--output-dir", 
      type=Path, 
      default=DEFAULT_OUTPUT_DIR,
      help="추출한 텍스트를 저장할 폴더 (기본 : data/interim)"
      )
    args = parser.parse_args()

    section_texts = extract_section_texts(args.hwpx_path)
    print(f"총 {len(section_texts)}개 섹션 추출됨")
    saved_paths = save_section_texts(section_texts, args.hwpx_path, args.output_dir)
    for path in saved_paths:
      print(f"저장됨: {path}")

if __name__ == "__main__":
  main()