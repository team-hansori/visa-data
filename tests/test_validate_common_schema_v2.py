"""validate_common_schema_v2.py(공통 스키마 v2 검증기) 회귀 테스트.

기본 fixture 부분은 13개 테이블이 서로 정합성 있게 맞물리는 최소 fixture 행 집합을
손으로 구성해 검증기가 통과/거부해야 하는 경우를 확인한다.

`TestCriterionGroupTreeIntegrity*`/`TestDocumentAttachmentRelationIntegrity*` 클래스는
task-3에서 "실제 마이그레이션 데이터가 준비되는 후속 작업(4~10단계)의 범위"로 미뤄뒀던
ROOT 유일성·순환참조·OR 그룹 최소 자식 수 검사(issue #44 task 10)를 다룬다. 실제 이관
데이터(`extraction/common_v2/`)가 이제 존재하므로, 각 규칙마다 실제 데이터에 대한
긍정 검증과 합성 fixture에 대한 부정(거부) 검증을 함께 둔다.
"""

from __future__ import annotations

import copy
from pathlib import Path

from scripts.schema_v2 import (
    DOCUMENT_ATTACHMENT_RELATIONS,
    SCHEMA_V2,
    SOURCE_RECORD_MAPPINGS,
    TABLE_ORDER,
    VISA_CRITERION_GROUPS,
    VISA_QUOTA_POLICIES,
    VISA_QUOTA_SNAPSHOTS,
    VISA_REQUIREMENT_CRITERIA,
)
from scripts.uuid_utils import generate_uuid4
from scripts.validate_common_schema_v2 import (
    _check_against_baseline,
    _check_criterion_group_tree_integrity,
    _check_document_attachment_relation_integrity,
    _check_quota_arithmetic,
    _check_target_table_is_real_table_name,
    _read_baseline,
    read_csv,
    validate_all,
    validate_directory,
)

REAL_COMMON_V2_DIR = Path("extraction/common_v2")

# --------------------------------------------------------------------------
# 서로 참조가 맞물리는 13개 테이블의 최소 유효 fixture
# --------------------------------------------------------------------------


