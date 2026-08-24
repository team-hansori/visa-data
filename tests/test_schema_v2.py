"""schema_v2.py(공통 스키마 v2 정의) 회귀 테스트."""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

from scripts import schema_v2
from scripts.schema_v2 import (
    SCHEMA_V2,
    TABLE_ORDER,
    ColumnKind,
    ColumnSpec,
    ForeignKey,
    PopulatedFileExistsError,
    TableSpec,
    generate_empty_csvs,
    write_empty_csv,
)


class TestTableCount:
    def test_exactly_13_tables(self):
        assert len(TABLE_ORDER) == 13
        assert len(SCHEMA_V2) == 13

    def test_table_order_matches_schema_keys(self):
        assert set(TABLE_ORDER) == set(SCHEMA_V2.keys())

    def test_expected_table_names_present(self):
        expected = {
            "source_documents",
            "visa_requirements",
            "visa_criterion_groups",
            "visa_requirement_criteria",
            "visa_scoring_models",
            "visa_scoring_items",
            "visa_process_stages",
            "document_requirements",
            "document_attachment_relations",
            "visa_quota_policies",
            "visa_quota_snapshots",
            "change_history",
            "source_record_mappings",
        }
        assert set(TABLE_ORDER) == expected


class TestLogicalNamesHaveNoCsvSuffix:
    def test_no_table_name_ends_with_csv(self):
        for name, table in SCHEMA_V2.items():
            assert not name.endswith(".csv"), f"{name}에 .csv가 붙어있음"
            assert not table.name.endswith(".csv"), f"{table.name}에 .csv가 붙어있음"

    def test_table_spec_rejects_csv_suffixed_name(self):
        with pytest.raises(ValueError, match=r"\.csv"):
            TableSpec(
                name="visa_requirements.csv",
                pk="visa_id",
                columns=(ColumnSpec("visa_id", ColumnKind.UUID),),
            )

    def test_check_no_csv_suffix_helper_flags_bad_schema(self):
        bad_schema = {
            "visa_requirements": TableSpec(
                name="visa_requirements",
                pk="visa_id",
                columns=(ColumnSpec("visa_id", ColumnKind.UUID),),
            )
        }
        # dict 키 자체에 .csv를 넣어 헬퍼가 키도 검사하는지 확인한다.
        bad_schema["visa_requirements.csv"] = bad_schema.pop("visa_requirements")
        errors = schema_v2.check_no_csv_suffix_in_logical_names(bad_schema)
        assert errors, "키에 .csv가 있는데도 에러가 없음"

    def test_check_no_csv_suffix_helper_passes_real_schema(self):
        assert schema_v2.check_no_csv_suffix_in_logical_names() == []


class TestForbiddenNames:
    def test_real_schema_has_no_forbidden_names(self):
        assert schema_v2.check_no_forbidden_names() == []

    @pytest.mark.parametrize(
        "forbidden_name",
        [
            "visa_round_facts",
            "visa_current_facts",
            "visa_fact_coverage",
            "extraction_status",
            "review_status",
            "consumption_gate",
            "confidence",
        ],
    )
    def test_flags_forbidden_column_name(self, forbidden_name: str):
        tainted_table = TableSpec(
            name="visa_requirements",
            pk="visa_id",
            columns=(
                ColumnSpec("visa_id", ColumnKind.UUID),
                ColumnSpec(forbidden_name, ColumnKind.TEXT, nullable=True),
            ),
        )
        errors = schema_v2.check_no_forbidden_names({"visa_requirements": tainted_table})
        assert any(forbidden_name in e for e in errors)

    def test_flags_forbidden_table_name(self):
        tainted_table = TableSpec(
            name="visa_round_facts",
            pk="id",
            columns=(ColumnSpec("id", ColumnKind.UUID),),
        )
        errors = schema_v2.check_no_forbidden_names({"visa_round_facts": tainted_table})
        assert any("visa_round_facts" in e for e in errors)


class TestColumnSpecValidation:
    def test_enum_column_requires_enum_values(self):
        with pytest.raises(ValueError, match="enum_values"):
            ColumnSpec("boolean_operator", ColumnKind.ENUM)

    def test_fk_column_must_be_uuid_kind(self):
        with pytest.raises(ValueError, match="UUID"):
            ColumnSpec(
                "visa_id",
                ColumnKind.TEXT,
                fk=ForeignKey(table="visa_requirements", column="visa_id"),
            )


class TestTableSpecValidation:
    def test_rejects_duplicate_column_names(self):
        with pytest.raises(ValueError, match="중복"):
            TableSpec(
                name="dup_table",
                pk="id",
                columns=(
                    ColumnSpec("id", ColumnKind.UUID),
                    ColumnSpec("id", ColumnKind.UUID),
                ),
            )

    def test_rejects_pk_not_in_columns(self):
        with pytest.raises(ValueError, match="PK"):
            TableSpec(
                name="orphan_pk",
                pk="missing_id",
                columns=(ColumnSpec("id", ColumnKind.UUID),),
            )

    def test_header_matches_column_order(self):
        table = SCHEMA_V2["visa_requirements"]
        assert table.header[0] == "visa_id"
        assert table.header == [c.name for c in table.columns]

    def test_filename_appends_csv(self):
        table = SCHEMA_V2["visa_requirements"]
        assert table.filename == "visa_requirements.csv"


