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
