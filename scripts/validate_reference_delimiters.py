"""
reference/ CSV의 다중값 컬럼이 저장소 전역 파이프(|) 구분자 컨벤션을
따르는지 검사한다. 쉼표(,)로 여러 값을 나열한 셀이 있으면 실패로 표시한다.

사용법: uv run python scripts/validate_reference_delimiters.py
"""

from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

REFERENCE_DIR = Path("reference")

# {파일명: [다중값을 담을 수 있는 컬럼명]}
MULTI_VALUE_COLUMNS: dict[str, list[str]] = {
    "agency_contacts.csv": ["region"],
    "risk_routing_table.csv": ["applies_to_visa_code", "external_region_scope"],
}

# 다중값: 쉼표 양쪽에 영문자나 한글 문자 포함 필수(하이픈 포함 비자코드 등도 한 토큰으로
# 인식). 쉼표 앞뒤 공백("청주, 진천")도 허용한다.
# 전화번호 내선 표기("2,4")는 양쪽이 숫자/하이픈뿐이라 문자로 시작하지 않으므로 제외됨
COMMA_IN_VALUE_RE = re.compile(
    r"[가-힣A-Za-z][가-힣A-Za-z0-9\-]*\s*,\s*[가-힣A-Za-z][가-힣A-Za-z0-9\-]*"
)


def find_comma_in_pipe_columns(
    path: Path, columns: list[str]
) -> list[tuple[int, str, str]]:
    """지정된 컬럼에서 쉼표로 여러 값을 나열한 셀을 찾는다."""
    violations: list[tuple[int, str, str]] = []
    if not path.exists():  # 파일이 아직 없으면 조용히 건너뜀 (validate_fk_integrity.py와 동일한 관례)
        return violations
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row_num, row in enumerate(reader, start=2):
            for column in columns:
                value = row.get(column, "")
                if COMMA_IN_VALUE_RE.search(value):
                    violations.append((row_num, column, value))
    return violations


def main() -> int:
    all_violations: list[str] = []
    for filename, columns in MULTI_VALUE_COLUMNS.items():
        path = REFERENCE_DIR / filename
        for row_num, column, value in find_comma_in_pipe_columns(path, columns):
            all_violations.append(
                f"{path}:{row_num} 컬럼 '{column}' — 쉼표 구분자 발견 (파이프 사용 필요): {value!r}"
            )

    if all_violations:
        print("파이프(|) 구분자 컨벤션 위반:")
        for line in all_violations:
            print(f"  - {line}")
        return 1

    print("OK: 모든 다중값 컬럼이 파이프 구분자를 사용합니다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
