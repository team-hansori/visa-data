"""
D_visa_requirements 공유 마스터 테이블 간 PK 유일성과 FK 참조 무결성을 검사한다.
CSV는 DB가 아니라 FK 제약이 걸려있지 않으므로, 여러 담당자가 나눠서 편집하다 참조가
어긋나는 문제를 이 스크립트가 대신 잡아낸다.

사용법: uv run python scripts/validate_fk_integrity.py
"""

from __future__ import annotations

import csv
import sys
from dataclasses import dataclass, field
from pathlib import Path

from scripts.reference_schema import AGENCY_TYPE_VALUES

D_DIR = Path("extraction/D_visa_requirements")
REFERENCE_DIR = Path("reference")
STAGE_STATUS_COLUMN = "document_requirements_status"
# 허용값 추가
ALLOWED_DOCUMENT_REQUIREMENTS_STATUSES = frozenset(
    {
        "not_checked",
        "present",
        "explicitly_none",
    }  # 통과, 문서 존재 여부 추가 검사, 문서 미존재 여부 추가 검사
)


@dataclass(frozen=True)
class TableSpec:
    """검사 대상 테이블 하나의 정의."""

    path: Path
    pk: str | None  # PK 컬럼명. 없으면 None(PK 유일성 검사를 건너뜀)
    # {FK 컬럼명: (참조할 부모 테이블 경로, 부모 테이블에서 조회할 컬럼명)}
    # 부모 조회 컬럼은 부모의 PK가 아닐 수도 있다(예: agency_contacts.category_minor).
    fks: dict[str, tuple[Path, str]] = field(default_factory=dict)
    required_columns: tuple[str, ...] = ()  # 필수 컬럼 추가
    # {FK 컬럼명: (조건 컬럼명, 조건 값)}. 조건 컬럼이 조건 값과 같을 때만 해당 FK 컬럼의
    # 빈 값을 에러로 보지 않는다 (예: EXTERNAL 라우팅의 target_agency_category는 "해당
    # 없음"을 의미하는 정상적인 빈 값 — reference/README.md NULL 규약 참고). 조건이
    # 성립하지 않는데 값이 비어 있으면(예: IN_DOMAIN 행의 target_agency_category) 그대로
    # 에러로 처리한다. 값이 존재하는 경우에는 조건과 무관하게 항상 부모 테이블에 대해
    # 검사한다.
    nullable_fks: dict[str, tuple[str, str]] = field(default_factory=dict)


def default_tables(base_dir: Path = D_DIR) -> list[TableSpec]:
    """D_visa_requirements 폴더의 기본 테이블·FK 구성. 새 공유 테이블이 생기면 여기에 추가한다."""
    visa_requirements = base_dir / "visa_requirements.csv"
    visa_process_stages = base_dir / "visa_process_stages.csv"
    return [
        TableSpec(visa_requirements, pk="visa_id"),
        TableSpec(
            base_dir / "visa_requirement_criteria.csv",
            pk="criteria_id",
            fks={"visa_id": (visa_requirements, "visa_id")},
        ),
        TableSpec(
            visa_process_stages,
            pk="stage_id",
            fks={"visa_id": (visa_requirements, "visa_id")},
            required_columns=(STAGE_STATUS_COLUMN,),  # visa_process_stages에 상태 컬럼 지정
        ),
        TableSpec(
            base_dir / "document_requirements.csv",
            pk="document_requirement_id",
            fks={"stage_id": (visa_process_stages, "stage_id")},
        ),
        TableSpec(
            base_dir / "visa_quota_status.csv",
            pk="quota_status_id",
            fks={"visa_id": (visa_requirements, "visa_id")},
        ),
        TableSpec(
            base_dir / "change_history.csv",
            pk="change_id",
            fks={"visa_id": (visa_requirements, "visa_id")},
        ),
    ]


