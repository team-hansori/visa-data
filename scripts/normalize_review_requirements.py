"""검수 CSV에서 구조가 명확한 복합 행을 하위 행으로 분리한다.

기존 review 행과 수동 검수 내용을 보존하면서, 원문 표·복합 문장 중 분리 기준이
확정된 행만 하위 행으로 추가한다. 의미 판단이 필요한 행은 자동으로 건드리지 않는다.

기본 실행은 ``_review_current_requirements_split.csv``를 만들고, ``--in-place``를
사용하면 입력 review CSV를 갱신한다.
"""

from __future__ import annotations

import argparse
import csv
import re
from dataclasses import dataclass
from io import StringIO
from pathlib import Path


PARENT_FIELD = "parent_record_id"
PAGE_RANGE_PATTERN = re.compile(r"^\d+\s*[-~]\s*\d+$")
SOURCE_SECTION_FIELD = "source_section"


@dataclass(frozen=True)
class ChildSpec:
    raw_text: str
    source_page: str | None = None
    review_decision: str | None = None
    target_table: str | None = None


@dataclass(frozen=True)
class SplitSpec:
    parent_record_id: str
    children: tuple[ChildSpec, ...]
    reason: str


@dataclass(frozen=True)
class FragmentMergeSpec:
    canonical_record_id: str
    fragment_record_ids: tuple[str, ...]
    expected_fragments: tuple[str, ...]
    merged_raw_text: str
    reason: str


def child(
    raw_text: str,
    source_page: str | None = None,
    review_decision: str | None = None,
    target_table: str | None = None,
) -> ChildSpec:
    return ChildSpec(raw_text, source_page, review_decision, target_table)


