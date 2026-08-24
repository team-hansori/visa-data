"""공통 스키마 v2(13개 테이블)의 헤더·PK·FK·enum·형식·nullable 계약을 검증한다.

`scripts/schema_v2.py`의 스키마 정의를 단일 진실 공급원으로 삼아 실제 v2 CSV와
대조한다. v1 검증기(`scripts/validate_fk_integrity.py`)는 v1 `extraction/D_visa_requirements/`
를 그대로 검사하는 별도 진입점으로 남겨두고 이 스크립트에 합치지 않는다.

이 스크립트가 확인하는 항목(task-3-brief.md "검증 항목" 절 그대로):

- 파일 존재와 헤더 순서
- PK 공백·중복과 UUID 버전(v4), 그리고 공통 마스터 전체 기준 PK 전역 유일성
  (같은 UUID가 다른 테이블에 재사용되면 안 됨)
- FK 존재 여부
- enum, 날짜, 숫자, JSON 형식
- nullable/필수 필드 계약
- valid_from/valid_to 역전 여부
- 금지된 테이블·컬럼명, 논리 테이블명의 .csv 접미사 여부
- `visa_criterion_groups`의 ROOT 유일성, 부모-자식 visa_id 일치, 자기참조·순환참조,
  OR 그룹 최소 참여 자식 수(2개 이상)
- `document_attachment_relations`의 자기참조·순환 첨부관계
- `source_record_mappings.target_table`이 NONE sentinel이거나 실제 v2 13개 테이블명
  중 하나인지 여부
- `visa_quota_policies`/`visa_quota_snapshots`의 쿼터 산술(UNLIMITED policy에 snapshot이
  없는지, `consumed_quota`/`remaining_quota` 등식, 음수 금지) — nullable 숫자는 0으로
  치환해서 검산하지 않고 관련 값이 모두 있을 때만 등식을 적용한다.

`plans/issue-44-common-schema-v2-migration.md`의 "검증기 세부 계약" 절에서 처음에는
"실제 마이그레이션 데이터가 준비되는 후속 작업"으로 미뤄뒀던 항목들이지만, 이제 실제
이관 데이터가 있으므로 위 목록에 모두 구현되어 있다. 단, `visa_requirement_criteria`의
"AUTOMATED일 때 field_identifier/operator 필수"는 docs/schema-v2.md의 컬럼 표 자체에
있는 필수 계약이라 별도로 포함했다.

사용법: uv run python scripts/validate_common_schema_v2.py [--base-dir DIR]
"""

from __future__ import annotations

import argparse
import csv
import json
from datetime import date, datetime
from pathlib import Path

from scripts import schema_v2
from scripts.schema_v2 import (
    CHANGE_HISTORY,
    DOCUMENT_ATTACHMENT_RELATIONS,
    SOURCE_RECORD_MAPPINGS,
    VISA_CRITERION_GROUPS,
    VISA_QUOTA_POLICIES,
    VISA_QUOTA_SNAPSHOTS,
    VISA_REQUIREMENT_CRITERIA,
    ColumnKind,
    ColumnSpec,
    TableSpec,
)
from scripts.uuid_utils import UUIDGenerationError, validate_uuid4

DEFAULT_BASE_DIR = Path("extraction/common_v2")

# change_history.table_name, source_record_mappings.{source_table,target_table}은
# 값 자체가 "논리 테이블명"이므로 여기도 .csv 접미사 금지를 적용한다.
_TABLE_NAME_VALUE_COLUMNS: dict[str, tuple[str, ...]] = {
    CHANGE_HISTORY: ("table_name",),
    SOURCE_RECORD_MAPPINGS: ("source_table", "target_table"),
}


# --------------------------------------------------------------------------
# 형식 검사 헬퍼
# --------------------------------------------------------------------------


def _is_valid_date(value: str) -> bool:
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return True


def _is_valid_timestamp(value: str) -> bool:
    try:
        datetime.fromisoformat(value)
    except ValueError:
        return False
    return True


def _is_valid_numeric(value: str) -> bool:
    try:
        float(value)
    except ValueError:
        return False
    return True


def _is_valid_json_array(value: str) -> bool:
    try:
        parsed = json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return False
    return isinstance(parsed, list)


