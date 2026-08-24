"""공통 스키마 v2(13개 테이블)의 컬럼 순서·자료형·nullable·PK·FK·enum 계약을 한 곳에서
정의한다.

이 모듈이 스키마의 단일 진실 공급원(SSOT)이다. `scripts/validate_common_schema_v2.py`와
`scripts/migrate_to_v2.py`는 여기서 import해서 쓰고, 별도로 헤더 목록을 하드코딩하지
않는다 — 문서(`docs/schema-v2.md`)와 실제 CSV 헤더가 따로 놀지 않게 하기 위함이다.

이 모듈은 CSV를 읽지 않는다. `generate_empty_csv`/`generate_empty_csvs`만 헤더 한 줄짜리
빈 CSV를 쓰는 예외다.

## nullable 판단 기준

`docs/schema-v2.md` 원문에 "nullable", "없으면 null", "미확인이면 null", "계속 유효하면
null/NULL" 등으로 **명시적으로** 언급된 컬럼만 `nullable=True`로 표시했다. 명시적 언급이
없는 컬럼은 기본값(필수)으로 처리했다. 이 원칙 외에 사람 판단이 들어간 부분은 다음과 같다
(자세한 근거는 task-3-report.md 참고):

- `valid_from`/`valid_to` 쌍: 문서 전반에 "종료일...계속 유효하면 null"이 반복되므로,
  이 쌍이 등장하는 모든 테이블에 동일하게 valid_from=필수/valid_to=nullable을 적용했다.
- `source_document_id`/`source_page`: 계획 문서 완료 체크리스트("모든 공통 행에 필요한
  출처·페이지·유효기간이 존재한다")에 따라 이 두 컬럼이 있는 모든 테이블에서 필수로 뒀다.
- `*_note`/`notes`/`mapping_note`/`blocking_reason` 계열의 자유 서술 컬럼: 3번 테이블의
  `applicability_note`가 명시적으로 nullable(필수 칸이 빈칸)인 선례를 따라 동일 계열
  컬럼을 모두 nullable로 처리했다.
- `notice_round`: 1번 테이블(source_documents)에서 "차수 없는 문서는 null"로 명시된
  선례를 같은 컬럼명이 재등장하는 다른 테이블에도 일관 적용했다.
- 그 외 값이 항상 채워질지 불확실한 자유 서술 컬럼(예: `signer`, `filled_by`,
  `stage_start_date`)은 문서에 nullable 언급이 없어 필수로 뒀지만, 실제 이관 데이터에서
  항상 채워지지 않을 수 있어 후속 작업에서 재검토가 필요할 수 있다.

## enum으로 강제 검증하는 컬럼

이슈 #44 댓글에서 "확정된 enum"으로 못박은 12개 컬럼만 `ColumnKind.ENUM`으로 강제 검증한다
(`plans/issue-44-common-schema-v2-migration.md`의 "확정된 enum" 표, task-3-brief.md의
"Confirmed enums" 표와 동일). `docs/schema-v2.md`에는 `page_basis`, `program_type`,
`document_category`, `quota_unit`, `change_type`, `applies_when`, `measurement_window_unit`,
`selection_rule`처럼 후보값이 나열된 컬럼이 더 있지만, brief가 "확정된 enum만 그대로
반영하고 새 값을 임의로 추가하지 말라"고 명시했으므로 이 컬럼들은 자유 텍스트
(`ColumnKind.TEXT`)로 둔다.
"""

from __future__ import annotations

import csv
from collections.abc import Iterable
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

# --------------------------------------------------------------------------
# 컬럼 종류
# --------------------------------------------------------------------------


class ColumnKind(str, Enum):
    """검증기가 값 형식을 판단할 때 쓰는 컬럼 종류."""

    UUID = "uuid"
    TEXT = "text"
    ENUM = "enum"
    DATE = "date"  # YYYY-MM-DD
    TIMESTAMP = "timestamp"  # YYYY-MM-DD 또는 YYYY-MM-DDTHH:MM:SS
    NUMERIC = "numeric"
    JSON_ARRAY = "json_array"
    BOOLEAN = "boolean"


@dataclass(frozen=True)
class ForeignKey:
    """FK 컬럼이 참조하는 대상 테이블·컬럼(둘 다 논리 이름, .csv 없음)."""

    table: str
    column: str


