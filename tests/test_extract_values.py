"""근거표 값 자동 추출 스크립트(extract_values.py) 회귀 테스트."""

from scripts.extract_values import (
    apply_extracted_values,
    extract_condition_value,
    extract_measurement_window,
)


class TestExtractConditionValue:
    def test_simple_year_condition(self):
        result = extract_condition_value("2년 이상 체류한 現 등록 외국인")
        assert result == {"value_numeric": "2", "unit": "년", "operator": ">="}

    def test_amount_condition(self):
        result = extract_condition_value("벌금 300만 원 이상의 형을 받은 자")
        assert result == {"value_numeric": "300", "unit": "만원", "operator": ">="}

    def test_particle_between_unit_and_comparison(self):
        """'71명을 초과'처럼 단위와 비교말 사이에 조사가 있어도 잡혀야 한다."""
        result = extract_condition_value("내국인 고용인원이 71명을 초과하는 경우")
        assert result == {"value_numeric": "71", "unit": "명", "operator": ">"}

    def test_multiple_candidates_returns_none(self):
        """숫자 조건이 두 개 이상 섞인 문장은 애매하니 자동으로 값을 뽑지 않는다."""
        text = "내국인 고용인원이 71명을 초과하는 경우 또는 내국인 고용인원이 135명 이상인 경우"
        assert extract_condition_value(text) is None

    def test_no_pattern_returns_none(self):
        assert extract_condition_value("조세 체납자(완납 시 신청 가능)") is None


class TestExtractMeasurementWindow:
    def test_recent_years_window(self):
        result = extract_measurement_window("최근 10년간 E-9 자격으로 2년 이상 체류")
        assert result == {"measurement_window_value": "10", "measurement_window_unit": "년"}

    def test_within_recent_years(self):
        result = extract_measurement_window("최근 5년 이내 체류한 적이 있는 경우 제외")
        assert result == {"measurement_window_value": "5", "measurement_window_unit": "년"}

    def test_no_window_returns_none(self):
        assert extract_measurement_window("벌금 300만 원 이상의 형을 받은 자") is None


class TestApplyExtractedValues:
    def test_fills_empty_condition_value(self):
        rows = [
            {"raw_text": "① 벌금 300만 원 이상의 형을 받은 자", "value_numeric": "", "notes": ""}
        ]
        apply_extracted_values(rows)
        assert rows[0]["value_numeric"] == "300"
        assert rows[0]["operator"] == ">="
        assert rows[0]["unit"] == "만원"

    def test_does_not_overwrite_already_filled_value(self):
        """사람이 이미 값을 채워둔 행은 자동 추출이 덮어쓰면 안 된다."""
        rows = [
            {
                "raw_text": "① 벌금 300만 원 이상의 형을 받은 자",
                "value_numeric": "999",
                "notes": "",
            }
        ]
        apply_extracted_values(rows)
        assert rows[0]["value_numeric"] == "999"  # 그대로 유지

    def test_ambiguous_row_is_flagged_not_filled(self):
        """71명 초과 / 135명 이상처럼 후보가 여러 개면 값은 비워두고 notes에 표시한다."""
        rows = [
            {
                "raw_text": (
                    "내국인 고용인원이 71명을 초과하는 경우 또는 "
                    "내국인 고용인원이 135명 이상인 경우"
                ),
                "value_numeric": "",
                "notes": "",
            }
        ]
        apply_extracted_values(rows)
        assert rows[0]["value_numeric"] == ""
        assert "직접 확인 필요" in rows[0]["notes"]
