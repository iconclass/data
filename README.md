# ICONCLASS

Please use the following to cite:

```
H. van de Waal, Iconclass, an iconographic classification system. Completed and edited by L.D. Couprie, E. Tholen & G. Vellekoop. (Amsterdam, 1972-1985). online edition by E. Posthumus & J.P.J. Brandhorst, 2024. https://iconclass.org/
```

[![DOI](https://zenodo.org/badge/350851584.svg)](https://zenodo.org/badge/latestdoi/350851584)

A multilingual subject classification system for cultural content
For more information see: http://www.iconclass.org/

Made by Hans Brandhorst <jpjbrand@xs4all.nl> & Etienne Posthumus <eposthumus@gmail.com>

    ...with lots of support from a global cast of many, many people since 1972.

## Data file

This repository contains the main data files for the ICONCLASS system. It is a collection of simple structured text files, dating back in concept to the late nineties of the previous century.

### Structure

The structure is determined by the file `notations.txt`.

For example, the file looks like:

```
N 1
C 10
; 11
; 12
; 13
; 14
$
N 10
$
```

This is a chunk of data (each chunk is separated by a single $ character on its own line)
The first part of a line, up to the first space, is the field name. If there are multi-valued fields, in other words, more than one value for a field, it is listed on a different line starting with a `;` character,followed by a space and the field value. The above snippet, is roughly equivalent to the following JSON value:

```javascript
[
    {N: "1",
     C: ["10", "11", "12", "13", "14"]},
    {N: "10}
]
```

## Why not use a standard Knowledge Management System?

You might wonder why we can not simply use a standard system to manage vocabularies or classification systems. If IC has a SKOS version, surely we can just use a SKOS editor?

Alas, no. The ["base" ICONCLASS system](notations.txt) has around 40K nodes arranged in a tree. But then there are several "sub-trees" that are switched on and off at various parts of the base tree. These so-called "keys" in the IC causes an explosion to more than 1 million nodes in the system, which would make it very [tricky to maintain in a traditional system](https://iconclass.org/help/skos_sparql).

![Keys to 25F](/misc/key_to_25F.jpg)

A further complication is the use of WITH-NAMES placeholders in tree, also known as _bracketed text_. These notations look like 11H(...) where the ... can be filled in with any valid entry that makes sense to the user using that particular node in the tree. In the example, 11H(...) are male saints, so that could be 11H(JOHN) - but this could be in any language or variant. In the printed volumes for IC, several entries were already filled in as a convenience, and over the years some items have been added to the "official" list.

This also causes a problem when we create static _dumps_ of the IC system, for example in RDF as it creates very large files.

## Dual-Agent Corpus Builder (WebScout → IconoCode)

This repository includes a complete MVP implementation for batch-first, evidence-traceable iconographic corpus construction. The dual-agent pipeline enables systematic analysis of visual culture with rigorous source validation and ABNT-ready academic output.

### Architecture Assets

- **Specification**: [`docs/spec-1/dual-agent-corpus-builder.md`](docs/spec-1/dual-agent-corpus-builder.md)  
  Complete architecture, state machine, scoring formulas, validation policies, and operational defaults.

- **JSON Schemas**: [`schemas/*.schema.json`](schemas/)  
  - `webscout-input.schema.json` — Query structure for search workers  
  - `webscout-output.schema.json` — Search results with evidence ledger  
  - `iconocode-output.schema.json` — Four-stage iconographic coding  
  - `master-record.schema.json` — Consolidated batch item record  

- **Database Migration**: [`sql/migrations/0001_dual_agent_corpus.sql`](sql/migrations/0001_dual_agent_corpus.sql)  
  PostgreSQL schema with batch, item, source, claim, and evidence tables.

### Utilities

#### 1. Schema Validation

Validate JSON records against the defined schemas:

```bash
python validate_schemas.py records.json --schema master-record
python validate_schemas.py webscout_output.jsonl --schema webscout-output -v
```

**Dependencies**: `pip install jsonschema`

#### 2. ABNT Citation Generator

Extract and format ABNT NBR 6023:2018 citations from WebScout/IconoCode outputs:

```bash
# From master record
python abnt_citations.py master_record.json -o references.txt

# From WebScout output (JSON format)
python abnt_citations.py webscout_output.json --format json -o citations.json
```

Supports source types: `primary_image`, `museum_record`, `academic_paper`, `legal_text`, `vocabulary`.

#### 3. Evidence Traceability Report

Analyze evidence coverage and validate MVP acceptance criteria:

```bash
python trace_evidence.py records.jsonl -o audit_report.json -v
```

Checks:
- 100% of non-trivial claims have evidence or explicit gap markers  
- Contradiction detection  
- Low-confidence alerts  
- ABNT citation completeness  

#### 4. Batch Example Generator

Create sample batch with complete WebScout/IconoCode cycle:

```bash
python batch_example.py --output-dir examples/pilot_batch --batch-name "Test Batch"
```

Generates:
- `batch_manifest.json` — Batch metadata and item list  
- `webscout_input_*.json` — Search query inputs  
- `webscout_output_*.json` — Example search results  
- `iconocode_output_*.json` — Example coding/interpretation  
- `master_record_*.json` — Consolidated records  
- `records.jsonl` — JSONL export for batch processing  

### Feminist Network Extraction

Extract ICONCLASS subtrees with thematic anchors for feminist/postcolonial analysis:

```bash
python extract_feminist_network.py \
  --root 48C51 \
  --feminist-notation 31AA231 \
  --bridge-notation 48C514 \
  --lang pt \
  --output feminist_network_48C51_pt.json
```

### Quick Start Workflow

```bash
# 1. Generate example batch
python batch_example.py

# 2. Validate master record
python validate_schemas.py examples/batch_001/master_record_*.json --schema master-record

# 3. Extract ABNT citations
python abnt_citations.py examples/batch_001/master_record_*.json -o citations.txt

# 4. Run evidence trace report
python trace_evidence.py examples/batch_001/records.jsonl -o audit.json -v

# 5. Check feminist network
python extract_feminist_network.py --lang pt
```

### Database Setup

```bash
psql -U postgres -d iconclass_corpus < sql/migrations/0001_dual_agent_corpus.sql
```

### MVP Acceptance Criteria

Per SPEC-1, the implementation must satisfy:

- [x] All items end in `done` or `failed` with explicit reason  
- [x] 100% of non-trivial claims linked to evidence or marked as `gap`  
- [x] ABNT citation generated for each source item  
- [x] Batch resumability without duplicate outputs  
- [x] Evidence traceability validation tooling  

### Related Files

- `make_index.py`, `make_skos.py`, `make_sqlite.py` — ICONCLASS transformation utilities  
- `kw/` — Multilingual keyword files (cz, de, en, es, fi, fr, it, nl, pt, zh)  
- `txt/` — Localized label text files  
- `notations.txt` — ICONCLASS hierarchical structure  

---

For implementation questions or contributions related to the dual-agent corpus builder, see [`docs/spec-1/dual-agent-corpus-builder.md`](docs/spec-1/dual-agent-corpus-builder.md).
