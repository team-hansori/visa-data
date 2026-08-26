# 지도 탭 기관·위험 라우팅 스키마 설계 (이슈 #51)

## 요약

`visa-bugi-web` 지도 탭(주변 기관 안내 + 위험 키워드 라우팅)을 위해 `agency_contacts`,
`risk_routing_table`, `risk_keyword_messages` 3개 테이블의 스키마를 확정한다.

핵심 결정 5가지:

1. **기존 97행 보존**: `agency_contacts.csv`의 기존 15개 컬럼과 값은 전혀 건드리지 않는다.
   지도 기능에 필요한 컬럼은 전부 **신규 nullable 컬럼으로 끝에 추가**한다.
2. **"지도 표시 대상"은 저장하지 않고 파생한다**: `is_map_visible` 같은 별도 상태 플래그를
   두지 않는다 — `agency_type IS NOT NULL AND latitude/longitude IS NOT NULL AND is_active
   AND is_user_facing`로 조회 시점에 계산한다. `scripts/schema_v2.py`의 `FORBIDDEN_NAMES`가
   `extraction_status`/`review_status`/`confidence` 같은 별도 상태관리 컬럼을 금지한 것과
   같은 이유 — 원본 데이터와 플래그가 어긋나는 것을 원천 차단한다.
3. **위험 라우팅 → 기관 연결 방식은 변경하지 않는다**: 기존 `target_agency_category`
   (→ `agency_contacts.category_minor`) + 지역 조인 방식을 그대로 쓴다. 신규 FK 컬럼이나
   N:M 테이블을 추가하지 않는다 — `reference/README.md`에 이미 문서화된 설계 원칙이고,
   지도 기능은 조회 시점 필터 조건(`agency_type`, 좌표)만 늘어날 뿐 연결 방식 자체가 달라질
   이유가 없다.
4. **`category_minor`/`agency_type`은 서로 다른 축**: `category_minor`는 프로그램·서비스
   분류(라우팅 조인 키, 기존 계약 유지)이고, `agency_type`은 지도 필터용 물리적 기관
   유형이다. 이름이 비슷해 보이는 `FOREIGN_SUPPORT_CENTER`가 두 컬럼 모두에 등장할 수
   있으나 의미와 값 목록은 독립적이다.
5. **다국어 기관명·`is_map_visible` 저장·전국 확장은 이번 범위에 포함하지 않는다** — 이슈
   원문 그대로 후속 결정으로 남긴다.

이 문서가 `visa-bugi-web`에 공유할 계약의 SSOT다. 표는 실제 구현
(`scripts/reference_schema.py`)과 항상 일치시킨다.

---

## 1. `agency_contacts`

### 1.1 기존 컬럼 (변경 없음, 97행 그대로 유지)

| 컬럼 | 타입 | nullable | 설명 |
|------|------|----------|------|
| `agency_id` | uuid | 아니오 (PK) | |
| `category_major` | text | 아니오 | 프로그램 대분류 (`FOREIGN_EMPLOYMENT_SUPPORT` 등) |
| `category_minor` | text | 아니오 | 프로그램 소분류. `risk_routing_table.target_agency_category`가 참조하는 FK 대상 |
| `region` | text | 아니오 | 라우팅 조인용 지역 문자열. `충청북도`(도 단위 전역), 시군명, 또는 `옥천\|영동`처럼 파이프로 다중 시군 표기 |
| `department_name` | text | 아니오 | 부서/기관명. 도 단위 프로그램 행은 기관명이 아니라 담당 부서명(예: 외국인정책추진단)인 경우가 많음 |
| `address` | text | 예 (빈 문자열 다수) | 자유서식 주소. 지오코딩 미검증 |
| `phone` | text | 아니오 | |
| `url` | text | 예 | 기관 홈페이지 |
| `target_audience` | text | 아니오 | enum. 다중 대상은 `region`과 동일하게 파이프로 나열 (기존 관례 재사용, 신규 enum 값 추가 안 함) |
| `is_user_facing` | boolean | 아니오 | "사용자에게 노출 가능한 정보인가" — 이슈의 "사용자 노출 여부" 요건을 이미 충족 |
| `valid_from` / `valid_to` | date / date | 아니오 / 예 | |
| `source_document` / `source_page` | text / text | 아니오 / 예 | 출처 명칭·페이지 요건을 이미 충족 |
| `last_verified_at` | date | 아니오 | |

