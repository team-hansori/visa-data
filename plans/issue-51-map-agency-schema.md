# Issue #51: 지도 탭 기관·위험 라우팅 스키마 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** `agency_contacts`/`risk_routing_table`/`risk_keyword_messages` 3개 reference 테이블의
스키마 SSOT, Supabase migration, importer, validator를 구현해 `visa-bugi-web` 지도 탭이 쓸 수
있는 데이터 계약을 완성한다.

**Architecture:** `scripts/schema_v2.py`/`import_common_v2.py`/`validate_fk_integrity.py`
패턴을 재사용하되, 복합 PK(`risk_keyword_messages`)와 text 논리 FK(`target_agency_category`)를
표현할 수 없는 `schema_v2.py`의 제약 때문에 `reference_schema.py`는 독립된
`ColumnSpec`/`TableSpec`을 새로 정의한다. 기존 97행 `agency_contacts.csv`는 15개 컬럼·값을
그대로 두고 지도용 컬럼 12개를 CSV 끝에 append하는 1회성 마이그레이션 스크립트로 확장한다.

**Tech Stack:** Python 3.11, pytest, psycopg, PostgreSQL(Supabase), uv

**Spec:** `docs/map-agency-schema.md` (Codex 리뷰 반영 완료본 — 이 계획의 모든 태스크는 그
문서의 §번호를 그대로 인용한다)

## Global Constraints

- 기존 `agency_contacts.csv` 97행의 15개 컬럼명·값은 절대 변경하지 않는다 (`is_active`
  backfill은 신규 컬럼이라 예외).
- 신규 컬럼은 항상 기존 15개 컬럼 뒤에 append한다. CSV/쿼리 결과는 헤더(컬럼명) 기준으로만
  파싱한다.
- `risk_routing_table` → `agency_contacts` 연결에 신규 FK 컬럼·N:M 테이블을 추가하지 않는다
  (기존 `category_minor` + `region` 조인 유지, 설계 문서 §2.2).
- `is_map_visible` 같은 저장형 상태 플래그를 만들지 않는다 — 항상 파생 조건으로 계산한다
  (설계 문서 §1.4).
- `region` 매칭은 `|` 토큰화 + 완전일치만 쓴다. 부분문자열 `LIKE` 금지(설계 문서 §2.2).
- 실증 지역 15~20행의 실제 기관 데이터 수집은 이 계획의 범위 밖이다(별도 리서치 작업).
- 다국어 기관명, 전국 확장, 반경/거리 기준, 지도 SDK 선정은 범위 밖(이슈 원문).

---

## File Structure

- Create: `scripts/reference_schema.py` — 3개 테이블의 컬럼·타입·enum·PK/FK SSOT
- Create: `tests/test_reference_schema.py`
- Create: `scripts/migrate_agency_contacts_map_columns.py` — 97행 CSV에 신규 컬럼 append + `is_active` backfill (1회성, 멱등)
- Create: `tests/test_migrate_agency_contacts_map_columns.py`
- Create: `supabase/migrations/20260827000000_reference_agency_map_schema.sql`
- Create: `tests/test_reference_agency_map_migration.py`
- Create: `scripts/import_reference_data.py`
- Create: `tests/test_import_reference_data.py`
- Modify: `scripts/validate_fk_integrity.py` — `agency_type`/좌표/`is_active` 규칙 추가
- Modify: `tests/test_validate_fk_integrity.py`
- Modify: `reference/agency_contacts.csv` — Task 2에서 마이그레이션 스크립트 실행 결과로 갱신
- Modify: `reference/README.md` — 신규 컬럼 존재를 한 줄로 안내
- Modify: `.github/workflows/ci.yml` — reference 검증기·importer dry-run·migration 회귀를 CI에 연결

---

## Task 1: `reference_schema.py` — 스키마 SSOT

**Files:**
- Create: `scripts/reference_schema.py`
- Test: `tests/test_reference_schema.py`

**Interfaces:**
- Consumes: `scripts.schema_v2.ColumnKind`, `scripts.schema_v2.ForeignKey` (그대로 재사용)
- Produces: `ColumnSpec`, `TableSpec`(복합 `pk: tuple[str, ...]`), `REFERENCE_SCHEMA: dict[str, TableSpec]`, `TABLE_ORDER: tuple[str, ...]`, `AGENCY_CONTACTS`/`RISK_ROUTING_TABLE`/`RISK_KEYWORD_MESSAGES`(문자열 상수), `AGENCY_TYPE_VALUES`/`RESOLUTION_TYPE_VALUES`(frozenset) — Task 2~5가 이 이름을 그대로 import한다.

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_reference_schema.py`:

```python
"""reference_schema.py(reference/ 3개 테이블 스키마 SSOT) 회귀 테스트."""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

from scripts.reference_schema import (
    AGENCY_CONTACTS,
    AGENCY_TYPE_VALUES,
    REFERENCE_SCHEMA,
    RISK_KEYWORD_MESSAGES,
    RISK_ROUTING_TABLE,
    TABLE_ORDER,
    ColumnSpec,
    TableSpec,
)
from scripts.schema_v2 import ColumnKind, ForeignKey


class TestTableCount:
    def test_exactly_3_tables(self):
        assert len(TABLE_ORDER) == 3
        assert set(TABLE_ORDER) == {AGENCY_CONTACTS, RISK_ROUTING_TABLE, RISK_KEYWORD_MESSAGES}


