"""
추출된 원문 텍스트를 문서 기호 기준으로 쪼개 근거표 초안을 만든다.
사용법: uv run python scripts/draft_requirements.py <텍스트파일> <기준CSV경로>
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path
import csv
import logging

logger = logging.getLogger(__name__)
SHORT_TEXT_THRESHOLD = 8

# 졍규식 전역 설정
SPLIT_PATTERN = re.compile(
      r"(?=[□❍※])" # 바로 다음 글자가 이 기호들 중 하나면 여기서 자름
      r"|(?<!<)(?=[①②③④⑤⑥⑦⑧⑨⑩])" # 번호 앞에서 자르되, 바로 앞이 '<'면 자르지 않음 (다이어그램 라벨 보호)
      r"|(?<=\s)(?=-\s)" # 바로 앞 공백이 2개 이상 + 바로 다음이 (하이픈+공백) 이면 여기서 자름 -> 공백 없이 붙은 하이픈은 건드리지 않음.
      r"|(?<=\s)(?=\*\s)" # 바로 앞에 공백이 있고, 다음이 '* '이면 여기서 자름
      r"|(?=공고 개요|추진 체계|자격 요건|제출서류)" # 최상위 챕터 제목 앞에서도 잘라 앞 내용과 안 섞이게 함
)

SECTION_MARKER = "□"
GROUP_START_MARKER = "❍"
SUBCONDITION_MARKERS = ("※", "-")
NUMBERED_MARKERS = "①②③④⑤⑥⑦⑧⑨⑩"
FOOTNOTE_MARKER = "*"

TOP_LEVEL_HEADINGS = ("공고 개요", "추진 체계", "자격 요건", "제출서류")

def split_into_chunks(text: str) -> list[str]:
      """원문을 □/❍/※/번호(①②③...)/공백 뒤 -/공백 뒤 * 기준으로 조각낸다."""
      chunks = SPLIT_PATTERN.split(text)
      return [chunk.strip() for chunk in chunks if chunk.strip()] 

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
            

def read_fieldnames(template_csv_path: Path) -> list[str]:
      """기존 근거표 CSV의 헤더 줄을 읽어 컬럼 목록으로 반환한다."""
      with template_csv_path.open(encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        return next(reader)

def detect_top_section(chunk: str, current_top_section: str) -> str:
    """조각 안에 있는 최상위 제목 문구 중 가장 뒤(오른쪽)에 있는 것으로 갱신한다.

    한 조각 안에 여러 제목이 섞여 있을 수 있어(예: '추진 체계'와 '자격 요건'이
    같은 조각에 같이 들어있는 경우), 첫 번째로 찾은 것이 아니라 가장 마지막에
    등장한 것을 써야 조각이 끝난 시점의 실제 챕터를 반영할 수 있다.
    """
    last_found = None
    last_index = -1
    for heading in TOP_LEVEL_HEADINGS:
        idx = chunk.rfind(heading)
        if idx > last_index:
            last_index = idx
            last_found = heading
    return last_found if last_found is not None else current_top_section

def build_draft_rows(chunks: list[str], source_documnet: str, fieldnames: list[str]) -> list[dict]:
      """분류된 조각들을 근거표 초안 행(dict) 리스트로 변환한다. fieldnames에 없는 컬럼은 빈 값으로 채운다. """
      rows = []
      current_section = ""
      current_top_section = ""
      current_group = ""
      group_count = 0

      for chunk in chunks:
            current_top_section = detect_top_section(chunk, current_top_section)
            kind = classify_chunk(chunk)

            if kind == "other": 
                  continue
            
            if kind == "section":
              current_section = chunk.lstrip("□<>").strip()
              current_group = ""
              continue

            if kind == "requirement": 
                group_count += 1
                current_group = f"G{group_count}"
                condition_group = current_group
            elif kind == "subcondition":
                condition_group = current_group
            else: # number, footnote
                condition_group = ""

            row = {name: "" for name in fieldnames} # 실제 CSV 헤더에 있는 컬럼 전부를 일단 빈 문자열로 채운 딕셔너리 
            row.update({ # 채울 수 있는 컬럼들만 새로 덮어씀 
                "record_id": f"REQ-{len(rows) + 1:03d}",
                "raw_text": chunk, 
                "condition_group": condition_group, 
                "status": "not_checked",
                "source_document": source_documnet, 
                "source_section": (f"{current_top_section} > {current_section}" if current_section else current_top_section),
            })
            rows.append(row)

      return rows

def detect_short_numbered_items(rows: list[dict]) -> None:
      """번호 항목인데 글자 수가 비정상적으로 짧으면 경고를 남긴다. """
      for current_row, next_row in zip(rows, rows[1:]): 
          current_text = current_row["raw_text"]
          next_text = next_row["raw_text"]
          if (
                current_text and next_text
                and current_text[0] in NUMBERED_MARKERS
                and next_text[0] in NUMBERED_MARKERS
                and len(current_text) < SHORT_TEXT_THRESHOLD
          ):
                logger.warning(
                    "%s: 내용이 너무 짧음 (%d자) - %r", 
                    current_row["record_id"], len(current_text), current_text, 
                )


def write_draft_csv(rows: list[dict], fieldnames: list[str], output_path: Path) -> None:
      """초안 행들을 CSV 파일로 저장한다"""
      with output_path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

def main() -> None:
      """CLI 진입점: 텍스트 파일과 기준 CSV 경로를 받아 근거표 초안 CSV를 만든다. """
      parser = argparse.ArgumentParser(description="원문 텍스트를 근거표 초안 CSV로 반환 ")
      parser.add_argument("text_path", type=Path, help="조각낼 텍스트 파일 경로")
      parser.add_argument("template_csv", type=Path, help="컬럼 구조를 따라갈 기존 근거표 csv 경로")
      args = parser.parse_args()

      text = args.text_path.read_text(encoding="utf-8")
      chunks = split_into_chunks(text)
      fieldnames = read_fieldnames(args.template_csv)
      rows = build_draft_rows(chunks, args.text_path.stem, fieldnames)
      detect_short_numbered_items(rows)

      output_path = args.template_csv.with_name(f"_draft_{args.template_csv.name}")
      write_draft_csv(rows, fieldnames, output_path)
      print(f"총 {len(rows)}행 생성됨 -> {output_path}")

if __name__ == "__main__":
      main()