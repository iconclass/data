#!/usr/bin/env python3
"""ABNT citation generator for dual-agent corpus builder sources."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


def normalize_name(name: str) -> str:
    """Normalize author/organization name for ABNT format."""
    name = name.strip()
    if not name:
        return ""
    
    # If it's an organization (contains institutional keywords), use uppercase
    org_keywords = ["museum", "biblioteca", "library", "foundation", "institute", "archives", "center"]
    if any(keyword in name.lower() for keyword in org_keywords):
        return name.upper()
    
    # Personal name: try to format as SURNAME, Given names
    parts = name.split()
    if len(parts) > 1:
        # Simple heuristic: last part is surname
        return f"{parts[-1].upper()}, {' '.join(parts[:-1])}"
    return name.upper()


def format_abnt_web_source(
    title: str,
    publisher: Optional[str],
    year: Optional[str],
    url: str,
    accessed_at: str,
    **kwargs
) -> str:
    """Format a web source in ABNT NBR 6023:2018 style.
    
    Args:
        title: Document title
        publisher: Publisher/institution name
        year: Publication year
        url: Document URL
        accessed_at: ISO-8601 access timestamp
        
    Returns:
        ABNT-formatted citation string
    """
    parts = []
    
    # Publisher/Author (if available)
    if publisher:
        parts.append(f"{normalize_name(publisher)}.")
    
    # Title in bold (we'll use double asterisks for markdown/plain text)
    parts.append(f"**{title}**.")
    
    # Year
    if year:
        parts.append(f"{year}.")
    
    # URL and access date
    try:
        access_date = datetime.fromisoformat(accessed_at.replace('Z', '+00:00'))
        access_formatted = access_date.strftime("%d %b. %Y").lower()
    except (ValueError, AttributeError):
        access_formatted = "data desconhecida"
    
    parts.append(f"Disponível em: <{url}>. Acesso em: {access_formatted}.")
    
    return " ".join(parts)


def format_abnt_museum_record(
    title: str,
    publisher: str,
    year: Optional[str],
    url: str,
    accessed_at: str,
    **kwargs
) -> str:
    """Format a museum/institutional record."""
    return format_abnt_web_source(title, publisher, year, url, accessed_at)


def format_abnt_academic_paper(
    title: str,
    author: Optional[str],
    journal: Optional[str],
    year: Optional[str],
    url: str,
    accessed_at: str,
    **kwargs
) -> str:
    """Format an academic paper citation."""
    parts = []
    
    if author:
        parts.append(f"{normalize_name(author)}.")
    
    parts.append(f"{title}.")
    
    if journal:
        parts.append(f"**{journal}**,")
    
    if year:
        parts.append(f"{year}.")
    
    try:
        access_date = datetime.fromisoformat(accessed_at.replace('Z', '+00:00'))
        access_formatted = access_date.strftime("%d %b. %Y").lower()
    except (ValueError, AttributeError):
        access_formatted = "data desconhecida"
    
    parts.append(f"Disponível em: <{url}>. Acesso em: {access_formatted}.")
    
    return " ".join(parts)


def format_abnt_legal_text(
    title: str,
    jurisdiction: Optional[str],
    year: Optional[str],
    url: str,
    accessed_at: str,
    **kwargs
) -> str:
    """Format a legal text citation."""
    parts = []
    
    if jurisdiction:
        parts.append(f"{normalize_name(jurisdiction)}.")
    
    parts.append(f"{title}.")
    
    if year:
        parts.append(f"{year}.")
    
    try:
        access_date = datetime.fromisoformat(accessed_at.replace('Z', '+00:00'))
        access_formatted = access_date.strftime("%d %b. %Y").lower()
    except (ValueError, AttributeError):
        access_formatted = "data desconhecida"
    
    parts.append(f"Disponível em: <{url}>. Acesso em: {access_formatted}.")
    
    return " ".join(parts)


def format_abnt_vocabulary(
    title: str,
    publisher: str,
    year: Optional[str],
    url: str,
    accessed_at: str,
    notation: Optional[str] = None,
    **kwargs
) -> str:
    """Format a controlled vocabulary entry."""
    parts = []
    
    parts.append(f"{normalize_name(publisher)}.")
    parts.append(f"**{title}**.")
    
    if notation:
        parts.append(f"Notação: {notation}.")
    
    if year:
        parts.append(f"{year}.")
    
    try:
        access_date = datetime.fromisoformat(accessed_at.replace('Z', '+00:00'))
        access_formatted = access_date.strftime("%d %b. %Y").lower()
    except (ValueError, AttributeError):
        access_formatted = "data desconhecida"
    
    parts.append(f"Disponível em: <{url}>. Acesso em: {access_formatted}.")
    
    return " ".join(parts)


def generate_abnt_citation(source_type: str, metadata: Dict[str, Any]) -> str:
    """Generate ABNT citation based on source type.
    
    Args:
        source_type: One of: primary_image, museum_record, academic_paper, legal_text, vocabulary
        metadata: Dictionary with citation metadata
        
    Returns:
        ABNT-formatted citation string
    """
    formatters = {
        "primary_image": format_abnt_museum_record,
        "museum_record": format_abnt_museum_record,
        "academic_paper": format_abnt_academic_paper,
        "legal_text": format_abnt_legal_text,
        "vocabulary": format_abnt_vocabulary,
    }
    
    formatter = formatters.get(source_type, format_abnt_web_source)
    return formatter(**metadata)


def process_webscout_output(data: Dict[str, Any]) -> List[str]:
    """Extract and generate ABNT citations from WebScout output."""
    citations = []
    
    for result in data.get("search_results", []):
        if "abnt_citation" in result and result["abnt_citation"]:
            # Already formatted
            citations.append(result["abnt_citation"])
        else:
            # Generate from metadata
            citation = generate_abnt_citation(
                source_type=result.get("source_type", "museum_record"),
                metadata={
                    "title": result.get("title", "Sem título"),
                    "publisher": result.get("publisher"),
                    "year": result.get("year"),
                    "url": result.get("url", ""),
                    "accessed_at": result.get("accessed_at", datetime.now().isoformat()),
                    "author": result.get("author"),
                    "journal": result.get("journal"),
                    "jurisdiction": result.get("jurisdiction"),
                    "notation": result.get("notation"),
                }
            )
            citations.append(citation)
    
    return citations


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate ABNT citations from WebScout/IconoCode output"
    )
    parser.add_argument(
        "input",
        type=Path,
        help="JSON file with WebScout output or master record"
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        help="Output file for citations (default: stdout)"
    )
    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format"
    )
    
    args = parser.parse_args()
    
    with args.input.open("r", encoding="utf-8") as f:
        data = json.load(f)
    
    # Handle both direct WebScout output and MasterRecord
    if "webscout" in data:
        citations = process_webscout_output(data["webscout"])
    else:
        citations = process_webscout_output(data)
    
    # Format output
    if args.format == "json":
        output = json.dumps(citations, ensure_ascii=False, indent=2)
    else:
        output = "\n\n".join(citations)
    
    # Write or print
    if args.output:
        args.output.write_text(output, encoding="utf-8")
        print(f"Generated {len(citations)} citation(s) → {args.output}")
    else:
        print(output)


if __name__ == "__main__":
    main()
