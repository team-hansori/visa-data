"""Validate the F-2-R source-layer extraction before PR completion.

Run from any directory:
    uv run python scripts/validate_f2r_extraction.py

The script uses only the Python standard library and exits non-zero when a
source locator, schema, review gate, or adjacent-round history rule is broken.
"""

from __future__ import annotations

import csv
import json
import re
import sys
import uuid
from collections import Counter
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "extraction" / "A_F-2-R"
F2R_VISA_ID = "78dca2d7-f771-553a-b788-46c9ff56d633"
SCORING_SOURCE_DOCUMENT_ID = "r09_announcement_2025~2026_a483f5df"
F2R_TARGET_REGIONS = ("제천시", "보은군", "옥천군", "영동군", "괴산군", "단양군")

EXPECTED_FILES = {
    "extraction_review_queue.csv",
    "ingestion_issues.csv",
    "visa_announcement_rounds.csv",
    "visa_change_history.csv",
    "visa_criterion_groups.csv",
    "visa_current_facts.csv",
    "visa_fact_coverage.csv",
    "visa_regional_quotas.csv",
    "visa_required_documents.csv",
    "visa_requirement_criteria.csv",
    "visa_requirements.csv",
    "visa_round_facts.csv",
    "visa_scoring_items.csv",
    "visa_scoring_models.csv",
}
SUPPORT_FILES = {"common_master_mapping.csv"}

MAPPING_COLUMNS = [
    "mapping_id",
    "visa_id",
    "source_table",
    "source_row_id",
    "source_group_id",
    "source_group_path",
    "target_table",
    "target_row_id",
    "mapping_action",
    "target_condition_group",
    "target_condition_operator",
    "source_document_id",
    "source_document_name",
    "source_page",
    "source_page_basis",
    "page_mapping_method",
    "valid_from",
    "valid_to",
    "validity_mapping_method",
    "mapping_status",
    "blocking_reason",
    "recommended_destination",
    "mapping_note",
]

REQUIRED_COLUMNS = {
    "extraction_review_queue.csv": {
        "review_id", "visa_code", "announcement_round", "requirement_type",
        "reason", "source_document_id", "status", "created_at",
    },
    "ingestion_issues.csv": {"issue_id", "issue_type", "severity", "message"},
    "visa_announcement_rounds.csv": {
        "announcement_id", "announcement_round", "source_document_id",
        "source_section", "source_block_index", "source_text",
    },
    "visa_change_history.csv": {
        "change_id", "from_round", "to_round", "source_document_id",
        "source_section", "source_table_index", "source_text",
    },
    "visa_criterion_groups.csv": {
        "group_id", "visa_id", "parent_group_id", "group_key",
        "boolean_operator",
    },
    "visa_current_facts.csv": {
        "current_fact_id", "source_round", "source_document_id", "source_fact_id",
    },
    "visa_fact_coverage.csv": {
        "coverage_id", "announcement_round", "fact_domain", "coverage_status",
    },
    "visa_regional_quotas.csv": {
        "quota_id", "source_document_id", "source_section",
        "source_table_index", "source_text",
    },
    "visa_required_documents.csv": {
        "document_requirement_id", "visa_id", "source_document_id",
        "source_section", "source_block_index", "source_table_index", "source_text",
    },
    "visa_requirement_criteria.csv": {
        "criteria_id", "visa_id", "group_id", "source_document_id",
        "source_section", "source_block_index", "source_table_index", "source_text",
    },
    "visa_requirements.csv": {
        "visa_id", "target_regions_json", "valid_from", "valid_to", "source_document_id",
        "source_section", "source_block_index", "source_text",
    },
    "visa_round_facts.csv": {
        "fact_id", "announcement_round", "source_document_id",
        "source_section", "source_block_index", "source_table_index", "source_text",
    },
    "visa_scoring_items.csv": {
        "scoring_item_id", "score_model_id", "visa_id", "source_round",
        "source_document_id", "source_section", "source_table_index", "raw_text",
        "fill_strategy", "review_status",
    },
    "visa_scoring_models.csv": {
        "score_model_id", "visa_id", "source_round", "source_document_id",
        "source_section", "source_table_index", "source_text", "fill_strategy",
        "review_status",
    },
}

