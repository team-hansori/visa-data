"""E-7-4R review CSV의 공통 스키마 1차 분류 제안 생성기.

원본 review CSV를 덮어쓰지 않고 ``auto_*`` 제안 컬럼이 추가된 별도 CSV를 만든다.
키워드와 섹션을 이용한 보수적인 1차 분류만 수행하며, 최종 ``review_decision``과
``target_table``은 사람이 확인한 뒤 반영해야 한다.

사용법::

    uv run python scripts/classify_review_rows.py \
      extraction/B_E-7-4R/requirements/_review_current_requirements.csv

기존 검수 내용을 보존하면서 확신도 높은 제안만 원본에 반영하려면 ``--in-place``를
사용한다. ``status``, 출처, 메모, 검토자 정보는 변경하지 않는다.

기본 출력은 입력 파일 옆의 ``_review_current_requirements_proposed.csv``다.
"""

from __future__ import annotations

import argparse
import csv
import re
from dataclasses import asdict, dataclass
from io import StringIO
from pathlib import Path


AUTO_FIELDS = (
    "auto_review_decision",
    "auto_target_table",
    "auto_confidence",
    "auto_reason",
)

HEADING_PATTERN = re.compile(r"^(?:\d+\s*\|\s*\||<[^>]+>)")
STRUCTURAL_MARKERS = (
    "❍",
    "※",
    "-",
    "①",
    "②",
    "③",
    "④",
    "⑤",
    "⑥",
    "⑦",
    "⑧",
    "⑨",
    "⑩",
    "Ⓐ",
    "Ⓑ",
    "Ⓒ",
    "Ⓓ",
    "Ⓔ",
    "Ⓕ",
    "Ⓖ",
    "Ⓗ",
    "Ⓘ",
    "Ⓙ",
)


@dataclass(frozen=True)
class Classification:
    review_decision: str
    target_table: str
    confidence: str
    reason: str


def classify_row(row: dict[str, str]) -> Classification:
    """한 행의 최종 분류 후보를 제안한다.

    분류 규칙은 확실한 단서가 있는 경우에만 제안하고, 나머지는
    ``needs_review/none``으로 남긴다.
    """

    raw_text = (row.get("raw_text") or "").strip()
    source_section = (row.get("source_section") or "").strip()
    requirement_type = (row.get("requirement_type") or "").strip()
    status = (row.get("status") or "").strip()
    combined = f"{source_section} {raw_text}"

    if status == "extraction_failed":
        return Classification(
            "needs_review",
            "none",
            "high",
            "원문 조각 복원 또는 행 구조 수정이 먼저 필요함",
        )

    if HEADING_PATTERN.match(raw_text):
        return Classification("excluded", "none", "high", "섹션 제목 또는 표 제목으로 보임")

    if any(keyword in combined for keyword in ("점수제 심사", "점수표", "가점 항목", "감점 항목")):
        return Classification(
            "reclassified",
            "scoring_items",
            "high",
            "K-POINT 점수표 영역으로 분류",
        )

    has_quota_signal = any(
        keyword in combined for keyword in ("쿼터", "기추천", "잔여", "모집규모")
    )
    has_process_signal = any(
        keyword in combined for keyword in ("추진 체계", "신청방법", "접수", "결과안내")
    )

    if has_quota_signal and has_process_signal:
        return Classification(
            "needs_review",
            "none",
            "low",
            "쿼터와 절차 정보가 섞인 혼합 행이라 행 분리 또는 수동 분류 필요",
        )

    if has_quota_signal:
        return Classification(
            "reclassified",
            "visa_quota_status",
            "high",
            "모집 규모 또는 쿼터 정보로 분류",
        )

    if has_process_signal:
        return Classification(
            "reclassified",
            "visa_process_stages",
            "high",
            "신청·접수·추천 절차 정보로 분류",
        )

    has_submission_signal = any(
        keyword in combined for keyword in ("제출서류", "제출 서류", "첨부서류")
    )
    has_form_context_signal = "서식" in combined and any(
        context in combined for context in ("제출", "첨부")
    )

    if has_submission_signal or has_form_context_signal:
        return Classification(
            "reclassified",
            "document_requirements",
            "high",
            "제출서류 또는 서식 영역으로 분류",
        )

    if "자격 요건" in source_section and raw_text.startswith(STRUCTURAL_MARKERS):
        return Classification(
            "approved",
            "visa_requirement_criteria",
            "medium",
            "자격 요건 영역의 조건 행으로 분류",
        )

    if "공고 개요" in source_section and requirement_type == "unclassified":
        return Classification(
            "needs_review",
            "none",
            "low",
            "공고 개요의 메타데이터인지 절차·쿼터인지 추가 확인 필요",
        )

    if "기타 사항" in source_section:
        return Classification(
            "needs_review",
            "none",
            "low",
            "기타 사항의 공통 마스터 대상 여부 추가 확인 필요",
        )

    return Classification("needs_review", "none", "low", "자동 분류 단서 부족")


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    """CSV를 읽고 엑셀 편집 과정에서 섞인 NUL 문자를 제거한다."""

    text = path.read_text(encoding="utf-8-sig").replace("\x00", "")
    reader = csv.DictReader(StringIO(text))
    if reader.fieldnames is None:
        raise ValueError(f"CSV 헤더가 없습니다: {path}")
    return reader.fieldnames, list(reader)


