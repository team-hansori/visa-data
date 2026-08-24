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

`visa_criterion_groups`의 ROOT 유일성, 순환 참조, OR 그룹 최소 자식 수, 쿼터 스냅샷의
계산식 검증 같은 더 깊은 무결성 규칙(`plans/issue-44-common-schema-v2-migration.md`의
"검증기 세부 계약" 절)은 실제 마이그레이션 데이터가 준비되는 후속 작업(4~10단계)의
범위이며 이 스크립트에는 아직 없다 — task-3-brief.md의 "검증 항목" 목록에 없는 항목은
의도적으로 생략했다. 단, `visa_requirement_criteria`의 "AUTOMATED일 때 field_identifier/
operator 필수"는 docs/schema-v2.md의 컬럼 표 자체에 있는 필수 계약이라 여기 포함한다.

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
    SOURCE_RECORD_MAPPINGS,
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
            errors.extend(_check_criteria_conditional_requirements(table, row, i))
            errors.extend(_check_criteria_list_value_text_is_json(table, row, i))

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