class TestEmptyCsvGeneration:
    """빈 CSV 골격이 schema_v2.py 정의와 드리프트 없이 정확히 일치하는지 확인한다."""

    def test_generates_13_files(self, tmp_path: Path):
        written = generate_empty_csvs(tmp_path)
        assert len(written) == 13
        for path in written:
            assert path.exists()

    def test_each_generated_header_matches_schema_exactly(self, tmp_path: Path):
        generate_empty_csvs(tmp_path)
        for table_name in TABLE_ORDER:
            table = SCHEMA_V2[table_name]
            path = tmp_path / table.filename
            with path.open(newline="", encoding="utf-8") as f:
                header = next(csv.reader(f))
            assert header == table.header, (
                f"{table.filename} 헤더 드리프트: {header} != {table.header}"
            )

    def test_generated_files_have_no_data_rows(self, tmp_path: Path):
        generate_empty_csvs(tmp_path)
        for table_name in TABLE_ORDER:
            table = SCHEMA_V2[table_name]
            path = tmp_path / table.filename
            with path.open(newline="", encoding="utf-8") as f:
                rows = list(csv.reader(f))
            assert len(rows) == 1, f"{table.filename}에 헤더 외 행이 있음: {rows}"

    def test_filenames_have_csv_extension_on_disk_only(self, tmp_path: Path):
        written = generate_empty_csvs(tmp_path)
        names = {p.name for p in written}
        for table_name in TABLE_ORDER:
            assert f"{table_name}.csv" in names


class TestDestructiveOverwriteProtection:
    """Finding 1 — 데이터가 있는 v2 CSV를 실수로 헤더만 남기고 덮어쓰지 못하게 막는다."""

    def test_empty_or_nonexistent_directory_does_not_require_force(self, tmp_path: Path):
        # 디렉터리가 비어 있거나 아직 없으면 --force 없이도 정상적으로 생성된다.
        written = generate_empty_csvs(tmp_path)
        assert len(written) == 13

    def test_write_empty_csv_refuses_populated_file_without_force(self, tmp_path: Path):
        table = SCHEMA_V2["visa_requirements"]
        path = tmp_path / table.filename
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(table.header)
            writer.writerow(["x"] * len(table.header))  # 데이터 행 1개

        with pytest.raises(PopulatedFileExistsError):
            write_empty_csv(table, tmp_path)

        # 거부됐으므로 원본 데이터 행이 그대로 남아 있어야 한다.
        with path.open(newline="", encoding="utf-8") as f:
            rows = list(csv.reader(f))
        assert len(rows) == 2, "거부된 쓰기가 실제로 파일을 건드리면 안 됨"

    def test_write_empty_csv_force_overrides_refusal(self, tmp_path: Path):
        table = SCHEMA_V2["visa_requirements"]
        path = tmp_path / table.filename
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(table.header)
            writer.writerow(["x"] * len(table.header))

        write_empty_csv(table, tmp_path, force=True)

        with path.open(newline="", encoding="utf-8") as f:
            rows = list(csv.reader(f))
        assert rows == [table.header], "force=True면 헤더만 남기고 덮어써야 함"

    def test_generate_empty_csvs_refuses_when_any_table_is_populated(self, tmp_path: Path):
        # 13개 중 1개만 데이터가 있어도 전체를 거부하고 아무 파일도 건드리지 않는다.
        populated_table = SCHEMA_V2["visa_scoring_items"]
        populated_path = tmp_path / populated_table.filename
        populated_path.parent.mkdir(parents=True, exist_ok=True)
        with populated_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(populated_table.header)
            writer.writerow(["x"] * len(populated_table.header))

        untouched_table = SCHEMA_V2["visa_requirements"]
        untouched_path = tmp_path / untouched_table.filename
        with untouched_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(untouched_table.header)
            writer.writerow(["y"] * len(untouched_table.header))

        with pytest.raises(PopulatedFileExistsError):
            generate_empty_csvs(tmp_path)

        with untouched_path.open(newline="", encoding="utf-8") as f:
            rows = list(csv.reader(f))
        assert len(rows) == 2, "거부 시 다른 파일도 건드리면 안 됨(all-or-nothing)"

    def test_generate_empty_csvs_force_overrides_all(self, tmp_path: Path):
        populated_table = SCHEMA_V2["visa_scoring_items"]
        populated_path = tmp_path / populated_table.filename
        populated_path.parent.mkdir(parents=True, exist_ok=True)
        with populated_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(populated_table.header)
            writer.writerow(["x"] * len(populated_table.header))

        written = generate_empty_csvs(tmp_path, force=True)
        assert len(written) == 13
        with populated_path.open(newline="", encoding="utf-8") as f:
            rows = list(csv.reader(f))
        assert rows == [populated_table.header]
