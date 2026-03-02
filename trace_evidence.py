#!/usr/bin/env python3
"""Evidence traceability report generator for dual-agent corpus builder."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict, Counter
from pathlib import Path
from typing import Any, Dict, List, Tuple


class EvidenceTracer:
    """Analyzes and reports on evidence traceability in corpus records."""
    
    def __init__(self):
        self.stats = {
            "total_records": 0,
            "total_claims": 0,
            "supported_claims": 0,
            "tentative_claims": 0,
            "gap_claims": 0,
            "claims_with_evidence": 0,
            "claims_without_evidence": 0,
            "total_sources": 0,
            "unique_sources": set(),
        }
        self.issues = []
        self.claim_details = []
    
    def trace_record(self, record: Dict[str, Any]) -> None:
        """Trace evidence for a single master record."""
        self.stats["total_records"] += 1
        
        # Extract claims from IconoCode interpretation
        iconocode = record.get("iconocode", {})
        claims = iconocode.get("interpretation", [])
        
        self.stats["total_claims"] += len(claims)
        
        # Map evidence IDs to source details
        webscout = record.get("webscout", {})
        evidence_map = {
            result["evidence_id"]: result
            for result in webscout.get("search_results", [])
        }
        
        self.stats["total_sources"] += len(evidence_map)
        for source in evidence_map.values():
            if "url" in source:
                self.stats["unique_sources"].add(source["url"])
        
        # Analyze validation ledger
        validation = iconocode.get("validation", {})
        claim_ledger = validation.get("claim_ledger", [])
        
        # Build evidence trace for each claim
        for i, claim in enumerate(claims):
            claim_text = claim["claim_text"]
            claim_type = claim["claim_type"]
            status = claim["status"]
            confidence = claim["confidence"]
            
            # Count by status
            if status == "supported":
                self.stats["supported_claims"] += 1
            elif status == "tentative":
                self.stats["tentative_claims"] += 1
            elif status == "gap":
                self.stats["gap_claims"] += 1
            
            # Find evidence in ledger
            ledger_entry = next(
                (entry for entry in claim_ledger if entry["claim_text"] == claim_text),
                None
            )
            
            has_evidence = False
            evidence_sources = []
            evidence_gaps = []
            
            if ledger_entry:
                supports = ledger_entry.get("supports", [])
                contradicts = ledger_entry.get("contradicts", [])
                gaps = ledger_entry.get("gaps", [])
                
                has_evidence = bool(supports or contradicts)
                evidence_sources = supports
                evidence_gaps = gaps
                
                if contradicts:
                    self.issues.append({
                        "item_id": record["item_id"],
                        "severity": "high",
                        "type": "contradiction",
                        "claim": claim_text,
                        "details": f"Contradictory evidence: {', '.join(contradicts)}"
                    })
            
            if has_evidence:
                self.stats["claims_with_evidence"] += 1
            else:
                self.stats["claims_without_evidence"] += 1
                
                # Issue: non-trivial claim without evidence
                if claim_type in ["iconographic", "legal_context", "postcolonial_marker"]:
                    self.issues.append({
                        "item_id": record["item_id"],
                        "severity": "medium",
                        "type": "missing_evidence",
                        "claim": claim_text,
                        "details": f"Non-trivial {claim_type} claim lacks evidence trace"
                    })
            
            # Issue: gap status but not properly documented
            if status == "gap" and not evidence_gaps:
                self.issues.append({
                    "item_id": record["item_id"],
                    "severity": "medium",
                    "type": "undocumented_gap",
                    "claim": claim_text,
                    "details": "Claim marked as gap but gaps not documented in ledger"
                })
            
            # Issue: low confidence without documented gaps
            if confidence < 0.60 and not evidence_gaps and status != "gap":
                self.issues.append({
                    "item_id": record["item_id"],
                    "severity": "low",
                    "type": "low_confidence",
                    "claim": claim_text,
                    "details": f"Confidence {confidence:.2f} but status is {status}"
                })
            
            # Store detailed trace
            self.claim_details.append({
                "item_id": record["item_id"],
                "claim_text": claim_text,
                "claim_type": claim_type,
                "status": status,
                "confidence": confidence,
                "evidence_sources": evidence_sources,
                "gaps": evidence_gaps,
                "traceable": has_evidence
            })
    
    def generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive evidence traceability report."""
        total_claims = self.stats["total_claims"]
        severity_counts = Counter(i["severity"] for i in self.issues)
        type_counts = Counter(i["type"] for i in self.issues)

        return {
            "summary": {
                "total_records": self.stats["total_records"],
                "total_claims": total_claims,
                "total_sources": self.stats["total_sources"],
                "unique_sources": len(self.stats["unique_sources"]),
                "traceability_rate": (
                    self.stats["claims_with_evidence"] / total_claims
                    if total_claims > 0 else 0.0
                ),
            },
            "claim_status_breakdown": {
                "supported": self.stats["supported_claims"],
                "tentative": self.stats["tentative_claims"],
                "gap": self.stats["gap_claims"],
                "supported_pct": (
                    self.stats["supported_claims"] / total_claims * 100
                    if total_claims > 0 else 0.0
                ),
                "gap_pct": (
                    self.stats["gap_claims"] / total_claims * 100
                    if total_claims > 0 else 0.0
                ),
            },
            "evidence_coverage": {
                "with_evidence": self.stats["claims_with_evidence"],
                "without_evidence": self.stats["claims_without_evidence"],
                "coverage_pct": (
                    self.stats["claims_with_evidence"] / total_claims * 100
                    if total_claims > 0 else 0.0
                ),
            },
            "issues": {
                "total": len(self.issues),
                "by_severity": {
                    "high": severity_counts["high"],
                    "medium": severity_counts["medium"],
                    "low": severity_counts["low"],
                },
                "by_type": dict(type_counts),
                "details": self.issues,
            },
            "claim_details": self.claim_details,
        }


