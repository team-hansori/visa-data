"""검수 완료된 공통 스키마 v2 스냅샷을 결정적으로 재생성한다.

이 스크립트는 v1 원천을 자동으로 의미 변환하지 않는다. 자격조건의 AND/OR 구조, 점수표,
제출서류, 쿼터처럼 사람의 원문 대조가 필요한 판단은 이미 ``extraction/common_v2``와
``source_record_mappings.csv``에 검수 결과로 보존되어 있다. 이 진입점의 책임은 그 확정
스냅샷을 다음 순서로 안전하게 materialize하는 것이다.

1. 원본 13개 CSV의 헤더와 전체 v2 무결성을 알려진 격차 baseline과 대조한다.
2. 행 순서를 유지하면서 UTF-8/LF CSV로 별도 임시 디렉터리에 직렬화한다.
3. 생성 결과를 같은 검증기로 다시 검사한 뒤에만 출력 디렉터리로 교체한다.

기본 출력은 git에서 제외된 ``build/common_v2``다. 검수 원본과 출력 경로가 같거나 서로
포함하는 경로는 ``--force`` 여부와 관계없이 거부하므로, 이 스크립트로
``extraction/common_v2``를 덮어쓸 수 없다.

사용법:
    uv run python scripts/migrate_to_v2.py
    uv run python scripts/migrate_to_v2.py --output-dir /tmp/common-v2
"""

from __future__ import annotations

import argparse
import csv
import os
import shutil
import tempfile
import uuid
from pathlib import Path

from scripts.schema_v2 import SCHEMA_V2, TABLE_ORDER, TableSpec
from scripts.validate_common_schema_v2 import validate_directory

DEFAULT_SOURCE_DIR = Path("extraction/common_v2")
DEFAULT_OUTPUT_DIR = Path("build/common_v2")
DEFAULT_BASELINE_PATH = DEFAULT_SOURCE_DIR / "known_validation_gaps.txt"


class SnapshotBuildError(RuntimeError):
    """스냅샷 입력·검증·출력 계약을 만족하지 못했을 때 발생한다."""


class UnsafeSnapshotPathError(SnapshotBuildError):
    """원본 손상 가능성이 있는 source/output 경로 조합을 거부한다."""


class SnapshotOutputExistsError(SnapshotBuildError):
    """기존 출력이 있는데 명시적인 교체 승인이 없을 때 발생한다."""


def _read_baseline(path: Path | None) -> set[str]:
    if path is None:
        return set()
    if not path.exists():
        raise SnapshotBuildError(f"검증 baseline 파일이 없음: {path}")
    return {
        stripped
        for line in path.read_text(encoding="utf-8").splitlines()
        if (stripped := line.strip()) and not stripped.startswith("#")
    }


def _assert_safe_paths(source_dir: Path, output_dir: Path) -> None:
    source = source_dir.resolve()
    output = output_dir.resolve()
    if source == output or source in output.parents or output in source.parents:
        raise UnsafeSnapshotPathError(
            "source-dir과 output-dir은 같거나 서로 포함할 수 없음: "
            f"source={source}, output={output}"
        )


def _read_table_rows(source_dir: Path, table: TableSpec) -> list[dict[str, str]]:
    path = source_dir / table.filename
    if not path.exists():
        raise SnapshotBuildError(f"스냅샷 원본 파일이 없음: {path}")

    with path.open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != table.header:
            raise SnapshotBuildError(
                f"{path} 헤더가 스키마와 다름: {reader.fieldnames} != {table.header}"
            )
        rows: list[dict[str, str]] = []
        for line_number, row in enumerate(reader, start=2):
            if None in row or any(value is None for value in row.values()):
                raise SnapshotBuildError(
                    f"{path}:{line_number} - 헤더와 데이터 열 개수가 일치하지 않음"
                )
            rows.append({column: row[column] for column in table.header})
    return rows


def _write_table(path: Path, table: TableSpec, rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=table.header,
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)