SPLIT_SPECS = (
    SplitSpec(
        "REQ-018",
        (
            child(
                "모집 공고(도 및 시군) | 수시 진행(수정사항 발생시)",
                "2",
                "reclassified",
                "visa_process_stages",
            ),
            child(
                "상시모집(외국인 → 시군) | 쿼터 소진시까지",
                "2",
                "reclassified",
                "visa_process_stages",
            ),
            child(
                "법무부 명단 제출(시군 → 도 → 법무부) | 매주 취합 제출(기간 중 내부심사 실시)",
                "2",
                "reclassified",
                "visa_process_stages",
            ),
            child(
                "체류자격 변경신청(외국인 → 하이코리아) | 하이코리아 전자민원 접수(추천서발급 3개월내)",
                "2",
                "reclassified",
                "visa_process_stages",
            ),
        ),
        "추진 체계 표를 절차 단계별 행으로 분리",
    ),
    SplitSpec(
        "REQ-036",
        (
            child(
                "※ 한국어능력: TOPIK(2급, 3급, 4급 이상), 사회통합프로그램 이수(2단계·3단계·4단계 이상), "
                "사회통합프로그램 사전평가 성적(41~60점, 61점~80점, 81점 이상)",
                "3",
                "reclassified",
                "scoring_items",
            ),
            child(
                "나이 : 최대 60점\n구   분 | 19세 ~ 26세 | 27세 ~ 33세 | 34세 ~ 40세 | 41세 ~\n"
                "배   점 | 40 | 60 | 30 | 10",
                "3",
                "reclassified",
                "scoring_items",
            ),
        ),
        "한국어능력 점수와 나이 점수 표가 하나의 추출 행에 결합되어 있어 분리",
    ),
    SplitSpec(
        "REQ-095",
        (
            child(
                "❍ (고용 가능 인원) 내국인 1명~5명 이하 → E-7-4R 최대 3명",
                "7",
                "approved",
                "visa_requirement_criteria",
            ),
            child(
                "❍ (고용 가능 인원) 내국인 6명 이상 50명 이하 → 내국인 고용 인원의 50%",
                "7",
                "approved",
                "visa_requirement_criteria",
            ),
            child(
                "❍ (고용 가능 인원) 내국인 51명 이상 100명 이하 → 내국인 고용 인원의 50% 내 최대 35명",
                "7",
                "approved",
                "visa_requirement_criteria",
            ),
            child(
                "❍ (고용 가능 인원) 내국인 101명 이상 150명 이하 → E-7-4R 최대 40명",
                "7",
                "approved",
                "visa_requirement_criteria",
            ),
            child(
                "❍ (고용 가능 인원) 내국인 151명 이상 → E-7-4R 최대 50명",
                "7",
                "approved",
                "visa_requirement_criteria",
            ),
        ),
        "고용 가능 인원 구간표를 구간별 자격요건 행으로 분리",
    ),
    SplitSpec(
        "REQ-048",
        (
            child(
                "③ 출입국관리법 3회 이하 위반자로 행정처분을 받은 자(과태료 미포함) (최대 15점) | 5 | 10 | 15",
                "3",
                "reclassified",
                "scoring_items",
            ),
            child("< 기본항목 >가. 소 득", "4", "excluded", "none"),
        ),
        "점수 행과 다음 페이지의 점수표 섹션 제목을 분리",
    ),
    SplitSpec(
        "REQ-060",
        (
            child(
                "* 현재 연도에서 출생 연도를 뺀 다음 계산 시점에 생일이 지났으면 그 수치 그대로 쓰고, 생일이 지나지 않았으면 1년을 뺀 수치를 사용",
                "4",
                "reclassified",
                "scoring_items",
            ),
            child("< 가점항목 >가. 고용주 및 지자체 추천(필수항목)", "5", "excluded", "none"),
        ),
        "나이 계산 보충설명과 다음 페이지의 가점 섹션 제목을 분리",
    ),
    SplitSpec(
        "REQ-077",
        (
            child(
                "※ 직전 근무처 휴‧폐업, 폭언‧폭행‧임금체불과 같은 부당행위 등 근로자 귀책 없는 사유로 근무처 변경을 한 사실이 객관적 증빙자료로 입증될 시, 직전 근무처와 현 근무처의 근무기간을 합산하여 1년 이상이 될 경우 추천 가능",
                "5",
                "reclassified",
                "scoring_items",
            ),
            child("다. 인구감소지역 등 근무경력", "6", "excluded", "none"),
        ),
        "근속 보충설명과 다음 점수 항목 제목을 분리",
    ),
    SplitSpec(
        "REQ-103",
        (
            child(
                "- (E-7-4와 E-7-4R 동시 고용) 숙련기능인력(E-7-4)과 지역특화형 숙련기능인력(E-7-4R)을 동시에 고용하고 있는 기업은 본 지침의 ‘고용가능인원’ 기준을 적용하되, 인구감소지역 소재 기업 또는 뿌리기업, 농림축산어업체에서 내국인 고용인원이 71명을 초과하는 경우 또는 인구감소(관심)지역에서 내국인 고용인원이 135명 이상인 경우 등 ｢숙련기능인력(E-7-4) 체류관리 지침｣ 적용이 사업장에게 더 유리한 경우 숙련기능인력(E-7-4) 허용인원 기준(내국인 고용인원의 50% 이내) 적용",
                "7",
                "approved",
                "visa_requirement_criteria",
            ),
            child("나. 고용주 요건(법무부 조회사항)", "8", "excluded", "none"),
        ),
        "고용 조건과 다음 페이지의 고용주 요건 제목을 분리",
    ),
    SplitSpec(
        "REQ-135",
        (
            child(
                "❍ 본 공고문에서 구체적으로 정하지 않은 사항 등에 대해서는 법무부 지역특화형 비자 운영지침에 따름",
                "11",
                "excluded",
                "none",
            ),
            child("[서  식]", "12", "excluded", "none"),
        ),
        "기타 안내 문장과 서식 섹션 제목을 분리",
    ),
)


MERGE_SPECS = (
    FragmentMergeSpec(
        "REQ-030",
        ("REQ-031", "REQ-032", "REQ-033"),
        ("①,", "③,", "④는 최근 10년 이내 사항만 해당"),
        "* ①, ③, ④는 최근 10년 이내 사항만 해당",
        "한 줄의 보충 설명이 네 개의 추출 행으로 분리됨",
    ),
)


# 분리된 행 또는 원문 의미가 확정된 행만 대상 테이블을 보정한다. 행 분리·원문
# 복원이 필요한 needs_review 행은 자동으로 확정하지 않는다.
TARGET_TABLE_RULES: dict[str, tuple[str, str]] = {
    "REQ-048-01": ("reclassified", "scoring_items"),
    "REQ-060-01": ("reclassified", "scoring_items"),
    "REQ-077-01": ("reclassified", "scoring_items"),
    "REQ-103-01": ("approved", "visa_requirement_criteria"),
    **dict.fromkeys(
        (f"REQ-{number:03d}" for number in range(116, 120)),
        ("reclassified", "visa_process_stages"),
    ),
}


