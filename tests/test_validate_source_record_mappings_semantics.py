import csv
from pathlib import Path

import pytest

from scripts.validate_source_record_mappings import validate_mappings


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _mapping_row(**overrides: str) -> dict[str, str]:
    row = {
        "mapping_id": "mapping-1",
        "visa_id": "visa-main",
        "source_dataset": "D_visa_requirements",
        "source_table": "visa_requirement_criteria",
        "source_record_id": "source-criteria",
        "source_group_path": "",
        "source_document_id": "document-main",
        "source_page": "2",
        "valid_from": "2026-01-01",
        "valid_to": "",
        "target_table": "visa_requirement_criteria",
        "target_record_id": "target-criteria",
        "mapping_action": "COPY",
        "mapping_status": "MAPPED",
        "blocking_reason": "",
        "mapped_at": "2026-08-25",
        "mapping_note": "",
    }
    row.update(overrides)
    return row


def _build_d_fixture(
    tmp_path: Path,
    *,
    source_overrides: dict[str, str] | None = None,
    mapping_overrides: dict[str, str] | None = None,
    document_overrides: dict[str, str] | None = None,
    target_group_overrides: dict[str, str] | None = None,
    target_overrides: dict[str, str] | None = None,
) -> tuple[Path, Path]:
    source_row = {
        "criteria_id": "source-criteria",
        "visa_id": "visa-main",
        "value_text": "decoy-id",
        "source_document": "announcement.pdf p.2",
        "source_page": "2",
        "valid_from": "2026-01-01",
        "valid_to": "",
    }
    source_row.update(source_overrides or {})

    document_row = {
        "source_document_id": "document-main",
        "source_document_key": "announcement-key",
        "visa_id": "visa-main",
        "document_name": "announcement.pdf",
        "source_location": "data/raw/announcement.hwpx",
    }
    document_row.update(document_overrides or {})

    target_group = {"group_id": "target-group", "visa_id": "visa-main"}
    target_group.update(target_group_overrides or {})

    target_row = {
        "criteria_id": "target-criteria",
        "group_id": "target-group",
        "source_document_id": "document-main",
        # 변환 결과의 페이지/날짜가 원천과 달라도 소유 문서가 같으면 허용한다.
        "source_page": "converted-page",
        "valid_from": "2026-02-01",
    }
    target_row.update(target_overrides or {})

    source_root = tmp_path
    v2_dir = tmp_path / "v2"
    _write_csv(
        source_root / "extraction/D_visa_requirements/visa_requirement_criteria.csv",
        [source_row],
    )
    _write_csv(
        source_root / "extraction/D_visa_requirements/visa_requirements.csv",
        [
            {"visa_id": "visa-main", "visa_code": "F-4-R"},
            {"visa_id": "visa-other", "visa_code": "E-7-4R"},
        ],
    )
    _write_csv(
        v2_dir / "visa_requirements.csv",
        [
            {"visa_id": "visa-main", "visa_code": "F-4-R"},
            {"visa_id": "visa-other", "visa_code": "E-7-4R"},
        ],
    )
    _write_csv(v2_dir / "source_documents.csv", [document_row])
    _write_csv(v2_dir / "visa_criterion_groups.csv", [target_group])
    _write_csv(v2_dir / "visa_requirement_criteria.csv", [target_row])
    _write_csv(v2_dir / "source_record_mappings.csv", [_mapping_row(**(mapping_overrides or {}))])
    return source_root, v2_dir


