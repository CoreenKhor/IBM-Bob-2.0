"""
POST /api/analyze — Change Blast Radius Analysis
GET  /api/analyze/schema — Return accepted JSON schema for the request body

--- Purpose ---
Accepts a target file + symbol + change description from the developer,
runs the full 7-category blast-radius analysis against the demo/ecommerce
codebase, and returns a structured JSON response.

--- Request ---
POST /api/analyze
Content-Type: application/json

{
  "target_file":        "services/payment_service.py",  // required
  "target_symbol":      "process_payment",               // required
  "change_description": "Add support for a new payment provider",  // optional, enriches analysis
  "change_type":        "general"                        // optional, see VALID_CHANGE_TYPES
}

--- Response 200 ---
{
  "ok": true,
  "report": {
    "meta": { ... },
    "target": { ... },
    "impacted_components": [ ... ],
    "contract_hazards": [ ... ],
    "risk_breakdown": { ... },
    "validation_plan": { ... },
    "mitigation": { ... },
    "mermaid_diagram": "graph TD ...",
    "impact_categories": {
      "target": { ... },
      "change": { ... },
      "risk_level": "HIGH",
      "risk_breakdown": { ... },
      "directly_affected":   [ { file, symbol, layer, reason, depth, impact_type } ],
      "indirectly_affected": [ ... ],
      "related_tests":       [ { file, function, test_type, command, reason } ],
      "related_apis":        [ { http_method, path, file, handler, reason } ],
      "related_db":          [ { table_name, operation, file, line, reason } ],
      "risk_areas":          [ { severity, category, title, description, affected_files } ],
      "testing_suggestions": [ { priority, action, detail, command } ]
    }
  }
}

--- Error responses ---
400  Missing required fields or invalid change_type
404  Content-Type is not application/json  (returns helpful message)
422  Symbol not found in the specified file
500  Unexpected analysis error (returned as structured JSON, never as HTML)
"""

from __future__ import annotations

import traceback
from flask import Blueprint, request, jsonify

from engine.target_resolver import resolve_target
from engine.impact_analyzer import run as run_analysis
from engine.report_builder import build_report
from engine.codebase_graph import get_graph, DEMO_ROOT

analyze_bp = Blueprint("analyze", __name__)

# ── Constants ────────────────────────────────────────────────────────────────

VALID_CHANGE_TYPES = frozenset({
    "general",
    "signature_change",
    "schema_change",
    "api_change",
    "refactor",
    "deletion",
    "new_feature",
})

MAX_DESCRIPTION_LENGTH = 1000   # characters — prevents accidental huge payloads
MAX_SYMBOL_LENGTH       = 120
MAX_FILE_PATH_LENGTH    = 260


# ── Request schema (returned by GET /api/analyze/schema) ────────────────────

_REQUEST_SCHEMA = {
    "description": "POST /api/analyze request body",
    "type": "object",
    "required": ["target_file", "target_symbol"],
    "properties": {
        "target_file": {
            "type": "string",
            "description": "Relative path to the file inside demo/ecommerce/",
            "example": "services/payment_service.py",
            "maxLength": MAX_FILE_PATH_LENGTH,
        },
        "target_symbol": {
            "type": "string",
            "description": "Name of the function or class to analyze",
            "example": "process_payment",
            "maxLength": MAX_SYMBOL_LENGTH,
        },
        "change_description": {
            "type": "string",
            "description": "Free-text description of the proposed change",
            "example": "Add support for a new payment provider",
            "maxLength": MAX_DESCRIPTION_LENGTH,
            "default": "",
        },
        "change_type": {
            "type": "string",
            "description": "Category of change — influences risk scoring",
            "enum": sorted(VALID_CHANGE_TYPES),
            "default": "general",
        },
    },
}


# ── Helpers ──────────────────────────────────────────────────────────────────

def _error(message: str, code: int, **extra) -> tuple:
    """Return a consistent JSON error envelope."""
    body = {"ok": False, "error": message}
    body.update(extra)
    return jsonify(body), code