# --------------------------------------------------------------------------
# CSV 읽기
# --------------------------------------------------------------------------


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    """CSV 헤더와 행을 읽는다."""
    with path.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        return reader.fieldnames or [], list(reader)


# --------------------------------------------------------------------------
# 컬럼 단위 검사
# --------------------------------------------------------------------------


def _validate_column_value(table: TableSpec, col: ColumnSpec, value: str, line: int) -> list[str]:
    """PK/FK가 아닌 일반 컬럼 하나의 값이 nullable 계약과 형식을 만족하는지 검사한다.

    빈 문자열은 CSV상 SQL NULL과 같으므로, nullable 컬럼의 빈 값은 그 자체로 유효하며
    이후 형식 검사를 하지 않는다 — 빈 값을 0/""로 강제 치환하지 않는다는 계획 문서의
    원칙을 검증기 쪽에서 지키는 방식이다.
    """
    if value == "":
        if col.nullable:
            return []
        return [f"{table.filename}:{line} - 필수 필드 '{col.name}'가 비어 있음"]

    if col.kind == ColumnKind.UUID:
        try:
            validate_uuid4(value, col.name)
        except UUIDGenerationError as exc:
            return [f"{table.filename}:{line} - {exc}"]
    elif col.kind == ColumnKind.ENUM:
        allowed = col.enum_values or frozenset()
        if value not in allowed:
            return [
                f"{table.filename}:{line} - {col.name}={value!r}는 허용되지 않은 값 "
                f"(허용: {', '.join(sorted(allowed))})"
            ]
    elif col.kind == ColumnKind.DATE:
        if not _is_valid_date(value):
            return [
                f"{table.filename}:{line} - {col.name}={value!r}는 유효한 날짜(YYYY-MM-DD)가 아님"
            ]
    elif col.kind == ColumnKind.TIMESTAMP:
        if not (_is_valid_date(value) or _is_valid_timestamp(value)):
            return [f"{table.filename}:{line} - {col.name}={value!r}는 유효한 날짜/시각이 아님"]
    elif col.kind == ColumnKind.NUMERIC:
        if not _is_valid_numeric(value):
            return [f"{table.filename}:{line} - {col.name}={value!r}는 숫자가 아님"]
    elif col.kind == ColumnKind.JSON_ARRAY:
        if not _is_valid_json_array(value):
            return [f"{table.filename}:{line} - {col.name}={value!r}는 유효한 JSON 배열이 아님"]
    elif col.kind == ColumnKind.BOOLEAN:
        if value.lower() not in {"true", "false"}:
            return [f"{table.filename}:{line} - {col.name}={value!r}는 true/false가 아님"]
    return []


def _check_fk(
    table: TableSpec,
    row: dict[str, str],
    line: int,
    pk_sets: dict[str, set[str]],
) -> list[str]:
    """FK 컬럼 값이 대상 테이블의 검증된 PK 집합에 실제로 존재하는지 검사한다."""
    errors: list[str] = []
    for col in table.columns:
        if col.fk is None:
            continue
        value = row.get(col.name, "")
        if value == "":
            if not col.nullable:
                errors.append(f"{table.filename}:{line} - FK '{col.name}'가 비어 있음")
            continue
        target_pks = pk_sets.get(col.fk.table, set())
        if value not in target_pks:
            errors.append(
                f"{table.filename}:{line} - {col.name}={value}가 "
                f"{col.fk.table}.{col.fk.column}에 존재하지 않음"
            )
    return errors


def _check_valid_period(table: TableSpec, row: dict[str, str], line: int) -> list[str]:
    """valid_from/valid_to가 둘 다 있는 테이블에서 valid_to < valid_from이면 거부한다."""
    header = table.header
    if "valid_from" not in header or "valid_to" not in header:
        return []
    valid_from = row.get("valid_from", "")
    valid_to = row.get("valid_to", "")
    if not valid_from or not valid_to:
        return []
    if not (_is_valid_date(valid_from) and _is_valid_date(valid_to)):
        return []  # 형식 오류는 컬럼 검사에서 이미 잡힘 — 중복 보고하지 않음
    if date.fromisoformat(valid_to) < date.fromisoformat(valid_from):
        return [f"{table.filename}:{line} - valid_to({valid_to}) < valid_from({valid_from})"]
    return []


