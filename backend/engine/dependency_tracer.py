"""
Step 2 — Dependency Tracer

Queries the CodebaseGraph to find direct and transitive callers/importers
of the target symbol. No file-scanning at request time — the graph is pre-built.
"""

from __future__ import annotations
from engine.codebase_graph import get_graph, RefEdge


def trace_dependencies(target_file: str, target_symbol: str) -> list[dict]:
    """
    Return all components that reference target_symbol, structured as
    ImpactedComponent dicts ready for the report builder.

    Two passes:
      Depth 1 — files that directly call or import the symbol (RefEdges)
      Depth 2 — files that import from depth-1 files (transitive)

    Results are deduplicated by file — one entry per affected file.
    """
    graph = get_graph()
    symbol_id = f"{target_file}#{target_symbol}"

    results: list[dict] = []
    direct_files: set[str] = set()

    # ── Depth 1: direct references via RefEdge and ImportEdge ───────────────
    for edge in graph.callers_of(symbol_id):
        if edge.from_file == target_file or edge.from_file in direct_files:
            continue
        _append_component(results, edge.from_file, graph, depth=1,
                          reason=f"Directly calls or references `{target_symbol}`")
        direct_files.add(edge.from_file)

    # Also catch files that import the symbol by name
    for imp in graph.imports:
        if imp.to_file == target_file and target_symbol in imp.names:
            if imp.from_file not in direct_files and imp.from_file != target_file:
                _append_component(results, imp.from_file, graph, depth=1,
                                  reason=f"Imports `{target_symbol}` from `{target_file}`")
                direct_files.add(imp.from_file)

    # ── Depth 2: transitive — files that import from direct callers ──────────
    transitive_files: set[str] = set()
    for d1_file in list(direct_files):
        for imp in graph.imports:
            if imp.to_file == d1_file:
                if (imp.from_file not in direct_files
                        and imp.from_file != target_file
                        and imp.from_file not in transitive_files):
                    _append_component(
                        results, imp.from_file, graph, depth=2,
                        reason=f"Imports from `{d1_file}` which references `{target_symbol}`",
                    )
                    transitive_files.add(imp.from_file)

    return results


def _append_component(results: list[dict], file: str,
                       graph, depth: int, reason: str) -> None:
    """Build an ImpactedComponent dict and append it to results."""
    # Pick the first non-dunder symbol defined in the file as the representative
    sym_name = next(
        (name for name in graph.files.get(file, object.__new__(object)).__dict__.get("symbols", [])
         if not name.startswith("_")),
        file.rsplit("/", 1)[-1].replace(".py", ""),
    )
    if hasattr(graph.files.get(file, None), "symbols"):
        syms = [s for s in graph.files[file].symbols if not s.startswith("_")]
        sym_name = syms[0] if syms else file.rsplit("/", 1)[-1].replace(".py", "")

    layer = graph.files[file].layer if file in graph.files else "other"

    results.append({
        "file":        file,
        "symbol":      sym_name,
        "impact_type": _impact_type(layer, depth),
        "depth":       depth,
        "risk_level":  "high" if depth == 1 else "medium",
        "reason":      reason,
    })


def _impact_type(layer: str, depth: int) -> str:
    if layer == "test":
        return "test_coverage"
    if layer in ("route", "controller"):
        return "api_surface" if depth == 1 else "transitive_caller"
    if layer == "model":
        return "data_schema"
    return "direct_caller" if depth == 1 else "transitive_caller"
