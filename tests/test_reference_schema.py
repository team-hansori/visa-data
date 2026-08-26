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
            "agency_id",
            "category_major",
            "category_minor",
            "region",
            "department_name",
            "address",
            "phone",
            "url",
            "target_audience",
            "is_user_facing",
            "valid_from",
            "valid_to",
            "source_document",
            "source_page",
            "last_verified_at",
        ]
        table = REFERENCE_SCHEMA[AGENCY_CONTACTS]
        assert table.header[:15] == legacy
        assert table.header[15:] == [
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
