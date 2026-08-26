"""agency_contacts.csv에 지도 기능용 신규 컬럼 12개를 append하고 기존 행의 is_active를
'true'로 backfill하는 1회성 마이그레이션 스크립트. 기존 15개 컬럼명·값은 건드리지 않는다.
멱등 — 이미 마이그레이션된 파일에 다시 실행하면 아무 것도 하지 않는다.

사용법: uv run python scripts/migrate_agency_contacts_map_columns.py
"""

from __future__ import annotations

import csv
from pathlib import Path

from scripts.reference_schema import AGENCY_CONTACTS, REFERENCE_SCHEMA

CSV_PATH = Path("reference/agency_contacts.csv")


def migrate(path: Path = CSV_PATH) -> int:
    """신규 컬럼을 append하고 is_active=true를 backfill한다. 반환값은 갱신한 행 수 —
    이미 마이그레이션된 파일이면 0."""
    table = REFERENCE_SCHEMA[AGENCY_CONTACTS]
    with path.open(newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    if rows and list(rows[0].keys()) == table.header:
        return 0  # 이미 마이그레이션됨

    new_columns = [c for c in table.header if c not in rows[0].keys()] if rows else []
    for row in rows:
        for column in new_columns:
            row[column] = "true" if column == "is_active" else ""

    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=table.header)
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)


def main() -> int:
    count = migrate()
    print(f"{count}행 마이그레이션 완료" if count else "이미 마이그레이션됨 — 변경 없음")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
