"""
HWPX 공고문에서 원문 텍스트를 추출한다.
"""

from __future__ import annotations

import argparse
import zipfile
from pathlib import Path
import xml.etree.ElementTree as ET

HWP_PARAGRAPH_NS = "http://www.hancom.co.kr/hwpml/2011/paragraph"
DEFAULT_OUTPUT_DIR = Path("data/interim")

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
      runs = root.iter(f"{{{HWP_PARAGRAPH_NS}}}t") # <hp:fwSpace/> 같은 빈 태그 뒤의 글자가 .text가 아니라 자식의 .tail에 있어서 누락
      section_texts.append("".join("".join(run.itertext()) for run in runs)) # itertext()로 태그 밑 모든 글자 순서대로 모음 
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