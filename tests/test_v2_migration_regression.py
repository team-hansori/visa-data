"""v1 -> v2 이관 완료 데이터에 대한 고정 회귀 테스트(issue #44 task 10, Deliverable 2).

`extraction/common_v2/*.csv`를 합성 fixture가 아니라 실제 파일 그대로 읽어, 이미 검수를
거쳐 확정된 사실들을 고정한다. 목적은 스키마 계약 검증(`test_validate_common_schema_v2.py`)이
아니라 "이 특정 값이 나중에 실수로 바뀌면 테스트가 시끄럽게 실패해야 한다"는 회귀 방지다.

각 숫자·문자열은 이 테스트를 작성하며 실제 CSV 파일을 다시 읽어 확인했다(task-10-brief.md의
수치를 그대로 베끼지 않았다). 이 파일은 확정된 의미 값의 회귀를 고정하고,
`tests/test_migrate_to_v2.py`는 검수 스냅샷 13개 파일의 결정적 재생성과 원본 보호를 별도로
검증한다.
"""

from __future__ import annotations

import csv
from pathlib import Path

COMMON_V2_DIR = Path("extraction/common_v2")

F_4_R_VISA_ID = "606d8651-1d04-47fe-8f69-165b3ed3d834"
E_7_4R_VISA_ID = "346834f7-ac6e-4958-8e0d-8c2b4fb03a7e"
F_2_R_VISA_ID = "a228433b-abe4-4785-8496-3e1cb3d597c1"


def _read_rows(table_filename: str) -> list[dict[str, str]]:
    path = COMMON_V2_DIR / table_filename
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


class TestE7_4RQuotaSnapshot:
    """E-7-4R visa_quota_snapshots의 유일한 행에 대한 확정 수치(542/246/10/236/306)."""

    def test_single_snapshot_row_has_expected_values(self):
        rows = _read_rows("visa_quota_snapshots.csv")
        policies = {row["quota_policy_id"]: row for row in _read_rows("visa_quota_policies.csv")}
        e74r_rows = [
            row for row in rows if policies[row["quota_policy_id"]]["visa_id"] == E_7_4R_VISA_ID
        ]
        assert len(e74r_rows) == 1
        row = e74r_rows[0]
        assert row["allocated_quota"] == "542"
        assert row["recommended_count"] == "246"
        assert row["quota_exempt_count"] == "10"
        assert row["consumed_quota"] == "236"
        assert row["remaining_quota"] == "306"
        assert row["scope_type"] == "PROVINCE"
        assert row["scope_name"] == "충청북도"

    def test_snapshot_belongs_to_e7_4r_via_quota_policy(self):
        snapshot_rows = _read_rows("visa_quota_snapshots.csv")
        policy_rows = _read_rows("visa_quota_policies.csv")
        policies_by_id = {row["quota_policy_id"]: row for row in policy_rows}

        snapshot = next(
            row
            for row in snapshot_rows
            if policies_by_id[row["quota_policy_id"]]["visa_id"] == E_7_4R_VISA_ID
        )
        policy = policies_by_id[snapshot["quota_policy_id"]]
        assert policy["visa_id"] == E_7_4R_VISA_ID


class TestE7_4RScoring:
    """E-7-4R visa_scoring_models/items의 확정 수치(300/200/50, 29행, MAX_SCORE_ONLY 2행)."""

    def test_scoring_model_has_expected_points(self):
        rows = _read_rows("visa_scoring_models.csv")
        assert len(rows) == 1
        row = rows[0]
        assert row["visa_id"] == E_7_4R_VISA_ID
        assert row["base_maximum_points"] == "300"
        assert row["minimum_required_points"] == "200"
        assert row["penalty_cap_points"] == "50"

    def test_scoring_items_has_exactly_29_rows(self):
        rows = _read_rows("visa_scoring_items.csv")
        assert len(rows) == 29

    def test_recommendation_source_exclusive_group_uses_max_score_only(self):
        rows = _read_rows("visa_scoring_items.csv")
        recommendation_rows = [
            row for row in rows if row["exclusive_group"] == "RECOMMENDATION_SOURCE"
        ]
        assert len(recommendation_rows) == 2
        for row in recommendation_rows:
            assert row["stacking_rule"] == "MAX_SCORE_ONLY"
        criteria_texts = {row["criterion"] for row in recommendation_rows}
        assert criteria_texts == {"추천 - 중앙부처", "추천 - 광역지자체"}


