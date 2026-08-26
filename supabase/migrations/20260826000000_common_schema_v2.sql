-- Common schema v2. Generated from scripts/schema_v2.py; data is imported separately.

CREATE TABLE public."source_documents" (
  "source_document_id" uuid PRIMARY KEY NOT NULL,
  "source_document_key" text NOT NULL,
  "visa_id" uuid,
  "document_type" text NOT NULL CHECK ("document_type" IN ('AMENDMENT', 'ANNOUNCEMENT', 'ATTACHMENT', 'FORM', 'GUIDELINE', 'OTHER')),
  "document_name" text NOT NULL,
  "notice_round" numeric,
  "published_at" date,
  "source_location" text NOT NULL,
  "file_hash_sha256" text,
  "page_basis" text NOT NULL,
  "last_verified_at" date NOT NULL
);

CREATE TABLE public."visa_requirements" (
  "visa_id" uuid PRIMARY KEY NOT NULL,
  "visa_code" text NOT NULL,
  "visa_name_kr" text NOT NULL,
  "program_type" text NOT NULL,
  "target_regions_json" jsonb NOT NULL CHECK (jsonb_typeof("target_regions_json") = 'array'),
  "residency_limit_years" numeric,
  "allowed_industries_json" jsonb CHECK (jsonb_typeof("allowed_industries_json") = 'array'),
  "application_method" text NOT NULL,
  "next_visa_code" text,
  "valid_from" date NOT NULL,
  "valid_to" date,
  "source_document_id" uuid NOT NULL,
  "source_page" text NOT NULL,
  "last_verified_at" date NOT NULL
);

CREATE TABLE public."visa_criterion_groups" (
  "group_id" uuid PRIMARY KEY NOT NULL,
  "visa_id" uuid NOT NULL,
  "parent_group_id" uuid,
  "group_key" text NOT NULL,
  "group_name_kr" text NOT NULL,
  "boolean_operator" text NOT NULL CHECK ("boolean_operator" IN ('AND', 'OR')),
  "applicability_note" text,
  "display_order" numeric NOT NULL,
  "valid_from" date NOT NULL,
  "valid_to" date,
  "source_document_id" uuid NOT NULL,
  "source_page" text NOT NULL,
  "last_verified_at" timestamptz NOT NULL
);

CREATE TABLE public."visa_requirement_criteria" (
  "criteria_id" uuid PRIMARY KEY NOT NULL,
  "group_id" uuid NOT NULL,
  "criteria_name" text NOT NULL,
  "field_identifier" text,
  "criteria_type" text NOT NULL CHECK ("criteria_type" IN ('BOOLEAN', 'EXISTENCE', 'LIST', 'NUMERIC', 'TEXT')),
  "evaluation_mode" text NOT NULL CHECK ("evaluation_mode" IN ('AUTOMATED', 'INFORMATIONAL', 'MANUAL')),
  "operator" text CHECK ("operator" IN ('EQ', 'EXISTS', 'GT', 'GTE', 'IN', 'LT', 'LTE', 'NOT_EXISTS', 'NOT_IN', 'WITHIN')),
  "value_numeric" numeric,
  "value_text" text NOT NULL,
  "unit" text,
  "measurement_window_value" numeric,
  "measurement_window_unit" text,
  "special_case_note" text,
  "display_order" numeric NOT NULL,
  "valid_from" date NOT NULL,
  "valid_to" date,
  "source_document_id" uuid NOT NULL,
  "source_page" text NOT NULL,
  "last_verified_at" timestamptz NOT NULL
);

CREATE TABLE public."visa_scoring_models" (
  "score_model_id" uuid PRIMARY KEY NOT NULL,
  "visa_id" uuid NOT NULL,
  "model_name_kr" text NOT NULL,
  "model_purpose" text NOT NULL CHECK ("model_purpose" IN ('BOTH', 'PASS_THRESHOLD', 'QUOTA_RANKING', 'UNKNOWN')),
  "applies_when" text NOT NULL,
  "selection_rule" text NOT NULL,
  "tie_breaker_rule" text,
  "base_maximum_points" numeric NOT NULL,
  "minimum_required_points" numeric NOT NULL,
  "final_maximum_points" numeric,
  "bonus_cap_points" numeric,
  "penalty_cap_points" numeric NOT NULL,
  "from_round" numeric NOT NULL,
  "to_round" numeric,
  "valid_from" date NOT NULL,
  "valid_to" date,
  "source_document_id" uuid NOT NULL,
  "source_page" text NOT NULL,
  "notes" text
);