def _validate_body(body: dict) -> str | None:
    """
    Validate the request body fields.
    Returns an error message string, or None if valid.
    """
    target_file   = body.get("target_file", "")
    target_symbol = body.get("target_symbol", "")
    change_type   = body.get("change_type", "general")
    description   = body.get("change_description", "")

    if not isinstance(target_file, str) or not target_file.strip():
        return "target_file is required and must be a non-empty string"

    if not isinstance(target_symbol, str) or not target_symbol.strip():
        return "target_symbol is required and must be a non-empty string"

    if len(target_file.strip()) > MAX_FILE_PATH_LENGTH:
        return f"target_file must be at most {MAX_FILE_PATH_LENGTH} characters"

    if len(target_symbol.strip()) > MAX_SYMBOL_LENGTH:
        return f"target_symbol must be at most {MAX_SYMBOL_LENGTH} characters"

    if len(description) > MAX_DESCRIPTION_LENGTH:
        return f"change_description must be at most {MAX_DESCRIPTION_LENGTH} characters"

    if not isinstance(change_type, str) or change_type.strip() not in VALID_CHANGE_TYPES:
        return (
            f"change_type must be one of: {', '.join(sorted(VALID_CHANGE_TYPES))}. "
            f"Got: {change_type!r}"
        )

    # Path traversal guard (belt-and-suspenders on top of target_resolver)
    norm = target_file.strip().replace("\\", "/")
    if ".." in norm or norm.startswith("/"):
        return "target_file must be a relative path inside the demo codebase"

    return None   # valid


def _list_available_symbols(target_file: str) -> list[str]:
    """Return the symbol names known for target_file (for helpful 422 hints)."""
    graph = get_graph()
    file_node = graph.files.get(target_file.strip())
    return file_node.symbols if file_node else []


# ── Routes ───────────────────────────────────────────────────────────────────

@analyze_bp.get("/analyze/schema")
def analyze_schema():
    """
    GET /api/analyze/schema

    Returns the JSON schema for the POST /api/analyze request body.
    Useful for the frontend to auto-generate forms and for API consumers
    to understand the accepted input.
    """
    return jsonify({
        "ok": True,
        "schema": _REQUEST_SCHEMA,
        "valid_change_types": sorted(VALID_CHANGE_TYPES),
    })


@analyze_bp.post("/analyze")
def analyze():
    """
    POST /api/analyze

    Run a Change Blast Radius Analysis for the specified target symbol.

    Returns a BlastRadiusReport with 7-category impact breakdown:
      directly_affected, indirectly_affected, related_tests,
      related_apis, related_db, risk_areas, testing_suggestions.
    """
    # ── 1. Content-type guard ────────────────────────────────────────────────
    # Flask's get_json(silent=True) returns None for non-JSON bodies;
    # give an explicit, developer-friendly error instead of a silent empty result.
    ct = request.content_type or ""
    if request.data and "application/json" not in ct:
        return _error(
            "Content-Type must be application/json",
            415,
            hint="Set the Content-Type: application/json request header",
        )

    body = request.get_json(silent=True)
    if body is None:
        body = {}

    # ── 2. Input validation ──────────────────────────────────────────────────
    validation_error = _validate_body(body)
    if validation_error:
        return _error(validation_error, 400, schema="/api/analyze/schema")

    target_file        = body["target_file"].strip()
    target_symbol      = body["target_symbol"].strip()
    change_description = body.get("change_description", "").strip()
    change_type        = body.get("change_type", "general").strip()

    # ── 3. Resolve the target symbol (Step 1 of the engine pipeline) ─────────
    target_info = resolve_target(target_file, target_symbol)
    if target_info.get("error"):
        available = _list_available_symbols(target_file)
        return _error(
            target_info["error"],
            422,
            available_symbols=available[:30],   # cap list for readability
            hint=(
                f"Check that target_symbol is one of the symbols defined in {target_file}. "
                "Call GET /api/symbols?path=<file> to see all available symbols."
            ),
        )

    # ── 4. Run the full 7-category analysis (Steps 2–6) ──────────────────────
    try:
        result = run_analysis(
            target_file=target_file,
            target_symbol=target_symbol,
            change_description=change_description,
            change_type=change_type,
            target_info=target_info,
        )
        report = build_report(result)

    except Exception as exc:
        # Surface engine errors as structured JSON — never as Flask HTML 500 pages.
        return _error(
            f"Analysis failed: {exc}",
            500,
            detail=traceback.format_exc()[-2000:],   # tail — enough context, not huge
        )

    # ── 5. Return structured response ─────────────────────────────────────────
    return jsonify({"ok": True, "report": report}), 200
