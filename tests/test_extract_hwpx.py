"""HWPX 텍스트 추출 스크립트(extract_hwpx.py) 회귀 테스트."""

from scripts.extract_hwpx import section_number


class TestSectionNumber:
    def test_extracts_digits_from_filename(self):
        assert section_number("Contents/section0.xml") == 0
        assert section_number("Contents/section12.xml") == 12

    def test_sorts_numerically_not_lexicographically(self):
        """문자열로 정렬하면 'section10'이 'section2'보다 앞에 오는 버그가 있었다."""
        names = [
            "Contents/section0.xml",
            "Contents/section1.xml",
            "Contents/section2.xml",
            "Contents/section10.xml",
            "Contents/section11.xml",
        ]
        assert sorted(names, key=section_number) == [
            "Contents/section0.xml",
            "Contents/section1.xml",
            "Contents/section2.xml",
            "Contents/section10.xml",
            "Contents/section11.xml",
        ]