def _ids(first: int, last: int) -> tuple[str, ...]:
    return tuple(f"REQ-{number:03d}" for number in range(first, last + 1))


COMMON_SCORE_ROOT = "자격 요건 > 점수제 심사 > 지역특화 숙련기능인력 점수표"
COMMON_EMPLOYER_ROOT = "자격 요건 > 고용기업 및 고용주 요건"

# 원문 메모에서 경로가 확정된 행만 등록한다. 섹션명을 추론하거나 raw_text를
# 검색해 자동 분류하지 않음으로써, 아직 논의가 필요한 행은 기존 값을 보존한다.
SOURCE_SECTION_RULES: dict[str, str] = {
    **dict.fromkeys(_ids(23, 33), "자격 요건 > 추천대상 > 제외대상"),
    "REQ-034": f"{COMMON_SCORE_ROOT} > 기본 항목",
    **dict.fromkeys(_ids(37, 44), f"{COMMON_SCORE_ROOT} > 가점 항목"),
    **dict.fromkeys(_ids(45, 47), f"{COMMON_SCORE_ROOT} > 감점 항목"),
    **dict.fromkeys(_ids(49, 52), f"{COMMON_SCORE_ROOT} > 기본 항목 > 가. 소득"),
    **dict.fromkeys(_ids(53, 57), f"{COMMON_SCORE_ROOT} > 기본 항목 > 나. 한국어 능력"),
    **dict.fromkeys(_ids(58, 59), f"{COMMON_SCORE_ROOT} > 기본 항목 > 다. 나이"),
    **dict.fromkeys(
        _ids(61, 72),
        f"{COMMON_SCORE_ROOT} > 가점 항목 > 가. 고용주 및 지자체 추천(필수항목)",
    ),
    **dict.fromkeys(_ids(74, 76), f"{COMMON_SCORE_ROOT} > 가점 항목 > 나. 현 근무처 근속"),
    "REQ-078": f"{COMMON_SCORE_ROOT} > 가점 항목 > 다. 인구감소지역 등 근무경력",
    **dict.fromkeys(_ids(79, 80), f"{COMMON_SCORE_ROOT} > 가점 항목 > 라. 자격증 소지"),
    **dict.fromkeys(_ids(81, 82), f"{COMMON_SCORE_ROOT} > 가점 항목 > 마. 국내대학 학위"),
    **dict.fromkeys(_ids(83, 86), f"{COMMON_SCORE_ROOT} > 가점 항목 > 바. 국내 운전면허증"),
    **dict.fromkeys(_ids(87, 92), f"{COMMON_SCORE_ROOT} > 감점 항목"),
    **dict.fromkeys(_ids(93, 103), f"{COMMON_EMPLOYER_ROOT} > 가. 고용기업 요건"),
    **dict.fromkeys(_ids(104, 105), f"{COMMON_EMPLOYER_ROOT} > 나. 고용주 요건"),
    **dict.fromkeys(_ids(106, 107), f"{COMMON_EMPLOYER_ROOT} > 다. 제외 대상"),
    "REQ-112": "제출서류 > 필수 서류: 모든 신청자 반드시 제출",
    "REQ-113": "제출서류 > 필수 서류: 모든 신청자 반드시 제출",
    "REQ-114": "제출서류 > 추가 서류: 해당자에 한 해 제출",
    "REQ-036-01": f"{COMMON_SCORE_ROOT} > 가점 항목",
    "REQ-036-02": f"{COMMON_SCORE_ROOT} > 가점 항목",
    "REQ-048-01": f"{COMMON_SCORE_ROOT} > 기본 항목 > 가. 소득",
    "REQ-048-02": f"{COMMON_SCORE_ROOT} > 기본 항목 > 가. 소득",
    "REQ-060-01": f"{COMMON_SCORE_ROOT} > 기본 항목 > 다. 나이",
    "REQ-060-02": f"{COMMON_SCORE_ROOT} > 가점 항목 > 가. 고용주 및 지자체 추천(필수항목)",
    "REQ-077-01": f"{COMMON_SCORE_ROOT} > 가점 항목 > 나. 현 근무처 근속",
    "REQ-077-02": f"{COMMON_SCORE_ROOT} > 가점 항목 > 다. 인구감소지역 등 근무경력",
    "REQ-103-01": f"{COMMON_EMPLOYER_ROOT} > 가. 고용기업 요건",
    "REQ-103-02": f"{COMMON_EMPLOYER_ROOT} > 나. 고용주 요건",
}