### 1.2 신규 컬럼 (지도 기능용, 이번 이슈에서 추가)

| 컬럼 | 타입 | nullable | 설명 |
|------|------|----------|------|
| `agency_type` | text (enum) | 예 | 지도 필터용 기관 유형. §1.3 참고 |
| `sido` | text | 예 | 시도. 위치 권한 거부 시 대체 조회용 |
| `sigungu` | text | 예 | 시군구. 위치 권한 거부 시 대체 조회용 |
| `eupmyeondong` | text | 예 | 읍면동. 있으면 채움, 없으면 null |
| `road_address` | text | 예 | 지오코딩 가능한 도로명 주소. 기존 `address`(자유서식, 미검증)와 별도 컬럼 — `address`를 소급 정제하지 않는다 |
| `latitude` | numeric(9,6) | 예 | CHECK -90..90. 정밀도·scale을 확정해 웹 타입 생성과 거리 계산이 흔들리지 않게 함 |
| `longitude` | numeric(9,6) | 예 | CHECK -180..180. `latitude`와 함께 채우거나 함께 비운다 |
| `geocode_method` | text | 예 | 좌표를 만든 방법(예: `Kakao Map API`, `수작업 확인`). 자유 텍스트라 표기가 흔들릴 수 있어 후속에서 작은 enum으로 좁히는 것을 검토한다 |
| `geocoded_at` | date | 예 | 좌표 확인일 |
| `operating_hours` | text | 예 | 운영시간, `Asia/Seoul` 기준. 확인 안 되면 추정하지 않고 null |
| `is_active` | boolean | **아니오, 명시적으로 채움** | 폐쇄·이전 등으로 더 이상 유효하지 않은 기관 표시. `is_user_facing`(노출 정책)과 별개 축 |
| `source_url` | text | 예 | 출처 문서/페이지의 URL. 기존 `url`(기관 자체 홈페이지)과 다른 필드 |

기존 97행은 `agency_type`/`sido`/`sigungu`/`eupmyeondong`/`road_address`/`latitude`/
`longitude`/`geocode_method`/`geocoded_at`/`operating_hours`/`source_url`은 빈 값으로
남긴다. 다만 **`is_active`는 예외** — `NOT NULL` 컬럼이므로 기존 97행 CSV에도 마이그레이션
스크립트가 `true`를 명시적으로 backfill한다. `import_reference_data.py`(§4)는 CSV의 빈
문자열을 `None`으로 변환해 그대로 INSERT하므로(`import_common_v2.py`와 동일한 패턴), CSV에
값을 쓰지 않고 DB `DEFAULT true`에 기대면 `NOT NULL` 위반이 난다 — 반드시 CSV 마이그레이션
단계에서 값을 채워야 한다. 신규 MVP 15~20행은 `agency_type`, 좌표, `road_address`를 채운
상태로 들어온다.

### 1.3 `agency_type` enum

| 값 | 의미 |
|----|------|
| `COMMUNITY_CENTER` | 주민센터 |
| `ADMINISTRATIVE_AGENCY` | 시청/군청/구청/출장소 등 행정기관 |
| `UNIVERSITY_DEPT_OFFICE` | 대학교 과사무실 |
| `FOREIGN_SUPPORT_CENTER` | 외국인지원기관 (다문화가족지원센터 등) |
| `OTHER` | 위 4개로 분류되지 않는 기관 |

### 1.4 "지도 표시 대상" 파생 규칙 (저장하지 않음)

```sql
-- 지도에 핀으로 찍을 수 있는 행
agency_type IS NOT NULL
  AND latitude IS NOT NULL AND longitude IS NOT NULL
  AND is_active = true
  AND is_user_facing = true
```

