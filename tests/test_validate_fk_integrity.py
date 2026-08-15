"""FK/PK 무결성 검증 스크립트(validate_fk_integrity.py) 회귀 테스트."""

from __future__ import annotations

import csv
from pathlib import Path

from scripts.validate_fk_integrity import (
    TableSpec,
    check_document_requirements_status,
    check_fk_integrity,
    check_pk_uniqueness,
    check_required_columns,
    collect_pk_sets,
    read_fieldnames,
    read_rows,
    validate,
)


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


class TestCheckPkUniqueness:
    def test_no_errors_when_all_pks_unique(self, tmp_path: Path):
        path = tmp_path / "parent.csv"
        rows = [{"id": "a"}, {"id": "b"}]
        table = TableSpec(path, pk="id")
        assert check_pk_uniqueness(table, rows) == []

    def test_flags_duplicate_pk(self, tmp_path: Path):
        path = tmp_path / "parent.csv"
        rows = [{"id": "a"}, {"id": "a"}]
        table = TableSpec(path, pk="id")
        errors = check_pk_uniqueness(table, rows)
        assert len(errors) == 1
        assert "id=a 중복 2회" in errors[0]

    def test_flags_empty_pk(self, tmp_path: Path):
        path = tmp_path / "parent.csv"
        rows = [{"id": ""}]
        table = TableSpec(path, pk="id")
        errors = check_pk_uniqueness(table, rows)
        assert len(errors) == 1
        assert "비어 있음" in errors[0]

    def test_skips_check_when_no_pk_defined(self, tmp_path: Path):
        path = tmp_path / "log.csv"
        rows = [{"id": "a"}, {"id": "a"}]
        table = TableSpec(path, pk=None)
        assert check_pk_uniqueness(table, rows) == []


class TestCheckFkIntegrity:
    def test_no_errors_when_fk_resolves(self, tmp_path: Path):
        parent_path = tmp_path / "parent.csv"
        child = TableSpec(
            tmp_path / "child.csv", pk="child_id", fks={"parent_id": parent_path}
        )
        rows = [{"child_id": "c1", "parent_id": "p1"}]
        pk_sets = {parent_path: {"p1"}}
        assert check_fk_integrity(child, rows, pk_sets) == []

    def test_flags_fk_pointing_to_missing_parent(self, tmp_path: Path):
        parent_path = tmp_path / "parent.csv"
        child = TableSpec(
            tmp_path / "child.csv", pk="child_id", fks={"parent_id": parent_path}
        )
        rows = [{"child_id": "c1", "parent_id": "does-not-exist"}]
        pk_sets = {parent_path: {"p1"}}
        errors = check_fk_integrity(child, rows, pk_sets)
        assert len(errors) == 1
        assert "parent_id=does-not-exist" in errors[0]
        assert str(parent_path) in errors[0]

    def test_flags_empty_fk(self, tmp_path: Path):
        parent_path = tmp_path / "parent.csv"
        child = TableSpec(
            tmp_path / "child.csv", pk="child_id", fks={"parent_id": parent_path}
        )
        rows = [{"child_id": "c1", "parent_id": ""}]
        pk_sets = {parent_path: {"p1"}}
        errors = check_fk_integrity(child, rows, pk_sets)
        assert len(errors) == 1
        assert "비어 있음" in errors[0]


class TestReadRows:
    def test_returns_empty_list_for_missing_file(self, tmp_path: Path):
        assert read_rows(tmp_path / "missing.csv") == []

    def test_returns_empty_list_for_header_only_file(self, tmp_path: Path):
        path = tmp_path / "empty.csv"
        write_csv(path, ["id"], [])
        assert read_rows(path) == []


class TestCollectPkSets:
    def test_collects_pk_values_across_tables(self, tmp_path: Path):
        parent_path = tmp_path / "parent.csv"
        write_csv(parent_path, ["id"], [{"id": "p1"}, {"id": "p2"}])
        table = TableSpec(parent_path, pk="id")
        pk_sets = collect_pk_sets([table])
        assert pk_sets[parent_path] == {"p1", "p2"}


