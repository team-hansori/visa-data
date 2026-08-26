# risk_routing_table 정규화 및 NULL 처리 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `reference/risk_routing_table.csv`의 실제 데이터 중복(갱신 이상 위험)과 컬럼별로 제각각인 NULL/미확인 표기 방식을 정리하고, `reference/` 폴더 테이블을 FK 검증 스크립트 대상에 포함시킨다.

**Architecture:** CSV 스키마 변경(행 병합, 컬럼 정리) + README 문서화 + `scripts/validate_fk_integrity.py` 확장. 코드 실행 로직(앱)이 아직 없으므로 "테스트"는 각 CSV의 구조적 정합성을 검증하는 스크립트 실행으로 대체한다.

**Tech Stack:** Python 3.11+ (표준 `csv` 모듈), 기존 `scripts/validate_fk_integrity.py` 패턴 재사용

**Spec status:** 이 문서는 GitHub 이슈 #45의 구현 기준(spec)이다. 아래 진단 근거와 전역 제약을 포함한 각 태스크의 파일·인터페이스·검증 절차를 모두 충족해야 한다. 구현 중 새 사실 확인이 필요하면 값을 추정하지 말고 이슈 또는 후속 PR에서 결정한다.

## Global Constraints

- 원본 PDF/근거 문서를 재조사하지 않고 이미 CSV에 존재하는 정보만으로 재구조화한다 — 새로운 사실 확인이 필요한 값(예: 근로복지공단 지사 직통번호)은 추측하지 않고 기존 `notes` 문구를 유지한다.
- 파이프(`|`) 구분자는 `visa_requirements.csv.target_region`에서 이미 쓰이는 저장소 전역 컨벤션이므로 유지한다 — 브릿지 테이블로 쪼개지 않는다. 정규화 대상은 "다치 속성"이 아니라 **행 단위로 반복된 동일 텍스트**(진짜 갱신 이상 위험)와 **컬럼별로 다른 미확인 표기 방식**이다.
- 모든 CSV 수정은 기존 컬럼 순서·헤더 컨벤션(`extraction/B_E-7-4R/README.md`에 정의된 근거표 원칙과 동일한 정신)을 따른다: 출처 문서·페이지 근거 보존, 확인 안 된 값은 추측 금지.
- 커밋/푸시/PR은 사용자가 명시적으로 요청하기 전까지 하지 않는다 (`CLAUDE.md` 원칙).

## 진단 근거 (브레인스토밍 결과 요약)

1. **실제 데이터 중복**: `INDUSTRIAL_ACCIDENT` 카테고리의 2행(근로복지공단 청주지사/충주지사)이 `external_phone`(1588-0075), `external_url`, `escalation_message_template`, `notes`를 문자 그대로 반복 보유 — `notes`에 "지사 직통번호는 확인되지 않음"이라고 명시되어 있어 애초에 지사 구분이 무의미함.
2. **행 단위 반복되는 안내 문구**: `escalation_message_template`의 앞부분 boilerplate("~은 저희가 직접 해결해드릴 수 없는 문제입니다")가 `keyword_category`에 종속된 값인데 지역별 행마다 전체 문자열이 복사됨 — `WAGE_ARREARS` 2행은 이 복사 과정에서 실제로 내용이 갈라짐(충주지청 행에만 지역대표번호 043-840-4000 포함).
3. **컬럼별로 다른 미확인 표기**: `source_page`는 미확인 값을 리터럴 문자열 `"N/A"`로 표기하는 반면, 다른 컬럼(`target_agency_category`, `valid_to` 등)은 빈 문자열을 쓴다. `external_region_scope`의 "빈칸=미확인 vs `NATIONWIDE`=확인된 전국단위" 구분은 `reference/README.md` 산문에만 있고 표로 정리되어 있지 않다.
4. **저장소 전역 구분자 불일치**: `agency_contacts.csv` row 36(`region` 컬럼)이 `"옥천,영동"`처럼 쉼표를 쓰는데, 같은 다중 지역 표현이 `visa_requirements.csv.target_region`과 `risk_routing_table.csv.external_region_scope`에서는 파이프(`|`)를 쓴다 — 저장소 전역 컨벤션에서 벗어난 행.
5. **FK 검증 공백**: `scripts/validate_fk_integrity.py`는 `extraction/D_visa_requirements/` 테이블만 검사하고 `reference/` 폴더(`agency_contacts.csv`, `risk_routing_table.csv`)는 대상 밖 — `target_agency_category` ↔ `agency_contacts.category_minor`, `applies_to_visa_code`(파이프 분리 후) ↔ `visa_requirements.visa_code` 참조가 깨져도 잡아내지 못함.