def proposed_output_path(input_path: Path) -> Path:
    """원본을 보존하는 제안 파일 경로를 만든다."""

    marker = "_review_current_requirements"
    if marker not in input_path.stem:
        raise ValueError(f"입력 파일명이 예상 형식이 아닙니다: {input_path}")
    return input_path.with_name(f"{marker}_proposed{input_path.suffix}")


def write_proposals(fieldnames: list[str], rows: list[dict[str, str]], output_path: Path) -> int:
    """분류 제안 컬럼을 추가해 별도 CSV로 저장한다."""

    output_fieldnames = [*fieldnames, *AUTO_FIELDS]
    with output_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=output_fieldnames)
        writer.writeheader()
        for row in rows:
            proposal = asdict(classify_row(row))
            row = {
                **row,
                **{
                    "auto_review_decision": proposal["review_decision"],
                    "auto_target_table": proposal["target_table"],
                    "auto_confidence": proposal["confidence"],
                    "auto_reason": proposal["reason"],
                },
            }
            writer.writerow(row)
    return len(rows)


def apply_high_confidence(rows: list[dict[str, str]]) -> int:
    """확신도 높은 자동 제안만 기존 review 필드에 반영한다.

    기존 ``status``와 출처·메모·검토자 컬럼은 보존한다. 애매한 행과 추출 실패 행은
    사람이 확인할 수 있도록 기존 ``needs_review/none`` 값을 유지한다.
    """

    applied = 0
    for row in rows:
        current_decision = row.get("review_decision", "")
        current_target = row.get("target_table", "")
        proposal = classify_row(row)
        if (
            current_decision == "needs_review"
            and current_target == "none"
            and proposal.confidence == "high"
            and proposal.review_decision != "needs_review"
        ):
            row["review_decision"] = proposal.review_decision
            row["target_table"] = proposal.target_table
            applied += 1
    return applied


def write_rows(fieldnames: list[str], rows: list[dict[str, str]], output_path: Path) -> None:
    """주어진 컬럼과 행을 CSV로 저장한다."""

    with output_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="E-7-4R review CSV 1차 분류 제안 생성")
    parser.add_argument("input_csv", type=Path, help="원본 review CSV 경로")
    parser.add_argument("--output", type=Path, help="제안 CSV 출력 경로")
    parser.add_argument(
        "--in-place",
        action="store_true",
        help="확신도 높은 제안만 입력 review CSV에 반영하고 기존 메타데이터는 보존",
    )
    args = parser.parse_args()

    fieldnames, rows = read_csv(args.input_csv)
    if args.in_place:
        applied = apply_high_confidence(rows)
        write_rows(fieldnames, rows, args.input_csv)
        print(f"확신도 높은 분류 {applied}행 반영 -> {args.input_csv}")
        return

    output_path = args.output or proposed_output_path(args.input_csv)
    count = write_proposals(fieldnames, rows, output_path)
    print(f"{count}행 분류 제안 생성 -> {output_path}")


if __name__ == "__main__":
    main()