class TestValidateEndToEnd:
    def _build_chain(self, tmp_path: Path) -> tuple[Path, Path, Path]:
        """visa_requirements -> visa_process_stages -> document_requirements 3단 체인을 만든다."""
        visa_requirements = tmp_path / "visa_requirements.csv"
        visa_process_stages = tmp_path / "visa_process_stages.csv"
        document_requirements = tmp_path / "document_requirements.csv"

        write_csv(visa_requirements, ["visa_id"], [{"visa_id": "V1"}])
        write_csv(
            visa_process_stages,
            ["stage_id", "visa_id"],
            [{"stage_id": "S1", "visa_id": "V1"}],
        )
        write_csv(
            document_requirements,
            ["document_requirement_id", "stage_id"],
            [{"document_requirement_id": "D1", "stage_id": "S1"}],
        )
        return visa_requirements, visa_process_stages, document_requirements

    def test_clean_chain_has_no_errors(self, tmp_path: Path):
        visa_requirements, visa_process_stages, document_requirements = self._build_chain(
            tmp_path
        )
        tables = [
            TableSpec(visa_requirements, pk="visa_id"),
            TableSpec(visa_process_stages, pk="stage_id", fks={"visa_id": visa_requirements}),
            TableSpec(
                document_requirements,
                pk="document_requirement_id",
                fks={"stage_id": visa_process_stages},
            ),
        ]
        assert validate(tables) == []

    def test_dangling_stage_id_is_caught(self, tmp_path: Path):
        visa_requirements, visa_process_stages, document_requirements = self._build_chain(
            tmp_path
        )
        # document_requirements가 존재하지 않는 stage_id를 가리키도록 덮어쓴다.
        write_csv(
            document_requirements,
            ["document_requirement_id", "stage_id"],
            [{"document_requirement_id": "D1", "stage_id": "does-not-exist"}],
        )
        tables = [
            TableSpec(visa_requirements, pk="visa_id"),
            TableSpec(visa_process_stages, pk="stage_id", fks={"visa_id": visa_requirements}),
            TableSpec(
                document_requirements,
                pk="document_requirement_id",
                fks={"stage_id": visa_process_stages},
            ),
        ]
        errors = validate(tables)
        assert len(errors) == 1
        assert "stage_id=does-not-exist" in errors[0]

    def test_missing_files_are_skipped_without_crashing(self, tmp_path: Path):
        tables = [TableSpec(tmp_path / "missing.csv", pk="id")]
        assert validate(tables) == []


class TestCheckRequiredColumns:
    def test_no_errors_when_pk_and_fk_columns_present(self):
        table = TableSpec(Path("child.csv"), pk="child_id", fks={"parent_id": Path("p.csv")})
        assert check_required_columns(table, ["child_id", "parent_id"]) == []

    def test_flags_missing_pk_column(self):
        table = TableSpec(Path("child.csv"), pk="child_id")
        errors = check_required_columns(table, ["other_column"])
        assert len(errors) == 1
        assert "child_id" in errors[0]
        assert "child.csv" in errors[0]

    def test_flags_missing_fk_column(self):
        table = TableSpec(Path("child.csv"), pk="child_id", fks={"parent_id": Path("p.csv")})
        errors = check_required_columns(table, ["child_id"])
        assert len(errors) == 1
        assert "parent_id" in errors[0]


class TestReadFieldnames:
    def test_returns_none_for_missing_file(self, tmp_path: Path):
        assert read_fieldnames(tmp_path / "missing.csv") is None

    def test_returns_header_for_existing_file(self, tmp_path: Path):
        path = tmp_path / "t.csv"
        write_csv(path, ["a", "b"], [{"a": "1", "b": "2"}])
        assert read_fieldnames(path) == ["a", "b"]


class TestValidateCatchesMissingColumns:
    def test_reports_clear_error_instead_of_crashing(self, tmp_path: Path):
        """PK 컬럼 자체가 헤더에 없는 비어있지 않은 CSV는 KeyError로 죽지 않고
        컬럼 누락을 정확히 짚는 에러 하나만 보고해야 한다(행별 '비어 있음' 에러가
        아니라)."""
        path = tmp_path / "broken.csv"
        write_csv(path, ["not_the_pk_column"], [{"not_the_pk_column": "x"}])
        table = TableSpec(path, pk="id")

        errors = validate([table])

        assert len(errors) == 1
        assert "id" in errors[0]
        assert "헤더에 없음" in errors[0]

    def test_reports_clear_error_for_missing_fk_column(self, tmp_path: Path):
        parent_path = tmp_path / "parent.csv"
        write_csv(parent_path, ["id"], [{"id": "p1"}])
        child_path = tmp_path / "child.csv"
        write_csv(child_path, ["child_id"], [{"child_id": "c1"}])  # parent_id 컬럼 없음

        tables = [
            TableSpec(parent_path, pk="id"),
            TableSpec(child_path, pk="child_id", fks={"parent_id": parent_path}),
        ]
        errors = validate(tables)

        assert len(errors) == 1
        assert "parent_id" in errors[0]
        assert "헤더에 없음" in errors[0]