CREATE TABLE public."visa_scoring_items" (
  "scoring_item_id" uuid PRIMARY KEY NOT NULL,
  "score_model_id" uuid NOT NULL,
  "score_group" text NOT NULL CHECK ("score_group" IN ('BASE', 'BONUS', 'PENALTY')),
  "category" text NOT NULL,
  "criterion" text NOT NULL,
  "min_value" numeric,
  "max_value" numeric,
  "min_inclusive" boolean,
  "max_inclusive" boolean,
  "value_text" text,
  "unit" text,
  "measurement_window_value" numeric,
  "measurement_window_unit" text,
  "points" numeric NOT NULL,
  "maximum_points" numeric,
  "is_mandatory" boolean NOT NULL,
  "minimum_required_points" numeric,
  "exclusive_group" text,
  "stacking_rule" text NOT NULL CHECK ("stacking_rule" IN ('MAX_SCORE_ONLY', 'ONE_OF', 'STACK', 'UNKNOWN')),
  "evidence_document" text,
  "display_order" numeric NOT NULL,
  "valid_from" date NOT NULL,
  "valid_to" date,
  "source_document_id" uuid NOT NULL,
  "source_page" text NOT NULL
);

CREATE TABLE public."visa_process_stages" (
  "stage_id" uuid PRIMARY KEY NOT NULL,
  "visa_id" uuid NOT NULL,
  "stage_order" numeric NOT NULL,
  "stage_code" text NOT NULL,
  "stage_name_kr" text NOT NULL,
  "actor_from" text NOT NULL,
  "actor_to" text NOT NULL,
  "stage_start_date" date NOT NULL,
  "stage_end_date" date NOT NULL,
  "notice_round" numeric,
  "notes" text,
  "valid_from" date NOT NULL,
  "valid_to" date,
  "source_document_id" uuid NOT NULL,
  "source_page" text NOT NULL,
  "last_verified_at" date NOT NULL
);

CREATE TABLE public."document_requirements" (
  "document_requirement_id" uuid PRIMARY KEY NOT NULL,
  "stage_id" uuid NOT NULL,
  "document_name" text NOT NULL,
  "document_category" text NOT NULL,
  "filled_by" text NOT NULL,
  "submitted_by" text NOT NULL,
  "submission_target" text NOT NULL,
  "signer" text NOT NULL,
  "requirement_status" text NOT NULL CHECK ("requirement_status" IN ('ALTERNATIVE', 'CONDITIONAL', 'OPTIONAL', 'REQUIRED')),
  "alternative_group" text,
  "condition_note" text,
  "display_order" numeric NOT NULL,
  "valid_from" date NOT NULL,
  "valid_to" date,
  "source_document_id" uuid NOT NULL,
  "source_page" text NOT NULL,
  "last_verified_at" date NOT NULL,
  "notes" text
);

CREATE TABLE public."document_attachment_relations" (
  "relation_id" uuid PRIMARY KEY NOT NULL,
  "parent_document_id" uuid NOT NULL,
  "attachment_document_id" uuid NOT NULL,
  "requirement_status" text NOT NULL CHECK ("requirement_status" IN ('ALTERNATIVE', 'CONDITIONAL', 'OPTIONAL', 'REQUIRED')),
  "alternative_group" text,
  "condition_note" text,
  "display_order" numeric NOT NULL,
  "valid_from" date NOT NULL,
  "valid_to" date,
  "source_document_id" uuid NOT NULL,
  "source_page" text NOT NULL
);

CREATE TABLE public."visa_quota_policies" (
  "quota_policy_id" uuid PRIMARY KEY NOT NULL,
  "visa_id" uuid NOT NULL,
  "quota_type" text NOT NULL CHECK ("quota_type" IN ('LIMITED', 'UNKNOWN', 'UNLIMITED')),
  "quota_unit" text NOT NULL,
  "valid_from" date NOT NULL,
  "valid_to" date,
  "source_document_id" uuid NOT NULL,
  "source_page" text NOT NULL
);

