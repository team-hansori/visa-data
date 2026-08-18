"""공통 UUID 생성 스크립트 회귀 테스트."""

from __future__ import annotations

import csv
import json
import uuid
from pathlib import Path

import pytest

from scripts.generate_uuids import UUIDGenerationError, main, prepare_row


VISA_FIELDS = ["visa_id", "visa_code", "visa_name_kr"]
STAGE_FIELDS = ["stage_id", "visa_id", "stage_order", "stage_name"]
DOCUMENT_FIELDS = ["document_requirement_id", "stage_id", "document_name"]


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def test_new_stage_id_is_uuid4_without_writing_by_default(tmp_path: Path):
    path = tmp_path / "visa_process_stages.csv"
    write_csv(path, STAGE_FIELDS, [])

    target, row, is_new = prepare_row(
        "visa_process_stages",
        {"visa_id": "visa-1", "stage_order": 1, "stage_name": "접수"},
        base_dir=tmp_path,
        csv_path=path,
    )

    assert target == path
    assert is_new is True
    assert uuid.UUID(row["stage_id"]).version == 4
    assert read_csv(path) == []


def test_write_appends_document_id_and_preserves_existing_rows(tmp_path: Path, capsys):
    path = tmp_path / "document_requirements.csv"
    existing = {
        "document_requirement_id": str(uuid.uuid4()),
        "stage_id": str(uuid.uuid4()),
        "document_name": "기존 서류",
    }
    write_csv(path, DOCUMENT_FIELDS, [existing])

    result = main(
        [
            "--table",
            "document_requirements",
            "--csv",
            str(path),
            "--base-dir",
            str(tmp_path),
            "--row-json",
            json.dumps({"stage_id": existing["stage_id"], "document_name": "신규 서류"}),
            "--write",
        ]
    )

    assert result == 0
    assert "행 추가 완료" in capsys.readouterr().out
    rows = read_csv(path)
    assert len(rows) == 2
    assert rows[0] == existing
    assert uuid.UUID(rows[1]["document_requirement_id"]).version == 4


def test_existing_visa_code_reuses_id_without_appending(tmp_path: Path):
    path = tmp_path / "visa_requirements.csv"
    existing_id = str(uuid.uuid4())
    write_csv(
        path,
        VISA_FIELDS,
        [{"visa_id": existing_id, "visa_code": "F-4-R", "visa_name_kr": "재외동포"}],
    )

    _, row, is_new = prepare_row(
        "visa_requirements",
        {"visa_code": "F-4-R", "visa_name_kr": "갱신된 이름"},
        base_dir=tmp_path,
        csv_path=path,
    )

    assert row["visa_id"] == existing_id
    assert is_new is False
    assert len(read_csv(path)) == 1


def test_existing_visa_code_rejects_a_different_supplied_id(tmp_path: Path):
    path = tmp_path / "visa_requirements.csv"
    existing_id = str(uuid.uuid4())
    write_csv(
        path,
        VISA_FIELDS,
        [{"visa_id": existing_id, "visa_code": "F-4-R", "visa_name_kr": "재외동포"}],
    )

    with pytest.raises(UUIDGenerationError, match="이미 발급된 visa_id와 입력값이 다름"):
        prepare_row(
            "visa_requirements",
            {"visa_id": str(uuid.uuid4()), "visa_code": "F-4-R"},
            base_dir=tmp_path,
            csv_path=path,
        )


def test_duplicate_id_across_tables_is_rejected(tmp_path: Path):
    duplicate_id = str(uuid.uuid4())
    write_csv(
        tmp_path / "visa_requirements.csv",
        VISA_FIELDS,
        [{"visa_id": duplicate_id, "visa_code": "F-4-R", "visa_name_kr": "재외동포"}],
    )
    path = tmp_path / "visa_process_stages.csv"
    write_csv(path, STAGE_FIELDS, [])

    with pytest.raises(UUIDGenerationError, match="이미 사용 중인 stage_id"):
        prepare_row(
            "visa_process_stages",
            {"stage_id": duplicate_id, "visa_id": duplicate_id, "stage_order": 1},
            base_dir=tmp_path,
            csv_path=path,
        )


def test_non_uuid4_and_missing_required_value_are_rejected(tmp_path: Path):
    path = tmp_path / "visa_process_stages.csv"
    write_csv(path, STAGE_FIELDS, [])

    with pytest.raises(UUIDGenerationError, match="UUID v4가 아님"):
        prepare_row(
            "visa_process_stages",
            {"stage_id": "00000000-0000-0000-0000-000000000000", "visa_id": "visa-1"},
            base_dir=tmp_path,
            csv_path=path,
        )

    with pytest.raises(UUIDGenerationError, match="필수 값이 비어 있음: visa_id"):
        prepare_row(
            "visa_process_stages",
            {"stage_name": "접수"},
            base_dir=tmp_path,
            csv_path=path,
        )


def test_invalid_json_returns_nonzero_without_writing(tmp_path: Path, capsys):
    path = tmp_path / "visa_requirements.csv"
    write_csv(path, VISA_FIELDS, [])

    result = main(
        [
            "--table",
            "visa_requirements",
            "--csv",
            str(path),
            "--base-dir",
            str(tmp_path),
            "--row-json",
            "[]",
            "--write",
        ]
    )

    assert result == 1
    assert "JSON object여야 함" in capsys.readouterr().err
    assert read_csv(path) == []