def _check_table_name_values(table: TableSpec, row: dict[str, str], line: int) -> list[str]:
    """table_name/source_table/target_table처럼 값 자체가 논리 테이블명인 컬럼에
    .csv 접미사가 없는지 검사한다."""
    columns = _TABLE_NAME_VALUE_COLUMNS.get(table.name, ())
    errors: list[str] = []
    for col_name in columns:
        value = row.get(col_name, "")
        if value.endswith(".csv"):
            errors.append(
                f"{table.filename}:{line} - {col_name}={value!r}에 .csv 접미사가 있으면 안 됨"
            )
    return errors


# source_record_mappings.target_table에서 "이관 대상 테이블 없음"을 뜻하는 명시적 sentinel.
# 빈 문자열과 구분되는 값으로, 원천 행을 검토했지만 공통 마스터로 옮길 데이터 자체가
# 없다는 것을 밝히는 감사 기록이다(docs/schema-v2.md §13, plan "출처·매핑" 절).
TARGET_TABLE_NONE_SENTINEL = "NONE"


def _check_target_table_is_real_table_name(
    table: TableSpec, row: dict[str, str], line: int
) -> list[str]:
    """source_record_mappings.target_table이 채워져 있고 NONE sentinel이 아니면
    실제 v2 13개 테이블 논리명 중 하나여야 한다(plan "검증기 세부 계약 > 출처·매핑" 절 —
    "mapping action/status 조합과 대상 테이블 계약을 검사한다"의 대상 테이블 부분).

    이 검사가 없으면 예전 `scoring_items`(→ 실제로는 `visa_scoring_items`/
    `visa_scoring_models`)나 `visa_quota_status`(v1 이름, v2는 `visa_quota_snapshots`)처럼
    존재하지 않는 테이블명이 장부에 조용히 섞여 들어가도 잡히지 않는다.
    """
    if table.name != SOURCE_RECORD_MAPPINGS:
        return []
    value = row.get("target_table", "")
    if value == "" or value == TARGET_TABLE_NONE_SENTINEL:
        return []
    if value not in schema_v2.TABLE_ORDER:
        return [
            f"{table.filename}:{line} - target_table={value!r}는 실제 v2 테이블명이 아님 "
            f"(허용: {TARGET_TABLE_NONE_SENTINEL} 또는 {', '.join(schema_v2.TABLE_ORDER)})"
        ]
    return []


def _check_criteria_conditional_requirements(
    table: TableSpec, row: dict[str, str], line: int
) -> list[str]:
    """visa_requirement_criteria: evaluation_mode=AUTOMATED면 field_identifier와
    operator가 필수라는 계약(docs/schema-v2.md 4번 테이블 컬럼 표에 명시)을 검사한다.

    이 규칙은 별도 "무결성 규칙" 절이 아니라 컬럼 자체의 필수 표시("AUTOMATED일 때 O")에
    있으므로 nullable/필수 필드 계약의 일부로 취급한다.
    """
    if table.name != VISA_REQUIREMENT_CRITERIA:
        return []
    errors: list[str] = []
    if row.get("evaluation_mode", "") == "AUTOMATED":
        if not row.get("field_identifier", ""):
            errors.append(
                f"{table.filename}:{line} - evaluation_mode=AUTOMATED인데 "
                "field_identifier가 비어 있음"
            )
        if not row.get("operator", ""):
            errors.append(
                f"{table.filename}:{line} - evaluation_mode=AUTOMATED인데 operator가 비어 있음"
            )
    return errors


def _check_criteria_list_value_text_is_json(
    table: TableSpec, row: dict[str, str], line: int
) -> list[str]:
    """visa_requirement_criteria: criteria_type=LIST면 value_text가 유효한 JSON 배열
    문자열이어야 한다는 계약(docs/schema-v2.md "목록 조건" 절)을 검사한다."""
    if table.name != VISA_REQUIREMENT_CRITERIA:
        return []
    if row.get("criteria_type", "") != "LIST":
        return []
    value_text = row.get("value_text", "")
    if not value_text:
        return []  # value_text 자체가 비어있으면 필수 필드 검사에서 이미 잡힘
    if not _is_valid_json_array(value_text):
        return [
            f"{table.filename}:{line} - criteria_type=LIST인데 value_text가 유효한 "
            f"JSON 배열이 아님: {value_text!r}"
        ]
    return []


