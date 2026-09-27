"""
GET /api/graph          — return a summary + all nodes/edges as JSON
GET /api/graph/file     — return all relationships for a specific file

These endpoints let the frontend (or a developer) inspect the full
structural model of the demo codebase that the analyzer is built on.
"""

from __future__ import annotations
from flask import Blueprint, request, jsonify
from engine.codebase_graph import get_graph

graph_bp = Blueprint("graph", __name__)


@graph_bp.get("/graph")
def graph_summary():
    """Return a summary of the codebase graph plus all structured data."""
    graph = get_graph()

    return jsonify({
        "summary": graph.summary(),
        "files": [
            {
                "path":       f.path,
                "language":   f.language,
                "layer":      f.layer,
                "size_lines": f.size_lines,
                "symbols":    f.symbols,
            }
            for f in graph.files.values()
        ],
        "symbols": [
            {
                "id":         s.id,
                "name":       s.name,
                "kind":       s.kind,
                "file":       s.file,
                "line_start": s.line_start,
                "line_end":   s.line_end,
                "signature":  s.signature,
            }
            for s in graph.symbols.values()
        ],
        "imports": [
            {
                "from_file": e.from_file,
                "to_module": e.to_module,
                "to_file":   e.to_file,
                "names":     e.names,
            }
            for e in graph.imports
        ],
        "routes": [
            {
                "method":           r.http_method,
                "path":             r.path,
                "file":             r.file,
                "handler_function": r.handler_function,
            }
            for r in graph.routes
        ],
        "schema_nodes": [
            {
                "table_name": s.table_name,
                "operation":  s.operation,
                "file":       s.file,
                "line":       s.line,
            }
            for s in graph.schema_nodes
        ],
        "test_covers": [
            {
                "test_file":       e.test_file,
                "test_function":   e.test_function,
                "covered_symbol":  e.covered_symbol,
                "covered_file":    e.covered_file,
            }
            for e in graph.test_covers
        ],
    })


@graph_bp.get("/graph/file")
def graph_file_detail():
    """
    GET /api/graph/file?path=services/order_service.py

    Return all symbols defined in a file plus every inbound/outbound edge.
    """
    path = request.args.get("path", "").strip()
    if not path:
        return jsonify({"error": "path query parameter is required"}), 400

    graph = get_graph()

    if path not in graph.files:
        return jsonify({"error": f"File not found in graph: {path}"}), 404

    file_node = graph.files[path]
    defined_symbols = [
        {
            "id":         graph.symbols[f"{path}#{name}"].id,
            "name":       name,
            "kind":       graph.symbols[f"{path}#{name}"].kind,
            "line_start": graph.symbols[f"{path}#{name}"].line_start,
            "signature":  graph.symbols[f"{path}#{name}"].signature,
        }
        for name in file_node.symbols
        if f"{path}#{name}" in graph.symbols
    ]

    outbound_imports = [
        {"to_module": e.to_module, "to_file": e.to_file, "names": e.names}
        for e in graph.imports_of(path)
    ]

    inbound_refs: list[dict] = []
    for sym_name in file_node.symbols:
        sym_id = f"{path}#{sym_name}"
        for edge in graph.callers_of(sym_id):
            inbound_refs.append({
                "from_file":   edge.from_file,
                "to_symbol":   edge.to_symbol,
                "line":        edge.line,
                "ref_type":    edge.ref_type,
            })

    routes = [
        {"method": r.http_method, "path": r.path, "handler_function": r.handler_function}
        for r in graph.routes_for_file(path)
    ]

    test_cover_edges = [
        {"test_file": e.test_file, "test_function": e.test_function}
        for sym_name in file_node.symbols
        for e in graph.tests_for(f"{path}#{sym_name}")
    ]

    return jsonify({
        "file":             {"path": path, "layer": file_node.layer, "size_lines": file_node.size_lines},
        "defined_symbols":  defined_symbols,
        "outbound_imports": outbound_imports,
        "inbound_refs":     inbound_refs,
        "routes":           routes,
        "test_covers":      test_cover_edges,
    })
