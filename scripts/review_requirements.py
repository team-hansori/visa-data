"""review CSV 처리 명령의 통합 진입점.

사용법:
    uv run python scripts/review_requirements.py <command> [command options]

기존 세부 모듈의 CLI를 그대로 호출하므로, 각 명령의 인자와 동작은 유지된다.
"""

from __future__ import annotations

import sys
from collections.abc import Callable


COMMANDS: dict[str, tuple[str, str]] = {
    "classify": ("scripts.classify_review_rows", "review CSV 1차 분류 제안"),
    "normalize": ("scripts.normalize_review_requirements", "복합 행 분리·source_section 정규화"),
    "merge": ("scripts.merge_reextracted_review", "재추출 draft 병합"),
    "add-children": ("scripts.add_reextracted_children", "재추출 하위 행 추가"),
    "sort": ("scripts.sort_review_requirements", "부모·자식 행 정렬"),
}


def _load_main(module_name: str) -> Callable[[], None]:
    module = __import__(module_name, fromlist=["main"])
    return module.main


def main() -> None:
    if len(sys.argv) < 2 or sys.argv[1] in {"-h", "--help"}:
        print(__doc__.strip())
        print("\ncommands:")
        for command, (_, description) in COMMANDS.items():
            print(f"  {command:12} {description}")
        return

    command = sys.argv[1]
    if command not in COMMANDS:
        available = ", ".join(COMMANDS)
        raise SystemExit(f"알 수 없는 review 명령: {command}; 사용 가능: {available}")

    # 하위 모듈은 기존 argparse를 그대로 사용하도록 command만 제거한다.
    sys.argv = [sys.argv[0], *sys.argv[2:]]
    module_name, _ = COMMANDS[command]
    _load_main(module_name)()


if __name__ == "__main__":
    main()
