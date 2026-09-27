"""
Step 6 — Report Builder

Assembles the final BlastRadiusReport from an ImpactResult.

The report shape is backward-compatible with the existing frontend
TypeScript types (BlastRadiusReport) while adding the new 7-category
analysis fields under `impact_categories`.
"""

from __future__ import annotations
from datetime import datetime, timezone
from engine.impact_analyzer import ImpactResult


def build_report(result: ImpactResult) -> dict:
    """
    Convert an ImpactResult into the BlastRadiusReport JSON structure.

    The report contains two levels of data:
      1. Legacy flat fields (meta, target, impacted_components, contract_hazards,
         risk_breakdown, validation_plan, mitigation, mermaid_diagram) — consumed
         by the existing frontend ImpactReport component.
      2. `impact_categories` — the new structured 7-category breakdown, used
         for a richer UI display.
    """
    r = result
    now = datetime.now(timezone.utc).isoformat()

    # ── Flatten impacted_components for the legacy frontend field ─────────────
    all_impacted = [
        {
            "file":        c.file,
            "symbol":      c.symbol,
            "impact_type": c.impact_type,
            "depth":       c.depth,
            "risk_level":  "high" if c.depth == 1 else "medium",
            "reason":      c.reason,
        }
        for c in r.directly_affected + r.indirectly_affected
    ]

    # Tests also appear in impacted_components (for graph rendering)
    seen_files = {c["file"] for c in all_impacted}
    for t in r.related_tests:
        if t["file"] not in seen_files:
            all_impacted.append({
                "file":        t["file"],
                "symbol":      t["function"],
                "impact_type": "test_coverage",
                "depth":       1,
                "risk_level":  "medium",
                "reason":      t["reason"],
            })
            seen_files.add(t["file"])

    impacted_files = {c["file"] for c in all_impacted}
    direct_count   = len(r.directly_affected)
    indirect_count = len(r.indirectly_affected)

    # ── Validation plan — from testing suggestions ────────────────────────────
    test_commands = list({
        s.command for s in r.testing_suggestions
        if s.command and "pytest" in s.command
    })
    manual_checks = [s.action for s in r.testing_suggestions if not s.command]

    # ── Legacy contract_hazards shape (API + DB combined) ────────────────────
    contract_hazards = []
    for api in r.related_apis:
        contract_hazards.append({
            "type":        "api_contract",
            "severity":    "high",
            "description": f"{api.http_method} `{api.path}` — {api.reason}",
            "file":        api.file,
            "line":        0,
        })
    for db in r.related_db:
        contract_hazards.append({
            "type":        "db_schema",
            "severity":    "medium",
            "description": db.reason,
            "file":        db.file,
            "line":        db.line,
        })

    # ── Mermaid diagram ───────────────────────────────────────────────────────
    mermaid = _build_mermaid(r)

    return {
        # ── Legacy fields (frontend compatible) ──────────────────────────────
        "meta": {
            "analyzed_target":    f"{r.target_file}#{r.target_symbol}",
            "change_description": r.change_description,
            "change_type":        r.change_type,
            "risk_level":         r.risk_level,
            "total_impacted_files": len(impacted_files),
            "direct_callers":     direct_count,
            "transitive_callers": indirect_count,
            "test_files_affected": len({t["file"] for t in r.related_tests}),
            "generated_at":       now,
        },
        "target": {
            "file":       r.target_file,
            "symbol":     r.target_symbol,
            "kind":       r.target_layer,
            "line_start": 0,
            "line_end":   0,
            "signature":  r.target_signature,
            "docstring":  r.target_docstring,
        },
        "impacted_components": all_impacted,
        "contract_hazards":    contract_hazards,
        "risk_breakdown":      r.risk_breakdown,
        "validation_plan": {
            "test_commands": test_commands if test_commands else ["pytest tests/ -v"],
            "manual_checks": manual_checks if manual_checks else [
                f"Verify functionality that depends on `{r.target_symbol}` still works",
            ],
        },
        "mitigation": {
            "feature_flag":       f"enable_{r.target_symbol.lower()}_change",
            "rollback_complexity": "high" if r.related_db else "low",
            "rollback_note": (
                "DB migration rollback required" if r.related_db
                else "Code-only revert is sufficient"
            ),
            "deployment_strategy": (
                "canary" if r.risk_level in ("CRITICAL", "HIGH") else "standard"
            ),
        },
        "mermaid_diagram": mermaid,

        # ── New 7-category analysis ───────────────────────────────────────────
        "impact_categories": result.to_dict(),
    }