class TestAgencyContactsHeaderMatchesRealCsv:
    def test_header_is_legacy_15_plus_new_12(self):
        legacy = [
            "agency_id", "category_major", "category_minor", "region", "department_name",
            "address", "phone", "url", "target_audience", "is_user_facing",
            "valid_from", "valid_to", "source_document", "source_page", "last_verified_at",
        ]
        table = REFERENCE_SCHEMA[AGENCY_CONTACTS]
        assert table.header[:15] == legacy
        assert table.header[15:] == [
            "agency_type", "sido", "sigungu", "eupmyeondong", "road_address",
            "latitude", "longitude", "geocode_method", "geocoded_at",
            "operating_hours", "is_active", "source_url",
        ]

    def test_legacy_15_columns_still_match_committed_csv(self):
        with Path("reference/agency_contacts.csv").open(newline="", encoding="utf-8-sig") as f:
            header = next(csv.reader(f))
        table = REFERENCE_SCHEMA[AGENCY_CONTACTS]
        # 마이그레이션 전 CSV의 헤더가 이 스키마의 legacy 15개와 정확히 같아야 한다.
        assert header == table.header[:15] or header == table.header


class TestCompositePk:
    def test_risk_keyword_messages_has_composite_pk(self):
        table = REFERENCE_SCHEMA[RISK_KEYWORD_MESSAGES]
        assert table.pk == ("keyword_category", "resolution_type")

    def test_single_pk_tables_use_one_element_tuple(self):
        assert REFERENCE_SCHEMA[AGENCY_CONTACTS].pk == ("agency_id",)
        assert REFERENCE_SCHEMA[RISK_ROUTING_TABLE].pk == ("routing_id",)


class TestTextForeignKeyAllowed:
    def test_target_agency_category_is_text_fk(self):
        table = REFERENCE_SCHEMA[RISK_ROUTING_TABLE]
        column = table.column("target_agency_category")
        assert column.kind == ColumnKind.TEXT
        assert column.fk == ForeignKey(AGENCY_CONTACTS, "category_minor")


class TestTableSpecValidation:
    def test_rejects_duplicate_column_names(self):
        with pytest.raises(ValueError, match="중복"):
            TableSpec(
                name="dup",
                pk=("id",),
                columns=(
                    ColumnSpec("id", ColumnKind.UUID),
                    ColumnSpec("id", ColumnKind.TEXT),
                ),
            )

    def test_rejects_pk_column_not_in_columns(self):
        with pytest.raises(ValueError, match="columns에 없음"):
            TableSpec(name="x", pk=("missing",), columns=(ColumnSpec("id", ColumnKind.UUID),))

    def test_enum_column_requires_enum_values(self):
        with pytest.raises(ValueError, match="enum_values"):
            ColumnSpec("status", ColumnKind.ENUM)


class TestAgencyTypeEnum:
    def test_agency_type_has_5_values(self):
        assert AGENCY_TYPE_VALUES == frozenset(
            {
                "COMMUNITY_CENTER",
                "ADMINISTRATIVE_AGENCY",
                "UNIVERSITY_DEPT_OFFICE",
                "FOREIGN_SUPPORT_CENTER",
                "OTHER",
            }
        )
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `uv run pytest tests/test_reference_schema.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts.reference_schema'`

- [ ] **Step 3: `scripts/reference_schema.py` 구현**

```python
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
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `uv run pytest tests/test_reference_schema.py -v`
Expected: PASS (모두)

- [ ] **Step 5: Lint**

Run: `uv run ruff check scripts/reference_schema.py tests/test_reference_schema.py && uv run ruff format --check scripts/reference_schema.py tests/test_reference_schema.py`
Expected: 통과. 실패하면 `ruff format`으로 고치고 다시 확인.

- [ ] **Step 6: 커밋**

```bash
git add scripts/reference_schema.py tests/test_reference_schema.py
git commit -m "feat: reference 3개 테이블(agency_contacts/risk_routing_table/risk_keyword_messages) 스키마 SSOT 추가"
```

---

## Task 2: `agency_contacts.csv` 신규 컬럼 마이그레이션

**Files:**
- Create: `scripts/migrate_agency_contacts_map_columns.py`
- Test: `tests/test_migrate_agency_contacts_map_columns.py`
- Modify: `reference/agency_contacts.csv` (Step 7에서 실제 실행)

**Interfaces:**
- Consumes: `scripts.reference_schema.REFERENCE_SCHEMA[AGENCY_CONTACTS].header` (Task 1)
- Produces: `migrate(path: Path = CSV_PATH) -> int` — 마이그레이션된 행 수(이미 마이그레이션됐으면 0)

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_migrate_agency_contacts_map_columns.py`:

