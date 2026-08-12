"""근거표 초안 생성 스크립트(draft_requirements.py) 회귀 테스트."""

from scripts.draft_requirements import (
    build_draft_rows,
    build_split_pattern,
    build_top_section_pattern,
    classify_chunk,
    detect_top_section,
    discover_top_headings,
    split_into_chunks,
)

FIELDNAMES = [
    "record_id",
    "requirement_type",
    "raw_text",
    "condition_group",
    "condition_operator",
    "status",
    "source_document",
    "source_section",
    "notes",
]


class TestSplitIntoChunks:
    def test_hyphen_inside_visa_code_not_split(self):
        """'E-9' 같은 코드 안의 하이픈은 목록 구분자로 오인해 잘리면 안 된다."""
        pattern = build_split_pattern(())
        chunks = split_into_chunks("❍ 최근 10년간 E-9, E-10, H-2 자격으로 2년 이상 체류", pattern)
        assert any("E-9, E-10, H-2" in chunk for chunk in chunks)

    def test_bullet_hyphen_with_leading_space_is_split(self):
        """앞에 공백이 있는 '- 항목'은 목록 구분자로 잘려야 한다."""
        pattern = build_split_pattern(())
        chunks = split_into_chunks("❍ 대상자\n    - 제외 대상자", pattern)
        assert chunks == ["❍ 대상자", "- 제외 대상자"]

    def test_numbered_marker_after_angle_bracket_not_split(self):
        """'<①모집공고>'처럼 다이어그램 라벨로 쓰인 번호는 안 잘려야 한다."""
        pattern = build_split_pattern(())
        chunks = split_into_chunks("❍ 추진체계<①모집공고> | → | <②서류 제출>", pattern)
        assert len(chunks) == 1
        assert "①모집공고" in chunks[0]
        assert "②서류 제출" in chunks[0]

    def test_numbered_marker_after_closing_bracket_is_split(self):
        """'<제외대상>① 벌금...'처럼 진짜 목록 항목은 잘려야 한다."""
        pattern = build_split_pattern(())
        chunks = split_into_chunks("<제외대상>① 벌금 300만 원 이상", pattern)
        assert chunks == ["<제외대상>", "① 벌금 300만 원 이상"]


class TestDiscoverTopHeadings:
    def test_finds_real_headings_only(self):
        """'<숫자> |  | <제목>\\n' 형태만 진짜 제목으로 인정하고, 표 안 우연한 숫자는 무시한다."""
        text = (
            "1 |  | 공고 개요\n내용\n"
            "2 |  | 추진 체계\n"
            "매주 취합제출주2 |  | 하이코리아전자민원 접수주3\n"
        )
        headings = discover_top_headings(text)
        assert headings == ("공고 개요", "추진 체계")

    def test_body_mention_is_not_a_heading(self):
        """본문 문장 속에 제목과 같은 문구가 나와도(숫자+파이프 접두 없이) 제목으로 안 잡혀야 한다."""
        text = "❍ 자격 요건을 충족하지 못한 경우 반려됩니다"
        assert discover_top_headings(text) == ()

    def test_multi_digit_chapter_number_is_found(self):
        """챕터 번호가 두 자리 이상이어도(\\d 한 글자가 아니라 \\d+) 제목을 찾아야 한다."""
        text = "10 |  | 기타 사항\n"
        assert discover_top_headings(text) == ("기타 사항",)

    def test_heading_with_parentheses_does_not_break_split(self):
        """제목에 괄호가 있어도(정규식 특수문자) re.escape로 안전하게 처리되어야 한다."""
        text = "1 |  | 신청(변경)\n  ❍ 내용\n"
        headings = discover_top_headings(text)
        assert headings == ("신청(변경)",)

        split_pattern = build_split_pattern(headings)
        top_section_pattern = build_top_section_pattern(headings)
        chunks = split_into_chunks(text, split_pattern)
        assert any("신청(변경)" in chunk for chunk in chunks)
        assert detect_top_section(text, "", top_section_pattern) == "신청(변경)"


class TestBuildDraftRows:
    def test_condition_group_set_but_operator_left_blank(self):
        """condition_group은 자동으로 묶지만, AND/OR(condition_operator)은 사람 몫으로 비워둔다."""
        chunks = ["❍ 요건 A", "※ 보충 설명"]
        pattern = build_top_section_pattern(())
        rows = build_draft_rows(chunks, "source.txt", FIELDNAMES, pattern)

        assert rows[0]["condition_group"] == "G1"
        assert rows[1]["condition_group"] == "G1"
        assert rows[0]["condition_operator"] == ""
        assert rows[1]["condition_operator"] == ""

    def test_unclassified_chunk_is_preserved_not_dropped(self):
        """기호가 없는 조각(other)도 버리지 않고 검토용 행으로 남겨야 한다."""
        chunks = ["기호 없는 일반 문장"]
        pattern = build_top_section_pattern(())
        rows = build_draft_rows(chunks, "source.txt", FIELDNAMES, pattern)

        assert len(rows) == 1
        assert rows[0]["raw_text"] == "기호 없는 일반 문장"
        assert rows[0]["status"] == "not_checked"

    def test_top_section_change_resets_stale_subsection(self):
        """최상위 챕터가 바뀌면, □ 표식 전에 나온 행이 이전 챕터의 하위 섹션을 물려받으면 안 된다."""
        chunks = [
            "□ 체류허가 사항",
            "❍ 체류기간 요건",
            "1 |  | 제출서류\n",  # 다음 챕터 제목, □ 없이 바로 등장
            "❍ (신청방법) 시군 담당부서 방문 접수",
        ]
        top_headings = ("체류허가 사항", "제출서류")
        pattern = build_top_section_pattern(top_headings)
        rows = build_draft_rows(chunks, "source.txt", FIELDNAMES, pattern)

        before = next(r for r in rows if r["raw_text"] == "❍ 체류기간 요건")
        after = next(r for r in rows if "신청방법" in r["raw_text"])
        assert before["source_section"] == "체류허가 사항"
        assert after["source_section"] == "제출서류"  # '체류허가 사항'을 물려받지 않아야 함


class TestClassifyChunk:
    def test_section_marker(self):
        assert classify_chunk("□ 추천대상") == "section"

    def test_diagram_style_angle_bracket_is_section(self):
        assert classify_chunk("<제외대상>") == "section"

    def test_requirement_marker(self):
        assert classify_chunk("❍ 요건") == "requirement"

    def test_footnote_marker(self):
        assert classify_chunk("* 각주") == "footnote"

    def test_no_marker_is_other(self):
        assert classify_chunk("그냥 문장") == "other"


class TestDetectTopSection:
    def test_last_heading_in_chunk_wins(self):
        """한 조각 안에 여러 제목이 섞여 있으면 가장 뒤(오른쪽) 것을 채택한다."""
        pattern = build_top_section_pattern(("추진 체계", "자격 요건"))
        chunk = "...2 |  | 추진 체계\n...\n\n3 |  | 자격 요건"
        assert detect_top_section(chunk, "", pattern) == "자격 요건"

    def test_no_match_keeps_previous_value(self):
        pattern = build_top_section_pattern(("자격 요건",))
        assert detect_top_section("❍ 관련 없는 문장", "자격 요건", pattern) == "자격 요건"