CREATE TABLE public."visa_quota_snapshots" (
  "quota_snapshot_id" uuid PRIMARY KEY NOT NULL,
  "quota_policy_id" uuid NOT NULL,
  "notice_round" numeric,
  "as_of_date" date NOT NULL,
  "scope_type" text NOT NULL CHECK ("scope_type" IN ('DEPARTMENT', 'INSTITUTION', 'MUNICIPALITY', 'NATIONAL', 'OTHER', 'PROVINCE')),
  "scope_name" text NOT NULL,
  "parent_scope_name" text,
  "allocated_quota" numeric NOT NULL,
  "recommended_count" numeric,
  "quota_exempt_count" numeric,
  "consumed_quota" numeric NOT NULL,
  "remaining_quota" numeric NOT NULL,
  "consumption_exception" text,
  "valid_from" date NOT NULL,
  "valid_to" date,
  "source_document_id" uuid NOT NULL,
  "source_page" text NOT NULL,
  "recorded_at" timestamptz NOT NULL
);

CREATE TABLE public."change_history" (
  "change_id" uuid PRIMARY KEY NOT NULL,
  "visa_id" uuid NOT NULL,
  "table_name" text NOT NULL,
  "field_identifier" text NOT NULL,
  "from_round" numeric NOT NULL,
  "to_round" numeric NOT NULL,
  "old_value" text,
  "new_value" text,
  "change_type" text NOT NULL,
  "old_source_page" text,
  "new_source_page" text,
  "description" text
);

CREATE TABLE public."source_record_mappings" (
  "mapping_id" uuid PRIMARY KEY NOT NULL,
  "visa_id" uuid NOT NULL,
  "source_dataset" text NOT NULL,
  "source_table" text NOT NULL,
  "source_record_id" text NOT NULL,
  "source_group_path" text,
  "source_document_id" uuid NOT NULL,
  "source_page" text,
  "valid_from" date,
  "valid_to" date,
  "target_table" text NOT NULL,
  "target_record_id" uuid,
  "mapping_action" text NOT NULL CHECK ("mapping_action" IN ('COPY', 'MANUAL_REVIEW', 'MERGE', 'SKIP', 'TRANSFORM')),
  "mapping_status" text NOT NULL CHECK ("mapping_status" IN ('BLOCKED', 'MAPPED', 'PENDING', 'READY')),
  "blocking_reason" text,
  "mapped_at" timestamptz,
  "mapping_note" text
);