SOURCE_SECTION_RULES.update(
    {f"REQ-095-{index:02d}": f"{COMMON_EMPLOYER_ROOT} > 가. 고용기업 요건" for index in range(1, 6)}
)


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    """CSV를 읽고 편집기에서 섞인 NUL 문자를 제거한다."""

    text = path.read_text(encoding="utf-8-sig").replace("\x00", "")
    reader = csv.DictReader(StringIO(text))
    if reader.fieldnames is None:
        raise ValueError(f"CSV 헤더가 없습니다: {path}")
    return reader.fieldnames, list(reader)


def append_note(existing: str, note: str) -> str:
    existing = (existing or "").strip()
    return f"{existing}; {note}" if existing else note


def find_page_range_rows(
    rows: list[dict[str, str]], resolved_parent_ids: set[str] | None = None
) -> list[str]:
    """source_page가 범위로 남아 있어 하위 페이지 확인이 필요한 행을 찾는다."""

    resolved_parent_ids = resolved_parent_ids or set()
    return [
        row.get("record_id", "")
        for row in rows
        if row.get("record_id", "") not in resolved_parent_ids
        if PAGE_RANGE_PATTERN.fullmatch((row.get("source_page") or "").strip())
    ]


def _resolve_child_spec_values(
    parent: dict[str, str], child_spec: ChildSpec
) -> dict[str, str]:
    """분리 사양의 자식 행 필드값을 부모의 보존값으로 보정해 반환한다."""

    return {
        "raw_text": child_spec.raw_text,
        "source_page": child_spec.source_page or parent.get("source_page", ""),
        "review_decision": child_spec.review_decision
        or parent.get("_original_review_decision", "reclassified"),
        "target_table": child_spec.target_table
        or parent.get("_original_target_table", "none"),
    }


def split_rows(
    fieldnames: list[str], rows: list[dict[str, str]], specs: tuple[SplitSpec, ...] = SPLIT_SPECS
) -> tuple[list[dict[str, str]], list[str], list[str]]:
    """분리 사양을 적용하고 새 행 ID 목록과 수동 검수 충돌 목록을 반환한다."""

    if PARENT_FIELD not in fieldnames:
        fieldnames = [*fieldnames, PARENT_FIELD]

    output = [{**row, PARENT_FIELD: row.get(PARENT_FIELD, "")} for row in rows]
    by_id = {row.get("record_id", ""): row for row in output}
    existing_ids = set(by_id)
    added_ids: list[str] = []
    manually_changed: list[str] = []

    for spec in specs:
        parent = by_id.get(spec.parent_record_id)
        if parent is None:
            continue

        child_ids = [
            f"{spec.parent_record_id}-{index:02d}" for index in range(1, len(spec.children) + 1)
        ]
        if all(child_id in existing_ids for child_id in child_ids):
            existing_rows = {row.get("record_id", ""): row for row in output}
            for child_id, child_spec in zip(child_ids, spec.children):
                existing_child = existing_rows[child_id]
                spec_values = _resolve_child_spec_values(parent, child_spec)
                for field_name, spec_value in spec_values.items():
                    current_value = existing_child.get(field_name, "")
                    if not current_value:
                        existing_child[field_name] = spec_value
                    elif current_value != spec_value:
                        # 검수자가 수동으로 바꿔둔 값은 덮어쓰지 않고 충돌로만 기록한다.
                        manually_changed.append(f"{child_id}.{field_name}")
            continue
        if any(child_id in existing_ids for child_id in child_ids):
            raise ValueError(f"일부 하위 행만 이미 존재합니다: {spec.parent_record_id}")

        parent["review_decision"] = "excluded"
        parent["target_table"] = "none"
        parent["review_note"] = append_note(
            parent.get("review_note", ""),
            f"복합 행을 {', '.join(child_ids)}로 분리함 ({spec.reason})",
        )

        for child_id, child_spec in zip(child_ids, spec.children):
            child = {name: parent.get(name, "") for name in fieldnames}
            child.update(
                {
                    "record_id": child_id,
                    PARENT_FIELD: spec.parent_record_id,
                    **_resolve_child_spec_values(parent, child_spec),
                    "review_note": append_note(
                        parent.get("review_note", ""),
                        f"{spec.parent_record_id}에서 파생된 하위 행 ({spec.reason})",
                    ),
                }
            )
            output.append(child)
            added_ids.append(child_id)

        existing_ids.update(child_ids)

    # 부모의 원래 매핑값을 자식 생성 전에 보존하기 위한 내부 키를 제거한다.
    for row in output:
        row.pop("_original_review_decision", None)
        row.pop("_original_target_table", None)
    return output, added_ids, manually_changed


