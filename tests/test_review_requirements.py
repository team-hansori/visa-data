import sys

import pytest

from scripts import review_requirements


def test_help_lists_review_commands(capsys):
    old_argv = sys.argv
    try:
        sys.argv = ["review_requirements.py", "--help"]
        review_requirements.main()
    finally:
        sys.argv = old_argv

    output = capsys.readouterr().out
    assert "add-children" in output
    assert "normalize" in output


def test_unknown_command_fails():
    old_argv = sys.argv
    try:
        sys.argv = ["review_requirements.py", "unknown"]
        with pytest.raises(SystemExit, match="알 수 없는 review 명령"):
            review_requirements.main()
    finally:
        sys.argv = old_argv
