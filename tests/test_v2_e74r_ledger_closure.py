"""Issue #44 E-7-4R 2단계 이관 장부와 변경이력 provenance를 고정한다."""

from __future__ import annotations

import csv
from pathlib import Path
from uuid import UUID


COMMON = Path("extraction/common_v2")
E74 = Path("extraction/B_E-7-4R")
VISA_ID = "346834f7-ac6e-4958-8e0d-8c2b4fb03a7e"

REVIEW_SOURCE_IDS = {
    "REQ-006",
    "REQ-007",
    "REQ-008",
    "REQ-009",
    "REQ-010",
    "REQ-011",
    "REQ-012",
    "REQ-013",
    "REQ-014",
    "REQ-015",
    "REQ-016",
    "REQ-017",
    "REQ-041",
    "REQ-042",
    "REQ-043",
    "REQ-044",
    "REQ-050",
    "REQ-051",
    "REQ-052",
    "REQ-058",
    "REQ-060-01",
    "REQ-063",
    "REQ-066",
    "REQ-067",
    "REQ-068",
    "REQ-070",
    "REQ-071",
    "REQ-073",
    "REQ-077-01",
    "REQ-086",
    "REQ-087",
    "REQ-092",
    "REQ-095-01",
    "REQ-095-02",
    "REQ-095-03",
    "REQ-095-04",
    "REQ-095-05",
    "REQ-103-01",
    "REQ-116",
    "REQ-117",
    "REQ-118",
    "REQ-119",
    "REQ-120",
    "REQ-121",
    "REQ-123",
    "REQ-128",
    "REQ-129",
    "REQ-130",
    "REQ-131",
    "REQ-132",
    "REQ-133",
    "REQ-134",
}
HISTORY_SOURCE_IDS = {f"CHG-{number:03d}" for number in range(1, 18)}
ROUND_DATES = {
    "1": "2026-01-13",
    "2": "2026-02-09",
    "3": "2026-03-03",
    "4": "2026-04-13",
    "5": "2026-05-12",
    "6": "2026-06-09",
    "7": "2026-07-08",
    "8": "2026-08-03",
}


def _rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def _is_uuid4(value: str) -> bool:
    parsed = UUID(value)
    return parsed.version == 4 and str(parsed) == value


MAPPINGS = _rows(COMMON / "source_record_mappings.csv")
E74_MAPPINGS = [row for row in MAPPINGS if row["source_dataset"] == "B_E-7-4R"]


def _mapping_rows(source_table: str, source_id: str) -> list[dict[str, str]]:
    return [
        row
        for row in E74_MAPPINGS
        if row["source_table"] == source_table and row["source_record_id"] == source_id
    ]


def _mapped_targets(source_table: str, source_id: str) -> set[str]:
    return {
        row["target_record_id"]
        for row in _mapping_rows(source_table, source_id)
        if row["mapping_status"] == "MAPPED"
    }


def test_all_69_second_phase_rows_are_closed_without_forcing_the_parser_fragment():
    assert len(REVIEW_SOURCE_IDS) + len(HISTORY_SOURCE_IDS) == 69
    assert not [row for row in E74_MAPPINGS if row["mapping_status"] == "PENDING"]

    for source_id in REVIEW_SOURCE_IDS - {"REQ-041"}:
        rows = _mapping_rows("_review_current_requirements", source_id)
        assert rows
        assert all(row["mapping_status"] == "MAPPED" for row in rows)
        assert all(row["target_record_id"] for row in rows)
        assert all(row["source_group_path"] for row in rows)

    blocked = _mapping_rows("_review_current_requirements", "REQ-041")
    assert len(blocked) == 1
    assert blocked[0]["mapping_status"] == "BLOCKED"
    assert blocked[0]["mapping_action"] == "MANUAL_REVIEW"
    assert blocked[0]["target_record_id"] == ""
    assert "'① |'" in blocked[0]["blocking_reason"]
    assert "target" in blocked[0]["blocking_reason"]

    for source_id in HISTORY_SOURCE_IDS:
        rows = _mapping_rows("change_history", source_id)
        assert len(rows) == 1
        assert rows[0]["mapping_status"] == "MAPPED"
        assert rows[0]["mapping_action"] == "COPY"
        assert rows[0]["source_group_path"]

    phase_rows = [
        row
        for row in E74_MAPPINGS
        if (
            row["source_table"] == "_review_current_requirements"
            and row["source_record_id"] in REVIEW_SOURCE_IDS
        )
        or (
            row["source_table"] == "change_history"
            and row["source_record_id"] in HISTORY_SOURCE_IDS
        )
    ]
    mapping_ids = [row["mapping_id"] for row in phase_rows]
    assert len(mapping_ids) == len(set(mapping_ids))
    assert all(_is_uuid4(mapping_id) for mapping_id in mapping_ids)