DIRECT_SOURCE_RULES = {
    "visa_announcement_rounds.csv": ("source_text", ("source_block_index",)),
    "visa_change_history.csv": ("source_text", ("source_section", "source_table_index")),
    "visa_regional_quotas.csv": ("source_text", ("source_table_index",)),
    "visa_required_documents.csv": (
        "source_text", ("source_block_index", "source_table_index")
    ),
    "visa_requirement_criteria.csv": (
        "source_text", ("source_block_index", "source_table_index")
    ),
    "visa_requirements.csv": ("source_text", ("source_block_index",)),
    "visa_round_facts.csv": (
        "source_text", ("source_block_index", "source_table_index")
    ),
    "visa_scoring_items.csv": ("raw_text", ("source_table_index",)),
    "visa_scoring_models.csv": ("source_text", ("source_table_index",)),
}

DOCUMENT_ID_RE = re.compile(
    r"^r\d{2}_(announcement|attachment|amendment|other)_.+_[0-9a-f]{8}$"
)


def fail(message: str) -> None:
    raise AssertionError(message)


def read_csv(name: str) -> tuple[list[str], list[dict[str, str]]]:
    path = BASE / name
    with path.open(encoding="utf-8-sig", newline="") as handle:
        physical_rows = list(csv.reader(handle))
    if not physical_rows:
        fail(f"empty CSV: {name}")
    header = physical_rows[0]
    if len(header) != len(set(header)):
        fail(f"duplicate columns: {name}")
    for line_number, row in enumerate(physical_rows[1:], start=2):
        if len(row) != len(header):
            fail(
                f"column count mismatch: {name}:{line_number} "
                f"expected={len(header)} actual={len(row)}"
            )
    with path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    return header, rows


actual_files = {path.name for path in BASE.glob("*.csv")}
allowed_files = EXPECTED_FILES | SUPPORT_FILES
if not EXPECTED_FILES <= actual_files or actual_files - allowed_files:
    fail(
        f"F-2-R CSV set mismatch: missing={sorted(EXPECTED_FILES - actual_files)} "
        f"extra={sorted(actual_files - allowed_files)}"
    )

tables: dict[str, list[dict[str, str]]] = {}
table_headers: dict[str, list[str]] = {}
total_rows = 0
for filename in sorted(EXPECTED_FILES):
    header, rows = read_csv(filename)
    missing = REQUIRED_COLUMNS[filename] - set(header)
    if missing:
        fail(f"missing columns in {filename}: {sorted(missing)}")
    table_headers[filename] = header
    tables[filename] = rows
    total_rows += len(rows)

requirement_rows = tables["visa_requirements.csv"]
if len(requirement_rows) != 1:
    fail(f"unexpected F-2-R requirement master rows: {len(requirement_rows)}")
try:
    target_regions = json.loads(requirement_rows[0]["target_regions_json"])
except json.JSONDecodeError as exc:
    fail(f"invalid target_regions_json: {exc}")
if tuple(target_regions) != F2R_TARGET_REGIONS:
    fail(f"F-2-R target_regions_json content/order mismatch: {target_regions!r}")

direct_source_rows = 0
known_document_ids: set[str] = set()
for filename, (text_column, location_columns) in DIRECT_SOURCE_RULES.items():
    for line_number, row in enumerate(tables[filename], start=2):
        document_id = row["source_document_id"]
        if not DOCUMENT_ID_RE.fullmatch(document_id):
            fail(f"invalid source_document_id: {filename}:{line_number} {document_id!r}")
        if not row["source_section"]:
            fail(f"missing source_section: {filename}:{line_number}")
        if not any(row[column] for column in location_columns):
            fail(f"missing source locator: {filename}:{line_number}")
        if not row[text_column].strip():
            fail(f"missing source text: {filename}:{line_number}")
        known_document_ids.add(document_id)
        direct_source_rows += 1

