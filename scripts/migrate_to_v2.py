"""v1 공통 마스터(extraction/D_visa_requirements/)를 공통 스키마 v2로 이관하는 진입점.

**중요 — 이 스크립트는 아직 실제 행 단위 변환 로직을 구현하지 않은 스텁이다.**

지금은 `scripts/schema_v2.py` 정의대로 13개 v2 CSV의 헤더만 생성한다(데이터 행은 0개).
v1 CSV는 참고삼아 존재 여부만 확인하고 읽어들이되, 실제로 v2 행으로 변환하지는 않는다.

F-4-R/E-7-4R/F-2-R 행 단위 변환(조건 그룹 트리 재구성, 점수표 분리, 쿼터 정책/스냅샷
변환 등)은 원문 공고·심사표를 다시 읽어야 하는 사람의 판단이 필요한 후속 작업이며,
`plans/issue-44-common-schema-v2-migration.md`의 4~10단계에서 다룬다. 이 스크립트를
실제 마이그레이션이 끝난 것으로 착각하지 말 것 — 헤더만 있는 빈 CSV를 만드는 것이
이 단계(3단계)의 의도된 범위다.

v1 파일은 참조만 하고 절대 덮어쓰지 않는다("마이그레이션 도중 v1 파일을 덮어쓰지
않는다" — 계획 문서의 구현 원칙).

사용법:
    uv run python scripts/migrate_to_v2.py [--v1-dir DIR] [--output-dir DIR]
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

from scripts.schema_v2 import TABLE_ORDER, PopulatedFileExistsError, generate_empty_csvs

DEFAULT_V1_DIR = Path("extraction/D_visa_requirements")
DEFAULT_OUTPUT_DIR = Path("extraction/common_v2")

# v1 공통 마스터의 6개 CSV 파일명(.csv 없이). 이 스텁은 이 파일들의 존재만 확인한다 —
# 실제 컬럼 매핑은 아직 이 스크립트의 책임이 아니다.
V1_TABLE_NAMES = (
    "visa_requirements",
    "visa_requirement_criteria",
    "visa_process_stages",
    "document_requirements",
    "visa_quota_status",
    "change_history",
)


def read_v1_csv(path: Path) -> list[dict[str, str]]:
    """v1 CSV를 읽어 행 딕셔너리 리스트로 반환한다. 파일이 없으면 빈 리스트."""
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def migrate(v1_dir: Path, output_dir: Path, *, force: bool = False) -> list[Path]:
    """v1 CSV 존재를 확인한 뒤(현재는 읽기만 함) v2 출력 디렉터리에 헤더만 있는 13개
    CSV를 생성한다.

    실제 행 변환 로직은 의도적으로 비어 있다 — 모듈 docstring의 스코프 설명 참고.
    v1 파일은 여기서 절대 쓰지 않는다.

    output_dir에 이미 데이터 행이 있는 v2 CSV가 있으면 `force=True`가 아닌 한
    `scripts.schema_v2.PopulatedFileExistsError`를 발생시키고 아무것도 쓰지 않는다 —
    이 스텁의 기본 출력 경로(`extraction/common_v2/`)는 검수 완료된 실 데이터 디렉터리이기
    때문이다.
    """
    for table_name in V1_TABLE_NAMES:
        # 지금은 파일이 읽히는지만 확인한다. 반환값은 아직 v2 행으로 변환하지 않는다.
        _ = read_v1_csv(v1_dir / f"{table_name}.csv")

    return generate_empty_csvs(output_dir, force=force)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "v1 -> v2 공통 스키마 마이그레이션 진입점. 현재는 헤더만 생성하는 스텁이며 "
            "실제 행 변환은 하지 않는다(모듈 docstring 참고)."
        )
    )
    parser.add_argument("--v1-dir", type=Path, default=DEFAULT_V1_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument(
        "--force",
        action="store_true",
        help=(
            "output-dir에 이미 데이터 행이 있는 CSV가 있어도 헤더만 남기고 덮어쓴다. "
            "기본값은 거부 — 기본 output-dir(extraction/common_v2/)는 검수 완료된 실 데이터 "
            "디렉터리이며 git 커밋 이력 외에는 복구 수단이 없다."
        ),
    )
    args = parser.parse_args()

    try:
        written = migrate(args.v1_dir, args.output_dir, force=args.force)
    except PopulatedFileExistsError as exc:
        print(f"거부됨 — {exc}")
        return 1

    print(
        f"v2 스텁 마이그레이션 완료 (헤더만 생성됨, 실제 행 변환 없음): "
        f"{len(written)}/{len(TABLE_ORDER)}개 파일 -> {args.output_dir}"
    )
    for path in written:
        print(f"  - {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
