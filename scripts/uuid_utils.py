"""공통 스키마 ID를 생성·재사용·검증하는 순수 유틸리티.

이 모듈은 CSV를 읽거나 쓰지 않는다. extraction 스크립트가 신규 행을 만든 뒤
행의 ID를 채울 때 호출하고, CSV 저장은 호출한 스크립트가 담당한다.
"""

from __future__ import annotations

import uuid
from collections.abc import Collection, Iterable, Mapping

UUID_ID_COLUMNS = frozenset(
    {
        "visa_id",
        "stage_id",
        "document_requirement_id",
        "group_id",
        "criteria_id",
        "score_model_id",
        "scoring_item_id",
        "relation_id",
        "quota_policy_id",
        "quota_snapshot_id",
        "source_document_id",
        "mapping_id",
        "change_id",
    }
)


class UUIDGenerationError(ValueError):
    """ID를 생성하거나 재사용할 수 없을 때 발생하는 오류."""


def validate_uuid4(value: str, field_name: str) -> None:
    """값이 UUID v4 문자열인지 확인한다."""
    try:
        parsed = uuid.UUID(value)
    except (ValueError, AttributeError) as exc:
        raise UUIDGenerationError(f"{field_name}가 UUID 형식이 아님: {value!r}") from exc
    if parsed.version != 4:
        raise UUIDGenerationError(f"{field_name}가 UUID v4가 아님: {value!r}")


def generate_uuid4(existing_ids: Collection[str] = ()) -> str:
    """기존 ID와 겹치지 않는 UUID v4를 생성한다."""
    used_ids = set(existing_ids)
    while True:
        candidate = str(uuid.uuid4())
        if candidate not in used_ids:
            return candidate


def assign_new_id(
    row: Mapping[str, str],
    id_column: str,
    existing_ids: Collection[str],
) -> dict[str, str]:
    """신규 행의 ID를 채운 복사본을 반환한다.

    이미 ID가 있으면 값을 보존하되 UUID v4 형식만 확인한다. 신규 ID를 생성할
    때는 ``existing_ids``와 중복되지 않도록 한다. 입력 행과 원본 매핑은 수정하지
    않는다.
    """
    if id_column not in UUID_ID_COLUMNS:
        allowed = ", ".join(sorted(UUID_ID_COLUMNS))
        raise UUIDGenerationError(f"지원하지 않는 ID 컬럼: {id_column!r} ({allowed})")

    result = dict(row)
    current_id = result.get(id_column, "")
    if current_id:
        validate_uuid4(current_id, id_column)
        return result

    result[id_column] = generate_uuid4(existing_ids)
    return result


def ensure_new_id_is_unique(value: str, id_column: str, existing_ids: Collection[str]) -> str:
    """외부에서 지정한 신규 ID가 UUID v4이고 기존 ID와 겹치지 않는지 확인한다."""
    if id_column not in UUID_ID_COLUMNS:
        raise UUIDGenerationError(f"지원하지 않는 ID 컬럼: {id_column!r}")
    validate_uuid4(value, id_column)
    if value in existing_ids:
        raise UUIDGenerationError(f"이미 사용 중인 {id_column}: {value}")
    return value


def get_or_create_visa_id(
    row: Mapping[str, str],
    existing_visa_rows: Iterable[Mapping[str, str]],
    existing_ids: Collection[str] = (),
) -> dict[str, str]:
    """비자 코드·트랙에 해당하는 ``visa_id``를 재사용하거나 새로 발급한다.

    ``existing_visa_rows``에 같은 ``visa_code``가 있으면 그 행의 ID를 재사용한다.
    같은 코드에 다른 ID를 함께 입력하면 오류로 처리한다. 새 비자 코드인 경우에만
    UUID v4를 발급한다.
    """
    visa_code = row.get("visa_code", "")
    if not visa_code:
        raise UUIDGenerationError("visa_code가 비어 있음")

    result = dict(row)
    supplied_id = result.get("visa_id", "")
    for existing_row in existing_visa_rows:
        if existing_row.get("visa_code") != visa_code:
            continue
        existing_id = existing_row.get("visa_id", "")
        validate_uuid4(existing_id, "visa_id")
        if supplied_id and supplied_id != existing_id:
            raise UUIDGenerationError(
                f"{visa_code}에 이미 발급된 visa_id와 입력값이 다름: {existing_id} != {supplied_id}"
            )
        result["visa_id"] = existing_id
        return result

    if supplied_id:
        ensure_new_id_is_unique(supplied_id, "visa_id", existing_ids)
        result["visa_id"] = supplied_id
    else:
        result["visa_id"] = generate_uuid4(existing_ids)
    return result
