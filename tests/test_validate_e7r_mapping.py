"""E-7-4R 원천·공통 매핑 무결성 검증 테스트."""

from __future__ import annotations

import csv
from pathlib import Path

from scripts.validate_e7r_mapping import validate_mapping


MAPPING_FIELDS = [
    "source_file",
    "local_record_id",
    "parent_record_id",
    "review_decision",
    "source_status",
    "target_table",
    "target_record_id",
    "mapping_action",
    "mapping_status",
    "source_document",
    "source_page",
    "source_section",
    "notes",
]
REVIEW_FIELDS = [
    "record_id",
    "parent_record_id",
    "source_document",
    "source_page",
    "source_section",
    "review_decision",
]
HISTORY_FIELDS = [
    "change_id",
    "from_round",
    "to_round",
    "old_source_page",
    "new_source_page",
    "old_value",
    "new_value",
]


def write_csv(path: Path, fields: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def build_files(tmp_path: Path) -> tuple[Path, Path, Path]:
    mapping = tmp_path / "schema_mapping.csv"
    review = tmp_path / "review.csv"
    history = tmp_path / "change_history.csv"
    write_csv(
        review,
        REVIEW_FIELDS,
        [
            {
                "record_id": "REQ-001",
                "parent_record_id": "",
                "source_document": "doc.pdf",
                "source_page": "1",
                "source_section": "공고 개요",
                "review_decision": "excluded",
            }
        ],
    )
    write_csv(
        history,
        HISTORY_FIELDS,
        [
            {
                "change_id": "CHG-001",
                "from_round": "1",
                "to_round": "2",
                "old_source_page": "7",
                "new_source_page": "7",
                "old_value": "old",
                "new_value": "new",
            }
        ],
    )
    write_csv(
        mapping,
        MAPPING_FIELDS,
        [
            {
                "source_file": "review.csv",
                "local_record_id": "REQ-001",
                "parent_record_id": "",
                "review_decision": "excluded",
                "source_status": "present",
                "target_table": "none",
                "target_record_id": "",
                "mapping_action": "exclude",
                "mapping_status": "verified",
                "source_document": "doc.pdf",
                "source_page": "1",
                "source_section": "공고 개요",
                "notes": "excluded by review",
            },
            {
                "source_file": "change_history.csv",
                "local_record_id": "CHG-001",
                "parent_record_id": "",
                "review_decision": "reclassified",
                "source_status": "present",
                "target_table": "change_history",
                "target_record_id": "",
                "mapping_action": "insert",
                "mapping_status": "pending_target_id",
                "source_document": "old.pdf → new.pdf",
                "source_page": "7→7",
                "source_section": "요건 > 고용",
                "notes": "change_history.csv:CHG-001 old_value/new_value",
            },
        ],
    )
    return mapping, review, history


def test_clean_mapping_has_no_errors(tmp_path: Path):
    paths = build_files(tmp_path)
    assert validate_mapping(*paths) == []


def test_missing_review_row_is_reported(tmp_path: Path):
    mapping, review, history = build_files(tmp_path)
    with review.open("a", encoding="utf-8") as stream:
        stream.write("REQ-002,,,,,approved\n")
    errors = validate_mapping(mapping, review, history)
    assert any("매핑 누락: REQ-002" in error for error in errors)


def test_history_page_and_reference_are_checked(tmp_path: Path):
    mapping, review, history = build_files(tmp_path)
    rows = list(csv.DictReader(mapping.open(encoding="utf-8")))
    rows[1]["source_page"] = "1→2"
    rows[1]["notes"] = "history only"
    write_csv(mapping, MAPPING_FIELDS, rows)
    errors = validate_mapping(mapping, review, history)
    assert any("CHG-001의 source_page가 history와 다름" in error for error in errors)
    assert any("CHG-001의 history 원문 참조 누락" in error for error in errors)


def test_unexpected_duplicate_mapping_is_reported(tmp_path: Path):
    mapping, review, history = build_files(tmp_path)
    rows = list(csv.DictReader(mapping.open(encoding="utf-8")))
    rows.append(rows[0].copy())
    write_csv(mapping, MAPPING_FIELDS, rows)
    errors = validate_mapping(mapping, review, history)
    assert any("REQ-001의 비허용 중복 매핑" in error for error in errors)
