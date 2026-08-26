"""import_reference_data.py 회귀 테스트."""

from scripts.import_reference_data import upsert_sql, verification_query
from scripts.reference_schema import (
    AGENCY_CONTACTS,
    RISK_KEYWORD_MESSAGES,
    TABLE_ORDER,
    REFERENCE_SCHEMA,
)


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


def test_verification_query_single_pk_matches_placeholder_count():
    table = REFERENCE_SCHEMA[AGENCY_CONTACTS]
    expected = {("a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d",)}
    sql, params = verification_query(table, expected)
    assert sql.count("%s") == len(params), (
        f"Placeholder count {sql.count('%s')} != param count {len(params)}"
    )
    assert 'WHERE ("agency_id") IN' in sql
    assert params == ["a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d"]


def test_verification_query_composite_pk_matches_placeholder_count():
    table = REFERENCE_SCHEMA[RISK_KEYWORD_MESSAGES]
    expected = {
        ("VISA_CATEGORY", "IN_DOMAIN"),
        ("ADDRESS_ISSUE", "EXTERNAL"),
    }
    sql, params = verification_query(table, expected)
    assert sql.count("%s") == len(params), (
        f"Placeholder count {sql.count('%s')} != param count {len(params)}"
    )
    assert 'WHERE ("keyword_category", "resolution_type") IN' in sql
    assert len(params) == 4, (
        f"Expected 4 flattened params for 2 PK tuples × 2 columns, got {len(params)}"
    )
    # Verify params contain the right values (set comparison, order doesn't matter for set)
    expected_params = {
        "VISA_CATEGORY",
        "IN_DOMAIN",
        "ADDRESS_ISSUE",
        "EXTERNAL",
    }
    assert set(params) == expected_params


def test_verification_query_empty_expected_set():
    table = REFERENCE_SCHEMA[AGENCY_CONTACTS]
    expected = set()
    sql, params = verification_query(table, expected)
    # SQL should still be well-formed (though unused when expected is empty)
    assert 'SELECT count(*) FROM public."agency_contacts"' in sql
    assert params == []
