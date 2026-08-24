"""validate_common_schema_v2.py(공통 스키마 v2 검증기) 회귀 테스트.

실제 v2 이관 데이터가 아직 없으므로(그 작업은 이슈 #44의 4~10단계), 13개 테이블이 서로
정합성 있게 맞물리는 최소 fixture 행 집합을 손으로 구성해 검증기가 통과/거부해야 하는
경우를 확인한다.
"""

from __future__ import annotations

import copy

from scripts.schema_v2 import SCHEMA_V2, TABLE_ORDER
from scripts.uuid_utils import generate_uuid4
from scripts.validate_common_schema_v2 import validate_all, validate_directory

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