def print_report_summary(report: Dict[str, Any], verbose: bool = False) -> None:
    """Print human-readable report summary."""
    summary = report["summary"]
    status = report["claim_status_breakdown"]
    coverage = report["evidence_coverage"]
    issues = report["issues"]
    
    print("=" * 70)
    print("EVIDENCE TRACEABILITY REPORT")
    print("=" * 70)
    print()
    
    print("CORPUS SUMMARY")
    print("-" * 70)
    print(f"  Records processed:        {summary['total_records']}")
    print(f"  Total claims:             {summary['total_claims']}")
    print(f"  Unique sources:           {summary['unique_sources']}")
    print(f"  Traceability rate:        {summary['traceability_rate']:.1%}")
    print()
    
    print("CLAIM STATUS BREAKDOWN")
    print("-" * 70)
    print(f"  Supported:                {status['supported']} ({status['supported_pct']:.1f}%)")
    print(f"  Tentative:                {status['tentative']}")
    print(f"  Gap:                      {status['gap']} ({status['gap_pct']:.1f}%)")
    print()
    
    print("EVIDENCE COVERAGE")
    print("-" * 70)
    print(f"  With evidence:            {coverage['with_evidence']} ({coverage['coverage_pct']:.1f}%)")
    print(f"  Without evidence:         {coverage['without_evidence']}")
    print()
    
    print("ISSUES")
    print("-" * 70)
    print(f"  Total issues:             {issues['total']}")
    print(f"    High severity:          {issues['by_severity']['high']}")
    print(f"    Medium severity:        {issues['by_severity']['medium']}")
    print(f"    Low severity:           {issues['by_severity']['low']}")
    print()
    
    if issues["by_type"]:
        print("  By type:")
        for issue_type, count in sorted(issues["by_type"].items()):
            print(f"    {issue_type:24s}  {count}")
        print()
    
    if verbose and issues["details"]:
        print("ISSUE DETAILS")
        print("-" * 70)
        for issue in issues["details"]:
            print(f"\n  [{issue['severity'].upper()}] {issue['type']}")
            print(f"  Item: {issue['item_id']}")
            print(f"  Claim: {issue['claim']}")
            print(f"  Details: {issue['details']}")
        print()
    
    # Acceptance criteria check
    print("MVP ACCEPTANCE CRITERIA")
    print("-" * 70)
    coverage_pct = coverage["coverage_pct"]
    gap_or_evidence = (
        (status["gap"] + coverage["with_evidence"]) / summary["total_claims"] * 100
        if summary["total_claims"] > 0 else 0.0
    )
    
    checks = [
        ("100% claims have evidence or gap status", gap_or_evidence >= 100.0),
        ("No high-severity issues", issues["by_severity"]["high"] == 0),
        ("Traceability rate > 80%", summary["traceability_rate"] >= 0.80),
    ]
    
    for criterion, passed in checks:
        status_mark = "✓" if passed else "✗"
        print(f"  {status_mark} {criterion}")
    
    print()
    all_passed = all(passed for _, passed in checks)
    if all_passed:
        print("✓ All acceptance criteria met")
    else:
        print("✗ Some acceptance criteria not met")
    print()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate evidence traceability report for corpus records"
    )
    parser.add_argument(
        "input",
        type=Path,
        help="JSONL file with master records"
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        help="Output JSON file for detailed report"
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show detailed issue list"
    )
    
    args = parser.parse_args()
    
    tracer = EvidenceTracer()
    
    # Process all records
    with args.input.open("r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
                tracer.trace_record(record)
            except json.JSONDecodeError as e:
                print(f"Warning: Skipping invalid JSON at line {line_num}: {e}")
    
    # Generate report
    report = tracer.generate_report()
    
    # Print summary
    print_report_summary(report, verbose=args.verbose)
    
    # Save detailed report
    if args.output:
        args.output.write_text(
            json.dumps(report, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        print(f"Detailed report saved to: {args.output}")


if __name__ == "__main__":
    main()
