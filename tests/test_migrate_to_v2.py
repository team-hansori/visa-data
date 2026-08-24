"""migrate_to_v2.py(v1 -> v2 마이그레이션 진입점 스텁) 테스트.

이 태스크 범위에서 migrate()는 실제 행 변환을 하지 않는 스텁이다 — 여기서는 "v1 파일을
읽되 v2 출력에는 스키마 헤더만 정확히 생성되고 v1 파일은 건드리지 않는다"는 계약만
검증한다. 실제 F-4-R/E-7-4R/F-2-R 행 변환 테스트는 해당 마이그레이션 태스크에서 추가한다.
"""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

from scripts.migrate_to_v2 import migrate, read_v1_csv
from scripts.schema_v2 import SCHEMA_V2, TABLE_ORDER, PopulatedFileExistsError


def _write_csv(path: Path, header: list[str], rows: list[dict[str, str]] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=header)
        writer.writeheader()
        for row in rows or []:
            writer.writerow(row)


class TestMigrateStub:
    def test_writes_all_13_v2_tables_with_headers_only(self, tmp_path: Path):
        v1_dir = tmp_path / "v1"
        output_dir = tmp_path / "v2"
        v1_dir.mkdir()

        written = migrate(v1_dir, output_dir)

        assert len(written) == 13
        for name in TABLE_ORDER:
            table = SCHEMA_V2[name]
            path = output_dir / table.filename
            assert path in written
            with path.open(newline="", encoding="utf-8") as f:
                rows = list(csv.reader(f))
            assert rows == [table.header], f"{table.filename}은 헤더만 있어야 함(스텁 범위)"

    def test_missing_v1_dir_does_not_crash(self, tmp_path: Path):
        # v1 디렉터리가 아예 없어도(예: 아직 체크아웃 전) 스텁은 헤더만 생성하며 죽지 않는다.
        v1_dir = tmp_path / "does-not-exist"
        output_dir = tmp_path / "v2"
        written = migrate(v1_dir, output_dir)
        assert len(written) == 13

    def test_does_not_modify_v1_files(self, tmp_path: Path):
        v1_dir = tmp_path / "v1"
        output_dir = tmp_path / "v2"
        v1_path = v1_dir / "visa_requirements.csv"
        original_header = ["visa_id", "visa_code"]
        original_row = {"visa_id": "606d8651-1d04-47fe-8f69-165b3ed3d834", "visa_code": "F-4-R"}
        _write_csv(v1_path, original_header, [original_row])
        before = v1_path.read_text(encoding="utf-8")

        migrate(v1_dir, output_dir)

        after = v1_path.read_text(encoding="utf-8")
        assert before == after, "마이그레이션 스텁이 v1 파일을 건드리면 안 됨"

    def test_read_v1_csv_returns_rows_for_existing_file(self, tmp_path: Path):
        path = tmp_path / "visa_requirements.csv"
        _write_csv(path, ["visa_id", "visa_code"], [{"visa_id": "x", "visa_code": "F-4-R"}])
        rows = read_v1_csv(path)
        assert rows == [{"visa_id": "x", "visa_code": "F-4-R"}]

    def test_read_v1_csv_returns_empty_list_for_missing_file(self, tmp_path: Path):
        assert read_v1_csv(tmp_path / "does-not-exist.csv") == []

    def test_output_headers_match_schema_exactly_even_when_v1_has_different_columns(
        self, tmp_path: Path
    ):
        # v1 visa_requirements.csv는 v2와 컬럼이 다르다(예: total_score_threshold,
        # quota_type 등 제거 대상 컬럼 포함) — 스텁은 v1 헤더를 베끼지 않고 schema_v2.py
        # 정의를 그대로 쓴다는 것을 확인한다.
        v1_dir = tmp_path / "v1"
        output_dir = tmp_path / "v2"
        _write_csv(
            v1_dir / "visa_requirements.csv",
            [
                "visa_id",
                "visa_code",
                "total_score_threshold",  # v2에서 제거된 v1 전용 컬럼
                "quota_type",
                "total_quota",
            ],
        )

        migrate(v1_dir, output_dir)

        v2_header = SCHEMA_V2["visa_requirements"].header
        with (output_dir / "visa_requirements.csv").open(newline="", encoding="utf-8") as f:
            written_header = next(csv.reader(f))
        assert written_header == v2_header
        assert "total_score_threshold" not in written_header
        assert "quota_type" not in written_header


class TestMigrateDestructiveOverwriteProtection:
    """Finding 1 — output_dir(기본값 extraction/common_v2/)에 이미 데이터가 있으면
    migrate()가 --force 없이 헤더만 남기고 덮어쓰지 않는다."""

    def test_refuses_when_output_dir_has_populated_v2_csv(self, tmp_path: Path):
        v1_dir = tmp_path / "v1"
        output_dir = tmp_path / "v2"
        v1_dir.mkdir()
        table = SCHEMA_V2["visa_requirements"]
        _write_csv(
            output_dir / table.filename,
            table.header,
            [dict.fromkeys(table.header, "x")],
        )

        with pytest.raises(PopulatedFileExistsError):
            migrate(v1_dir, output_dir)

        with (output_dir / table.filename).open(newline="", encoding="utf-8") as f:
            rows = list(csv.reader(f))
        assert len(rows) == 2, "거부됐다면 기존 데이터 행이 그대로 남아 있어야 함"

    def test_force_overrides_refusal(self, tmp_path: Path):
        v1_dir = tmp_path / "v1"
        output_dir = tmp_path / "v2"
        v1_dir.mkdir()
        table = SCHEMA_V2["visa_requirements"]
        _write_csv(
            output_dir / table.filename,
            table.header,
            [dict.fromkeys(table.header, "x")],
        )

        written = migrate(v1_dir, output_dir, force=True)

        assert len(written) == 13
        with (output_dir / table.filename).open(newline="", encoding="utf-8") as f:
            rows = list(csv.reader(f))
        assert rows == [table.header]
