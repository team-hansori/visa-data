from pathlib import Path

from scripts.validate_source_record_mappings import validate_mappings


ROOT = Path(__file__).resolve().parents[1]


def test_real_mapping_ledger_has_valid_source_and_target_links():
    errors = validate_mappings(ROOT, ROOT / "extraction/common_v2")
    assert errors == []
