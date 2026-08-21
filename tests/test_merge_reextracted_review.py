from scripts.merge_reextracted_review import merge_rows


def make_row(record_id, raw_text, **extra):
    return {
        "record_id": record_id,
        "raw_text": raw_text,
        "status": extra.get("status", "present"),
        "review_decision": extra.get("review_decision", "approved"),
        "target_table": extra.get("target_table", "visa_requirement_criteria"),
        "review_note": extra.get("review_note", "검수 메모"),
        "reviewer": extra.get("reviewer", "이정연"),
        "reviewed_at": extra.get("reviewed_at", "2026-08-19"),
    }


def test_updates_text_without_overwriting_review_fields():
    merged, skipped = merge_rows(
        [make_row("REQ-001", "old")],
        [make_row("REQ-001", "new", status="not_checked")],
        [make_row("REQ-001", "old")],
    )
    assert merged[0]["raw_text"] == "new"
    assert merged[0]["status"] == "present"
    assert merged[0]["review_decision"] == "approved"
    assert skipped == []


def test_preserves_manually_changed_text():
    merged, skipped = merge_rows(
        [make_row("REQ-001", "manual merge")],
        [make_row("REQ-001", "new")],
        [make_row("REQ-001", "old")],
    )
    assert merged[0]["raw_text"] == "manual merge"
    assert skipped == ["REQ-001"]


def test_appends_new_draft_row_with_empty_review_fields():
    merged, _ = merge_rows(
        [make_row("REQ-001", "old")],
        [make_row("REQ-001", "old"), make_row("REQ-002", "new")],
        [make_row("REQ-001", "old")],
        append_new=True,
    )
    assert [row["record_id"] for row in merged] == ["REQ-001", "REQ-002"]
    assert merged[1]["review_decision"] == ""
    assert merged[1]["reviewer"] == ""
