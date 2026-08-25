"""F-2-R common schema v2의 중첩 대체경로 의미를 고정한다."""

from __future__ import annotations

import csv
from pathlib import Path
from uuid import UUID

import pytest

COMMON_V2_DIR = Path("extraction/common_v2")
F_2_R_VISA_ID = "a228433b-abe4-4785-8496-3e1cb3d597c1"

PASS = "PASS"
FAIL = "FAIL"
REVIEW_REQUIRED = "REVIEW_REQUIRED"


def _read_rows(filename: str) -> list[dict[str, str]]:
    with (COMMON_V2_DIR / filename).open(newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))


ALL_GROUPS = _read_rows("visa_criterion_groups.csv")
F2R_GROUPS = [row for row in ALL_GROUPS if row["visa_id"] == F_2_R_VISA_ID]
F2R_GROUPS_BY_ID = {row["group_id"]: row for row in F2R_GROUPS}
F2R_GROUPS_BY_KEY = {row["group_key"]: row for row in F2R_GROUPS}

ALL_CRITERIA = _read_rows("visa_requirement_criteria.csv")
F2R_CRITERIA = [row for row in ALL_CRITERIA if row["group_id"] in F2R_GROUPS_BY_ID]
F2R_CRITERIA_BY_NAME = {row["criteria_name"]: row for row in F2R_CRITERIA}


def _combine(operator: str, results: list[str]) -> str:
    assert results, "판정 참여 criteria나 자식 그룹이 없는 테스트 대상 그룹"
    if operator == "AND":
        if FAIL in results:
            return FAIL
        if REVIEW_REQUIRED in results:
            return REVIEW_REQUIRED
        return PASS
    if operator == "OR":
        if PASS in results:
            return PASS
        if REVIEW_REQUIRED in results:
            return REVIEW_REQUIRED
        return FAIL
    raise AssertionError(f"지원하지 않는 boolean_operator: {operator}")


def _evaluate(group_key: str, criterion_results: dict[str, str]) -> str:
    """실제 CSV 트리를 따라 강제한 원자 판정값을 재귀 결합한다.

    명세의 INFORMATIONAL 제외, AND/OR 우선순위를 테스트 안에서 독립적으로 구현해
    그룹 배치가 바뀌어 논리가 평탄화되면 truth table이 실패하도록 한다.
    """

    group = F2R_GROUPS_BY_KEY[group_key]
    direct_results = [
        criterion_results.get(row["criteria_name"], FAIL)
        for row in F2R_CRITERIA
        if row["group_id"] == group["group_id"] and row["evaluation_mode"] != "INFORMATIONAL"
    ]
    child_results = [
        _evaluate(child["group_key"], criterion_results)
        for child in F2R_GROUPS
        if child["parent_group_id"] == group["group_id"]
    ]
    return _combine(group["boolean_operator"], direct_results + child_results)


def _assert_group_shape(
    group_key: str,
    *,
    operator: str,
    parent_key: str,
    direct_criteria: set[str],
    child_groups: set[str],
) -> None:
    group = F2R_GROUPS_BY_KEY[group_key]
    parent = F2R_GROUPS_BY_KEY[parent_key]
    assert group["boolean_operator"] == operator
    assert group["parent_group_id"] == parent["group_id"]
    assert {
        row["criteria_name"] for row in F2R_CRITERIA if row["group_id"] == group["group_id"]
    } == direct_criteria
    assert {
        row["group_key"] for row in F2R_GROUPS if row["parent_group_id"] == group["group_id"]
    } == child_groups


class TestApplicantStatusStructure:
    def test_e74_and_e74r_paths_are_nested_below_applicant_or(self):
        _assert_group_shape(
            "f2r_applicant_status",
            operator="OR",
            parent_key="f2r_root",
            direct_criteria=set(),
            child_groups={"f2r_e74_path", "f2r_e74r_path"},
        )
        _assert_group_shape(
            "f2r_e74_path",
            operator="AND",
            parent_key="f2r_applicant_status",
            direct_criteria={"E-7-4 체류기간"},
            child_groups={"f2r_e74_status_options"},
        )
        _assert_group_shape(
            "f2r_e74_status_options",
            operator="OR",
            parent_key="f2r_e74_path",
            direct_criteria={
                "E-7-4 현 근무처 계속 근무",
                "E-7-4 계약 종료 경로",
                "E-7-4 후 D-10 포함",
            },
            child_groups=set(),
        )
        _assert_group_shape(
            "f2r_e74r_path",
            operator="AND",
            parent_key="f2r_applicant_status",
            direct_criteria={"E-7-4R 체류기간", "인구감소지역 거주"},
            child_groups=set(),
        )


