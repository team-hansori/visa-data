-- Reference agency contacts + risk routing schema (지도 탭 기관 연락처·위험 라우팅).
-- 설계 근거와 파생 규칙은 docs/map-agency-schema.md 참고. common_schema_v2와 책임을
-- 섞지 않는 별도 migration이다.

CREATE TABLE public."agency_contacts" (
  "agency_id" uuid PRIMARY KEY NOT NULL,
  "category_major" text NOT NULL,
  "category_minor" text NOT NULL,
  "region" text NOT NULL,
  "department_name" text NOT NULL,
  "address" text,
  "phone" text NOT NULL,
  "url" text,
  "target_audience" text NOT NULL,
  "is_user_facing" boolean NOT NULL,
  "valid_from" date NOT NULL,
  "valid_to" date,
  "source_document" text NOT NULL,
  "source_page" text,
  "last_verified_at" date NOT NULL,
  "agency_type" text CONSTRAINT "agency_contacts_type_allowed" CHECK (
    "agency_type" IS NULL OR "agency_type" IN (
      'COMMUNITY_CENTER', 'ADMINISTRATIVE_AGENCY', 'UNIVERSITY_DEPT_OFFICE',
      'FOREIGN_SUPPORT_CENTER', 'OTHER'
    )
  ),
  "sido" text,
  "sigungu" text,
  "eupmyeondong" text,
  "road_address" text,
  "latitude" numeric(9,6) CONSTRAINT "agency_contacts_latitude_range" CHECK ("latitude" BETWEEN -90 AND 90),
  "longitude" numeric(9,6) CONSTRAINT "agency_contacts_longitude_range" CHECK ("longitude" BETWEEN -180 AND 180),
  "geocode_method" text,
  "geocoded_at" date,
  "operating_hours" text,
  "is_active" boolean NOT NULL DEFAULT true,
  "source_url" text,
  CONSTRAINT "agency_contacts_coords_paired" CHECK (("latitude" IS NULL) = ("longitude" IS NULL)),
  CONSTRAINT "agency_contacts_map_pin_requires_type" CHECK ("latitude" IS NULL OR "agency_type" IS NOT NULL)
);

CREATE TABLE public."risk_routing_table" (
  "routing_id" uuid PRIMARY KEY NOT NULL,
  "keyword_category" text NOT NULL,
  "user_type" text NOT NULL,
  "applies_to_visa_code" text,
  "resolution_type" text NOT NULL CHECK ("resolution_type" IN ('EXTERNAL', 'IN_DOMAIN')),
  "target_agency_category" text,
  "external_agency_name" text,
  "external_region_scope" text,
  "external_phone" text,
  "external_url" text,
  "message_addendum" text,
  "notes" text,
  "valid_from" date NOT NULL,
  "valid_to" date,
  "source_document" text NOT NULL,
  "source_page" text,
  "last_verified_at" date NOT NULL
);

CREATE TABLE public."risk_keyword_messages" (
  "keyword_category" text NOT NULL,
  "resolution_type" text NOT NULL CHECK ("resolution_type" IN ('EXTERNAL', 'IN_DOMAIN')),
  "message_stem" text NOT NULL,
  "source_document" text NOT NULL,
  "source_page" text,
  "last_verified_at" date NOT NULL,
  PRIMARY KEY ("keyword_category", "resolution_type")
);

-- security_invoker=true: 뷰 소유자가 아니라 조회하는 role 기준으로 agency_contacts의
-- RLS를 평가한다 — 기본값(off)이면 뷰가 RLS를 우회할 수 있다.
CREATE VIEW public."map_visible_agency_contacts"
  WITH (security_invoker = true) AS
  SELECT * FROM public."agency_contacts"
  WHERE "agency_type" IS NOT NULL
    AND "latitude" IS NOT NULL
    AND "longitude" IS NOT NULL
    AND "is_active" = true
    AND "is_user_facing" = true;

CREATE INDEX "agency_contacts_map_lookup_idx" ON public."agency_contacts" ("category_minor", "region")
  WHERE "agency_type" IS NOT NULL AND "latitude" IS NOT NULL AND "longitude" IS NOT NULL
    AND "is_active" AND "is_user_facing";
CREATE INDEX "agency_contacts_region_idx" ON public."agency_contacts" ("sido", "sigungu");
CREATE INDEX "risk_routing_category_idx" ON public."risk_routing_table" ("keyword_category", "user_type");

ALTER TABLE public."agency_contacts" ENABLE ROW LEVEL SECURITY;
ALTER TABLE public."risk_routing_table" ENABLE ROW LEVEL SECURITY;
ALTER TABLE public."risk_keyword_messages" ENABLE ROW LEVEL SECURITY;

CREATE POLICY "public read" ON public."agency_contacts" FOR SELECT TO anon, authenticated USING (true);
CREATE POLICY "public read" ON public."risk_routing_table" FOR SELECT TO anon, authenticated USING (true);
CREATE POLICY "public read" ON public."risk_keyword_messages" FOR SELECT TO anon, authenticated USING (true);

GRANT SELECT ON public."agency_contacts", public."risk_routing_table", public."risk_keyword_messages"
  TO anon, authenticated;
GRANT SELECT ON public."map_visible_agency_contacts" TO anon, authenticated;
