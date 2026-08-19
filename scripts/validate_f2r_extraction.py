"""Validate the F-2-R source-layer extraction before PR completion.

Run from any directory:
    python scripts/validate_f2r_extraction.py

The script uses only the Python standard library and exits non-zero when a
source locator, schema, review gate, or adjacent-round history rule is broken.
"""

from __future__ import annotations

import csv
import json
import re
import sys
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "extraction" / "A_F-2-R"
F2R_VISA_ID = "78dca2d7-f771-553a-b788-46c9ff56d633"

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

REQUIRED_COLUMNS = {
    "extraction_review_queue.csv": {
        "review_id", "requirement_type", "source_document_id",
        "related_source_document_ids_json", "blocking_scope",
        "completion_criteria", "status",
    },
    "ingestion_issues.csv": {"issue_id", "issue_type", "severity", "message"},
    "visa_announcement_rounds.csv": {
        "announcement_id", "announcement_round", "source_document_id",
        "source_section", "source_block_index", "source_text",
    },
    "visa_change_history.csv": {
        "change_id", "from_round", "to_round", "source_document_id",
        "source_section", "source_block_index", "source_table_index",
        "source_locator_type", "source_text",
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
        "visa_id", "valid_from", "valid_to", "source_document_id",
        "source_section", "source_block_index", "source_text",
    },
    "visa_round_facts.csv": {
        "fact_id", "announcement_round", "source_document_id",
        "source_section", "source_block_index", "source_table_index", "source_text",
    },
    "visa_scoring_items.csv": {
        "scoring_item_id", "score_model_id", "visa_id", "source_round",
        "source_document_id", "source_section", "source_table_index", "source_page",
        "source_page_basis", "raw_text", "valid_from", "valid_to", "date_basis",
        "assumed_target_round", "related_source_document_ids_json",
        "inheritance_scope", "applicability_assumption", "consumption_gate",
        "review_completion_criteria", "fill_strategy", "review_status",
    },
    "visa_scoring_models.csv": {
        "score_model_id", "visa_id", "source_round", "source_document_id",
        "source_section", "source_table_index", "source_page", "source_page_basis",
        "source_text", "valid_from", "valid_to", "date_basis",
        "assumed_target_round", "related_source_document_ids_json",
        "inheritance_scope", "applicability_assumption", "consumption_gate",
        "review_completion_criteria", "fill_strategy", "review_status",
    },
}

DIRECT_SOURCE_RULES = {
    "visa_announcement_rounds.csv": ("source_text", ("source_block_index",)),
    "visa_change_history.csv": ("source_text", ("source_block_index",)),
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
if actual_files != EXPECTED_FILES:
    fail(
        f"F-2-R CSV set mismatch: missing={sorted(EXPECTED_FILES - actual_files)} "
        f"extra={sorted(actual_files - EXPECTED_FILES)}"
    )

tables: dict[str, list[dict[str, str]]] = {}
total_rows = 0
for filename in sorted(EXPECTED_FILES):
    header, rows = read_csv(filename)
    missing = REQUIRED_COLUMNS[filename] - set(header)
    if missing:
        fail(f"missing columns in {filename}: {sorted(missing)}")
    tables[filename] = rows
    total_rows += len(rows)

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
for key in ("applicant_status", "education_or_income"):
    if criteria_count[group_by_key[key]["group_id"]] != 0:
        fail(f"flattened criteria remain directly under {key}")

models = tables["visa_scoring_models.csv"]
items = tables["visa_scoring_items.csv"]
if len(models) != 1 or len(items) != 12:
    fail(f"unexpected scoring rows: models={len(models)} items={len(items)}")
model_id = models[0]["score_model_id"]
required_scoring_sources = {
    "r09_announcement_2025~2026_a483f5df",
    "r17_announcement_2026_df1fdde9",
    "r17_attachment_2026_07f157ee",
    "r17_amendment_2026_4407bdfe",
}
for row in models + items:
    if row["visa_id"] != F2R_VISA_ID:
        fail("unexpected scoring visa_id")
    if row.get("score_model_id") != model_id:
        fail("scoring item points to another model")
    if row["source_round"] != "9" or row["assumed_target_round"] != "17":
        fail("scoring source/target round mismatch")
    if row["source_page"] != "6" or not row["source_page_basis"]:
        fail("scoring source page is not document-scoped and verified")
    if (row["valid_from"], row["valid_to"]) != ("2025-03-07", "2026-09-18"):
        fail("scoring program period mismatch")
    if row["fill_strategy"] != "backfilled" or row["review_status"] != "needs_review":
        fail("backfilled scoring data must remain needs_review")
    if row["consumption_gate"] != "blocked_while_needs_review":
        fail("needs_review scoring data is not blocked from consumption")
    sources = set(json.loads(row["related_source_document_ids_json"]))
    if sources != required_scoring_sources:
        fail("scoring source-document list mismatch")
    if not all(
        row[column]
        for column in (
            "date_basis", "inheritance_scope", "applicability_assumption",
            "review_completion_criteria",
        )
    ):
        fail("scoring review metadata is incomplete")

consumable_scores = [
    row for row in models + items
    if row["review_status"] == "reviewed" and row["consumption_gate"] == "allowed"
]
if consumable_scores:
    fail("provisional round-9 scoring rows must not be consumable")

reviews = tables["extraction_review_queue.csv"]
if len(reviews) != 6:
    fail(f"unexpected review queue size: {len(reviews)}")
for line_number, row in enumerate(reviews, start=2):
    if row["status"] not in {"open", "resolved", "ignored"}:
        fail(f"invalid review status: line {line_number}")
    if not row["blocking_scope"] or not row["completion_criteria"]:
        fail(f"incomplete review gate: line {line_number}")
    sources = json.loads(row["related_source_document_ids_json"])
    if not isinstance(sources, list) or not sources:
        fail(f"review source list is empty: line {line_number}")
    if row["source_document_id"] not in sources:
        fail(f"primary source is absent from review source list: line {line_number}")

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
    if not row["source_block_index"]:
        fail(f"missing change-history block index: line {line_number}")
    if row["source_locator_type"] == "table" and not row["source_table_index"]:
        fail(f"table evidence without table index: line {line_number}")
    if row["source_locator_type"] == "paragraph" and row["source_table_index"]:
        fail(f"paragraph evidence unexpectedly has table index: line {line_number}")
pairs = {(row["from_round"], row["to_round"]) for row in changes}
if not {("15", "16"), ("16", "17")} <= pairs or ("15", "17") in pairs:
    fail("latest adjacent-round comparison chain is incomplete")

round_fact_ids = {row["fact_id"] for row in tables["visa_round_facts.csv"]}
for row in tables["visa_current_facts.csv"]:
    if row["source_fact_id"] not in round_fact_ids:
        fail(f"missing source_fact_id: {row['source_fact_id']}")

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
        "source_page_key": [models[0]["source_document_id"], models[0]["source_page"]],
        "consumable_rows": len(consumable_scores),
        "gate": "blocked_while_needs_review",
    },
}
print(json.dumps(result, ensure_ascii=False, indent=2))
sys.exit(0)
