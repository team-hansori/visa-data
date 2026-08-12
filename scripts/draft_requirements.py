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

SECTION_MARKER = "□"
GROUP_START_MARKER = "❍"
SUBCONDITION_MARKERS = ("※", "-")
NUMBERED_MARKERS = "①②③④⑤⑥⑦⑧⑨⑩"
FOOTNOTE_MARKER = "*"

# 최상위 챕터 제목은 원문에서 항상 '<숫자> |  | <제목>\n' 형태(헤딩 번호박스 표)로만 등장한다.
# 숫자가 다른 글자에 안 붙어있고(바로 앞이 공백/줄바꿈) 제목 뒤에 바로 줄바꿈이 오는 것으로,
# 표 안에서 우연히 숫자+파이프가 이어지는 경우(예: '...접수주2 |  | 하이코리아...')와 구분한다.
HEADING_DISCOVERY_PATTERN = re.compile(r"(?<!\S)\d\s*\|\s*\|\s*([가-힣][가-힣·() 　]*?)(?=\n)")

# 조각 분리 기호 앞에서 자르는 기본 규칙(최상위 챕터 제목 부분은 문서마다 달라서 여기 안 포함)
BASE_SPLIT_PATTERN = (
    r"(?=[□❍※])"  # 바로 다음 글자가 이 기호들 중 하나면 여기서 자름
    r"|(?<!<)(?=[①②③④⑤⑥⑦⑧⑨⑩])"  # 번호 앞에서 자르되, 바로 앞이 '<'면 자르지 않음 (다이어그램 라벨 보호)
    r"|(?<=\s)(?=-\s)"  # 바로 앞 공백이 2개 이상 + 바로 다음이 (하이픈+공백) 이면 여기서 자름 -> 공백 없이 붙은 하이픈은 건드리지 않음.
    r"|(?<=\s)(?=\*\s)"  # 바로 앞에 공백이 있고, 다음이 '* '이면 여기서 자름
)


def discover_top_headings(text: str) -> tuple[str, ...]:
    """원문을 미리 훑어서 최상위 챕터 제목을 등장 순서대로 전부 찾아 반환한다.

    목록을 손으로 미리 만들어두면 문서마다 챕터 개수가 달라서 빠뜨리기 쉽다
    (실제로 8차 공고에서 4개인 줄 알았는데 6개였음). 작업 시작 전에 이 함수로
    해당 문서에 실제로 있는 제목을 파악해서 쓴다.
    """
    seen: list[str] = []
    for match in HEADING_DISCOVERY_PATTERN.finditer(text):
        heading = match.group(1)
        if heading not in seen:
            seen.append(heading)
    return tuple(seen)


def build_split_pattern(top_headings: tuple[str, ...]) -> re.Pattern[str]:
    """발견된 최상위 챕터 제목까지 포함한 전체 분리 정규식을 만든다."""
    pattern = BASE_SPLIT_PATTERN
    if top_headings:
        heading_alt = "|".join(top_headings)
        pattern += rf"|(?=\d\s*\|\s*\|\s*(?:{heading_alt}))"  # 최상위 챕터 제목(번호박스 표 패턴)에서만 잘라 본문 속 재언급과 구분함
    return re.compile(pattern)


def build_top_section_pattern(top_headings: tuple[str, ...]) -> re.Pattern[str]:
    """발견된 최상위 챕터 제목 중 하나를 캡처하는 정규식을 만든다."""
    if (
        not top_headings
    ):  # 제목을 하나도 못 찾았으면 절대 안 걸리는 패턴을 돌려줌 (빈 캡처그룹 방지)
        return re.compile(r"(?!x)x")
    heading_alt = "|".join(top_headings)
    return re.compile(rf"\d\s*\|\s*\|\s*({heading_alt})")


def split_into_chunks(text: str, split_pattern: re.Pattern[str]) -> list[str]:
    """원문을 □/❍/※/번호(①②③...)/공백 뒤 -/공백 뒤 */최상위 챕터 제목 기준으로 조각낸다."""
    chunks = split_pattern.split(text)
    return [chunk.strip() for chunk in chunks if chunk.strip()]


def classify_chunk(chunk: str) -> str:
    """조각의 첫 글자를 보고 종류(section/requirement/subcondition/numbered/footnote/other)를 판단한다."""
    first = chunk[0]
    if first == SECTION_MARKER or chunk.startswith("<"):
        return "section"
    if first == GROUP_START_MARKER:
        return "requirement"  # 새로운 요건 시작
    if first in SUBCONDITION_MARKERS:
        return "subcondition"
    if first in NUMBERED_MARKERS:
        return "number"
    if first == FOOTNOTE_MARKER:
        return "footnote"  # 각주
    return "other"