# --------------------------------------------------------------------------
# 그룹 트리 / 첨부관계 무결성 검사 (docs/schema-v2.md §3, §9)
#
# task-3에서 "실제 마이그레이션 데이터가 준비되는 후속 작업(4~10단계)의 범위"로 명시적으로
# 미룬 항목들(ROOT 유일성, 순환참조, OR 그룹 최소 자식 수)을 여기서 구현한다. 이제 실제
# 이관 데이터(`extraction/common_v2/`)가 있으므로 이 검사들을 건너뛸 이유가 없다.
# --------------------------------------------------------------------------


def _detect_cycles(edges: dict[str, list[str]]) -> list[list[str]]:
    """방향 그래프에서 사이클을 찾아 노드 리스트로 반환한다(자기참조도 길이 1 사이클로 포함).

    ``edges``는 {node: [neighbor, ...]} 형태의 인접 리스트다. 3-color DFS로 순회하며,
    한 사이클에 속한 노드는 어느 시작점에서 순회하든 한 번만 보고한다(같은 사이클을
    여러 번 중복 보고하지 않기 위함). 존재하지 않는 노드를 가리키는 엣지는 조용히
    무시한다 — 그 문제는 FK 검사(`_check_fk`)가 별도로 잡는다.
    """
    WHITE, GRAY, BLACK = 0, 1, 2
    color: dict[str, int] = dict.fromkeys(edges, WHITE)
    cycles: list[list[str]] = []
    reported_nodes: set[str] = set()

    def dfs(node: str, stack: list[str]) -> None:
        color[node] = GRAY
        stack.append(node)
        for neighbor in edges.get(node, []):
            if neighbor not in color:
                continue
            if color[neighbor] == WHITE:
                dfs(neighbor, stack)
            elif color[neighbor] == GRAY:
                idx = stack.index(neighbor)
                cycle = stack[idx:]
                if not (set(cycle) & reported_nodes):
                    cycles.append(cycle)
                    reported_nodes.update(cycle)
        stack.pop()
        color[node] = BLACK

    for node in list(edges):
        if color[node] == WHITE:
            dfs(node, [])
    return cycles


