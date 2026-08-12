"""근거표 raw_text에서 숫자·단위·비교연산자를 추출해 자동으로 채운다.

사용법: uv run python scripts/extract_values.py <근거표CSV경로>
"""

from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path

OPERATOR_MAP = {
    "이상": ">=",
    "이하": "<=",
    "초과": ">",
    "미만": "<",
}
CONDITION_UNIT_ALT = "년|개월|일|회|명|만\\s*원|점"
CONDITION_VALUE_PATTERN = re.compile(
    rf"(\d+)\s*({CONDITION_UNIT_ALT})\s*(?:을|를)?\s*(이상|이하|초과|미만)"
)

WINDOW_UNIT_ALT = "년|개월"
MEASUREMENT_WINDOW_PATTERN = re.compile(rf"최근\s*(\d+)\s*({WINDOW_UNIT_ALT})\s*(간|이내)?")


def extract_condition_value(raw_text: str) -> dict[str, str] | None:
    """raw_text에 조건 값 패턴이 정확히 하나만 있으면 뽑아서 돌려준다. 없거나 여러 개면 None."""
    matches = list(CONDITION_VALUE_PATTERN.finditer(raw_text))
    if len(matches) != 1:
        return None
    number, unit, comparison = matches[0].groups()
    return {
        "value_numeric": number,
        "unit": unit.replace(" ", ""),
        "operator": OPERATOR_MAP[comparison],
    }


def extract_measurement_window(raw_text: str) -> dict[str, str] | None:
    """raw_text에 측정기간 패턴('최근 N년간' 등)이 정확히 하나만 있으면 뽑아서 돌려준다. 없거나 여러 개면 None."""
    matches = list(MEASUREMENT_WINDOW_PATTERN.finditer(raw_text))
    if len(matches) != 1:
        return None
    number, unit, _suffix = matches[0].groups()
    return {
        "measurement_window_value": number,
        "measurement_window_unit": unit,
    }


def _append_note(row: dict, note: str) -> None:
    """notes 컬럼에 메모를 이어붙인다 (기존 내용은 유지)."""
    existing = row.get("notes", "")
    if note in existing:
        return
    row["notes"] = f"{existing} / {note}".strip(" /") if existing else note


def apply_extracted_values(rows: list[dict]) -> int:
    """행마다 raw_text에서 값을 추출해 비어있는 칸만 채운다. 후보가 여러 개면 notes에 표시.

    이미 값이 있는 칸은(형제 칸이 비어있어도) 절대 덮어쓰지 않는다.
    반환값은 이번 호출로 실제 칸이 하나 이상 채워진 행 수.
    """
    updated_row_count = 0
    for row in rows:
        raw_text = row.get("raw_text", "")
        row_changed = False

        condition_matches = list(CONDITION_VALUE_PATTERN.finditer(raw_text))
        if len(condition_matches) == 1:
            extracted = extract_condition_value(raw_text)
            for field in ("value_numeric", "unit", "operator"):
                if not row.get(field):
                    row[field] = extracted[field]
                    row_changed = True
        elif len(condition_matches) > 1 and any(
            not row.get(field) for field in ("value_numeric", "unit", "operator")
        ):
            _append_note(row, "값 후보 여러 개 발견 - 직접 확인 필요")

        window_matches = list(MEASUREMENT_WINDOW_PATTERN.finditer(raw_text))
        if len(window_matches) == 1:
            extracted = extract_measurement_window(raw_text)
            for field in ("measurement_window_value", "measurement_window_unit"):
                if not row.get(field):
                    row[field] = extracted[field]
                    row_changed = True
        elif len(window_matches) > 1 and any(
            not row.get(field)
            for field in ("measurement_window_value", "measurement_window_unit")
        ):
            _append_note(row, "측정기간 후보 여러 개 발견 - 직접 확인 필요")

        if row_changed:
            updated_row_count += 1

    return updated_row_count


def main() -> None:
    """CLI 진입점: 근거표 CSV를 받아 비어있는 값·단위·연산자·측정기간을 채운다."""
    parser = argparse.ArgumentParser(description="근거표 raw_text에서 숫자/단위/연산자 자동 추출")
    parser.add_argument("csv_path", type=Path, help="채울 근거표 CSV 경로")
    args = parser.parse_args()

    with args.csv_path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)

    updated_row_count = apply_extracted_values(rows)

    with args.csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"이번 실행으로 채워진 행: {updated_row_count}개 / 전체 {len(rows)}행")


if __name__ == "__main__":
    main()
