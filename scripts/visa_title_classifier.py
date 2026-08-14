"""공고 HWPX 문서 제목에서 visa_code와 회차를 판별하고, D_visa_requirements
자동화의 처리 대상인지 라우팅을 결정한다.

PDF로 변환한 버전은 문장 안에 강조로 삽입된 숫자(공고 차수, 나이·연수 기준값 등)가
벡터 도형/이미지로 내보내져 텍스트 레이어에서 통째로 빠지는 문제가 있어(실측 결과
"모집 공고(12차)"가 "모집 공고 차"로 추출됨), 원본 HWPX를 직접 입력으로 쓴다.
HWPX는 XML 기반이라 이 문제가 없다(scripts/extract_hwpx.py로 검증 완료).

사용법: uv run python scripts/visa_title_classifier.py <HWPX경로>
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

from extract_hwpx import extract_section_texts

# 키워드 -> visa_code. 실제 F-4-R 12차 공고문 붙임1(허가조건 안내문)에 나온
# "지역특화형 우수인재(F-2-R)"/"지역특화형 숙련기능인력(E-7-4R)"/
# "지역특화형 재외동포(F-4-R)" 표기를 근거로 삼는다.
VISA_CODE_KEYWORDS = {
    "외국국적동포": "F-4-R",
    "우수인재": "F-2-R",
    "숙련기능인력": "E-7-4R",
    "K-유학생 광역형": "D-2-GWANGYEOK",
    "광역형": "D-2-GWANGYEOK",  # "K-유학생 광역형" 표현이 안 나오는 경우 대비한 완화 매칭
}

# D_visa_requirements(이 자동화)가 갱신 대상으로 삼는 visa_code.
# E-7-4R은 기존 B_E-7-4R 전용 스키마를 계속 쓰기로 했으므로 여기서 제외한다
# (extraction/D_visa_requirements/README.md "마스터 레코드 수명주기" 참고).
IN_SCOPE_VISA_CODES = {"F-2-R", "F-4-R", "D-2-GWANGYEOK"}

# visa_code는 판별됐지만 이 자동화가 아니라 다른 기존 폴더가 처리 대상인 경우.
KNOWN_OUT_OF_SCOPE_TARGETS = {
    "E-7-4R": "extraction/B_E-7-4R/ (기존 전용 스키마 - 이 자동화 대상 아님, 기존 프로세스로 처리)",
}

ROUND_PATTERN = re.compile(r"\((\d+)\s*차\)")  # 본문 표기: "모집 공고(12차)"


@dataclass
class NoticeClassification:
    visa_code: str | None
    notice_round: int | None
    target: str  # "D_visa_requirements" / 기존 폴더 설명 / "UNKNOWN"
    in_scope: bool
    reason: str
    title_snippet: str


def extract_full_text(hwpx_path: Path) -> str:
    """HWPX 내 모든 section 텍스트를 이어붙인 전체 원문을 반환한다."""
    return "\n".join(extract_section_texts(hwpx_path))


def classify_visa_code(text: str) -> str | None:
    """텍스트에서 키워드를 찾아 visa_code를 반환한다.

    서로 다른 키워드가 동시에 매칭되면(문서가 여러 비자를 함께 다룬다는 뜻,
    예: 붙임1 허가조건 안내문은 F-2-R/E-7-4R/F-4-R을 전부 언급함) 첫 등장
    위치가 가장 이른 키워드를 채택한다 - 공고문 제목/공고개요는 항상 문서
    맨 앞에 나오고, 다른 비자유형에 대한 참고 언급은 뒤쪽(붙임 등)에 나오기
    때문이다.
    """
    positions = {
        code: text.find(keyword)
        for keyword, code in VISA_CODE_KEYWORDS.items()
        if keyword in text
    }
    if not positions:
        return None
    return min(positions, key=positions.get)


TITLE_SNIPPET_WINDOW = 40  # "모집 공고" 앞뒤로 몇 글자를 보여줄지


def _pick_title_snippet(text: str) -> str:
    """사람이 눈으로 훑어볼 때 쓸 제목 조각을 고른다.

    HWPX 추출 텍스트는 문단 사이에 줄바꿈이 거의 없어(extract_hwpx.py가 원문
    구조를 그대로 이어붙임) 줄 단위로 자르면 문서 앞부분 전체가 한 줄로 잡힌다.
    그래서 "모집 공고" 주변 일부만 잘라서 보여준다.
    """
    marker = "모집 공고"
    index = text.find(marker)
    if index == -1:
        stripped = text.strip()
        return stripped[: TITLE_SNIPPET_WINDOW * 2].strip()
    start = max(0, index - TITLE_SNIPPET_WINDOW)
    end = index + len(marker) + TITLE_SNIPPET_WINDOW
    return text[start:end].strip()


def extract_notice_round(text: str) -> int | None:
    """텍스트에서 '(N차)' 표기를 찾아 회차 숫자를 반환한다."""
    match = ROUND_PATTERN.search(text)
    return int(match.group(1)) if match else None


def classify_notice(hwpx_path: Path) -> NoticeClassification:
    """HWPX 전체 텍스트를 읽어 visa_code/notice_round/라우팅 대상을 판별한다."""
    text = extract_full_text(hwpx_path)
    visa_code = classify_visa_code(text)
    notice_round = extract_notice_round(text)
    snippet = _pick_title_snippet(text)

    if visa_code is None:
        return NoticeClassification(
            visa_code=None,
            notice_round=notice_round,
            target="UNKNOWN",
            in_scope=False,
            reason="문서에서 비자유형 키워드를 찾지 못함 - 사람 확인 필요",
            title_snippet=snippet,
        )

    if visa_code in KNOWN_OUT_OF_SCOPE_TARGETS:
        return NoticeClassification(
            visa_code=visa_code,
            notice_round=notice_round,
            target=KNOWN_OUT_OF_SCOPE_TARGETS[visa_code],
            in_scope=False,
            reason=f"{visa_code}은(는) 기존 전용 폴더로 처리하는 비자유형이라 이 자동화 대상이 아님",
            title_snippet=snippet,
        )

    if visa_code not in IN_SCOPE_VISA_CODES:
        return NoticeClassification(
            visa_code=visa_code,
            notice_round=notice_round,
            target="UNKNOWN",
            in_scope=False,
            reason=f"{visa_code}은(는) 이 자동화의 처리 대상 목록에 없음 - 사람 확인 필요",
            title_snippet=snippet,
        )

    if notice_round is None:
        return NoticeClassification(
            visa_code=visa_code,
            notice_round=None,
            target="D_visa_requirements",
            in_scope=False,
            reason="visa_code는 판별했으나 문서에서 회차(N차) 표기를 찾지 못함 - 사람 확인 필요",
            title_snippet=snippet,
        )

    return NoticeClassification(
        visa_code=visa_code,
        notice_round=notice_round,
        target="D_visa_requirements",
        in_scope=True,
        reason="",
        title_snippet=snippet,
    )


def main() -> None:
    """CLI 진입점: HWPX 경로를 받아 분류 결과를 JSON으로 출력한다."""
    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8")  # Windows cp949 콘솔에서 한글/특수문자 출력 오류 방지

    parser = argparse.ArgumentParser(description="공고 HWPX 문서에서 visa_code/회차/처리대상 판별")
    parser.add_argument("hwpx_path", type=Path, help="분류할 HWPX 경로")
    args = parser.parse_args()

    result = classify_notice(args.hwpx_path)
    print(json.dumps(asdict(result), ensure_ascii=False, indent=2))

    if not result.in_scope:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
