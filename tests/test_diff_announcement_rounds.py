"""차수 비교 스크립트(diff_announcement_rounds.py) 회귀 테스트."""

from pathlib import Path

import pytest

from scripts.diff_announcement_rounds import chunk_units, diff_rounds, extract_document_units


class TestExtractDocumentUnits:
    def test_raises_on_unsupported_extension(self):
        with pytest.raises(ValueError, match=r"\.hwpx/\.hwp/\.pdf"):
            extract_document_units(Path("공고(2026년 4차).docx"))


class TestChunkUnits:
    def test_splits_on_document_markers(self):
        units = ["❍ 요건 A ※ 보충 설명"]
        assert chunk_units(units) == ["❍ 요건 A", "※ 보충 설명"]

    def test_normalizes_internal_line_breaks(self):
        """추출기(HWPX/HWP)마다 줄바꿈이 달라도 조각 안 공백은 하나로 합쳐져야 한다."""
        units = ["❍ 최근 10년간\r체류한 現 등록\n외국인"]
        assert chunk_units(units) == ["❍ 최근 10년간 체류한 現 등록 외국인"]

    def test_treats_multiple_units_as_one_document(self):
        units = ["❍ 첫 페이지 내용", "❍ 둘째 페이지 내용"]
        assert chunk_units(units) == ["❍ 첫 페이지 내용", "❍ 둘째 페이지 내용"]


class TestDiffRounds:
    def test_no_diff_when_identical(self):
        units = ["❍ 같은 내용"]
        assert diff_rounds(units, units) == ""

    def test_detects_changed_chunk(self):
        old_units = ["❍ 체류기간 2년 이상"]
        new_units = ["❍ 체류기간 3년 이상"]
        diff = diff_rounds(old_units, new_units)
        assert "-❍ 체류기간 2년 이상" in diff
        assert "+❍ 체류기간 3년 이상" in diff

    def test_ignores_line_break_differences_across_extractors(self):
        """줄바꿈 방식만 다르고(HWP의 \\r vs HWPX) 내용이 같으면 diff에 안 잡혀야 한다."""
        old_units = ["❍ 체류기간\r2년 이상"]
        new_units = ["❍ 체류기간 2년 이상"]
        assert diff_rounds(old_units, new_units) == ""

    def test_detects_added_chunk(self):
        old_units = ["❍ 기존 항목"]
        new_units = ["❍ 기존 항목", "❍ 새로 추가된 항목"]
        diff = diff_rounds(old_units, new_units)
        assert "+❍ 새로 추가된 항목" in diff
