"""E-7-4R v2 eligibility 트리의 구조와 경계값 의미를 고정한다."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from uuid import UUID

import pytest


COMMON_V2_DIR = Path("extraction/common_v2")
E_7_4R_VISA_ID = "346834f7-ac6e-4958-8e0d-8c2b4fb03a7e"

PASS = "PASS"
FAIL = "FAIL"
REVIEW_REQUIRED = "REVIEW_REQUIRED"


def _read_rows(filename: str) -> list[dict[str, str]]:
    with (COMMON_V2_DIR / filename).open(newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))


GROUPS = _read_rows("visa_criterion_groups.csv")
CRITERIA = _read_rows("visa_requirement_criteria.csv")
E74R_GROUPS = [row for row in GROUPS if row["visa_id"] == E_7_4R_VISA_ID]
E74R_GROUPS_BY_KEY = {row["group_key"]: row for row in E74R_GROUPS}
E74R_GROUPS_BY_ID = {row["group_id"]: row for row in E74R_GROUPS}
E74R_GROUP_IDS = set(E74R_GROUPS_BY_ID)
E74R_CRITERIA = [row for row in CRITERIA if row["group_id"] in E74R_GROUP_IDS]


def _criterion_by_id(criteria_id: str) -> dict[str, str]:
    return next(row for row in E74R_CRITERIA if row["criteria_id"] == criteria_id)


def _direct_criteria(group_key: str) -> list[dict[str, str]]:
    group_id = E74R_GROUPS_BY_KEY[group_key]["group_id"]
    return [row for row in E74R_CRITERIA if row["group_id"] == group_id]


def _child_group_keys(group_key: str) -> set[str]:
    group_id = E74R_GROUPS_BY_KEY[group_key]["group_id"]
    return {row["group_key"] for row in E74R_GROUPS if row["parent_group_id"] == group_id}


def _is_uuid4(value: str) -> bool:
    parsed = UUID(value)
    return parsed.version == 4 and str(parsed) == value


def _expected_value(row: dict[str, str]):
    if row["criteria_type"] == "NUMERIC":
        return float(row["value_numeric"])
    if row["criteria_type"] == "LIST":
        return json.loads(row["value_text"])
    if row["criteria_type"] == "BOOLEAN":
        return row["value_text"].lower() == "true"
    return row["value_text"]


def _evaluate_criterion(row: dict[str, str], facts: dict[str, object]) -> str | None:
    if row["evaluation_mode"] == "INFORMATIONAL":
        return None
    if row["evaluation_mode"] == "MANUAL":
        return REVIEW_REQUIRED

    actual = facts.get(row["field_identifier"])
    expected = _expected_value(row)
    operator = row["operator"]

    if operator == "EQ":
        passed = actual == expected
    elif operator == "LT":
        passed = actual is not None and float(actual) < expected
    elif operator == "GTE":
        passed = actual is not None and float(actual) >= expected
    elif operator == "IN":
        passed = actual in expected
    elif operator == "NOT_IN":
        passed = actual not in expected
    elif operator == "EXISTS":
        passed = bool(actual)
    elif operator == "NOT_EXISTS":
        passed = not bool(actual)
    else:  # 이 fixture가 소비하는 E-7-4R operator가 늘어나면 의미를 명시적으로 추가한다.
        raise AssertionError(f"unsupported operator in semantic fixture: {operator}")
    return PASS if passed else FAIL


def _combine(operator: str, results: list[str]) -> str:
    if operator == "AND":
        if FAIL in results:
            return FAIL
        if REVIEW_REQUIRED in results:
            return REVIEW_REQUIRED
        return PASS
    if PASS in results:
        return PASS
    if REVIEW_REQUIRED in results:
        return REVIEW_REQUIRED
    return FAIL


def _evaluate_group(group_key: str, facts: dict[str, object]) -> str | None:
    group = E74R_GROUPS_BY_KEY[group_key]
    results = [
        result
        for row in _direct_criteria(group_key)
        if (result := _evaluate_criterion(row, facts)) is not None
    ]
    child_keys = sorted(_child_group_keys(group_key))
    results.extend(
        result
        for child_key in child_keys
        if (result := _evaluate_group(child_key, facts)) is not None
    )
    if not results:
        return None
    return _combine(group["boolean_operator"], results)


class TestE74RStructure:
    def test_all_e74r_ids_are_uuid4_and_criteria_stay_inside_the_e74r_tree(self):
        assert E74R_GROUPS
        assert E74R_CRITERIA
        assert all(_is_uuid4(row["group_id"]) for row in E74R_GROUPS)
        assert all(_is_uuid4(row["criteria_id"]) for row in E74R_CRITERIA)
        assert {row["group_id"] for row in E74R_CRITERIA} <= E74R_GROUP_IDS

    def test_existing_conceptual_rows_keep_their_ids(self):
        expected_names_by_id = {
            "d7958d0a-6990-42c9-9adf-8c296e964690": "허용 체류자격 체류기간 2년 이상",
            "9992cdb1-92c6-4afc-89b6-e0396b4490fe": "예정 근무처 인구감소지역 소재",
            "38715576-8ac6-41a8-85ee-c93c9ffa2473": "벌금 300만원 이상 형 이력 없음",
            "82978fc6-a68a-4a5c-bd66-f27436818ecc": "고용주 출입국관리법 결격사유 미해당",
            "2a85408f-1106-4c54-952f-f94ee5dbbc42": "K-point E74 시행일 이전 불법고용 적발",
            "cecbc5cf-ab3a-4eb4-8e55-1a08fcb9a6c3": "전환 후 계약연봉 일반(2,600만원 이상)",
            "164c975e-67e7-431f-85c7-79540f6b00e5": (
                "전환 후 계약연봉 농축산업·어업·내항상선 예외(2,500만원 이상)"
            ),
        }
        assert {
            criteria_id: _criterion_by_id(criteria_id)["criteria_name"]
            for criteria_id in expected_names_by_id
        } == expected_names_by_id

    def test_applicant_status_is_split_into_atomic_and_nested_paths(self):
        assert E74R_GROUPS_BY_KEY["e74r_applicant_status_paths"]["boolean_operator"] == "OR"
        assert _child_group_keys("e74r_applicant_status_paths") == {
            "e74r_applicant_standard",
            "e74r_population_decline_exception",
        }
        standard_fields = {
            row["field_identifier"] for row in _direct_criteria("e74r_applicant_standard")
        }
        assert standard_fields == {
            "applicant.eligible_status_residency_years_recent10y",
            "applicant.is_currently_registered_foreigner",
            "applicant.is_lawfully_employed_at_current_workplace",
        }
        assert _child_group_keys("e74r_population_decline_status_paths") == {
            "e74r_population_decline_d10_path"
        }
        assert len(_direct_criteria("e74r_population_decline_status_paths")) == 1

    def test_conduct_rows_are_eligibility_predicates_not_disqualifier_matches(self):
        rows = _direct_criteria("e74r_conduct")
        assert len(rows) == 6
        assert all(row["evaluation_mode"] == "AUTOMATED" for row in rows)
        by_field = {row["field_identifier"]: row for row in rows}
        assert (
            by_field["applicant.criminal_record.maximum_fine_amount_manwon_recent10y"]["operator"]
            == "LT"
        )
        assert by_field["applicant.immigration_act_violation_count_recent10y"]["operator"] == "LT"
        assert by_field["applicant.maximum_illegal_stay_months_recent10y"]["operator"] == "LT"
        assert {
            by_field["applicant.public_safety_harm_concern"]["operator"],
            by_field["applicant.economic_or_social_order_harm_concern"]["operator"],
            by_field["applicant.tax_delinquency_status"]["operator"],
        } == {"NOT_EXISTS"}

    def test_income_or_paths_each_include_salary_and_industry(self):
        assert E74R_GROUPS_BY_KEY["e74r_income"]["boolean_operator"] == "OR"
        assert _child_group_keys("e74r_income") == {
            "e74r_income_general",
            "e74r_income_industry_exception",
        }
        for group_key, industry_operator, salary in (
            ("e74r_income_general", "NOT_IN", "2600"),
            ("e74r_income_industry_exception", "IN", "2500"),
        ):
            rows = _direct_criteria(group_key)
            assert E74R_GROUPS_BY_KEY[group_key]["boolean_operator"] == "AND"
            assert {row["field_identifier"] for row in rows} == {
                "applicant.contract_annual_salary_manwon",
                "employment.industry",
            }
            industry_row = next(
                row for row in rows if row["field_identifier"] == "employment.industry"
            )
            salary_row = next(
                row
                for row in rows
                if row["field_identifier"] == "applicant.contract_annual_salary_manwon"
            )
            assert industry_row["operator"] == industry_operator
            assert salary_row["value_numeric"] == salary

    def test_employer_exception_is_an_or_path_with_atomic_conditions(self):
        assert E74R_GROUPS_BY_KEY["e74r_employer_compliance_paths"]["boolean_operator"] == "OR"
        assert _child_group_keys("e74r_employer_compliance_paths") == {
            "e74r_employer_standard_compliance",
            "e74r_employer_pre_kpoint_exception",
        }
        exception_rows = _direct_criteria("e74r_employer_pre_kpoint_exception")
        assert {row["field_identifier"] for row in exception_rows} == {
            "employer.illegal_employment_detection_before_2023_09_25",
            "application.is_existing_worker_transition",
            "employer.non_exempt_immigration_control_act_disqualifying_ground",
        }
        assert all(row["evaluation_mode"] == "AUTOMATED" for row in exception_rows)
        assert not any(
            row["evaluation_mode"] == "MANUAL" for row in _direct_criteria("e74r_employer")
        )


@pytest.mark.parametrize(
    ("facts", "expected"),
    [
        (
            {
                "applicant.eligible_status_residency_years_recent10y": 2,
                "applicant.is_currently_registered_foreigner": True,
                "applicant.is_lawfully_employed_at_current_workplace": True,
                "applicant.recent_regional_visa_or_dependent_status": False,
            },
            PASS,
        ),
        (
            {
                "applicant.eligible_status_residency_years_recent10y": 1.99,
                "applicant.is_currently_registered_foreigner": True,
                "applicant.is_lawfully_employed_at_current_workplace": True,
                "applicant.recent_regional_visa_or_dependent_status": False,
            },
            FAIL,
        ),
        (
            {
                "applicant.eligible_status_residency_years_recent10y": 2,
                "applicant.is_currently_registered_foreigner": False,
                "applicant.is_lawfully_employed_at_current_workplace": True,
                "applicant.recent_regional_visa_or_dependent_status": False,
            },
            FAIL,
        ),
        (
            {
                "applicant.eligible_status_residency_years_recent10y": 2,
                "applicant.is_currently_registered_foreigner": True,
                "applicant.is_lawfully_employed_at_current_workplace": False,
                "applicant.recent_regional_visa_or_dependent_status": False,
            },
            FAIL,
        ),
        (
            {
                "employment.planned_workplace_region_type": "인구감소지역",
                "applicant.is_job_seeking": True,
                "applicant.current_status": "E-9",
                "applicant.recent_regional_visa_or_dependent_status": False,
            },
            PASS,
        ),
        (
            {
                "employment.planned_workplace_region_type": "인구감소지역",
                "applicant.is_job_seeking": True,
                "applicant.current_status": "D-10",
                "applicant.immediately_prior_status": "E-7-4R",
                "applicant.recent_regional_visa_or_dependent_status": False,
            },
            PASS,
        ),
        (
            {
                "employment.planned_workplace_region_type": "인구감소관심지역",
                "applicant.is_job_seeking": True,
                "applicant.current_status": "E-9",
                "applicant.recent_regional_visa_or_dependent_status": False,
            },
            FAIL,
        ),
        (
            {
                "employment.planned_workplace_region_type": "인구감소지역",
                "applicant.is_job_seeking": True,
                "applicant.current_status": "D-10",
                "applicant.immediately_prior_status": "E-9",
                "applicant.recent_regional_visa_or_dependent_status": False,
            },
            FAIL,
        ),
    ],
)
def test_applicant_status_truth_table(facts: dict[str, object], expected: str):
    assert _evaluate_group("e74r_applicant_status", facts) == expected


@pytest.mark.parametrize(
    ("field", "eligible_value", "excluded_value"),
    [
        ("applicant.criminal_record.maximum_fine_amount_manwon_recent10y", 299, 300),
        ("applicant.immigration_act_violation_count_recent10y", 3, 4),
        ("applicant.maximum_illegal_stay_months_recent10y", 2.99, 3),
        ("applicant.tax_delinquency_status", False, True),
        ("applicant.public_safety_harm_concern", False, True),
        ("applicant.economic_or_social_order_harm_concern", False, True),
    ],
)
def test_conduct_disqualifier_truth_table(
    field: str, eligible_value: object, excluded_value: object
):
    clean = {
        "applicant.criminal_record.maximum_fine_amount_manwon_recent10y": 0,
        "applicant.immigration_act_violation_count_recent10y": 0,
        "applicant.maximum_illegal_stay_months_recent10y": 0,
        "applicant.tax_delinquency_status": False,
        "applicant.public_safety_harm_concern": False,
        "applicant.economic_or_social_order_harm_concern": False,
    }
    assert _evaluate_group("e74r_conduct", clean | {field: eligible_value}) == PASS
    assert _evaluate_group("e74r_conduct", clean | {field: excluded_value}) == FAIL


@pytest.mark.parametrize(
    ("industry", "salary", "expected"),
    [
        ("일반제조업", 2600, PASS),
        ("일반제조업", 2599, FAIL),
        ("농업", 2500, PASS),
        ("농업", 2499, FAIL),
        ("내항상선", 2500, PASS),
        ("일반제조업", 2500, FAIL),
    ],
)
def test_income_industry_truth_table(industry: str, salary: int, expected: str):
    facts = {
        "employment.industry": industry,
        "applicant.contract_annual_salary_manwon": salary,
    }
    assert _evaluate_group("e74r_income", facts) == expected


@pytest.mark.parametrize(
    ("facts", "expected"),
    [
        (
            {
                "employer.immigration_control_act_disqualifying_ground": False,
                "employer.illegal_employment_detection_before_2023_09_25": False,
                "application.is_existing_worker_transition": False,
                "employer.non_exempt_immigration_control_act_disqualifying_ground": False,
            },
            PASS,
        ),
        (
            {
                "employer.immigration_control_act_disqualifying_ground": True,
                "employer.illegal_employment_detection_before_2023_09_25": True,
                "application.is_existing_worker_transition": True,
                "employer.non_exempt_immigration_control_act_disqualifying_ground": False,
            },
            PASS,
        ),
        (
            {
                "employer.immigration_control_act_disqualifying_ground": True,
                "employer.illegal_employment_detection_before_2023_09_25": True,
                "application.is_existing_worker_transition": False,
                "employer.non_exempt_immigration_control_act_disqualifying_ground": False,
            },
            FAIL,
        ),
        (
            {
                "employer.immigration_control_act_disqualifying_ground": True,
                "employer.illegal_employment_detection_before_2023_09_25": False,
                "application.is_existing_worker_transition": True,
                "employer.non_exempt_immigration_control_act_disqualifying_ground": False,
            },
            FAIL,
        ),
        (
            {
                "employer.immigration_control_act_disqualifying_ground": True,
                "employer.illegal_employment_detection_before_2023_09_25": True,
                "application.is_existing_worker_transition": True,
                "employer.non_exempt_immigration_control_act_disqualifying_ground": True,
            },
            FAIL,
        ),
    ],
)
def test_employer_one_time_exception_truth_table(facts: dict[str, object], expected: str):
    assert _evaluate_group("e74r_employer_compliance_paths", facts) == expected