별도 boolean 컬럼(`is_map_visible` 등)을 두지 않는다. 좌표를 나중에 채우거나 `is_active`를
`false`로 바꿀 때 플래그를 별도로 갱신해야 하는 update anomaly를 피하기 위함이다.

다만 값을 저장하지 않기로 한 결정이 "조건을 여러 쿼리에 매번 복제해도 된다"는 뜻은 아니다
— 실제로 초안의 §2.2 라우팅 SQL이 이 조건 중 `is_active`/`is_user_facing`을 빠뜨렸던 것이
그 사례다. 구현 단계에서 `CREATE VIEW public.map_visible_agency_contacts AS SELECT * FROM
agency_contacts WHERE ...`(위 조건 그대로)를 만들어 지도 핀 조회(§2.2 (a))가 이 VIEW를
쓰게 하는 것을 권장한다 — 조건은 한 곳(VIEW 정의)에만 있고, 위험 라우팅 대표 연락처 조회
(§2.2 (b))처럼 애초에 좌표·`agency_type` 조건이 필요 없는 쿼리는 이 VIEW를 쓰지 않는다.

### 1.5 신규 컬럼 CHECK 제약

```sql
ALTER TABLE public.agency_contacts
  ADD CONSTRAINT agency_contacts_type_allowed CHECK (
    agency_type IS NULL OR agency_type IN (
      'COMMUNITY_CENTER', 'ADMINISTRATIVE_AGENCY', 'UNIVERSITY_DEPT_OFFICE',
      'FOREIGN_SUPPORT_CENTER', 'OTHER'
    )
  ),
  ADD CONSTRAINT agency_contacts_latitude_range CHECK (latitude BETWEEN -90 AND 90),
  ADD CONSTRAINT agency_contacts_longitude_range CHECK (longitude BETWEEN -180 AND 180),
  ADD CONSTRAINT agency_contacts_coords_paired
    CHECK ((latitude IS NULL) = (longitude IS NULL)),
  ADD CONSTRAINT agency_contacts_map_pin_requires_type
    CHECK (latitude IS NULL OR agency_type IS NOT NULL);
```

`agency_type` 허용값을 DB CHECK로 강제하는 이유: CSV 검증기(§4)는 importer를 거치지 않는
직접 SQL 쓰기까지는 막지 못한다. RLS는 읽기 전용이어도 service-role 쓰기 경로는 CHECK 없이
임의 값을 넣을 수 있으므로 DB 레벨에서도 enum을 강제한다.

`agency_contacts_map_pin_requires_type`는 **좌표 기준**이다 — "먼저 `agency_type`만 분류하고
좌표는 아직 없는" 중간 상태를 막지 않기 위해 "agency_type이 있으면 좌표 필수"가 아니라
"좌표가 있으면 agency_type 필수"로 방향을 고정했다. §1.6 NULL 정책의 `road_address`/
`geocode_method`/`geocoded_at`/`sido`/`sigungu` "좌표가 있으면 항상 채움" 규칙은 CSV
품질 규칙(validator, §4)으로만 강제하고 DB CHECK로는 강제하지 않는다 — 운영 중 좌표를
검증기 없이 직접 갱신하는 경로가 생기면 이 계층 구분을 재검토한다.

### 1.6 NULL 정책 표 (신규 컬럼)

| 컬럼 | 빈 칸의 의미 | 명시적 값이 필요한 경우 |
|------|------|------|
| `agency_type` | 지도 미노출 대상(기존 97행 대부분) | 지도에 핀을 찍을 신규 행은 항상 채움 |
| `sido`/`sigungu`/`eupmyeondong` | 아직 세분화하지 않음 | 신규 행은 항상 채움 |
| `road_address` | 지오코딩 미완료 | 좌표가 있으면 항상 채움 |
| `latitude`/`longitude` | 지도 미노출 대상 또는 좌표 미확인 | 확인되지 않은 좌표를 추정해서 채우지 않는다 |
| `geocode_method`/`geocoded_at` | 좌표 자체가 없음 | 좌표가 있으면 항상 채움 |
| `operating_hours` | 운영시간 미확인 | 확인 안 된 값을 추정해서 채우지 않는다(이슈 원칙) |
| `source_url` | 출처에 URL이 없음(예: PDF만 존재) | 웹페이지 출처면 채움 |

