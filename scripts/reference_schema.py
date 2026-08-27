"""reference/ 폴더의 지도·위험 라우팅 테이블(agency_contacts, risk_routing_table,
risk_keyword_messages) 스키마 계약을 정의하는 SSOT.

scripts/schema_v2.py의 ColumnKind/ForeignKey는 재사용하지만 ColumnSpec/TableSpec은 독립
정의다 — schema_v2.TableSpec.pk는 단일 문자열만 받고, schema_v2.ColumnSpec은 FK 컬럼이
항상 UUID여야 한다는 불변식이 있어 risk_keyword_messages의 복합 PK와 target_agency_category
(→ category_minor, text FK)를 표현할 수 없다. 상세 설계 근거는 docs/map-agency-schema.md 참고.
"""

from __future__ import annotations

from dataclasses import dataclass

from scripts.schema_v2 import ColumnKind, ForeignKey

# --------------------------------------------------------------------------
# 컬럼/테이블 계약
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class ColumnSpec:
    """reference 테이블 컬럼 하나의 계약. FK 컬럼에 UUID 제약을 두지 않는다."""

    name: str
    kind: ColumnKind
    nullable: bool = False
    enum_values: frozenset[str] | None = None
    fk: ForeignKey | None = None

    def __post_init__(self) -> None:
        if self.kind == ColumnKind.ENUM and not self.enum_values:
            raise ValueError(f"ENUM 컬럼 '{self.name}'에 enum_values가 비어 있음")


@dataclass(frozen=True)
class TableSpec:
    """reference 테이블 하나의 계약. pk는 복합키 표현을 위해 항상 tuple다."""

    name: str
    columns: tuple[ColumnSpec, ...]
    pk: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.name.endswith(".csv"):
            raise ValueError(f"논리 테이블명에 .csv를 붙이면 안 됨: {self.name!r}")
        names = [c.name for c in self.columns]
        if len(names) != len(set(names)):
            duplicates = {n for n in names if names.count(n) > 1}
            raise ValueError(f"{self.name}: 컬럼명이 중복됨: {duplicates}")
        missing_pk = [p for p in self.pk if p not in names]
        if missing_pk:
            raise ValueError(f"{self.name}: PK 컬럼 {missing_pk}이 columns에 없음")

    @property
    def header(self) -> list[str]:
        return [c.name for c in self.columns]

    @property
    def filename(self) -> str:
        return f"{self.name}.csv"

    def column(self, name: str) -> ColumnSpec:
        for c in self.columns:
            if c.name == name:
                return c
        raise KeyError(f"{self.name}에 컬럼 '{name}'이 없음")


def _uuid(name: str, *, nullable: bool = False, fk: ForeignKey | None = None) -> ColumnSpec:
    return ColumnSpec(name, ColumnKind.UUID, nullable=nullable, fk=fk)


def _text(name: str, *, nullable: bool = False, fk: ForeignKey | None = None) -> ColumnSpec:
    return ColumnSpec(name, ColumnKind.TEXT, nullable=nullable, fk=fk)


def _enum(name: str, values: frozenset[str], *, nullable: bool = False) -> ColumnSpec:
    return ColumnSpec(name, ColumnKind.ENUM, nullable=nullable, enum_values=values)


def _date(name: str, *, nullable: bool = False) -> ColumnSpec:
    return ColumnSpec(name, ColumnKind.DATE, nullable=nullable)


def _numeric(name: str, *, nullable: bool = False) -> ColumnSpec:
    return ColumnSpec(name, ColumnKind.NUMERIC, nullable=nullable)


def _boolean(name: str, *, nullable: bool = False) -> ColumnSpec:
    return ColumnSpec(name, ColumnKind.BOOLEAN, nullable=nullable)


# --------------------------------------------------------------------------
# 테이블 논리명
# --------------------------------------------------------------------------

AGENCY_CONTACTS = "agency_contacts"
RISK_ROUTING_TABLE = "risk_routing_table"
RISK_KEYWORD_MESSAGES = "risk_keyword_messages"

# --------------------------------------------------------------------------
# 확정된 enum (docs/map-agency-schema.md §1.3, §2.1)
# --------------------------------------------------------------------------