def _check_criterion_group_tree_integrity(
    tables_rows: dict[str, list[dict[str, str]]],
) -> list[str]:
    """visa_criterion_groups의 트리 무결성을 검사한다(docs/schema-v2.md §3 "무결성 규칙").

    - 비자별 ROOT 그룹(parent_group_id가 빈 값)이 정확히 하나여야 한다.
    - 자식 그룹의 visa_id는 부모 그룹의 visa_id와 같아야 한다.
    - group_id == parent_group_id 자기참조를 허용하지 않는다.
    - parent_group_id 체인에 순환참조가 없어야 한다.
    - OR 그룹은 판정에 참여하는 항목(직속 criteria 중 evaluation_mode != INFORMATIONAL
      + 자식 그룹)이 2개 이상이어야 한다.
    """
    errors: list[str] = []
    table = schema_v2.SCHEMA_V2[VISA_CRITERION_GROUPS]
    rows = tables_rows.get(VISA_CRITERION_GROUPS, [])
    if not rows:
        return errors

    by_id: dict[str, dict[str, str]] = {
        row["group_id"]: row for row in rows if row.get("group_id", "")
    }

    # ROOT 유일성: parent_group_id가 빈 값인 그룹을 비자별로 묶어 정확히 1개인지 확인.
    roots_by_visa: dict[str, list[str]] = {}
    for row in rows:
        if row.get("parent_group_id", "") == "":
            roots_by_visa.setdefault(row.get("visa_id", ""), []).append(row.get("group_id", ""))
    for visa_id, root_ids in roots_by_visa.items():
        if len(root_ids) != 1:
            errors.append(
                f"{table.filename} - visa_id={visa_id}의 ROOT 그룹이 {len(root_ids)}개임"
                f"(정확히 1개여야 함): {root_ids}"
            )

    # 자기참조 + 부모-자식 visa_id 일치.
    for i, row in enumerate(rows, start=2):
        group_id = row.get("group_id", "")
        parent_id = row.get("parent_group_id", "")
        if not parent_id:
            continue
        if group_id == parent_id:
            errors.append(
                f"{table.filename}:{i} - group_id와 parent_group_id가 동일함(자기참조): {group_id}"
            )
        parent_row = by_id.get(parent_id)
        if parent_row is not None and parent_row.get("visa_id", "") != row.get("visa_id", ""):
            errors.append(
                f"{table.filename}:{i} - group_id={group_id}의 visa_id가 "
                f"부모 그룹({parent_id})의 visa_id와 다름"
            )

    # 순환참조: 자식 -> 부모 방향 엣지로 그래프를 구성해 검사한다.
    edges: dict[str, list[str]] = {
        group_id: ([row["parent_group_id"]] if row.get("parent_group_id", "") else [])
        for group_id, row in by_id.items()
    }
    for cycle in _detect_cycles(edges):
        errors.append(
            f"{table.filename} - parent_group_id 체인에 순환참조 발견: "
            f"{' -> '.join([*cycle, cycle[0]])}"
        )

    # OR 그룹 최소 참여 자식 수(직속 criteria 중 INFORMATIONAL 제외 + 자식 그룹) >= 2.
    criteria_rows = tables_rows.get(VISA_REQUIREMENT_CRITERIA, [])
    participating_criteria_count: dict[str, int] = {}
    for crow in criteria_rows:
        if crow.get("evaluation_mode", "") == "INFORMATIONAL":
            continue
        gid = crow.get("group_id", "")
        if gid:
            participating_criteria_count[gid] = participating_criteria_count.get(gid, 0) + 1

    child_group_count: dict[str, int] = {}
    for row in rows:
        parent_id = row.get("parent_group_id", "")
        if parent_id:
            child_group_count[parent_id] = child_group_count.get(parent_id, 0) + 1

    for row in rows:
        if row.get("boolean_operator", "") != "OR":
            continue
        group_id = row.get("group_id", "")
        total = participating_criteria_count.get(group_id, 0) + child_group_count.get(group_id, 0)
        if total < 2:
            errors.append(
                f"{table.filename} - OR 그룹 group_id={group_id}"
                f"({row.get('group_key', '')})의 판정 참여 자식 수가 {total}개임"
                "(2개 이상이어야 함)"
            )

    return errors


