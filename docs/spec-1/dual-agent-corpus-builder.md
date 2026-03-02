# SPEC-1 — Dual-Agent Corpus Builder (WebScout → IconoCode)

This document defines an MVP-ready, batch-first architecture for building a traceable iconographic corpus focused on female allegories in legal culture (Brazil/Europe, XV–XX c.).

## 1) Scope and MVP goals

- Batch ingestion for 10–10,000 records.
- Resumable/idempotent item processing.
- Evidence-first interpretation: all non-trivial claims must cite sources or be marked as gaps.
- Structured outputs for:
  - WebScout input/output.
  - IconoCode 4-stage analysis and validation.
  - Exportable master record for thesis-ready reuse.

## 2) System architecture

### Components

1. **Ingestor**
   - Accepts batch manifests (`urls + hints`) and seed queries (e.g., Europeana query string).
2. **Orchestrator**
   - Maintains queue state, retries with exponential backoff, connector-specific rate limits, and resumability checks.
3. **WebScout workers**
   - Execute three-layer search packs (vocabulary, image repositories, legal/history collections).
4. **IconoCode workers**
   - Consume WebScout output + image references, produce four-stage coding/interpretation/validation.
5. **PostgreSQL**
   - Canonical storage for entities, links, claims, evidence ledger, and run metrics.
6. **Object storage**
   - Raw JSON snapshots (`webscout.json`, `iconocode.json`), optional thumbnails.
7. **Exporter**
   - Produces JSONL, CSV tables, ABNT bibliography bundle, and audit summary.

### Orchestration states

Per-item finite state machine:

- `pending` → `normalizing` → `webscout_running` → `webscout_done` → `iconocode_running` → `done`
- Error branches:
  - `*_running` → `retry_wait` (with backoff, capped retries)
  - `retry_wait` → `*_running`
  - terminal: `failed` (hard connector/config/data failures)

Batch-level states:

- `created` → `running` → (`paused` optional) → `completed` / `completed_with_errors` / `failed`

## 3) Layer packs

Layer packs are declarative bundles consumed by WebScout workers.

```json
{
  "name": "default-justice-pack-v1",
  "layers": [
    {
      "id": "vocabularies",
      "connectors": ["iconclass", "getty_sparql"],
      "enabled": true
    },
    {
      "id": "image_databases",
      "connectors": ["europeana_search", "europeana_record", "gallica_document"],
      "enabled": true
    },
    {
      "id": "legal_history_collections",
      "connectors": ["curated_catalogs"],
      "enabled": true
    }
  ]
}
```

## 4) Scoring formula (default)

`final_score = 0.25*term_overlap + 0.20*period_match + 0.15*geo_match + 0.15*authority + 0.15*metadata_completeness + 0.10*cross_source_agreement`

Each feature is normalized to `[0,1]`.

Hard boosts:

- `+0.05` if result includes institution-level canonical record.
- `+0.05` if result includes IIIF manifest or stable persistent identifier.

Hard penalties:

- `-0.10` for obvious metadata contradiction (period/country mismatch).
- `-0.10` for dead links / inaccessible records in two consecutive retries.

## 5) Validation policy (IconoCode)

A claim is:

- **supported** when either:
  - at least two independent sources agree, or
  - one primary institutional record + one secondary scholarly/legal source agree.
- **tentative** when only one source supports and no contradiction exists.
- **gap** when insufficient support, missing sources, or direct contradiction remains unresolved.

## 6) MasterRecord JSON shape

MasterRecord consolidates operational, evidence, and interpretation data per item.

```json
{
  "master_record_version": "1.0.0",
  "batch_id": "uuid",
  "item_id": "uuid",
  "item_hash": "sha256",
  "input": {
    "input_url": "https://...",
    "title_hint": "...",
    "date_hint": "...",
    "place_hint": "..."
  },
  "webscout": {
    "query": {"query_type": "seed|item", "target": "...", "context": {}, "constraints": {}},
    "search_results": [],
    "summary_evidence": "...",
    "gaps": []
  },
  "iconocode": {
    "pre_iconographic": [],
    "codes": [],
    "interpretation": [],
    "validation": {"claim_ledger": [], "confidence": 0.0}
  },
  "exports": {
    "abnt_citations": [],
    "audit_flags": []
  },
  "timestamps": {
    "created_at": "ISO-8601",
    "updated_at": "ISO-8601"
  }
}
```

## 7) Operational defaults

- Concurrency default: `8` workers.
- Batch starting size: `100` items.
- Max retries per connector call: `4`.
- Backoff: `2^attempt * base_ms` with jitter.
- Connector rate limits (token bucket):
  - iconclass: `5 req/s`
  - europeana: `5 req/s`
  - getty_sparql: `2 req/s`
  - gallica: `3 req/s`

## 8) Export set

Per batch:

- `records.jsonl` (master records)
- `codes.csv`
- `claims.csv`
- `claim_evidence.csv`
- `abnt_references.txt`
- `audit_summary.json`

## 9) Acceptance criteria (MVP)

- 100% processed items end in `done` or `failed` with explicit reason.
- 100% non-trivial claims have claim-evidence links or `gap` status.
- ABNT citation generated for each returned source item.
- Resumability proven by stopping and resuming a batch without duplicate item outputs.