@dataclass(frozen=True)
class ColumnSpec:
    """테이블 컬럼 하나의 계약."""

    name: str
    kind: ColumnKind
    nullable: bool = False
    enum_values: frozenset[str] | None = None
    fk: ForeignKey | None = None

    def __post_init__(self) -> None:
        if self.kind == ColumnKind.ENUM and not self.enum_values:
            raise ValueError(f"ENUM 컬럼 '{self.name}'에 enum_values가 비어 있음")
        if self.fk is not None and self.kind != ColumnKind.UUID:
            raise ValueError(f"FK 컬럼 '{self.name}'은 kind=UUID여야 함")


@dataclass(frozen=True)
class TableSpec:
    """테이블 하나의 계약: 논리 이름, 컬럼 순서, PK."""

    name: str  # 논리 테이블명. .csv 확장자를 붙이지 않는다.
    columns: tuple[ColumnSpec, ...]
    pk: str

    def __post_init__(self) -> None:
        if self.name.endswith(".csv"):
            raise ValueError(f"논리 테이블명에 .csv를 붙이면 안 됨: {self.name!r}")
        names = [c.name for c in self.columns]
        if len(names) != len(set(names)):
            duplicates = {n for n in names if names.count(n) > 1}
            raise ValueError(f"{self.name}: 컬럼명이 중복됨: {duplicates}")
        if self.pk not in names:
            raise ValueError(f"{self.name}: PK 컬럼 '{self.pk}'이 columns에 없음")

    @property
    def header(self) -> list[str]:
        """CSV 헤더 순서 그대로의 컬럼명 목록."""
        return [c.name for c in self.columns]

    @property
    def filename(self) -> str:
        """실제 디스크에 쓸 파일명(.csv 포함)."""
        return f"{self.name}.csv"

    def column(self, name: str) -> ColumnSpec:
        for c in self.columns:
            if c.name == name:
                return c
        raise KeyError(f"{self.name}에 컬럼 '{name}'이 없음")


def _uuid(name: str, *, nullable: bool = False, fk: ForeignKey | None = None) -> ColumnSpec:
    return ColumnSpec(name, ColumnKind.UUID, nullable=nullable, fk=fk)


def _text(name: str, *, nullable: bool = False) -> ColumnSpec:
    return ColumnSpec(name, ColumnKind.TEXT, nullable=nullable)


def _enum(name: str, values: frozenset[str], *, nullable: bool = False) -> ColumnSpec:
    return ColumnSpec(name, ColumnKind.ENUM, nullable=nullable, enum_values=values)


def _date(name: str, *, nullable: bool = False) -> ColumnSpec:
    return ColumnSpec(name, ColumnKind.DATE, nullable=nullable)


def _timestamp(name: str, *, nullable: bool = False) -> ColumnSpec:
    return ColumnSpec(name, ColumnKind.TIMESTAMP, nullable=nullable)


def _numeric(name: str, *, nullable: bool = False) -> ColumnSpec:
    return ColumnSpec(name, ColumnKind.NUMERIC, nullable=nullable)


def _json_array(name: str, *, nullable: bool = False) -> ColumnSpec:
    return ColumnSpec(name, ColumnKind.JSON_ARRAY, nullable=nullable)


def _boolean(name: str, *, nullable: bool = False) -> ColumnSpec:
    return ColumnSpec(name, ColumnKind.BOOLEAN, nullable=nullable)


def _fk(table: str, column: str) -> ForeignKey:
    return ForeignKey(table=table, column=column)


# --------------------------------------------------------------------------
# 테이블 논리명 (docs/schema-v2.md "전체 테이블" 표, .csv 없음)
# --------------------------------------------------------------------------

SOURCE_DOCUMENTS = "source_documents"
VISA_REQUIREMENTS = "visa_requirements"
VISA_CRITERION_GROUPS = "visa_criterion_groups"
VISA_REQUIREMENT_CRITERIA = "visa_requirement_criteria"
VISA_SCORING_MODELS = "visa_scoring_models"
VISA_SCORING_ITEMS = "visa_scoring_items"
VISA_PROCESS_STAGES = "visa_process_stages"
DOCUMENT_REQUIREMENTS = "document_requirements"
DOCUMENT_ATTACHMENT_RELATIONS = "document_attachment_relations"
VISA_QUOTA_POLICIES = "visa_quota_policies"
VISA_QUOTA_SNAPSHOTS = "visa_quota_snapshots"
CHANGE_HISTORY = "change_history"
SOURCE_RECORD_MAPPINGS = "source_record_mappings"