---

## 2. `risk_routing_table` / `risk_keyword_messages`

### 2.1 계약 유지 사항 (변경 없음)

- `resolution_type` = `IN_DOMAIN` / `EXTERNAL` 분기 그대로 유지.
- 실제 메시지 = `risk_keyword_messages.message_stem` + (있으면) 라우팅 행의
  `message_addendum` + 연락처 정보. 결합 순서 그대로 유지.
- `IN_DOMAIN` 행의 실제 담당기관은 신규 FK를 추가하지 않고, 화면에서
  `target_agency_category`(`agency_contacts.category_minor`) + 사용자 지역으로
  `agency_contacts`를 조인해 조회한다. `EXTERNAL` 행은 `external_*` 컬럼에 연락처를
  직접 보유한다.

### 2.2 지도 강조 연결 방식 (이슈의 열린 결정 → 확정)

**결정: 신규 컬럼·FK·N:M 테이블을 추가하지 않는다.** 다만 용도가 다른 두 조회를 분리한다 —
지도에는 매칭되는 기관을 **전부** 핀으로 찍어야 하고(개수 제한이 목적이 아님), 위험 라우팅
안내 메시지에는 **대표 연락처 1건**이 필요하다. 이 둘을 같은 `ORDER BY ... LIMIT 1`로
합치면 지도 쪽에서 후보가 임의로 잘리므로 조회를 나눈다.

**지역 매칭 규칙 (두 조회 공통)**: `region` 컬럼은 자유서식이 섞여 있다 — 파이프로
구분한 다중 시군(`옥천|영동`), 도 단위(`충청북도`), 그리고 `청주(관할:전지역)`처럼 괄호
설명이 붙은 자유서술 값이 실제로 존재한다. 부분문자열 `LIKE`는 오탐/누락을 모두 일으키므로
쓰지 않는다 — 대신 `region`을 애플리케이션에서 `|`로 토큰화한 뒤 각 토큰을 사용자의
`sigungu`와 **완전 일치**로 비교한다. `청주(관할:전지역)`처럼 토큰화·완전일치로 해석되지
않는 자유서술 값은 기존 데이터의 알려진 결함으로 별도 이슈에서 `충청북도`(도 단위) 또는
명시적 시군 나열로 정규화해야 한다 — 이번 지도 스키마 설계로 소급 수정하지 않는다.

**(a) 지도 핀 목록 — 매칭되는 모든 행 반환, 개수 제한 없음:**

```sql
SELECT agency_id, department_name, agency_type, road_address, latitude, longitude,
       phone, url, operating_hours
FROM agency_contacts
WHERE category_minor = :target_agency_category
  AND agency_type IS NOT NULL
  AND latitude IS NOT NULL
  AND is_active = true
  AND is_user_facing = true
  AND (
    :user_sigungu = ANY(string_to_array(region, '|'))
    OR region = '충청북도'
  );
```

**(b) 위험 라우팅 안내 메시지용 대표 연락처 — 정확 지역 매칭을 도 단위보다 우선:**

```sql
SELECT agency_id, department_name, phone, url
FROM agency_contacts
WHERE category_minor = :target_agency_category
  AND is_active = true
  AND is_user_facing = true
  AND (
    :user_sigungu = ANY(string_to_array(region, '|'))
    OR region = '충청북도'
  )
ORDER BY (region <> '충청북도') DESC  -- 정확 지역 매칭 우선, 도 단위는 후순위
LIMIT 1;
```

