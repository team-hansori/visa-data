from scripts.add_reextracted_children import add_children


def row(record_id, raw_text):
    return {
        "record_id": record_id,
        "raw_text": raw_text,
        "status": "present",
        "source_page": "3",
        "review_decision": "approved",
        "target_table": "scoring_items",
        "review_note": "기존 메모",
        "reviewer": "이정연",
        "reviewed_at": "2026-08-19",
        "parent_record_id": "",
    }


def test_adds_explicit_children_and_preserves_parent():
    review = [row("REQ-034", "복합 부모"), row("REQ-035", "복합 부모"), row("REQ-036", "복합 부모")]
    draft = [row(f"REQ-{number:03d}", f"draft {number}") for number in range(34, 40)]

    merged, added = add_children(review, draft)

    assert added == [
        "REQ-034-01",
        "REQ-034-02",
        "REQ-034-03",
        "REQ-035-01",
        "REQ-036-01",
        "REQ-036-02",
    ]
    assert merged[0]["raw_text"] == "복합 부모"
    child = next(item for item in merged if item["record_id"] == "REQ-034-02")
    assert child["raw_text"] == "draft 35"
    assert child["parent_record_id"] == "REQ-034"
    assert child["review_decision"] == "needs_review"
    assert child["target_table"] == "none"


def test_is_idempotent():
    review = [row("REQ-034", "parent")]
    draft = [row(f"REQ-{number:03d}", f"draft {number}") for number in range(34, 40)]
    first, _ = add_children(review, draft)
    second, added = add_children(first, draft)

    assert len(second) == len(first)
    assert added == []