---

### Task 1: `agency_contacts.csv` 구분자 불일치 수정

**Files:**
- Modify: `reference/agency_contacts.csv:36`
- Test: `scripts/validate_reference_delimiters.py` (신규, 이 태스크에서 생성)

**Interfaces:**
- Produces: `scripts/validate_reference_delimiters.py`의 `find_comma_in_pipe_columns(path: Path, columns: list[str]) -> list[tuple[int, str, str]]` — (행 번호, 컬럼명, 값) 리스트를 반환. Task 5에서 `validate_fk_integrity.py`에 흡수됨.

- [ ] **Step 1: 쉼표 구분자를 찾아내는 검증 스크립트를 먼저 작성한다 (실패하는 상태로)**

`scripts/validate_reference_delimiters.py` 생성:

```python
"""
reference/ CSV의 다중값 컬럼이 저장소 전역 파이프(|) 구분자 컨벤션을
따르는지 검사한다. 쉼표(,)로 여러 값을 나열한 셀이 있으면 실패로 표시한다.

사용법: uv run python scripts/validate_reference_delimiters.py
"""

from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

REFERENCE_DIR = Path("reference")

# {파일명: [다중값을 담을 수 있는 컬럼명]}
MULTI_VALUE_COLUMNS: dict[str, list[str]] = {
    "agency_contacts.csv": ["region"],
    "risk_routing_table.csv": ["applies_to_visa_code", "external_region_scope"],
}

# "042-220-2001~2,4" 같은 전화번호 내선 표기는 다중값이 아니므로 제외
COMMA_IN_VALUE_RE = re.compile(r"[가-힣A-Za-z0-9]+,[가-힣A-Za-z0-9]+")


def find_comma_in_pipe_columns(
    path: Path, columns: list[str]
) -> list[tuple[int, str, str]]:
    """지정된 컬럼에서 쉼표로 여러 값을 나열한 셀을 찾는다."""
    violations: list[tuple[int, str, str]] = []
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row_num, row in enumerate(reader, start=2):
            for column in columns:
                value = row.get(column, "")
                if COMMA_IN_VALUE_RE.search(value):
                    violations.append((row_num, column, value))
    return violations


def main() -> int:
    all_violations: list[str] = []
    for filename, columns in MULTI_VALUE_COLUMNS.items():
        path = REFERENCE_DIR / filename
        for row_num, column, value in find_comma_in_pipe_columns(path, columns):
            all_violations.append(
                f"{path}:{row_num} 컬럼 '{column}' — 쉼표 구분자 발견 (파이프 사용 필요): {value!r}"
            )

    if all_violations:
        print("파이프(|) 구분자 컨벤션 위반:")
        for line in all_violations:
            print(f"  - {line}")
        return 1

    print("OK: 모든 다중값 컬럼이 파이프 구분자를 사용합니다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: 스크립트를 실행해 현재 위반이 잡히는지 확인한다**

Run: `uv run python scripts/validate_reference_delimiters.py`
Expected: 종료 코드 1, `reference/agency_contacts.csv:36 컬럼 'region' — 쉼표 구분자 발견 (파이프 사용 필요): '옥천,영동'` 출력

- [ ] **Step 3: `agency_contacts.csv` row 36을 파이프 구분자로 수정한다**

`reference/agency_contacts.csv:36`의 `region` 컬럼 값을 `"옥천,영동"` → `옥천|영동`으로 수정 (다른 컬럼은 그대로 유지):

```
41739526-bc52-4bfe-a9c2-ea095d7f7c3f,FOREIGN_EMPLOYMENT_SUPPORT,VISA_STATUS_CHANGE,옥천|영동,대전출입국·외국인사무소 관리과,,"042-220-2001~2,4",,FOREIGN_WORKER,true,2026-01-01,2026-12-31,충청북도_외국인정책_지원사업_안내_2026.pdf p.5,5,2026-08-12
```

(전화번호 컬럼의 `"042-220-2001~2,4"`는 내선번호 표기이므로 정규식이 무시하도록 이미 설계됨 — 건드리지 않는다)

- [ ] **Step 4: 스크립트를 다시 실행해 통과하는지 확인한다**

Run: `uv run python scripts/validate_reference_delimiters.py`
Expected: 종료 코드 0, `OK: 모든 다중값 컬럼이 파이프 구분자를 사용합니다.`

- [ ] **Step 5: 커밋**

```bash
git add reference/agency_contacts.csv scripts/validate_reference_delimiters.py
git commit -m "fix: agency_contacts.csv 다중 지역 표기를 파이프 구분자로 통일"
```

---

### Task 2: 근로복지공단 중복 행(INDUSTRIAL_ACCIDENT) 병합

**Files:**
- Modify: `reference/risk_routing_table.csv` (INDUSTRIAL_ACCIDENT 2행 → 1행)
- Modify: `reference/README.md` (병합 사유 문서화)

**Interfaces:**
- Consumes: Task 1에서 만든 `scripts/validate_reference_delimiters.py`의 파이프 컨벤션 (병합된 행의 `external_region_scope`는 11개 시군 전체를 파이프로 나열)

- [ ] **Step 1: 두 행이 지역을 제외하고 완전히 동일한 값임을 확인한다**

Run: `python -c "import csv; rows=[r for r in csv.DictReader(open('reference/risk_routing_table.csv', encoding='utf-8-sig')) if r['keyword_category']=='INDUSTRIAL_ACCIDENT']; a,b=rows; diff=[k for k in a if a[k]!=b[k]]; print(diff)"`
Expected: `['routing_id', 'external_agency_name', 'external_region_scope']` — 이 세 컬럼만 다르고 나머지(전화, URL, 메시지, notes 등)는 동일함을 확인

- [ ] **Step 2: 두 행을 하나로 병합한다**

`reference/risk_routing_table.csv`의 `INDUSTRIAL_ACCIDENT` 2행(현재 4번째·5번째 데이터 행)을 아래 1행으로 교체한다. `routing_id`는 두 UUID 중 먼저 등장한 `4d137caf-132a-4610-8075-10f63ec0ae5a`를 유지하고, `external_agency_name`에서 "청주지사/충주지사" 구분을 제거하며, `external_region_scope`를 11개 시군 전체로 확장한다:

```
4d137caf-132a-4610-8075-10f63ec0ae5a,INDUSTRIAL_ACCIDENT,FOREIGN_WORKER,,EXTERNAL,,근로복지공단,청주|진천|괴산|증평|보은|옥천|영동|충주|제천|음성|단양,1588-0075,https://www.kcomwel.or.kr/,업무상 재해(산재)는 저희가 직접 판단해드릴 수 없는 문제입니다. 근로복지공단(1588-0075)으로 연락해 산재 신청 절차를 안내받으세요.,"1588-0075는 근로복지공단 전국 콜센터 번호로 관할 지사 구분 없이 동일하게 연결됨 — 청주지사·충주지사 직통번호는 확인되지 않아 지사 구분을 제거하고 전 시군 공통 행으로 병합함(기존 routing_id: eff1af73-7473-497d-9e2b-e10edd36b4ac는 폐기).",2026-08-15,,"웹서칭 종합(근로복지공단 지사 현황, 4대사회보험정보연계센터)",N/A,2026-08-15
```

- [ ] **Step 3: 파일에 남은 행 수를 확인한다**

Run: `python -c "import csv; print(sum(1 for _ in csv.DictReader(open('reference/risk_routing_table.csv', encoding='utf-8-sig'))))"`
Expected: `6` (기존 7행에서 1행 줄어듦)

- [ ] **Step 4: `reference/README.md`의 설계 원칙에 병합 사유를 추가한다**

`reference/README.md`의 "## \`risk_routing_table.csv\` 설계 원칙" 목록 마지막에 항목 추가:

```markdown
- **동일 연락처를 공유하는 지사는 행을 합친다**: `external_phone`·`external_url`·`escalation_message_template`·`notes`가 지역과 무관하게 완전히 동일하다면(예: 근로복지공단 전국 콜센터 1588-0075) 지사별로 행을 나누지 않고 `external_region_scope`에 해당 지역을 모두 나열한 1행으로 합친다 — 안내 문구 수정 시 여러 행을 동시에 고쳐야 하는 갱신 이상(update anomaly)을 막기 위함.
```

- [ ] **Step 5: 커밋**

```bash
git add reference/risk_routing_table.csv reference/README.md
git commit -m "fix: 근로복지공단 중복 행(청주지사/충주지사) 병합"
```

---

### Task 3: `escalation_message_template` boilerplate를 keyword_category 단위로 분리

**Files:**
- Create: `reference/risk_keyword_messages.csv`
- Modify: `reference/risk_routing_table.csv` (`escalation_message_template` 컬럼 제거)
- Modify: `reference/README.md`

**Interfaces:**
- Produces: `reference/risk_keyword_messages.csv`의 스키마 `keyword_category, resolution_type, message_stem, source_document, source_page, last_verified_at` — Task 5의 FK 검증에서 `risk_routing_table.keyword_category + resolution_type` 조합이 이 테이블에 존재하는지 검사한다.

- [ ] **Step 1: 현재 6행(Task 2 이후)의 `escalation_message_template`에서 boilerplate와 지역별 supplement를 분리해 표로 정리한다**

각 `keyword_category`(현재 5종: WAGE_ARREARS, INDUSTRIAL_ACCIDENT, ASSAULT, ILLEGAL_EMPLOYMENT, RESIDENCE_CONDITION_VIOLATION)의 공통 boilerplate 문장을 추출:

| keyword_category | message_stem (공통 부분) |
|---|---|
| WAGE_ARREARS | 임금체불은 저희가 직접 해결해드릴 수 없는 문제입니다. 고용노동부 고객상담센터(국번없이 1350)로 연락해 진정 절차를 안내받으세요. |
| INDUSTRIAL_ACCIDENT | 업무상 재해(산재)는 저희가 직접 판단해드릴 수 없는 문제입니다. 근로복지공단(1588-0075)으로 연락해 산재 신청 절차를 안내받으세요. |
| ASSAULT | 폭행 등 폭력 피해는 저희가 직접 해결해드릴 수 없는 문제입니다. 다누리콜센터(1577-1366, 24시간, 13개 언어)로 연락해 도움을 받으세요. |
| ILLEGAL_EMPLOYMENT | 허가된 체류자격 범위를 벗어난 취업은 체류자격에 영향을 줄 수 있는 문제입니다. 저희가 직접 판단해드릴 수 없으니 관할 출입국·외국인사무소에 문의하시기 바랍니다. |
| RESIDENCE_CONDITION_VIOLATION | 거주지 유지의무 위반(비추천지역 전출, 실거주지 불일치, 타 광역지역 경제활동 등)은 체류자격 취소 사유가 될 수 있는 중요한 문제입니다. 저희가 직접 판단해드릴 수 없으니 관할 출입국·외국인사무소에 문의하시기 바랍니다. |

`WAGE_ARREARS`의 충주지청 행에만 있던 "지역대표 043-840-4000" 문구는 boilerplate가 아니므로 `risk_routing_table.csv`의 `notes` 컬럼으로 옮긴다(이미 해당 행 `notes`에 "지역대표 043-840-4000 사용"이 언급되어 있으므로 중복 없이 흡수됨).

- [ ] **Step 2: `reference/risk_keyword_messages.csv`를 생성한다**

```csv
keyword_category,resolution_type,message_stem,source_document,source_page,last_verified_at
WAGE_ARREARS,EXTERNAL,임금체불은 저희가 직접 해결해드릴 수 없는 문제입니다. 고용노동부 고객상담센터(국번없이 1350)로 연락해 진정 절차를 안내받으세요.,moel.go.kr/local/chungju/introduce/dept/list.do (부서안내 페이지 원문),N/A,2026-08-15
INDUSTRIAL_ACCIDENT,EXTERNAL,업무상 재해(산재)는 저희가 직접 판단해드릴 수 없는 문제입니다. 근로복지공단(1588-0075)으로 연락해 산재 신청 절차를 안내받으세요.,"웹서칭 종합(근로복지공단 지사 현황, 4대사회보험정보연계센터)",N/A,2026-08-15
ASSAULT,EXTERNAL,"폭행 등 폭력 피해는 저희가 직접 해결해드릴 수 없는 문제입니다. 다누리콜센터(1577-1366, 24시간, 13개 언어)로 연락해 도움을 받으세요.",여성가족부/한국건강가정진흥원 다누리콜센터 공식 안내(liveinkorea.kr),N/A,2026-08-15
ILLEGAL_EMPLOYMENT,IN_DOMAIN,허가된 체류자격 범위를 벗어난 취업은 체류자격에 영향을 줄 수 있는 문제입니다. 저희가 직접 판단해드릴 수 없으니 관할 출입국·외국인사무소에 문의하시기 바랍니다.,법무부 하이코리아 외국인 취업정보 온라인 신고제 보도자료(immigration.go.kr),N/A,2026-08-15
RESIDENCE_CONDITION_VIOLATION,IN_DOMAIN,"거주지 유지의무 위반(비추천지역 전출, 실거주지 불일치, 타 광역지역 경제활동 등)은 체류자격 취소 사유가 될 수 있는 중요한 문제입니다. 저희가 직접 판단해드릴 수 없으니 관할 출입국·외국인사무소에 문의하시기 바랍니다.",충북_지혁특화형비자사업_외국국적동포_모집공고_12차.pdf,N/A,2026-08-15
```

- [ ] **Step 3: `risk_routing_table.csv`에서 `escalation_message_template` 컬럼을 제거한다**

헤더에서 `escalation_message_template`을 삭제하고, 각 데이터 행에서 해당 값을 제거한다(값 자체는 Step 2에서 `risk_keyword_messages.csv`로 이관됨). `WAGE_ARREARS` 충주지청 행의 "지역대표 043-840-4000" 문구는 이미 `notes`에 있으므로 별도 이관 불필요.

- [ ] **Step 4: 컬럼 수가 일치하는지 검증한다**

Run: `python -c "import csv; rows=list(csv.reader(open('reference/risk_routing_table.csv', encoding='utf-8-sig'))); print(len(rows[0])); assert all(len(r)==len(rows[0]) for r in rows[1:])"`
Expected: `16` 출력 (기존 17컬럼 - `escalation_message_template` 1개), assert 통과

- [ ] **Step 5: `reference/README.md`에 새 테이블을 문서화한다**

"## 파일" 표에 행 추가:

```markdown
| `risk_keyword_messages.csv` | `risk_routing_table.csv`의 `keyword_category`+`resolution_type`별 공통 안내 문구(boilerplate). 지역별로 반복되던 `escalation_message_template`을 카테고리 단위로 분리해 문구 수정 시 한 곳만 고치면 되도록 함. 실제 발송 메시지는 앱이 `message_stem` + 라우팅 행의 연락처 정보를 조합해 만든다. |
```

- [ ] **Step 6: 커밋**

```bash
git add reference/risk_routing_table.csv reference/risk_keyword_messages.csv reference/README.md
git commit -m "refactor: escalation_message_template boilerplate를 keyword_category 단위로 분리"
```

---

### Task 4: NULL/미확인 표기 통일

**Files:**
- Modify: `reference/risk_routing_table.csv` (`source_page`의 `"N/A"` → 빈 문자열)
- Modify: `reference/README.md`

**Interfaces:**
- Consumes: 없음 (독립 태스크)

- [ ] **Step 1: `source_page`에 남아있는 리터럴 `"N/A"` 값을 확인한다**

Run: `python -c "import csv; rows=list(csv.DictReader(open('reference/risk_routing_table.csv', encoding='utf-8-sig'))); print(sum(1 for r in rows if r['source_page']=='N/A'))"`
Expected: `6` (Task 2 병합 이후 6행 모두 `source_page='N/A'`)

- [ ] **Step 2: `"N/A"`를 빈 문자열로 통일한다**

`reference/risk_routing_table.csv`의 모든 데이터 행에서 `source_page` 컬럼 값 `N/A`를 빈 문자열로 바꾼다(다른 컬럼은 그대로 유지).

- [ ] **Step 3: 변경을 검증한다**

Run: `python -c "import csv; rows=list(csv.DictReader(open('reference/risk_routing_table.csv', encoding='utf-8-sig'))); print(sum(1 for r in rows if r['source_page']=='N/A'))"`
Expected: `0`

- [ ] **Step 4: `reference/README.md`에 NULL 컨벤션 표를 추가한다**

기존 "`external_region_scope`는 NULL과 `NATIONWIDE`를 구분한다" 항목 뒤에 컬럼별 빈칸 의미를 정리한 표를 추가한다:

```markdown