```python
"""migrate_agency_contacts_map_columns.py 회귀 테스트."""

from __future__ import annotations

import csv
from pathlib import Path

from scripts.migrate_agency_contacts_map_columns import migrate
from scripts.reference_schema import AGENCY_CONTACTS, REFERENCE_SCHEMA

LEGACY_HEADER = [
    "agency_id", "category_major", "category_minor", "region", "department_name",
    "address", "phone", "url", "target_audience", "is_user_facing",
    "valid_from", "valid_to", "source_document", "source_page", "last_verified_at",
]


def write_legacy_csv(path: Path) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=LEGACY_HEADER)
        writer.writeheader()
        writer.writerow(
            {
                "agency_id": "11111111-1111-1111-1111-111111111111",
                "category_major": "FOREIGN_EMPLOYMENT_SUPPORT",
                "category_minor": "F-2-R",
                "region": "충청북도",
                "department_name": "외국인정책추진단",
                "address": "",
                "phone": "043-220-2693",
                "url": "",
                "target_audience": "FOREIGN_WORKER",
                "is_user_facing": "true",
                "valid_from": "2026-01-01",
                "valid_to": "2026-12-31",
                "source_document": "test.pdf",
                "source_page": "1",
                "last_verified_at": "2026-08-12",
            }
        )


def test_migrate_appends_new_columns_and_backfills_is_active(tmp_path: Path):
    path = tmp_path / "agency_contacts.csv"
    write_legacy_csv(path)

    migrated = migrate(path)

    assert migrated == 1
    with path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    table = REFERENCE_SCHEMA[AGENCY_CONTACTS]
    assert list(rows[0].keys()) == table.header
    assert rows[0]["is_active"] == "true"
    assert rows[0]["agency_type"] == ""
    assert rows[0]["latitude"] == ""
    # 기존 값은 그대로 유지된다.
    assert rows[0]["department_name"] == "외국인정책추진단"


def test_migrate_is_idempotent(tmp_path: Path):
    path = tmp_path / "agency_contacts.csv"
    write_legacy_csv(path)

    first = migrate(path)
    second = migrate(path)

    assert first == 1
    assert second == 0
    with path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 1  # 두 번 실행해도 행이 중복되지 않는다.
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `uv run pytest tests/test_migrate_agency_contacts_map_columns.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts.migrate_agency_contacts_map_columns'`

- [ ] **Step 3: 구현**

`scripts/migrate_agency_contacts_map_columns.py`:

```python
"""agency_contacts.csv에 지도 기능용 신규 컬럼 12개를 append하고 기존 행의 is_active를
'true'로 backfill하는 1회성 마이그레이션 스크립트. 기존 15개 컬럼명·값은 건드리지 않는다.
멱등 — 이미 마이그레이션된 파일에 다시 실행하면 아무 것도 하지 않는다.

사용법: uv run python scripts/migrate_agency_contacts_map_columns.py
"""

from __future__ import annotations

import csv
from pathlib import Path

from scripts.reference_schema import AGENCY_CONTACTS, REFERENCE_SCHEMA

CSV_PATH = Path("reference/agency_contacts.csv")


def migrate(path: Path = CSV_PATH) -> int:
    """신규 컬럼을 append하고 is_active=true를 backfill한다. 반환값은 갱신한 행 수 —
    이미 마이그레이션된 파일이면 0."""
    table = REFERENCE_SCHEMA[AGENCY_CONTACTS]
    with path.open(newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    if rows and list(rows[0].keys()) == table.header:
        return 0  # 이미 마이그레이션됨

    new_columns = [c for c in table.header if c not in rows[0].keys()] if rows else []
    for row in rows:
        for column in new_columns:
            row[column] = "true" if column == "is_active" else ""

    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=table.header)
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)


def main() -> int:
    count = migrate()
    print(f"{count}행 마이그레이션 완료" if count else "이미 마이그레이션됨 — 변경 없음")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `uv run pytest tests/test_migrate_agency_contacts_map_columns.py -v`
Expected: PASS

- [ ] **Step 5: Lint**

Run: `uv run ruff check scripts/migrate_agency_contacts_map_columns.py tests/test_migrate_agency_contacts_map_columns.py && uv run ruff format --check scripts/migrate_agency_contacts_map_columns.py tests/test_migrate_agency_contacts_map_columns.py`

- [ ] **Step 6: 커밋 (스크립트만)**

```bash
git add scripts/migrate_agency_contacts_map_columns.py tests/test_migrate_agency_contacts_map_columns.py
git commit -m "feat: agency_contacts.csv 지도용 컬럼 마이그레이션 스크립트 추가"
```

- [ ] **Step 7: 실제 `reference/agency_contacts.csv`에 실행**

```bash
uv run python scripts/migrate_agency_contacts_map_columns.py
git diff --stat reference/agency_contacts.csv
```

Expected: `97행 마이그레이션 완료` 출력. `git diff`로 헤더 한 줄과 97개 데이터 행 전체가 바뀐
것으로 보이는 게 정상이다(컬럼이 늘어나 모든 행이 재작성됨) — 단, 각 행을 열어보면 기존
15개 값은 그대로이고 뒤에 빈 칸(대부분)과 `is_active=true`만 추가된 것을 확인한다.

```bash
uv run python scripts/validate_fk_integrity.py
```

Expected: `FK/PK 검증 통과: 문제 없음` (Task 5에서 신규 규칙을 추가하기 전이므로 기존
검사만 통과하면 된다 — 새 컬럼이 늘어났다고 기존 `required_columns`/FK 검사가 깨지지
않는지 지금 먼저 확인한다).

- [ ] **Step 8: 데이터 변경 커밋**

```bash
git add reference/agency_contacts.csv
git commit -m "data: agency_contacts.csv에 지도용 컬럼 12개 추가(기존 97행 값 불변, is_active=true 백필)"
```

---

## Task 3: Supabase migration SQL

**Files:**
- Create: `supabase/migrations/20260827000000_reference_agency_map_schema.sql`
- Test: `tests/test_reference_agency_map_migration.py`

**Interfaces:**
- Consumes: 없음 (정적 SQL 파일)
- Produces: `public.agency_contacts`/`public.risk_routing_table`/`public.risk_keyword_messages`
  테이블, `public.map_visible_agency_contacts` VIEW — Task 4 importer가 이 테이블명을 그대로
  사용한다.

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_reference_agency_map_migration.py`:

