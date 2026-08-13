"""서식 초안 생성 스크립트(draft_document_forms.py) 회귀 테스트."""

from scripts.draft_document_forms import (
    build_draft_rows,
    find_checklist_page,
    find_form_pages,
    split_checklist_items,
)

FIELDNAMES = [
    "form_id",
    "form_name",
    "raw_text",
    "filled_by",
    "submitted_by",
    "submission_target",
    "signer",
    "required_attachments",
    "is_mandatory",
    "source_document",
    "source_page",
    "notes",
]


class TestFindFormPages:
    def test_finds_form_marker_pages(self):
        pages = [
            "1 |  | 공고 개요\n내용",
            "【서식1】지역특화형 비자사업 추천서 발급신청서\n\n내용...",
            "일반 본문 페이지, 서식 얘기가 나와도 마커로 시작 안 하면 무시",
            "【서식1-2】위 임 장\n\n내용...",
        ]
        forms = find_form_pages(pages)
        assert len(forms) == 2
        assert forms[0] == {
            "form_number": "1",
            "label": "지역특화형 비자사업 추천서 발급신청서",
            "source_page": 2,
            "raw_text": pages[1].strip(),
        }
        assert forms[1]["form_number"] == "1-2"
        assert forms[1]["source_page"] == 4

    def test_ignores_pages_without_marker(self):
        pages = ["본문 내용", "다른 본문", "서식1에 대한 설명이 본문 중간에 나옴"]
        assert find_form_pages(pages) == []


class TestFindChecklistPage:
    def test_finds_page_by_section_title_in_first_line(self):
        pages = ["1 |  | 공고 개요\n내용", "4 제출서류\n<시군 제출 서류>\n..."]
        result = find_checklist_page(pages, "제출서류")
        assert result == pages[1]

    def test_returns_none_when_not_found(self):
        pages = ["1 |  | 공고 개요\n내용"]
        assert find_checklist_page(pages, "제출서류") is None


class TestSplitChecklistItems:
    def test_splits_on_submitter_markers(self):
        text = (
            "4 제출서류\n<시군 제출 서류>\n□ 필수 서류\n"
            "(외국인 본인) 신청서 제출\n"
            "(현재 근무처) 사업자등록증 사본 제출"
        )
        items = split_checklist_items(text)
        assert items == [
            "(외국인 본인) 신청서 제출",
            "(현재 근무처) 사업자등록증 사본 제출",
        ]

    def test_header_text_before_first_marker_is_dropped(self):
        text = "4 제출서류\n<시군 제출 서류>\n□ 필수 서류\n(외국인 본인) 신청서 제출"
        items = split_checklist_items(text)
        assert len(items) == 1
        assert "필수 서류" not in items[0]


class TestBuildDraftRows:
    def test_fills_only_mechanically_safe_fields(self):
        forms = [
            {"form_number": "1", "label": "제목", "source_page": 13, "raw_text": "원문..."},
        ]
        rows = build_draft_rows(forms, FIELDNAMES)

        assert len(rows) == 1
        row = rows[0]
        assert row["form_id"] == "서식1"
        assert row["source_page"] == "13"
        assert row["raw_text"] == "원문..."
        assert row["notes"] == "사람이 원문을 읽고 채워야 함 - 자동 채움 안 됨"
        # 사람이 직접 읽고 판단해야 하는 필드는 자동으로 채우지 않는다
        assert row["form_name"] == ""
        assert row["filled_by"] == ""
        assert row["signer"] == ""