def apply_specs(
    fieldnames: list[str], rows: list[dict[str, str]], specs: tuple[SplitSpec, ...] = SPLIT_SPECS
) -> tuple[list[str], list[dict[str, str]], list[str], list[str]]:
    """분리 전에 부모의 기존 매핑값을 보존해 자식 행에 전달한다."""

    prepared = []
    for row in rows:
        prepared.append(
            {
                **row,
                "_original_review_decision": row.get("review_decision", ""),
                "_original_target_table": row.get("target_table", ""),
            }
        )
    output, added_ids, manually_changed = split_rows(fieldnames, prepared, specs)
    output_fieldnames = [*fieldnames] if PARENT_FIELD in fieldnames else [*fieldnames, PARENT_FIELD]
    return output_fieldnames, output, added_ids, manually_changed


def normalize_fragment_merges(
    fieldnames: list[str],
    rows: list[dict[str, str]],
    specs: tuple[FragmentMergeSpec, ...] = MERGE_SPECS,
) -> tuple[list[str], list[dict[str, str]], list[str], list[str]]:
    """확정된 원문 조각 행을 대표 행으로 병합한다.

    모든 조각이 예상값과 일치할 때만 적용한다. 일부 행이 없거나 내용이 다르면
    추측으로 병합하지 않고 보류 목록에 기록한다.
    """

    by_id = {row.get("record_id", ""): row for row in rows}
    applied: list[str] = []
    skipped: list[str] = []

    for spec in specs:
        record_ids = (spec.canonical_record_id, *spec.fragment_record_ids)
        target_rows = [by_id.get(record_id) for record_id in record_ids]
        if any(target_row is None for target_row in target_rows):
            skipped.append(spec.canonical_record_id)
            continue

        canonical = target_rows[0]
        fragments = target_rows[1:]
        current_fragments = tuple(row.get("raw_text", "") for row in fragments)
        already_merged = canonical.get("raw_text", "") == spec.merged_raw_text
        if not already_merged and current_fragments != spec.expected_fragments:
            skipped.append(spec.canonical_record_id)
            continue

        if already_merged and all(
            row.get("review_decision") == "excluded" and row.get("target_table") == "none"
            for row in fragments
        ):
            continue

        canonical["raw_text"] = spec.merged_raw_text
        canonical["review_note"] = append_note(
            canonical.get("review_note", ""),
            f"{', '.join(record_ids)}를 하나의 원문 행으로 병합함 ({spec.reason})",
        )
        for fragment in fragments:
            fragment["review_decision"] = "excluded"
            fragment["target_table"] = "none"
            fragment["review_note"] = append_note(
                fragment.get("review_note", ""),
                f"{spec.canonical_record_id} 대표 행에 병합된 원문 조각 ({spec.reason})",
            )
        applied.append(spec.canonical_record_id)

    return fieldnames, rows, applied, skipped


def normalize_target_tables(
    fieldnames: list[str],
    rows: list[dict[str, str]],
    rules: dict[str, tuple[str, str]] = TARGET_TABLE_RULES,
) -> tuple[list[str], list[dict[str, str]], list[tuple[str, str, str, str, str]]]:
    """확정된 행의 검수 판정과 대상 테이블을 보정한다."""

    changes: list[tuple[str, str, str, str, str]] = []
    for row in rows:
        record_id = row.get("record_id", "")
        rule = rules.get(record_id)
        if rule is None:
            continue
        new_decision, new_target = rule
        old_decision = row.get("review_decision", "")
        old_target = row.get("target_table", "")
        if old_decision == new_decision and old_target == new_target:
            continue
        row["review_decision"] = new_decision
        row["target_table"] = new_target
        changes.append((record_id, old_decision, old_target, new_decision, new_target))
    return fieldnames, rows, changes