def build_valid_tables_rows() -> dict[str, list[dict[str, str]]]:
    """13개 테이블에 각각 1~2행씩 담긴, FK가 모두 맞물리는 최소 유효 데이터셋을 만든다."""
    ids = {
        name: generate_uuid4()
        for name in [
            "source_document",
            "visa",
            "group_root",
            "criteria",
            "score_model",
            "scoring_item",
            "stage",
            "document_main",
            "document_attachment",
            "relation",
            "quota_policy",
            "quota_snapshot",
            "change",
            "mapping",
        ]
    }

    tables_rows: dict[str, list[dict[str, str]]] = {
        "source_documents": [
            {
                "source_document_id": ids["source_document"],
                "source_document_key": "r12_announcement_2026_test",
                "visa_id": "",
                "document_type": "ANNOUNCEMENT",
                "document_name": "테스트 공고문",
                "notice_round": "12",
                "published_at": "2026-01-01",
                "source_location": "data/raw/test.pdf",
                "file_hash_sha256": "a" * 64,
                "page_basis": "PDF",
                "last_verified_at": "2026-01-02",
            }
        ],
        "visa_requirements": [
            {
                "visa_id": ids["visa"],
                "visa_code": "F-2-R",
                "visa_name_kr": "테스트 비자",
                "program_type": "REGIONAL_SPECIALIZED",
                "target_regions_json": '["제천시"]',
                "residency_limit_years": "2",
                "allowed_industries_json": "",
                "application_method": "방문접수",
                "next_visa_code": "",
                "valid_from": "2026-01-01",
                "valid_to": "",
                "source_document_id": ids["source_document"],
                "source_page": "1",
                "last_verified_at": "2026-01-02",
            }
        ],
        "visa_criterion_groups": [
            {
                "group_id": ids["group_root"],
                "visa_id": ids["visa"],
                "parent_group_id": "",
                "group_key": "root",
                "group_name_kr": "루트 그룹",
                "boolean_operator": "AND",
                "applicability_note": "",
                "display_order": "1",
                "valid_from": "2026-01-01",
                "valid_to": "",
                "source_document_id": ids["source_document"],
                "source_page": "1",
                "last_verified_at": "2026-01-02",
            }
        ],
        "visa_requirement_criteria": [
            {
                "criteria_id": ids["criteria"],
                "group_id": ids["group_root"],
                "criteria_name": "체류기간",
                "field_identifier": "residency.years",
                "criteria_type": "NUMERIC",
                "evaluation_mode": "AUTOMATED",
                "operator": "GTE",
                "value_numeric": "2",
                "value_text": "체류기간 2년 이상",
                "unit": "YEAR",
                "measurement_window_value": "",
                "measurement_window_unit": "",
                "special_case_note": "",
                "display_order": "1",
                "valid_from": "2026-01-01",
                "valid_to": "",
                "source_document_id": ids["source_document"],
                "source_page": "1",
                "last_verified_at": "2026-01-02",
            }
        ],
        "visa_scoring_models": [
            {
                "score_model_id": ids["score_model"],
                "visa_id": ids["visa"],
                "model_name_kr": "테스트 점수표",
                "model_purpose": "QUOTA_RANKING",
                "applies_when": "APPLICATIONS_EXCEED_QUOTA",
                "selection_rule": "HIGHEST_TOTAL_SCORE_FIRST",
                "tie_breaker_rule": "",
                "base_maximum_points": "100",
                "minimum_required_points": "60",
                "final_maximum_points": "",
                "bonus_cap_points": "",
                "penalty_cap_points": "10",
                "from_round": "12",
                "to_round": "",
                "valid_from": "2026-01-01",
                "valid_to": "",
                "source_document_id": ids["source_document"],
                "source_page": "1",
                "notes": "",
            }
        ],
        "visa_scoring_items": [
            {
                "scoring_item_id": ids["scoring_item"],
                "score_model_id": ids["score_model"],
                "score_group": "BASE",
                "category": "LANGUAGE",
                "criterion": "TOPIK 3급 이상",
                "min_value": "",
                "max_value": "",
                "min_inclusive": "",
                "max_inclusive": "",
                "value_text": "TOPIK 3급 이상",
                "unit": "TOPIK_GRADE",
                "measurement_window_value": "",
                "measurement_window_unit": "",
                "points": "10",
                "maximum_points": "",
                "is_mandatory": "false",
                "minimum_required_points": "",
                "exclusive_group": "",
                "stacking_rule": "STACK",
                "evidence_document": "TOPIK 성적표",
                "display_order": "1",
                "valid_from": "2026-01-01",
                "valid_to": "",
                "source_document_id": ids["source_document"],
                "source_page": "1",
            }
        ],
        "visa_process_stages": [
            {
                "stage_id": ids["stage"],
                "visa_id": ids["visa"],
                "stage_order": "1",
                "stage_code": "NOTICE_PUBLICATION",
                "stage_name_kr": "공고",
                "actor_from": "시",
                "actor_to": "일반",
                "stage_start_date": "2026-01-01",
                "stage_end_date": "2026-01-01",
                "notice_round": "12",
                "notes": "",
                "valid_from": "2026-01-01",
                "valid_to": "",
                "source_document_id": ids["source_document"],
                "source_page": "1",
                "last_verified_at": "2026-01-02",
            }
        ],
        "document_requirements": [
            {
                "document_requirement_id": ids["document_main"],
                "stage_id": ids["stage"],
                "document_name": "신청서",
                "document_category": "APPLICATION",
                "filled_by": "신청자",
                "submitted_by": "신청자",
                "submission_target": "시청",
                "signer": "신청자",
                "requirement_status": "REQUIRED",
                "alternative_group": "",
                "condition_note": "",
                "display_order": "1",
                "valid_from": "2026-01-01",
                "valid_to": "",
                "source_document_id": ids["source_document"],
                "source_page": "1",
                "last_verified_at": "2026-01-02",
                "notes": "",
            },
            {
                "document_requirement_id": ids["document_attachment"],
                "stage_id": ids["stage"],
                "document_name": "첨부 서류",
                "document_category": "IDENTITY",
                "filled_by": "신청자",
                "submitted_by": "신청자",
                "submission_target": "시청",
                "signer": "신청자",
                "requirement_status": "REQUIRED",
                "alternative_group": "",
                "condition_note": "",
                "display_order": "2",
                "valid_from": "2026-01-01",
                "valid_to": "",
                "source_document_id": ids["source_document"],
                "source_page": "1",
                "last_verified_at": "2026-01-02",
                "notes": "",
            },
        ],
        "document_attachment_relations": [
            {
                "relation_id": ids["relation"],
                "parent_document_id": ids["document_main"],
                "attachment_document_id": ids["document_attachment"],
                "requirement_status": "REQUIRED",
                "alternative_group": "",
                "condition_note": "",
                "display_order": "1",
                "valid_from": "2026-01-01",
                "valid_to": "",
                "source_document_id": ids["source_document"],
                "source_page": "1",
            }
        ],
        "visa_quota_policies": [
            {
                "quota_policy_id": ids["quota_policy"],
                "visa_id": ids["visa"],
                "quota_type": "LIMITED",
                "quota_unit": "PERSON",
                "valid_from": "2026-01-01",
                "valid_to": "",
                "source_document_id": ids["source_document"],
                "source_page": "1",
            }
        ],
        "visa_quota_snapshots": [
            {
                "quota_snapshot_id": ids["quota_snapshot"],
                "quota_policy_id": ids["quota_policy"],
                "notice_round": "12",
                "as_of_date": "2026-01-15",
                "scope_type": "MUNICIPALITY",
                "scope_name": "제천시",
                "parent_scope_name": "충청북도",
                "allocated_quota": "75",
                "recommended_count": "",
                "quota_exempt_count": "",
                "consumed_quota": "42",
                "remaining_quota": "33",
                "consumption_exception": "",
                "valid_from": "2026-01-01",
                "valid_to": "",
                "source_document_id": ids["source_document"],
                "source_page": "1",
                "recorded_at": "2026-01-15T00:00:00",
            }
        ],
        "change_history": [
            {
                "change_id": ids["change"],
                "visa_id": ids["visa"],
                "table_name": "visa_requirements",
                "field_identifier": "residency_limit_years",
                "from_round": "11",
                "to_round": "12",
                "old_value": "1",
                "new_value": "2",
                "change_type": "VALUE_CHANGED",
                "old_source_page": "1",
                "new_source_page": "1",
                "description": "체류기간 상한 변경",
            }
        ],
        "source_record_mappings": [
            {
                "mapping_id": ids["mapping"],
                "visa_id": ids["visa"],
                "source_dataset": "D_visa_requirements",
                "source_table": "visa_requirements",
                "source_record_id": "legacy-1",
                "source_group_path": "",
                "source_document_id": ids["source_document"],
                "source_page": "1",
                "valid_from": "2026-01-01",
                "valid_to": "",
                "target_table": "visa_requirements",
                "target_record_id": ids["visa"],
                "mapping_action": "COPY",
                "mapping_status": "MAPPED",
                "blocking_reason": "",
                "mapped_at": "2026-01-02T00:00:00",
                "mapping_note": "",
            }
        ],
    }

    assert set(tables_rows) == set(TABLE_ORDER), "fixture가 13개 테이블을 모두 덮지 않음"
    for name, rows in tables_rows.items():
        expected_header = set(SCHEMA_V2[name].header)
        for row in rows:
            assert set(row) == expected_header, f"{name} fixture 행이 스키마 컬럼과 다름"
    return tables_rows


def mutate(
    tables_rows: dict[str, list[dict[str, str]]],
    table: str,
    row_index: int,
    column: str,
    value: str,
) -> dict[str, list[dict[str, str]]]:
    """fixture를 깊은 복사한 뒤 특정 셀 하나만 바꿔서 반환한다(원본은 건드리지 않음)."""
    mutated = copy.deepcopy(tables_rows)
    mutated[table][row_index][column] = value
    return mutated


class TestHappyPath:
    def test_valid_fixture_passes_with_no_errors(self):
        errors = validate_all(build_valid_tables_rows())
        assert errors == []