AGENCY_TYPE_VALUES = frozenset(
    {
        "COMMUNITY_CENTER",
        "ADMINISTRATIVE_AGENCY",
        "UNIVERSITY_DEPT_OFFICE",
        "FOREIGN_SUPPORT_CENTER",
        "OTHER",
    }
)
RESOLUTION_TYPE_VALUES = frozenset({"IN_DOMAIN", "EXTERNAL"})

# --------------------------------------------------------------------------
# 1. agency_contacts — 기존 15개 컬럼(불변) + 지도용 신규 12개(append)
# --------------------------------------------------------------------------

_AGENCY_CONTACTS_TABLE = TableSpec(
    name=AGENCY_CONTACTS,
    pk=("agency_id",),
    columns=(
        _uuid("agency_id"),
        _text("category_major"),
        _text("category_minor"),
        _text("region"),
        _text("department_name"),
        _text("address", nullable=True),
        _text("phone"),
        _text("url", nullable=True),
        _text("target_audience"),
        _boolean("is_user_facing"),
        _date("valid_from"),
        _date("valid_to", nullable=True),
        _text("source_document"),
        _text("source_page", nullable=True),
        _date("last_verified_at"),
        # --- 신규 컬럼 (지도 기능용, docs/map-agency-schema.md §1.2) ---
        _enum("agency_type", AGENCY_TYPE_VALUES, nullable=True),
        _text("sido", nullable=True),
        _text("sigungu", nullable=True),
        _text("eupmyeondong", nullable=True),
        _text("road_address", nullable=True),
        _numeric("latitude", nullable=True),
        _numeric("longitude", nullable=True),
        _text("geocode_method", nullable=True),
        _date("geocoded_at", nullable=True),
        _text("operating_hours", nullable=True),
        _boolean("is_active"),
        _text("source_url", nullable=True),
    ),
)

# --------------------------------------------------------------------------
# 2. risk_routing_table — 기존 계약 그대로(컬럼 변경 없음)
# --------------------------------------------------------------------------

_RISK_ROUTING_TABLE_TABLE = TableSpec(
    name=RISK_ROUTING_TABLE,
    pk=("routing_id",),
    columns=(
        _uuid("routing_id"),
        _text("keyword_category"),
        _text("user_type"),
        _text("applies_to_visa_code", nullable=True),
        _enum("resolution_type", RESOLUTION_TYPE_VALUES),
        _text(
            "target_agency_category",
            nullable=True,
            fk=ForeignKey(AGENCY_CONTACTS, "category_minor"),
        ),
        _text("external_agency_name", nullable=True),
        _text("external_region_scope", nullable=True),
        _text("external_phone", nullable=True),
        _text("external_url", nullable=True),
        _text("message_addendum", nullable=True),
        _text("notes", nullable=True),
        _date("valid_from"),
        _date("valid_to", nullable=True),
        _text("source_document"),
        _text("source_page", nullable=True),
        _date("last_verified_at"),
    ),
)

# --------------------------------------------------------------------------
# 3. risk_keyword_messages — 복합 PK, 기존 계약 그대로
# --------------------------------------------------------------------------

_RISK_KEYWORD_MESSAGES_TABLE = TableSpec(
    name=RISK_KEYWORD_MESSAGES,
    pk=("keyword_category", "resolution_type"),
    columns=(
        _text("keyword_category"),
        _enum("resolution_type", RESOLUTION_TYPE_VALUES),
        _text("message_stem"),
        _text("source_document"),
        _text("source_page", nullable=True),
        _date("last_verified_at"),
    ),
)

REFERENCE_SCHEMA: dict[str, TableSpec] = {
    AGENCY_CONTACTS: _AGENCY_CONTACTS_TABLE,
    RISK_ROUTING_TABLE: _RISK_ROUTING_TABLE_TABLE,
    RISK_KEYWORD_MESSAGES: _RISK_KEYWORD_MESSAGES_TABLE,
}

TABLE_ORDER: tuple[str, ...] = tuple(REFERENCE_SCHEMA.keys())

assert len(TABLE_ORDER) == 3, f"reference 스키마는 3개 테이블이어야 함 (현재 {len(TABLE_ORDER)}개)"
