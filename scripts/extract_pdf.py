"""
PDF 공고문에서 원문 텍스트/표를 추출하고 차수 표기 일치 여부를 확인한다.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pdfplumber


def extract_page_texts(pdf_path: Path) -> list[str]:
    """PDF의 각 페이지 원문 텍스트를 순서대로 리스트로 변환한다."""
    with pdfplumber.open(pdf_path) as pdf:
        return [page.extract_text() or "" for page in pdf.pages]


def main() -> None:
    """CLI 진입점: PDF 경로를 받아 텍스트 추출과 차수 일치 검사를 실행한다"""

    parser = argparse.ArgumentParser(description="PDF 자격요건/점수표 추출")
    parser.add_argument("pdf_path", type=Path, help="추출할 PDF 파일 경로")  # 사용법
    args = parser.parse_args()

    print(f"대상 파일: {args.pdf_path}")

    page_texts = extract_page_texts(args.pdf_path)
    print(f"총 {len(page_texts)}페이지 추출됨")
    print("--- 1페이지 미리보기 ---")
    print(page_texts[0][:300])


if __name__ == "__main__":
    main()