def test_one_to_many_and_corrected_tree_mappings_are_exact():
    expected_targets = {
        ("_review_current_requirements", "REQ-042"): {
            "5a84d51e-9635-4164-a497-aeb952b7bf90",
            "48fb7175-1356-47c4-aecd-d468162aa5fc",
            "ced36df4-ed05-4a36-98bc-06943f7bcd4c",
            "2e10a5b1-bcb1-4e0e-b5e1-7bf7856482ba",
            "0e9e8a81-1fdd-41b4-90ac-cc772aa2e3dc",
            "5a4de849-3ff8-4e12-b8a8-21264e9219ab",
            "a084d738-2223-4a02-b75f-488a6fbf0179",
        },
        ("_review_current_requirements", "REQ-050"): {
            "8342bb1c-8fb3-41f9-b1bd-7397f03a9e8f",
            "a943a8ad-fc2a-4330-8cb5-19db555733ed",
            "1eb4aaa9-2582-44be-9ca0-88f40f851e1b",
            "6820a916-d072-4170-b97b-facc164ee28e",
            "00c2aa1b-0dab-405d-96a9-6f95f2565928",
            "d8bf2fb6-2083-4717-8b33-4ea41b08c671",
        },
        ("_review_current_requirements", "REQ-103-01"): {
            "17709673-04ed-465c-92e1-d08a2ee8e769",
            "c7fd1b63-c954-4ea5-ad99-269ec5a3c43a",
        },
        ("_review_current_requirements", "REQ-133"): {
            "5b636b06-5984-4191-bdb6-f5b329334329",
            "e51a4dfb-7caa-422c-bfec-b7e77ea70261",
        },
        ("_review_current_requirements", "REQ-020"): {
            "d7958d0a-6990-42c9-9adf-8c296e964690",
            "04fda22d-273f-4b33-992c-4a3f21eba0d6",
            "b59fe87d-8381-45ce-a5a0-72d006815c24",
        },
        ("_review_current_requirements", "REQ-023"): {
            "9992cdb1-92c6-4afc-89b6-e0396b4490fe",
            "7cbc0463-4015-4090-9576-9724140f5e2c",
            "42bcc8f9-aef5-48eb-9482-522e1e543a48",
            "4dce9e8b-e1c5-4f14-9f5e-ec7739c59553",
            "a07e2faa-99a8-4369-bf96-f130ec619878",
        },
        ("_review_current_requirements", "REQ-107"): {
            "2a85408f-1106-4c54-952f-f94ee5dbbc42",
            "77962498-e4fb-42ff-a139-3242bb57fee9",
        },
        ("current_requirements", "REQ-116"): {
            "cecbc5cf-ab3a-4eb4-8e55-1a08fcb9a6c3",
            "dd46b60f-26c0-4c58-8210-3f3edb0b648a",
        },
        ("current_requirements", "REQ-117"): {
            "164c975e-67e7-431f-85c7-79540f6b00e5",
            "9fd21a9d-2954-4f09-a17f-eb975814bb63",
        },
    }
    for source, targets in expected_targets.items():
        assert _mapped_targets(*source) == targets
        assert all(row["target_table"] != "visa_criterion_groups" for row in _mapping_rows(*source))

    derived_group_ids = {
        "79f1794b-dcf2-472d-b001-776ed4088ad2",
        "f9eb5fd2-1825-4366-82d8-45c5b9cae00d",
        "3f8af0eb-ffd5-4b0e-8877-7f424fcd548d",
        "61a2a314-f99a-489b-95ff-30510b1fb76f",
        "a2c9444a-7e94-45ab-9eb3-4873e12300f9",
        "ca7f7555-b3b9-4d78-bcf2-be09770746cf",
        "cad28668-116b-4503-a506-b48359394abb",
        "2981ee98-d912-49fe-a300-d0b61233b9eb",
        "81b7cdeb-ec7b-4a50-adee-e5d9e58143bf",
    }
    assert not [row for row in E74_MAPPINGS if row["target_record_id"] in derived_group_ids]


