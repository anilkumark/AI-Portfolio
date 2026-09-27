-- Post-Market Drug Safety & Performance Platform — schema.
-- One Aurora PostgreSQL instance, three logical schemas:
--   operational  — case records, audit trail (source of truth)
--   omop         — the unified drug-performance view (derived, rebuildable)
--   coding       — MedDRA terminology corpus for coding suggestion

CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pgcrypto;  -- gen_random_uuid()

CREATE SCHEMA IF NOT EXISTS operational;
CREATE SCHEMA IF NOT EXISTS omop;
CREATE SCHEMA IF NOT EXISTS coding;

-- =====================================================================
-- OPERATIONAL — the case record created for every document processed
-- =====================================================================

CREATE TABLE IF NOT EXISTS operational.case_records (
    case_id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_type             TEXT NOT NULL CHECK (source_type IN ('case_report', 'ehr_extract')),
    received_at             TIMESTAMPTZ NOT NULL,   -- regulatory clock start — never modified after insert
    document_s3_path        TEXT NOT NULL,
    doc_type                TEXT,                    -- digital_pdf | scanned_fax | structured_form | email

    -- extracted clinical fields
    patient_age             INTEGER,
    patient_sex             TEXT,
    patient_weight_kg        NUMERIC(5,2),
    adverse_event_text      TEXT,
    adverse_event_meddra_code TEXT,                  -- set only after human confirmation
    suspect_product         TEXT,
    therapy_details          JSONB,
    concomitant_drugs        JSONB,
    medical_history           JSONB,

    field_confidence         JSONB,                  -- {"field_name": 0.0-1.0, ...}

    -- seriousness gate output
    seriousness_result       TEXT CHECK (seriousness_result IN ('serious', 'non_serious')),
    seriousness_criteria     TEXT[],                 -- which rule(s) fired, for audit

    -- review
    review_required          BOOLEAN NOT NULL DEFAULT false,
    review_priority          TEXT CHECK (review_priority IN ('priority', 'standard')),
    review_status             TEXT NOT NULL DEFAULT 'not_required'
                                CHECK (review_status IN ('not_required','pending','approved','rejected')),
    reviewer_id               TEXT,
    reviewed_at                TIMESTAMPTZ,

    -- submission
    submission_status         TEXT NOT NULL DEFAULT 'not_submitted'
                                CHECK (submission_status IN ('not_submitted','submitted','failed')),
    e2b_xml_s3_path           TEXT,
    submitted_at               TIMESTAMPTZ,

    -- dedup
    duplicate_of_case_id      UUID REFERENCES operational.case_records(case_id),

    -- version governance
    model_version              TEXT,
    prompt_version              TEXT,
    meddra_kb_version            TEXT,

    created_at                  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at                  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_case_received_at ON operational.case_records(received_at);
CREATE INDEX IF NOT EXISTS idx_case_review_status ON operational.case_records(review_status);
CREATE INDEX IF NOT EXISTS idx_case_suspect_product ON operational.case_records(suspect_product);

-- Append-only audit trail. Never UPDATE or DELETE — only INSERT.
CREATE TABLE IF NOT EXISTS operational.audit_log (
    audit_id     BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    case_id      UUID NOT NULL REFERENCES operational.case_records(case_id),
    event_type   TEXT NOT NULL CHECK (event_type IN
                   ('field_extracted','field_corrected','code_confirmed',
                    'seriousness_set','review_decided','submitted','dedup_linked')),
    actor        TEXT NOT NULL,       -- 'system' or the human reviewer's identity
    before_value TEXT,
    after_value  TEXT,
    occurred_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Reviewer approval queue (feeds the LangGraph interrupt/resume pattern)
CREATE TABLE IF NOT EXISTS operational.pending_reviews (
    case_id       UUID PRIMARY KEY REFERENCES operational.case_records(case_id),
    thread_id     TEXT NOT NULL UNIQUE,   -- LangGraph checkpoint thread id
    queued_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    priority      TEXT NOT NULL CHECK (priority IN ('priority','standard'))
);

-- Structured feed records that failed schema validation
CREATE TABLE IF NOT EXISTS operational.quarantine (
    quarantine_id  BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    batch_id       TEXT NOT NULL,
    raw_record     JSONB NOT NULL,
    failure_reason TEXT NOT NULL,
    quarantined_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- =====================================================================
-- CODING — MedDRA terminology corpus (embedded once at setup)
-- =====================================================================

CREATE TABLE IF NOT EXISTS coding.meddra_terms (
    term_id       TEXT PRIMARY KEY,        -- MedDRA PT code
    term_text     TEXT NOT NULL,
    soc           TEXT,                     -- system organ class, for grouping
    embedding     VECTOR(1024),
    term_tsv      TSVECTOR GENERATED ALWAYS AS (to_tsvector('english', term_text)) STORED,
    kb_version    TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_meddra_embedding
    ON coding.meddra_terms USING hnsw (embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS idx_meddra_tsv
    ON coding.meddra_terms USING GIN (term_tsv);

-- =====================================================================
-- OMOP — unified drug-performance view (derived, rebuildable)
-- Simplified subset of the standard OMOP CDM tables.
-- =====================================================================

CREATE TABLE IF NOT EXISTS omop.person (
    person_id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_record_id  UUID,          -- links back to the originating case or feed record
    source_type        TEXT NOT NULL,
    year_of_birth        INTEGER,
    sex                    TEXT
);

CREATE TABLE IF NOT EXISTS omop.condition_occurrence (
    condition_occurrence_id  BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    person_id                 UUID NOT NULL REFERENCES omop.person(person_id),
    source_record_id           UUID,
    condition_source_value     TEXT NOT NULL,   -- MedDRA term or raw text for EHR/feed
    condition_meddra_code       TEXT,
    condition_start_date         DATE
);

CREATE TABLE IF NOT EXISTS omop.drug_exposure (
    drug_exposure_id  BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    person_id           UUID NOT NULL REFERENCES omop.person(person_id),
    source_record_id     UUID,
    source_type            TEXT NOT NULL,   -- case_report | ehr_extract | structured_feed
    drug_source_value       TEXT NOT NULL,
    is_suspect_product       BOOLEAN NOT NULL DEFAULT false,
    exposure_start_date       DATE
);

CREATE TABLE IF NOT EXISTS omop.observation (
    observation_id     BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    person_id            UUID NOT NULL REFERENCES omop.person(person_id),
    source_record_id      UUID NOT NULL,
    observation_type        TEXT NOT NULL,   -- e.g. 'seriousness_result'
    value_as_string           TEXT,
    observation_date            DATE
);