```python
"""reference_agency_map_schema.sql migration 회귀 테스트."""

from pathlib import Path


def _read_migration() -> str:
    return next(Path("supabase/migrations").glob("*_reference_agency_map_schema.sql")).read_text()


def test_migration_creates_all_3_tables_with_rls():
    migration = _read_migration()
    for table in ("agency_contacts", "risk_routing_table", "risk_keyword_messages"):
        assert f'CREATE TABLE public."{table}"' in migration
        assert f'ALTER TABLE public."{table}" ENABLE ROW LEVEL SECURITY' in migration
        assert f'CREATE POLICY "public read" ON public."{table}"' in migration


def test_risk_keyword_messages_has_composite_primary_key():
    migration = _read_migration()
    assert 'PRIMARY KEY ("keyword_category", "resolution_type")' in migration


def test_agency_type_check_enumerates_5_values():
    migration = _read_migration()
    for value in (
        "COMMUNITY_CENTER",
        "ADMINISTRATIVE_AGENCY",
        "UNIVERSITY_DEPT_OFFICE",
        "FOREIGN_SUPPORT_CENTER",
        "OTHER",
    ):
        assert value in migration


def test_coordinate_range_checks_present():
    migration = _read_migration()
    assert "BETWEEN -90 AND 90" in migration
    assert "BETWEEN -180 AND 180" in migration


def test_map_visible_view_uses_security_invoker():
    migration = _read_migration()
    assert 'CREATE VIEW public."map_visible_agency_contacts"' in migration
    assert "security_invoker = true" in migration


def test_grants_select_to_anon_and_authenticated():
    migration = _read_migration()
    assert "GRANT SELECT" in migration
    assert "anon, authenticated" in migration
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `uv run pytest tests/test_reference_agency_map_migration.py -v`
Expected: FAIL — `StopIteration`(파일이 없어 `glob()`이 빈 이터레이터를 반환)

- [ ] **Step 3: migration SQL 작성**

`supabase/migrations/20260827000000_reference_agency_map_schema.sql`:

```sql
-- Reference agency contacts + risk routing schema (지도 탭 기관 연락처·위험 라우팅).
-- 설계 근거와 파생 규칙은 docs/map-agency-schema.md 참고. common_schema_v2와 책임을
-- 섞지 않는 별도 migration이다.

CREATE TABLE public."agency_contacts" (
  "agency_id" uuid PRIMARY KEY NOT NULL,
  "category_major" text NOT NULL,
  "category_minor" text NOT NULL,
  "region" text NOT NULL,
  "department_name" text NOT NULL,
  "address" text,
  "phone" text NOT NULL,
  "url" text,
  "target_audience" text NOT NULL,
  "is_user_facing" boolean NOT NULL,
  "valid_from" date NOT NULL,
  "valid_to" date,
  "source_document" text NOT NULL,
  "source_page" text,
  "last_verified_at" date NOT NULL,
  "agency_type" text CHECK (
    "agency_type" IS NULL OR "agency_type" IN (
      'COMMUNITY_CENTER', 'ADMINISTRATIVE_AGENCY', 'UNIVERSITY_DEPT_OFFICE',
      'FOREIGN_SUPPORT_CENTER', 'OTHER'
    )
  ),
  "sido" text,
  "sigungu" text,
  "eupmyeondong" text,
  "road_address" text,
  "latitude" numeric(9,6) CHECK ("latitude" BETWEEN -90 AND 90),
  "longitude" numeric(9,6) CHECK ("longitude" BETWEEN -180 AND 180),
  "geocode_method" text,
  "geocoded_at" date,
  "operating_hours" text,
  "is_active" boolean NOT NULL DEFAULT true,
  "source_url" text,
  CONSTRAINT "agency_contacts_coords_paired" CHECK (("latitude" IS NULL) = ("longitude" IS NULL)),
  CONSTRAINT "agency_contacts_map_pin_requires_type" CHECK ("latitude" IS NULL OR "agency_type" IS NOT NULL)
);

CREATE TABLE public."risk_routing_table" (
  "routing_id" uuid PRIMARY KEY NOT NULL,
  "keyword_category" text NOT NULL,
  "user_type" text NOT NULL,
  "applies_to_visa_code" text,
  "resolution_type" text NOT NULL CHECK ("resolution_type" IN ('EXTERNAL', 'IN_DOMAIN')),
  "target_agency_category" text,
  "external_agency_name" text,
  "external_region_scope" text,
  "external_phone" text,
  "external_url" text,
  "message_addendum" text,
  "notes" text,
  "valid_from" date NOT NULL,
  "valid_to" date,
  "source_document" text NOT NULL,
  "source_page" text,
  "last_verified_at" date NOT NULL
);

CREATE TABLE public."risk_keyword_messages" (
  "keyword_category" text NOT NULL,
  "resolution_type" text NOT NULL CHECK ("resolution_type" IN ('EXTERNAL', 'IN_DOMAIN')),
  "message_stem" text NOT NULL,
  "source_document" text NOT NULL,
  "source_page" text,
  "last_verified_at" date NOT NULL,
  PRIMARY KEY ("keyword_category", "resolution_type")
);

