"""Build the F-2-R source-to-common-master mapping ledger for issue #39.

This script reads the ``extraction/A_F-2-R`` tables and, when supplied, the
source manifest and converted PDFs used for verification.  It writes a mapping
ledger to the A source layer and never edits ``extraction/D_visa_requirements``.

The common criteria schema can represent top-level AND conditions and one flat
OR group, but cannot represent nested expressions such as
``(A AND B) OR (C AND D)``.  Rows with those expressions are therefore marked
``blocked`` instead of being flattened.

Example with the original HWPX manifest and converted PDFs::

    uv run python scripts/build_f2r_common_mapping.py \
      --manifest /path/to/parsed/manifest.csv \
      --pdf-root /path/to/지역특화_우수인재_F-2-R_pdf
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import unicodedata
import uuid
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "extraction" / "A_F-2-R"
COMMON_DIR = ROOT / "extraction" / "D_visa_requirements"
DEFAULT_OUTPUT = SOURCE_DIR / "common_master_mapping.csv"
F2R_VISA_ID = "78dca2d7-f771-553a-b788-46c9ff56d633"
MAPPING_NAMESPACE = uuid.UUID("bd9c2e28-81fc-4f61-b5a2-6e8dd945fb1a")

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

COMPLEX_ROOT_GROUPS = {
    "applicant_status",
    "education_or_income",
    "economic_activity",
}
READY_GROUPS = {"language", "residence", "conduct", "excluded_applicants"}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def normalize_name(value: str) -> str:
    return unicodedata.normalize("NFC", value)


def validate_pipe_list(field_name: str, value: str) -> None:
    parts = value.split("|") if value else []
    if not parts or any(not part or part != part.strip() for part in parts):
        raise ValueError(f"{field_name} must be a non-empty pipe-delimited list")
    if len(parts) != len(set(parts)):
        raise ValueError(f"{field_name} contains duplicate values")


def load_existing(path: Path) -> dict[tuple[str, str], dict[str, str]]:
    if not path.exists():
        return {}
    return {
        (row["source_table"], row["source_row_id"]): row
        for row in read_csv(path)
    }


def mapping_id(source_table: str, source_row_id: str) -> str:
    key = f"visa-data:F-2-R:common-map:{source_table}:{source_row_id}"
    return str(uuid.uuid5(MAPPING_NAMESPACE, key))


def target_id(
    existing: dict[tuple[str, str], dict[str, str]],
    source_table: str,
    source_row_id: str,
    status: str,
) -> str:
    if source_table == "visa_requirements.csv":
        return F2R_VISA_ID
    if status != "ready":
        return ""
    old = existing.get((source_table, source_row_id), {}).get("target_row_id", "")
    return old or str(uuid.uuid4())


def build_group_paths(
    groups: list[dict[str, str]],
) -> tuple[dict[str, dict[str, str]], dict[str, list[str]]]:
    by_id = {row["group_id"]: row for row in groups}
    paths: dict[str, list[str]] = {}
    for group_id in by_id:
        path: list[str] = []
        current = group_id
        seen: set[str] = set()
        while current:
            if current in seen:
                raise ValueError(f"criterion group cycle: {current}")
            seen.add(current)
            group = by_id[current]
            path.append(group["group_key"])
            current = group["parent_group_id"]
        paths[group_id] = list(reversed(path))
    return by_id, paths


def classify_criterion(
    row: dict[str, str],
    by_group: dict[str, dict[str, str]],
    paths: dict[str, list[str]],
) -> tuple[str, str, str, str, str, str]:
    group = by_group[row["group_id"]]
    path = paths[row["group_id"]]
    path_set = set(path)

    if path_set & COMPLEX_ROOT_GROUPS:
        return (
            "manual_review",
            "",
            "",
            "flat_schema_cannot_represent_nested_and_or",
            "visa_requirement_criteria.csv after schema/team decision",
            "중첩 AND/OR 원식을 평탄화하면 필수조건이 누락되므로 이관을 차단한다.",
        )

    if group["group_scope"] != "eligibility":
        if group["group_scope"] == "procedure":
            destination = "visa_process_stages.csv (relative schedule review required)"
        else:
            destination = "admin_guide_corpus (future shared corpus)"
        return (
            "not_applicable",
            "",
            "",
            "outside_initial_eligibility",
            destination,
            "승인 이후 의무·동반가족·상대 일정은 공통 자격 criteria에 넣지 않는다.",
        )

    ready_group = next((name for name in READY_GROUPS if name in path_set), "")
    if not ready_group:
        raise ValueError(f"unclassified criterion path: {' > '.join(path)}")
    if ready_group == "language":
        return (
            "direct",
            "G1",
            "OR",
            "",
            "visa_requirement_criteria.csv",
            "세 언어요건은 실제 대체조건이므로 F-2-R 로컬 OR 그룹 G1로 매핑한다.",
        )
    return (
        "direct",
        "",
        "",
        "",
        "visa_requirement_criteria.csv",
        "그룹 없는 행으로 두어 다른 자격요건과 AND로 결합한다.",
    )


def criterion_page(row: dict[str, str]) -> int:
    order = int(row["display_order"])
    document_id = row["source_document_id"]

    if document_id == "r17_announcement_2026_df1fdde9":
        if 10 <= order <= 23:
            return 3
        if 30 <= order <= 42:
            return 4
        if 50 <= order <= 72:
            return 5
        if 73 <= order <= 92 or 100 <= order <= 101:
            return 6
        if 102 <= order <= 104 or 110 <= order <= 113:
            return 7
        if 114 <= order <= 116 or 163 <= order <= 165:
            return 8

    if document_id == "r17_attachment_2026_07f157ee":
        if 130 <= order <= 133:
            return 4
        if order == 140:
            return 8
        if order == 150:
            return 16
        if 160 <= order <= 162:
            return 2
        if 170 <= order <= 173:
            return 3

    raise ValueError(
        f"no verified page rule for {row['criteria_id']} "
        f"({document_id}, display_order={order})"
    )


def load_manifest(path: Path | None) -> dict[str, dict[str, str]]:
    if path is None:
        return {}
    rows = read_csv(path)
    return {row["document_id"]: row for row in rows}


def verify_manifest_hashes(manifest: dict[str, dict[str, str]], document_ids: set[str]) -> None:
    for document_id in sorted(document_ids):
        row = manifest.get(document_id)
        if row is None:
            raise ValueError(f"document absent from manifest: {document_id}")
        source_path = Path(row["source_name"])
        if not source_path.exists():
            raise FileNotFoundError(f"HWPX source not found: {source_path}")
        digest = hashlib.sha256(source_path.read_bytes()).hexdigest()
        if digest != row["sha256"]:
            raise ValueError(f"HWPX SHA-256 mismatch: {document_id}")


def resolve_pdf_pages(
    manifest: dict[str, dict[str, str]], pdf_root: Path | None
) -> dict[str, int]:
    if pdf_root is None:
        return {}
    try:
        import pdfplumber
    except ImportError as exc:
        raise RuntimeError("pdfplumber is required when --pdf-root is used") from exc

    pdf_by_stem = {
        normalize_name(path.stem): path for path in pdf_root.rglob("*.pdf")
    }
    page_counts: dict[str, int] = {}
    for document_id, row in manifest.items():
        stem = normalize_name(Path(row["filename"]).stem)
        pdf_path = pdf_by_stem.get(stem)
        if pdf_path is None:
            continue
        with pdfplumber.open(pdf_path) as document:
            page_counts[document_id] = len(document.pages)
    return page_counts


def document_name(
    document_id: str,
    manifest: dict[str, dict[str, str]],
    existing_row: dict[str, str] | None,
) -> str:
    if document_id in manifest:
        return str(Path(manifest[document_id]["filename"]).with_suffix(".pdf"))
    if existing_row and existing_row.get("source_document_name"):
        return existing_row["source_document_name"]
    raise ValueError(
        "--manifest is required for the first build so source document names can be recorded"
    )


def validate_page(
    document_id: str, page: int, page_counts: dict[str, int]
) -> None:
    if not page_counts:
        return
    count = page_counts.get(document_id)
    if count is None:
        raise ValueError(f"converted PDF not found for {document_id}")
    if not 1 <= page <= count:
        raise ValueError(f"page out of range: {document_id} page={page} count={count}")


def write_mapping(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=MAPPING_COLUMNS,
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)


def build_mapping(
    output: Path, manifest_path: Path | None, pdf_root: Path | None
) -> list[dict[str, str]]:
    resolved_output = output.resolve()
    if COMMON_DIR.resolve() in resolved_output.parents:
        raise ValueError(
            "issue #39 writes only an A-layer mapping ledger; "
            "an output inside extraction/D_visa_requirements is forbidden"
        )
    existing = load_existing(output)
    existing_document_names = {
        row["source_document_id"]: row["source_document_name"]
        for row in existing.values()
        if row.get("source_document_id") and row.get("source_document_name")
    }
    manifest = load_manifest(manifest_path)
    requirements = read_csv(SOURCE_DIR / "visa_requirements.csv")
    groups = read_csv(SOURCE_DIR / "visa_criterion_groups.csv")
    criteria = read_csv(SOURCE_DIR / "visa_requirement_criteria.csv")
    if len(requirements) != 1 or requirements[0]["visa_id"] != F2R_VISA_ID:
        raise ValueError("F-2-R source master must contain exactly one fixed visa_id row")

    current = requirements[0]
    try:
        target_regions = json.loads(current.get("target_regions_json", ""))
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid target_regions_json: {exc}") from exc
    if not isinstance(target_regions, list) or not target_regions:
        raise ValueError("target_regions_json must be a non-empty JSON list")
    if any(not isinstance(region, str) or not region.strip() for region in target_regions):
        raise ValueError("target_regions_json must contain non-empty strings")
    if len(target_regions) != len(set(target_regions)):
        raise ValueError("target_regions_json contains duplicate values")
    by_group, paths = build_group_paths(groups)
    document_ids = {current["source_document_id"]} | {
        row["source_document_id"] for row in criteria
    }
    if manifest:
        verify_manifest_hashes(manifest, document_ids)
    page_counts = resolve_pdf_pages(manifest, pdf_root)

    master_key = ("visa_requirements.csv", current["visa_id"])
    master_existing = existing.get(master_key)
    master_page = 1
    validate_page(current["source_document_id"], master_page, page_counts)
    rows: list[dict[str, str]] = [
        {
            "mapping_id": mapping_id(*master_key),
            "visa_id": F2R_VISA_ID,
            "source_table": master_key[0],
            "source_row_id": master_key[1],
            "source_group_id": "",
            "source_group_path": "",
            "target_table": "visa_requirements.csv",
            "target_row_id": F2R_VISA_ID,
            "mapping_action": "transform",
            "target_condition_group": "",
            "target_condition_operator": "",
            "source_document_id": current["source_document_id"],
            "source_document_name": document_name(
                current["source_document_id"], manifest, master_existing
            ),
            "source_page": str(master_page),
            "source_page_basis": "converted_pdf_page",
            "page_mapping_method": "manual_verified_section_page",
            "valid_from": current["valid_from"],
            "valid_to": current["valid_to"],
            "validity_mapping_method": "source_application_period",
            "mapping_status": "ready",
            "blocking_reason": "",
            "recommended_destination": "visa_requirements.csv",
            "mapping_note": (
                "visa_id는 재사용한다. program_type은 REGIONAL_SPECIALIZED, "
                "target_regions_json은 공통 지역 목록으로 변환하고, 17차 total_quota=311과 "
                "quota_type=LIMITED로 변환한다."
            ),
        }
    ]

    for row in sorted(criteria, key=lambda item: int(item["display_order"])):
        key = ("visa_requirement_criteria.csv", row["criteria_id"])
        old = existing.get(key)
        action, group, operator, blocker, destination, note = classify_criterion(
            row, by_group, paths
        )
        status = {
            "direct": "ready",
            "manual_review": "blocked",
            "not_applicable": "not_applicable",
        }[action]
        page = criterion_page(row)
        validate_page(row["source_document_id"], page, page_counts)
        row_valid_from = row["valid_from"] or current["valid_from"]
        row_valid_to = row["valid_to"] or current["valid_to"]
        validity_method = (
            "source_row_interval"
            if row["valid_from"] or row["valid_to"]
            else "inherited_master_application_period"
        )
        target_table = (
            "visa_requirement_criteria.csv"
            if status in {"ready", "blocked"}
            else ""
        )
        rows.append(
            {
                "mapping_id": mapping_id(*key),
                "visa_id": F2R_VISA_ID,
                "source_table": key[0],
                "source_row_id": key[1],
                "source_group_id": row["group_id"],
                "source_group_path": " > ".join(paths[row["group_id"]]),
                "target_table": target_table,
                "target_row_id": target_id(existing, *key, status),
                "mapping_action": action,
                "target_condition_group": group,
                "target_condition_operator": operator,
                "source_document_id": row["source_document_id"],
                "source_document_name": document_name(
                    row["source_document_id"],
                    manifest,
                    old
                    or {
                        "source_document_name": existing_document_names.get(
                            row["source_document_id"], ""
                        )
                    },
                ),
                "source_page": str(page),
                "source_page_basis": "converted_pdf_page",
                "page_mapping_method": "manual_verified_criteria_page_rule",
                "valid_from": row_valid_from,
                "valid_to": row_valid_to,
                "validity_mapping_method": validity_method,
                "mapping_status": status,
                "blocking_reason": blocker,
                "recommended_destination": destination,
                "mapping_note": note,
            }
        )

    write_mapping(output, rows)
    return rows


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--pdf-root", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    rows = build_mapping(args.output, args.manifest, args.pdf_root)
    summary = {
        "output": str(args.output),
        "rows": len(rows),
        "actions": dict(Counter(row["mapping_action"] for row in rows)),
        "statuses": dict(Counter(row["mapping_status"] for row in rows)),
        "source_pages_resolved": sum(bool(row["source_page"]) for row in rows),
        "shared_master_modified": False,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