### 빈 칸(NULL) 의미 정리

같은 빈 칸이라도 컬럼에 따라 의미가 다르다 — 아래 표로 명시한다.

| 컬럼 | 빈 칸의 의미 | 명시적 값이 필요한 경우 |
|------|------|------|
| `applies_to_visa_code` | 특정 비자 제한 없음(전체 적용) | 제한이 있으면 파이프로 비자코드 나열 |
| `target_agency_category` | `resolution_type=EXTERNAL`이라 해당 없음 | — (`resolution_type=IN_DOMAIN`이면 항상 채움) |
| `external_agency_name`/`external_region_scope`/`external_phone`/`external_url` | `resolution_type=IN_DOMAIN`이라 해당 없음 | — (`resolution_type=EXTERNAL`이면 항상 채움) |
| `external_region_scope`(EXTERNAL 행 한정) | **사용 금지** — 관할지역 미확인 상태를 빈칸으로 남기지 않는다 | 전국 단일기관이면 `NATIONWIDE`, 특정 지역이면 파이프로 시군 나열 |
| `valid_to` | 종료일 미정(현재 유효) | 종료가 확정되면 날짜 기입 |
| `source_page` | 출처 문서에 페이지 구분이 없음(예: 웹페이지 종합) | 페이지 번호가 있으면 숫자 기입 — `"N/A"` 같은 리터럴 문자열 사용 금지 |
```

- [ ] **Step 5: 커밋**

```bash
git add reference/risk_routing_table.csv reference/README.md
git commit -m "docs: risk_routing_table 빈칸(NULL) 의미를 컬럼별로 명문화, source_page N/A 리터럴 제거"
```

---

### Task 5: `scripts/validate_fk_integrity.py`를 `reference/` 테이블까지 확장

**Files:**
- Modify: `scripts/validate_fk_integrity.py`
- Test: 스크립트 자체 실행 결과로 검증 (별도 테스트 파일 없음 — 기존 파일도 동일한 패턴)

**Interfaces:**
- Consumes: `TableSpec` dataclass(`scripts/validate_fk_integrity.py:29`의 `path`, `pk`, `fks`, `required_columns` 필드), `default_tables()` 함수 시그니처
- Produces: `reference_tables()` 함수 — `default_tables()`와 동일한 반환 타입(`list[TableSpec]`)을 반환하며 `main()`에서 두 리스트를 합쳐 검사

- [ ] **Step 1: 현재 스크립트의 `main()` 구조와 FK 검사 로직을 확인한다**

Run: `python -c "import ast; tree=ast.parse(open('scripts/validate_fk_integrity.py', encoding='utf-8').read()); print([n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)])"`
Expected: 함수 목록에 `default_tables`, `main`이 포함된 리스트 출력 (기존 구조 파악용)

- [ ] **Step 2: `reference/` 폴더 검사 대상을 정의하는 `reference_tables()` 함수를 추가한다**

`scripts/validate_fk_integrity.py` 상단 `D_DIR = Path("extraction/D_visa_requirements")` 아래에 상수 추가:

```python
REFERENCE_DIR = Path("reference")
```

`default_tables()` 함수 뒤에 새 함수 추가:

```python
def reference_tables(
    base_dir: Path = REFERENCE_DIR, d_dir: Path = D_DIR
) -> list[TableSpec]:
    """reference/ 폴더의 서비스·라우팅 테이블 구성. 새 참조 테이블이 생기면 여기에 추가한다."""
    agency_contacts = base_dir / "agency_contacts.csv"
    risk_keyword_messages = base_dir / "risk_keyword_messages.csv"
    visa_requirements = d_dir / "visa_requirements.csv"
    return [
        TableSpec(agency_contacts, pk="agency_id"),
        TableSpec(
            risk_keyword_messages,
            pk=None,  # keyword_category+resolution_type 복합키라 단일 PK 검사는 건너뜀
        ),
        TableSpec(
            base_dir / "risk_routing_table.csv",
            pk="routing_id",
            fks={"target_agency_category": agency_contacts},
        ),
    ]
