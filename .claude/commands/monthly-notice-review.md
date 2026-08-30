공고 HWPX 문서 하나를 받아 `extraction/D_visa_requirements/` 4개 테이블(+`change_history.csv`) 반영 여부를 검토하는 리뷰 리포트를 만든다. **이 커맨드는 CSV를 직접 수정하지 않는다 — 리포트만 생성한다.** 사용자가 인자로 HWPX 파일 경로를 준다(예: `/monthly-notice-review data/raw/F-4-R/충북_..._13차.hwpx`). 인자가 없으면 사용자에게 경로를 물어본다.

## 0단계 — 사전 확인

- 파일이 `.hwpx` 확장자가 맞는지 확인한다. `.pdf`나 `.hwp`(구버전 바이너리)면 중단하고, HWPX 원본을 요청한다 — 이 파이프라인은 PDF 변환 과정에서 강조 숫자(연령·연수 기준값 등)가 벡터 도형/이미지로 빠지는 문제 때문에 HWPX만 신뢰한다(`scripts/visa_title_classifier.py` 상단 주석 참고).

## 1단계 — 분류

```bash
uv run python scripts/visa_title_classifier.py <HWPX경로>
```

(uv가 없으면 `python scripts/visa_title_classifier.py <HWPX경로>`)

출력 JSON의 `in_scope`가 `false`면 **여기서 중단**하고 `reason`/`target`을 사용자에게 그대로 안내한다. 예:
- `target=UNKNOWN` → "비자유형을 판별하지 못했습니다, 직접 확인해주세요"
- `target=extraction/B_E-7-4R/...` → "E-7-4R은 기존 프로세스로 처리하는 대상입니다"

`in_scope=true`면 `visa_code`, `notice_round`를 이후 단계에서 계속 쓴다.

## 2단계 — 중복 확인

`extraction/D_visa_requirements/visa_requirements.csv`에서 `visa_code`로 행을 찾아 `visa_id`를 확인한다(없으면 "신규 비자 최초 등록"으로 간주하고 계속 진행).

`visa_id`가 있으면 `extraction/D_visa_requirements/visa_process_stages.csv`에 같은 `visa_id`+`notice_round` 행이 이미 있는지 확인한다. 있으면 **여기서 중단**하고 "이미 {notice_round}차가 처리되어 있습니다"라고 안내한다(에러 아님, 정상 종료).

## 3단계 — 챕터 분리

```bash
uv run python scripts/extract_notice_sections.py <HWPX경로>
```

출력 JSON의 `chapters` 목록에서 각 챕터가 저장된 텍스트 파일 경로를 확인한다. 보통 "공고 개요"/"공고 일정"/"자격요건"/"접수방법 및 결과발표"(문의처 포함)/"체류 특례사항"(다음 비자 전환 조건) 5개 챕터가 이번 단계에서 필요하다.

## 4단계 — 구조화 (Claude가 직접 판단)

Read 툴로 3단계에서 저장된 챕터 텍스트 파일들을 **그대로 읽는다**(별도 OCR/이미지 판독 불필요 — HWPX 추출 텍스트에 원문 숫자가 그대로 살아있음). 그리고 `extraction/D_visa_requirements/README.md`의 판단 기준(5단계 질문, OR조건 `condition_group`/`condition_operator` 처리, 복합조건 A AND (B OR C) 분리, `admin_guide_corpus`로 뺄 재량판단 표현 제외, `quota_type` LIMITED/UNLIMITED/UNKNOWN 구분, 배열 필드 파이프 표기)을 그대로 적용해 아래 스키마의 draft JSON을 만든다.

```json
{
  "visa_code": "F-4-R",
  "notice_round": 13,
  "source_document": "<HWPX 파일명>",
  "requirements": {
    "visa_name_kr": "...", "program_type": "...",
    "target_region": ["제천시", "..."],
    "total_score_threshold": null,
    "residency_limit_years": 2,
    "allowed_industries": null,
    "application_method": "...",
    "quota_type": "LIMITED|UNLIMITED|UNKNOWN",
    "total_quota": null,
    "quota_shared_with": null,
    "next_visa_code": "F-5-6R",
    "valid_from": "YYYY-MM-DD", "valid_to": "YYYY-MM-DD",
    "source_page": "챕터 번호 등 참고용 표기"
  },
  "criteria": [
    {"criteria_name": "...", "criteria_type": "binary",
     "threshold_value": "...", "point_value": null,
     "condition_group": "G1", "condition_operator": "OR",
     "special_case_note": "...", "source_page": "..."}
  ],
  "stages": [
    {"stage_order": 1, "stage_name": "NOTICE_PUBLICATION", "stage_name_kr": "모집공고",
     "actor_from": "...", "actor_to": "...",
     "stage_start_date": "YYYY-MM-DD", "stage_end_date": "YYYY-MM-DD",
     "notes": "...", "source_page": "..."}
  ],
  "quota_status": {"remaining_quota": 0, "as_of_date": "YYYY-MM-DD", "source_page": "..."} ,
  "contacts": [{"region": "제천", "department_name": "...", "phone": "..."}]
}
```

주의:
- `quota_status`는 `quota_type=LIMITED`이고 공고문에 잔여인원이 실제로 언급된 경우에만 채운다. 그 외엔 `null`.
- criteria는 재량판단 표현("인정되는 경우" 등)이 들어간 단서를 별도 criteria 행으로 만들지 않는다 — `special_case_note`에만 남긴다.
- 확인되지 않은 값은 추측하지 않는다. 애매하면 그 필드를 비우고 리포트에서 사람이 보게 한다.

완성한 draft를 `reports/notices/_drafts/{visa_code}_{notice_round}차_draft.json`에 저장한다(폴더 없으면 생성).

## 5단계 — 비교 및 리포트 생성

```bash
uv run python scripts/compare_and_report.py reports/notices/_drafts/<visa_code>_<notice_round>차_draft.json
```

출력된 리포트 경로(`reports/notices/notice_{round}차_{visa_code}_review.md`)를 Read 툴로 읽는다.

## 6단계 — 마무리 보고

사용자에게:
- 리포트 경로
- 핵심 변경사항 3~5줄 요약(신규/변경 필드 개수, criteria added/removed/changed 개수, agency_contacts 경고 유무)
- **"CSV는 자동 반영되지 않았습니다. 검토 후 change_history.csv 제안 행부터 직접 반영해주세요."** 안내

HWPX 원본이 `data/raw/<visa_code>/` 밖에 있었다면(예: `data/incoming/`), `data/raw/<visa_code>/`로 이동할지 사용자에게 확인한다 — 자동으로 이동시키지 않는다.
