# reference/ — 비자 요건과 무관한 참조·서비스 데이터

`extraction/<비자유형>/`은 비자 심사요건(조건문) 근거표 전용이다. 그와 달리 이 폴더는 특정 비자의 심사조건이 아니라 "이런 기관/제도가 있다"는 목록형 데이터를 담는다. `chungbuk-sari` 저장소와 구조를 통일하기로 팀 컨펌 후 신설했다 (관련 논의: PR 참고).

## 파일

| 파일 | 내용 |
|------|------|
| `agency_contacts.csv` | 충북 시군별 가족센터·다문화가족지원센터·외국인지원센터 연락처 |

`support_programs.csv`(지원사업 목록), `external_link_registry.csv`, `risk_routing_table.csv`도 같은 성격으로 이 폴더에 들어올 예정이지만, 아직 `chungbuk-sari` 쪽에서 데이터가 만들어지지 않아 이번 PR에는 포함하지 않았다 — 스키마만 있는 빈 파일은 만들지 않는다.
