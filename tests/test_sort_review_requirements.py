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