groups = tables["visa_criterion_groups.csv"]
criteria = tables["visa_requirement_criteria.csv"]
group_by_id = {row["group_id"]: row for row in groups}
group_by_key = {row["group_key"]: row for row in groups}
if len(group_by_id) != len(groups) or len(group_by_key) != len(groups):
    fail("duplicate criterion group identifiers")
for row in groups:
    if row["visa_id"] != F2R_VISA_ID:
        fail(f"unexpected group visa_id: {row['group_key']}")
    parent = row["parent_group_id"]
    if parent and parent not in group_by_id:
        fail(f"missing parent group: {row['group_key']} -> {parent}")
for row in groups:
    ancestry: list[str] = []
    current_group_id = row["group_id"]
    while current_group_id:
        if current_group_id in ancestry:
            cycle_start = ancestry.index(current_group_id)
            cycle_ids = ancestry[cycle_start:] + [current_group_id]
            cycle_keys = [group_by_id[group_id]["group_key"] for group_id in cycle_ids]
            fail(f"criterion group parent cycle: {' -> '.join(cycle_keys)}")
        ancestry.append(current_group_id)
        current_group_id = group_by_id[current_group_id]["parent_group_id"]
for row in criteria:
    if row["visa_id"] != F2R_VISA_ID or row["group_id"] not in group_by_id:
        fail(f"invalid criterion foreign key: {row['criteria_id']}")

criteria_count = Counter(row["group_id"] for row in criteria)
child_count = Counter(row["parent_group_id"] for row in groups if row["parent_group_id"])
for row in groups:
    if row["boolean_operator"] == "OR":
        alternatives = criteria_count[row["group_id"]] + child_count[row["group_id"]]
        if alternatives < 2:
            fail(f"OR group has fewer than two alternatives: {row['group_key']}")
models = tables["visa_scoring_models.csv"]
items = tables["visa_scoring_items.csv"]
if len(models) != 1 or len(items) != 12:
    fail(f"unexpected scoring rows: models={len(models)} items={len(items)}")
model_id = models[0]["score_model_id"]
scoring_rows = models + items
scoring_states = {row["review_status"] for row in scoring_rows}
if scoring_states != {"needs_review"}:
    fail(f"unexpected scoring review states: {sorted(scoring_states)}")

for row in scoring_rows:
    if row["visa_id"] != F2R_VISA_ID:
        fail("unexpected scoring visa_id")
    if row.get("score_model_id") != model_id:
        fail("scoring item points to another model")
    if row["source_round"] != "9":
        fail("scoring source round mismatch")
    if row["source_document_id"] != SCORING_SOURCE_DOCUMENT_ID:
        fail("scoring primary source must be the round-9 announcement")
    if row["fill_strategy"] != "backfilled":
        fail("round-9 scoring data must retain its backfilled provenance")

consumable_scores = [
    row for row in scoring_rows
    if row["review_status"] == "reviewed"
]

reviews = tables["extraction_review_queue.csv"]
if len(reviews) != 4:
    fail(f"unexpected review queue size: {len(reviews)}")
for line_number, row in enumerate(reviews, start=2):
    if row["status"] not in {"open", "resolved", "ignored"}:
        fail(f"invalid review status: line {line_number}")
    if row["visa_code"] != "F-2-R" or row["announcement_round"] != "17":
        fail(f"unexpected review scope: line {line_number}")
    if not row["reason"] or not row["source_document_id"] or not row["created_at"]:
        fail(f"incomplete review row: line {line_number}")
expected_review_types = {
    "applicant_status",
    "employer_capacity",
    "excluded_applicants",
    "scoring_model",
}
review_status_by_type = {row["requirement_type"]: row["status"] for row in reviews}
if set(review_status_by_type) != expected_review_types:
    fail(f"unexpected review types: {sorted(review_status_by_type)}")
