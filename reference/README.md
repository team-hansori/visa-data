# reference/ — 비자 요건과 무관한 참조·서비스 데이터

`extraction/<비자유형>/`은 비자 심사요건(조건문) 근거표 전용이다. 그와 달리 이 폴더는 특정 비자의 심사조건이 아니라 "이런 기관/제도가 있다"는 목록형 데이터를 담는다. `chungbuk-sari` 저장소와 구조를 통일하기로 팀 컨펌 후 신설했다 (관련 논의: PR 참고).

## 파일

| 파일 | 내용 |
|------|------|
| `agency_contacts.csv` | 충북 시군별 가족센터·다문화가족지원센터·외국인지원센터 연락처. `url` 컬럼 추가됨(전화 다음 위치) — 기존 행은 아직 URL 미검증이라 빈 값, 추가 조사 필요. 지도 탭용 컬럼 12개(`agency_type`/좌표/`is_active` 등, 이슈 #51)가 끝에 추가됨 — 스키마는 `docs/map-agency-schema.md` 참고 |
| `risk_routing_table.csv` | ⑤번 위험 키워드 감지 기능의 라우팅 규칙표. 사용자 대화에서 위험 신호(임금체불·산재·폭행·불법취업·거주지 유지의무 위반 등)가 감지되면 AI가 직접 답하지 않고 전문기관으로 연결한다. `admin_guide_corpus`(사용자가 물어봤을 때만 답하는 RAG)와 달리 선제적으로 개입하는 성격이 다르다 |
| `risk_keyword_messages.csv` | `risk_routing_table.csv`의 `keyword_category`+`resolution_type`별 공통 안내 문구(boilerplate). 지역별로 반복되던 `escalation_message_template`을 카테고리 단위로 분리해 문구 수정 시 한 곳만 고치면 되도록 함. 실제 발송 메시지는 앱이 `message_stem` + 라우팅 행의 `message_addendum`(있는 경우) + 연락처 정보를 조합해 만든다. |

`support_programs.csv`, `external_link_registry.csv`도 같은 성격으로 이 폴더에 들어올 예정이지만, 아직 `chungbuk-sari` 쪽에서 데이터가 만들어지지 않아 이번 PR에는 포함하지 않았다 — 스키마만 있는 빈 파일은 만들지 않는다.

## `risk_routing_table.csv` 설계 원칙

- **도메인 안/밖 구분**: 담당기관이 우리 서비스가 이미 추적하는 도메인 안에 있으면(`resolution_type=IN_DOMAIN`) `target_agency_category`에 `agency_contacts.category_minor` 값을 적어두고, 실제 지역별 기관은 화면에서 `region + target_agency_category`로 `agency_contacts.csv`를 조인해 조회한다. 도메인 밖(노동청·근로복지공단·다누리콜센터 등 범용 공공기관)이면 `resolution_type=EXTERNAL`로 두고 `external_*` 필드에 연락처를 직접 보유한다 — agency_contacts에는 도메인 밖 기관을 추가하지 않는다.
- **user_type=FOREIGN_WORKER만 채움**: 현재 6행 모두 이주노동자 대상으로만 확인했다. 유학생(STUDENT)에게도 동일 카테고리가 적용되는지는 검토하지 않았으므로 임의로 행을 늘리지 않았다 — 필요 시 검토 후 추가.
- **한국어 템플릿만 작성**: `risk_keyword_messages.csv`의 `message_stem`은 한국어 원문만 채운다. 다국어 지원은 앱 전체 i18n 전략이 정해진 뒤 별도 테이블(예: `risk_routing_message_i18n.csv`)로 확장할 예정이며, 지금은 보류 상태다.
- **행별 추가 안내는 `message_addendum`에 작성**: 카테고리 전체에 공통인 문장은 `message_stem`에 두고, 특정 라우팅 행에서만 노출해야 하는 정보(예: 충주지청 지역대표 전화)는 `risk_routing_table.csv.message_addendum`에 둔다. 실제 메시지를 만들 때 비어 있지 않은 `message_addendum`을 `message_stem` 뒤에 붙인다.
- **`external_region_scope`는 `resolution_type`에 따라 의미가 다르다**: `resolution_type=IN_DOMAIN`인 행은 이 필드 자체가 해당 없음이라 빈 칸이어도 무방하다. `resolution_type=EXTERNAL`인 행은 빈 칸이 허용되지 않는다 — "관할지역을 아직 확인 안 함" 상태를 빈 칸으로 남겨두지 않고, 전국 단일기관으로 **확인된** 경우(예: 다누리콜센터)는 `NATIONWIDE`, 특정 지역이 확인된 경우는 파이프로 시군을 나열한다. `quota_type`(LIMITED/UNLIMITED/UNKNOWN)과 같은 이유로, 비어 있는 값을 자동으로 "지역 제한 없음"으로 해석해 넘어가면 안 된다. 컬럼별 빈 칸 규칙 전체는 아래 "빈 칸(NULL) 의미 정리" 표 참고.
- **`notes`에 확인되지 않은 부분을 명시**: 예를 들어 다누리콜센터(1577-1366)는 이주여성 대상 서비스로 명시돼 있어 남성 피해자 커버 여부가 확인되지 않았고, 근로복지공단 콜센터(1588-0075)는 지사 직통이 아니라 전국 단일번호다. 이런 확인되지 않은 판단은 추측해서 메우지 않고 `notes`에 남긴다.
- **보류된 카테고리**: `ATTENDANCE_SHORTAGE`(출석미달)는 단일 담당기관을 확인하지 못해 제외했다. `RESTRICTED_PARTTIME_WORK`(제한업종 시간제취업)는 필요성 재검토 후 채택하지 않기로 했다.
- **동일 연락처를 공유하는 지사는 행을 합친다**: `external_phone`·`external_url`·`notes`가 지역과 무관하게 완전히 동일하다면(예: 근로복지공단 전국 콜센터 1588-0075) 지사별로 행을 나누지 않고 `external_region_scope`에 해당 지역을 모두 나열한 1행으로 합친다. `external_agency_name`이 지사명만 다르고(예: 청주지사/충주지사) 상위 기관명(예: 근로복지공단)으로 수렴하는 경우는 병합을 막는 조건이 아니다 — 병합된 행에는 상위 기관명만 남긴다. 안내 문구 수정 시 여러 행을 동시에 고쳐야 하는 갱신 이상(update anomaly)을 막기 위함이다.

### 빈 칸(NULL) 의미 정리

같은 빈 칸이라도 컬럼에 따라 의미가 다르다 — 아래 표로 명시한다.

| 컬럼 | 빈 칸의 의미 | 명시적 값이 필요한 경우 |
|------|------|------|
| `applies_to_visa_code` | 특정 비자 제한 없음(전체 적용) | 제한이 있으면 파이프로 비자코드 나열 |
| `target_agency_category` | `resolution_type=EXTERNAL`이라 해당 없음 | — (`resolution_type=IN_DOMAIN`이면 항상 채움) |
| `external_agency_name`/`external_phone`/`external_url` | `resolution_type=IN_DOMAIN`이라 해당 없음 | — (`resolution_type=EXTERNAL`이면 항상 채움) |
| `message_addendum` | 해당 라우팅 행에만 덧붙일 안내 없음 | 지역별 직통번호처럼 공통 `message_stem`에 넣을 수 없는 안내가 있으면 문장으로 기입 |
| `external_region_scope` | `resolution_type=IN_DOMAIN`이면 이 필드 자체가 해당 없음이라 빈 칸이어도 무방. `resolution_type=EXTERNAL`이면 **빈 칸 사용 금지** — 관할지역 미확인 상태를 빈칸으로 남기지 않는다 | EXTERNAL 행: 전국 단일기관으로 확인되면 `NATIONWIDE`, 특정 지역이 확인되면 파이프로 시군 나열 |
| `valid_to` | 종료일 미정(현재 유효) | 종료가 확정되면 날짜 기입 |
| `source_page` | 출처 문서에 페이지 구분이 없음(예: 웹페이지 종합) | 페이지 번호가 있으면 숫자 기입 — `"N/A"` 같은 리터럴 문자열 사용 금지 |