ALTER TABLE public."source_documents" ADD CONSTRAINT "source_documents_visa_id_fkey" FOREIGN KEY ("visa_id") REFERENCES public."visa_requirements" ("visa_id") ON UPDATE CASCADE ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE public."visa_requirements" ADD CONSTRAINT "visa_requirements_source_document_id_fkey" FOREIGN KEY ("source_document_id") REFERENCES public."source_documents" ("source_document_id") ON UPDATE CASCADE ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE public."visa_criterion_groups" ADD CONSTRAINT "visa_criterion_groups_visa_id_fkey" FOREIGN KEY ("visa_id") REFERENCES public."visa_requirements" ("visa_id") ON UPDATE CASCADE ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE public."visa_criterion_groups" ADD CONSTRAINT "visa_criterion_groups_parent_group_id_fkey" FOREIGN KEY ("parent_group_id") REFERENCES public."visa_criterion_groups" ("group_id") ON UPDATE CASCADE ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE public."visa_criterion_groups" ADD CONSTRAINT "visa_criterion_groups_source_document_id_fkey" FOREIGN KEY ("source_document_id") REFERENCES public."source_documents" ("source_document_id") ON UPDATE CASCADE ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE public."visa_requirement_criteria" ADD CONSTRAINT "visa_requirement_criteria_group_id_fkey" FOREIGN KEY ("group_id") REFERENCES public."visa_criterion_groups" ("group_id") ON UPDATE CASCADE ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE public."visa_requirement_criteria" ADD CONSTRAINT "visa_requirement_criteria_source_document_id_fkey" FOREIGN KEY ("source_document_id") REFERENCES public."source_documents" ("source_document_id") ON UPDATE CASCADE ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE public."visa_scoring_models" ADD CONSTRAINT "visa_scoring_models_visa_id_fkey" FOREIGN KEY ("visa_id") REFERENCES public."visa_requirements" ("visa_id") ON UPDATE CASCADE ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE public."visa_scoring_models" ADD CONSTRAINT "visa_scoring_models_source_document_id_fkey" FOREIGN KEY ("source_document_id") REFERENCES public."source_documents" ("source_document_id") ON UPDATE CASCADE ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE public."visa_scoring_items" ADD CONSTRAINT "visa_scoring_items_score_model_id_fkey" FOREIGN KEY ("score_model_id") REFERENCES public."visa_scoring_models" ("score_model_id") ON UPDATE CASCADE ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE public."visa_scoring_items" ADD CONSTRAINT "visa_scoring_items_source_document_id_fkey" FOREIGN KEY ("source_document_id") REFERENCES public."source_documents" ("source_document_id") ON UPDATE CASCADE ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE public."visa_process_stages" ADD CONSTRAINT "visa_process_stages_visa_id_fkey" FOREIGN KEY ("visa_id") REFERENCES public."visa_requirements" ("visa_id") ON UPDATE CASCADE ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE public."visa_process_stages" ADD CONSTRAINT "visa_process_stages_source_document_id_fkey" FOREIGN KEY ("source_document_id") REFERENCES public."source_documents" ("source_document_id") ON UPDATE CASCADE ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE public."document_requirements" ADD CONSTRAINT "document_requirements_stage_id_fkey" FOREIGN KEY ("stage_id") REFERENCES public."visa_process_stages" ("stage_id") ON UPDATE CASCADE ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE public."document_requirements" ADD CONSTRAINT "document_requirements_source_document_id_fkey" FOREIGN KEY ("source_document_id") REFERENCES public."source_documents" ("source_document_id") ON UPDATE CASCADE ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE public."document_attachment_relations" ADD CONSTRAINT "document_attachment_relations_parent_document_id_fkey" FOREIGN KEY ("parent_document_id") REFERENCES public."document_requirements" ("document_requirement_id") ON UPDATE CASCADE ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE public."document_attachment_relations" ADD CONSTRAINT "document_attachment_relations_attachment_document_id_fkey" FOREIGN KEY ("attachment_document_id") REFERENCES public."document_requirements" ("document_requirement_id") ON UPDATE CASCADE ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE public."document_attachment_relations" ADD CONSTRAINT "document_attachment_relations_source_document_id_fkey" FOREIGN KEY ("source_document_id") REFERENCES public."source_documents" ("source_document_id") ON UPDATE CASCADE ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE public."visa_quota_policies" ADD CONSTRAINT "visa_quota_policies_visa_id_fkey" FOREIGN KEY ("visa_id") REFERENCES public."visa_requirements" ("visa_id") ON UPDATE CASCADE ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE public."visa_quota_policies" ADD CONSTRAINT "visa_quota_policies_source_document_id_fkey" FOREIGN KEY ("source_document_id") REFERENCES public."source_documents" ("source_document_id") ON UPDATE CASCADE ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE public."visa_quota_snapshots" ADD CONSTRAINT "visa_quota_snapshots_quota_policy_id_fkey" FOREIGN KEY ("quota_policy_id") REFERENCES public."visa_quota_policies" ("quota_policy_id") ON UPDATE CASCADE ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE public."visa_quota_snapshots" ADD CONSTRAINT "visa_quota_snapshots_source_document_id_fkey" FOREIGN KEY ("source_document_id") REFERENCES public."source_documents" ("source_document_id") ON UPDATE CASCADE ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE public."change_history" ADD CONSTRAINT "change_history_visa_id_fkey" FOREIGN KEY ("visa_id") REFERENCES public."visa_requirements" ("visa_id") ON UPDATE CASCADE ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE public."source_record_mappings" ADD CONSTRAINT "source_record_mappings_visa_id_fkey" FOREIGN KEY ("visa_id") REFERENCES public."visa_requirements" ("visa_id") ON UPDATE CASCADE ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;
ALTER TABLE public."source_record_mappings" ADD CONSTRAINT "source_record_mappings_source_document_id_fkey" FOREIGN KEY ("source_document_id") REFERENCES public."source_documents" ("source_document_id") ON UPDATE CASCADE ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED;