for requirement_type in expected_review_types:
    if review_status_by_type[requirement_type] != "open":
        fail(f"domain review gate changed unexpectedly: {requirement_type}")

issues = tables["ingestion_issues.csv"]
if any(row["issue_type"] == "suspicious_filename" for row in issues):
    fail("unresolved suspicious_filename issue remains")
if not any(row["issue_type"] == "cross_document_conflict" for row in issues):
    fail("announcement/guide conflict is not recorded")
if any(row["severity"] not in {"info", "warning", "error"} for row in issues):
    fail("invalid ingestion issue severity")

changes = tables["visa_change_history.csv"]
for line_number, row in enumerate(changes, start=2):
    if int(row["to_round"]) - int(row["from_round"]) != 1:
        fail(f"non-adjacent change history row: line {line_number}")
    if not row["source_document_id"] or not row["source_section"] or not row["source_text"]:
        fail(f"incomplete change-history source: line {line_number}")
pairs = {(row["from_round"], row["to_round"]) for row in changes}
if not {("15", "16"), ("16", "17")} <= pairs or ("15", "17") in pairs:
    fail("latest adjacent-round comparison chain is incomplete")

round_fact_ids = {row["fact_id"] for row in tables["visa_round_facts.csv"]}
for row in tables["visa_current_facts.csv"]:
    if row["source_fact_id"] not in round_fact_ids:
        fail(f"missing source_fact_id: {row['source_fact_id']}")

mapping_header, mappings = read_csv("common_master_mapping.csv")
if mapping_header != MAPPING_COLUMNS:
    fail("common_master_mapping.csv column order/schema mismatch")
if len(mappings) != 68:
    fail(f"unexpected common mapping rows: {len(mappings)}")

mapping_ids: set[str] = set()
source_keys: set[tuple[str, str]] = set()
ready_target_ids: set[str] = set()
for line_number, row in enumerate(mappings, start=2):
    if row["visa_id"] != F2R_VISA_ID:
        fail(f"unexpected mapping visa_id: line {line_number}")
    try:
        parsed_mapping_id = uuid.UUID(row["mapping_id"])
    except ValueError:
        fail(f"invalid mapping_id UUID: line {line_number}")
    if parsed_mapping_id.version != 5:
        fail(f"mapping_id must be deterministic UUID v5: line {line_number}")
    if row["mapping_id"] in mapping_ids:
        fail(f"duplicate mapping_id: line {line_number}")
    mapping_ids.add(row["mapping_id"])

    source_key = (row["source_table"], row["source_row_id"])
    if source_key in source_keys:
        fail(f"duplicate mapping source key: line {line_number}")
    source_keys.add(source_key)

    if not DOCUMENT_ID_RE.fullmatch(row["source_document_id"]):
        fail(f"invalid mapping source_document_id: line {line_number}")
    if not row["source_document_name"] or not row["source_page"].isdigit():
        fail(f"incomplete document-scoped mapping page: line {line_number}")
    if row["source_page_basis"] != "converted_pdf_page":
        fail(f"unexpected mapping page basis: line {line_number}")
    if not row["page_mapping_method"]:
        fail(f"missing mapping page method: line {line_number}")

    try:
        valid_from = date.fromisoformat(row["valid_from"])
        valid_to = date.fromisoformat(row["valid_to"])
    except ValueError:
        fail(f"invalid mapping validity date: line {line_number}")
    if valid_from > valid_to or not row["validity_mapping_method"]:
        fail(f"invalid mapping validity interval: line {line_number}")

    status = row["mapping_status"]
    action = row["mapping_action"]
    if status == "ready":
        if not row["target_table"] or not row["target_row_id"]:
            fail(f"ready mapping lacks target: line {line_number}")
        if row["blocking_reason"]:
            fail(f"ready mapping unexpectedly blocked: line {line_number}")
        if row["source_table"] == "visa_requirement_criteria.csv":
            try:
                parsed_target_id = uuid.UUID(row["target_row_id"])
            except ValueError:
                fail(f"invalid target criteria UUID: line {line_number}")
            if parsed_target_id.version != 4:
                fail(f"new target criteria_id must be UUID v4: line {line_number}")
            if row["target_row_id"] == row["source_row_id"]:
                fail(f"source criteria_id copied to common target: line {line_number}")
            if row["target_row_id"] in ready_target_ids:
                fail(f"duplicate ready target criteria_id: line {line_number}")
            ready_target_ids.add(row["target_row_id"])
    elif status == "blocked":
        if action != "manual_review" or row["target_row_id"]:
            fail(f"blocked mapping must not mint a target row: line {line_number}")
        if not row["blocking_reason"] or not row["recommended_destination"]:
            fail(f"blocked mapping lacks routing information: line {line_number}")
    elif status == "not_applicable":
        if action != "not_applicable" or row["target_table"] or row["target_row_id"]:
            fail(f"not_applicable mapping has a common target: line {line_number}")
        if not row["blocking_reason"] or not row["recommended_destination"]:
            fail(f"not_applicable mapping lacks routing information: line {line_number}")
    else:
        fail(f"invalid mapping status: line {line_number}")

    if row["source_table"] == "visa_requirement_criteria.csv":
        if not row["source_group_id"] or not row["source_group_path"]:
            fail(f"criterion mapping lacks source group lineage: line {line_number}")

