"""E-7-4R 원천 검수·history 매핑 무결성 검증."""

from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path

DEFAULT_BASE = Path("extraction/B_E-7-4R")
ALLOWED_TARGET_TABLES = frozenset(
    {
        "none",
        "visa_requirements",
        "visa_requirement_criteria",
        "visa_process_stages",
        "document_requirements",
        "visa_quota_status",
        "change_history",
        "scoring_items",
    }
)
ALLOWED_ACTIONS = frozenset({"insert", "reuse", "exclude"})
ALLOWED_STATUSES = frozenset({"verified", "pending_target_id"})
REQUIRED_MAPPING_COLUMNS = (
    "source_file",
    "local_record_id",
    "parent_record_id",
    "review_decision",
    "source_status",
    "target_table",
    "target_record_id",
    "mapping_action",
    "mapping_status",
    "source_document",
    "source_page",
    "source_section",
    "notes",
)
REQUIRED_REVIEW_COLUMNS = (
    "record_id",
    "parent_record_id",
    "source_document",
    "source_page",
    "source_section",
)
REQUIRED_HISTORY_COLUMNS = (
    "change_id",
    "from_round",
    "to_round",
    "old_source_page",
    "new_source_page",
    "old_value",
    "new_value",
)


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    """CSV 헤더와 행을 읽는다."""
    with path.open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        return reader.fieldnames or [], list(reader)


def _missing_columns(path: Path, fieldnames: list[str], required: tuple[str, ...]) -> list[str]:
    return [f"{path}: 필수 컬럼 누락: {column}" for column in required if column not in fieldnames]


def _duplicate_ids(rows: list[dict[str, str]], column: str, path: Path) -> list[str]:
    positions: defaultdict[str, list[int]] = defaultdict(list)
    for line_number, row in enumerate(rows, start=2):
        value = row.get(column, "")
        if value:
            positions[value].append(line_number)
    return [
        f"{path}:{column}={value} 중복 ({', '.join(map(str, lines))}행)"
        for value, lines in positions.items()
        if len(lines) > 1
    ]


def _page_pair(old_page: str, new_page: str) -> str:
    return f"{old_page}→{new_page}"


