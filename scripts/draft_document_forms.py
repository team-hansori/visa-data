"""공고문 PDF에서 【서식N】 페이지와 제출서류 체크리스트를 찾아 document_forms.csv 초안을 만든다.

이 공고문은 서식이 별도 파일이 아니라 공고문 PDF 안에 페이지로 포함돼 있고,
각 서식 페이지는 항상 '【서식N】제목' 형태로 시작한다. 이 패턴으로 서식 페이지를
찾아 form_id/source_page/raw_text를 기계적으로 채우고, form_name/filled_by/
submitted_by/submission_target/signer/required_attachments/is_mandatory는
사람이 원문을 읽고 판단해야 해서 빈 값으로 남긴다(draft_requirements.py와 같은 원칙).

제출서류 체크리스트 섹션(예: '4 제출서류')은 번호 기호(①②③...)가 아니라
'(외국인 본인)'/'(현재 근무처)' 같은 제출자 표시로 항목이 시작해서, 이 표시를
기준으로 따로 나눠 참고용 텍스트 파일로 저장한다. 이 섹션은 서식 번호 참조가
굵은 글씨라 텍스트 추출에서 누락되는 경우가 있어(#5), 서식 번호 매칭은 사람이
원문과 대조해야 한다.

사용법: uv run python scripts/draft_document_forms.py <PDF경로> <기준CSV경로> [제출서류섹션제목]
"""

from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path

from scripts.extract_pdf import extract_page_texts

FORM_PAGE_PATTERN = re.compile(r"^【서식([^】]+)】\s*(.*)")
CHECKLIST_ITEM_PATTERN = re.compile(r"(?=\((외국인 본인|현재 근무처)\))")
SECTION_HEADER_PATTERN = re.compile(r"<[^>]+>")
DEFAULT_CHECKLIST_SECTION_TITLE = "제출서류"
NEEDS_REVIEW_NOTE = "사람이 원문을 읽고 채워야 함 - 자동 채움 안 됨"


def find_form_pages(page_texts: list[str]) -> list[dict]:
    """'【서식N】제목'으로 시작하는 페이지를 찾아 서식 번호·제목·페이지 번호·원문을 뽑는다."""
    forms = []
    for page_number, text in enumerate(page_texts, start=1):
        stripped = text.strip()
        match = FORM_PAGE_PATTERN.match(stripped)
        if not match:
            continue
        forms.append(
            {
                "form_number": match.group(1),
                "label": match.group(2).strip(),
                "source_page": page_number,
                "raw_text": text.strip(),
            }
        )
    return forms


def find_checklist_page(page_texts: list[str], section_title: str) -> str | None:
    """제출서류 체크리스트가 있는 페이지 원문을 찾아 반환한다(없으면 None)."""
    for text in page_texts:
        if section_title in text.split("\n", 1)[0]:
            return text
    return None


def truncate_before_next_section(text: str) -> str:
    """체크리스트 시작 표시(예: <시군 제출 서류>) 다음에 '<...>' 형태의 다른 섹션 헤더가
    있으면 그 앞까지만 남긴다. 이걸 안 하면 뒤에 오는 다른 섹션(예: <법무부 제출 서류>)의
    텍스트가 마지막 항목 끝에 그대로 붙어버린다."""
    matches = list(SECTION_HEADER_PATTERN.finditer(text))
    if len(matches) < 2:
        return text
    return text[: matches[-1].start()]


def split_checklist_items(checklist_text: str) -> list[str]:
    """'(외국인 본인)'/'(현재 근무처)' 표시를 기준으로 체크리스트를 항목별로 나눈다."""
    truncated = truncate_before_next_section(checklist_text)
    chunks = CHECKLIST_ITEM_PATTERN.split(truncated)
    return [chunk.strip() for chunk in chunks if chunk.strip().startswith(("(외국인", "(현재"))]


def read_fieldnames(template_csv_path: Path) -> list[str]:
    """기존 document_forms.csv의 헤더 줄을 읽어 컬럼 목록으로 반환한다."""
    with template_csv_path.open(encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        return next(reader)


def build_draft_rows(forms: list[dict], fieldnames: list[str], source_document: str) -> list[dict]:
    """서식 페이지 목록을 document_forms.csv 초안 행(dict) 리스트로 변환한다."""
    rows = []
    for form in forms:
        row = {name: "" for name in fieldnames}
        row.update(
            {
                "form_id": f"서식{form['form_number']}",
                "raw_text": form["raw_text"],
                "source_document": source_document,
                "source_page": str(form["source_page"]),
                "notes": NEEDS_REVIEW_NOTE,
            }
        )
        rows.append(row)
    return rows


def write_draft_csv(rows: list[dict], fieldnames: list[str], output_path: Path) -> None:
    """초안 행들을 CSV 파일로 저장한다."""
    with output_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    """CLI 진입점: PDF와 기준 CSV 경로를 받아 document_forms.csv 초안과 체크리스트 참고 파일을 만든다."""
    parser = argparse.ArgumentParser(description="공고문 PDF에서 document_forms.csv 초안 생성")
    parser.add_argument("pdf_path", type=Path, help="서식이 포함된 공고문 PDF 경로")
    parser.add_argument(
        "template_csv", type=Path, help="컬럼 구조를 따라갈 기존 document_forms.csv 경로"
    )
    parser.add_argument(
        "checklist_section_title",
        nargs="?",
        default=DEFAULT_CHECKLIST_SECTION_TITLE,
        help=f"제출서류 체크리스트 섹션 제목 (기본값: '{DEFAULT_CHECKLIST_SECTION_TITLE}')",
    )
    args = parser.parse_args()

    page_texts = extract_page_texts(args.pdf_path)
    print(f"PDF 총 {len(page_texts)}페이지 로드됨")

    forms = find_form_pages(page_texts)
    print(f"서식 페이지 {len(forms)}개 발견: {', '.join('서식' + f['form_number'] for f in forms)}")

    fieldnames = read_fieldnames(args.template_csv)
    rows = build_draft_rows(forms, fieldnames, source_document=args.pdf_path.stem)

    output_path = args.template_csv.with_name(f"_draft_{args.template_csv.name}")
    write_draft_csv(rows, fieldnames, output_path)
    print(f"{len(rows)}행 생성됨 -> {output_path}")

    checklist_text = find_checklist_page(page_texts, args.checklist_section_title)
    if checklist_text is None:
        print(f"'{args.checklist_section_title}' 섹션을 못 찾음 - 체크리스트 참고 파일 생성 건너뜀")
        return

    items = split_checklist_items(checklist_text)
    checklist_output_path = args.template_csv.with_name("_draft_document_forms_checklist.txt")
    checklist_output_path.write_text("\n\n".join(items), encoding="utf-8")
    print(
        f"제출서류 체크리스트 {len(items)}항목 -> {checklist_output_path} "
        "(서식 번호는 굵은 글씨라 텍스트 추출에서 빠질 수 있음 - 원문 대조 필요)"
    )


if __name__ == "__main__":
    main()