def reference_tables(base_dir: Path = REFERENCE_DIR) -> list[TableSpec]:
    """reference/ 폴더의 서비스·라우팅 테이블 구성. 새 참조 테이블이 생기면 여기에 추가한다."""
    agency_contacts = base_dir / "agency_contacts.csv"
    risk_keyword_messages = base_dir / "risk_keyword_messages.csv"
    return [
        TableSpec(
            agency_contacts,
            pk="agency_id",
            # 지도 기능용 신규 컬럼 — 헤더 존재만 검사(값 규칙은
            # check_agency_contacts_map_columns가 별도로 검사).
            required_columns=(
                "agency_type",
                "sido",
                "sigungu",
                "eupmyeondong",
                "road_address",
                "latitude",
                "longitude",
                "geocode_method",
                "geocoded_at",
                "operating_hours",
                "is_active",
                "source_url",
            ),
        ),
        TableSpec(
            risk_keyword_messages,
            pk=None,  # keyword_category+resolution_type 복합키라 단일 PK 검사는 건너뜀
        ),
        TableSpec(
            base_dir / "risk_routing_table.csv",
            pk="routing_id",
            fks={"target_agency_category": (agency_contacts, "category_minor")},
            required_columns=("message_addendum",),
            # resolution_type=EXTERNAL 행에 한해서만 target_agency_category가 "해당 없음"이라
            # 비어 있는 것이 정상(reference/README.md NULL 규약). resolution_type=IN_DOMAIN
            # 행은 항상 채워야 하므로 빈 값이면 에러로 잡는다. 값이 있는 행(IN_DOMAIN)은
            # agency_contacts.category_minor에 존재해야 하므로 그 검사는 그대로 적용된다.
            nullable_fks={"target_agency_category": ("resolution_type", "EXTERNAL")},
        ),
    ]


def read_rows(path: Path) -> list[dict[str, str]]:
    """CSV를 읽어 행 딕셔너리 리스트로 반환한다. 파일이 없으면 빈 리스트.

    utf-8-sig로 열어 파일 앞에 BOM(byte-order mark)이 있어도 첫 컬럼명이
    깨지지 않게 한다. BOM이 없는 파일은 일반 utf-8과 동일하게 동작한다.
    """
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def read_fieldnames(path: Path) -> list[str] | None:
    """CSV 헤더를 읽어 컬럼명 리스트를 반환한다. 파일이 없으면 None, 빈 파일이면 빈 리스트.

    utf-8-sig로 열어 BOM이 첫 컬럼명에 섞여 들어가지 않게 한다.
    """
    if not path.exists():
        return None
    with path.open(newline="", encoding="utf-8-sig") as f:
        return next(csv.reader(f), [])


def check_required_columns(table: TableSpec, fieldnames: list[str]) -> list[str]:
    """PK/FK로 쓰는 컬럼이 실제 헤더에 있는지 검사한다.

    여기서 걸러내지 않으면 이후 row[column] 접근에서 KeyError가 나거나,
    row.get(column)이 조용히 빈 값으로 처리돼 "값이 비어 있음"이라는 오해를
    주는 대량의 행별 에러로 원인이 묻힌다 — 컬럼 자체가 없다는 걸 파일당
    하나의 명확한 에러로 먼저 보고한다.
    """
    required = (
        ([table.pk] if table.pk else [])
        + list(table.fks.keys())
        + list(table.required_columns)  # PK, FK뿐 아니라 테이블별 추가 필수 컬럼도 검사
    )
    return [
        f"{table.path} - 필수 컬럼 '{column}'이 헤더에 없음"
        for column in required
        if column not in fieldnames
    ]


