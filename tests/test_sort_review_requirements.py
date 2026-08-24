from scripts.sort_review_requirements import sort_parent_children


def row(record_id, parent=""):
    return {"record_id": record_id, "parent_record_id": parent}


def test_places_children_after_parent_and_preserves_other_order():
    rows = [
        row("REQ-001"),
        row("REQ-034-01", "REQ-034"),
        row("REQ-002"),
        row("REQ-034"),
        row("REQ-034-02", "REQ-034"),
    ]

    sorted_rows = sort_parent_children(rows)

    assert [item["record_id"] for item in sorted_rows] == [
        "REQ-001",
        "REQ-002",
        "REQ-034",
        "REQ-034-01",
        "REQ-034-02",
    ]


def test_is_idempotent():
    rows = [row("REQ-034"), row("REQ-034-01", "REQ-034")]

    assert sort_parent_children(sort_parent_children(rows)) == rows


def test_grandchild_before_grandparent_is_not_dropped():
    # 손자 행(REQ-034-01-01)이 원본에서 조부모(REQ-034)보다 먼저 등장하는 경우를 재현한다.
    rows = [
        row("REQ-034-01-01", "REQ-034-01"),
        row("REQ-034-01", "REQ-034"),
        row("REQ-034"),
    ]

    sorted_rows = sort_parent_children(rows)

    input_ids = {item["record_id"] for item in rows}
    output_ids = {item["record_id"] for item in sorted_rows}
    assert len(sorted_rows) == len(rows)
    assert output_ids == input_ids
    assert [item["record_id"] for item in sorted_rows] == [
        "REQ-034",
        "REQ-034-01",
        "REQ-034-01-01",
    ]


def test_self_referencing_parent_does_not_infinite_loop_or_drop_row():
    rows = [row("REQ-001"), row("REQ-002", "REQ-002")]

    sorted_rows = sort_parent_children(rows)

    assert {item["record_id"] for item in sorted_rows} == {"REQ-001", "REQ-002"}
    assert len(sorted_rows) == len(rows)


def test_missing_parent_reference_is_still_emitted():
    rows = [row("REQ-001", "REQ-999"), row("REQ-002")]

    sorted_rows = sort_parent_children(rows)

    assert {item["record_id"] for item in sorted_rows} == {"REQ-001", "REQ-002"}
    assert len(sorted_rows) == len(rows)