(b)는 지도 좌표 유무와 무관하게 연락처 텍스트를 반환해도 되므로 `agency_type`/좌표 조건이
없다 — 메시지 안내가 목적이지 핀 찍기가 목적이 아니기 때문이다. 동일 지역·카테고리에
후보가 둘 이상 남으면(예: 같은 시군에 유사 기관이 여러 곳) 이 시점의 `ORDER BY`로는
결정할 수 없다 — MVP 데이터에서 실제로 그런 중복이 나오면 `department_name` 알파벳순
등 명시적 tie-breaker를 추가하거나, 여러 건을 한 메시지에 모두 안내하는 쪽으로 계약을
바꾼다. 현재는 카테고리·지역 조합당 기관이 대부분 1건이라 이 경우를 별도 규칙 없이
남겨둔다.

근거: 이미 `reference/README.md`가 카테고리+지역 조인 방식을 설계 원칙으로 명문화했고
(§"도메인 안/밖 구분"), 라우팅 규칙 수·기관 수가 적은 MVP 단계에서 별도 링크 테이블은
과설계다.

### 2.3 Fallback 규칙 (신규 확정)

1. 사용자 지역을 알 수 없음(위치 권한 거부 + 저장된 시군구 없음): §2.2 쿼리의
   `:user_sigungu` 조건을 생략하고 `region = '충청북도'`인 도 단위 행만 후보로 삼는다.
2. 사용자 지역은 알지만 (a) 지도 핀 조회 결과가 0건: 핀 없이 (b) 대표 연락처 조회 결과만
   텍스트로 안내한다 — 없는 좌표를 추정해서 지도에 찍지 않는다.
3. (b) 대표 연락처 조회까지 0건(도 단위 행도 없는 카테고리): 화면에 "관할 기관 정보를
   확인 중"류의 명시적 미확인 상태를 보여준다 — 임의 기관을 대신 보여주지 않는다.
4. `EXTERNAL` 행은 기존 `external_region_scope`(`NATIONWIDE` 또는 시군 파이프 나열) 규칙을
   그대로 따른다. 변경 없음.

### 2.4 `user_type` 임시 의미

웹 사용자 스키마 미확정 상태이므로 현재 `user_type` 값(`FOREIGN_WORKER` 등)을 그대로
유지한다. `visa-bugi-web` 이슈 #5에서 비자유형/체류자격 기준이 확정되면 값 재정렬이
필요할 수 있음을 계약에 명시한다 — 지금 임의로 값을 늘리지 않는다.

---

## 3. Supabase 반영 설계

### 3.1 신규 migration 파일

`supabase/migrations/<타임스탬프>_reference_agency_map_schema.sql` — `common_schema_v2`와
책임을 섞지 않고 별도 파일로 추가한다. 내용:

- `CREATE TABLE public.agency_contacts` (uuid PK, 위 §1.1+§1.2 전체 컬럼, CHECK 5종)
- `CREATE TABLE public.risk_routing_table` (uuid PK `routing_id`)
- `CREATE TABLE public.risk_keyword_messages` (복합 PK `(keyword_category, resolution_type)` —
  단일 uuid PK가 없는 유일한 신규 테이블)
- `CREATE VIEW public.map_visible_agency_contacts` (§1.4의 파생 조건을 한 곳에 캡슐화 —
  지도 핀 조회 전용, §2.2 (a))