-- security_invoker=true: 뷰 소유자가 아니라 조회하는 role 기준으로 agency_contacts의
-- RLS를 평가한다 — 기본값(off)이면 뷰가 RLS를 우회할 수 있다.
CREATE VIEW public."map_visible_agency_contacts"
  WITH (security_invoker = true) AS
  SELECT * FROM public."agency_contacts"
  WHERE "agency_type" IS NOT NULL
    AND "latitude" IS NOT NULL
    AND "longitude" IS NOT NULL
    AND "is_active" = true
    AND "is_user_facing" = true;

CREATE INDEX "agency_contacts_map_lookup_idx" ON public."agency_contacts" ("category_minor", "region")
  WHERE "agency_type" IS NOT NULL AND "latitude" IS NOT NULL AND "longitude" IS NOT NULL
    AND "is_active" AND "is_user_facing";
CREATE INDEX "agency_contacts_region_idx" ON public."agency_contacts" ("sido", "sigungu");
CREATE INDEX "risk_routing_category_idx" ON public."risk_routing_table" ("keyword_category", "user_type");

ALTER TABLE public."agency_contacts" ENABLE ROW LEVEL SECURITY;
ALTER TABLE public."risk_routing_table" ENABLE ROW LEVEL SECURITY;
ALTER TABLE public."risk_keyword_messages" ENABLE ROW LEVEL SECURITY;

CREATE POLICY "public read" ON public."agency_contacts" FOR SELECT TO anon, authenticated USING (true);
CREATE POLICY "public read" ON public."risk_routing_table" FOR SELECT TO anon, authenticated USING (true);
CREATE POLICY "public read" ON public."risk_keyword_messages" FOR SELECT TO anon, authenticated USING (true);

GRANT SELECT ON public."agency_contacts", public."risk_routing_table", public."risk_keyword_messages"
  TO anon, authenticated;
GRANT SELECT ON public."map_visible_agency_contacts" TO anon, authenticated;
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `uv run pytest tests/test_reference_agency_map_migration.py -v`
Expected: PASS (모두)

- [ ] **Step 5: 로컬 Postgres에 실제 적용해 문법 검증** (CI와 동일한 방식 — `migration-import-regression` 잡이 이미 `postgres:15` 서비스 컨테이너를 씀, 로컬에 docker 없으면 이 스텝은 건너뛰고 Task 6의 CI에서 검증)

```bash
docker run --rm -d --name pg-map-test -e POSTGRES_PASSWORD=postgres -p 5433:5432 postgres:15
sleep 3
psql "postgresql://postgres:postgres@localhost:5433/postgres" -v ON_ERROR_STOP=1 \
  -c 'CREATE ROLE anon; CREATE ROLE authenticated;'
psql "postgresql://postgres:postgres@localhost:5433/postgres" -v ON_ERROR_STOP=1 \
  -f supabase/migrations/20260827000000_reference_agency_map_schema.sql
docker stop pg-map-test
```

Expected: 에러 없이 완료. CHECK 제약 문법 오류, VIEW `security_invoker` 미지원(PostgreSQL
15는 지원 — Supabase도 PG 15 기준이라 문제없음) 등을 여기서 잡는다.

- [ ] **Step 6: 커밋**

```bash
git add supabase/migrations/20260827000000_reference_agency_map_schema.sql tests/test_reference_agency_map_migration.py
git commit -m "feat: agency_contacts/risk_routing_table/risk_keyword_messages Supabase migration 추가"
```

---

## Task 4: `import_reference_data.py`

**Files:**
- Create: `scripts/import_reference_data.py`
- Test: `tests/test_import_reference_data.py`

**Interfaces:**
- Consumes: `scripts.reference_schema.REFERENCE_SCHEMA`/`TABLE_ORDER`(Task 1),
  `scripts.import_common_v2.safe_target`(재사용), `scripts.validate_fk_integrity.main`(preflight)
- Produces: `upsert_sql(table) -> str`, `convert_value`, `prepared_rows`, `import_data`,
  `verify_database`, CLI `main()`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_import_reference_data.py`:

```python
"""import_reference_data.py 회귀 테스트."""

from scripts.import_reference_data import upsert_sql
from scripts.reference_schema import RISK_KEYWORD_MESSAGES, TABLE_ORDER, REFERENCE_SCHEMA


def test_every_table_has_upsert_sql_matching_placeholder_count():
    for name in TABLE_ORDER:
        table = REFERENCE_SCHEMA[name]
        sql = upsert_sql(table)
        assert f'INSERT INTO public."{name}"' in sql
        assert sql.count("%s") == len(table.columns)


def test_single_pk_tables_conflict_on_one_column():
    table = REFERENCE_SCHEMA["agency_contacts"]
    sql = upsert_sql(table)
    assert 'ON CONFLICT ("agency_id") DO UPDATE' in sql


def test_composite_pk_table_conflicts_on_both_columns_and_excludes_them_from_update():
    table = REFERENCE_SCHEMA[RISK_KEYWORD_MESSAGES]
    sql = upsert_sql(table)
    assert 'ON CONFLICT ("keyword_category", "resolution_type") DO UPDATE' in sql
    assert '"keyword_category" = EXCLUDED."keyword_category"' not in sql
    assert '"resolution_type" = EXCLUDED."resolution_type"' not in sql
    assert '"message_stem" = EXCLUDED."message_stem"' in sql
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `uv run pytest tests/test_import_reference_data.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts.import_reference_data'`

- [ ] **Step 3: 구현**

`scripts/import_reference_data.py`:

