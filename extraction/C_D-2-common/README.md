# C_D-2-common — D-2(유학생) 비자 공통 요건

`chungbuk-sari`(충북살이 서비스 DB 저장소)에서 이미 검수 완료 상태로 만들어져 있던 D-2 관련 근거표 3종을 그대로 옮겨왔다.

## 파일

| 파일 | 내용 |
|------|------|
| `parttime_work_rules.csv` | D-2/D-4 시간제취업 허가 요건 (학적별 한국어능력·근로시간 한도) |
| `certified_universities.csv` | 교육국제화역량 인증대학 명단 |
| `gwangyeok_eligible_departments.csv` | 충북 K-유학생 광역형 비자(D-2-GWANGYEOK) 대상 학과 |

## 스키마 관련 주의

이 3개 파일은 `B_E-7-4R`이 쓰는 표준 4종 근거표(`current_requirements.csv`/`scoring_items.csv`/`document_forms.csv`/`change_history.csv`) 포맷이 아니라 `chungbuk-sari`에서 쓰던 원래 컬럼 구조 그대로다. `current_requirements.csv` 포맷으로 재구성하려면 `raw_text`(원문 보존)·`status`·`condition_group`/`condition_operator` 같은 필드를 채워야 하는데, 원본 PDF 재확인 없이는 추측으로 채우게 되어 "확인되지 않은 값은 추측하지 않는다" 원칙에 어긋난다. 그래서 이번 PR에서는 원본 스키마 그대로 옮기고, 표준 포맷 재구성은 원본 재확인이 가능한 후속 작업으로 미룬다.

각 파일의 `source_document`/`source_page`/`last_verified_at` 컬럼에 근거 문서·페이지·최종 확인일이 남아 있다.