@pytest.mark.parametrize(
    ("passing", "expected"),
    [
        ({"E-7-4 체류기간", "E-7-4 현 근무처 계속 근무"}, PASS),
        ({"E-7-4 체류기간", "E-7-4 계약 종료 경로"}, PASS),
        ({"E-7-4 체류기간", "E-7-4 후 D-10 포함"}, PASS),
        ({"E-7-4 체류기간"}, FAIL),
        ({"E-7-4 현 근무처 계속 근무"}, FAIL),
        ({"E-7-4R 체류기간", "인구감소지역 거주"}, PASS),
        ({"E-7-4R 체류기간"}, FAIL),
        ({"인구감소지역 거주"}, FAIL),
    ],
)
def test_applicant_status_truth_table(passing: set[str], expected: str):
    assert _evaluate("f2r_applicant_status", dict.fromkeys(passing, PASS)) == expected


class TestEducationOrIncomeStructure:
    def test_education_and_income_are_distinct_or_paths(self):
        _assert_group_shape(
            "f2r_education_or_income",
            operator="OR",
            parent_key="f2r_root",
            direct_criteria=set(),
            child_groups={"f2r_education_path", "f2r_income_path"},
        )
        _assert_group_shape(
            "f2r_education_path",
            operator="AND",
            parent_key="f2r_education_or_income",
            direct_criteria={"국내 교육과정 체류"},
            child_groups={"f2r_education_degree_status"},
        )
        _assert_group_shape(
            "f2r_education_degree_status",
            operator="OR",
            parent_key="f2r_education_path",
            direct_criteria={"국내 전문학사 이상 학위 취득"},
            child_groups={"f2r_education_expected_path"},
        )
        _assert_group_shape(
            "f2r_education_expected_path",
            operator="AND",
            parent_key="f2r_education_degree_status",
            direct_criteria={"국내 전문대학 이상 졸업 예정", "졸업예정 기한"},
            child_groups=set(),
        )
        _assert_group_shape(
            "f2r_income_path",
            operator="AND",
            parent_key="f2r_education_or_income",
            direct_criteria={
                "연간 생활임금 이상",
                "소득 인정 주체",
                "소득 산정기간",
                "인정 소득 종류",
            },
            child_groups=set(),
        )


@pytest.mark.parametrize(
    ("passing", "expected"),
    [
        ({"국내 교육과정 체류", "국내 전문학사 이상 학위 취득"}, PASS),
        ({"국내 교육과정 체류", "국내 전문대학 이상 졸업 예정", "졸업예정 기한"}, PASS),
        ({"국내 전문학사 이상 학위 취득"}, FAIL),
        ({"국내 교육과정 체류", "국내 전문대학 이상 졸업 예정"}, FAIL),
        ({"연간 생활임금 이상", "소득 인정 주체", "인정 소득 종류"}, PASS),
        ({"연간 생활임금 이상"}, FAIL),
    ],
)
def test_education_or_income_truth_table(passing: set[str], expected: str):
    assert _evaluate("f2r_education_or_income", dict.fromkeys(passing, PASS)) == expected


class TestEmployerCapacityStructure:
    def test_standard_and_small_business_paths_are_siblings_under_or(self):
        _assert_group_shape(
            "f2r_employment_capacity_paths",
            operator="OR",
            parent_key="f2r_employer",
            direct_criteria=set(),
            child_groups={"f2r_standard_employment_capacity", "f2r_small_business_exception"},
        )
        _assert_group_shape(
            "f2r_standard_employment_capacity",
            operator="AND",
            parent_key="f2r_employment_capacity_paths",
            direct_criteria={"내국인 고용인원 산정", "고용 허용인원 계산"},
            child_groups=set(),
        )
        _assert_group_shape(
            "f2r_small_business_exception",
            operator="AND",
            parent_key="f2r_employment_capacity_paths",
            direct_criteria={
                "특례 허용인원",
                "특례 대상",
                "소상공인 허용 업종",
                "사업 운영기간",
                "소상공인 특례 매출액",
            },
            child_groups=set(),
        )

    def test_common_employer_requirements_stay_outside_the_capacity_or(self):
        _assert_group_shape(
            "f2r_employer",
            operator="AND",
            parent_key="f2r_employment",
            direct_criteria={
                "국세·지방세 체납 없음",
                "중대 법 위반 고용주",
                "경미 법 위반 고용주",
                "성매매·사행·마약 관련 고용주",
                "성폭력 관련 고용주",
                "근로기준법 위반 고용주",
                "불법체류 다수 발생 초청자",
                "신고의무 반복 위반 고용주",
            },
            child_groups={"f2r_employment_capacity_paths"},
        )

    def test_sales_alternative_remains_one_manual_criterion(self):
        sales = F2R_CRITERIA_BY_NAME["소상공인 특례 매출액"]
        assert sales["criteria_id"] == "ba1630cc-1776-4093-9757-bac0f5f1ab4c"
        assert sales["evaluation_mode"] == "MANUAL"
        assert sales["field_identifier"] == ""
        assert sales["operator"] == ""
        assert sales["value_numeric"] == ""
        assert "전년도 매출액 1억원 이상" in sales["value_text"]
        assert "최근 2년 평균액 1억원 이상" in sales["value_text"]