def validate_mapping(
    mapping_path: Path,
    review_path: Path,
    history_path: Path,
) -> list[str]:
    """E-7-4R 매핑표와 원천 파일 간 무결성 오류를 반환한다."""
    errors: list[str] = []
    mapping_fields, mapping_rows = read_csv(mapping_path)
    review_fields, review_rows = read_csv(review_path)
    history_fields, history_rows = read_csv(history_path)

    errors.extend(_missing_columns(mapping_path, mapping_fields, REQUIRED_MAPPING_COLUMNS))
    errors.extend(_missing_columns(review_path, review_fields, REQUIRED_REVIEW_COLUMNS))
    errors.extend(_missing_columns(history_path, history_fields, REQUIRED_HISTORY_COLUMNS))
    if errors:
        return errors

    review_by_id = {row["record_id"]: row for row in review_rows if row.get("record_id")}
    history_by_id = {row["change_id"]: row for row in history_rows if row.get("change_id")}
    mapping_by_id: defaultdict[str, list[dict[str, str]]] = defaultdict(list)
    for row in mapping_rows:
        mapping_by_id[row.get("local_record_id", "")].append(row)

    errors.extend(_duplicate_ids(review_rows, "record_id", review_path))
    errors.extend(_duplicate_ids(history_rows, "change_id", history_path))

    expected_ids = set(review_by_id) | set(history_by_id)
    actual_ids = set(mapping_by_id) - {""}
    for record_id in sorted(expected_ids - actual_ids):
        errors.append(f"매핑 누락: {record_id}")
    for record_id in sorted(actual_ids - expected_ids):
        errors.append(f"알 수 없는 원천 ID 매핑: {record_id}")

    for record_id, rows in mapping_by_id.items():
        if not record_id:
            errors.append(f"{mapping_path}: local_record_id가 비어 있음")
            continue

        is_score_expansion = all(
            row.get("target_table") == "scoring_items" and row.get("mapping_action") == "reuse"
            for row in rows
        )
        if len(rows) > 1 and not is_score_expansion:
            errors.append(f"{mapping_path}: {record_id}의 비허용 중복 매핑 {len(rows)}건")
        if is_score_expansion and len({row.get("target_record_id", "") for row in rows}) != len(
            rows
        ):
            errors.append(f"{mapping_path}: {record_id}의 scoring_items target_record_id 중복")

        for row in rows:
            line = mapping_rows.index(row) + 2
            target_table = row.get("target_table", "")
            action = row.get("mapping_action", "")
            status = row.get("mapping_status", "")
            target_id = row.get("target_record_id", "")
            if target_table not in ALLOWED_TARGET_TABLES:
                errors.append(f"{mapping_path}:{line} 허용되지 않은 target_table={target_table!r}")
            if action not in ALLOWED_ACTIONS:
                errors.append(f"{mapping_path}:{line} 허용되지 않은 mapping_action={action!r}")
            if status not in ALLOWED_STATUSES:
                errors.append(f"{mapping_path}:{line} 허용되지 않은 mapping_status={status!r}")
            if not row.get("source_document") or not row.get("source_page"):
                errors.append(f"{mapping_path}:{line} source_document/source_page 누락")
            # 공통 테이블로 이관하지 않는 공고 제목·안내 조각은 원문에
            # 독립된 section heading이 없을 수 있다. 실제 이관 대상에는
            # source_section을 필수로 적용하고, 제외 행은 review 원문과의
            # 출처 일치 여부만 검사한다.
            if not row.get("source_section") and target_table != "none":
                errors.append(f"{mapping_path}:{line} source_section 누락")
            if not row.get("notes"):
                errors.append(f"{mapping_path}:{line} notes 누락")

            if action == "exclude" and (target_table != "none" or target_id):
                errors.append(f"{mapping_path}:{line} exclude 매핑의 target 값이 잘못됨")
            if action == "insert" and target_table == "none":
                errors.append(f"{mapping_path}:{line} insert 매핑의 target_table이 none임")
            if action == "reuse" and target_table == "none":
                errors.append(f"{mapping_path}:{line} reuse 매핑의 target_table이 none임")
            if status == "pending_target_id" and target_id:
                errors.append(
                    f"{mapping_path}:{line} pending_target_id인데 target_record_id가 채워짐"
                )
            if status == "verified" and target_table != "none" and not target_id:
                errors.append(f"{mapping_path}:{line} verified인데 target_record_id가 비어 있음")

            if record_id in review_by_id:
                source = review_by_id[record_id]
                for column in (
                    "parent_record_id",
                    "source_document",
                    "source_page",
                    "source_section",
                ):
                    if row.get(column, "") != source.get(column, ""):
                        errors.append(
                            f"{mapping_path}:{line} {record_id}의 {column}이 review CSV와 다름"
                        )
                if row.get("review_decision", "") != source.get("review_decision", ""):
                    errors.append(f"{mapping_path}:{line} {record_id}의 review_decision 불일치")
            elif record_id in history_by_id:
                source = history_by_id[record_id]
                expected_page = _page_pair(source["old_source_page"], source["new_source_page"])
                if row.get("source_page") != expected_page:
                    errors.append(
                        f"{mapping_path}:{line} {record_id}의 source_page가 history와 다름"
                    )
                if f"change_history.csv:{record_id}" not in row.get("notes", ""):
                    errors.append(f"{mapping_path}:{line} {record_id}의 history 원문 참조 누락")
                if not source["old_value"] or not source["new_value"]:
                    errors.append(f"{history_path}:{record_id} old_value/new_value 누락")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="E-7-4R 원천·공통 매핑 무결성 검증")
    parser.add_argument("--base-dir", type=Path, default=DEFAULT_BASE)
    args = parser.parse_args()
    errors = validate_mapping(
        args.base_dir / "schema_mapping.csv",
        args.base_dir / "requirements/_review_current_requirements.csv",
        args.base_dir / "history/change_history.csv",
    )
    if errors:
        print("E-7-4R 매핑 검증 실패:")
        print("\n".join(f"- {error}" for error in errors))
        return 1
    print("E-7-4R 매핑 검증 통과: 문제 없음")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
