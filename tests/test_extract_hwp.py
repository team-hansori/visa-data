"""HWP(구버전) 텍스트 추출 스크립트(extract_hwp.py) 회귀 테스트."""

from lxml import etree

from scripts.extract_hwp import (
    extract_node_text,
    extract_table_text,
    find_section_divs,
    normalize_paragraph_breaks,
)

XHTML_NS = "http://www.w3.org/1999/xhtml"


def xml(fragment: str) -> etree._Element:
    """네임스페이스가 있는 XHTML 조각 문자열을 파싱해서 루트 엘리먼트를 반환한다."""
    wrapped = f'<div xmlns="{XHTML_NS}">{fragment}</div>'
    return etree.fromstring(wrapped.encode("utf-8"))


class TestExtractTableText:
    def test_joins_cells_with_pipe(self):
        table = xml(
            "<table><tr><td><p>구분</p></td><td><p>쿼터</p></td></tr>"
            "<tr><td><p>충북</p></td><td><p>542</p></td></tr></table>"
        ).find(f"{{{XHTML_NS}}}table")
        assert extract_table_text(table) == "구분 | 쿼터\n충북 | 542"


class TestExtractNodeText:
    def test_extracts_plain_paragraph_text(self):
        node = xml("<p>충청북도 공고<span> 제2026호</span></p>").find(f"{{{XHTML_NS}}}p")
        assert extract_node_text(node) == "충청북도 공고 제2026호"

    def test_wraps_table_with_newlines(self):
        node = xml("<div><p>안내</p><table><tr><td><p>1</p></td></tr></table></div>")
        result = extract_node_text(node)
        assert result == "안내\n1\n"

    def test_nested_table_not_duplicated(self):
        """표 안에 표가 있어도 findall(직계 자식만)이라 중복 추출되면 안 된다."""
        node = xml(
            "<table><tr><td><table><tr><td><p>안쪽</p></td></tr></table></td></tr></table>"
        ).find(f"{{{XHTML_NS}}}table")
        result = extract_table_text(node)
        assert result.count("안쪽") == 1


class TestNormalizeParagraphBreaks:
    def test_replaces_carriage_return_with_space(self):
        assert normalize_paragraph_breaks("가\r나") == "가 나"

    def test_replaces_crlf_with_space(self):
        assert normalize_paragraph_breaks("가\r\n나") == "가 나"

    def test_does_not_touch_table_row_newlines(self):
        assert normalize_paragraph_breaks("구분 | 쿼터\n충북 | 542") == "구분 | 쿼터\n충북 | 542"


class TestFindSectionDivs:
    def test_finds_only_top_level_section_divs(self):
        root = xml(
            '<div class="Section Section-0 Paper"><p>0번</p></div>'
            '<div class="Section Section-1 Paper"><p>1번</p></div>'
            '<div class="HeaderArea"><p>헤더는 아님</p></div>'
        )
        divs = find_section_divs(root)
        assert len(divs) == 2
        assert divs[0].get("class") == "Section Section-0 Paper"
        assert divs[1].get("class") == "Section Section-1 Paper"