SMALL_BUSINESS_CRITERIA = {
    "특례 허용인원",
    "특례 대상",
    "소상공인 허용 업종",
    "사업 운영기간",
    "소상공인 특례 매출액",
}


@pytest.mark.parametrize(
    ("results", "expected"),
    [
        ({"고용 허용인원 계산": PASS}, PASS),
        ({name: PASS for name in SMALL_BUSINESS_CRITERIA}, PASS),
        ({}, FAIL),
        ({"고용 허용인원 계산": REVIEW_REQUIRED}, REVIEW_REQUIRED),
        (
            {
                **{name: PASS for name in SMALL_BUSINESS_CRITERIA - {"소상공인 특례 매출액"}},
                "소상공인 특례 매출액": REVIEW_REQUIRED,
            },
            REVIEW_REQUIRED,
        ),
    ],
)
def test_employment_capacity_truth_table(results: dict[str, str], expected: str):
    assert _evaluate("f2r_employment_capacity_paths", results) == expected


class TestUuidLifecycle:
    def test_existing_group_uuids_are_preserved_when_only_parentage_changes(self):
        assert F2R_GROUPS_BY_KEY["f2r_applicant_status"]["group_id"] == (
            "b6736ef7-d3d4-4ac5-bf37-b282a9a2baa3"
        )
        assert F2R_GROUPS_BY_KEY["f2r_education_or_income"]["group_id"] == (
            "0afbb8e2-fbc4-4d32-8fe7-8a9b2b603eb9"
        )
        assert F2R_GROUPS_BY_KEY["f2r_employer"]["group_id"] == (
            "a73c677a-9af6-46c1-86c8-4162c3022556"
        )
        assert F2R_GROUPS_BY_KEY["f2r_small_business_exception"]["group_id"] == (
            "f1106f3f-7fb1-478e-9c20-24dc1c0bfda2"
        )

    @pytest.mark.parametrize(
        ("criteria_name", "criteria_id"),
        [
            ("E-7-4 체류기간", "1dea27f6-a648-4359-b526-c432fe997108"),
            ("E-7-4 현 근무처 계속 근무", "5ccfc29b-0289-4f55-8458-e708c8f3787d"),
            ("E-7-4 계약 종료 경로", "6428247e-68a9-42b2-87a8-8f82d03b6e93"),
            ("E-7-4 후 D-10 포함", "238c8701-2aed-4a65-a3fe-b2ae83b8c52e"),
            ("E-7-4R 체류기간", "3ff4bf67-c04b-4744-9e29-90ca7dbee389"),
            ("국내 교육과정 체류", "e99de2e2-917f-4509-9e9f-812c87fa0a98"),
            ("국내 전문학사 이상 학위 취득", "73a65413-d9c8-4562-ad66-f621c78f4e5a"),
            ("졸업예정 기한", "61edeeaa-fdfb-4f47-b40c-637519ae002a"),
            ("연간 생활임금 이상", "97c2d7cd-9e9b-452b-8b4e-e89e728cd8f4"),
            ("소득 인정 주체", "4c82898d-70ed-471b-ad64-941cc3ba7baa"),
            ("소득 산정기간", "3a3c2b3a-d6d2-4bf4-b569-c4800e2f4744"),
            ("인정 소득 종류", "0c674e1d-910a-46a1-be99-3e853b0dc0e9"),
            ("내국인 고용인원 산정", "88c7e6ec-87c3-4a33-98f0-0ce93be4f2b1"),
            ("고용 허용인원 계산", "690ca976-2e5c-482d-afcf-7df44ab215ae"),
            ("소상공인 특례 매출액", "ba1630cc-1776-4093-9757-bac0f5f1ab4c"),
        ],
    )
    def test_existing_criteria_uuids_are_preserved(self, criteria_name: str, criteria_id: str):
        assert F2R_CRITERIA_BY_NAME[criteria_name]["criteria_id"] == criteria_id

    def test_new_groups_and_split_criteria_use_uuid4(self):
        new_group_keys = {
            "f2r_e74_path",
            "f2r_e74_status_options",
            "f2r_e74r_path",
            "f2r_education_path",
            "f2r_education_degree_status",
            "f2r_education_expected_path",
            "f2r_income_path",
            "f2r_employment_capacity_paths",
            "f2r_standard_employment_capacity",
        }
        new_ids = {F2R_GROUPS_BY_KEY[key]["group_id"] for key in new_group_keys}
        new_ids |= {
            F2R_CRITERIA_BY_NAME[name]["criteria_id"]
            for name in {"인구감소지역 거주", "국내 전문대학 이상 졸업 예정"}
        }
        assert all(UUID(value).version == 4 for value in new_ids)
        assert len(new_ids) == 11