class TestF2RNestedLogic:
    """F-2-R f2r_language(OR, 3개) / f2r_conduct(AND) 중첩 논리."""

    def test_f2r_language_group_is_or_with_three_criteria(self):
        groups = _read_rows("visa_criterion_groups.csv")
        criteria = _read_rows("visa_requirement_criteria.csv")

        language_group = next(row for row in groups if row["group_key"] == "f2r_language")
        assert language_group["visa_id"] == F_2_R_VISA_ID
        assert language_group["boolean_operator"] == "OR"

        language_criteria = [
            row for row in criteria if row["group_id"] == language_group["group_id"]
        ]
        assert len(language_criteria) == 3
        names = {row["criteria_name"] for row in language_criteria}
        assert names == {"한국어능력시험", "사회통합프로그램 이수", "사회통합프로그램 사전평가"}

    def test_f2r_conduct_group_is_and(self):
        groups = _read_rows("visa_criterion_groups.csv")
        conduct_group = next(row for row in groups if row["group_key"] == "f2r_conduct")
        assert conduct_group["visa_id"] == F_2_R_VISA_ID
        assert conduct_group["boolean_operator"] == "AND"


class TestF4RNestedLogic:
    """F-4-R f4r_eligibility_paths(OR, 3개) /
    f4r_dependent_child_requirements(AND, 연령 2개 + 재학요건 OR 하위그룹)."""

    def test_f4r_eligibility_paths_group_is_or_with_three_criteria(self):
        groups = _read_rows("visa_criterion_groups.csv")
        criteria = _read_rows("visa_requirement_criteria.csv")

        paths_group = next(row for row in groups if row["group_key"] == "f4r_eligibility_paths")
        assert paths_group["visa_id"] == F_4_R_VISA_ID
        assert paths_group["boolean_operator"] == "OR"

        paths_criteria = [row for row in criteria if row["group_id"] == paths_group["group_id"]]
        assert len(paths_criteria) == 3
        names = {row["criteria_name"] for row in paths_criteria}
        assert names == {
            "신청자격(기존거주자)",
            "신청자격(국내전입자)",
            "신청자격(해외전입자)",
        }

    def test_f4r_dependent_child_requirements_group_is_and_with_age_criteria_and_or_subgroup(
        self,
    ):
        groups = _read_rows("visa_criterion_groups.csv")
        criteria = _read_rows("visa_requirement_criteria.csv")
        groups_by_id = {row["group_id"]: row for row in groups}

        requirements_group = next(
            row for row in groups if row["group_key"] == "f4r_dependent_child_requirements"
        )
        assert requirements_group["visa_id"] == F_4_R_VISA_ID
        assert requirements_group["boolean_operator"] == "AND"

        direct_criteria = [
            row for row in criteria if row["group_id"] == requirements_group["group_id"]
        ]
        assert len(direct_criteria) == 2
        criteria_names = {row["criteria_name"] for row in direct_criteria}
        assert criteria_names == {"동반자녀 연령요건(하한)", "동반자녀 연령요건(상한)"}

        child_groups = [
            row for row in groups if row["parent_group_id"] == requirements_group["group_id"]
        ]
        assert len(child_groups) == 1
        school_paths_group = child_groups[0]
        assert school_paths_group["group_key"] == "f4r_dependent_child_school_paths"
        assert school_paths_group["boolean_operator"] == "OR"
        assert groups_by_id[school_paths_group["group_id"]]["visa_id"] == F_4_R_VISA_ID


class TestF4RUuidLifecycle:
    """F-4-R의 v1 공통 UUID가 v2에서도 재발급 없이 재사용됐는지 고정한다."""

    def test_f4r_visa_id_matches_reused_v1_uuid(self):
        rows = _read_rows("visa_requirements.csv")
        f4r_row = next(row for row in rows if row["visa_code"] == "F-4-R")
        assert f4r_row["visa_id"] == F_4_R_VISA_ID