def normalize_source_sections(
    fieldnames: list[str],
    rows: list[dict[str, str]],
    rules: dict[str, str] = SOURCE_SECTION_RULES,
) -> tuple[list[str], list[dict[str, str]], list[tuple[str, str, str]]]:
    """확정된 record_id의 source_section만 정규화한다.

    반환하는 변경 목록은 ``(record_id, 기존 경로, 새 경로)`` 형식이다. 규칙에
    없는 행은 추론하지 않고 그대로 두며, raw_text·review_note 등 다른 필드는
    수정하지 않는다.
    """

    output_fieldnames = [*fieldnames]
    if SOURCE_SECTION_FIELD not in output_fieldnames:
        output_fieldnames.append(SOURCE_SECTION_FIELD)

    changes: list[tuple[str, str, str]] = []
    for row in rows:
        record_id = row.get("record_id", "")
        new_section = rules.get(record_id)
        if new_section is None:
            continue
        old_section = row.get(SOURCE_SECTION_FIELD, "")
        if old_section == new_section:
            continue
        row[SOURCE_SECTION_FIELD] = new_section
        changes.append((record_id, old_section, new_section))
    return output_fieldnames, rows, changes


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(
            file, fieldnames=fieldnames, extrasaction="ignore", lineterminator="\r\n"
        )
        writer.writeheader()
        writer.writerows(rows)


def output_path(input_path: Path) -> Path:
    return input_path.with_name("_review_current_requirements_split.csv")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="E-7-4R review CSV의 복합 행 분리 및 source_section 정규화"
    )
    parser.add_argument("input_csv", type=Path, help="입력 review CSV 경로")
    parser.add_argument("--output", type=Path, help="분리 결과 CSV 경로")
    parser.add_argument("--in-place", action="store_true", help="입력 CSV에 분리 결과를 반영")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="결과를 저장하지 않고 분리·source_section 변경 내역만 출력",
    )
    args = parser.parse_args()

    fieldnames, rows = read_csv(args.input_csv)
    fieldnames, split_result, added_ids, manually_changed_ids = apply_specs(fieldnames, rows)
    fieldnames, split_result, merged_ids, skipped_merge_ids = normalize_fragment_merges(
        fieldnames, split_result
    )
    fieldnames, split_result, target_changes = normalize_target_tables(fieldnames, split_result)
    fieldnames, split_result, section_changes = normalize_source_sections(fieldnames, split_result)
    resolved_parent_ids = {spec.parent_record_id for spec in SPLIT_SPECS}
    page_range_rows = find_page_range_rows(rows, resolved_parent_ids)

    print(f"분리 대상: {len(added_ids)}행")
    if added_ids:
        print("추가 예정: " + ", ".join(added_ids))
    if manually_changed_ids:
        print("수동 검수값 보존(자동 갱신 보류): " + ", ".join(manually_changed_ids))
    print(f"원문 조각 병합: {len(merged_ids)}건")
    if merged_ids:
        print("병합 완료: " + ", ".join(merged_ids))
    if skipped_merge_ids:
        print("원문 확인 필요(자동 병합 보류): " + ", ".join(skipped_merge_ids))
    print(f"target_table 변경: {len(target_changes)}행")
    for record_id, old_decision, old_target, new_decision, new_target in target_changes:
        print(
            f"- {record_id}: {old_decision}/{old_target or 'none'} -> {new_decision}/{new_target}"
        )
    print(f"source_section 변경: {len(section_changes)}행")
    for record_id, old_section, new_section in section_changes:
        print(f"- {record_id}: {old_section or '(비어 있음)'} -> {new_section}")
    if page_range_rows:
        print("페이지별 확인 필요: " + ", ".join(page_range_rows))

    if args.dry_run:
        return
    if args.in_place and args.output:
        parser.error("--in-place와 --output은 함께 사용할 수 없습니다")

    destination = args.input_csv if args.in_place else (args.output or output_path(args.input_csv))
    write_csv(destination, fieldnames, split_result)
    print(f"저장됨: {destination}")


if __name__ == "__main__":
    main()
