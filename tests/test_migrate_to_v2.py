"""검수 완료된 공통 v2 스냅샷 재생성 진입점 테스트."""

from __future__ import annotations

import csv
import hashlib
import shutil
from pathlib import Path

import pytest

from scripts.migrate_to_v2 import (
    DEFAULT_BASELINE_PATH,
    SnapshotBuildError,
    SnapshotOutputExistsError,
    UnsafeSnapshotPathError,
    build_snapshot,
)
from scripts.schema_v2 import SCHEMA_V2, TABLE_ORDER
from scripts.validate_common_schema_v2 import validate_directory

COMMON_V2_DIR = Path("extraction/common_v2")


def _file_hashes(base_dir: Path) -> dict[str, str]:
    return {
        SCHEMA_V2[name].filename: hashlib.sha256(
            (base_dir / SCHEMA_V2[name].filename).read_bytes()
        ).hexdigest()
        for name in TABLE_ORDER
    }


def _baseline_errors() -> set[str]:
    return {
        line.strip()
        for line in DEFAULT_BASELINE_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    }


class TestBuildReviewedSnapshot:
    def test_materializes_all_13_tables_with_same_rows(self, tmp_path: Path):
        output_dir = tmp_path / "common_v2"

        written = build_snapshot(COMMON_V2_DIR, output_dir)

        assert len(written) == len(TABLE_ORDER) == 13
        assert set(validate_directory(output_dir)) == _baseline_errors()
        for name in TABLE_ORDER:
            table = SCHEMA_V2[name]
            source_path = COMMON_V2_DIR / table.filename
            output_path = output_dir / table.filename
            assert output_path in written
            with source_path.open(newline="", encoding="utf-8-sig") as source_stream:
                source_rows = list(csv.DictReader(source_stream))
            with output_path.open(newline="", encoding="utf-8") as output_stream:
                output_rows = list(csv.DictReader(output_stream))
            assert output_rows == source_rows
            assert b"\r\n" not in output_path.read_bytes()

    def test_does_not_modify_reviewed_source(self, tmp_path: Path):
        before = _file_hashes(COMMON_V2_DIR)

        build_snapshot(COMMON_V2_DIR, tmp_path / "output")

        assert _file_hashes(COMMON_V2_DIR) == before

    def test_two_clean_builds_are_byte_identical(self, tmp_path: Path):
        first = tmp_path / "first"
        second = tmp_path / "second"

        build_snapshot(COMMON_V2_DIR, first)
        build_snapshot(COMMON_V2_DIR, second)

        assert _file_hashes(first) == _file_hashes(second)


class TestSnapshotSafety:
    def test_refuses_source_as_output_even_with_force(self):
        with pytest.raises(UnsafeSnapshotPathError):
            build_snapshot(COMMON_V2_DIR, COMMON_V2_DIR, force=True)

    def test_refuses_nested_output_path(self):
        with pytest.raises(UnsafeSnapshotPathError):
            build_snapshot(COMMON_V2_DIR, COMMON_V2_DIR / "generated")

    def test_existing_output_is_unchanged_without_force(self, tmp_path: Path):
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        sentinel = output_dir / "keep.txt"
        sentinel.write_text("keep", encoding="utf-8")

        with pytest.raises(SnapshotOutputExistsError):
            build_snapshot(COMMON_V2_DIR, output_dir)

        assert sentinel.read_text(encoding="utf-8") == "keep"

    def test_force_replaces_existing_output_only_after_validation(self, tmp_path: Path):
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        (output_dir / "old.txt").write_text("old", encoding="utf-8")

        written = build_snapshot(COMMON_V2_DIR, output_dir, force=True)

        assert len(written) == 13
        assert not (output_dir / "old.txt").exists()
        assert set(validate_directory(output_dir)) == _baseline_errors()

    def test_invalid_source_fails_before_creating_output(self, tmp_path: Path):
        source_dir = tmp_path / "invalid-source"
        output_dir = tmp_path / "output"
        shutil.copytree(COMMON_V2_DIR, source_dir)
        path = source_dir / "visa_requirements.csv"
        lines = path.read_text(encoding="utf-8").splitlines()
        lines[0] = "wrong_header"
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")

        with pytest.raises(SnapshotBuildError):
            build_snapshot(source_dir, output_dir)

        assert not output_dir.exists()
