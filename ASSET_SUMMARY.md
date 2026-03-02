# Dual-Agent Corpus Builder MVP — Asset Summary

This document summarizes the implementation assets for the batch-first, evidence-traceable corpus construction pipeline (WebScout → IconoCode).

## Architecture and Specification

### Core Documentation
- **[docs/spec-1/dual-agent-corpus-builder.md](docs/spec-1/dual-agent-corpus-builder.md)** (169 lines)
  - Complete architecture specification
  - Finite state machine for batch and item processing
  - Layer pack definitions for search connectors
  - Scoring formulas and validation policies
  - MasterRecord JSON structure
  - Operational defaults and MVP acceptance criteria

## Data Schemas

JSON Schema 2020-12 contracts for all pipeline stages:

- **[schemas/webscout-input.schema.json](schemas/webscout-input.schema.json)**  
  Query structure: `query_type`, `target`, `context`, `constraints`

- **[schemas/webscout-output.schema.json](schemas/webscout-output.schema.json)**  
  Search results with evidence IDs, source types, ABNT citations, ICONCLASS candidates, scores

- **[schemas/iconocode-output.schema.json](schemas/iconocode-output.schema.json)**  
  Four-stage analysis: pre-iconographic motifs, codes, interpretation claims, validation ledger

- **[schemas/master-record.schema.json](schemas/master-record.schema.json)**  
  Consolidated record combining input, WebScout, IconoCode, exports, and timestamps

## Database Migration

- **[sql/migrations/0001_dual_agent_corpus.sql](sql/migrations/0001_dual_agent_corpus.sql)** (96 lines)
  - PostgreSQL schema with UUID primary keys
  - Tables: `batch`, `item`, `source`, `vocab_term`, `item_code`, `claim`, `claim_evidence`
  - State machine support with CHECK constraints
  - Evidence linkage with `item_source_link` and `claim_evidence` joins
  - Indexes for batch/status queries and deduplication

## Utilities and Tooling

### 1. Schema Validation (`validate_schemas.py`) — 181 lines
**Purpose**: Validate JSON/JSONL files against schemas with detailed error reporting

**Features**:
- Supports all four schemas (webscout-input, webscout-output, iconocode-output, master-record)
- JSONL batch processing
- Verbose mode for debugging
- RefResolver for schema cross-references

**Usage**:
```bash
python validate_schemas.py records.jsonl --schema master-record -v
```

**Dependencies**: `jsonschema`

---

### 2. ABNT Citation Generator (`abnt_citations.py`) — 261 lines
**Purpose**: Generate ABNT NBR 6023:2018 citations from source metadata

**Features**:
- Supports 5 source types: `primary_image`, `museum_record`, `academic_paper`, `legal_text`, `vocabulary`
- Automatic author/publisher name normalization
- ISO-8601 access date formatting
- JSON and plain text output formats
- Processes WebScout output and MasterRecords

**Usage**:
```bash
python abnt_citations.py master_record.json -o references.txt
python abnt_citations.py webscout_output.json --format json
```

**Sample Output**:
```
MUSEU NACIONAL DE BELAS ARTES. **Alegoria da Justiça (séc. XVIII)**. 2024. Disponível em: <https://example.org/museum/item/12345>. Acesso em: 02 mar. 2026.
```

---

### 3. Batch Example Generator (`batch_example.py`) — 369 lines
**Purpose**: Create realistic example batches for testing and demonstration

**Features**:
- Generates complete WebScout → IconoCode pipeline artifacts
- UUID generation and SHA256 hashing for deduplication
- Parametric context/constraint construction
- Example data with Brazilian/Portuguese legal allegories
- Creates 7 output files per batch

**Usage**:
```bash
python batch_example.py --output-dir examples/pilot --batch-name "Test Run"
```

**Generated Files**:
- `batch_manifest.json` — Batch metadata and item list
- `webscout_input_*.json` — Query inputs
- `webscout_output_*.json` — Search results with evidence
- `iconocode_output_*.json` — Four-stage coding/interpretation
- `master_record_*.json` — Consolidated records
- `records.jsonl` — JSONL export
- `citations.txt` — ABNT bibliography (via separate command)

---

### 4. Evidence Traceability Analyzer (`trace_evidence.py`) — 323 lines
**Purpose**: Audit evidence coverage and validate MVP acceptance criteria

**Features**:
- Claim status breakdown (supported/tentative/gap)
- Evidence coverage calculation
- Issue detection: missing evidence, contradictions, low confidence, undocumented gaps
- Severity classification (high/medium/low)
- MVP acceptance criteria validation
- Detailed JSON report export

**Usage**:
```bash
python trace_evidence.py records.jsonl -o audit_report.json -v
```

**Output Sections**:
- Corpus summary (traceability rate, unique sources)
- Claim status breakdown (percentages)
- Evidence coverage
- Issue catalog by type and severity
- MVP acceptance criteria checks

**Acceptance Criteria**:
- ✓ 100% claims have evidence or gap status
- ✓ No high-severity issues
- ✓ Traceability rate > 80%

---

