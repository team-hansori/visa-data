"""F-2-R 17차 제출서류의 source coverage, 첨부관계, provenance를 고정한다."""

from __future__ import annotations

import csv
from collections import Counter, defaultdict
from pathlib import Path

from scripts.validate_common_schema_v2 import (
    _check_document_attachment_relation_integrity,
)


ROOT = Path(__file__).resolve().parents[1]
COMMON_DIR = ROOT / "extraction" / "common_v2"
SOURCE_DIR = ROOT / "extraction" / "A_F-2-R"

F2R_VISA_ID = "a228433b-abe4-4785-8496-3e1cb3d597c1"
ANNOUNCEMENT_SOURCE_ID = "2c892d50-7de9-431f-95f7-c02c7b2a7d76"
ATTACHMENT_SOURCE_ID = "6fe08cb5-96dd-4784-b266-f72d517595fc"
ROUND_17_ID = "6833996f-8110-5836-b1d6-1f94bd249d59"
SCHOOL_RECOMMENDATION_SOURCE_ID = "1dc9c6a3-6581-57c8-ac24-6b8e3a87cc41"
SCHOOL_RECOMMENDATION_TARGET_ID = "6a3802b8-ad3f-48c5-9612-62e6a402d23d"
DOSSIER_SOURCE_ID = "e8d9e3f9-fdbe-5733-a035-3abd4c605ae4"
PILOT_DOCUMENT_IDS = {
    "74d649df-7e93-4767-b297-622227a12b53",
    "3dab1bf8-ba25-4af6-9605-6bd3849079cb",
    "cd1d2c50-feed-479c-b811-5773fb010f30",
    "3751de40-5ee8-4c2d-90c1-afbe8615b2ae",
}
PILOT_RELATION_IDS = {
    "0fa8c1a4-d8d2-4d62-a592-e55d7a16803a",
    "280072ed-534d-4ab5-aefb-a7645e4aad13",
    "48c4fcb7-5898-4784-95be-c2d54b2ea1ad",
    "70ebc8a4-df87-4d1a-96c6-f871b9dfeb4d",
}


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


SOURCE_DOCUMENT_ROWS = _read_rows(SOURCE_DIR / "visa_required_documents.csv")
STAGE_ROWS = _read_rows(COMMON_DIR / "visa_process_stages.csv")
DOCUMENT_ROWS = _read_rows(COMMON_DIR / "document_requirements.csv")
RELATION_ROWS = _read_rows(COMMON_DIR / "document_attachment_relations.csv")
MAPPING_ROWS = _read_rows(COMMON_DIR / "source_record_mappings.csv")

F2R_STAGE_ROWS = [row for row in STAGE_ROWS if row["visa_id"] == F2R_VISA_ID]
F2R_STAGE_IDS = {row["stage_id"] for row in F2R_STAGE_ROWS}
F2R_DOCUMENT_ROWS = [row for row in DOCUMENT_ROWS if row["stage_id"] in F2R_STAGE_IDS]
F2R_DOCUMENT_IDS = {row["document_requirement_id"] for row in F2R_DOCUMENT_ROWS}
F2R_RELATION_ROWS = [row for row in RELATION_ROWS if row["parent_document_id"] in F2R_DOCUMENT_IDS]
F2R_RELATION_IDS = {row["relation_id"] for row in F2R_RELATION_ROWS}
F2R_MAPPING_ROWS = [
    row
    for row in MAPPING_ROWS
    if row["visa_id"] == F2R_VISA_ID and row["source_dataset"] == "A_F-2-R"
]