# --------------------------------------------------------------------------
# 확정된 enum (이슈 #44 댓글 결정. brief/plan의 "확정된 enum" 표와 동일하게 유지한다.
# 새 값을 추가하려면 이 상수와 docs/schema-v2.md, plans/issue-44-....md를 함께 갱신한다.)
# --------------------------------------------------------------------------

BOOLEAN_OPERATOR_VALUES = frozenset({"AND", "OR"})
CRITERIA_TYPE_VALUES = frozenset({"NUMERIC", "TEXT", "BOOLEAN", "LIST", "EXISTENCE"})
EVALUATION_MODE_VALUES = frozenset({"AUTOMATED", "MANUAL", "INFORMATIONAL"})
OPERATOR_VALUES = frozenset(
    {"EQ", "GT", "GTE", "LT", "LTE", "IN", "NOT_IN", "EXISTS", "NOT_EXISTS", "WITHIN"}
)
MODEL_PURPOSE_VALUES = frozenset({"PASS_THRESHOLD", "QUOTA_RANKING", "BOTH", "UNKNOWN"})
SCORE_GROUP_VALUES = frozenset({"BASE", "BONUS", "PENALTY"})
STACKING_RULE_VALUES = frozenset({"STACK", "ONE_OF", "MAX_SCORE_ONLY", "UNKNOWN"})
REQUIREMENT_STATUS_VALUES = frozenset({"REQUIRED", "OPTIONAL", "CONDITIONAL", "ALTERNATIVE"})
QUOTA_TYPE_VALUES = frozenset({"LIMITED", "UNLIMITED", "UNKNOWN"})
SCOPE_TYPE_VALUES = frozenset(
    {"NATIONAL", "PROVINCE", "MUNICIPALITY", "INSTITUTION", "DEPARTMENT", "OTHER"}
)
DOCUMENT_TYPE_VALUES = frozenset(
    {"ANNOUNCEMENT", "ATTACHMENT", "AMENDMENT", "GUIDELINE", "FORM", "OTHER"}
)
MAPPING_ACTION_VALUES = frozenset({"COPY", "TRANSFORM", "MERGE", "SKIP", "MANUAL_REVIEW"})
MAPPING_STATUS_VALUES = frozenset({"PENDING", "READY", "MAPPED", "BLOCKED"})

# --------------------------------------------------------------------------
# 절대 존재하면 안 되는 테이블·컬럼명 (docs/schema-v2.md "제외되는 것" 절)
# "별도 상태관리 테이블" 자체는 이름이 정해져 있지 않아 이름 목록으로 걸러낼 수 없다 —
# 새 테이블을 추가할 때 상태관리 전용 테이블을 만들지 않는 것은 리뷰로 지켜야 한다.
# --------------------------------------------------------------------------

FORBIDDEN_NAMES = frozenset(
    {
        "visa_round_facts",
        "visa_current_facts",
        "visa_fact_coverage",
        "extraction_status",
        "review_status",
        "consumption_gate",
        "confidence",
    }
)

# --------------------------------------------------------------------------
# 1. source_documents
# --------------------------------------------------------------------------

_SOURCE_DOCUMENTS_TABLE = TableSpec(
    name=SOURCE_DOCUMENTS,
    pk="source_document_id",
    columns=(
        _uuid("source_document_id"),
        _text("source_document_key"),
        _uuid("visa_id", nullable=True, fk=_fk(VISA_REQUIREMENTS, "visa_id")),
        _enum("document_type", DOCUMENT_TYPE_VALUES),
        _text("document_name"),
        _numeric("notice_round", nullable=True),
        # 게시일이 명확히 하나로 특정되지 않는 문서(웹 목록 등)가 있어 nullable.
        _date("published_at", nullable=True),
        _text("source_location"),
        # 원본 PDF는 이 저장소에 올리지 않으므로(data/raw/ 또는 별도 공유 저장소
        # 참조) 대부분의 문서는 해시를 계산할 파일 자체가 없다 — nullable.
        _text("file_hash_sha256", nullable=True),
        _text("page_basis"),
        _date("last_verified_at"),
    ),
)

# --------------------------------------------------------------------------
# 2. visa_requirements
# --------------------------------------------------------------------------

