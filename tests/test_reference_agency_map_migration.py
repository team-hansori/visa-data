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