def read_fieldnames(template_csv_path: Path) -> list[str]:
    """기존 근거표 CSV의 헤더 줄을 읽어 컬럼 목록으로 반환한다."""
    with template_csv_path.open(encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        return next(reader)


def detect_top_section(
    chunk: str, current_top_section: str, top_section_pattern: re.Pattern[str]
) -> str:
    """조각 안에 있는 최상위 제목 중 가장 뒤(오른쪽)에 있는 것으로 갱신한다.

    '<숫자> |  | <제목>' 형태(헤딩 번호박스 표 특유의 패턴, top_section_pattern)일
    때만 진짜 제목으로 인정한다. 본문 문장 속에서 같은 문구가 그냥 언급된 경우는
    이 패턴과 안 맞아서 걸러진다. 한 조각 안에 여러 제목이 섞여 있을 수 있어(예:
    '추진 체계'와 '자격 요건'이 같은 조각에 같이 들어있는 경우), 첫 번째가 아니라
    가장 마지막에 등장한 것을 써야 조각이 끝난 시점의 실제 챕터를 반영할 수 있다.
    """
    matches = list(top_section_pattern.finditer(chunk))
    if not matches:
        return current_top_section
    return matches[-1].group(1)


def build_draft_rows(
    chunks: list[str],
    source_documnet: str,
    fieldnames: list[str],
    top_section_pattern: re.Pattern[str],
) -> list[dict]:
    """분류된 조각들을 근거표 초안 행(dict) 리스트로 변환한다. fieldnames에 없는 컬럼은 빈 값으로 채운다."""
    rows = []
    current_section = ""
    current_top_section = ""
    current_group = ""
    group_count = 0

    for chunk in chunks:
        next_top_section = detect_top_section(chunk, current_top_section, top_section_pattern)
        if (
            next_top_section != current_top_section
        ):  # 최상위 챕터가 바뀌면 하위 섹션/그룹은 이전 챕터 것이라 초기화
            current_section = ""
            current_group = ""
        current_top_section = next_top_section
        kind = classify_chunk(chunk)

        if kind == "other":
            row = {name: "" for name in fieldnames}
            row.update(
                {
                    "record_id": f"REQ-{len(rows) + 1:03d}",
                    "requirement_type": "unclassified",
                    "raw_text": chunk,
                    "status": "not_checked",
                    "source_document": source_documnet,
                    "source_section": " > ".join(
                        part for part in (current_top_section, current_section) if part
                    ),
                    "notes": "자동 분류되지 않은 원문 조각 - 사람이 확인 필요",
                }
            )
            rows.append(row)
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
        else:  # number, footnote
            condition_group = ""

        row = {
            name: "" for name in fieldnames
        }  # 실제 CSV 헤더에 있는 컬럼 전부를 일단 빈 문자열로 채운 딕셔너리
        row.update(
            {  # 채울 수 있는 컬럼들만 새로 덮어씀
                "record_id": f"REQ-{len(rows) + 1:03d}",
                "raw_text": chunk,
                "condition_group": condition_group,
                "status": "not_checked",
                "source_document": source_documnet,
                "source_section": " > ".join(
                    part for part in (current_top_section, current_section) if part
                ),
            }
        )
        rows.append(row)

    return rows


def detect_short_numbered_items(rows: list[dict]) -> None:
    """번호 항목인데 글자 수가 비정상적으로 짧으면 경고를 남긴다."""
    for current_row, next_row in zip(rows, rows[1:]):
        current_text = current_row["raw_text"]
        next_text = next_row["raw_text"]
        if (
            current_text
            and next_text
            and current_text[0] in NUMBERED_MARKERS
            and next_text[0] in NUMBERED_MARKERS
            and len(current_text) < SHORT_TEXT_THRESHOLD
        ):
            logger.warning(
                "%s: 내용이 너무 짧음 (%d자) - %r",
                current_row["record_id"],
                len(current_text),
                current_text,
            )


def write_draft_csv(rows: list[dict], fieldnames: list[str], output_path: Path) -> None:
    """초안 행들을 CSV 파일로 저장한다"""
    with output_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    """CLI 진입점: 텍스트 파일과 기준 CSV 경로를 받아 근거표 초안 CSV를 만든다."""
    parser = argparse.ArgumentParser(description="원문 텍스트를 근거표 초안 CSV로 반환 ")
    parser.add_argument("text_path", type=Path, help="조각낼 텍스트 파일 경로")
    parser.add_argument("template_csv", type=Path, help="컬럼 구조를 따라갈 기존 근거표 csv 경로")
    args = parser.parse_args()

    text = args.text_path.read_text(encoding="utf-8")
    top_headings = discover_top_headings(text)
    print(f"발견된 최상위 챕터: {top_headings}")
    split_pattern = build_split_pattern(top_headings)
    top_section_pattern = build_top_section_pattern(top_headings)

    chunks = split_into_chunks(text, split_pattern)
    fieldnames = read_fieldnames(args.template_csv)
    rows = build_draft_rows(chunks, args.text_path.stem, fieldnames, top_section_pattern)
    detect_short_numbered_items(rows)

    output_path = args.template_csv.with_name(f"_draft_{args.template_csv.name}")
    write_draft_csv(rows, fieldnames, output_path)
    print(f"총 {len(rows)}행 생성됨 -> {output_path}")


if __name__ == "__main__":
    main()