def _quota_numeric(row: dict[str, str], col_name: str) -> float | None:
    """쿼터 숫자 컬럼 값을 float로 반환한다. 빈 값은 None(= 미확인, 0이 아님)으로
    돌려준다. 형식 오류(숫자가 아님)는 `_validate_column_value`가 이미 별도로 보고하므로
    여기서는 조용히 None으로 취급해 중복 보고하지 않는다."""
    value = row.get(col_name, "")
    if value == "":
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _check_quota_arithmetic(
    tables_rows: dict[str, list[dict[str, str]]],
) -> list[str]:
    """쿼터 정책·스냅샷의 산술·정합성 규칙을 검사한다(plan "검증기 세부 계약 > 쿼터" 절,
    docs/schema-v2.md §10~11 "확정 규칙"/"추가 적용 원칙").

    - `UNLIMITED` policy에는 연결된 snapshot이 하나도 없어야 한다.
    - `recommended_count`/`quota_exempt_count`처럼 nullable인 숫자는 0으로 치환해서
      검산하지 않는다 — 관련 값이 전부 존재할 때만 등식을 검사한다.
    - 값이 모두 있을 때: `consumed_quota == recommended_count - quota_exempt_count`.
    - `allocated_quota`/`consumed_quota`가 있을 때: `remaining_quota ==
      allocated_quota - consumed_quota`.
    - 쿼터 관련 숫자 컬럼은 모두 음수가 아니어야 한다.
    """
    errors: list[str] = []
    snapshot_table = schema_v2.SCHEMA_V2[VISA_QUOTA_SNAPSHOTS]
    policy_rows = tables_rows.get(VISA_QUOTA_POLICIES, [])
    snapshot_rows = tables_rows.get(VISA_QUOTA_SNAPSHOTS, [])

    # UNLIMITED policy는 snapshot을 가지면 안 된다.
    unlimited_policy_ids = {
        row["quota_policy_id"]
        for row in policy_rows
        if row.get("quota_type", "") == "UNLIMITED" and row.get("quota_policy_id", "")
    }
    if unlimited_policy_ids:
        for i, row in enumerate(snapshot_rows, start=2):
            policy_id = row.get("quota_policy_id", "")
            if policy_id in unlimited_policy_ids:
                errors.append(
                    f"{snapshot_table.filename}:{i} - quota_policy_id={policy_id}는 "
                    f"UNLIMITED policy인데 snapshot이 존재함(UNLIMITED는 snapshot을 가지면 안 됨)"
                )

    numeric_cols = (
        "allocated_quota",
        "recommended_count",
        "quota_exempt_count",
        "consumed_quota",
        "remaining_quota",
    )
    for i, row in enumerate(snapshot_rows, start=2):
        values = {col: _quota_numeric(row, col) for col in numeric_cols}

        # 음수 금지(값이 있는 컬럼만).
        for col, val in values.items():
            if val is not None and val < 0:
                errors.append(
                    f"{snapshot_table.filename}:{i} - {col}={val!r}가 음수임"
                    "(쿼터 수량은 음수일 수 없음)"
                )

        allocated, recommended, exempt, consumed, remaining = (
            values["allocated_quota"],
            values["recommended_count"],
            values["quota_exempt_count"],
            values["consumed_quota"],
            values["remaining_quota"],
        )

        # consumed_quota = recommended_count - quota_exempt_count (세 값 모두 있을 때만)
        if recommended is not None and exempt is not None and consumed is not None:
            expected = recommended - exempt
            if consumed != expected:
                errors.append(
                    f"{snapshot_table.filename}:{i} - consumed_quota={consumed!r}가 "
                    f"recommended_count({recommended!r}) - quota_exempt_count({exempt!r}) = "
                    f"{expected!r}와 다름"
                )

        # remaining_quota = allocated_quota - consumed_quota (둘 다 있을 때만)
        if allocated is not None and consumed is not None and remaining is not None:
            expected = allocated - consumed
            if remaining != expected:
                errors.append(
                    f"{snapshot_table.filename}:{i} - remaining_quota={remaining!r}가 "
                    f"allocated_quota({allocated!r}) - consumed_quota({consumed!r}) = "
                    f"{expected!r}와 다름"
                )

    return errors


def _check_document_attachment_relation_integrity(
    tables_rows: dict[str, list[dict[str, str]]],
) -> list[str]:
    """document_attachment_relations의 자기참조·순환 첨부관계를 검사한다.

    docs/schema-v2.md §9 제약조건: ``parent_document_id != attachment_document_id``,
    순환 첨부관계 금지. 2행짜리 실제 데이터에서는 순환이 물리적으로 불가능하지만,
    행 수와 무관하게 일반적인 그래프 사이클 검사로 구현한다.
    """
    errors: list[str] = []
    table = schema_v2.SCHEMA_V2[DOCUMENT_ATTACHMENT_RELATIONS]
    rows = tables_rows.get(DOCUMENT_ATTACHMENT_RELATIONS, [])
    if not rows:
        return errors

    for i, row in enumerate(rows, start=2):
        parent_id = row.get("parent_document_id", "")
        attachment_id = row.get("attachment_document_id", "")
        if parent_id and parent_id == attachment_id:
            errors.append(
                f"{table.filename}:{i} - parent_document_id와 attachment_document_id가 "
                f"동일함(자기참조): {parent_id}"
            )

    edges: dict[str, list[str]] = {}
    for row in rows:
        parent_id = row.get("parent_document_id", "")
        attachment_id = row.get("attachment_document_id", "")
        if not parent_id or not attachment_id:
            continue
        edges.setdefault(parent_id, []).append(attachment_id)
        edges.setdefault(attachment_id, [])

    for cycle in _detect_cycles(edges):
        errors.append(
            f"{table.filename} - document_attachment_relations에 순환 첨부관계 발견: "
            f"{' -> '.join([*cycle, cycle[0]])}"
        )

    return errors