def _build_a_legacy_fixture(
    tmp_path: Path,
    *,
    group_overrides: dict[str, str] | None = None,
    mapping_overrides: dict[str, str] | None = None,
) -> tuple[Path, Path]:
    source_root = tmp_path
    v2_dir = tmp_path / "v2"
    source_group = {
        "group_id": "source-group",
        "visa_id": "legacy-visa",
        "parent_group_id": "",
        "group_key": "root",
    }
    source_group.update(group_overrides or {})

    _write_csv(
        source_root / "extraction/A_F-2-R/visa_requirements.csv",
        [{"visa_id": "legacy-visa", "visa_code": "F-2-R"}],
    )
    _write_csv(
        source_root / "extraction/A_F-2-R/visa_criterion_groups.csv",
        [source_group],
    )
    _write_csv(
        source_root / "extraction/A_F-2-R/visa_requirement_criteria.csv",
        [
            {
                "criteria_id": "source-criteria",
                "visa_id": "legacy-visa",
                "group_id": "source-group",
                "source_document_id": "legacy-document-key",
                "valid_from": "",
                "valid_to": "",
            }
        ],
    )
    _write_csv(
        v2_dir / "visa_requirements.csv",
        [{"visa_id": "visa-main", "visa_code": "F-2-R"}],
    )
    _write_csv(
        v2_dir / "source_documents.csv",
        [
            {
                "source_document_id": "document-main",
                "source_document_key": "legacy-document-key",
                "visa_id": "visa-main",
                "document_name": "F-2-R announcement.pdf",
                "source_location": "data/raw/f2r-announcement.hwpx",
            }
        ],
    )
    _write_csv(
        v2_dir / "visa_criterion_groups.csv",
        [{"group_id": "target-group", "visa_id": "visa-main"}],
    )
    _write_csv(
        v2_dir / "visa_requirement_criteria.csv",
        [
            {
                "criteria_id": "target-criteria",
                "group_id": "target-group",
                "source_document_id": "document-main",
            }
        ],
    )
    mapping = _mapping_row(
        visa_id="visa-main",
        source_dataset="A_F-2-R",
        source_group_path="root",
        source_document_id="document-main",
        source_page="4",
        valid_from="2026-01-01",
    )
    mapping.update(mapping_overrides or {})
    _write_csv(v2_dir / "source_record_mappings.csv", [mapping])
    return source_root, v2_dir


def test_accepts_consistent_mapping_with_distinct_target_page_and_date(tmp_path: Path):
    source_root, v2_dir = _build_d_fixture(tmp_path)

    assert validate_mappings(source_root, v2_dir) == []


def test_accepts_legacy_visa_id_and_missing_optional_source_metadata(tmp_path: Path):
    source_root, v2_dir = _build_a_legacy_fixture(tmp_path)

    assert validate_mappings(source_root, v2_dir) == []


def test_rejects_source_id_found_only_in_non_pk_cell(tmp_path: Path):
    source_root, v2_dir = _build_d_fixture(
        tmp_path,
        mapping_overrides={"source_record_id": "decoy-id"},
    )

    errors = validate_mappings(source_root, v2_dir)

    assert any("criteria_id PK에 없음" in error for error in errors)


@pytest.mark.parametrize(
    ("source_overrides", "mapping_overrides", "target_overrides", "expected"),
    [
        ({"source_document": "unrelated.pdf"}, {}, {}, "source_document 경로"),
        ({"source_page": "3"}, {}, {}, "source_page가 원천 행과 다름"),
        ({"valid_from": "2025-01-01"}, {}, {}, "valid_from이 원천 행과 다름"),
        ({}, {}, {"source_document_id": "document-other"}, "target source_document_id"),
    ],
)
def test_rejects_source_evidence_mismatches(
    tmp_path: Path,
    source_overrides: dict[str, str],
    mapping_overrides: dict[str, str],
    target_overrides: dict[str, str],
    expected: str,
):
    source_root, v2_dir = _build_d_fixture(
        tmp_path,
        source_overrides=source_overrides,
        mapping_overrides=mapping_overrides,
        target_overrides=target_overrides,
    )

    errors = validate_mappings(source_root, v2_dir)

    assert any(expected in error for error in errors)


def test_rejects_source_visa_code_mismatch(tmp_path: Path):
    source_root, v2_dir = _build_d_fixture(
        tmp_path,
        source_overrides={"visa_id": "visa-other"},
    )

    errors = validate_mappings(source_root, v2_dir)

    assert any("원천 visa가 mapping visa와 다름" in error for error in errors)


def test_rejects_target_criterion_owned_by_another_visa(tmp_path: Path):
    source_root, v2_dir = _build_d_fixture(
        tmp_path,
        target_group_overrides={"visa_id": "visa-other"},
    )

    errors = validate_mappings(source_root, v2_dir)

    assert any("target 소유 visa_id가 mapping과 다름" in error for error in errors)


def test_rejects_source_criterion_owned_by_another_group_visa(tmp_path: Path):
    source_root, v2_dir = _build_a_legacy_fixture(
        tmp_path,
        group_overrides={"visa_id": "different-legacy-visa"},
    )

    errors = validate_mappings(source_root, v2_dir)

    assert any("원천 criteria/group 소유 visa_id가 다름" in error for error in errors)


def test_rejects_source_group_path_mismatch(tmp_path: Path):
    source_root, v2_dir = _build_a_legacy_fixture(
        tmp_path,
        mapping_overrides={"source_group_path": "root > wrong"},
    )

    errors = validate_mappings(source_root, v2_dir)

    assert any("source_group_path가 원천 그룹 경로와 다름" in error for error in errors)