```

- [ ] **Step 3: `target_agency_category` FK 검사가 `category_minor` 컬럼을 참조하도록 FK 검사 로직을 확인한다**

기존 `validate_fk_integrity.py`의 FK 검사 함수를 읽고(파일 60번째 줄 이후), FK 컬럼명과 부모 테이블의 PK 컬럼명이 다를 때(`target_agency_category` → `agency_contacts.category_minor`, PK는 `agency_id`)의 처리 방식을 확인한다. 기존 코드가 "FK 컬럼명 = 부모 PK 컬럼명"만 지원한다면, `fks` 딕셔너리 값을 `(부모 테이블 경로, 부모 조회 컬럼명)` 튜플로 받도록 `TableSpec.fks` 타입과 검사 함수를 확장한다:

```python
fks: dict[str, tuple[Path, str]] = field(default_factory=dict)  # {FK 컬럼명: (부모 테이블 경로, 부모 조회 컬럼명)}
```

이에 맞춰 `default_tables()`와 `reference_tables()`의 기존 `fks={"visa_id": visa_requirements}` 형태도 `fks={"visa_id": (visa_requirements, "visa_id")}`로 함께 갱신한다.

- [ ] **Step 4: `main()`에서 `default_tables()`와 `reference_tables()`를 합쳐 검사하도록 수정한다**

`main()` 함수에서 `tables = default_tables()`로 되어 있던 부분을 찾아:

```python
tables = default_tables() + reference_tables()
```

로 교체한다.

- [ ] **Step 5: 스크립트를 실행해 통과하는지 확인한다**

Run: `uv run python scripts/validate_fk_integrity.py`
Expected: 종료 코드 0, `reference/risk_routing_table.csv`의 `target_agency_category` 값(`VISA_STATUS_CHANGE`)이 `agency_contacts.csv`의 `category_minor`에 존재함을 확인하는 메시지 포함

- [ ] **Step 6: 일부러 깨뜨려서 검사가 실제로 실패를 잡아내는지 확인한다**

`reference/risk_routing_table.csv`의 아무 `target_agency_category` 값을 `NONEXISTENT_CATEGORY`로 임시 변경 후 재실행:

Run: `uv run python scripts/validate_fk_integrity.py`
Expected: 종료 코드 1, `NONEXISTENT_CATEGORY`가 `agency_contacts.category_minor`에 없다는 에러 메시지

변경을 되돌린다: `git checkout -- reference/risk_routing_table.csv`

- [ ] **Step 7: 커밋**

```bash
git add scripts/validate_fk_integrity.py
git commit -m "test: validate_fk_integrity.py를 reference/ 테이블까지 확장"
```

---

## Self-Review 메모

- **Spec coverage**: 진단 근거 1~5 모두 Task 1~5에 1:1 매핑됨 (실제 중복→Task2, boilerplate 반복→Task3, 컬럼별 NULL 불일치→Task4, 구분자 불일치→Task1, FK 검증 공백→Task5).
- **Placeholder scan**: 각 Step에 실제 CSV 값·코드·실행 명령을 명시함, "적절히 처리" 류 표현 없음.
- **Type/이름 일관성**: `TableSpec.fks` 타입을 Task 5 Step 3에서 변경하면서 `default_tables()`(기존 함수)의 기존 `fks=` 호출부도 함께 갱신하도록 명시함 — 두 함수가 같은 `TableSpec` 정의를 공유하므로 타입이 어긋나면 기존 D_visa_requirements 검사가 깨짐.