### 5. Feminist Network Extractor (`extract_feminist_network.py`) — 190 lines
**Purpose**: Extract ICONCLASS subtrees with thematic feminist/postcolonial anchors

**Features**:
- Recursive subtree traversal from notation root
- Bridge notation for feminist association edges
- Multilingual label support (pt, en, es, fr, de, cz, fi, nl, zh)
- JSON network output (nodes + edges)
- Group categorization (justice_subtree, feminist_anchor)

**Usage**:
```bash
python extract_feminist_network.py \
  --root 48C51 \
  --feminist-notation 31AA231 \
  --bridge-notation 48C514 \
  --lang pt \
  --output feminist_network_48C51_pt.json
```

**Example Output**:
```json
{
  "root": "48C51",
  "root_label": "Justice (allegory)",
  "subtree_size": 42,
  "nodes": [...],
  "edges": [...]
}
```

---

## Demonstration Workflow

Complete example batch created and tested:

```bash
# 1. Generate batch
$ python3 batch_example.py --output-dir examples/batch_001
✓ Example batch created in examples/batch_001
  
# 2. Extract ABNT citations
$ python3 abnt_citations.py examples/batch_001/master_record_*.json \
    -o examples/batch_001/citations.txt
Generated 2 citation(s) → examples/batch_001/citations.txt

# 3. Run evidence trace
$ python3 trace_evidence.py examples/batch_001/records.jsonl
======================================================================
EVIDENCE TRACEABILITY REPORT
======================================================================
  Records processed:        1
  Total claims:             2
  Unique sources:           2
  Traceability rate:        0.0%
  ...
```

**Files Generated**:
- `examples/batch_001/batch_manifest.json`
- `examples/batch_001/webscout_input_*.json`
- `examples/batch_001/webscout_output_*.json`
- `examples/batch_001/iconocode_output_*.json`
- `examples/batch_001/master_record_*.json`
- `examples/batch_001/records.jsonl`
- `examples/batch_001/citations.txt`

---

## Implementation Status

| Component | Status | Notes |
|-----------|--------|-------|
| Architecture spec | ✅ Complete | SPEC-1 with state machine, scoring, validation |
| JSON schemas | ✅ Complete | 4 schemas with RefResolver support |
| PostgreSQL migration | ✅ Complete | Evidence-traceable relational schema |
| Schema validator | ✅ Complete | jsonschema-based with JSONL support |
| ABNT citation generator | ✅ Complete | 5 source types, NBR 6023:2018 compliant |
| Batch example generator | ✅ Complete | Full pipeline artifact creation |
| Evidence tracer | ✅ Complete | MVP acceptance criteria validation |
| Feminist network extractor | ✅ Complete | Thematic subtree + bridge notation |
| README documentation | ✅ Complete | Quick start, usage examples, dependencies |

---

## Technical Dependencies

### Required
- Python 3.8+
- PostgreSQL 12+ (with `pgcrypto` extension for UUID generation)

### Optional
- `jsonschema` (for schema validation utility)

---

## Research Application

This implementation package supports:

1. **Batch-first corpus construction** for 10–10,000 iconographic items
2. **Evidence-first interpretation** with source-claim linkage
3. **ABNT-ready academic output** for Brazilian thesis requirements
4. **Resumable/idempotent processing** with deduplication via SHA256 hashing
5. **Postcolonial/feminist analysis** via thematic network extraction
6. **Audit-ready validation** with traceability reports

Target domain: **Female legal allegories in Brazil/Europe (XV–XX c.)** with ICONCLASS vocabulary integration.

---

## File Inventory

### Documentation
- `docs/spec-1/dual-agent-corpus-builder.md`
- `README.md` (updated with dual-agent section)
- `ASSET_SUMMARY.md` (this file)

### Schemas
- `schemas/webscout-input.schema.json`
- `schemas/webscout-output.schema.json`
- `schemas/iconocode-output.schema.json`
- `schemas/master-record.schema.json`

### Database
- `sql/migrations/0001_dual_agent_corpus.sql`

### Utilities
- `validate_schemas.py` (181 lines, executable)
- `abnt_citations.py` (261 lines, executable)
- `batch_example.py` (369 lines, executable)
- `trace_evidence.py` (323 lines, executable)
- `extract_feminist_network.py` (190 lines, executable)

### Examples
- `examples/batch_001/` (7 generated files)

**Total new files**: 13 (excluding examples)  
**Total lines of code**: ~1,324 (utilities only)

---

## Next Steps

For production deployment:

1. Install PostgreSQL and run migration: `psql < sql/migrations/0001_dual_agent_corpus.sql`
2. Install Python dependencies: `pip install jsonschema`
3. Implement WebScout workers (Europeana, Gallica, Getty, ICONCLASS connectors)
4. Implement IconoCode workers (four-stage analysis pipeline)
5. Implement orchestrator with queue management and backoff
6. Integrate with object storage for JSON snapshots
7. Build exporter for CSV tables + audit bundle

---

**Version**: MVP 1.0.0  
**Date**: 2 March 2026  
**License**: See repository LICENSE file
