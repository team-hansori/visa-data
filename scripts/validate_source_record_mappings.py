"""v2 source_record_mappings 원천·대상 연결을 검증한다.

공통 스키마 형식 검증기와 분리해, 원천 파일의 테이블별 PK로 source_record_id를
찾고 MAPPED 행의 target_record_id와 비자·출처·그룹 소유권까지 확인한다.
"""

from __future__ import annotations

import argparse
import csv
import unicodedata
from dataclasses import dataclass
from pathlib import Path

from scripts import schema_v2

DEFAULT_SOURCE_ROOT = Path(".")
DEFAULT_V2_DIR = Path("extraction/common_v2")

# source_record_mappings.csv가 실제로 참조하는 원천 CSV 헤더에서 확인한 PK다.
# 지원 대상을 명시적으로 관리해 새 원천 테이블이 추가됐을 때 임의의 다른 셀 값으로
# source_record_id가 우연히 통과하지 않게 한다.
SOURCE_PRIMARY_KEYS: dict[tuple[str, str], str] = {
    ("A_F-2-R", "visa_announcement_rounds"): "announcement_id",
    ("A_F-2-R", "visa_criterion_groups"): "group_id",
    ("A_F-2-R", "visa_regional_quotas"): "quota_id",
    ("A_F-2-R", "visa_requirement_criteria"): "criteria_id",
    ("A_F-2-R", "visa_required_documents"): "document_requirement_id",
    ("A_F-2-R", "visa_requirements"): "visa_id",
    ("B_E-7-4R", "_review_current_requirements"): "record_id",
    ("B_E-7-4R", "change_history"): "change_id",
    ("B_E-7-4R", "current_requirements"): "record_id",
    ("B_E-7-4R", "document_forms"): "form_id",
    ("B_E-7-4R", "scoring_items"): "score_id",
    ("C_D-2-common", "certified_universities"): "cert_id",
    ("C_D-2-common", "gwangyeok_eligible_departments"): "eligible_id",
    ("C_D-2-common", "parttime_work_rules"): "rule_id",
    ("D_visa_requirements", "visa_process_stages"): "stage_id",
    ("D_visa_requirements", "visa_requirement_criteria"): "criteria_id",
    ("D_visa_requirements", "visa_requirements"): "visa_id",
}

# visa_id를 직접 갖지 않는 v2 테이블은 이 소유 관계를 따라 비자를 찾는다.
TARGET_OWNER_RELATIONS: dict[str, tuple[tuple[str, str], ...]] = {
    schema_v2.VISA_REQUIREMENT_CRITERIA: (("group_id", schema_v2.VISA_CRITERION_GROUPS),),
    schema_v2.VISA_SCORING_ITEMS: (("score_model_id", schema_v2.VISA_SCORING_MODELS),),
    schema_v2.DOCUMENT_REQUIREMENTS: (("stage_id", schema_v2.VISA_PROCESS_STAGES),),
    schema_v2.DOCUMENT_ATTACHMENT_RELATIONS: (
        ("parent_document_id", schema_v2.DOCUMENT_REQUIREMENTS),
        ("attachment_document_id", schema_v2.DOCUMENT_REQUIREMENTS),
    ),
    schema_v2.VISA_QUOTA_SNAPSHOTS: (("quota_policy_id", schema_v2.VISA_QUOTA_POLICIES),),
}


@dataclass(frozen=True)
class SourceRecord:
    """명시적 PK로 찾은 원천 행과 해당 파일."""

    row: dict[str, str]
    path: Path


@dataclass(frozen=True)
class SourceTableIndex:
    """한 원천 논리 테이블의 PK 인덱스."""

    pk_column: str | None
    records: dict[str, list[SourceRecord]]
    paths: list[Path]
    missing_pk_paths: list[Path]