class TestEnumRejection:
    def test_boolean_operator_rejects_invalid_value(self):
        rows = mutate(
            build_valid_tables_rows(), "visa_criterion_groups", 0, "boolean_operator", "XOR"
        )
        errors = validate_all(rows)
        assert any("boolean_operator" in e for e in errors)

    def test_criteria_type_rejects_invalid_value(self):
        rows = mutate(
            build_valid_tables_rows(), "visa_requirement_criteria", 0, "criteria_type", "FLOAT"
        )
        errors = validate_all(rows)
        assert any("criteria_type" in e for e in errors)

    def test_evaluation_mode_rejects_invalid_value(self):
        rows = mutate(
            build_valid_tables_rows(),
            "visa_requirement_criteria",
            0,
            "evaluation_mode",
            "SEMI_AUTO",
        )
        errors = validate_all(rows)
        assert any("evaluation_mode" in e for e in errors)

    def test_operator_rejects_invalid_value(self):
        rows = mutate(build_valid_tables_rows(), "visa_requirement_criteria", 0, "operator", "==")
        errors = validate_all(rows)
        assert any("operator" in e for e in errors)

    def test_model_purpose_rejects_invalid_value(self):
        rows = mutate(build_valid_tables_rows(), "visa_scoring_models", 0, "model_purpose", "MAYBE")
        errors = validate_all(rows)
        assert any("model_purpose" in e for e in errors)

    def test_score_group_rejects_invalid_value(self):
        rows = mutate(build_valid_tables_rows(), "visa_scoring_items", 0, "score_group", "EXTRA")
        errors = validate_all(rows)
        assert any("score_group" in e for e in errors)

    def test_stacking_rule_rejects_invalid_value(self):
        rows = mutate(
            build_valid_tables_rows(), "visa_scoring_items", 0, "stacking_rule", "COMBINE"
        )
        errors = validate_all(rows)
        assert any("stacking_rule" in e for e in errors)

    def test_requirement_status_rejects_invalid_value(self):
        rows = mutate(
            build_valid_tables_rows(),
            "document_requirements",
            0,
            "requirement_status",
            "MAYBE_REQUIRED",
        )
        errors = validate_all(rows)
        assert any("requirement_status" in e for e in errors)

    def test_quota_type_rejects_invalid_value(self):
        rows = mutate(build_valid_tables_rows(), "visa_quota_policies", 0, "quota_type", "SOME")
        errors = validate_all(rows)
        assert any("quota_type" in e for e in errors)

    def test_scope_type_rejects_invalid_value(self):
        rows = mutate(build_valid_tables_rows(), "visa_quota_snapshots", 0, "scope_type", "CITY")
        errors = validate_all(rows)
        assert any("scope_type" in e for e in errors)

    def test_document_type_rejects_invalid_value(self):
        rows = mutate(build_valid_tables_rows(), "source_documents", 0, "document_type", "MEMO")
        errors = validate_all(rows)
        assert any("document_type" in e for e in errors)

    def test_mapping_action_rejects_invalid_value(self):
        rows = mutate(
            build_valid_tables_rows(), "source_record_mappings", 0, "mapping_action", "DELETE"
        )
        errors = validate_all(rows)
        assert any("mapping_action" in e for e in errors)

    def test_mapping_status_rejects_invalid_value(self):
        rows = mutate(
            build_valid_tables_rows(), "source_record_mappings", 0, "mapping_status", "DONE"
        )
        errors = validate_all(rows)
        assert any("mapping_status" in e for e in errors)


class TestPkFormatAndUniqueness:
    def test_rejects_non_uuid4_pk(self):
        rows = mutate(build_valid_tables_rows(), "visa_requirements", 0, "visa_id", "not-a-uuid")
        errors = validate_all(rows)
        assert any("visa_id" in e for e in errors)

    def test_rejects_empty_pk(self):
        rows = mutate(build_valid_tables_rows(), "visa_requirements", 0, "visa_id", "")
        errors = validate_all(rows)
        assert any("비어 있음" in e for e in errors)

    def test_rejects_pk_reused_across_different_tables(self):
        rows = build_valid_tables_rows()
        # visa_requirements의 PK를 다른 테이블(visa_criterion_groups)의 PK로도 재사용 —
        # "공통 마스터 전체에서 UUID가 겹치면 안 된다"는 요구사항을 검사한다.
        shared = rows["visa_requirements"][0]["visa_id"]
        rows["visa_criterion_groups"][0]["group_id"] = shared
        errors = validate_all(rows)
        assert any("중복 사용됨" in e for e in errors)

    def test_rejects_duplicate_pk_within_same_table(self):
        rows = build_valid_tables_rows()
        dup_row = dict(rows["document_requirements"][0])
        dup_row["document_requirement_id"] = rows["document_requirements"][1][
            "document_requirement_id"
        ]
        rows["document_requirements"].append(dup_row)
        # FK 정합성이 깨지지 않도록 stage_id 등은 그대로 두되, attachment 관계 검증은
        # 건드리지 않는다 — 이 테스트의 관심사는 PK 중복 탐지뿐이다.
        errors = validate_all(rows)
        assert any("중복 사용됨" in e for e in errors)


class TestForeignKeyRejection:
    def test_rejects_fk_pointing_to_missing_parent(self):
        rows = mutate(
            build_valid_tables_rows(),
            "visa_requirement_criteria",
            0,
            "group_id",
            generate_uuid4(),
        )
        errors = validate_all(rows)
        assert any("group_id" in e and "존재하지 않음" in e for e in errors)

    def test_rejects_empty_required_fk(self):
        rows = mutate(build_valid_tables_rows(), "visa_process_stages", 0, "visa_id", "")
        errors = validate_all(rows)
        assert any("visa_id" in e and "비어 있음" in e for e in errors)

    def test_nullable_fk_may_be_empty(self):
        # source_documents.visa_id는 nullable — 이미 fixture에서 빈 값이므로 통과해야 한다.
        rows = build_valid_tables_rows()
        assert rows["source_documents"][0]["visa_id"] == ""
        errors = validate_all(rows)
        assert errors == []

    def test_self_referential_fk_rejects_missing_parent_group(self):
        rows = mutate(
            build_valid_tables_rows(),
            "visa_criterion_groups",
            0,
            "parent_group_id",
            generate_uuid4(),
        )
        errors = validate_all(rows)
        assert any("parent_group_id" in e and "존재하지 않음" in e for e in errors)


class TestNullableFieldsNotCoerced:
    def test_nullable_numeric_field_empty_string_is_valid(self):
        rows = build_valid_tables_rows()
        rows["visa_requirements"][0]["residency_limit_years"] = ""
        errors = validate_all(rows)
        assert errors == [], "nullable 필드의 빈 값은 유효해야 함"

    def test_empty_string_not_treated_as_zero(self):
        rows = build_valid_tables_rows()
        rows["visa_quota_snapshots"][0]["recommended_count"] = ""
        errors = validate_all(rows)
        # 빈 값 자체는 통과해야 하고, 검증기가 "0"으로 바꿔치기하지 않았는지 확인한다.
        assert errors == []
        assert rows["visa_quota_snapshots"][0]["recommended_count"] == ""

    def test_required_field_left_empty_is_rejected(self):
        rows = mutate(build_valid_tables_rows(), "visa_requirements", 0, "visa_code", "")
        errors = validate_all(rows)
        assert any("visa_code" in e and "비어 있음" in e for e in errors)


