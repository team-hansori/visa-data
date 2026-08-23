from scripts.classify_review_rows import apply_high_confidence, classify_row, proposed_output_path


def row(**overrides):
    base = {
        "raw_text": "",
        "source_section": "",
        "requirement_type": "",
        "status": "present",
    }
    return {**base, **overrides}


def test_classifies_scoring_rows_separately_from_criteria():
    result = classify_row(row(source_section="자격 요건 > 점수제 심사", raw_text="❍ 평균소득 점수"))

    assert result.review_decision == "reclassified"
    assert result.target_table == "scoring_items"
    assert result.confidence == "high"


def test_classifies_quota_rows():
    result = classify_row(row(raw_text="❍ 모집규모 : 542명"))

    assert result.target_table == "visa_quota_status"
    assert result.review_decision == "reclassified"


def test_classifies_process_rows():
    result = classify_row(row(source_section="추진 체계", raw_text="추천서 발급 신청방법"))

    assert result.target_table == "visa_process_stages"
    assert result.review_decision == "reclassified"


def test_keeps_mixed_process_and_quota_rows_for_manual_review():
    result = classify_row(
        row(
            source_section="추천서 발급 신청방법 및 결과안내",
            raw_text="❍ 추진체계\n수시 공고 · 쿼터 소진시까지 상시접수",
        )
    )

    assert result.review_decision == "needs_review"
    assert result.target_table == "none"
    assert "혼합" in result.reason


def test_keeps_extraction_failures_for_manual_review():
    result = classify_row(row(status="extraction_failed", raw_text="제출서류 표"))

    assert result.review_decision == "needs_review"
    assert result.target_table == "none"


def test_does_not_auto_approve_ambiguous_notice_metadata():
    result = classify_row(
        row(
            requirement_type="unclassified",
            source_section="공고 개요",
            raw_text="❍ 사업내용: 지역특화형 비자 사업",
        )
    )

    assert result.review_decision == "needs_review"
    assert result.target_table == "none"
    assert result.confidence == "low"


def test_classifies_document_requirement_rows_with_submission_and_form_signal():
    result = classify_row(row(raw_text="❍ 제출서류: 서식 8호 작성 후 제출"))

    assert result.review_decision == "reclassified"
    assert result.target_table == "document_requirements"
    assert result.confidence == "high"


def test_classifies_attachment_rows_without_form_word():
    result = classify_row(row(raw_text="❍ 첨부서류 : 사업자등록증 사본 1부"))

    assert result.review_decision == "reclassified"
    assert result.target_table == "document_requirements"
    assert result.confidence == "high"


def test_does_not_auto_classify_form_metadata_mentioning_only_form_word():
    result = classify_row(row(raw_text="서식 8 작성자"))

    assert result.review_decision == "needs_review"
    assert result.target_table == "none"


def test_does_not_auto_classify_signature_field_metadata():
    result = classify_row(row(raw_text="서명란"))

    assert result.review_decision == "needs_review"
    assert result.target_table == "none"


def test_proposed_output_never_overwrites_review_file():
    assert (
        proposed_output_path(__import__("pathlib").Path("_review_current_requirements.csv")).name
        == "_review_current_requirements_proposed.csv"
    )


def test_in_place_application_preserves_manual_fields_and_skips_ambiguous_rows():
    rows = [
        row(
            raw_text="❍ 모집규모 : 542명",
            review_decision="needs_review",
            target_table="none",
            status="present",
            source_page="1",
            review_note="수동 메모",
        ),
        row(
            raw_text="❍ 추진체계\n쿼터 소진시까지 접수",
            source_section="추천서 발급 신청방법 및 결과안내",
            review_decision="needs_review",
            target_table="none",
            status="present",
            source_page="2",
            review_note="혼합 행",
        ),
    ]

    applied = apply_high_confidence(rows)

    assert applied == 1
    assert rows[0]["review_decision"] == "reclassified"
    assert rows[0]["target_table"] == "visa_quota_status"
    assert rows[0]["status"] == "present"
    assert rows[0]["source_page"] == "1"
    assert rows[0]["review_note"] == "수동 메모"
    assert rows[1]["review_decision"] == "needs_review"
    assert rows[1]["target_table"] == "none"