ALTER TABLE public.visa_criterion_groups ADD CONSTRAINT visa_criterion_groups_not_self_parent CHECK (group_id <> parent_group_id);
ALTER TABLE public.document_attachment_relations ADD CONSTRAINT document_attachment_relations_not_self CHECK (parent_document_id <> attachment_document_id);
ALTER TABLE public.visa_quota_snapshots ADD CONSTRAINT visa_quota_snapshots_arithmetic CHECK (consumed_quota = coalesce(recommended_count, 0) - coalesce(quota_exempt_count, 0) AND remaining_quota = allocated_quota - consumed_quota);
CREATE UNIQUE INDEX visa_requirements_code_valid_from_uidx ON public.visa_requirements (visa_code, valid_from);
CREATE UNIQUE INDEX visa_criterion_groups_visa_key_uidx ON public.visa_criterion_groups (visa_id, group_key);
CREATE INDEX source_documents_visa_idx ON public.source_documents (visa_id);
CREATE INDEX criteria_group_idx ON public.visa_requirement_criteria (group_id);
CREATE INDEX scoring_models_visa_idx ON public.visa_scoring_models (visa_id);
CREATE INDEX scoring_items_model_idx ON public.visa_scoring_items (score_model_id);
CREATE INDEX process_stages_visa_order_idx ON public.visa_process_stages (visa_id, stage_order);
CREATE INDEX document_requirements_stage_idx ON public.document_requirements (stage_id);
CREATE INDEX attachment_parent_idx ON public.document_attachment_relations (parent_document_id);
CREATE INDEX attachment_child_idx ON public.document_attachment_relations (attachment_document_id);
CREATE INDEX quota_policies_visa_idx ON public.visa_quota_policies (visa_id);
CREATE INDEX quota_snapshots_policy_date_idx ON public.visa_quota_snapshots (quota_policy_id, as_of_date);
CREATE INDEX change_history_visa_idx ON public.change_history (visa_id);
CREATE INDEX source_record_mappings_source_idx ON public.source_record_mappings (source_dataset, source_table, source_record_id);
CREATE INDEX source_record_mappings_target_idx ON public.source_record_mappings (target_table, target_record_id);

-- API boundary: service tables are read-only to anon/authenticated; audit ledgers stay private.
ALTER TABLE public.source_documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.visa_requirements ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.visa_criterion_groups ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.visa_requirement_criteria ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.visa_scoring_models ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.visa_scoring_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.visa_process_stages ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.document_requirements ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.document_attachment_relations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.visa_quota_policies ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.visa_quota_snapshots ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.change_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.source_record_mappings ENABLE ROW LEVEL SECURITY;

CREATE POLICY "public read" ON public.source_documents FOR SELECT TO anon, authenticated USING (true);
CREATE POLICY "public read" ON public.visa_requirements FOR SELECT TO anon, authenticated USING (true);
CREATE POLICY "public read" ON public.visa_criterion_groups FOR SELECT TO anon, authenticated USING (true);
CREATE POLICY "public read" ON public.visa_requirement_criteria FOR SELECT TO anon, authenticated USING (true);
CREATE POLICY "public read" ON public.visa_scoring_models FOR SELECT TO anon, authenticated USING (true);
CREATE POLICY "public read" ON public.visa_scoring_items FOR SELECT TO anon, authenticated USING (true);
CREATE POLICY "public read" ON public.visa_process_stages FOR SELECT TO anon, authenticated USING (true);
CREATE POLICY "public read" ON public.document_requirements FOR SELECT TO anon, authenticated USING (true);
CREATE POLICY "public read" ON public.document_attachment_relations FOR SELECT TO anon, authenticated USING (true);
CREATE POLICY "public read" ON public.visa_quota_policies FOR SELECT TO anon, authenticated USING (true);
CREATE POLICY "public read" ON public.visa_quota_snapshots FOR SELECT TO anon, authenticated USING (true);
REVOKE ALL ON public.change_history, public.source_record_mappings FROM anon, authenticated;


