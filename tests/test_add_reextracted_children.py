import pytest

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
    # REEXTRACTED_CHILD_MAP의 모든 parent_id(REQ-034/035/036)가 review_rows에
    # 실제로 존재해야 add_children이 유효한 입력으로 검증한다.
    review = [row("REQ-034", "parent"), row("REQ-035", "parent"), row("REQ-036", "parent")]
    draft = [row(f"REQ-{number:03d}", f"draft {number}") for number in range(34, 40)]
    first, _ = add_children(review, draft)
    second, added = add_children(first, draft)

    assert len(second) == len(first)
    assert added == []


def test_missing_parent_id_raises_value_error():
    # REQ-034가 review_rows에 없으면(필터링 등으로 누락) 존재하지 않는
    # parent_record_id를 참조하는 자식 행이 생기므로 명시적으로 실패해야 한다.
    review = [row("REQ-035", "복합 부모"), row("REQ-036", "복합 부모")]
    draft = [row(f"REQ-{number:03d}", f"draft {number}") for number in range(34, 40)]

    with pytest.raises(ValueError, match="REQ-034"):
        add_children(review, draft)


def test_missing_source_id_raises_value_error():
    # draft_rows에 매핑된 source_id가 없으면 KeyError가 아니라
    # 원인을 알 수 있는 명시적 에러를 내야 한다.
    review = [row("REQ-034", "복합 부모"), row("REQ-035", "복합 부모"), row("REQ-036", "복합 부모")]
    draft = [row(f"REQ-{number:03d}", f"draft {number}") for number in range(34, 39)]

    with pytest.raises(ValueError, match="REQ-039"):
        add_children(review, draft)
