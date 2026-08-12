"""추출된 원문 텍스트를 문서 기호 기준으로 쪼개 근거표 초안을 만든다."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

# 졍규식 전역 설정 
SPLIT_PATTERN = re.compile(
      r"(?=[□❍※①②③④⑤⑥⑦⑧⑨⑩])" # 바로 다음 글자가 이 기호들 중 하나면 여기서 자름 
      r"|(?<=\s)(?=-\s)" # 바로 앞 공백이 2개 이상 + 바로 다음이 (하이픈+공백) 이면 여기서 자름 -> 공백 없이 붙은 하이픈은 건드리지 않음. 
      r"|(?<=\s)(?=\*\s)" # 바로 앞에 공백이 있고, 다음이 '* '이면 여기서 자름 
)

def split_into_chunks(text: str) -> list[str]:
      """원문을 □/❍/※/번호(①②③...)/공백 뒤 -/공백 뒤 * 기준으로 조각낸다."""
      chunks = SPLIT_PATTERN.split(text)
      return [chunk.strip() for chunk in chunks if chunk.strip()] 

SECTION_MARKER = "□"
GROUP_START_MARKER = "❍"
SUBCONDITION_MARKERS = ("※", "-")
NUMBERED_MARKERS = "①②③④⑤⑥⑦⑧⑨⑩"
FOOTNOTE_MARKER = "*"

def classify_chunk(chunk: str) -> str: 
      """조각의 첫 글자를 보고 종류(section/requirement/subcondition/numbered/footnote/other)를 판단한다."""
      first = chunk[0]
      if first == SECTION_MARKER or chunk.startswith("<"):
            return "section"
      if first == GROUP_START_MARKER: 
          return "requirement" # 새로운 요건 시작 
      if first in SUBCONDITION_MARKERS:
          return "subcondition"
      if first in NUMBERED_MARKERS:
            return "number"
      if first == FOOTNOTE_MARKER:
            return "footnote" # 각주
      return "other"
            

def main() -> None:
      """CLI 진입점: 텍스트 파일 경로를 받아 조각낸 결과를 번호 매겨 출력"""
      parser = argparse.ArgumentParser(description="원문 텍스트를 기호 기준으로 조각내 확인")
      parser.add_argument("text_path", type=Path, help="조각낼 텍스트 파일 경로")
      args = parser.parse_args()

      text = args.text_path.read_text(encoding="utf-8")
      chunks = split_into_chunks(text)
      print(f"총 {len(chunks)}개 조각")
      for i, chunk in enumerate(chunks):
            kind = classify_chunk(chunk)
            print(f"[{i}] ({kind}) {chunk[:60]}")

if __name__ == "__main__":
      main()