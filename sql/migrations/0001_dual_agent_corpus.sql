-- SPEC-1 Dual-Agent Corpus Builder MVP schema

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS batch (
  batch_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  params_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  status TEXT NOT NULL CHECK (status IN ('created','running','paused','completed','completed_with_errors','failed'))
);

CREATE TABLE IF NOT EXISTS item (
  item_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  batch_id UUID NOT NULL REFERENCES batch(batch_id) ON DELETE CASCADE,
  input_url TEXT NOT NULL,
  title_hint TEXT,
  date_hint TEXT,
  place_hint TEXT,
  status TEXT NOT NULL CHECK (status IN ('pending','normalizing','webscout_running','webscout_done','iconocode_running','done','retry_wait','failed')),
  hash TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS source (
  source_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  source_type TEXT NOT NULL CHECK (source_type IN ('primary_image','museum_record','academic_paper','legal_text','vocabulary')),
  title TEXT NOT NULL,
  publisher TEXT,
  year TEXT,
  url TEXT,
  accessed_at TIMESTAMPTZ,
  abnt_citation TEXT NOT NULL,
  raw_meta_json JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS item_source_link (
  item_id UUID NOT NULL REFERENCES item(item_id) ON DELETE CASCADE,
  source_id UUID NOT NULL REFERENCES source(source_id) ON DELETE CASCADE,
  relevance_score NUMERIC(4,3) NOT NULL CHECK (relevance_score >= 0 AND relevance_score <= 1),
  notes TEXT,
  PRIMARY KEY (item_id, source_id)
);

CREATE TABLE IF NOT EXISTS vocab_term (
  term_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  scheme TEXT NOT NULL CHECK (scheme IN ('iconclass','getty_aat','tgn','ulan','custom')),
  notation TEXT NOT NULL,
  label TEXT NOT NULL,
  uri TEXT
);

CREATE TABLE IF NOT EXISTS item_code (
  item_id UUID NOT NULL REFERENCES item(item_id) ON DELETE CASCADE,
  term_id UUID NOT NULL REFERENCES vocab_term(term_id) ON DELETE CASCADE,
  code_role TEXT NOT NULL CHECK (code_role IN ('depicts','attribute','context','style')),
  confidence NUMERIC(4,3) NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
  evidence_source_id UUID REFERENCES source(source_id) ON DELETE SET NULL,
  PRIMARY KEY (item_id, term_id, code_role)
);

CREATE TABLE IF NOT EXISTS claim (
  claim_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  item_id UUID NOT NULL REFERENCES item(item_id) ON DELETE CASCADE,
  claim_text TEXT NOT NULL,
  claim_type TEXT NOT NULL CHECK (claim_type IN ('iconographic','legal_context','dating','attribution','postcolonial_marker')),
  confidence NUMERIC(4,3) NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
  status TEXT NOT NULL CHECK (status IN ('supported','tentative','gap'))
);

CREATE TABLE IF NOT EXISTS claim_evidence (
  claim_id UUID NOT NULL REFERENCES claim(claim_id) ON DELETE CASCADE,
  source_id UUID NOT NULL REFERENCES source(source_id) ON DELETE CASCADE,
  supports BOOLEAN NOT NULL,
  quote_snippet TEXT CHECK (char_length(quote_snippet) <= 250),
  weight NUMERIC(4,3) NOT NULL CHECK (weight >= 0 AND weight <= 1),
  PRIMARY KEY (claim_id, source_id)
);

CREATE INDEX IF NOT EXISTS idx_item_batch_status ON item (batch_id, status);
CREATE INDEX IF NOT EXISTS idx_item_hash ON item (hash);
CREATE UNIQUE INDEX IF NOT EXISTS idx_source_url_unique ON source (url) WHERE url IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_vocab_term_scheme_notation ON vocab_term (scheme, notation);
