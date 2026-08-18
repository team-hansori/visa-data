"""섹션 필터링 스크립트(filter_by_section.py) 회귀 테스트."""

from pathlib import Path

import pytest

from scripts.filter_by_section import filter_rows_by_section, resolve_output_path


class TestFilterRowsBySection:
    def test_keeps_only_matching_sections(self):
        rows = [
            {"source_section": "자격 요건 > 추천대상"},
            {"source_section": "자격 요건 > 점수제 심사"},
        ]
        result = filter_rows_by_section(rows, {"자격 요건 > 추천대상"})
        assert result == [{"source_section": "자격 요건 > 추천대상"}]


class TestResolveOutputPath:
    def test_replaces_draft_with_review(self):
        output = resolve_output_path(Path("extraction/B_E-7-4R/requirements/_draft_current_requirements.csv"))
        assert output == Path("extraction/B_E-7-4R/requirements/_review_current_requirements.csv")

    def test_raises_when_filename_has_no_draft_marker(self):
        """'_draft_'가 없는 파일명은 출력 경로가 입력과 같아져 원본을 덮어쓰게 되므로 막아야 한다."""
        with pytest.raises(ValueError, match="_draft_"):
            resolve_output_path(Path("extraction/B_E-7-4R/requirements/current_requirements.csv"))