def test_second_phase_mapped_targets_exist_and_new_rows_have_real_sources():
    target_pk = {
        "visa_requirements": ("visa_requirements.csv", "visa_id"),
        "visa_process_stages": ("visa_process_stages.csv", "stage_id"),
        "visa_scoring_models": ("visa_scoring_models.csv", "score_model_id"),
        "visa_scoring_items": ("visa_scoring_items.csv", "scoring_item_id"),
        "visa_requirement_criteria": (
            "visa_requirement_criteria.csv",
            "criteria_id",
        ),
        "change_history": ("change_history.csv", "change_id"),
        "document_attachment_relations": (
            "document_attachment_relations.csv",
            "relation_id",
        ),
    }
    ids_by_table = {
        table: {row[pk] for row in _rows(COMMON / filename)}
        for table, (filename, pk) in target_pk.items()
    }
    phase_sources = REVIEW_SOURCE_IDS | HISTORY_SOURCE_IDS
    for row in E74_MAPPINGS:
        if row["source_record_id"] not in phase_sources:
            continue
        if row["mapping_status"] != "MAPPED":
            continue
        assert row["target_record_id"] in ids_by_table[row["target_table"]]

    criteria = {row["criteria_id"]: row for row in _rows(COMMON / "visa_requirement_criteria.csv")}
    directly_supported = {
        "REQ-131": "f2dc4707-ea40-42d8-ac4a-dacacdd6d48b",
        "REQ-134": "ccd00ea6-7986-4ffd-bd47-d92e23ec03f5",
    }
    for source_id, criteria_id in directly_supported.items():
        assert _mapped_targets("_review_current_requirements", source_id) == {criteria_id}
        row = criteria[criteria_id]
        assert row["evaluation_mode"] == "INFORMATIONAL"
        assert row["source_document_id"]
        assert row["source_page"] == "11"


def test_all_17_history_rows_preserve_values_pages_documents_sections_and_dates():
    local_rows = _rows(E74 / "history/change_history.csv")
    assert len(local_rows) == 17
    assert all(None not in row for row in local_rows)
    local = {row["change_id"]: row for row in local_rows}
    migrated = {
        row["change_id"]: row
        for row in _rows(COMMON / "change_history.csv")
        if row["visa_id"] == VISA_ID
    }
    assert len(migrated) == 17
    assert all(_is_uuid4(change_id) for change_id in migrated)

    documents = {row["source_document_id"]: row for row in _rows(COMMON / "source_documents.csv")}
    for source_id, source in local.items():
        mapping = _mapping_rows("change_history", source_id)[0]
        target = migrated[mapping["target_record_id"]]
        for field in (
            "from_round",
            "to_round",
            "old_value",
            "new_value",
            "change_type",
            "old_source_page",
            "new_source_page",
        ):
            assert target[field] == source[field]
        assert mapping["source_document_id"] in documents
        assert documents[mapping["source_document_id"]]["page_basis"] == "CONVERTED_PDF"
        assert mapping["source_group_path"] in target["description"]
        assert mapping["source_document_id"] in target["description"]
        assert f"source_page={mapping['source_page']}" in target["description"]
        expected_dates = (
            f"source_dates={ROUND_DATES[source['from_round']]}→{ROUND_DATES[source['to_round']]}"
        )
        assert expected_dates in target["description"]
        assert f"valid_from={mapping['valid_from']}" in target["description"]
        assert f"valid_to={mapping['valid_to']}" in target["description"]
