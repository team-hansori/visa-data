"""Claude가 만든 구조화 draft(JSON)를 기존 D_visa_requirements CSV와 비교해
리뷰 리포트(md)만 생성한다. final CSV는 이 스크립트가 절대 수정하지 않는다.

draft JSON 스키마:
{
  "visa_code": "F-4-R",
  "notice_round": 13,
  "source_document": "충북_..._13차.pdf",
  "requirements": {
    "visa_name_kr": str, "program_type": str,
    "target_region": [str, ...] | null,
    "total_score_threshold": int | null,
    "residency_limit_years": int,
    "allowed_industries": [str, ...] | null,
    "application_method": str,
    "quota_type": "LIMITED" | "UNLIMITED" | "UNKNOWN",
    "total_quota": int | null,
    "quota_shared_with": str | null,
    "next_visa_code": str | null,
    "valid_from": "YYYY-MM-DD", "valid_to": "YYYY-MM-DD",
    "source_page": str
  },
  "criteria": [
    {"criteria_name": str, "criteria_type": "binary"|"graduated",
     "threshold_value": str, "point_value": int | null,
     "condition_group": str | null, "condition_operator": str | null,
     "special_case_note": str, "source_page": str}, ...
  ],
  "stages": [
    {"stage_order": int, "stage_name": str, "stage_name_kr": str,
     "actor_from": str, "actor_to": str,
     "stage_start_date": "YYYY-MM-DD", "stage_end_date": "YYYY-MM-DD",
     "notes": str, "source_page": str}, ...
  ],
  "quota_status": {"remaining_quota": int, "as_of_date": "YYYY-MM-DD", "source_page": str} | null,
  "contacts": [{"region": str, "department_name": str, "phone": str}, ...]
}

사용법: uv run python scripts/compare_and_report.py <draft_json경로>
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import uuid
from datetime import date
from pathlib import Path

D_VISA_DIR = Path("extraction/D_visa_requirements")
AGENCY_CONTACTS_PATH = Path("reference/agency_contacts.csv")
REPORTS_DIR = Path("reports/notices")

REQUIREMENTS_COMPARE_FIELDS = [
    "visa_name_kr",
    "program_type",
    "target_region",
    "total_score_threshold",
    "residency_limit_years",
    "allowed_industries",
    "application_method",
    "quota_type",
    "total_quota",
    "quota_shared_with",
    "next_visa_code",
]
CRITERIA_COMPARE_FIELDS = [
    "threshold_value",
    "point_value",
    "condition_group",
    "condition_operator",
    "special_case_note",
]


def read_csv_rows(path: Path) -> list[dict]:
    """CSV를 읽어 dict 행 리스트로 반환한다. 파일이 없으면 빈 리스트."""
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def array_to_cell(values: list[str] | None) -> str:
    """text[] 값을 D_visa_requirements 배열 표기 규칙(파이프 구분)으로 직렬화한다."""
    if not values:
        return ""
    return "|".join(values)


def normalize(value) -> str:
    """비교를 위해 None/빈문자열을 하나로 통일하고 문자열로 바꾼다."""
    if value is None:
        return ""
    if isinstance(value, list):
        return array_to_cell(value)
    return str(value)


def find_existing_visa_row(visa_code: str) -> dict | None:
    """visa_requirements.csv에서 visa_code에 해당하는 행을 찾는다(없으면 None = 신규 비자)."""
    rows = read_csv_rows(D_VISA_DIR / "visa_requirements.csv")
    for row in rows:
        if row.get("visa_code") == visa_code:
            return row
    return None


def diff_requirements(existing: dict | None, draft: dict) -> list[dict]:
    """visa_requirements 필드별 변경사항을 (field, old, new) 목록으로 만든다."""
    changes = []
    for field in REQUIREMENTS_COMPARE_FIELDS:
        new_value = draft.get(field)
        old_value = existing.get(field) if existing else None
        old_normalized = normalize(old_value) if existing else None
        new_normalized = normalize(new_value)
        if existing is None:
            changes.append({"field": field, "old": None, "new": new_normalized})
        elif old_normalized != new_normalized:
            changes.append({"field": field, "old": old_normalized, "new": new_normalized})
    return changes


def diff_criteria(visa_id: str | None, draft_criteria: list[dict]) -> dict:
    """기존 criteria 행과 draft criteria를 criteria_name 기준으로 매칭해 added/removed/changed를 나눈다."""
    existing_rows = read_csv_rows(D_VISA_DIR / "visa_requirement_criteria.csv")
    existing_for_visa = (
        {r["criteria_name"]: r for r in existing_rows if r.get("visa_id") == visa_id}
        if visa_id
        else {}
    )
    draft_by_name = {c["criteria_name"]: c for c in draft_criteria}

    added = [draft_by_name[name] for name in draft_by_name if name not in existing_for_visa]
    removed = [existing_for_visa[name] for name in existing_for_visa if name not in draft_by_name]
    changed = []
    for name in draft_by_name:
        if name not in existing_for_visa:
            continue
        old_row = existing_for_visa[name]
        new_row = draft_by_name[name]
        field_changes = []
        for field in CRITERIA_COMPARE_FIELDS:
            old_value = normalize(old_row.get(field))
            new_value = normalize(new_row.get(field))
            if old_value != new_value:
                field_changes.append({"field": field, "old": old_value, "new": new_value})
        if field_changes:
            changed.append({"criteria_name": name, "changes": field_changes})

    return {"added": added, "removed": removed, "changed": changed}


def is_round_already_recorded(visa_id: str | None, notice_round: int, table_name: str) -> bool:
    """visa_process_stages/visa_quota_status에 같은 visa_id+notice_round 행이 이미 있는지 확인한다."""
    if not visa_id:
        return False
    rows = read_csv_rows(D_VISA_DIR / f"{table_name}.csv")
    return any(
        r.get("visa_id") == visa_id and r.get("notice_round") == str(notice_round) for r in rows
    )


def check_agency_contacts(visa_code: str, contacts: list[dict]) -> list[str]:
    """공고문의 문의처 전화번호/부서명을 reference/agency_contacts.csv와 대조한다."""
    warnings = []
    agency_rows = read_csv_rows(AGENCY_CONTACTS_PATH)
    for contact in contacts:
        region = contact.get("region", "")
        matches = [
            r
            for r in agency_rows
            if r.get("region") == region and r.get("category_minor") == visa_code
        ]
        if not matches:
            warnings.append(
                f"agency_contacts.csv에 {region}/{visa_code} 조합이 없음 - 신규 행 추가 필요 여부 확인"
            )
            continue
        for match in matches:
            if match.get("phone") != contact.get("phone"):
                warnings.append(
                    f"{region}/{visa_code}: agency_contacts.csv 전화번호({match.get('phone')}) "
                    f"vs 공고문({contact.get('phone')}) 불일치 - 지난 문의처 불일치 사례처럼 확인 필요"
                )
            if match.get("department_name") != contact.get("department_name"):
                warnings.append(
                    f"{region}/{visa_code}: agency_contacts.csv 부서명({match.get('department_name')}) "
                    f"vs 공고문({contact.get('department_name')}) 불일치 - 확인 필요"
                )
    return warnings


def build_change_history_proposals(
    visa_id: str,
    from_round: int | None,
    to_round: int,
    requirements_changes: list[dict],
    criteria_diff: dict,
    source_document: str,
    new_source_page: str,
) -> list[dict]:
    """change_history.csv에 추가할 제안 행을 만든다(자동 반영 아님, 사람이 직접 반영)."""
    proposals = []

    for change in requirements_changes:
        proposals.append(
            {
                "change_id": str(uuid.uuid4()),
                "visa_id": visa_id,
                "table_name": "visa_requirements",
                "field_identifier": change["field"],
                "from_round": from_round,
                "to_round": to_round,
                "old_value": change["old"],
                "new_value": change["new"],
                "change_type": "added" if change["old"] is None else "value_changed",
                "old_source_page": "",
                "new_source_page": new_source_page,
                "description": f"{source_document} 반영",
            }
        )

    for row in criteria_diff["added"]:
        proposals.append(
            {
                "change_id": str(uuid.uuid4()),
                "visa_id": visa_id,
                "table_name": "visa_requirement_criteria",
                "field_identifier": row["criteria_name"],
                "from_round": from_round,
                "to_round": to_round,
                "old_value": "",
                "new_value": normalize(row.get("threshold_value")),
                "change_type": "added",
                "old_source_page": "",
                "new_source_page": row.get("source_page", ""),
                "description": f"{source_document} 반영",
            }
        )

    for row in criteria_diff["removed"]:
        proposals.append(
            {
                "change_id": str(uuid.uuid4()),
                "visa_id": visa_id,
                "table_name": "visa_requirement_criteria",
                "field_identifier": row["criteria_name"],
                "from_round": from_round,
                "to_round": to_round,
                "old_value": normalize(row.get("threshold_value")),
                "new_value": "",
                "change_type": "removed",
                "old_source_page": row.get("source_page", ""),
                "new_source_page": "",
                "description": f"{source_document}에서 확인 안 됨 - 삭제 여부 사람 확인 필요",
            }
        )

    for entry in criteria_diff["changed"]:
        for field_change in entry["changes"]:
            change_type = (
                "scope_changed"
                if field_change["field"] in ("condition_group", "condition_operator")
                else "value_changed"
            )
            proposals.append(
                {
                    "change_id": str(uuid.uuid4()),
                    "visa_id": visa_id,
                    "table_name": "visa_requirement_criteria",
                    "field_identifier": f"{entry['criteria_name']}.{field_change['field']}",
                    "from_round": from_round,
                    "to_round": to_round,
                    "old_value": field_change["old"],
                    "new_value": field_change["new"],
                    "change_type": change_type,
                    "old_source_page": "",
                    "new_source_page": new_source_page,
                    "description": f"{source_document} 반영",
                }
            )

    return proposals


def render_report(
    draft: dict,
    existing_row: dict | None,
    visa_id: str,
    requirements_changes: list[dict],
    criteria_diff: dict,
    stages_already_recorded: bool,
    quota_already_recorded: bool,
    agency_warnings: list[str],
    change_history_proposals: list[dict],
) -> str:
    """리뷰 리포트를 마크다운 문자열로 만든다."""
    visa_code = draft["visa_code"]
    notice_round = draft["notice_round"]
    is_new_visa = existing_row is None

    lines = [
        f"# {visa_code} {notice_round}차 공고 반영 검토 리포트",
        "",
        f"- 생성일: {date.today().isoformat()}",
        f"- 원본 문서: {draft.get('source_document', '')}",
        f"- visa_id: `{visa_id}`{' (신규 발급 - 최초 등록)' if is_new_visa else ''}",
        "",
        "이 리포트는 자동 반영되지 않았습니다. 검토 후 아래 내용을 직접 CSV에 반영하세요.",
        "",
    ]

    lines.append("## 1. visa_requirements 변경사항")
    lines.append("")
    if not requirements_changes:
        lines.append("변경 없음.")
    else:
        lines.append("| 필드 | 기존값 | 신규값 |")
        lines.append("|---|---|---|")
        for change in requirements_changes:
            old = change["old"] if change["old"] not in (None, "") else "(없음)"
            lines.append(f"| `{change['field']}` | {old} | {change['new']} |")
    lines.append("")

    lines.append("## 2. visa_requirement_criteria 변경사항")
    lines.append("")
    if criteria_diff["added"]:
        lines.append("### 신규 추가")
        lines.append("")
        lines.append("| criteria_name | threshold_value | condition_group/operator | 근거 페이지 |")
        lines.append("|---|---|---|---|")
        for row in criteria_diff["added"]:
            group_op = f"{row.get('condition_group') or '-'}/{row.get('condition_operator') or '-'}"
            lines.append(
                f"| {row['criteria_name']} | {row.get('threshold_value', '')} | {group_op} | "
                f"{row.get('source_page', '')} |"
            )
        lines.append("")
    if criteria_diff["removed"]:
        lines.append("### 이번 공고문에서 확인 안 됨(삭제 후보 - 사람 확인 필요)")
        lines.append("")
        lines.append("| criteria_name | 기존 threshold_value |")
        lines.append("|---|---|")
        for row in criteria_diff["removed"]:
            lines.append(f"| {row['criteria_name']} | {row.get('threshold_value', '')} |")
        lines.append("")
    if criteria_diff["changed"]:
        lines.append("### 값 변경")
        lines.append("")
        lines.append("| criteria_name | 필드 | 기존값 | 신규값 |")
        lines.append("|---|---|---|---|")
        for entry in criteria_diff["changed"]:
            for field_change in entry["changes"]:
                marker = (
                    " ⚠️논리구조 변경"
                    if field_change["field"] in ("condition_group", "condition_operator")
                    else ""
                )
                lines.append(
                    f"| {entry['criteria_name']} | `{field_change['field']}`{marker} | "
                    f"{field_change['old']} | {field_change['new']} |"
                )
        lines.append("")
    if not (criteria_diff["added"] or criteria_diff["removed"] or criteria_diff["changed"]):
        lines.append("변경 없음.")
        lines.append("")

    lines.append("## 3. visa_process_stages 신규 행")
    lines.append("")
    if stages_already_recorded:
        lines.append(f"이미 {notice_round}차 행이 존재합니다 - 신규 행을 추가하지 마세요.")
    elif not draft.get("stages"):
        lines.append("draft에 stages 정보가 없습니다.")
    else:
        lines.append("| stage_order | stage_name_kr | actor_from | actor_to | 시작일 | 마감일 |")
        lines.append("|---|---|---|---|---|---|")
        for stage in draft["stages"]:
            lines.append(
                f"| {stage.get('stage_order', '')} | {stage.get('stage_name_kr', '')} | "
                f"{stage.get('actor_from', '')} | {stage.get('actor_to', '')} | "
                f"{stage.get('stage_start_date', '')} | {stage.get('stage_end_date', '')} |"
            )
    lines.append("")

    lines.append("## 4. visa_quota_status 신규 행")
    lines.append("")
    quota_status = draft.get("quota_status")
    if quota_already_recorded:
        lines.append(f"이미 {notice_round}차 행이 존재합니다 - 신규 행을 추가하지 마세요.")
    elif not quota_status:
        lines.append("해당 없음 (quota_type이 UNLIMITED거나 공고문에 잔여인원 언급 없음).")
    else:
        lines.append(
            f"remaining_quota={quota_status.get('remaining_quota')}, "
            f"as_of_date={quota_status.get('as_of_date')}"
        )
    lines.append("")

    lines.append("## 5. agency_contacts 대조 경고")
    lines.append("")
    if not agency_warnings:
        lines.append("경고 없음.")
    else:
        for warning in agency_warnings:
            lines.append(f"- ⚠️ {warning}")
    lines.append("")

    lines.append("## 6. change_history.csv 제안 행 (사람이 직접 반영)")
    lines.append("")
    if not change_history_proposals:
        lines.append("제안 없음.")
    else:
        lines.append(
            "| table_name | field_identifier | from_round | to_round | old_value | new_value | change_type |"
        )
        lines.append("|---|---|---|---|---|---|---|")
        for proposal in change_history_proposals:
            from_round = proposal["from_round"] if proposal["from_round"] is not None else "(직접 확인)"
            lines.append(
                f"| {proposal['table_name']} | {proposal['field_identifier']} | "
                f"{from_round} | {proposal['to_round']} | "
                f"{proposal['old_value'] or '(없음)'} | {proposal['new_value'] or '(없음)'} | "
                f"{proposal['change_type']} |"
            )
    lines.append("")

    return "\n".join(lines)


def run(draft_path: Path) -> Path:
    """draft JSON을 읽어 리포트를 생성하고 저장된 경로를 반환한다."""
    draft = json.loads(draft_path.read_text(encoding="utf-8"))
    visa_code = draft["visa_code"]
    notice_round = draft["notice_round"]

    existing_row = find_existing_visa_row(visa_code)
    visa_id = existing_row["visa_id"] if existing_row else str(uuid.uuid4())
    from_round = None  # 전체 이력에서 정확한 직전 회차를 사람이 채우는 게 더 안전해 비워둠

    requirements_changes = diff_requirements(existing_row, draft["requirements"])
    criteria_diff = diff_criteria(visa_id if existing_row else None, draft.get("criteria", []))
    stages_recorded = is_round_already_recorded(
        visa_id if existing_row else None, notice_round, "visa_process_stages"
    )
    quota_recorded = is_round_already_recorded(
        visa_id if existing_row else None, notice_round, "visa_quota_status"
    )
    agency_warnings = check_agency_contacts(visa_code, draft.get("contacts", []))
    change_history_proposals = build_change_history_proposals(
        visa_id,
        from_round,
        notice_round,
        requirements_changes,
        criteria_diff,
        draft.get("source_document", ""),
        draft["requirements"].get("source_page", ""),
    )

    report_text = render_report(
        draft,
        existing_row,
        visa_id,
        requirements_changes,
        criteria_diff,
        stages_recorded,
        quota_recorded,
        agency_warnings,
        change_history_proposals,
    )

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORTS_DIR / f"notice_{notice_round}차_{visa_code}_review.md"
    report_path.write_text(report_text, encoding="utf-8")
    return report_path


def main() -> None:
    """CLI 진입점: draft JSON 경로를 받아 리뷰 리포트를 생성한다."""
    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8")  # Windows cp949 콘솔 출력 오류 방지

    parser = argparse.ArgumentParser(description="draft JSON과 기존 CSV를 비교해 리뷰 리포트 생성")
    parser.add_argument("draft_path", type=Path, help="Claude가 만든 draft JSON 경로")
    args = parser.parse_args()

    report_path = run(args.draft_path)
    print(f"리포트 생성됨 -> {report_path}")


if __name__ == "__main__":
    main()