expected_source_keys = {
    ("visa_requirements.csv", F2R_VISA_ID),
    *{
        ("visa_requirement_criteria.csv", row["criteria_id"])
        for row in criteria
    },
}
if source_keys != expected_source_keys:
    fail("common mapping does not cover the master row and all source criteria exactly once")

action_counts = Counter(row["mapping_action"] for row in mappings)
status_counts = Counter(row["mapping_status"] for row in mappings)
if action_counts != Counter(
    {"transform": 1, "direct": 14, "manual_review": 42, "not_applicable": 11}
):
    fail(f"unexpected mapping actions: {dict(action_counts)}")
if status_counts != Counter({"ready": 15, "blocked": 42, "not_applicable": 11}):
    fail(f"unexpected mapping statuses: {dict(status_counts)}")

ready_criteria = [
    row for row in mappings
    if row["mapping_status"] == "ready"
    and row["source_table"] == "visa_requirement_criteria.csv"
]
grouped_ready = [row for row in ready_criteria if row["target_condition_group"]]
if len(grouped_ready) != 3 or {
    (row["target_condition_group"], row["target_condition_operator"])
    for row in grouped_ready
} != {("G1", "OR")}:
    fail("only the three language alternatives may use common local OR group G1")
if any(
    row["target_condition_operator"]
    for row in ready_criteria
    if not row["target_condition_group"]
):
    fail("ungrouped common criteria must not carry a condition operator")

result = {
    "result": "PASS",
    "csv_files": len(EXPECTED_FILES),
    "csv_rows": total_rows,
    "direct_source_rows": direct_source_rows,
    "criterion_groups": len(groups),
    "criteria": len(criteria),
    "review_queue": {"rows": len(reviews), "status": dict(Counter(r["status"] for r in reviews))},
    "ingestion_issues": {
        "rows": len(issues),
        "types": dict(Counter(row["issue_type"] for row in issues)),
    },
    "change_history": {"rows": len(changes), "adjacent_only": True},
    "scoring": {
        "source_round": 9,
        "assumed_target_round": 17,
        "source_document_id": models[0]["source_document_id"],
        "consumable_rows": len(consumable_scores),
        "review_status": next(iter(scoring_states)),
        "gate": "blocked_by_review_status",
    },
    "common_mapping": {
        "rows": len(mappings),
        "actions": dict(action_counts),
        "statuses": dict(status_counts),
        "ready_target_criteria": len(ready_target_ids),
        "page_basis": "converted_pdf_page",
    },
}
print(json.dumps(result, ensure_ascii=False, indent=2))
sys.exit(0)
