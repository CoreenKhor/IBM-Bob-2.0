"""
Step 3 — Contract Checker

Queries the CodebaseGraph for API routes and SQL schema nodes that are
linked to the target symbol's file or module, surfacing contract hazards.
"""

from __future__ import annotations
from engine.codebase_graph import get_graph


def check_contracts(target_file: str, target_symbol: str) -> list[dict]:
    """
    Identify API routes and DB schema definitions that may be broken by
    a change to target_symbol.

    Two categories:
      api_contract — RouteNodes in files that import or reference target_file
      db_schema    — SchemaNodes in .sql files (always flagged for any
                     service/model-layer target)
    """
    graph = get_graph()
    hazards: list[dict] = []
    symbol_id = f"{target_file}#{target_symbol}"
    target_layer = graph.files.get(target_file, None)

    # ── API contract hazards ─────────────────────────────────────────────────
    # Collect files that directly reference the target
    referencing_files: set[str] = {target_file}
    for imp in graph.imports:
        if imp.to_file == target_file:
            referencing_files.add(imp.from_file)
    for edge in graph.callers_of(symbol_id):
        referencing_files.add(edge.from_file)

    for route in graph.routes:
        if route.file in referencing_files and route.file != target_file:
            hazards.append({
                "type":        "api_contract",
                "severity":    "high",
                "description": (
                    f"{route.http_method} `{route.path}` (handler: `{route.handler_function}`) "
                    f"in `{route.file}` may expose a changed interface for `{target_symbol}`"
                ),
                "file":        route.file,
                "line":        0,
            })

    # ── DB schema hazards ────────────────────────────────────────────────────
    # Flag schema nodes when the target is in a model or service layer
    if target_layer and target_layer.layer in ("model", "service"):
        for schema in graph.schema_nodes:
            hazards.append({
                "type":        "db_schema",
                "severity":    "medium",
                "description": (
                    f"Table `{schema.table_name}` ({schema.operation}) in "
                    f"`{schema.file}` may need migration if `{target_symbol}` "
                    "alters persisted data"
                ),
                "file":        schema.file,
                "line":        schema.line,
            })

    return hazards