```python
"""Validate and transactionally upsert reference/ (agency_contacts, risk_routing_table,
risk_keyword_messages) CSVs into PostgreSQL. extraction/common_v2/ 13개 표를 다루는
import_common_v2.py와 책임을 분리한다. 설계 근거는 docs/map-agency-schema.md 참고.

CSV에서 사라진 행을 자동 삭제하지 않는다 — 기관 폐쇄는 agency_contacts.is_active=false로
표현하는 설계와 일치시키기 위함이다. 그래서 사후 검증도 "DB 행 수 == CSV 행 수"가 아니라
"CSV의 모든 PK가 DB에 존재하는가"만 확인한다.
"""

from __future__ import annotations

import argparse
import csv
import os
import subprocess
import sys
from collections.abc import Iterable
from pathlib import Path

from scripts.import_common_v2 import safe_target
from scripts.reference_schema import REFERENCE_SCHEMA, TABLE_ORDER, ColumnKind, TableSpec

DEFAULT_DATA_DIR = Path("reference")


def read_rows(data_dir: Path, table: TableSpec) -> list[dict[str, str]]:
    with (data_dir / table.filename).open(newline="", encoding="utf-8-sig") as stream:
        return list(csv.DictReader(stream))


def convert_value(value: str, kind: ColumnKind):
    if value == "":
        return None
    if kind == ColumnKind.BOOLEAN:
        return value.lower() == "true"
    return value


def prepared_rows(rows: Iterable[dict[str, str]], table: TableSpec) -> list[tuple[object, ...]]:
    return [
        tuple(convert_value(row[column.name], column.kind) for column in table.columns)
        for row in rows
    ]


def upsert_sql(table: TableSpec) -> str:
    columns = table.header
    quoted = ", ".join(f'"{column}"' for column in columns)
    placeholders = ", ".join(["%s"] * len(columns))
    pk_quoted = ", ".join(f'"{column}"' for column in table.pk)
    updates = ", ".join(
        f'"{column}" = EXCLUDED."{column}"' for column in columns if column not in table.pk
    )
    return (
        f'INSERT INTO public."{table.name}" ({quoted}) VALUES ({placeholders}) '
        f"ON CONFLICT ({pk_quoted}) DO UPDATE SET {updates}"
    )


def run_preflight() -> None:
    root = Path(__file__).resolve().parents[1]
    subprocess.run(
        [sys.executable, str(root / "scripts/validate_fk_integrity.py")], cwd=root, check=True
    )


def import_data(database_url: str, data_dir: Path) -> dict[str, int]:
    try:
        import psycopg
    except ImportError as exc:  # pragma: no cover - environment-specific guidance
        raise RuntimeError("psycopg is required: uv sync") from exc

    counts: dict[str, int] = {}
    with psycopg.connect(database_url) as connection:
        with connection.transaction():
            with connection.cursor() as cursor:
                for name in TABLE_ORDER:
                    table = REFERENCE_SCHEMA[name]
                    rows = read_rows(data_dir, table)
                    if rows:
                        cursor.executemany(upsert_sql(table), prepared_rows(rows, table))
                    counts[name] = len(rows)
            verify_database(connection, data_dir)
    return counts


def verify_database(connection, data_dir: Path) -> None:
    """CSV의 모든 PK가 DB에 존재하는지만 확인한다(삭제 정책이 없어 행 수 동일성은
    가정하지 않는다)."""
    for name in TABLE_ORDER:
        table = REFERENCE_SCHEMA[name]
        rows = read_rows(data_dir, table)
        if not rows:
            continue
        pk_columns_sql = ", ".join(f'"{c}"' for c in table.pk)
        expected = {tuple(row[c] for c in table.pk) for row in rows}
        row_placeholders = "(" + ", ".join(["%s"] * len(table.pk)) + ")"
        placeholders = ", ".join([row_placeholders] * len(expected))
        flat_params = [value for pk_tuple in expected for value in pk_tuple]
        found = connection.execute(
            f'SELECT count(*) FROM public."{name}" WHERE ({pk_columns_sql}) IN ({placeholders})',
            flat_params,
        ).fetchone()[0]
        if found != len(expected):
            raise RuntimeError(f"{name}: CSV {len(expected)}건 중 {found}건만 DB에서 확인됨")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--database-url", default=os.getenv("DATABASE_URL"))
    parser.add_argument("--apply", action="store_true", help="Commit the validated upsert")
    args = parser.parse_args()

    run_preflight()
    counts = {name: len(read_rows(args.data_dir, REFERENCE_SCHEMA[name])) for name in TABLE_ORDER}
    print("Validated rows: " + ", ".join(f"{name}={count}" for name, count in counts.items()))
    if not args.apply:
        print("Dry run only; pass --apply with DATABASE_URL to write data.")
        return 0
    if not args.database_url:
        parser.error("--apply requires DATABASE_URL or --database-url")
    print(f"Applying to {safe_target(args.database_url)} (credentials hidden)")
    import_data(args.database_url, args.data_dir)
    print("Import and post-import validation completed in one transaction.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `uv run pytest tests/test_import_reference_data.py -v`
Expected: PASS (모두)

- [ ] **Step 5: dry-run으로 실제 CSV 검증**

```bash
uv run python scripts/import_reference_data.py
```

Expected: `Validated rows: agency_contacts=97, risk_routing_table=6, risk_keyword_messages=5`
(Task 5까지 끝나야 `run_preflight`가 신규 규칙까지 통과 — Task 5 이후 다시 확인)

- [ ] **Step 6: Lint + 커밋**

```bash
uv run ruff check scripts/import_reference_data.py tests/test_import_reference_data.py
uv run ruff format --check scripts/import_reference_data.py tests/test_import_reference_data.py
git add scripts/import_reference_data.py tests/test_import_reference_data.py
git commit -m "feat: reference 3개 테이블 Supabase importer 추가"
```

---

## Task 5: `validate_fk_integrity.py` 확장 — 지도 컬럼 규칙

**Files:**
- Modify: `scripts/validate_fk_integrity.py`
- Modify: `tests/test_validate_fk_integrity.py`

**Interfaces:**
- Consumes: `scripts.reference_schema.AGENCY_TYPE_VALUES`(Task 1)
- Produces: `check_agency_contacts_map_columns(path: Path) -> list[str]` — `validate()`에서 호출

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_validate_fk_integrity.py`에 아래 클래스를 추가한다 (파일 끝에 append):