class TestF2RDocumentSourceCoverage:
    def test_every_source_document_row_is_mapped_once(self):
        direct_mappings = [
            row
            for row in F2R_MAPPING_ROWS
            if row["source_table"] == "visa_required_documents"
            and row["target_table"] == "document_requirements"
        ]
        by_source: dict[str, list[dict[str, str]]] = defaultdict(list)
        for row in direct_mappings:
            by_source[row["source_record_id"]].append(row)

        assert len(SOURCE_DOCUMENT_ROWS) == 45
        assert set(by_source) == {row["document_requirement_id"] for row in SOURCE_DOCUMENT_ROWS}
        assert all(len(rows) == 1 for rows in by_source.values())
        assert Counter(row["mapping_status"] for row in direct_mappings) == {"MAPPED": 45}

        mapped_targets = {rows[0]["target_record_id"] for source_id, rows in by_source.items()}
        assert mapped_targets == F2R_DOCUMENT_IDS

    def test_school_recommendation_uses_the_explicit_page_8_scope(self):
        row = next(
            row
            for row in F2R_MAPPING_ROWS
            if row["source_record_id"] == SCHOOL_RECOMMENDATION_SOURCE_ID
            and row["target_table"] == "document_requirements"
        )
        assert row["mapping_action"] == "TRANSFORM"
        assert row["mapping_status"] == "MAPPED"
        assert row["target_record_id"] == SCHOOL_RECOMMENDATION_TARGET_ID
        assert row["source_document_id"] == ATTACHMENT_SOURCE_ID
        assert row["source_page"] == "8,16"
        assert row["blocking_reason"] == ""
        assert "국내 대학 졸업생 필수 제출" in row["mapping_note"]

        document = next(
            row
            for row in F2R_DOCUMENT_ROWS
            if row["document_requirement_id"] == SCHOOL_RECOMMENDATION_TARGET_ID
        )
        assert document["requirement_status"] == "CONDITIONAL"
        assert document["condition_note"] == "국내 대학 졸업생 필수 제출"
        assert document["source_document_id"] == ATTACHMENT_SOURCE_ID
        assert document["source_page"] == "8,16"

    def test_round_17_has_exact_one_to_many_stage_mappings(self):
        rows = [
            row
            for row in F2R_MAPPING_ROWS
            if row["source_table"] == "visa_announcement_rounds"
            and row["source_record_id"] == ROUND_17_ID
            and row["target_table"] == "visa_process_stages"
        ]
        assert len(rows) == 4
        assert {row["target_record_id"] for row in rows} == F2R_STAGE_IDS
        assert {row["mapping_action"] for row in rows} == {"TRANSFORM"}
        assert {row["mapping_status"] for row in rows} == {"MAPPED"}
        assert all("1:many" in row["mapping_note"] for row in rows)


class TestF2RDocumentSemantics:
    def test_only_source_supported_requirement_statuses_are_created(self):
        assert len(F2R_DOCUMENT_ROWS) == 45
        assert Counter(row["requirement_status"] for row in F2R_DOCUMENT_ROWS) == {
            "REQUIRED": 19,
            "CONDITIONAL": 14,
            "ALTERNATIVE": 12,
        }
        assert all(row["requirement_status"] != "OPTIONAL" for row in F2R_DOCUMENT_ROWS)
        assert all(row["required_status"] != "optional" for row in SOURCE_DOCUMENT_ROWS)

    def test_alternative_groups_and_condition_notes_preserve_source_meaning(self):
        alternatives = [
            row for row in F2R_DOCUMENT_ROWS if row["requirement_status"] == "ALTERNATIVE"
        ]
        assert Counter(row["alternative_group"] for row in alternatives) == {
            "EDUCATION_OR_INCOME": 2,
            "RESIDENCE_PROOF": 3,
            "EXCEPTION_ENTITY_TYPE": 2,
            "SALES_PROOF": 2,
            "LANGUAGE_PROOF": 3,
        }
        assert all(row["condition_note"] for row in alternatives)
        assert all(
            row["condition_note"]
            for row in F2R_DOCUMENT_ROWS
            if row["requirement_status"] == "CONDITIONAL"
        )