_VISA_REQUIREMENTS_TABLE = TableSpec(
    name=VISA_REQUIREMENTS,
    pk="visa_id",
    columns=(
        _uuid("visa_id"),
        _text("visa_code"),
        _text("visa_name_kr"),
        _text("program_type"),
        _json_array("target_regions_json"),
        _numeric("residency_limit_years", nullable=True),
        _json_array("allowed_industries_json", nullable=True),
        _text("application_method"),
        _text("next_visa_code", nullable=True),
        _date("valid_from"),
        _date("valid_to", nullable=True),
        _uuid("source_document_id", fk=_fk(SOURCE_DOCUMENTS, "source_document_id")),
        _text("source_page"),
        _date("last_verified_at"),
    ),
)

# --------------------------------------------------------------------------
# 3. visa_criterion_groups
# --------------------------------------------------------------------------

_VISA_CRITERION_GROUPS_TABLE = TableSpec(
    name=VISA_CRITERION_GROUPS,
    pk="group_id",
    columns=(
        _uuid("group_id"),
        _uuid("visa_id", fk=_fk(VISA_REQUIREMENTS, "visa_id")),
        # ROOT 그룹만 비워야 한다는 규칙은 스키마의 nullable 여부만으로는 표현할 수 없다 —
        # ROOT 유일성/자식 visa_id 일치/자기참조·순환참조/OR 그룹 최소 자식 수 등 트리
        # 무결성 규칙은 scripts/validate_common_schema_v2.py에 구현되어 있다
        # (plans/issue-44-....md "검증기 세부 계약"의 자격조건 절 참고).
        _uuid(
            "parent_group_id",
            nullable=True,
            fk=_fk(VISA_CRITERION_GROUPS, "group_id"),
        ),
        _text("group_key"),
        _text("group_name_kr"),
        _enum("boolean_operator", BOOLEAN_OPERATOR_VALUES),
        _text("applicability_note", nullable=True),
        _numeric("display_order"),
        _date("valid_from"),
        _date("valid_to", nullable=True),
        _uuid("source_document_id", fk=_fk(SOURCE_DOCUMENTS, "source_document_id")),
        _text("source_page"),
        _timestamp("last_verified_at"),
    ),
)

# --------------------------------------------------------------------------
# 4. visa_requirement_criteria
# --------------------------------------------------------------------------

_VISA_REQUIREMENT_CRITERIA_TABLE = TableSpec(
    name=VISA_REQUIREMENT_CRITERIA,
    pk="criteria_id",
    columns=(
        _uuid("criteria_id"),
        _uuid("group_id", fk=_fk(VISA_CRITERION_GROUPS, "group_id")),
        _text("criteria_name"),
        # AUTOMATED일 때만 필수 — 컬럼 자체는 nullable, 조건부 필수는 검증기에서 별도 확인.
        _text("field_identifier", nullable=True),
        _enum("criteria_type", CRITERIA_TYPE_VALUES),
        _enum("evaluation_mode", EVALUATION_MODE_VALUES),
        # AUTOMATED일 때만 필수 — 위와 동일한 이유로 nullable.
        _enum("operator", OPERATOR_VALUES, nullable=True),
        _numeric("value_numeric", nullable=True),
        _text("value_text"),
        _text("unit", nullable=True),
        _numeric("measurement_window_value", nullable=True),
        _text("measurement_window_unit", nullable=True),
        _text("special_case_note", nullable=True),
        _numeric("display_order"),
        _date("valid_from"),
        _date("valid_to", nullable=True),
        _uuid("source_document_id", fk=_fk(SOURCE_DOCUMENTS, "source_document_id")),
        _text("source_page"),
        _timestamp("last_verified_at"),
    ),
)

# --------------------------------------------------------------------------
# 5. visa_scoring_models
# --------------------------------------------------------------------------

_VISA_SCORING_MODELS_TABLE = TableSpec(
    name=VISA_SCORING_MODELS,
    pk="score_model_id",
    columns=(
        _uuid("score_model_id"),
        _uuid("visa_id", fk=_fk(VISA_REQUIREMENTS, "visa_id")),
        _text("model_name_kr"),
        _enum("model_purpose", MODEL_PURPOSE_VALUES),
        _text("applies_when"),
        _text("selection_rule"),
        _text("tie_breaker_rule", nullable=True),
        _numeric("base_maximum_points"),
        _numeric("minimum_required_points"),
        _numeric("final_maximum_points", nullable=True),
        _numeric("bonus_cap_points", nullable=True),
        _numeric("penalty_cap_points"),
        _numeric("from_round"),
        _numeric("to_round", nullable=True),
        _date("valid_from"),
        _date("valid_to", nullable=True),
        _uuid("source_document_id", fk=_fk(SOURCE_DOCUMENTS, "source_document_id")),
        _text("source_page"),
        _text("notes", nullable=True),
    ),
)

