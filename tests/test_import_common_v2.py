from pathlib import Path

from scripts.import_common_v2 import safe_target, upsert_sql
from scripts.schema_v2 import SCHEMA_V2, TABLE_ORDER


def test_every_table_has_idempotent_upsert() -> None:
    for name in TABLE_ORDER:
        table = SCHEMA_V2[name]
        sql = upsert_sql(table)
        assert f'INSERT INTO public."{name}"' in sql
        assert f'ON CONFLICT ("{table.pk}") DO UPDATE' in sql
        assert sql.count("%s") == len(table.columns)


def test_database_target_never_contains_credentials() -> None:
    url = "postgresql://secret-user:secret-password@db.example.test:6543/postgres"
    target = safe_target(url)
    assert target == "db.example.test:6543/postgres"
    assert "secret" not in target


def test_migration_defines_all_tables_and_rls() -> None:
    migration = next(Path("supabase/migrations").glob("*_common_schema_v2.sql")).read_text()
    for name in TABLE_ORDER:
        assert f'CREATE TABLE public."{name}"' in migration
        assert f"ALTER TABLE public.{name} ENABLE ROW LEVEL SECURITY" in migration
    assert "DEFERRABLE INITIALLY DEFERRED" in migration
    assert "REVOKE ALL ON public.change_history, public.source_record_mappings" in migration
