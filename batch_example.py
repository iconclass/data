#!/usr/bin/env python3
"""Example batch processor demonstrating dual-agent corpus builder workflow."""

from __future__ import annotations

import argparse
import hashlib
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


def generate_item_hash(input_url: str, title_hint: str = "", date_hint: str = "") -> str:
    """Generate SHA256 hash for item deduplication."""
    content = f"{input_url}|{title_hint}|{date_hint}"
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def create_batch_manifest(items: List[Dict[str, str]], batch_name: str) -> Dict[str, Any]:
    """Create a batch manifest for processing.
    
    Args:
        items: List of dicts with keys: input_url, title_hint, date_hint, place_hint
        batch_name: Human-readable batch identifier
        
    Returns:
        Batch manifest with metadata and item list
    """
    batch_id = str(uuid.uuid4())
    
    batch = {
        "batch_id": batch_id,
        "name": batch_name,
        "created_at": datetime.now().isoformat(),
        "params": {
            "layer_pack": "default-justice-pack-v1",
            "concurrency": 8,
            "max_retries": 4,
            "scoring_formula": "default"
        },
        "status": "created",
        "items": []
    }
    
    for item_input in items:
        item_id = str(uuid.uuid4())
        item_hash = generate_item_hash(
            item_input["input_url"],
            item_input.get("title_hint", ""),
            item_input.get("date_hint", "")
        )
        
        batch["items"].append({
            "item_id": item_id,
            "batch_id": batch_id,
            "input_url": item_input["input_url"],
            "title_hint": item_input.get("title_hint"),
            "date_hint": item_input.get("date_hint"),
            "place_hint": item_input.get("place_hint"),
            "status": "pending",
            "hash": item_hash
        })
    
    return batch


def create_webscout_input(item: Dict[str, Any]) -> Dict[str, Any]:
    """Generate WebScout input from item metadata."""
    context = {}
    constraints = {
        "max_results": 50,
        "must_have_image": True,
        "must_have_institution": False
    }
    
    # Extract context from hints
    if item.get("date_hint"):
        context["period"] = item["date_hint"]
    if item.get("place_hint"):
        context["region"] = item["place_hint"]
    
    context["languages"] = ["pt", "en", "es", "fr"]
    
    return {
        "query_type": "item",
        "target": item.get("title_hint") or item["input_url"],
        "context": context,
        "constraints": constraints
    }


def create_example_webscout_output() -> Dict[str, Any]:
    """Create example WebScout output for demonstration."""
    return {
        "search_results": [
            {
                "evidence_id": str(uuid.uuid4()),
                "source_type": "museum_record",
                "title": "Alegoria da Justiça (séc. XVIII)",
                "url": "https://example.org/museum/item/12345",
                "abnt_citation": "MUSEU NACIONAL DE BELAS ARTES. **Alegoria da Justiça (séc. XVIII)**. 2024. Disponível em: <https://example.org/museum/item/12345>. Acesso em: 02 mar. 2026.",
                "iconclass_candidates": ["48C514", "31AA231"],
                "notes": "Pintura a óleo, escola portuguesa",
                "score": 0.85
            },
            {
                "evidence_id": str(uuid.uuid4()),
                "source_type": "vocabulary",
                "title": "Justice (allegory)",
                "url": "https://iconclass.org/48C514",
                "abnt_citation": "ICONCLASS. **Justice (allegory)**. Notação: 48C514. 2024. Disponível em: <https://iconclass.org/48C514>. Acesso em: 02 mar. 2026.",
                "iconclass_candidates": ["48C514"],
                "notes": "ICONCLASS definition",
                "score": 0.95
            }
        ],
        "summary_evidence": "Encontrados 2 resultados relevantes com correspondência iconográfica ICONCLASS 48C514 (Justice).",
        "gaps": [
            "Informações sobre contexto legal brasileiro limitadas",
            "Necessário verificar atribuição autoral"
        ]
    }


def create_example_iconocode_output() -> Dict[str, Any]:
    """Create example IconoCode output for demonstration."""
    return {
        "pre_iconographic": [
            {"motif": "female figure", "observed": True, "notes": "Central figure, classical dress"},
            {"motif": "scales", "observed": True, "notes": "Right hand, balanced position"},
            {"motif": "sword", "observed": True, "notes": "Left hand, pointing downward"},
            {"motif": "blindfold", "observed": False, "notes": "Eyes open, not blindfolded"}
        ],
        "codes": [
            {
                "scheme": "iconclass",
                "notation": "48C514",
                "label": "Justice (allegory)",
                "code_role": "depicts",
                "confidence": 0.95,
                "evidence_source_id": None
            },
            {
                "scheme": "iconclass",
                "notation": "31AA231",
                "label": "woman standing",
                "code_role": "attribute",
                "confidence": 0.90,
                "evidence_source_id": None
            }
        ],
        "interpretation": [
            {
                "claim_text": "Representação alegórica da Justiça sem venda nos olhos, típica do período colonial português",
                "claim_type": "iconographic",
                "status": "tentative",
                "confidence": 0.75
            },
            {
                "claim_text": "Obra datada entre 1750-1800 com base no estilo pictórico",
                "claim_type": "dating",
                "status": "tentative",
                "confidence": 0.65
            }
        ],
        "validation": {
            "claim_ledger": [
                {
                    "claim_text": "Representação alegórica da Justiça",
                    "supports": ["ICONCLASS definition", "Museum catalog"],
                    "contradicts": [],
                    "gaps": ["Análise iconográfica comparativa necessária"]
                }
            ]
        },
        "confidence": 0.78
    }