# --------------------------------------------------------------------------
# 6. visa_scoring_items
# --------------------------------------------------------------------------

_VISA_SCORING_ITEMS_TABLE = TableSpec(
    name=VISA_SCORING_ITEMS,
    pk="scoring_item_id",
    columns=(
        _uuid("scoring_item_id"),
        _uuid("score_model_id", fk=_fk(VISA_SCORING_MODELS, "score_model_id")),
        _enum("score_group", SCORE_GROUP_VALUES),
        _text("category"),
        _text("criterion"),
        _numeric("min_value", nullable=True),
        _numeric("max_value", nullable=True),
        _boolean("min_inclusive", nullable=True),
        _boolean("max_inclusive", nullable=True),
        _text("value_text", nullable=True),
        _text("unit", nullable=True),
        _numeric("measurement_window_value", nullable=True),
        _text("measurement_window_unit", nullable=True),
        _numeric("points"),
        _numeric("maximum_points", nullable=True),
        _boolean("is_mandatory"),
        _numeric("minimum_required_points", nullable=True),
        _text("exclusive_group", nullable=True),
        _enum("stacking_rule", STACKING_RULE_VALUES),
        _text("evidence_document", nullable=True),
        _numeric("display_order"),
        _date("valid_from"),
        _date("valid_to", nullable=True),
        _uuid("source_document_id", fk=_fk(SOURCE_DOCUMENTS, "source_document_id")),
        _text("source_page"),
    ),
)

# --------------------------------------------------------------------------
# 7. visa_process_stages
# --------------------------------------------------------------------------

_VISA_PROCESS_STAGES_TABLE = TableSpec(
    name=VISA_PROCESS_STAGES,
    pk="stage_id",
    columns=(
        _uuid("stage_id"),
        _uuid("visa_id", fk=_fk(VISA_REQUIREMENTS, "visa_id")),
        _numeric("stage_order"),
        _text("stage_code"),
        _text("stage_name_kr"),
        _text("actor_from"),
        _text("actor_to"),
        _date("stage_start_date"),
        _date("stage_end_date"),
        _numeric("notice_round", nullable=True),
        _text("notes", nullable=True),
        _date("valid_from"),
        _date("valid_to", nullable=True),
        _uuid("source_document_id", fk=_fk(SOURCE_DOCUMENTS, "source_document_id")),
        _text("source_page"),
        _date("last_verified_at"),
    ),
)

# --------------------------------------------------------------------------
# 8. document_requirements
# --------------------------------------------------------------------------

_DOCUMENT_REQUIREMENTS_TABLE = TableSpec(
    name=DOCUMENT_REQUIREMENTS,
    pk="document_requirement_id",
    columns=(
        _uuid("document_requirement_id"),
        _uuid("stage_id", fk=_fk(VISA_PROCESS_STAGES, "stage_id")),
        _text("document_name"),
        _text("document_category"),
        _text("filled_by"),
        _text("submitted_by"),
        _text("submission_target"),
        _text("signer"),
        _enum("requirement_status", REQUIREMENT_STATUS_VALUES),
        _text("alternative_group", nullable=True),
        _text("condition_note", nullable=True),
        _numeric("display_order"),
        _date("valid_from"),
        _date("valid_to", nullable=True),
        _uuid("source_document_id", fk=_fk(SOURCE_DOCUMENTS, "source_document_id")),
        _text("source_page"),
        _date("last_verified_at"),
        _text("notes", nullable=True),
    ),
)

# --------------------------------------------------------------------------
# 9. document_attachment_relations
# --------------------------------------------------------------------------

_DOCUMENT_ATTACHMENT_RELATIONS_TABLE = TableSpec(
    name=DOCUMENT_ATTACHMENT_RELATIONS,
    pk="relation_id",
    columns=(
        _uuid("relation_id"),
        _uuid(
            "parent_document_id",
            fk=_fk(DOCUMENT_REQUIREMENTS, "document_requirement_id"),
        ),
        _uuid(
            "attachment_document_id",
            fk=_fk(DOCUMENT_REQUIREMENTS, "document_requirement_id"),
        ),
        _enum("requirement_status", REQUIREMENT_STATUS_VALUES),
        _text("alternative_group", nullable=True),
        _text("condition_note", nullable=True),
        _numeric("display_order"),
        _date("valid_from"),
        _date("valid_to", nullable=True),
        _uuid("source_document_id", fk=_fk(SOURCE_DOCUMENTS, "source_document_id")),
        _text("source_page"),
    ),
)