# --------------------------------------------------------------------------
# 테이블 단위 / 전체 검증
# --------------------------------------------------------------------------


def validate_all(tables_rows: dict[str, list[dict[str, str]]]) -> list[str]:
    """이미 메모리에 있는 {테이블 논리명: 행 목록}을 검증한다(파일 I/O 없음).

    테스트에서 파일을 거치지 않고 fixture 행을 바로 검증할 때 쓴다. 파일 존재/헤더
    순서 검사는 ``validate_directory``에서만 한다.
    """
    errors: list[str] = []
    errors.extend(schema_v2.check_no_forbidden_names())
    errors.extend(schema_v2.check_no_csv_suffix_in_logical_names())

    # 1) PK 검사 + 전역(테이블 간) UUID 유일성 집계
    pk_sets: dict[str, set[str]] = {}
    pk_locations: dict[str, list[str]] = {}
    for table_name, rows in tables_rows.items():
        table = schema_v2.SCHEMA_V2[table_name]
        pk_values: set[str] = set()
        for i, row in enumerate(rows, start=2):
            value = row.get(table.pk, "")
            if not value:
                errors.append(f"{table.filename}:{i} - PK '{table.pk}'가 비어 있음")
                continue
            try:
                validate_uuid4(value, table.pk)
            except UUIDGenerationError as exc:
                errors.append(f"{table.filename}:{i} - {exc}")
                continue
            pk_values.add(value)
            pk_locations.setdefault(value, []).append(f"{table.name}:{i}")
        pk_sets[table_name] = pk_values

    for value, locations in pk_locations.items():
        if len(locations) > 1:
            errors.append(
                f"UUID {value}가 공통 마스터 전체에서 중복 사용됨: {', '.join(locations)}"
            )

    # 2) 컬럼별 형식/nullable, FK, valid_from/valid_to, 특수 규칙 검사
    for table_name, rows in tables_rows.items():
        table = schema_v2.SCHEMA_V2[table_name]
        for i, row in enumerate(rows, start=2):
            for col in table.columns:
                if col.name == table.pk or col.fk is not None:
                    continue  # PK는 위에서, FK는 아래 _check_fk에서 별도 처리
                value = row.get(col.name, "")
                errors.extend(_validate_column_value(table, col, value, i))
            errors.extend(_check_fk(table, row, i, pk_sets))
            errors.extend(_check_valid_period(table, row, i))
            errors.extend(_check_table_name_values(table, row, i))
            errors.extend(_check_target_table_is_real_table_name(table, row, i))
            errors.extend(_check_criteria_conditional_requirements(table, row, i))
            errors.extend(_check_criteria_list_value_text_is_json(table, row, i))

    # 3) 그룹 트리 / 첨부관계 / 쿼터처럼 여러 테이블·행을 함께 봐야 하는 무결성 규칙
    errors.extend(_check_criterion_group_tree_integrity(tables_rows))
    errors.extend(_check_document_attachment_relation_integrity(tables_rows))
    errors.extend(_check_quota_arithmetic(tables_rows))

    return errors


def validate_directory(base_dir: Path) -> list[str]:
    """base_dir 아래 13개 v2 CSV 파일의 존재·헤더 순서를 확인한 뒤 내용을 검증한다."""
    errors: list[str] = []
    tables_rows: dict[str, list[dict[str, str]]] = {}

    for table_name in schema_v2.TABLE_ORDER:
        table = schema_v2.SCHEMA_V2[table_name]
        path = base_dir / table.filename
        if not path.exists():
            errors.append(f"{path} - 파일이 없음")
            continue
        header, rows = read_csv(path)
        if header != table.header:
            errors.append(f"{path} - 헤더가 스키마와 다름: {header} != {table.header}")
            continue
        tables_rows[table_name] = rows

    errors.extend(validate_all(tables_rows))
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="공통 스키마 v2(13개 테이블) 검증기")
    parser.add_argument("--base-dir", type=Path, default=DEFAULT_BASE_DIR)
    args = parser.parse_args()

    errors = validate_directory(args.base_dir)
    if errors:
        print(f"v2 스키마 검증 실패: {len(errors)}건")
        for error in errors:
            print(f"  - {error}")
        return 1

    print("v2 스키마 검증 통과: 문제 없음")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