def collect_lookup_sets(tables: list[TableSpec]) -> dict[tuple[Path, str], set[str]]:
    """FK가 참조하는 (부모 테이블 경로, 부모 조회 컬럼) 조합별 값 집합을 미리 모아둔다.

    부모 조회 컬럼은 부모 테이블의 PK와 다를 수 있으므로(예: agency_contacts.category_minor),
    각 테이블의 fks 값에 등장하는 (경로, 컬럼) 조합을 기준으로 직접 모은다.
    """
    lookup_sets: dict[tuple[Path, str], set[str]] = {}
    for table in tables:
        for parent_path, parent_column in table.fks.values():
            key = (parent_path, parent_column)
            if key in lookup_sets:
                continue
            rows = read_rows(parent_path)
            lookup_sets[key] = {row[parent_column] for row in rows if row.get(parent_column)}
    return lookup_sets


def check_pk_uniqueness(table: TableSpec, rows: list[dict[str, str]]) -> list[str]:
    """PK가 비어있거나 같은 값이 두 번 이상 나오면 에러로 기록한다."""
    if table.pk is None:
        return []
    errors: list[str] = []
    seen: dict[str, int] = {}
    for i, row in enumerate(rows, start=2):  # 1행은 헤더이므로 데이터는 2행부터
        value = row.get(table.pk, "")
        if not value:
            errors.append(f"{table.path}:{i} - {table.pk}가 비어 있음")
            continue
        seen[value] = seen.get(value, 0) + 1
    for value, count in seen.items():
        if count > 1:
            errors.append(f"{table.path} - {table.pk}={value} 중복 {count}회")
    return errors


def check_fk_integrity(
    table: TableSpec, rows: list[dict[str, str]], lookup_sets: dict[tuple[Path, str], set[str]]
) -> list[str]:
    """FK 컬럼 값이 참조 테이블의 지정된 조회 컬럼 값 집합에 실제로 존재하는지 검사한다.

    table.nullable_fks에 포함된 FK 컬럼은, 지정된 조건 컬럼이 조건 값과 같을 때만 값이
    비어 있어도 에러로 보지 않는다(예: resolution_type=EXTERNAL인 행의
    target_agency_category="해당 없음"). 조건이 성립하지 않는데 값이 비어 있으면(예:
    resolution_type=IN_DOMAIN인데 target_agency_category가 빈 값) 그대로 에러로 처리한다.
    값이 존재하면 그 값은 여전히 부모 테이블에 대해 정상적으로 검사한다.
    """
    errors: list[str] = []
    for fk_column, (parent_path, parent_column) in table.fks.items():
        parent_values = lookup_sets.get((parent_path, parent_column), set())
        for i, row in enumerate(rows, start=2):
            value = row.get(fk_column, "")
            if not value:
                condition = table.nullable_fks.get(fk_column)
                if condition is not None:
                    condition_column, condition_value = condition
                    if row.get(condition_column) == condition_value:
                        continue
                errors.append(f"{table.path}:{i} - {fk_column}가 비어 있음")
                continue
            if value not in parent_values:
                errors.append(
                    f"{table.path}:{i} - {fk_column}={value}가 "
                    f"{parent_path}의 {parent_column}에 존재하지 않음"
                )
    return errors


STAGES_FILENAME = "visa_process_stages.csv"
DOCUMENT_REQUIREMENTS_FILENAME = "document_requirements.csv"


