#!/usr/bin/env python3
"""Extrai uma subárvore do ICONCLASS e gera uma rede temática em JSON."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, List


def parse_textbase(path: Path) -> List[Dict[str, List[str]]]:
    chunks: List[Dict[str, List[str]]] = []
    current: Dict[str, List[str]] = {}
    last_key: str | None = None

    with path.open("rt", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.rstrip("\n")
            if not line:
                continue
            if line == "$":
                if current:
                    chunks.append(current)
                current = {}
                last_key = None
                continue
            if line.startswith("; "):
                if last_key is None:
                    continue
                current.setdefault(last_key, []).append(line[2:])
                continue

            parts = line.split(" ", 1)
            key = parts[0]
            value = parts[1] if len(parts) == 2 else ""
            current.setdefault(key, []).append(value)
            last_key = key

    if current:
        chunks.append(current)
    return chunks


def load_notations(path: Path) -> Dict[str, Dict[str, List[str]]]:
    data: Dict[str, Dict[str, List[str]]] = {}
    for obj in parse_textbase(path):
        notation = obj.get("N", [None])[0]
        if notation:
            data[notation] = obj
    return data


def load_labels(path: Path) -> Dict[str, str]:
    labels: Dict[str, str] = {}
    with path.open("rt", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip() or line.startswith("#"):
                continue
            parts = line.rstrip("\n").split("|", 1)
            if len(parts) == 2:
                labels[parts[0]] = parts[1]
    return labels


def collect_subtree(notations: Dict[str, Dict[str, List[str]]], root: str) -> List[str]:
    if root not in notations:
        raise KeyError(f"Raiz não encontrada em notations.txt: {root}")

    ordered: List[str] = []
    stack = [root]
    seen = set()
    while stack:
        node = stack.pop()
        if node in seen:
            continue
        seen.add(node)
        ordered.append(node)
        children = notations.get(node, {}).get("C", [])
        for child in reversed(children):
            stack.append(child)
    return ordered


def build_network(
    notations: Dict[str, Dict[str, List[str]]],
    labels: Dict[str, str],
    root: str,
    feminist_notation: str,
    bridge_notation: str,
) -> Dict[str, object]:
    subtree_nodes = collect_subtree(notations, root)

    nodes = []
    edges = []

    for notation in subtree_nodes:
        nodes.append(
            {
                "id": notation,
                "label": labels.get(notation, ""),
                "group": "justice_subtree",
            }
        )
        for child in notations.get(notation, {}).get("C", []):
            if child in subtree_nodes:
                edges.append(
                    {
                        "source": notation,
                        "target": child,
                        "type": "narrower",
                    }
                )

    extras = [feminist_notation]
    for notation in extras:
        if notation not in {n["id"] for n in nodes}:
            nodes.append(
                {
                    "id": notation,
                    "label": labels.get(notation, ""),
                    "group": "feminist_anchor",
                }
            )

    if feminist_notation and bridge_notation:
        edges.append(
            {
                "source": feminist_notation,
                "target": bridge_notation,
                "type": "feminist_association",
            }
        )

    return {
        "root": root,
        "root_label": labels.get(root, ""),
        "subtree_size": len(subtree_nodes),
        "nodes": nodes,
        "edges": edges,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extrai uma subárvore do notations.txt e gera rede temática em JSON"
    )
    parser.add_argument("--root", default="48C51", help="Raiz da subárvore")
    parser.add_argument(
        "--feminist-notation",
        default="31AA231",
        help="Notação feminina para conectar à rede",
    )
    parser.add_argument(
        "--bridge-notation",
        default="48C514",
        help="Notação da subárvore para ponte temática",
    )
    parser.add_argument("--lang", default="pt", help="Idioma dos rótulos")
    parser.add_argument(
        "--output",
        default="feminist_network_48C51_pt.json",
        help="Arquivo JSON de saída",
    )
    args = parser.parse_args()

    notations = load_notations(Path("notations.txt"))
    labels = {}
    for candidate in Path(f"txt/{args.lang}").glob(f"txt_{args.lang}_*.txt"):
        labels.update(load_labels(candidate))

    network = build_network(
        notations=notations,
        labels=labels,
        root=args.root,
        feminist_notation=args.feminist_notation,
        bridge_notation=args.bridge_notation,
    )

    output_path = Path(args.output)
    output_path.write_text(json.dumps(network, ensure_ascii=False, indent=2), encoding="utf-8")

    print(
        f"Rede gerada: {output_path} | nós={len(network['nodes'])} arestas={len(network['edges'])}"
    )


if __name__ == "__main__":
    main()