# --------------------------------------------------------------------------
# 10. visa_quota_policies
# --------------------------------------------------------------------------

_VISA_QUOTA_POLICIES_TABLE = TableSpec(
    name=VISA_QUOTA_POLICIES,
    pk="quota_policy_id",
    columns=(
        _uuid("quota_policy_id"),
        _uuid("visa_id", fk=_fk(VISA_REQUIREMENTS, "visa_id")),
        _enum("quota_type", QUOTA_TYPE_VALUES),
        _text("quota_unit"),
        _date("valid_from"),
        _date("valid_to", nullable=True),
        _uuid("source_document_id", fk=_fk(SOURCE_DOCUMENTS, "source_document_id")),
        _text("source_page"),
    ),
)

# --------------------------------------------------------------------------
# 11. visa_quota_snapshots
# --------------------------------------------------------------------------

_VISA_QUOTA_SNAPSHOTS_TABLE = TableSpec(
    name=VISA_QUOTA_SNAPSHOTS,
    pk="quota_snapshot_id",
    columns=(
        _uuid("quota_snapshot_id"),
        _uuid("quota_policy_id", fk=_fk(VISA_QUOTA_POLICIES, "quota_policy_id")),
        _numeric("notice_round", nullable=True),
        _date("as_of_date"),
        _enum("scope_type", SCOPE_TYPE_VALUES),
        _text("scope_name"),
        # NATIONAL/PROVINCE처럼 상위 범위가 없는 스냅샷은 부모가 없는 게 정상이다
        # (실제 사례: E-7-4R 8차 PROVINCE 스냅샷). Task 3에서 "실제 사례가 나오면
        # 완화" 조건으로 non-nullable로 되돌렸던 필드 — 그 사례가 나와 완화한다.
        _text("parent_scope_name", nullable=True),
        _numeric("allocated_quota"),
        _numeric("recommended_count", nullable=True),
        _numeric("quota_exempt_count", nullable=True),
        _numeric("consumed_quota"),
        _numeric("remaining_quota"),
        _text("consumption_exception", nullable=True),
        _date("valid_from"),
        _date("valid_to", nullable=True),
        _uuid("source_document_id", fk=_fk(SOURCE_DOCUMENTS, "source_document_id")),
        _text("source_page"),
        _timestamp("recorded_at"),
    ),
)

# --------------------------------------------------------------------------
# 12. change_history — 댓글 결정에 따라 v1 헤더를 그대로 유지한다.
# --------------------------------------------------------------------------

_CHANGE_HISTORY_TABLE = TableSpec(
    name=CHANGE_HISTORY,
    pk="change_id",
    columns=(
        _uuid("change_id"),
        _uuid("visa_id", fk=_fk(VISA_REQUIREMENTS, "visa_id")),
        _text("table_name"),
        _text("field_identifier"),
        _numeric("from_round"),
        _numeric("to_round"),
        _text("old_value", nullable=True),
        _text("new_value", nullable=True),
        _text("change_type"),
        _text("old_source_page", nullable=True),
        _text("new_source_page", nullable=True),
        _text("description", nullable=True),
    ),
)

# --------------------------------------------------------------------------
# 13. source_record_mappings
# --------------------------------------------------------------------------