```python
class TestCheckAgencyContactsMapColumns:
    HEADER = [
        "agency_id", "category_major", "category_minor", "region", "department_name",
        "address", "phone", "url", "target_audience", "is_user_facing",
        "valid_from", "valid_to", "source_document", "source_page", "last_verified_at",
        "agency_type", "sido", "sigungu", "eupmyeondong", "road_address",
        "latitude", "longitude", "geocode_method", "geocoded_at",
        "operating_hours", "is_active", "source_url",
    ]

    def base_row(self, **overrides):
        row = {column: "" for column in self.HEADER}
        row.update(
            agency_id="a1", category_major="X", category_minor="Y", region="청주",
            department_name="테스트기관", phone="043-000-0000", target_audience="STUDENT",
            is_user_facing="true", valid_from="2026-01-01", source_document="doc.pdf",
            last_verified_at="2026-08-01", is_active="true",
        )
        row.update(overrides)
        return row

    def test_valid_row_without_map_pin_passes(self, tmp_path: Path):
        path = tmp_path / "agency_contacts.csv"
        write_csv(path, self.HEADER, [self.base_row()])
        assert check_agency_contacts_map_columns(path) == []

    def test_valid_map_pin_row_passes(self, tmp_path: Path):
        path = tmp_path / "agency_contacts.csv"
        row = self.base_row(
            agency_type="COMMUNITY_CENTER", sido="충청북도", sigungu="청주시",
            road_address="충청북도 청주시 상당구 1", latitude="36.6", longitude="127.5",
            geocode_method="Kakao Map API", geocoded_at="2026-08-20",
        )
        write_csv(path, self.HEADER, [row])
        assert check_agency_contacts_map_columns(path) == []

    def test_flags_invalid_agency_type(self, tmp_path: Path):
        path = tmp_path / "agency_contacts.csv"
        write_csv(path, self.HEADER, [self.base_row(agency_type="NOT_A_REAL_TYPE")])
        errors = check_agency_contacts_map_columns(path)
        assert any("agency_type" in e for e in errors)

    def test_flags_invalid_is_active(self, tmp_path: Path):
        path = tmp_path / "agency_contacts.csv"
        write_csv(path, self.HEADER, [self.base_row(is_active="")])
        errors = check_agency_contacts_map_columns(path)
        assert any("is_active" in e for e in errors)

    def test_flags_latitude_without_longitude(self, tmp_path: Path):
        path = tmp_path / "agency_contacts.csv"
        write_csv(path, self.HEADER, [self.base_row(latitude="36.6")])
        errors = check_agency_contacts_map_columns(path)
        assert any("latitude/longitude" in e for e in errors)

    def test_flags_latitude_without_required_metadata(self, tmp_path: Path):
        path = tmp_path / "agency_contacts.csv"
        row = self.base_row(latitude="36.6", longitude="127.5")  # road_address 등 누락
        write_csv(path, self.HEADER, [row])
        errors = check_agency_contacts_map_columns(path)
        assert any("road_address" in e for e in errors)
```

파일 상단 import 목록에 `check_agency_contacts_map_columns`를 추가한다:

```python
from scripts.validate_fk_integrity import (
    TableSpec,
    check_agency_contacts_map_columns,  # 추가
    check_document_requirements_status,
    check_fk_integrity,
    check_pk_uniqueness,
    check_required_columns,
    check_risk_message_coverage,
    collect_lookup_sets,
    read_fieldnames,
    read_rows,
    reference_tables,
    validate,
)
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `uv run pytest tests/test_validate_fk_integrity.py -v`
Expected: FAIL — `ImportError: cannot import name 'check_agency_contacts_map_columns'`

- [ ] **Step 3: `scripts/validate_fk_integrity.py` 구현**

파일 상단 import에 추가:

```python
from scripts.reference_schema import AGENCY_TYPE_VALUES
```

`reference_tables()` 함수에서 `agency_contacts` `TableSpec`에 `required_columns`를 추가한다
(기존 함수 교체):

```python
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
                "agency_type", "sido", "sigungu", "eupmyeondong", "road_address",
                "latitude", "longitude", "geocode_method", "geocoded_at",
                "operating_hours", "is_active", "source_url",
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
            nullable_fks={"target_agency_category": ("resolution_type", "EXTERNAL")},
        ),
    ]