class TestValidPeriodOrdering:
    def test_rejects_valid_to_before_valid_from(self):
        rows = build_valid_tables_rows()
        rows["visa_requirements"][0]["valid_from"] = "2026-06-01"
        rows["visa_requirements"][0]["valid_to"] = "2026-01-01"
        errors = validate_all(rows)
        assert any("valid_to" in e and "valid_from" in e for e in errors)

    def test_accepts_valid_to_after_valid_from(self):
        rows = build_valid_tables_rows()
        rows["visa_requirements"][0]["valid_from"] = "2026-01-01"
        rows["visa_requirements"][0]["valid_to"] = "2026-06-01"
        errors = validate_all(rows)
        assert errors == []

    def test_accepts_equal_valid_from_and_valid_to(self):
        rows = build_valid_tables_rows()
        rows["visa_requirements"][0]["valid_from"] = "2026-01-01"
        rows["visa_requirements"][0]["valid_to"] = "2026-01-01"
        errors = validate_all(rows)
        assert errors == []


class TestFormatChecks:
    def test_rejects_invalid_date(self):
        rows = mutate(build_valid_tables_rows(), "visa_requirements", 0, "valid_from", "2026/01/01")
        errors = validate_all(rows)
        assert any("valid_from" in e for e in errors)

    def test_rejects_non_numeric_value(self):
        rows = mutate(
            build_valid_tables_rows(), "visa_requirement_criteria", 0, "value_numeric", "약간"
        )
        errors = validate_all(rows)
        assert any("value_numeric" in e for e in errors)

    def test_rejects_invalid_json_array(self):
        rows = mutate(
            build_valid_tables_rows(), "visa_requirements", 0, "target_regions_json", "제천시"
        )
        errors = validate_all(rows)
        assert any("target_regions_json" in e for e in errors)

    def test_accepts_valid_json_array(self):
        rows = build_valid_tables_rows()
        rows["visa_requirements"][0]["target_regions_json"] = '["제천시","보은군"]'
        errors = validate_all(rows)
        assert errors == []

    def test_criteria_list_value_text_must_be_valid_json_when_criteria_type_is_list(self):
        rows = build_valid_tables_rows()
        rows["visa_requirement_criteria"][0]["criteria_type"] = "LIST"
        rows["visa_requirement_criteria"][0]["operator"] = "IN"
        rows["visa_requirement_criteria"][0]["value_text"] = "E-9, E-10, H-2"  # JSON 아님
        errors = validate_all(rows)
        assert any("value_text" in e and "JSON" in e for e in errors)

    def test_criteria_list_value_text_valid_json_passes(self):
        rows = build_valid_tables_rows()
        rows["visa_requirement_criteria"][0]["criteria_type"] = "LIST"
        rows["visa_requirement_criteria"][0]["operator"] = "IN"
        rows["visa_requirement_criteria"][0]["value_text"] = '["E-9","E-10","H-2"]'
        errors = validate_all(rows)
        assert errors == []


class TestAutomatedConditionalRequirements:
    def test_automated_without_field_identifier_is_rejected(self):
        rows = mutate(
            build_valid_tables_rows(), "visa_requirement_criteria", 0, "field_identifier", ""
        )
        errors = validate_all(rows)
        assert any("field_identifier" in e and "AUTOMATED" in e for e in errors)

    def test_automated_without_operator_is_rejected(self):
        rows = mutate(build_valid_tables_rows(), "visa_requirement_criteria", 0, "operator", "")
        errors = validate_all(rows)
        assert any("operator" in e and "AUTOMATED" in e for e in errors)

    def test_manual_without_operator_is_allowed(self):
        rows = build_valid_tables_rows()
        rows["visa_requirement_criteria"][0]["evaluation_mode"] = "MANUAL"
        rows["visa_requirement_criteria"][0]["operator"] = ""
        rows["visa_requirement_criteria"][0]["field_identifier"] = ""
        rows["visa_requirement_criteria"][0]["value_text"] = (
            "현재 근무처에서 합법적으로 근로 중인지 확인"
        )
        errors = validate_all(rows)
        assert errors == []


class TestForbiddenNamesAndCsvSuffix:
    def test_validate_all_flags_forbidden_names_via_schema(self, monkeypatch):
        import scripts.validate_common_schema_v2 as validator_module

        def _fake_forbidden():
            return ["금지된 테이블명이 스키마에 있음: visa_round_facts"]

        monkeypatch.setattr(validator_module.schema_v2, "check_no_forbidden_names", _fake_forbidden)
        errors = validate_all(build_valid_tables_rows())
        assert any("visa_round_facts" in e for e in errors)

    def test_table_name_value_with_csv_suffix_is_rejected(self):
        rows = mutate(
            build_valid_tables_rows(),
            "change_history",
            0,
            "table_name",
            "visa_requirements.csv",
        )
        errors = validate_all(rows)
        assert any("table_name" in e and ".csv" in e for e in errors)

    def test_source_table_value_with_csv_suffix_is_rejected(self):
        rows = mutate(
            build_valid_tables_rows(),
            "source_record_mappings",
            0,
            "source_table",
            "visa_requirements.csv",
        )
        errors = validate_all(rows)
        assert any("source_table" in e and ".csv" in e for e in errors)


