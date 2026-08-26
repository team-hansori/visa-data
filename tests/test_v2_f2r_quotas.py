"""F-2-R 시군별 차수 쿼터 이관의 원천 행 단위 회귀 테스트."""

from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path

SOURCE_DIR = Path("extraction/A_F-2-R")
COMMON_V2_DIR = Path("extraction/common_v2")

F2R_VISA_ID = "a228433b-abe4-4785-8496-3e1cb3d597c1"
F2R_LIMITED_POLICY_ID = "e5966735-9d7c-4fe2-a7ef-0ca6c85e88fb"
VALID_FROM = "2025-03-07"
VALID_TO = "2026-09-18"


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as file:
        return list(csv.DictReader(file))


def _common_rows(filename: str) -> list[dict[str, str]]:
    return _read_rows(COMMON_V2_DIR / filename)


def _f2r_mappings() -> list[dict[str, str]]:
    return [
        row
        for row in _common_rows("source_record_mappings.csv")
        if row["source_dataset"] == "A_F-2-R" and row["source_table"] == "visa_regional_quotas"
    ]


def _f2r_snapshots() -> list[dict[str, str]]:
    return [
        row
        for row in _common_rows("visa_quota_snapshots.csv")
        if row["quota_policy_id"] == F2R_LIMITED_POLICY_ID
    ]


def test_every_source_quota_row_is_mapped_exactly_once() -> None:
    source_rows = _read_rows(SOURCE_DIR / "visa_regional_quotas.csv")
    mappings = _f2r_mappings()

    assert len(source_rows) == len(mappings) == 60
    assert Counter(row["source_record_id"] for row in mappings) == Counter(
        row["quota_id"] for row in source_rows
    )
    assert len({row["target_record_id"] for row in mappings}) == 60
    assert {row["mapping_status"] for row in mappings} == {"MAPPED"}
    assert {row["mapping_action"] for row in mappings} == {"TRANSFORM"}
    assert {row["target_table"] for row in mappings} == {"visa_quota_snapshots"}
    assert all(row["blocking_reason"] == "" for row in mappings)


def test_existing_limited_policy_uuid_is_reused() -> None:
    policies = [
        row
        for row in _common_rows("visa_quota_policies.csv")
        if row["visa_id"] == F2R_VISA_ID
        and row["quota_type"] == "LIMITED"
        and row["quota_unit"] == "PERSON"
    ]

    assert len(policies) == 1
    assert policies[0]["quota_policy_id"] == F2R_LIMITED_POLICY_ID
    assert policies[0]["valid_from"] == VALID_FROM
    assert policies[0]["valid_to"] == VALID_TO


def test_source_values_round_scope_dates_and_provenance_match_snapshots() -> None:
    source_rows = _read_rows(SOURCE_DIR / "visa_regional_quotas.csv")
    rounds = {
        row["announcement_id"]: row
        for row in _read_rows(SOURCE_DIR / "visa_announcement_rounds.csv")
    }
    mappings = {row["source_record_id"]: row for row in _f2r_mappings()}
    snapshots = {row["quota_snapshot_id"]: row for row in _common_rows("visa_quota_snapshots.csv")}
    documents = {row["source_document_id"]: row for row in _common_rows("source_documents.csv")}

    for source in source_rows:
        source_round = rounds[source["announcement_id"]]
        mapping = mappings[source["quota_id"]]
        snapshot = snapshots[mapping["target_record_id"]]
        document = documents[snapshot["source_document_id"]]

        assert snapshot["notice_round"] == source_round["announcement_round"]
        assert snapshot["as_of_date"] == source_round["announcement_date"]
        assert snapshot["scope_type"] == "MUNICIPALITY"
        assert snapshot["scope_name"] == source["region"]
        assert snapshot["parent_scope_name"] == "충청북도"
        assert snapshot["allocated_quota"] == source["allocated_quota"]
        assert snapshot["recommended_count"] == source["previously_recommended"]
        assert snapshot["consumed_quota"] == source["previously_recommended"]
        assert snapshot["remaining_quota"] == source["remaining_quota"]
        assert snapshot["valid_from"] == mapping["valid_from"] == VALID_FROM
        assert snapshot["valid_to"] == mapping["valid_to"] == VALID_TO
        assert snapshot["source_document_id"] == mapping["source_document_id"]
        assert snapshot["source_page"] == mapping["source_page"] == "2"
        assert document["source_document_key"] == source["source_document_id"]
        assert document["notice_round"] == snapshot["notice_round"]
        assert document["published_at"] == snapshot["as_of_date"]
        assert document["last_verified_at"] == "2026-08-15"


def test_snapshot_identity_is_unique_by_policy_scope_and_as_of_date() -> None:
    snapshots = _common_rows("visa_quota_snapshots.csv")
    identities = [
        (
            row["quota_policy_id"],
            row["scope_type"],
            row["scope_name"],
            row["as_of_date"],
        )
        for row in snapshots
    ]

    assert len(identities) == len(set(identities))
    assert len(_f2r_snapshots()) == 60
    assert {row["notice_round"] for row in _f2r_snapshots()} == {
        str(round_number) for round_number in range(8, 18)
    }


def test_quota_values_are_non_negative_and_arithmetic_is_consistent() -> None:
    snapshots = _common_rows("visa_quota_snapshots.csv")
    numeric_columns = (
        "allocated_quota",
        "recommended_count",
        "quota_exempt_count",
        "consumed_quota",
        "remaining_quota",
    )

    for row in snapshots:
        for column in numeric_columns:
            if row[column] != "":
                assert int(row[column]) >= 0

        if all(
            row[column] != "" for column in ("allocated_quota", "consumed_quota", "remaining_quota")
        ):
            assert int(row["remaining_quota"]) == int(row["allocated_quota"]) - int(
                row["consumed_quota"]
            )

        if all(
            row[column] != ""
            for column in ("recommended_count", "quota_exempt_count", "consumed_quota")
        ):
            assert int(row["consumed_quota"]) == int(row["recommended_count"]) - int(
                row["quota_exempt_count"]
            )

    for row in _f2r_snapshots():
        assert row["quota_exempt_count"] == ""
        assert row["consumption_exception"] == ""