def check_document_requirements_status(
    stages_path: Path, document_requirements_path: Path
) -> list[str]:
    """visa_process_stages.document_requirements_status가 document_requirements의
    실제 행 존재 여부와 맞는지 검사한다: `present`는 해당 stage_id 행이 1개 이상,
    `explicitly_none`은 0개여야 한다 ("이 단계엔 서류가 없다"고 명시했는데 실제로
    행이 있으면 모순이므로).
    """
    stage_rows = read_rows(stages_path)
    if not stage_rows:
        return []
    document_rows = read_rows(document_requirements_path)
    stage_ids_with_documents = {row["stage_id"] for row in document_rows if row.get("stage_id")}

    errors: list[str] = []
    for i, row in enumerate(stage_rows, start=2):
        status = row.get(
            STAGE_STATUS_COLUMN, ""
        )  # 현재 단계의 제출서류 상태를 읽고, 값이 없으면 빈 문자열로 처리
        stage_id = row.get("stage_id", "")  # 현재 절차 단계의 ID를 읽음 -> 제출서류 테이블 조회용

        if (
            status not in ALLOWED_DOCUMENT_REQUIREMENTS_STATUSES
        ):  # 상태값이 허용된 3가지 중 하나인지 확인
            errors.append(  # 잘못된 상태값 error 목록에 추가
                f"{stages_path}:{i} - 허용되지 않은 {STAGE_STATUS_COLUMN} 값: {status!r}"
            )
            continue  # 잘못된 상태값은 더 이상 검사하지 않고 다음 단계 행으로 넘어감

        has_documents = (
            stage_id in stage_ids_with_documents
        )  # 현재 단계에 제출서류가 연결되어 있는지 확인

        # 상태와 실제 데이터가 일치하는지 검사 (not_checked는 확인하지 않은 상태이므로 오류를 내지 않음)
        if status == "present" and not has_documents:
            errors.append(
                f"{stages_path}:{i} - {STAGE_STATUS_COLUMN}=present이지만 "
                f"{document_requirements_path}에 stage_id={stage_id}인 행이 없음"
            )
        elif status == "explicitly_none" and has_documents:
            errors.append(
                f"{stages_path}:{i} - {STAGE_STATUS_COLUMN}=explicitly_none이지만 "
                f"{document_requirements_path}에 stage_id={stage_id}인 행이 있음"
            )
    return errors


RISK_ROUTING_FILENAME = "risk_routing_table.csv"
RISK_KEYWORD_MESSAGES_FILENAME = "risk_keyword_messages.csv"


def check_risk_message_coverage(routing_path: Path, messages_path: Path) -> list[str]:
    """risk_routing_table.csv의 (keyword_category, resolution_type) 조합이
    risk_keyword_messages.csv에 boilerplate 행으로 존재하는지, 그리고
    risk_keyword_messages.csv 자체에 같은 조합의 중복 행이 없는지 검사한다.

    risk_keyword_messages.csv는 (keyword_category, resolution_type) 복합키라 단일
    컬럼 PK 유일성 검사(check_pk_uniqueness)로는 중복을 잡을 수 없다 — 그래서 이 두
    검사를 함께 여기서 처리한다.
    """
    routing_rows = read_rows(routing_path)
    message_rows = read_rows(messages_path)

    errors: list[str] = []

    # risk_keyword_messages.csv 자체의 (keyword_category, resolution_type) 중복 검사
    seen: dict[tuple[str, str], int] = {}
    for row in message_rows:
        key = (row.get("keyword_category", ""), row.get("resolution_type", ""))
        seen[key] = seen.get(key, 0) + 1
    for key, count in seen.items():
        if count > 1:
            errors.append(
                f"{messages_path} - (keyword_category, resolution_type)={key} 중복 {count}회"
            )

    # risk_routing_table.csv의 각 조합이 risk_keyword_messages.csv에 존재하는지 검사
    message_keys = set(seen.keys())
    for i, row in enumerate(routing_rows, start=2):
        key = (row.get("keyword_category", ""), row.get("resolution_type", ""))
        if key not in message_keys:
            errors.append(
                f"{routing_path}:{i} - (keyword_category, resolution_type)={key}에 대응하는 "
                f"boilerplate 행이 {messages_path}에 없음"
            )
    return errors


AGENCY_CONTACTS_FILENAME = "agency_contacts.csv"
COORDINATE_METADATA_COLUMNS = (
    "agency_type",
    "road_address",
    "sido",
    "sigungu",
    "geocode_method",
    "geocoded_at",
)


