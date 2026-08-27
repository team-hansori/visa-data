"""migrate_agency_contacts_map_columns.py 회귀 테스트."""

from __future__ import annotations

import csv
from pathlib import Path

from scripts.migrate_agency_contacts_map_columns import migrate
from scripts.reference_schema import AGENCY_CONTACTS, REFERENCE_SCHEMA

LEGACY_HEADER = [
    "agency_id",
    "category_major",
    "category_minor",
    "region",
    "department_name",
    "address",
    "phone",
    "url",
    "target_audience",
    "is_user_facing",
    "valid_from",
    "valid_to",
    "source_document",
    "source_page",
    "last_verified_at",
]


def write_legacy_csv(path: Path) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=LEGACY_HEADER)
        writer.writeheader()
        writer.writerow(
            {
                "agency_id": "11111111-1111-1111-1111-111111111111",
                "category_major": "FOREIGN_EMPLOYMENT_SUPPORT",
                "category_minor": "F-2-R",
                "region": "충청북도",
                "department_name": "외국인정책추진단",
                "address": "",
                "phone": "043-220-2693",
                "url": "",
                "target_audience": "FOREIGN_WORKER",
                "is_user_facing": "true",
                "valid_from": "2026-01-01",
                "valid_to": "2026-12-31",
                "source_document": "test.pdf",
                "source_page": "1",
                "last_verified_at": "2026-08-12",
            }
        )


def test_migrate_appends_new_columns_and_backfills_is_active(tmp_path: Path):
    path = tmp_path / "agency_contacts.csv"
    write_legacy_csv(path)

    migrated = migrate(path)

    assert migrated == 1
    with path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    table = REFERENCE_SCHEMA[AGENCY_CONTACTS]
    assert list(rows[0].keys()) == table.header
    assert rows[0]["is_active"] == "true"
    assert rows[0]["agency_type"] == ""
    assert rows[0]["latitude"] == ""
    # 기존 값은 그대로 유지된다.
    assert rows[0]["department_name"] == "외국인정책추진단"


def test_migrate_is_idempotent(tmp_path: Path):
    path = tmp_path / "agency_contacts.csv"
    write_legacy_csv(path)

    first = migrate(path)
    second = migrate(path)

    assert first == 1
    assert second == 0
    with path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 1  # 두 번 실행해도 행이 중복되지 않는다.
