from scripts.normalize_review_requirements import (
    SPLIT_SPECS,
    SplitSpec,
    apply_specs,
    child,
    find_page_range_rows,
    normalize_source_sections,
    normalize_fragment_merges,
    normalize_target_tables,
)


FIELDNAMES = [
    "record_id",
    "raw_text",
    "condition_group",
    "status",
    "source_document",
    "source_page",
    "source_section",
    "review_decision",
    "target_table",
    "review_note",
    "reviewer",
    "reviewed_at",
]


def row(
    record_id: str,
    decision: str = "approved",
    target: str = "visa_requirement_criteria",
) -> dict[str, str]:
    return {
        "record_id": record_id,
        "raw_text": "원문 전체",
        "condition_group": "G1",
        "status": "present",
        "source_document": "notice.hwpx_section0",
        "source_page": "5",
        "source_section": "자격 요건",
        "review_decision": decision,
        "target_table": target,
        "review_note": "기존 메모",
        "reviewer": "이정연",
        "reviewed_at": "2026-08-19",
    }


def test_split_adds_children_and_excludes_parent():
    fields, rows, added, manually_changed = apply_specs(FIELDNAMES, [row("REQ-095")])

    assert "parent_record_id" in fields
    assert manually_changed == []
    assert added == ["REQ-095-01", "REQ-095-02", "REQ-095-03", "REQ-095-04", "REQ-095-05"]
    parent = rows[0]
    assert parent["review_decision"] == "excluded"
    assert parent["target_table"] == "none"
    assert "REQ-095-01" in parent["review_note"]

    children = rows[1:]
    assert all(child["parent_record_id"] == "REQ-095" for child in children)
    assert all(child["review_decision"] == "approved" for child in children)
    assert all(child["target_table"] == "visa_requirement_criteria" for child in children)
    assert all(child["source_page"] == "7" for child in children)


def test_split_preserves_original_metadata_and_mapping():
    fields, rows, added, manually_changed = apply_specs(
        FIELDNAMES,
        [row("REQ-036", decision="reclassified", target="scoring_items")],
        specs=(next(spec for spec in SPLIT_SPECS if spec.parent_record_id == "REQ-036"),),
    )

    assert added == ["REQ-036-01", "REQ-036-02"]
    assert rows[1]["review_decision"] == "reclassified"
    assert rows[1]["target_table"] == "scoring_items"
    assert rows[1]["reviewer"] == "이정연"
    assert "한국어능력" in rows[1]["raw_text"]
    assert "나이" in rows[2]["raw_text"]


def test_split_is_idempotent():
    fields, first, added, manually_changed = apply_specs(
        FIELDNAMES,
        [row("REQ-018", decision="reclassified", target="visa_process_stages")],
    )
    assert added
    assert manually_changed == []

    fields, second, added_again, manually_changed_again = apply_specs(fields, first)
    assert added_again == []
    assert manually_changed_again == []
    assert len(second) == len(first)


def test_split_preserves_manually_edited_child_fields_on_rerun():
    fields, first, added, manually_changed = apply_specs(FIELDNAMES, [row("REQ-095")])
    assert added
    assert manually_changed == []

    # 검수자가 첫 번째 자식 행의 review_decision과 target_table을 수동으로 수정한 상황을 재현
    first[1]["review_decision"] = "needs_review"
    first[1]["target_table"] = "visa_process_stages"

    fields, second, added_again, manually_changed_again = apply_specs(fields, first)

    assert added_again == []
    assert second[1]["record_id"] == "REQ-095-01"
    assert second[1]["review_decision"] == "needs_review"
    assert second[1]["target_table"] == "visa_process_stages"
    assert manually_changed_again == [
        "REQ-095-01.review_decision",
        "REQ-095-01.target_table",
    ]


def test_split_assigns_page_per_child_instead_of_copying_parent_range():
    spec = SplitSpec(
        "REQ-001",
        (child("첫 페이지 원문", "5"), child("다음 페이지 원문", "6")),
        "페이지 경계 테스트",
    )
    fields, rows, added, manually_changed = apply_specs(FIELDNAMES, [row("REQ-001")], specs=(spec,))

    assert added == ["REQ-001-01", "REQ-001-02"]
    assert rows[1]["source_page"] == "5"
    assert rows[2]["source_page"] == "6"


def test_page_ranges_are_reported_for_manual_review():
    rows = [row("REQ-001"), {**row("REQ-002"), "source_page": "5-6"}]

    assert find_page_range_rows(rows, {"REQ-001"}) == ["REQ-002"]