def _read_table(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        return reader.fieldnames or [], list(reader)


def _read_rows(path: Path) -> list[dict[str, str]]:
    return _read_table(path)[1]


def _source_table_paths(source_root: Path, dataset: str, table: str) -> list[Path]:
    dataset_root = source_root / "extraction" / dataset
    if not dataset_root.exists():
        return []
    return sorted(dataset_root.rglob(f"{table}.csv"))


def _load_source_index(source_root: Path, dataset: str, table: str) -> SourceTableIndex:
    paths = _source_table_paths(source_root, dataset, table)
    pk_column = SOURCE_PRIMARY_KEYS.get((dataset, table))
    records: dict[str, list[SourceRecord]] = {}
    missing_pk_paths: list[Path] = []

    if pk_column is None:
        return SourceTableIndex(pk_column, records, paths, missing_pk_paths)

    for path in paths:
        header, rows = _read_table(path)
        if pk_column not in header:
            missing_pk_paths.append(path)
            continue
        for row in rows:
            record_id = row.get(pk_column, "")
            if record_id:
                records.setdefault(record_id, []).append(SourceRecord(row=row, path=path))

    return SourceTableIndex(pk_column, records, paths, missing_pk_paths)


def _load_target_rows(v2_dir: Path) -> dict[str, dict[str, dict[str, str]]]:
    rows_by_id: dict[str, dict[str, dict[str, str]]] = {}
    for table_name in schema_v2.TABLE_ORDER:
        table = schema_v2.SCHEMA_V2[table_name]
        path = v2_dir / table.filename
        if not path.exists():
            rows_by_id[table_name] = {}
            continue
        rows_by_id[table_name] = {
            row[table.pk]: row for row in _read_rows(path) if row.get(table.pk)
        }
    return rows_by_id


def _normalize_reference(value: str) -> str:
    normalized = unicodedata.normalize("NFC", value).replace("\\", "/").casefold()
    return " ".join(normalized.split())


def _document_reference_matches(value: str, document: dict[str, str]) -> bool:
    """레거시 문서명/경로가 v2 문서 메타데이터 중 하나를 가리키는지 확인한다."""
    normalized_value = _normalize_reference(value)
    candidates = (
        document.get("source_document_key", ""),
        document.get("document_name", ""),
        document.get("source_location", ""),
    )
    for candidate in candidates:
        normalized_candidate = _normalize_reference(candidate)
        if not normalized_candidate:
            continue
        if normalized_value == normalized_candidate:
            return True
        # 레거시 값은 문서명 뒤에 "p.2"나 "_section0"을 덧붙여 저장한 경우가 있다.
        if len(normalized_candidate) >= 8 and normalized_candidate in normalized_value:
            return True
        if len(normalized_value) >= 8 and normalized_value in normalized_candidate:
            return True
    return False


def _normalize_visa_code(value: str) -> str:
    return "".join(value.upper().split())


def _source_page(row: dict[str, str]) -> str:
    page = row.get("source_page", "")
    if page:
        return page
    if "old_source_page" in row or "new_source_page" in row:
        old_page = row.get("old_source_page", "")
        new_page = row.get("new_source_page", "")
        if old_page or new_page:
            return f"{old_page}→{new_page}"
    return ""


def _source_visa_codes(
    source_root: Path,
    dataset: str,
    source_row: dict[str, str],
    source_cache: dict[tuple[str, str], SourceTableIndex],
) -> set[str]:
    """원천 행에서 확인 가능한 비자 코드를 보수적으로 해석한다.

    A_F-2-R처럼 원천 visa_id를 v2 UUID로 재발급한 데이터셋은 같은 원천의
    visa_requirements 행을 따라가 visa_code로 동일성을 비교한다. 해석할 메타데이터가
    없으면 빈 집합을 반환해 레거시 행을 추측으로 거부하지 않는다.
    """
    codes = {
        value
        for value in (source_row.get("visa_code", ""), source_row.get("visa_type", ""))
        if value
    }
    source_visa_id = source_row.get("visa_id", "")
    visa_key = (dataset, schema_v2.VISA_REQUIREMENTS)
    if not source_visa_id or visa_key not in SOURCE_PRIMARY_KEYS:
        return codes

    if visa_key not in source_cache:
        source_cache[visa_key] = _load_source_index(source_root, *visa_key)
    candidates = source_cache[visa_key].records.get(source_visa_id, [])
    if len(candidates) == 1 and candidates[0].row.get("visa_code"):
        codes.add(candidates[0].row["visa_code"])
    return codes


def _target_visa_ids(
    table_name: str,
    row: dict[str, str],
    target_rows: dict[str, dict[str, dict[str, str]]],
    *,
    visited: frozenset[tuple[str, str]] = frozenset(),
) -> tuple[set[str], list[str]]:
    """v2 대상 행의 직·간접 소유 visa_id와 끊어진 소유 관계를 반환한다."""
    direct_visa_id = row.get("visa_id", "")
    if direct_visa_id:
        return {direct_visa_id}, []

    errors: list[str] = []
    visa_ids: set[str] = set()
    for fk_column, owner_table in TARGET_OWNER_RELATIONS.get(table_name, ()):
        owner_id = row.get(fk_column, "")
        if not owner_id:
            continue
        edge = (owner_table, owner_id)
        if edge in visited:
            errors.append(f"target 소유 관계에 순환참조가 있음: {owner_table}/{owner_id}")
            continue
        owner_row = target_rows.get(owner_table, {}).get(owner_id)
        if owner_row is None:
            errors.append(
                f"target {table_name}의 {fk_column}가 소유 테이블에 없음: {owner_table}/{owner_id}"
            )
            continue
        nested_ids, nested_errors = _target_visa_ids(
            owner_table,
            owner_row,
            target_rows,
            visited=visited | {edge},
        )
        visa_ids.update(nested_ids)
        errors.extend(nested_errors)
    return visa_ids, errors


def _source_group_path(group_id: str, group_index: SourceTableIndex) -> str | None:
    keys: list[str] = []
    visited: set[str] = set()
    current_id = group_id
    while current_id:
        if current_id in visited:
            return None
        visited.add(current_id)
        candidates = group_index.records.get(current_id, [])
        if len(candidates) != 1:
            return None
        group = candidates[0].row
        group_key = group.get("group_key", "")
        if not group_key:
            return None
        keys.append(group_key)
        current_id = group.get("parent_group_id", "")
    return " > ".join(reversed(keys))


def _check_source_group_ownership(
    source_root: Path,
    dataset: str,
    source_row: dict[str, str],
    mapping: dict[str, str],
    source_cache: dict[tuple[str, str], SourceTableIndex],
) -> list[str]:
    group_id = source_row.get("group_id", "")
    group_key = (dataset, schema_v2.VISA_CRITERION_GROUPS)
    if not group_id or group_key not in SOURCE_PRIMARY_KEYS:
        return []

    if group_key not in source_cache:
        source_cache[group_key] = _load_source_index(source_root, *group_key)
    group_index = source_cache[group_key]
    if not group_index.paths:
        return []

    groups = group_index.records.get(group_id, [])
    if not groups:
        return [f"원천 criteria의 group_id가 원천 그룹 PK에 없음: {dataset}/{group_id}"]
    if len(groups) > 1:
        return [f"원천 criteria의 group_id가 중복되어 소유권이 모호함: {dataset}/{group_id}"]

    errors: list[str] = []
    group_row = groups[0].row
    criteria_visa_id = source_row.get("visa_id", "")
    group_visa_id = group_row.get("visa_id", "")
    if criteria_visa_id and group_visa_id and criteria_visa_id != group_visa_id:
        errors.append(
            f"원천 criteria/group 소유 visa_id가 다름: "
            f"criteria={criteria_visa_id}, group={group_visa_id}"
        )

    mapped_path = mapping.get("source_group_path", "")
    resolved_path = _source_group_path(group_id, group_index)
    if mapped_path and resolved_path and mapped_path != resolved_path:
        errors.append(
            f"source_group_path가 원천 그룹 경로와 다름: "
            f"mapping={mapped_path!r}, source={resolved_path!r}"
        )
    return errors


def _check_semantic_integrity(
    *,
    source_root: Path,
    mapping: dict[str, str],
    source_record: SourceRecord | None,
    target_row: dict[str, str] | None,
    target_rows: dict[str, dict[str, dict[str, str]]],
    source_cache: dict[tuple[str, str], SourceTableIndex],
) -> list[str]:
    errors: list[str] = []
    dataset = mapping.get("source_dataset", "")
    mapping_visa_id = mapping.get("visa_id", "")
    mapping_visa = target_rows.get(schema_v2.VISA_REQUIREMENTS, {}).get(mapping_visa_id)

    if mapping_visa_id and mapping_visa is None:
        errors.append(f"mapping visa_id가 v2 visa PK에 없음: {mapping_visa_id}")

    document_id = mapping.get("source_document_id", "")
    document = target_rows.get(schema_v2.SOURCE_DOCUMENTS, {}).get(document_id)
    if document_id and document is None:
        errors.append(f"source_document_id가 v2 문서 PK에 없음: {document_id}")
    elif document is not None:
        document_visa_id = document.get("visa_id", "")
        if mapping_visa_id and document_visa_id and mapping_visa_id != document_visa_id:
            errors.append(
                f"source document 소유 visa_id가 mapping과 다름: "
                f"mapping={mapping_visa_id}, document={document_visa_id}"
            )

    if source_record is not None:
        source_row = source_record.row
        source_codes = _source_visa_codes(source_root, dataset, source_row, source_cache)
        target_code = mapping_visa.get("visa_code", "") if mapping_visa else ""
        if target_code:
            for source_code in source_codes:
                if _normalize_visa_code(source_code) != _normalize_visa_code(target_code):
                    errors.append(
                        f"원천 visa가 mapping visa와 다름: "
                        f"source={source_code}, target={target_code}"
                    )

        if document is not None:
            legacy_document_id = source_row.get("source_document_id", "")
            valid_document_ids = {document_id, document.get("source_document_key", "")}
            if legacy_document_id and legacy_document_id not in valid_document_ids:
                errors.append(
                    f"원천 source_document_id가 mapping 문서와 다름: "
                    f"source={legacy_document_id}, mapping={document_id}"
                )

            legacy_document = source_row.get("source_document", "")
            if legacy_document and not _document_reference_matches(legacy_document, document):
                errors.append(
                    f"원천 source_document 경로가 mapping 문서와 다름: "
                    f"source={legacy_document!r}, mapping={document_id}"
                )

        source_page = _source_page(source_row)
        mapping_page = mapping.get("source_page", "")
        if source_page and mapping_page and source_page != mapping_page:
            errors.append(
                f"source_page가 원천 행과 다름: mapping={mapping_page!r}, source={source_page!r}"
            )

        for field in ("valid_from", "valid_to"):
            source_value = source_row.get(field, "")
            mapping_value = mapping.get(field, "")
            if source_value and mapping_value and source_value != mapping_value:
                errors.append(
                    f"{field}이 원천 행과 다름: mapping={mapping_value!r}, source={source_value!r}"
                )

        errors.extend(
            _check_source_group_ownership(
                source_root,
                dataset,
                source_row,
                mapping,
                source_cache,
            )
        )

    if target_row is not None:
        target_table = mapping.get("target_table", "")
        target_id = mapping.get("target_record_id", "")
        target_document_id = target_row.get("source_document_id", "")
        if document_id and target_document_id and document_id != target_document_id:
            errors.append(
                f"target source_document_id가 mapping과 다름: "
                f"target={target_document_id}, mapping={document_id}"
            )

        target_visa_ids, ownership_errors = _target_visa_ids(
            target_table,
            target_row,
            target_rows,
            visited=frozenset({(target_table, target_id)}),
        )
        errors.extend(ownership_errors)
        if mapping_visa_id and target_visa_ids and target_visa_ids != {mapping_visa_id}:
            errors.append(
                f"target 소유 visa_id가 mapping과 다름: "
                f"mapping={mapping_visa_id}, target={','.join(sorted(target_visa_ids))}"
            )

    return errors


def validate_mappings(
    source_root: Path = DEFAULT_SOURCE_ROOT,
    v2_dir: Path = DEFAULT_V2_DIR,
) -> list[str]:
    """source_record_mappings.csv의 원천·대상·상태 정합성을 반환한다."""
    mapping_path = v2_dir / "source_record_mappings.csv"
    if not mapping_path.exists():
        return [f"{mapping_path} - 파일이 없음"]

    mappings = _read_rows(mapping_path)
    target_rows = _load_target_rows(v2_dir)
    errors: list[str] = []
    source_cache: dict[tuple[str, str], SourceTableIndex] = {}

    for line, row in enumerate(mappings, start=2):
        dataset = row.get("source_dataset", "")
        source_table = row.get("source_table", "")
        key = (dataset, source_table)
        if key not in source_cache:
            source_cache[key] = _load_source_index(source_root, dataset, source_table)
        source_index = source_cache[key]
        source_record: SourceRecord | None = None

        if source_index.pk_column is None:
            errors.append(
                f"source_record_mappings.csv:{line} - 원천 PK 정의가 없음: {dataset}/{source_table}"
            )
        elif not source_index.paths:
            errors.append(
                f"source_record_mappings.csv:{line} - 원천 테이블 파일이 없음: "
                f"{dataset}/{source_table}.csv"
            )
        elif source_index.missing_pk_paths:
            for path in source_index.missing_pk_paths:
                errors.append(
                    f"source_record_mappings.csv:{line} - 원천 테이블에 명시적 PK "
                    f"'{source_index.pk_column}'가 없음: {path}"
                )
        else:
            source_record_id = row.get("source_record_id", "")
            matches = source_index.records.get(source_record_id, [])
            if not matches:
                errors.append(
                    f"source_record_mappings.csv:{line} - 원천 source_record_id가 "
                    f"{source_index.pk_column} PK에 없음: "
                    f"{dataset}/{source_table}/{source_record_id}"
                )
            elif len(matches) > 1:
                locations = ", ".join(str(match.path) for match in matches)
                errors.append(
                    f"source_record_mappings.csv:{line} - 원천 PK가 중복되어 행이 모호함: "
                    f"{dataset}/{source_table}/{source_record_id} ({locations})"
                )
            else:
                source_record = matches[0]

        status = row.get("mapping_status", "")
        action = row.get("mapping_action", "")
        target_table = row.get("target_table", "")
        target_id = row.get("target_record_id", "")
        target_row: dict[str, str] | None = None

        if status == "MAPPED":
            if target_table == "NONE" or not target_id:
                errors.append(f"source_record_mappings.csv:{line} - MAPPED 행에 target 연결이 없음")
            else:
                target_row = target_rows.get(target_table, {}).get(target_id)
                if target_row is None:
                    errors.append(
                        f"source_record_mappings.csv:{line} - target_record_id가 대상 PK에 없음: "
                        f"{target_table}/{target_id}"
                    )
        elif status in {"PENDING", "READY", "BLOCKED"} and target_id:
            errors.append(
                f"source_record_mappings.csv:{line} - {status} 행에 target_record_id가 채워짐"
            )

        if action == "SKIP" and target_table != "NONE":
            errors.append(
                f"source_record_mappings.csv:{line} - SKIP 행의 target_table은 NONE이어야 함"
            )
        if action != "SKIP" and target_table == "NONE" and status == "MAPPED":
            errors.append(
                f"source_record_mappings.csv:{line} - SKIP 아닌 MAPPED 행의 target_table이 NONE임"
            )

        semantic_errors = _check_semantic_integrity(
            source_root=source_root,
            mapping=row,
            source_record=source_record,
            target_row=target_row,
            target_rows=target_rows,
            source_cache=source_cache,
        )
        errors.extend(f"source_record_mappings.csv:{line} - {error}" for error in semantic_errors)

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="source_record_mappings 원천·대상 연결 검증")
    parser.add_argument("--source-root", type=Path, default=DEFAULT_SOURCE_ROOT)
    parser.add_argument("--v2-dir", type=Path, default=DEFAULT_V2_DIR)
    args = parser.parse_args()
    errors = validate_mappings(args.source_root, args.v2_dir)
    if errors:
        print(f"source_record_mappings 검증 실패: {len(errors)}건")
        for error in errors:
            print(f"  - {error}")
        return 1
    print("source_record_mappings 검증 통과: 문제 없음")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
