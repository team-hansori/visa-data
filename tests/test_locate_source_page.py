"""근거표 페이지 찾기 스크립트(locate_source_page.py) 회귀 테스트."""

import csv

from scripts.locate_source_page import (
    apply_source_page,
    build_search_fragment,
    find_matching_pages,
    normalize,
    write_csv_atomic,
)


class TestNormalize:
    def test_collapses_newlines_and_multiple_spaces(self):
        assert normalize("❍ 최근 10년간\n   E-9, E-10") == "❍ 최근 10년간 E-9, E-10"


class TestBuildSearchFragment:
    def test_strips_leading_marker(self):
        fragment = build_search_fragment("❍ 최근 10년간 E-9, E-10, H-2 자격으로 2년 이상 체류")
        assert fragment.startswith("최근 10년간")

    def test_strips_numbered_marker(self):
        fragment = build_search_fragment("① 벌금 300만 원 이상의 형을 받은 자")
        assert fragment == "벌금 300만 원 이상의 형을 받은 자"


class TestFindMatchingPages:
    def test_single_match(self):
        pages = ["1페이지 내용", "2페이지에 벌금 300만 원 이상 조항 있음", "3페이지 내용"]
        assert find_matching_pages("벌금 300만 원 이상", pages) == [2]

    def test_no_match(self):
        pages = ["1페이지 내용", "2페이지 내용"]
        assert find_matching_pages("존재하지 않는 문구", pages) == []

    def test_multiple_matches(self):
        pages = ["중복 문구 있음", "다른 내용", "중복 문구 있음"]
        assert find_matching_pages("중복 문구", pages) == [1, 3]


class TestApplySourcePage:
    def test_fills_when_exactly_one_page_matches(self):
        rows = [{"raw_text": "① 벌금 300만 원 이상의 형을 받은 자", "source_page": "", "notes": ""}]
        pages = ["1페이지", "벌금 300만 원 이상의 형을 받은 자가 있는 페이지"]
        filled, not_found, ambiguous = apply_source_page(rows, pages)
        assert filled == 1
        assert rows[0]["source_page"] == "2"

    def test_does_not_overwrite_already_filled_page(self):
        rows = [
            {"raw_text": "① 벌금 300만 원 이상의 형을 받은 자", "source_page": "5", "notes": ""}
        ]
        pages = ["벌금 300만 원 이상의 형을 받은 자가 있는 페이지"]
        apply_source_page(rows, pages)
        assert rows[0]["source_page"] == "5"

    def test_no_match_is_flagged_not_guessed(self):
        rows = [{"raw_text": "① 벌금 300만 원 이상의 형을 받은 자", "source_page": "", "notes": ""}]
        pages = ["전혀 관련 없는 내용"]
        filled, not_found, ambiguous = apply_source_page(rows, pages)
        assert filled == 0
        assert not_found == 1
        assert rows[0]["source_page"] == ""
        assert "직접 확인 필요" in rows[0]["notes"]

    def test_ambiguous_match_is_flagged_not_guessed(self):
        rows = [{"raw_text": "① 벌금 300만 원 이상의 형을 받은 자", "source_page": "", "notes": ""}]
        pages = [
            "벌금 300만 원 이상의 형을 받은 자 언급 1",
            "벌금 300만 원 이상의 형을 받은 자 언급 2",
        ]
        filled, not_found, ambiguous = apply_source_page(rows, pages)
        assert filled == 0
        assert ambiguous == 1
        assert rows[0]["source_page"] == ""

    def test_too_short_fragment_is_flagged(self):
        rows = [{"raw_text": "* ", "source_page": "", "notes": ""}]
        pages = ["아무 내용"]
        filled, not_found, ambiguous = apply_source_page(rows, pages)
        assert filled == 0
        assert not_found == 1
        assert "너무 짧아" in rows[0]["notes"]

    def test_note_is_not_duplicated_on_rerun(self):
        rows = [{"raw_text": "① 벌금 300만 원 이상의 형을 받은 자", "source_page": "", "notes": ""}]
        pages = ["전혀 관련 없는 내용"]
        apply_source_page(rows, pages)
        apply_source_page(rows, pages)
        assert (
            rows[0]["notes"]
            == "PDF에서 일치하는 페이지를 못 찾음(굵은 글씨 누락 가능) - 직접 확인 필요"
        )


class TestWriteCsvAtomic:
    def test_writes_rows_and_replaces_original(self, tmp_path):
        csv_path = tmp_path / "current_requirements.csv"
        csv_path.write_text("record_id,notes\nREQ-001,old\n", encoding="utf-8")

        write_csv_atomic(
            csv_path, ["record_id", "notes"], [{"record_id": "REQ-001", "notes": "new"}]
        )

        with csv_path.open(encoding="utf-8", newline="") as f:
            rows = list(csv.DictReader(f))
        assert rows == [{"record_id": "REQ-001", "notes": "new"}]

    def test_no_leftover_temp_file_after_success(self, tmp_path):
        csv_path = tmp_path / "current_requirements.csv"
        csv_path.write_text("record_id\n", encoding="utf-8")

        write_csv_atomic(csv_path, ["record_id"], [{"record_id": "REQ-001"}])

        assert list(tmp_path.iterdir()) == [csv_path]

    def test_original_untouched_when_write_fails(self, tmp_path):
        """쓰는 도중 오류가 나면 원본 CSV는 손상되지 않고 그대로 남아야 한다."""
        csv_path = tmp_path / "current_requirements.csv"
        csv_path.write_text("record_id\nREQ-001\n", encoding="utf-8")

        bad_row = {"record_id": "REQ-002", "unexpected_field": "boom"}
        try:
            write_csv_atomic(csv_path, ["record_id"], [bad_row])
        except ValueError:
            pass

        assert csv_path.read_text(encoding="utf-8") == "record_id\nREQ-001\n"
        assert list(tmp_path.iterdir()) == [csv_path]