def test_source_section_uses_explicit_record_id_rules_only():
    fields, rows, changes = normalize_source_sections(
        FIELDNAMES,
        [row("REQ-049"), row("REQ-999")],
    )

    assert fields == FIELDNAMES
    assert rows[0]["source_section"].endswith("> 기본 항목 > 가. 소득")
    assert rows[1]["source_section"] == "자격 요건"
    assert changes == [
        (
            "REQ-049",
            "자격 요건",
            "자격 요건 > 점수제 심사 > 지역특화 숙련기능인력 점수표 > 기본 항목 > 가. 소득",
        )
    ]


def test_source_section_normalization_preserves_other_review_fields():
    original = row("REQ-112", decision="needs_review", target="none")
    original.update({"raw_text": "원문", "source_page": "9", "review_note": "메모"})

    fields, rows, changes = normalize_source_sections(FIELDNAMES, [original])

    assert changes
    assert rows[0]["raw_text"] == "원문"
    assert rows[0]["source_page"] == "9"
    assert rows[0]["review_note"] == "메모"
    assert rows[0]["review_decision"] == "needs_review"
    assert rows[0]["target_table"] == "none"


def test_source_section_normalization_is_idempotent():
    fields, first, changes = normalize_source_sections(FIELDNAMES, [row("REQ-049")])
    assert changes

    fields, second, changes_again = normalize_source_sections(fields, first)
    assert changes_again == []
    assert second == first


def test_fragment_merge_reconstructs_one_source_line():
    rows = [
        {**row("REQ-030", decision="excluded", target="none"), "raw_text": "*"},
        {**row("REQ-031"), "raw_text": "①,"},
        {**row("REQ-032"), "raw_text": "③,"},
        {**row("REQ-033"), "raw_text": "④는 최근 10년 이내 사항만 해당"},
    ]

    fields, merged, applied, skipped = normalize_fragment_merges(FIELDNAMES, rows)

    assert applied == ["REQ-030"]
    assert skipped == []
    assert merged[0]["raw_text"] == "* ①, ③, ④는 최근 10년 이내 사항만 해당"
    assert all(item["review_decision"] == "excluded" for item in merged[1:])
    assert all(item["target_table"] == "none" for item in merged[1:])
    assert "REQ-030" in merged[0]["review_note"]


def test_fragment_merge_skips_unexpected_fragments():
    rows = [
        {**row("REQ-030", decision="excluded", target="none"), "raw_text": "*"},
        {**row("REQ-031"), "raw_text": "예상하지 않은 조각"},
        {**row("REQ-032"), "raw_text": "③,"},
        {**row("REQ-033"), "raw_text": "④는 최근 10년 이내 사항만 해당"},
    ]

    fields, merged, applied, skipped = normalize_fragment_merges(FIELDNAMES, rows)

    assert applied == []
    assert skipped == ["REQ-030"]
    assert merged[0]["raw_text"] == "*"
    assert merged[1]["review_decision"] == "approved"


def test_fragment_merge_is_idempotent():
    rows = [
        {**row("REQ-030", decision="excluded", target="none"), "raw_text": "*"},
        {**row("REQ-031"), "raw_text": "①,"},
        {**row("REQ-032"), "raw_text": "③,"},
        {**row("REQ-033"), "raw_text": "④는 최근 10년 이내 사항만 해당"},
    ]

    fields, first, applied, skipped = normalize_fragment_merges(FIELDNAMES, rows)
    fields, second, applied_again, skipped_again = normalize_fragment_merges(fields, first)

    assert applied == ["REQ-030"]
    assert skipped == []
    assert applied_again == []
    assert skipped_again == []
    assert second == first


def test_target_table_rules_reclassify_confirmed_rows_only():
    rows = [
        row("REQ-048-01", decision="excluded", target="none"),
        row("REQ-116", decision="needs_review", target="none"),
        row("REQ-120", decision="needs_review", target="none"),
    ]

    fields, normalized, changes = normalize_target_tables(FIELDNAMES, rows)

    assert normalized[0]["review_decision"] == "reclassified"
    assert normalized[0]["target_table"] == "scoring_items"
    assert normalized[1]["review_decision"] == "reclassified"
    assert normalized[1]["target_table"] == "visa_process_stages"
    assert normalized[2]["review_decision"] == "needs_review"
    assert normalized[2]["target_table"] == "none"
    assert [change[0] for change in changes] == ["REQ-048-01", "REQ-116"]