def create_master_record(
    batch_id: str,
    item: Dict[str, Any],
    webscout_output: Dict[str, Any],
    iconocode_output: Dict[str, Any]
) -> Dict[str, Any]:
    """Assemble a complete master record."""
    abnt_citations = [
        result["abnt_citation"]
        for result in webscout_output.get("search_results", [])
        if "abnt_citation" in result
    ]
    
    audit_flags = []
    if webscout_output.get("gaps"):
        audit_flags.append(f"WebScout gaps: {len(webscout_output['gaps'])}")
    if iconocode_output.get("confidence", 1.0) < 0.70:
        audit_flags.append(f"Low confidence: {iconocode_output['confidence']:.2f}")
    
    return {
        "master_record_version": "1.0.0",
        "batch_id": batch_id,
        "item_id": item["item_id"],
        "item_hash": item["hash"],
        "input": {
            "input_url": item["input_url"],
            "title_hint": item.get("title_hint"),
            "date_hint": item.get("date_hint"),
            "place_hint": item.get("place_hint")
        },
        "webscout": webscout_output,
        "iconocode": iconocode_output,
        "exports": {
            "abnt_citations": abnt_citations,
            "audit_flags": audit_flags
        },
        "timestamps": {
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate example batch for dual-agent corpus builder"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("examples/batch_001"),
        help="Output directory for example files"
    )
    parser.add_argument(
        "--batch-name",
        default="Female Legal Allegories - Pilot Batch",
        help="Human-readable batch name"
    )
    
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    
    # Create example items
    example_items = [
        {
            "input_url": "https://example.org/museum/item/12345",
            "title_hint": "Alegoria da Justiça",
            "date_hint": "XVIII century",
            "place_hint": "Brasil"
        },
        {
            "input_url": "https://example.org/archive/document/67890",
            "title_hint": "Themis na iconografia jurídica",
            "date_hint": "XIX century",
            "place_hint": "Portugal"
        }
    ]
    
    # 1. Create batch manifest
    print(f"Creating batch manifest: {args.batch_name}")
    batch = create_batch_manifest(example_items, args.batch_name)
    batch_file = args.output_dir / "batch_manifest.json"
    batch_file.write_text(json.dumps(batch, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  ✓ {batch_file}")
    
    # 2. Create WebScout input for first item
    item = batch["items"][0]
    webscout_input = create_webscout_input(item)
    webscout_input_file = args.output_dir / f"webscout_input_{item['item_id']}.json"
    webscout_input_file.write_text(
        json.dumps(webscout_input, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    print(f"  ✓ {webscout_input_file}")
    
    # 3. Create example WebScout output
    webscout_output = create_example_webscout_output()
    webscout_output_file = args.output_dir / f"webscout_output_{item['item_id']}.json"
    webscout_output_file.write_text(
        json.dumps(webscout_output, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    print(f"  ✓ {webscout_output_file}")
    
    # 4. Create example IconoCode output
    iconocode_output = create_example_iconocode_output()
    iconocode_output_file = args.output_dir / f"iconocode_output_{item['item_id']}.json"
    iconocode_output_file.write_text(
        json.dumps(iconocode_output, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    print(f"  ✓ {iconocode_output_file}")
    
    # 5. Create master record
    master_record = create_master_record(
        batch["batch_id"],
        item,
        webscout_output,
        iconocode_output
    )
    master_record_file = args.output_dir / f"master_record_{item['item_id']}.json"
    master_record_file.write_text(
        json.dumps(master_record, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    print(f"  ✓ {master_record_file}")
    
    # 6. Create records.jsonl with all items (for this example, just one)
    records_file = args.output_dir / "records.jsonl"
    with records_file.open("w", encoding="utf-8") as f:
        f.write(json.dumps(master_record, ensure_ascii=False) + "\n")
    print(f"  ✓ {records_file}")
    
    print(f"\n✓ Example batch created in {args.output_dir}")
    print(f"\nNext steps:")
    print(f"  1. Validate schemas:")
    print(f"     python validate_schemas.py {master_record_file} --schema master-record")
    print(f"  2. Extract ABNT citations:")
    print(f"     python abnt_citations.py {master_record_file} -o {args.output_dir}/citations.txt")
    print(f"  3. Run evidence trace:")
    print(f"     python trace_evidence.py {records_file}")


if __name__ == "__main__":
    main()
