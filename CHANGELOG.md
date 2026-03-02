# CHANGELOG — Dual-Agent Corpus Builder MVP

## [1.0.0] - 2026-03-02

### Added

#### Architecture & Specification
- Complete dual-agent corpus builder specification (`docs/spec-1/dual-agent-corpus-builder.md`)
  - Batch-first architecture with resumable processing
  - WebScout → IconoCode pipeline with state machine
  - Evidence-first validation policies
  - ABNT-ready output requirements
  - MVP acceptance criteria

#### Data Schemas (JSON Schema 2020-12)
- `schemas/webscout-input.schema.json` — Search query structure
- `schemas/webscout-output.schema.json` — Search results with evidence ledger
- `schemas/iconocode-output.schema.json` — Four-stage iconographic analysis
- `schemas/master-record.schema.json` — Consolidated batch item record

#### Database Migration
- `sql/migrations/0001_dual_agent_corpus.sql` — PostgreSQL schema
  - Evidence-traceable relational model
  - Batch/item state machine support
  - Source-claim linkage tables
  - ABNT citation storage
  - UUID primary keys with deduplication indexes

#### Utilities & Tooling
- `validate_schemas.py` — JSON/JSONL schema validation with RefResolver
- `abnt_citations.py` — ABNT NBR 6023:2018 citation generator (5 source types)
- `batch_example.py` — Complete batch demonstration generator
- `trace_evidence.py` — Evidence traceability audit and MVP validation
- `extract_feminist_network.py` — ICONCLASS subtree + thematic bridge extraction

#### Documentation
- Updated `README.md` with comprehensive dual-agent section
  - Quick start workflow
  - Utility usage examples
  - Database setup instructions
  - MVP acceptance criteria checklist
- Added `ASSET_SUMMARY.md` with detailed implementation inventory

#### Examples
- `examples/batch_001/` — Generated demonstration batch
  - Batch manifest with 2 sample items
  - Complete WebScout/IconoCode cycle artifacts
  - Master records and JSONL export
  - ABNT citations output

### Features

#### Batch Processing
- Idempotent item processing with SHA256 deduplication
- Resumable batch execution
- State machine: `pending` → `normalizing` → `webscout_running` → `webscout_done` → `iconocode_running` → `done`
- Retry logic with exponential backoff

#### Evidence Traceability
- 100% claim-to-source linkage requirement
- Explicit gap documentation for insufficient evidence
- Contradiction detection
- Multi-source validation (institutional + scholarly)

#### ABNT Citation Support
- Automatic citation generation from metadata
- Support for museum records, academic papers, legal texts, vocabularies
- ISO-8601 access date formatting
- Portuguese/multilingual support

#### Feminist/Postcolonial Analysis
- Thematic network extraction from ICONCLASS
- Bridge notation for cross-hierarchy associations
- Multilingual label support (pt, en, es, fr, de, cz, fi, nl, zh)
- Female allegory + justice/legal iconography focus

### Technical Details

- **Language**: Python 3.8+ (type hints, dataclasses-friendly)
- **Database**: PostgreSQL 12+ with `pgcrypto` extension
- **Schema Standard**: JSON Schema 2020-12
- **Citation Standard**: ABNT NBR 6023:2018
- **Vocabulary**: ICONCLASS iconographic classification

### Dependencies

**Required**:
- Python 3.8+
- PostgreSQL 12+

**Optional**:
- `jsonschema` (for validation utility)

### Research Context

Target domain: **Female legal allegories in Brazilian and European visual culture (XV–XX centuries)**

Research goals:
- Evidence-traceable iconographic corpus construction
- Batch processing of museum/archive collections
- ABNT-compliant academic output for thesis integration
- Postcolonial feminist analysis of legal iconography
- ICONCLASS vocabulary integration with thematic bridges

### Files Changed

```
docs/spec-1/dual-agent-corpus-builder.md      +169 lines
schemas/webscout-input.schema.json            +35 lines
schemas/webscout-output.schema.json           +42 lines
schemas/iconocode-output.schema.json          +94 lines
schemas/master-record.schema.json             +60 lines
sql/migrations/0001_dual_agent_corpus.sql     +96 lines
validate_schemas.py                            +181 lines (new)
abnt_citations.py                              +261 lines (new)
batch_example.py                               +369 lines (new)
trace_evidence.py                              +323 lines (new)
extract_feminist_network.py                    +190 lines (new)
README.md                                      ~120 lines modified
ASSET_SUMMARY.md                               +421 lines (new)
CHANGELOG.md                                   +148 lines (new, this file)
```

**Total additions**: ~2,509 lines across 14 files

### Testing

✅ Batch example generation verified  
✅ ABNT citation extraction verified  
✅ Evidence traceability analysis verified  
✅ All Python utilities executable  
✅ Example files validate against schemas (requires `jsonschema` install)

### MVP Status

| Acceptance Criterion | Status |
|---------------------|--------|
| 100% items end in done/failed with reason | ✅ State machine enforced |
| 100% claims have evidence or gap marker | ✅ Validation utility implemented |
| ABNT citation per source | ✅ Generator implemented |
| Batch resumability proven | ✅ Deduplication via hash |
| Evidence traceability tooling | ✅ Audit reports implemented |

---

**For detailed asset inventory, see**: `ASSET_SUMMARY.md`  
**For architecture specification, see**: `docs/spec-1/dual-agent-corpus-builder.md`  
**For usage examples, see**: `README.md` (Dual-Agent Corpus Builder section)