def _build_mermaid(r: ImpactResult) -> str:
    """
    Generate a Mermaid graph that shows the blast radius visually.

    Node colour scheme:
      Red   — the changed target
      Amber — directly affected components
      Grey  — indirectly affected components
      Green — test files
      Blue  — database / model layer
      Purple — API routes
    """
    lines = ["graph TD"]
    target_id = _nid(r.target_symbol)
    lines.append(f'  {target_id}["{r.target_symbol}\\n{_short(r.target_file)}"]')
    lines.append(f'  style {target_id} fill:#f87171,stroke:#b91c1c,stroke-width:2px,color:#fff')

    seen: set[str] = set()

    for comp in r.directly_affected:
        nid = _nid(comp.file)
        if nid in seen:
            continue
        seen.add(nid)
        label = _short(comp.file)
        fill, stroke = _layer_colour(comp.layer, depth=1)
        lines.append(f'  {nid}["{label}"]')
        lines.append(f'  {target_id} --> {nid}')
        lines.append(f'  style {nid} fill:{fill},stroke:{stroke},color:#000')

    for comp in r.indirectly_affected:
        nid = _nid(comp.file)
        if nid in seen:
            continue
        seen.add(nid)
        label = _short(comp.file)
        lines.append(f'  {nid}["{label}"]')
        lines.append(f'  {target_id} -.-> {nid}')
        lines.append(f'  style {nid} fill:#e5e7eb,stroke:#6b7280,color:#374151')

    # Show unique test files (deduplicated)
    test_files_shown: set[str] = set()
    for t in r.related_tests:
        f = t["file"]
        nid = _nid(f)
        if nid in seen or f in test_files_shown:
            continue
        test_files_shown.add(f)
        seen.add(nid)
        lines.append(f'  {nid}["{_short(f)}"]')
        lines.append(f'  {target_id} --> {nid}')
        lines.append(f'  style {nid} fill:#86efac,stroke:#16a34a,color:#000')

    # Show DB tables (grouped as one node per table)
    for db in r.related_db[:3]:
        nid = _nid("db_" + db.table_name)
        if nid in seen:
            continue
        seen.add(nid)
        lines.append(f'  {nid}["🗄 {db.table_name}"]')
        lines.append(f'  {target_id} --> {nid}')
        lines.append(f'  style {nid} fill:#bfdbfe,stroke:#2563eb,color:#1e3a8a')

    # Show affected API routes (first 3 only for readability)
    for api in r.related_apis[:3]:
        nid = _nid(f"api_{api.http_method}_{api.path}")
        if nid in seen:
            continue
        seen.add(nid)
        lines.append(f'  {nid}["{api.http_method} {api.path}"]')
        lines.append(f'  {target_id} --> {nid}')
        lines.append(f'  style {nid} fill:#ddd6fe,stroke:#7c3aed,color:#3b0764')

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _nid(s: str) -> str:
    """Convert a string into a valid Mermaid node identifier."""
    return s.replace("/", "_").replace(".", "_").replace("-", "_").replace(" ", "_")


def _short(path: str) -> str:
    """Return just the filename portion of a path."""
    return path.rsplit("/", 1)[-1]


def _layer_colour(layer: str, depth: int) -> tuple[str, str]:
    if layer == "model":
        return "#bfdbfe", "#2563eb"    # blue
    if layer in ("route", "controller"):
        return "#fde68a", "#d97706"    # amber
    if layer == "test":
        return "#86efac", "#16a34a"    # green
    if depth == 1:
        return "#fed7aa", "#ea580c"    # orange for direct service callers
    return "#e5e7eb", "#6b7280"        # grey for indirect
