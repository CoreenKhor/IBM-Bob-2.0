"""
GET /api/symbols?path=<file>       — list all symbols in a file
GET /api/symbols/all               — list every symbol across the entire codebase
GET /api/symbols/layers            — list files grouped by architectural layer

These endpoints let the frontend file picker show available symbols
immediately after a file is selected, avoiding a round-trip to /api/analyze
just to discover valid symbol names.
"""

from __future__ import annotations
from flask import Blueprint, request, jsonify
from engine.codebase_graph import get_graph

symbols_bp = Blueprint("symbols", __name__)


@symbols_bp.get("/symbols")
def list_symbols():
    """
    GET /api/symbols?path=services/payment_service.py

    Returns every symbol defined in the requested file, ordered by
    line number.  Includes name, kind, signature, and line range so the
    frontend can render a useful picker without additional requests.

    Query parameters:
      path        (required) — relative path inside demo/ecommerce/
      kind        (optional) — filter by "function" | "class" | "method"

    Response 200:
    {
      "ok": true,
      "file": "services/payment_service.py",
      "layer": "service",
      "symbols": [
        {
          "name": "process_payment",
          "kind": "function",
          "signature": "def process_payment(order_id: int, ...) -> dict:",
          "line_start": 104,
          "line_end": 177,
          "docstring_preview": "Process a payment for an order. ..."
        },
        ...
      ]
    }
    """
    path     = request.args.get("path", "").strip()
    kind_filter = request.args.get("kind", "").strip().lower() or None

    if not path:
        return jsonify({
            "ok": False,
            "error": "path query parameter is required",
            "hint": "Example: GET /api/symbols?path=services/payment_service.py",
        }), 400

    # Reject traversal attempts
    norm = path.replace("\\", "/")
    if ".." in norm or norm.startswith("/"):
        return jsonify({"ok": False, "error": "Invalid path"}), 400

    graph = get_graph()
    file_node = graph.files.get(path)
    if file_node is None:
        # Return available .py file paths to help the caller
        py_files = sorted(
            p for p, f in graph.files.items() if f.language == "python"
        )
        return jsonify({
            "ok": False,
            "error": f"File not found in codebase index: {path}",
            "available_files": py_files,
        }), 404

    # Collect symbols defined in this file, sorted by line
    results = []
    for sym_name in file_node.symbols:
        sym = graph.symbols.get(f"{path}#{sym_name}")
        if sym is None:
            continue
        if kind_filter and sym.kind != kind_filter:
            continue
        results.append({
            "name":              sym.name,
            "kind":              sym.kind,
            "signature":         sym.signature,
            "line_start":        sym.line_start,
            "line_end":          sym.line_end,
            "docstring_preview": sym.docstring[:120] + "…" if len(sym.docstring) > 120 else sym.docstring,
        })

    # Sort by line number
    results.sort(key=lambda s: s["line_start"])

    return jsonify({
        "ok":      True,
        "file":    path,
        "layer":   file_node.layer,
        "count":   len(results),
        "symbols": results,
    })


@symbols_bp.get("/symbols/all")
def all_symbols():
    """
    GET /api/symbols/all?layer=<layer>

    Returns every symbol across the entire codebase, optionally filtered
    by architectural layer.  Used by the frontend search/autocomplete.

    Query parameters:
      layer  (optional) — one of service | model | controller | route | test | schema

    Response 200:
    {
      "ok": true,
      "count": 182,
      "symbols": [
        { "id": "services/order_service.py#calculate_order_total", "name": ..., "file": ..., "kind": ..., "layer": ... },
        ...
      ]
    }
    """
    layer_filter = request.args.get("layer", "").strip().lower() or None
    graph = get_graph()

    results = []
    for sym_id, sym in graph.symbols.items():
        file_node = graph.files.get(sym.file)
        layer = file_node.layer if file_node else "other"
        if layer_filter and layer != layer_filter:
            continue
        results.append({
            "id":    sym_id,
            "name":  sym.name,
            "file":  sym.file,
            "kind":  sym.kind,
            "layer": layer,
        })

    results.sort(key=lambda s: (s["file"], s["name"]))
    return jsonify({"ok": True, "count": len(results), "symbols": results})


@symbols_bp.get("/symbols/layers")
def symbols_by_layer():
    """
    GET /api/symbols/layers

    Returns all Python files grouped by their architectural layer.
    Used by the frontend file tree to group files visually.

    Response 200:
    {
      "ok": true,
      "layers": {
        "service":    [ { "path": "services/order_service.py", "symbols": [...] } ],
        "model":      [ ... ],
        "controller": [ ... ],
        "route":      [ ... ],
        "test":       [ ... ],
        "schema":     [ ... ]
      }
    }
    """
    graph = get_graph()
    layers: dict[str, list[dict]] = {}

    for path, file_node in sorted(graph.files.items()):
        if file_node.language != "python":
            continue
        layer = file_node.layer
        layers.setdefault(layer, []).append({
            "path":    path,
            "symbols": [
                s for s in file_node.symbols if not s.startswith("_")
            ],
        })

    return jsonify({"ok": True, "layers": layers})