class TestF2RAttachmentIntegrity:
    def test_document_stage_fks_belong_to_f2r(self):
        assert {(row["stage_order"], row["stage_code"]) for row in F2R_STAGE_ROWS} == {
            ("1", "NOTICE_PUBLICATION"),
            ("2", "APPLICATION_SUBMISSION"),
            ("3", "RECOMMENDATION_REVIEW"),
            ("4", "STATUS_CHANGE_APPLICATION"),
        }
        assert len(F2R_DOCUMENT_ROWS) == 45
        assert all(row["stage_id"] in F2R_STAGE_IDS for row in F2R_DOCUMENT_ROWS)

    def test_dossier_relations_have_valid_fks_and_no_cycle(self):
        document_by_id = {row["document_requirement_id"]: row for row in F2R_DOCUMENT_ROWS}
        dossier = next(
            row for row in F2R_DOCUMENT_ROWS if row["document_name"] == "시·군 제출서류 일체"
        )
        city_stage_id = next(
            row["stage_id"]
            for row in F2R_STAGE_ROWS
            if row["stage_code"] == "APPLICATION_SUBMISSION"
        )

        assert len(F2R_RELATION_ROWS) == 35
        assert {row["parent_document_id"] for row in F2R_RELATION_ROWS} == {
            dossier["document_requirement_id"]
        }
        assert all(row["attachment_document_id"] in document_by_id for row in F2R_RELATION_ROWS)
        assert all(
            document_by_id[row["attachment_document_id"]]["stage_id"] == city_stage_id
            for row in F2R_RELATION_ROWS
        )
        assert (
            _check_document_attachment_relation_integrity(
                {"document_attachment_relations": RELATION_ROWS}
            )
            == []
        )

    def test_each_relation_has_two_source_rows_merged_into_one_target(self):
        direct_document_mappings = {
            row["target_record_id"]: row["source_record_id"]
            for row in F2R_MAPPING_ROWS
            if row["target_table"] == "document_requirements" and row["mapping_status"] == "MAPPED"
        }
        by_relation: dict[str, list[dict[str, str]]] = defaultdict(list)
        for row in F2R_MAPPING_ROWS:
            if row["target_record_id"] in F2R_RELATION_IDS:
                by_relation[row["target_record_id"]].append(row)

        assert set(by_relation) == F2R_RELATION_IDS
        assert all(len(rows) == 2 for rows in by_relation.values())
        assert all(
            {row["mapping_action"] for row in rows} == {"MERGE"} for rows in by_relation.values()
        )
        for relation in F2R_RELATION_ROWS:
            source_ids = {row["source_record_id"] for row in by_relation[relation["relation_id"]]}
            assert source_ids == {
                DOSSIER_SOURCE_ID,
                direct_document_mappings[relation["attachment_document_id"]],
            }

        dossier_targets = {
            row["target_record_id"]
            for row in F2R_MAPPING_ROWS
            if row["source_record_id"] == DOSSIER_SOURCE_ID
            and row["target_table"] == "document_attachment_relations"
        }
        assert dossier_targets == F2R_RELATION_IDS


class TestF2RDocumentProvenance:
    def test_migrated_documents_preserve_page_and_applicable_period(self):
        round_rows = [
            row
            for row in F2R_DOCUMENT_ROWS
            if row["document_requirement_id"] != SCHOOL_RECOMMENDATION_TARGET_ID
        ]
        assert all(row["source_document_id"] == ANNOUNCEMENT_SOURCE_ID for row in round_rows)
        assert all(row["source_page"] == "9" for row in round_rows)

        pilot_rows = [
            row for row in F2R_DOCUMENT_ROWS if row["document_requirement_id"] in PILOT_DOCUMENT_IDS
        ]
        period_round_rows = [
            row
            for row in F2R_DOCUMENT_ROWS
            if row["document_requirement_id"] not in PILOT_DOCUMENT_IDS
        ]
        assert len(pilot_rows) == 4
        assert all(row["valid_from"] == "2026-05-18" for row in pilot_rows)
        assert all(row["valid_to"] == "2027-12-31" for row in pilot_rows)
        assert all(row["valid_from"] == "2026-08-03" for row in period_round_rows)
        assert all(row["valid_to"] == "2026-09-18" for row in period_round_rows)
        assert all(row["last_verified_at"] == "2026-08-25" for row in round_rows)

    def test_attachment_relations_preserve_page_and_attachment_period(self):
        assert all(row["source_document_id"] == ANNOUNCEMENT_SOURCE_ID for row in F2R_RELATION_ROWS)
        assert all(row["source_page"] == "9" for row in F2R_RELATION_ROWS)

        pilot_rows = [row for row in F2R_RELATION_ROWS if row["relation_id"] in PILOT_RELATION_IDS]
        round_rows = [
            row for row in F2R_RELATION_ROWS if row["relation_id"] not in PILOT_RELATION_IDS
        ]
        assert len(pilot_rows) == 4
        assert all(row["valid_from"] == "2026-05-18" for row in pilot_rows)
        assert all(row["valid_to"] == "2027-12-31" for row in pilot_rows)
        assert all(row["valid_from"] == "2026-08-03" for row in round_rows)
        assert all(row["valid_to"] == "2026-09-18" for row in round_rows)