_SOURCE_RECORD_MAPPINGS_TABLE = TableSpec(
    name=SOURCE_RECORD_MAPPINGS,
    pk="mapping_id",
    columns=(
        _uuid("mapping_id"),
        _uuid("visa_id", fk=_fk(VISA_REQUIREMENTS, "visa_id")),
        _text("source_dataset"),
        _text("source_table"),
        _text("source_record_id"),
        _text("source_group_path", nullable=True),
        _uuid("source_document_id", fk=_fk(SOURCE_DOCUMENTS, "source_document_id")),
        # source_record_mappings는 서비스 판정용 코어가 아니라 이관 장부다. 원천 값
        # 자체가 페이지·유효기간을 안 주는 경우(웹 목록, "미확인"으로 명시된 원문 등)가
        # 있어 nullable — 실제 서비스 테이블(criteria/groups 등)의 source_page/
        # valid_from은 여전히 필수다.
        _text("source_page", nullable=True),
        _date("valid_from", nullable=True),
        _date("valid_to", nullable=True),
        _text("target_table"),
        # 발급 전에는 null. 대상 테이블이 target_table 값에 따라 달라져 일반적인 단일
        # FK로 표현할 수 없으므로 fk를 지정하지 않는다(검증기에서도 존재 검사를 하지 않음).
        _uuid("target_record_id", nullable=True),
        _enum("mapping_action", MAPPING_ACTION_VALUES),
        _enum("mapping_status", MAPPING_STATUS_VALUES),
        _text("blocking_reason", nullable=True),
        # target_record_id와 마찬가지로 실제 이관(9단계) 전에는 비어 있다. PENDING/
        # BLOCKED 상태의 초안 행은 아직 매핑되지 않았으므로 null이 정상이다.
        _timestamp("mapped_at", nullable=True),
        _text("mapping_note", nullable=True),
    ),
)

# --------------------------------------------------------------------------
# 전체 스키마 — docs/schema-v2.md의 "1. ~ 13." 번호 순서를 그대로 따른다.
# --------------------------------------------------------------------------

SCHEMA_V2: dict[str, TableSpec] = {
    SOURCE_DOCUMENTS: _SOURCE_DOCUMENTS_TABLE,
    VISA_REQUIREMENTS: _VISA_REQUIREMENTS_TABLE,
    VISA_CRITERION_GROUPS: _VISA_CRITERION_GROUPS_TABLE,
    VISA_REQUIREMENT_CRITERIA: _VISA_REQUIREMENT_CRITERIA_TABLE,
    VISA_SCORING_MODELS: _VISA_SCORING_MODELS_TABLE,
    VISA_SCORING_ITEMS: _VISA_SCORING_ITEMS_TABLE,
    VISA_PROCESS_STAGES: _VISA_PROCESS_STAGES_TABLE,
    DOCUMENT_REQUIREMENTS: _DOCUMENT_REQUIREMENTS_TABLE,
    DOCUMENT_ATTACHMENT_RELATIONS: _DOCUMENT_ATTACHMENT_RELATIONS_TABLE,
    VISA_QUOTA_POLICIES: _VISA_QUOTA_POLICIES_TABLE,
    VISA_QUOTA_SNAPSHOTS: _VISA_QUOTA_SNAPSHOTS_TABLE,
    CHANGE_HISTORY: _CHANGE_HISTORY_TABLE,
    SOURCE_RECORD_MAPPINGS: _SOURCE_RECORD_MAPPINGS_TABLE,
}

TABLE_ORDER: tuple[str, ...] = tuple(SCHEMA_V2.keys())

assert len(TABLE_ORDER) == 13, f"v2 스키마는 13개 테이블이어야 함 (현재 {len(TABLE_ORDER)}개)"


# --------------------------------------------------------------------------
# 자기 검사: 금지된 이름, .csv 접미사
# --------------------------------------------------------------------------


def check_no_forbidden_names(schema: dict[str, TableSpec] | None = None) -> list[str]:
    """스키마 정의 안에 금지된 테이블·컬럼명이 없는지 확인한다.

    docs/schema-v2.md "제외되는 것" 절 — 별도 상태관리 성격의 컬럼·테이블을 나중에
    실수로 다시 들여오는 것을 막는 가드레일이다.
    """
    schema = SCHEMA_V2 if schema is None else schema
    errors: list[str] = []
    for table_name, table in schema.items():
        if table_name in FORBIDDEN_NAMES:
            errors.append(f"금지된 테이블명이 스키마에 있음: {table_name}")
        for col in table.columns:
            if col.name in FORBIDDEN_NAMES:
                errors.append(f"{table_name}.{col.name}: 금지된 컬럼명이 스키마에 있음")
    return errors


def check_no_csv_suffix_in_logical_names(schema: dict[str, TableSpec] | None = None) -> list[str]:
    """스키마의 논리 테이블명 어디에도 .csv 확장자가 없는지 확인한다."""
    schema = SCHEMA_V2 if schema is None else schema
    errors: list[str] = []
    for key, table in schema.items():
        if key.endswith(".csv"):
            errors.append(f"스키마 dict 키에 .csv 확장자가 있으면 안 됨: {key!r}")
        if table.name.endswith(".csv"):
            errors.append(f"테이블 논리명에 .csv 확장자가 있으면 안 됨: {table.name!r}")
    return errors