def _assert_expected_validation_result(base_dir: Path, expected_errors: set[str]) -> None:
    actual_errors = set(validate_directory(base_dir))
    if actual_errors == expected_errors:
        return

    new_errors = sorted(actual_errors - expected_errors)
    missing_errors = sorted(expected_errors - actual_errors)
    details: list[str] = []
    if new_errors:
        details.append("새 검증 오류: " + " | ".join(new_errors))
    if missing_errors:
        details.append("baseline과 달리 사라진 오류: " + " | ".join(missing_errors))
    raise SnapshotBuildError(f"{base_dir} 검증 결과가 baseline과 다름 — {'; '.join(details)}")


def _replace_output_directory(staged_dir: Path, output_dir: Path, *, force: bool) -> None:
    if output_dir.exists() and not force:
        raise SnapshotOutputExistsError(
            f"출력 경로가 이미 존재함: {output_dir}. 교체하려면 --force를 명시하세요."
        )

    output_dir.parent.mkdir(parents=True, exist_ok=True)
    if not output_dir.exists():
        os.replace(staged_dir, output_dir)
        return

    backup = output_dir.parent / f".{output_dir.name}.backup-{uuid.uuid4().hex}"
    os.replace(output_dir, backup)
    try:
        os.replace(staged_dir, output_dir)
    except BaseException:
        os.replace(backup, output_dir)
        raise
    if backup.is_dir():
        shutil.rmtree(backup)
    else:
        backup.unlink()


def build_snapshot(
    source_dir: Path,
    output_dir: Path,
    *,
    baseline_path: Path | None = DEFAULT_BASELINE_PATH,
    force: bool = False,
) -> list[Path]:
    """검수된 v2 13개 CSV를 검증 후 별도 디렉터리에 결정적으로 재생성한다.

    원본과 출력은 서로 겹칠 수 없다. 기존 출력은 ``force=True``일 때만, 새 스냅샷이 임시
    디렉터리에서 완전히 생성되고 검증된 다음 교체한다. 따라서 읽기·직렬화·검증 중 실패하면
    기존 출력과 원본은 그대로 유지된다.
    """
    _assert_safe_paths(source_dir, output_dir)
    expected_errors = _read_baseline(baseline_path)

    tables_and_rows = [
        (SCHEMA_V2[table_name], _read_table_rows(source_dir, SCHEMA_V2[table_name]))
        for table_name in TABLE_ORDER
    ]
    _assert_expected_validation_result(source_dir, expected_errors)

    output_dir.parent.mkdir(parents=True, exist_ok=True)
    staged_dir = Path(tempfile.mkdtemp(prefix=f".{output_dir.name}.tmp-", dir=output_dir.parent))
    try:
        for table, rows in tables_and_rows:
            _write_table(staged_dir / table.filename, table, rows)
        _assert_expected_validation_result(staged_dir, expected_errors)
        _replace_output_directory(staged_dir, output_dir, force=force)
    finally:
        if staged_dir.exists():
            shutil.rmtree(staged_dir)

    return [output_dir / SCHEMA_V2[name].filename for name in TABLE_ORDER]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="검수 완료된 공통 스키마 v2 13개 CSV를 별도 디렉터리에 재생성·검증한다."
    )
    parser.add_argument("--source-dir", type=Path, default=DEFAULT_SOURCE_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--baseline", type=Path, default=DEFAULT_BASELINE_PATH)
    parser.add_argument(
        "--force",
        action="store_true",
        help="기존 output-dir을 검증 완료된 새 스냅샷으로 교체한다. source-dir은 교체 불가.",
    )
    args = parser.parse_args()

    try:
        written = build_snapshot(
            args.source_dir,
            args.output_dir,
            baseline_path=args.baseline,
            force=args.force,
        )
    except SnapshotBuildError as exc:
        print(f"스냅샷 생성 거부 — {exc}")
        return 1

    print(f"v2 검수 스냅샷 생성 완료: {len(written)}/{len(TABLE_ORDER)}개 -> {args.output_dir}")
    for path in written:
        print(f"  - {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