def check_agency_contacts_map_columns(path: Path) -> list[str]:
    """agency_contacts.csv의 지도 기능용 신규 컬럼이 docs/map-agency-schema.md §1.5/§1.6
    규칙을 지키는지 검사한다: agency_type enum, is_active 값, 좌표 페어링, 좌표가 있으면
    필수 메타데이터(§1.5의 DB CHECK와 동일하게 좌표 기준 — agency_type 기준이 아님)."""
    rows = read_rows(path)
    errors: list[str] = []
    for i, row in enumerate(rows, start=2):
        agency_type = row.get("agency_type", "")
        if agency_type and agency_type not in AGENCY_TYPE_VALUES:
            errors.append(f"{path}:{i} - agency_type={agency_type!r}가 허용된 enum이 아님")

        is_active = row.get("is_active", "")
        if is_active not in ("true", "false"):
            errors.append(f"{path}:{i} - is_active 값이 'true'/'false'가 아님: {is_active!r}")

        latitude = row.get("latitude", "")
        longitude = row.get("longitude", "")
        if bool(latitude) != bool(longitude):
            errors.append(f"{path}:{i} - latitude/longitude 중 한쪽만 비어 있음")

        if latitude:
            for column in COORDINATE_METADATA_COLUMNS:
                if not row.get(column, ""):
                    errors.append(f"{path}:{i} - latitude가 있는데 {column}이 비어 있음")
    return errors


def validate(tables: list[TableSpec]) -> list[str]:
    """모든 테이블에 대해 필수 컬럼 존재, PK 유일성, FK 참조 무결성을 검사하고 에러 목록을 반환한다."""
    errors: list[str] = []

    # 헤더에 PK/FK로 쓰는 컬럼이 있는지 먼저 확인한다 — 없는 테이블은 이후 단계에서
    # KeyError로 죽거나 row.get()이 조용히 빈 값 처리하는 걸 막기 위해 여기서 걸러낸다.
    checkable_tables: list[TableSpec] = []
    for table in tables:
        fieldnames = read_fieldnames(table.path)
        if fieldnames is None:  # 파일 자체가 없음 - 기존 동작대로 조용히 건너뜀
            continue
        column_errors = check_required_columns(table, fieldnames)
        if column_errors:
            errors.extend(column_errors)
            continue
        checkable_tables.append(table)

    lookup_sets = collect_lookup_sets(checkable_tables)
    for table in checkable_tables:
        rows = read_rows(table.path)
        if not rows:
            continue
        errors.extend(check_pk_uniqueness(table, rows))
        errors.extend(check_fk_integrity(table, rows, lookup_sets))

    stages_table = next((t for t in checkable_tables if t.path.name == STAGES_FILENAME), None)
    documents_table = next(
        (t for t in checkable_tables if t.path.name == DOCUMENT_REQUIREMENTS_FILENAME), None
    )
    if stages_table is not None and documents_table is not None:
        errors.extend(check_document_requirements_status(stages_table.path, documents_table.path))

    routing_table = next(
        (t for t in checkable_tables if t.path.name == RISK_ROUTING_FILENAME), None
    )
    messages_table = next(
        (t for t in checkable_tables if t.path.name == RISK_KEYWORD_MESSAGES_FILENAME), None
    )
    if routing_table is not None and messages_table is not None:
        errors.extend(check_risk_message_coverage(routing_table.path, messages_table.path))

    agency_contacts_table = next(
        (t for t in checkable_tables if t.path.name == AGENCY_CONTACTS_FILENAME), None
    )
    if agency_contacts_table is not None:
        errors.extend(check_agency_contacts_map_columns(agency_contacts_table.path))

    return errors


def main() -> int:
    errors = validate(default_tables() + reference_tables())

    if errors:
        print(f"FK/PK 검증 실패: {len(errors)}건")
        for error in errors:
            print(f"  - {error}")
        return 1

    print("FK/PK 검증 통과: 문제 없음")
    return 0


if __name__ == "__main__":
    sys.exit(main())