# --------------------------------------------------------------------------
# 빈 CSV 골격 생성 — 문서/코드/실제 파일 드리프트 방지용
# --------------------------------------------------------------------------


class PopulatedFileExistsError(RuntimeError):
    """헤더 외에 데이터 행이 있는 기존 CSV를 force 없이 덮어쓰려 할 때 발생시키는 예외.

    `extraction/common_v2/`는 검수를 마친, git 커밋 이력 외에는 복구 수단이 없는 데이터다.
    이 예외는 그 디렉터리를 기본 출력 경로로 삼는 스크립트를 그대로 실행했을 때 실수로
    13개 CSV를 헤더만 남기고 지워버리는 사고를 막기 위한 안전장치다.
    """


def _has_data_rows(path: Path) -> bool:
    """CSV 파일에 헤더 외의 데이터 행이 하나라도 있으면 True.

    파일이 없거나 헤더 한 줄(또는 완전히 빈 파일)뿐이면 False — 이 경우는 덮어써도 안전하다.
    """
    if not path.exists():
        return False
    with path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.reader(f))
    return len(rows) > 1


def write_empty_csv(table: TableSpec, output_dir: Path, *, force: bool = False) -> Path:
    """테이블 정의의 헤더만 담은 빈 CSV 하나를 output_dir에 쓰고 경로를 반환한다.

    기존 파일에 헤더 외 데이터 행이 있으면 `force=True`를 명시하지 않는 한 거부한다 —
    `extraction/common_v2/`처럼 검수 완료된 데이터를 실수로 헤더만 남기고 지우는 사고를
    막기 위함이다(git 커밋 이력이 유일한 복구 수단인 데이터).
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / table.filename
    if not force and _has_data_rows(path):
        raise PopulatedFileExistsError(
            f"{path}에 이미 데이터 행이 있어 덮어쓰기를 거부합니다. "
            "의도적으로 비우려면 --force(또는 force=True)를 명시하세요."
        )
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(table.header)
    return path


def generate_empty_csvs(
    output_dir: Path,
    tables: Iterable[TableSpec] | None = None,
    *,
    force: bool = False,
) -> list[Path]:
    """스키마 정의 순서대로 13개(또는 지정한) 빈 CSV를 output_dir에 생성한다.

    기존 파일에 데이터 행이 있는 경우 `force=True`가 아니면 `PopulatedFileExistsError`를
    발생시키고 어떤 파일도 쓰지 않는다(부분적으로 파괴하는 상황을 피하기 위해 쓰기 전에
    먼저 전체 대상 파일을 검사한다).
    """
    tables = [SCHEMA_V2[name] for name in TABLE_ORDER] if tables is None else list(tables)
    if not force:
        populated = [
            output_dir / t.filename for t in tables if _has_data_rows(output_dir / t.filename)
        ]
        if populated:
            names = ", ".join(str(p) for p in populated)
            raise PopulatedFileExistsError(
                f"다음 파일에 이미 데이터 행이 있어 덮어쓰기를 거부합니다: {names}. "
                "의도적으로 비우려면 --force(또는 force=True)를 명시하세요."
            )
    return [write_empty_csv(table, output_dir, force=force) for table in tables]


DEFAULT_OUTPUT_DIR = Path("extraction/common_v2")


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description="schema_v2.py 정의에서 13개 v2 빈 CSV 골격(헤더만)을 생성한다."
    )
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument(
        "--force",
        action="store_true",
        help=(
            "output-dir에 이미 데이터 행이 있는 CSV가 있어도 헤더만 남기고 덮어쓴다. "
            "기본값은 거부(PopulatedFileExistsError) — extraction/common_v2/처럼 검수 완료된 "
            "데이터를 실수로 지우는 것을 막기 위함이다."
        ),
    )
    args = parser.parse_args()

    forbidden_errors = check_no_forbidden_names()
    if forbidden_errors:
        print("스키마 자기 검사 실패 — 금지된 이름이 있음:")
        for error in forbidden_errors:
            print(f"  - {error}")
        return 1

    try:
        written = generate_empty_csvs(args.output_dir, force=args.force)
    except PopulatedFileExistsError as exc:
        print(f"거부됨 — {exc}")
        return 1
    print(f"v2 빈 CSV {len(written)}개 생성 완료 -> {args.output_dir}")
    for path in written:
        print(f"  - {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