```

새 검사 함수를 `check_risk_message_coverage` 함수 뒤에 추가한다:

```python
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
```

`validate()` 함수의 마지막(risk_message_coverage 검사 이후)에 추가:

```python
    agency_contacts_table = next(
        (t for t in checkable_tables if t.path.name == AGENCY_CONTACTS_FILENAME), None
    )
    if agency_contacts_table is not None:
        errors.extend(check_agency_contacts_map_columns(agency_contacts_table.path))

    return errors
```

(기존 `return errors`를 이 블록 뒤로 옮긴다.)

- [ ] **Step 4: 테스트 통과 확인**

Run: `uv run pytest tests/test_validate_fk_integrity.py -v`
Expected: PASS (모두, 기존 테스트 포함 회귀 없음)

- [ ] **Step 5: 실제 데이터에 대해 최종 검증**

```bash
uv run python scripts/validate_fk_integrity.py
uv run python scripts/import_reference_data.py
```

Expected: 둘 다 통과. (Task 2에서 backfill한 `is_active=true`가 여기서 검증된다 — 만약
`is_active` 관련 에러가 나오면 Task 2 Step 7이 제대로 실행됐는지 다시 확인한다.)

- [ ] **Step 6: Lint + 커밋**

```bash
uv run ruff check scripts/validate_fk_integrity.py tests/test_validate_fk_integrity.py
uv run ruff format --check scripts/validate_fk_integrity.py tests/test_validate_fk_integrity.py
git add scripts/validate_fk_integrity.py tests/test_validate_fk_integrity.py
git commit -m "feat: agency_contacts 지도용 컬럼(agency_type/좌표/is_active) 검증 규칙 추가"
```

---

## Task 6: CI 연결 + 문서 갱신 + 통합 검증

**Files:**
- Modify: `.github/workflows/ci.yml`
- Modify: `reference/README.md`

**Interfaces:** 없음(설정·문서 변경)

- [ ] **Step 1: `ci.yml`의 `lint-and-test` 잡에 reference 검증 단계 추가**

`E-7-4R 매핑 무결성 검증` 스텝 뒤에 추가:

```yaml
      - name: reference/ FK·지도 컬럼 무결성 검증
        run: python scripts/validate_fk_integrity.py

      - name: reference importer dry-run
        run: python scripts/import_reference_data.py
```

`ruff check`/`ruff format --check` 대상 목록에도 추가:

```yaml
          ruff check \
            scripts/reference_schema.py \
            scripts/migrate_agency_contacts_map_columns.py \
            scripts/import_reference_data.py \
            scripts/validate_fk_integrity.py
          ruff format --check \
            scripts/reference_schema.py \
            scripts/migrate_agency_contacts_map_columns.py \
            scripts/import_reference_data.py \
            scripts/validate_fk_integrity.py
```

- [ ] **Step 2: `migration-import-regression` 잡에 신규 migration 적용 + 2회 import 추가**

`Apply migration` 스텝 뒤에 추가:

```yaml
      - name: Apply reference migration
        run: psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f supabase/migrations/20260827000000_reference_agency_map_schema.sql
```

`Import twice and verify idempotency` 스텝 뒤에 추가:

```yaml
      - name: Import reference data twice and verify idempotency
        run: |
          python scripts/import_reference_data.py --apply
          python scripts/import_reference_data.py --apply
```

- [ ] **Step 3: `reference/README.md`에 한 줄 추가**

`agency_contacts.csv` 설명 행을 아래로 교체:

```markdown
| `agency_contacts.csv` | 충북 시군별 가족센터·다문화가족지원센터·외국인지원센터 연락처. `url` 컬럼 추가됨(전화 다음 위치) — 기존 행은 아직 URL 미검증이라 빈 값, 추가 조사 필요. 지도 탭용 컬럼 12개(`agency_type`/좌표/`is_active` 등, 이슈 #51)가 끝에 추가됨 — 스키마는 `docs/map-agency-schema.md` 참고 |
```

- [ ] **Step 4: 전체 테스트 + 로컬 통합 검증**

```bash
uv run pytest tests/ -v --tb=short
uv run ruff check scripts/ tests/
uv run ruff format --check scripts/ tests/
uv run python scripts/validate_fk_integrity.py
uv run python scripts/import_reference_data.py
```

Expected: 전부 통과. (Supabase 로컬/원격 적용은 issue #51 완료 기준의 "로컬 Supabase 또는
승인된 대상에서 dry-run 및 적재 검증" 항목 — `docs/supabase-runbook.md` 절차를 따라 별도로
승인받아 진행한다. 이 계획은 CI의 `migration-import-regression` 잡으로 회귀 검증을
자동화하는 데까지만 다룬다.)

- [ ] **Step 5: 커밋**

```bash
git add .github/workflows/ci.yml reference/README.md
git commit -m "ci: reference 스키마 검증·importer dry-run·migration 회귀를 CI에 연결"
```

---

## 완료 후 남는 일 (이 계획 범위 밖)

- 실증 4개 지역(음성/진천/청주/충주) 지도 노출용 기관 15~20행 실제 수집·검증 — 공식 출처
  확인이 필요한 리서치 작업, 별도 진행.
- 원격 Supabase 프로젝트 link 및 실제 배포 — `docs/supabase-runbook.md` 절차, 별도 승인 단계.
- `docs/map-agency-schema.md`를 `visa-bugi-web` 저장소에 공유(§5 계약 전달).
- 기존 `region` 값의 자유서술 이상치(`청주(관할:전지역)`) 정규화 — 별도 이슈.
