"""
Step 4 — Test Mapper

Queries the CodebaseGraph for test files and functions that cover the target symbol.
"""

from __future__ import annotations
from engine.codebase_graph import get_graph


def map_tests(target_symbol: str) -> list[dict]:
    """
    Return test files that cover target_symbol, using the pre-built
    TestCoversEdges from the CodebaseGraph.

    Returns a list of ImpactedComponent dicts with impact_type = "test_coverage".
    """
    graph = get_graph()
    results: list[dict] = []
    seen_files: set[str] = set()

    # Find all TestCoversEdges where the covered symbol name matches
    for edge in graph.test_covers:
        # edge.covered_symbol is a symbol_id like "services/order_service.py#calculate_order_total"
        if edge.covered_symbol.endswith(f"#{target_symbol}"):
            test_type = (
                "integration" if "route" in edge.test_file or "checkout" in edge.test_file
                else "unit"
            )
            depth = 2 if test_type == "integration" else 1
            key = f"{edge.test_file}#{edge.test_function}"
            if key in seen_files:
                continue
            seen_files.add(key)
            results.append({
                "file":        edge.test_file,
                "symbol":      edge.test_function,
                "impact_type": "test_coverage",
                "depth":       depth,
                "risk_level":  "medium",
                "reason": (
                    f"{test_type.capitalize()} test `{edge.test_function}` "
                    f"covers `{target_symbol}` and must be re-validated after change"
                ),
            })

    return results