class TestValidateDirectory:
    def test_missing_file_is_reported(self, tmp_path):
        errors = validate_directory(tmp_path)
        # 13개 파일이 전부 없으므로 최소 13건의 "파일이 없음" 에러가 나야 한다.
        missing_errors = [e for e in errors if "파일이 없음" in e]
        assert len(missing_errors) == 13

    def test_header_order_mismatch_is_reported(self, tmp_path):
        import csv

        from scripts.schema_v2 import generate_empty_csvs

        generate_empty_csvs(tmp_path)
        # visa_requirements.csv의 헤더 순서를 임의로 섞는다.
        path = tmp_path / "visa_requirements.csv"
        table = SCHEMA_V2["visa_requirements"]
        shuffled = list(reversed(table.header))
        with path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(shuffled)

        errors = validate_directory(tmp_path)
        assert any("visa_requirements.csv" in e and "헤더" in e for e in errors)

    def test_valid_directory_passes(self, tmp_path):
        import csv

        for name in TABLE_ORDER:
            table = SCHEMA_V2[name]
            path = tmp_path / table.filename
            with path.open("w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=table.header)
                writer.writeheader()

        tables_rows = build_valid_tables_rows()
        for name in TABLE_ORDER:
            table = SCHEMA_V2[name]
            path = tmp_path / table.filename
            with path.open("a", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=table.header)
                writer.writerows(tables_rows[name])

        errors = validate_directory(tmp_path)
        assert errors == []


# --------------------------------------------------------------------------
# 베이스라인 비교 (finding 5) — CI가 알려진 18건은 통과시키되 회귀(새 에러/조용한 변경)는
# 잡아내도록 하는 --baseline 옵션.
# --------------------------------------------------------------------------

REAL_BASELINE_PATH = REAL_COMMON_V2_DIR / "known_validation_gaps.txt"


class TestBaseline:
    def test_read_baseline_ignores_blank_and_comment_lines(self, tmp_path):
        path = tmp_path / "baseline.txt"
        path.write_text(
            "# 주석 줄\n\nfoo.csv:2 - 에러 A\n  \nfoo.csv:3 - 에러 B\n",
            encoding="utf-8",
        )
        assert _read_baseline(path) == ["foo.csv:2 - 에러 A", "foo.csv:3 - 에러 B"]

    def test_read_baseline_missing_file_returns_empty_list(self, tmp_path):
        assert _read_baseline(tmp_path / "does-not-exist.txt") == []

    def test_matching_baseline_passes(self, tmp_path):
        errors = ["a.csv:2 - x", "b.csv:3 - y"]
        baseline_path = tmp_path / "baseline.txt"
        baseline_path.write_text("\n".join(errors) + "\n", encoding="utf-8")
        exit_code = _check_against_baseline(errors, baseline_path)
        assert exit_code == 0

    def test_new_error_not_in_baseline_fails(self, tmp_path):
        baseline_path = tmp_path / "baseline.txt"
        baseline_path.write_text("a.csv:2 - x\n", encoding="utf-8")
        errors = ["a.csv:2 - x", "a.csv:5 - 새로운 에러"]
        exit_code = _check_against_baseline(errors, baseline_path)
        assert exit_code == 1

    def test_baseline_error_that_silently_disappeared_fails(self, tmp_path):
        # 베이스라인에 있던 에러가 실제 결과에는 없음 — 의도한 수정이면 baseline 파일도
        # 같이 갱신해야 하므로 이 경우도 실패(0이 아님) 처리한다.
        baseline_path = tmp_path / "baseline.txt"
        baseline_path.write_text("a.csv:2 - x\na.csv:3 - y\n", encoding="utf-8")
        errors = ["a.csv:2 - x"]
        exit_code = _check_against_baseline(errors, baseline_path)
        assert exit_code == 1

    def test_real_data_matches_committed_baseline_file(self):
        """extraction/common_v2/known_validation_gaps.txt가 실제 검증 결과와 정확히
        일치하는지 확인한다 — CI가 사용하는 것과 같은 조합."""
        errors = validate_directory(REAL_COMMON_V2_DIR)
        exit_code = _check_against_baseline(errors, REAL_BASELINE_PATH)
        assert exit_code == 0
        assert len(errors) == 8


# --------------------------------------------------------------------------
# 그룹 트리 무결성 (docs/schema-v2.md §3) — ROOT 유일성 / 순환참조 / OR 최소 자식 수
# --------------------------------------------------------------------------


def _load_real_table(table_name: str) -> list[dict[str, str]]:
    """extraction/common_v2/의 실제 CSV 하나를 읽어 행 목록을 반환한다."""
    table = SCHEMA_V2[table_name]
    _, rows = read_csv(REAL_COMMON_V2_DIR / table.filename)
    return rows


def _group_row(
    *,
    group_id: str,
    visa_id: str,
    parent_group_id: str = "",
    group_key: str = "test_group",
    boolean_operator: str = "AND",
    display_order: str = "1",
    source_document_id: str | None = None,
) -> dict[str, str]:
    return {
        "group_id": group_id,
        "visa_id": visa_id,
        "parent_group_id": parent_group_id,
        "group_key": group_key,
        "group_name_kr": "테스트 그룹",
        "boolean_operator": boolean_operator,
        "applicability_note": "",
        "display_order": display_order,
        "valid_from": "2026-01-01",
        "valid_to": "",
        "source_document_id": source_document_id or generate_uuid4(),
        "source_page": "1",
        "last_verified_at": "2026-01-02",
    }


def _criteria_row(
    *,
    criteria_id: str,
    group_id: str,
    evaluation_mode: str = "AUTOMATED",
) -> dict[str, str]:
    return {
        "criteria_id": criteria_id,
        "group_id": group_id,
        "criteria_name": "테스트 조건",
        "field_identifier": "test.field" if evaluation_mode == "AUTOMATED" else "",
        "criteria_type": "EXISTENCE",
        "evaluation_mode": evaluation_mode,
        "operator": "EXISTS" if evaluation_mode == "AUTOMATED" else "",
        "value_numeric": "",
        "value_text": "테스트 조건 원문",
        "unit": "",
        "measurement_window_value": "",
        "measurement_window_unit": "",
        "special_case_note": "",
        "display_order": "1",
        "valid_from": "2026-01-01",
        "valid_to": "",
        "source_document_id": generate_uuid4(),
        "source_page": "1",
        "last_verified_at": "2026-01-02",
    }


class TestCriterionGroupTreeIntegrityRealData:
    """extraction/common_v2/의 실제 F-4-R·F-2-R·E-7-4R 그룹 트리에 대한 긍정 검증."""

    def test_real_data_has_no_root_uniqueness_or_cycle_or_or_group_violations(self):
        tables_rows = {
            VISA_CRITERION_GROUPS: _load_real_table(VISA_CRITERION_GROUPS),
            VISA_REQUIREMENT_CRITERIA: _load_real_table(VISA_REQUIREMENT_CRITERIA),
        }
        errors = _check_criterion_group_tree_integrity(tables_rows)
        assert errors == []

    def test_real_data_has_exactly_one_root_per_visa(self):
        rows = _load_real_table(VISA_CRITERION_GROUPS)
        roots_by_visa: dict[str, list[str]] = {}
        for row in rows:
            if row["parent_group_id"] == "":
                roots_by_visa.setdefault(row["visa_id"], []).append(row["group_id"])
        # F-4-R, F-2-R, E-7-4R(task-11) 세 비자유형에 그룹 트리가 있고 각각 ROOT가 정확히 1개여야 한다.
        assert len(roots_by_visa) == 3
        for visa_id, root_ids in roots_by_visa.items():
            assert len(root_ids) == 1, f"visa_id={visa_id}의 ROOT 그룹이 {root_ids}"

    def test_real_data_or_group_participant_counts(self):
        """brief에 명시된 실제 수치를 고정한다: f2r_language(OR)=3, f4r_eligibility_paths(OR)=2,
        e74r_applicant_status_paths(OR)=2, e74r_income(OR)=2(task-11-brief.md)."""
        groups = {row["group_key"]: row for row in _load_real_table(VISA_CRITERION_GROUPS)}
        criteria = _load_real_table(VISA_REQUIREMENT_CRITERIA)

        def participant_count(group_key: str) -> int:
            group_id = groups[group_key]["group_id"]
            direct = sum(
                1
                for c in criteria
                if c["group_id"] == group_id and c["evaluation_mode"] != "INFORMATIONAL"
            )
            children = sum(1 for g in groups.values() if g["parent_group_id"] == group_id)
            return direct + children

        assert groups["f2r_language"]["boolean_operator"] == "OR"
        assert participant_count("f2r_language") == 3

        assert groups["f4r_eligibility_paths"]["boolean_operator"] == "OR"
        assert participant_count("f4r_eligibility_paths") == 3

        assert groups["e74r_applicant_status_paths"]["boolean_operator"] == "OR"
        assert participant_count("e74r_applicant_status_paths") == 2

        assert groups["e74r_income"]["boolean_operator"] == "OR"
        assert participant_count("e74r_income") == 2


class TestCriterionGroupTreeIntegrityRejection:
    """ROOT 유일성 / 자기참조 / 순환참조 / OR 최소 자식 수를 합성 fixture로 거부하는지 확인."""

    def test_two_roots_for_same_visa_is_rejected(self):
        visa_id = generate_uuid4()
        rows = [
            _group_row(group_id=generate_uuid4(), visa_id=visa_id, group_key="root_a"),
            _group_row(group_id=generate_uuid4(), visa_id=visa_id, group_key="root_b"),
        ]
        errors = _check_criterion_group_tree_integrity({VISA_CRITERION_GROUPS: rows})
        assert any("ROOT" in e and visa_id in e for e in errors)

    def test_self_reference_is_rejected(self):
        gid = generate_uuid4()
        visa_id = generate_uuid4()
        rows = [_group_row(group_id=gid, visa_id=visa_id, parent_group_id=gid)]
        errors = _check_criterion_group_tree_integrity({VISA_CRITERION_GROUPS: rows})
        assert any("자기참조" in e for e in errors)

    def test_two_node_cycle_is_rejected(self):
        visa_id = generate_uuid4()
        gid_a, gid_b = generate_uuid4(), generate_uuid4()
        rows = [
            _group_row(group_id=gid_a, visa_id=visa_id, parent_group_id=gid_b, group_key="a"),
            _group_row(group_id=gid_b, visa_id=visa_id, parent_group_id=gid_a, group_key="b"),
        ]
        errors = _check_criterion_group_tree_integrity({VISA_CRITERION_GROUPS: rows})
        assert any("순환참조" in e for e in errors)

    def test_child_visa_id_mismatch_with_parent_is_rejected(self):
        parent_visa_id = generate_uuid4()
        child_visa_id = generate_uuid4()
        parent_id = generate_uuid4()
        rows = [
            _group_row(group_id=parent_id, visa_id=parent_visa_id, group_key="parent"),
            _group_row(
                group_id=generate_uuid4(),
                visa_id=child_visa_id,
                parent_group_id=parent_id,
                group_key="child",
            ),
        ]
        errors = _check_criterion_group_tree_integrity({VISA_CRITERION_GROUPS: rows})
        assert any("visa_id" in e and "다름" in e for e in errors)

    def test_or_group_with_fewer_than_two_participants_is_rejected(self):
        visa_id = generate_uuid4()
        root_id = generate_uuid4()
        or_group_id = generate_uuid4()
        rows = [
            _group_row(group_id=root_id, visa_id=visa_id, group_key="root"),
            _group_row(
                group_id=or_group_id,
                visa_id=visa_id,
                parent_group_id=root_id,
                group_key="lonely_or",
                boolean_operator="OR",
            ),
        ]
        criteria_rows = [_criteria_row(criteria_id=generate_uuid4(), group_id=or_group_id)]
        errors = _check_criterion_group_tree_integrity(
            {VISA_CRITERION_GROUPS: rows, VISA_REQUIREMENT_CRITERIA: criteria_rows}
        )
        assert any("OR 그룹" in e and "2개 이상" in e for e in errors)

    def test_or_group_with_two_participants_passes(self):
        visa_id = generate_uuid4()
        root_id = generate_uuid4()
        or_group_id = generate_uuid4()
        rows = [
            _group_row(group_id=root_id, visa_id=visa_id, group_key="root"),
            _group_row(
                group_id=or_group_id,
                visa_id=visa_id,
                parent_group_id=root_id,
                group_key="valid_or",
                boolean_operator="OR",
            ),
        ]
        criteria_rows = [
            _criteria_row(criteria_id=generate_uuid4(), group_id=or_group_id),
            _criteria_row(criteria_id=generate_uuid4(), group_id=or_group_id),
        ]
        errors = _check_criterion_group_tree_integrity(
            {VISA_CRITERION_GROUPS: rows, VISA_REQUIREMENT_CRITERIA: criteria_rows}
        )
        assert errors == []

    def test_informational_criteria_do_not_count_as_or_group_participants(self):
        """evaluation_mode=INFORMATIONAL은 계산에서 제외되므로 OR 참여 카운트에도 안 들어가야 한다."""
        visa_id = generate_uuid4()
        root_id = generate_uuid4()
        or_group_id = generate_uuid4()
        rows = [
            _group_row(group_id=root_id, visa_id=visa_id, group_key="root"),
            _group_row(
                group_id=or_group_id,
                visa_id=visa_id,
                parent_group_id=root_id,
                group_key="or_with_informational",
                boolean_operator="OR",
            ),
        ]
        criteria_rows = [
            _criteria_row(criteria_id=generate_uuid4(), group_id=or_group_id),
            _criteria_row(
                criteria_id=generate_uuid4(),
                group_id=or_group_id,
                evaluation_mode="INFORMATIONAL",
            ),
        ]
        errors = _check_criterion_group_tree_integrity(
            {VISA_CRITERION_GROUPS: rows, VISA_REQUIREMENT_CRITERIA: criteria_rows}
        )
        assert any("OR 그룹" in e and "2개 이상" in e for e in errors)


# --------------------------------------------------------------------------
# 첨부관계 무결성 (docs/schema-v2.md §9) — 자기참조 / 순환 첨부관계
# --------------------------------------------------------------------------


def _relation_row(
    *, relation_id: str, parent_document_id: str, attachment_document_id: str
) -> dict[str, str]:
    return {
        "relation_id": relation_id,
        "parent_document_id": parent_document_id,
        "attachment_document_id": attachment_document_id,
        "requirement_status": "REQUIRED",
        "alternative_group": "",
        "condition_note": "",
        "display_order": "1",
        "valid_from": "2026-01-01",
        "valid_to": "",
        "source_document_id": generate_uuid4(),
        "source_page": "1",
    }


class TestDocumentAttachmentRelationIntegrityRealData:
    """extraction/common_v2/document_attachment_relations.csv(실제 2행)에 대한 긍정 검증."""

    def test_real_data_has_no_self_reference_or_cycle(self):
        rows = _load_real_table(DOCUMENT_ATTACHMENT_RELATIONS)
        assert len(rows) == 2, "브리프가 전제한 실제 행 수(2)와 다름 — 수치를 다시 확인할 것"
        errors = _check_document_attachment_relation_integrity(
            {DOCUMENT_ATTACHMENT_RELATIONS: rows}
        )
        assert errors == []


class TestDocumentAttachmentRelationIntegrityRejection:
    """자기참조 / 순환 첨부관계를 합성 fixture로 거부하는지 확인."""

    def test_self_reference_is_rejected(self):
        doc_id = generate_uuid4()
        rows = [
            _relation_row(
                relation_id=generate_uuid4(),
                parent_document_id=doc_id,
                attachment_document_id=doc_id,
            )
        ]
        errors = _check_document_attachment_relation_integrity(
            {DOCUMENT_ATTACHMENT_RELATIONS: rows}
        )
        assert any("자기참조" in e for e in errors)

    def test_two_node_cycle_is_rejected(self):
        doc_a, doc_b = generate_uuid4(), generate_uuid4()
        rows = [
            _relation_row(
                relation_id=generate_uuid4(),
                parent_document_id=doc_a,
                attachment_document_id=doc_b,
            ),
            _relation_row(
                relation_id=generate_uuid4(),
                parent_document_id=doc_b,
                attachment_document_id=doc_a,
            ),
        ]
        errors = _check_document_attachment_relation_integrity(
            {DOCUMENT_ATTACHMENT_RELATIONS: rows}
        )
        assert any("순환" in e for e in errors)

    def test_acyclic_chain_of_three_passes(self):
        doc_a, doc_b, doc_c = generate_uuid4(), generate_uuid4(), generate_uuid4()
        rows = [
            _relation_row(
                relation_id=generate_uuid4(),
                parent_document_id=doc_a,
                attachment_document_id=doc_b,
            ),
            _relation_row(
                relation_id=generate_uuid4(),
                parent_document_id=doc_b,
                attachment_document_id=doc_c,
            ),
        ]
        errors = _check_document_attachment_relation_integrity(
            {DOCUMENT_ATTACHMENT_RELATIONS: rows}
        )
        assert errors == []


# --------------------------------------------------------------------------
# source_record_mappings.target_table — 실제 v2 테이블명(또는 NONE sentinel)만 허용
# (finding 2: 이전에는 검사 자체가 없어 "scoring_items"/"visa_quota_status" 같은 잘못된
# 값이 조용히 통과했다)
# --------------------------------------------------------------------------


class TestTargetTableIsRealTableName:
    def test_real_data_target_table_values_are_all_valid(self):
        """이번 태스크에서 target_table 오류 102건(finding 2)을 고친 뒤
        source_record_mappings.csv 전체가 새 검사를 통과하는지 확인한다."""
        table = SCHEMA_V2[SOURCE_RECORD_MAPPINGS]
        rows = _load_real_table(SOURCE_RECORD_MAPPINGS)
        errors: list[str] = []
        for i, row in enumerate(rows, start=2):
            errors.extend(_check_target_table_is_real_table_name(table, row, i))
        assert errors == []

    def test_none_sentinel_is_allowed(self):
        rows = mutate(
            build_valid_tables_rows(), "source_record_mappings", 0, "target_table", "NONE"
        )
        errors = validate_all(rows)
        assert errors == []

    def test_empty_target_table_is_allowed(self):
        # target_table 자체는 컬럼 정의상 필수라 별도의 "필수 필드 비어 있음" 에러가
        # 나지만, 이 새 검사(target_table enum 여부)만 놓고 보면 빈 값은 통과해야 한다.
        table = SCHEMA_V2[SOURCE_RECORD_MAPPINGS]
        errors = _check_target_table_is_real_table_name(table, {"target_table": ""}, 2)
        assert errors == []

    def test_legacy_scoring_items_shorthand_is_rejected(self):
        rows = mutate(
            build_valid_tables_rows(), "source_record_mappings", 0, "target_table", "scoring_items"
        )
        errors = validate_all(rows)
        assert any("target_table" in e and "scoring_items" in e for e in errors)

    def test_obsolete_v1_quota_status_name_is_rejected(self):
        rows = mutate(
            build_valid_tables_rows(),
            "source_record_mappings",
            0,
            "target_table",
            "visa_quota_status",
        )
        errors = validate_all(rows)
        assert any("target_table" in e and "visa_quota_status" in e for e in errors)

    def test_real_v2_table_name_is_accepted(self):
        rows = mutate(
            build_valid_tables_rows(),
            "source_record_mappings",
            0,
            "target_table",
            "visa_scoring_items",
        )
        errors = validate_all(rows)
        assert errors == []


# --------------------------------------------------------------------------
# 쿼터 산술 검증 (finding 4, plan "검증기 세부 계약 > 쿼터" 절) —
# UNLIMITED policy에 snapshot 없음 / consumed·remaining 등식 / 음수 금지.
# nullable 숫자(recommended_count, quota_exempt_count)는 0으로 치환하지 않고,
# 관련 값이 전부 존재할 때만 등식을 적용한다.
# --------------------------------------------------------------------------


def _quota_policy_row(
    *, quota_policy_id: str, visa_id: str, quota_type: str = "LIMITED"
) -> dict[str, str]:
    return {
        "quota_policy_id": quota_policy_id,
        "visa_id": visa_id,
        "quota_type": quota_type,
        "quota_unit": "PERSON",
        "valid_from": "2026-01-01",
        "valid_to": "",
        "source_document_id": generate_uuid4(),
        "source_page": "1",
    }


def _quota_snapshot_row(
    *,
    quota_snapshot_id: str,
    quota_policy_id: str,
    allocated_quota: str = "100",
    recommended_count: str = "",
    quota_exempt_count: str = "",
    consumed_quota: str = "40",
    remaining_quota: str = "60",
) -> dict[str, str]:
    return {
        "quota_snapshot_id": quota_snapshot_id,
        "quota_policy_id": quota_policy_id,
        "notice_round": "12",
        "as_of_date": "2026-01-15",
        "scope_type": "PROVINCE",
        "scope_name": "충청북도",
        "parent_scope_name": "",
        "allocated_quota": allocated_quota,
        "recommended_count": recommended_count,
        "quota_exempt_count": quota_exempt_count,
        "consumed_quota": consumed_quota,
        "remaining_quota": remaining_quota,
        "consumption_exception": "",
        "valid_from": "2026-01-01",
        "valid_to": "",
        "source_document_id": generate_uuid4(),
        "source_page": "1",
        "recorded_at": "2026-01-15T00:00:00",
    }


class TestQuotaArithmeticRealData:
    """실제 E-7-4R 8차 쿼터 스냅샷(542/246/10/236/306)이 새 산술 검증을 통과하는지 확인."""

    def test_real_quota_data_has_no_arithmetic_violations(self):
        tables_rows = {
            VISA_QUOTA_POLICIES: _load_real_table(VISA_QUOTA_POLICIES),
            VISA_QUOTA_SNAPSHOTS: _load_real_table(VISA_QUOTA_SNAPSHOTS),
        }
        errors = _check_quota_arithmetic(tables_rows)
        assert errors == []

    def test_real_e7_4r_snapshot_values_are_542_246_10_236_306(self):
        snapshots = _load_real_table(VISA_QUOTA_SNAPSHOTS)
        assert len(snapshots) == 1
        row = snapshots[0]
        assert row["allocated_quota"] == "542"
        assert row["recommended_count"] == "246"
        assert row["quota_exempt_count"] == "10"
        assert row["consumed_quota"] == "236"
        assert row["remaining_quota"] == "306"


class TestQuotaArithmeticRejection:
    def test_unlimited_policy_with_snapshot_is_rejected(self):
        visa_id = generate_uuid4()
        policy_id = generate_uuid4()
        policies = [
            _quota_policy_row(quota_policy_id=policy_id, visa_id=visa_id, quota_type="UNLIMITED")
        ]
        snapshots = [
            _quota_snapshot_row(quota_snapshot_id=generate_uuid4(), quota_policy_id=policy_id)
        ]
        errors = _check_quota_arithmetic(
            {VISA_QUOTA_POLICIES: policies, VISA_QUOTA_SNAPSHOTS: snapshots}
        )
        assert any("UNLIMITED" in e for e in errors)

    def test_unlimited_policy_without_snapshot_passes(self):
        visa_id = generate_uuid4()
        policy_id = generate_uuid4()
        policies = [
            _quota_policy_row(quota_policy_id=policy_id, visa_id=visa_id, quota_type="UNLIMITED")
        ]
        errors = _check_quota_arithmetic({VISA_QUOTA_POLICIES: policies, VISA_QUOTA_SNAPSHOTS: []})
        assert errors == []

    def test_wrong_consumed_quota_is_rejected(self):
        policy_id = generate_uuid4()
        snapshots = [
            _quota_snapshot_row(
                quota_snapshot_id=generate_uuid4(),
                quota_policy_id=policy_id,
                allocated_quota="542",
                recommended_count="246",
                quota_exempt_count="10",
                consumed_quota="999",  # 246 - 10 = 236이어야 하는데 틀림
                remaining_quota="306",
            )
        ]
        errors = _check_quota_arithmetic({VISA_QUOTA_POLICIES: [], VISA_QUOTA_SNAPSHOTS: snapshots})
        assert any("consumed_quota" in e for e in errors)

    def test_correct_consumed_quota_passes(self):
        policy_id = generate_uuid4()
        snapshots = [
            _quota_snapshot_row(
                quota_snapshot_id=generate_uuid4(),
                quota_policy_id=policy_id,
                allocated_quota="542",
                recommended_count="246",
                quota_exempt_count="10",
                consumed_quota="236",
                remaining_quota="306",
            )
        ]
        errors = _check_quota_arithmetic({VISA_QUOTA_POLICIES: [], VISA_QUOTA_SNAPSHOTS: snapshots})
        assert errors == []

    def test_wrong_remaining_quota_is_rejected(self):
        policy_id = generate_uuid4()
        snapshots = [
            _quota_snapshot_row(
                quota_snapshot_id=generate_uuid4(),
                quota_policy_id=policy_id,
                allocated_quota="100",
                consumed_quota="40",
                remaining_quota="1",  # 100 - 40 = 60이어야 하는데 틀림
            )
        ]
        errors = _check_quota_arithmetic({VISA_QUOTA_POLICIES: [], VISA_QUOTA_SNAPSHOTS: snapshots})
        assert any("remaining_quota" in e for e in errors)

    def test_nullable_recommended_and_exempt_are_not_coerced_to_zero(self):
        # recommended_count/quota_exempt_count가 비어 있으면 consumed_quota 등식 자체를
        # 적용하지 않아야 한다(0으로 치환해서 억지로 검산하지 않음).
        policy_id = generate_uuid4()
        snapshots = [
            _quota_snapshot_row(
                quota_snapshot_id=generate_uuid4(),
                quota_policy_id=policy_id,
                allocated_quota="75",
                recommended_count="",
                quota_exempt_count="",
                consumed_quota="42",
                remaining_quota="33",
            )
        ]
        errors = _check_quota_arithmetic({VISA_QUOTA_POLICIES: [], VISA_QUOTA_SNAPSHOTS: snapshots})
        assert errors == []

    def test_negative_consumed_quota_is_rejected(self):
        policy_id = generate_uuid4()
        snapshots = [
            _quota_snapshot_row(
                quota_snapshot_id=generate_uuid4(),
                quota_policy_id=policy_id,
                allocated_quota="100",
                consumed_quota="-5",
                remaining_quota="105",
            )
        ]
        errors = _check_quota_arithmetic({VISA_QUOTA_POLICIES: [], VISA_QUOTA_SNAPSHOTS: snapshots})
        assert any("consumed_quota" in e and "음수" in e for e in errors)

    def test_negative_allocated_quota_is_rejected(self):
        policy_id = generate_uuid4()
        snapshots = [
            _quota_snapshot_row(
                quota_snapshot_id=generate_uuid4(),
                quota_policy_id=policy_id,
                allocated_quota="-1",
                consumed_quota="0",
                remaining_quota="-1",
            )
        ]
        errors = _check_quota_arithmetic({VISA_QUOTA_POLICIES: [], VISA_QUOTA_SNAPSHOTS: snapshots})
        assert any("allocated_quota" in e and "음수" in e for e in errors)