class TestCheckDocumentRequirementsStatus:
    def test_no_error_when_present_has_matching_document(self, tmp_path: Path):
        stages_path = tmp_path / "visa_process_stages.csv"
        documents_path = tmp_path / "document_requirements.csv"
        write_csv(
            stages_path,
            ["stage_id", "document_requirements_status"],
            [{"stage_id": "S1", "document_requirements_status": "present"}],
        )
        write_csv(
            documents_path,
            ["document_requirement_id", "stage_id"],
            [{"document_requirement_id": "D1", "stage_id": "S1"}],
        )
        assert check_document_requirements_status(stages_path, documents_path) == []

    def test_error_when_present_has_no_matching_document(self, tmp_path: Path):
        stages_path = tmp_path / "visa_process_stages.csv"
        documents_path = tmp_path / "document_requirements.csv"
        write_csv(
            stages_path,
            ["stage_id", "document_requirements_status"],
            [{"stage_id": "S1", "document_requirements_status": "present"}],
        )
        write_csv(documents_path, ["document_requirement_id", "stage_id"], [])

        errors = check_document_requirements_status(stages_path, documents_path)
        assert len(errors) == 1
        assert "present" in errors[0]

    def test_no_error_when_explicitly_none_has_no_document(self, tmp_path: Path):
        stages_path = tmp_path / "visa_process_stages.csv"
        documents_path = tmp_path / "document_requirements.csv"
        write_csv(
            stages_path,
            ["stage_id", "document_requirements_status"],
            [{"stage_id": "S1", "document_requirements_status": "explicitly_none"}],
        )
        write_csv(documents_path, ["document_requirement_id", "stage_id"], [])
        assert check_document_requirements_status(stages_path, documents_path) == []

    def test_error_when_explicitly_none_has_matching_document(self, tmp_path: Path):
        stages_path = tmp_path / "visa_process_stages.csv"
        documents_path = tmp_path / "document_requirements.csv"
        write_csv(
            stages_path,
            ["stage_id", "document_requirements_status"],
            [{"stage_id": "S1", "document_requirements_status": "explicitly_none"}],
        )
        write_csv(
            documents_path,
            ["document_requirement_id", "stage_id"],
            [{"document_requirement_id": "D1", "stage_id": "S1"}],
        )

        errors = check_document_requirements_status(stages_path, documents_path)
        assert len(errors) == 1
        assert "explicitly_none" in errors[0]

    def test_no_error_when_not_checked(self, tmp_path: Path):
        stages_path = tmp_path / "visa_process_stages.csv"
        documents_path = tmp_path / "document_requirements.csv"
        write_csv(
            stages_path,
            ["stage_id", "document_requirements_status"],
            [{"stage_id": "S1", "document_requirements_status": "not_checked"}],
        )
        write_csv(documents_path, ["document_requirement_id", "stage_id"], [])
        assert check_document_requirements_status(stages_path, documents_path) == []

    def test_validate_wires_status_check_in_when_both_tables_present(self, tmp_path: Path):
        stages_path = tmp_path / "visa_process_stages.csv"
        documents_path = tmp_path / "document_requirements.csv"
        write_csv(
            stages_path,
            ["stage_id", "document_requirements_status"],
            [{"stage_id": "S1", "document_requirements_status": "present"}],
        )
        write_csv(documents_path, ["document_requirement_id", "stage_id"], [])

        tables = [
            TableSpec(stages_path, pk="stage_id"),
            TableSpec(documents_path, pk="document_requirement_id"),
        ]
        errors = validate(tables)
        assert len(errors) == 1
        assert "present" in errors[0]