- FK: `risk_routing_table.target_agency_category` → PostgreSQL 자체는 text 컬럼에도 FK를
  걸 수 있지만, 참조 대상인 `agency_contacts.category_minor`가 **행마다 반복되는 값이라
  UNIQUE/PK 조건을 충족하지 못해 FK 대상이 될 수 없다**(이 부분이 정확한 이유이지 "text라서
  불가능"이 아니다). 강한 DB 무결성이 필요해지면 `category_minor` lookup 테이블을 별도로
  만들어 양쪽이 그 테이블을 참조하게 해야 한다. 이번 범위에서는 기존
  `validate_fk_integrity.py`처럼 CSV/애플리케이션 레벨 논리 참조로 유지한다.

### 3.2 인덱스

```sql
CREATE INDEX agency_contacts_map_lookup_idx
  ON public.agency_contacts (category_minor, region)
  WHERE agency_type IS NOT NULL AND latitude IS NOT NULL
    AND longitude IS NOT NULL AND is_active AND is_user_facing;
CREATE INDEX agency_contacts_region_idx ON public.agency_contacts (sido, sigungu);
CREATE INDEX risk_routing_category_idx ON public.risk_routing_table (keyword_category, user_type);
```

partial index 조건을 §2.2의 실제 조회 조건(`is_active`, `is_user_facing` 포함)과 맞췄다 —
조건이 어긋나면 인덱스가 실제로는 쓰이지 않는다. MVP 15~20행 규모에서는 이 인덱스 자체가
성능상 필수는 아니며, 향후 반경/거리 조회가 핵심이 되면 B-tree가 아니라 PostGIS
`geography(Point, 4326)` + GiST 인덱스 도입을 검토한다(지금 범위 아님).

### 3.3 RLS와 쓰기 경로

`common_schema_v2`와 동일하게 3개 테이블 모두 `ENABLE ROW LEVEL SECURITY` 후
`anon, authenticated` 대상 `SELECT`만 허용하는 `public read` 정책을 추가한다. PostgreSQL은
RLS 정책과 테이블 권한이 별개이므로, 정책과 함께 아래 `GRANT`도 migration에 명시한다.

```sql
GRANT SELECT ON public.agency_contacts, public.risk_routing_table,
  public.risk_keyword_messages TO anon, authenticated;
```

쓰기는 `scripts/import_reference_data.py`가 `DATABASE_URL`(직접 PostgreSQL 접속 문자열)로
수행한다 — Supabase service-role JWT와는 별개의 자격 증명 방식이며, `import_common_v2.py`가
이미 쓰는 것과 동일한 방식이다("서비스 키"라는 표현은 혼동을 줄 수 있어 쓰지 않는다).

---

## 4. Importer / Validator 설계

기존 `scripts/import_common_v2.py`/`scripts/schema_v2.py`는 `extraction/common_v2/` 13개
표만 다룬다 — 이슈 원문대로 여기에 합치지 않고 별도로 만든다.

- `scripts/reference_schema.py` (신규): `schema_v2.py`의 `ColumnKind`/`ColumnSpec`/
  `TableSpec`을 그대로 import해 재사용하지 **않는다** — 두 가지 계약을 표현할 수 없기
  때문이다. `TableSpec.pk`는 단일 문자열만 받아 `risk_keyword_messages`의 복합 PK
  `(keyword_category, resolution_type)`를 표현하지 못하고, `ColumnSpec`은 "FK가 있으면
  반드시 UUID"라는 불변식이 있어(`schema_v2.py:86`) text 논리 FK인
  `target_agency_category`(→ `category_minor`)를 표현하지 못한다. 대신 같은 *패턴*(자료형
  분리, dataclass 기반 컬럼/테이블 계약, enum 강제)을 따르는 독립된
  `ColumnKind`/`ColumnSpec`/`TableSpec`을 이 모듈에 새로 정의하되, `TableSpec.pk`를
  `tuple[str, ...]`로, FK 컬럼은 UUID 제한 없이(text FK 포함) 표현할 수 있게 한다.
  `validate_fk_integrity.py`가 이미 text FK(`target_agency_category` → `category_minor`)를
  CSV 레벨에서 문제없이 검사하고 있으므로, 제약을 두는 쪽은 `schema_v2.py`의 설계
  선택이지 일반 원칙이 아니다.
- `scripts/import_reference_data.py` (신규): `import_common_v2.py`와 동일한 구조
  (dry-run 기본, `--apply` + `DATABASE_URL`, 단일 트랜잭션, 적재 후 행 수 검증)를 따르되
  두 가지를 다르게 한다.
  1. `risk_keyword_messages`의 upsert는 `ON CONFLICT (keyword_category, resolution_type)`
     복합키 기준으로 생성한다(`import_common_v2.py`의 단일 PK `ON CONFLICT` 생성 로직을
     그대로 쓸 수 없음).
  2. **삭제/잔존 행 정책을 명시한다**: CSV에서 사라진 행을 트랜잭션 내에서 자동 삭제하지
     않는다(기관 폐쇄는 행 삭제가 아니라 `agency_contacts.is_active=false`로 표현하는
     설계와 일치). 따라서 사후 검증도 `import_common_v2.py`처럼 "DB 행 수 == CSV 행 수"를
     기대하지 않고, "CSV의 모든 PK가 DB에 존재하는가"만 확인한다.
- `scripts/validate_fk_integrity.py`: 기존 `reference_tables()`에 `agency_type` enum 검사,
  좌표 페어 검사, "좌표가 있으면 `road_address`/`geocode_method`/`geocoded_at`/`sido`/
  `sigungu` 필수"(§1.5 CHECK와 동일하게 좌표 기준, `agency_type` 기준 아님) 규칙을
  추가한다 — 새 스크립트를 만들지 않고 기존 검증기를 확장한다(이미 이 파일이 reference/
  폴더 검증 책임을 지고 있음).
- **CI 연결**: 확인 결과 `validate_fk_integrity.py`는 현재 `ci.yml`에 연결되어 있지 않다.
  스키마를 설계하는 것만으로는 회귀를 막지 못하므로, 이 검증기(및 신규
  `import_reference_data.py`의 dry-run)를 CI와 `import_reference_data.py` preflight
  양쪽에서 실행하도록 구현 계획에 포함한다.

---

## 5. 웹 저장소(`visa-bugi-web`) 공유 계약 요약

- 테이블/컬럼/타입/enum: 본 문서 §1~§2 표 전체.
- **CSV/조회 결과는 헤더(컬럼명) 기준으로 파싱한다** — 위치 인덱스 기준 파싱 금지. 기존
  15개 컬럼의 이름·의미는 불변이며 신규 컬럼은 항상 그 뒤에 append된다. 구버전 소비자는
  알 수 없는 trailing 컬럼을 무시해야 한다.
- 지도 핀 목록 조회: §2.2 (a) SQL 그대로 — `SELECT *` 대신 필요한 컬럼만 명시해 응답
  크기와 타입 생성이 컬럼 추가에 흔들리지 않게 한다. 정렬은 웹 쪽에서 좌표 기준 거리
  계산(반경/개수 기준은 범위 밖 — 웹이 결정).
- 위치 권한 거부 시 조회 필드: `sigungu`, `eupmyeondong` (지도 화면 목록 필터용).
- 위험 라우팅 → 대표 연락처 조회: §2.2 (b) SQL 그대로. 지도 핀(복수)과 라우팅 메시지용
  연락처(단일)는 서로 다른 조회이므로 혼용하지 않는다.
- 지역 매칭: `region` 컬럼은 반드시 `|`로 토큰화한 뒤 사용자 시군구와 완전 일치로
  비교한다(부분문자열 `LIKE` 금지) — §2.2 참고.
- 메시지 조립: `message_stem` + `message_addendum`(있으면, 뒤에 이어붙임) + 연락처.
- `user_type`: 현재 `FOREIGN_WORKER` 등 기존 값 유지, `visa-bugi-web` #5 확정 후 재정렬
  가능성 있음 — 지금 하드코딩 시 이 사실을 주석으로 남길 것.

---

## 6. 범위 밖 / 후속 결정 (변경 없음, 이슈 원문 유지)

- 다국어 기관명
- `is_map_visible` 같은 저장형 플래그 (§1.4에서 파생 조건으로 대체 — 채택 안 함)
- 전국 확장
- 반경/가까운 기관 N개 기준, 위치 권한 거부 UI, 지도 SDK 선정 — 웹 저장소 책임
- 실증 4개 지역 15~20행의 실제 기관명·주소·좌표 수집 — 공식 출처 확인이 필요한 리서치
  작업이라 이 설계 문서와 뒤따르는 구현 계획(스키마/마이그레이션/importer)에는 포함하지
  않는다. 완료 기준 체크리스트의 별도 후속 작업으로 진행한다.
