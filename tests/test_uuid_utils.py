"""공통 UUID 유틸리티 회귀 테스트."""

from __future__ import annotations

import uuid

import pytest

from scripts.uuid_utils import (
    UUIDGenerationError,
    assign_new_id,
    ensure_new_id_is_unique,
    generate_uuid4,
    get_or_create_visa_id,
    validate_uuid4,
)


def test_generate_uuid4_returns_unique_uuid4():
    existing = {str(uuid.uuid4())}

    generated = generate_uuid4(existing)

    assert uuid.UUID(generated).version == 4
    assert generated not in existing


def test_assign_new_id_fills_blank_id_without_mutating_input():
    row = {"stage_id": "", "visa_id": "visa-1", "stage_name": "신청 접수"}

    result = assign_new_id(row, "stage_id", set())

    assert row["stage_id"] == ""
    assert uuid.UUID(result["stage_id"]).version == 4
    assert result["visa_id"] == row["visa_id"]


def test_assign_new_id_preserves_existing_id():
    existing_id = str(uuid.uuid4())
    row = {"stage_id": existing_id, "visa_id": "visa-1"}

    result = assign_new_id(row, "stage_id", {existing_id})

    assert result == row


def test_assign_new_id_rejects_unknown_column_and_invalid_existing_id():
    with pytest.raises(UUIDGenerationError, match="지원하지 않는 ID 컬럼"):
        # "criteria_id"는 issue #44 task 10에서 UUID_ID_COLUMNS에 추가돼 더 이상 예시로
        # 쓸 수 없다 — 스키마에 실재하지 않는 컬럼명으로 "미지원" 케이스를 확인한다.
        assign_new_id({}, "not_a_real_id_column", set())

    with pytest.raises(UUIDGenerationError, match="UUID 형식이 아님"):
        assign_new_id({"stage_id": "not-an-id"}, "stage_id", set())


def test_get_or_create_visa_id_reuses_existing_visa_code():
    existing_id = str(uuid.uuid4())
    row = {"visa_code": "F-4-R"}

    result = get_or_create_visa_id(
        row,
        [{"visa_code": "F-4-R", "visa_id": existing_id}],
    )

    assert result["visa_id"] == existing_id
    assert "visa_id" not in row


def test_get_or_create_visa_id_rejects_different_id_for_existing_code():
    with pytest.raises(UUIDGenerationError, match="이미 발급된 visa_id와 입력값이 다름"):
        get_or_create_visa_id(
            {"visa_code": "F-4-R", "visa_id": str(uuid.uuid4())},
            [{"visa_code": "F-4-R", "visa_id": str(uuid.uuid4())}],
        )


def test_get_or_create_visa_id_generates_new_id_for_new_code():
    result = get_or_create_visa_id(
        {"visa_code": "F-2-R"},
        [{"visa_code": "F-4-R", "visa_id": str(uuid.uuid4())}],
    )

    assert uuid.UUID(result["visa_id"]).version == 4


def test_ensure_new_id_is_unique_rejects_duplicate():
    existing_id = str(uuid.uuid4())

    with pytest.raises(UUIDGenerationError, match="이미 사용 중인 stage_id"):
        ensure_new_id_is_unique(existing_id, "stage_id", {existing_id})


def test_validate_uuid4_rejects_non_v4_uuid():
    with pytest.raises(UUIDGenerationError, match="UUID v4가 아님"):
        validate_uuid4("00000000-0000-0000-0000-000000000000", "stage_id")
