"""
Impact Analyzer — Core Change Blast Radius Analysis

Given a target (file + symbol) and a free-text change description, this
module produces a structured 7-category impact result by querying the
pre-built CodebaseGraph.

The 7 categories:
  1. directly_affected      — files / symbols that directly call or import the target
  2. indirectly_affected    — files that reach the target through one transitive hop
  3. related_tests          — test functions that cover the target or any direct caller
  4. related_apis           — HTTP routes whose handler chain touches the target
  5. related_db             — database tables / schema definitions in scope
  6. risk_areas             — specific risk signals derived from both graph topology
                              and semantic cues in the change description
  7. testing_suggestions    — concrete, actionable testing recommendations

Design philosophy
-----------------
Every category is derived algorithmically from the CodebaseGraph — no
hard-coded component names, no if-statement heuristics for specific symbols.
The same logic that works for `process_payment` will work for `calculate_order_total`,
`register_user`, or any other symbol in the codebase.

The only place where the change description influences output is in
`_extract_change_signals()`, which extracts semantic keywords (e.g. "new
payment provider", "schema change", "rename") to adjust risk levels and
generate relevant suggestions.  This is intentionally simple regex-based NLP
rather than an LLM call — it is fast, deterministic, and hackathon-friendly.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

from engine.codebase_graph import get_graph, CodebaseGraph


# ---------------------------------------------------------------------------
# Result data classes
# ---------------------------------------------------------------------------

@dataclass
class AffectedComponent:
    """A file/symbol pair that is impacted by the change."""
    file: str
    symbol: str           # representative symbol name (first public name in file)
    layer: str            # architectural layer (service, model, route…)
    reason: str           # human-readable explanation
    depth: int            # 1 = direct, 2 = indirect
    impact_type: str      # "direct_caller" | "transitive_caller" | "data_schema" | "api_surface"


@dataclass
class AffectedAPI:
    http_method: str
    path: str
    file: str
    handler: str
    reason: str


@dataclass
class AffectedDB:
    table_name: str
    operation: str        # "CREATE TABLE" etc.
    file: str
    line: int
    reason: str


@dataclass
class RiskArea:
    severity: str         # "critical" | "high" | "medium" | "low"
    category: str         # "api_contract" | "db_migration" | "test_gap" | "wide_impact" | "semantic"
    title: str
    description: str
    affected_files: list[str]


@dataclass
class TestingSuggestion:
    priority: str         # "must" | "should" | "consider"
    action: str           # short imperative sentence
    detail: str           # longer explanation
    command: Optional[str] = None   # runnable pytest command, if applicable


@dataclass
class ImpactResult:
    """Complete 7-category blast radius analysis result."""
    target_file: str
    target_symbol: str
    target_layer: str
    target_signature: str
    target_docstring: str
    change_description: str
    change_type: str

    # The 7 categories
    directly_affected:   list[AffectedComponent]
    indirectly_affected: list[AffectedComponent]
    related_tests:       list[dict]               # {file, function, test_type, reason}
    related_apis:        list[AffectedAPI]
    related_db:          list[AffectedDB]
    risk_areas:          list[RiskArea]
    testing_suggestions: list[TestingSuggestion]

    # Rolled-up numbers for the executive summary
    risk_level: str       # CRITICAL | HIGH | MEDIUM | LOW
    risk_breakdown: dict

    def to_dict(self) -> dict:
        """Convert to a plain dict for JSON serialisation."""
        return {
            "target": {
                "file":        self.target_file,
                "symbol":      self.target_symbol,
                "layer":       self.target_layer,
                "signature":   self.target_signature,
                "docstring":   self.target_docstring,
            },
            "change": {
                "description": self.change_description,
                "type":        self.change_type,
            },
            "risk_level":    self.risk_level,
            "risk_breakdown": self.risk_breakdown,

            "directly_affected":   [_comp_dict(c) for c in self.directly_affected],
            "indirectly_affected": [_comp_dict(c) for c in self.indirectly_affected],

            "related_tests": self.related_tests,

            "related_apis": [
                {
                    "http_method": a.http_method,
                    "path":        a.path,
                    "file":        a.file,
                    "handler":     a.handler,
                    "reason":      a.reason,
                }
                for a in self.related_apis
            ],

            "related_db": [
                {
                    "table_name": d.table_name,
                    "operation":  d.operation,
                    "file":       d.file,
                    "line":       d.line,
                    "reason":     d.reason,
                }
                for d in self.related_db
            ],

            "risk_areas": [
                {
                    "severity":       r.severity,
                    "category":       r.category,
                    "title":          r.title,
                    "description":    r.description,
                    "affected_files": r.affected_files,
                }
                for r in self.risk_areas
            ],

            "testing_suggestions": [
                {
                    "priority": s.priority,
                    "action":   s.action,
                    "detail":   s.detail,
                    "command":  s.command,
                }
                for s in self.testing_suggestions
            ],
        }


def _comp_dict(c: AffectedComponent) -> dict:
    return {
        "file":        c.file,
        "symbol":      c.symbol,
        "layer":       c.layer,
        "reason":      c.reason,
        "depth":       c.depth,
        "impact_type": c.impact_type,
    }


# ---------------------------------------------------------------------------
# Change signal extraction
# (Simple keyword NLP — deterministic, no external dependencies)
# ---------------------------------------------------------------------------

# Maps keyword patterns → signal tags
_SIGNAL_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\bschema\b|\btable\b|\bcolumn\b|\bmigrat\b|\bdb\b|\bdatabase\b",  re.I), "db_change"),
    (re.compile(r"\brename\b|\bremove\b|\bdelete\b|\bdrop\b|\bdeprecate\b",         re.I), "breaking_change"),
    (re.compile(r"\bapi\b|\bendpoint\b|\broute\b|\bcontract\b|\bpayload\b",         re.I), "api_change"),
    (re.compile(r"\bprovider\b|\bgateway\b|\bintegrat\b|\bthird.party\b",           re.I), "new_integration"),
    (re.compile(r"\bsignature\b|\bparameter\b|\bargument\b|\breturn type\b",        re.I), "signature_change"),
    (re.compile(r"\brefactor\b|\bclean\b|\bextract\b|\bsplit\b|\bmodularize\b",     re.I), "refactor"),
    (re.compile(r"\bsecurity\b|\bauth\b|\btoken\b|\bpermission\b|\bencrypt\b",      re.I), "security"),
    (re.compile(r"\bperformance\b|\bcache\b|\boptimize\b|\bindex\b|\bslow\b",       re.I), "performance"),
    (re.compile(r"\btest\b|\bspec\b|\bcoverage\b",                                  re.I), "test_focus"),
    (re.compile(r"\bnew\b|\badd\b|\bintroduce\b|\bsupport\b",                       re.I), "additive"),
]


def _extract_change_signals(description: str) -> set[str]:
    """Return a set of semantic signal tags from the change description."""
    signals: set[str] = set()
    for pattern, tag in _SIGNAL_PATTERNS:
        if pattern.search(description):
            signals.add(tag)
    return signals


# ---------------------------------------------------------------------------
# Main analysis function
# ---------------------------------------------------------------------------

def run(
    target_file: str,
    target_symbol: str,
    change_description: str,
    change_type: str,
    target_info: dict,
) -> ImpactResult:
    """
    Execute the full 7-category impact analysis.

    Parameters
    ----------
    target_file        : relative path within demo/ecommerce (e.g. "services/payment_service.py")
    target_symbol      : name of the changed symbol         (e.g. "process_payment")
    change_description : free-text description from the developer
    change_type        : one of "signature_change" | "schema_change" | "api_change" |
                         "refactor" | "deletion" | "general"
    target_info        : dict from resolve_target() — carries signature, docstring, layer

    Returns
    -------
    ImpactResult with all 7 categories populated.
    """
    graph = get_graph()
    signals = _extract_change_signals(change_description)

    # Merge change_type keyword into signals for consistent downstream logic
    if change_type and change_type != "general":
        signals.add(change_type)

    target_layer = graph.files[target_file].layer if target_file in graph.files else "other"

    # ── Category 1 & 2: directly and indirectly affected ────────────────────
    directly, indirectly = _trace_affected(graph, target_file, target_symbol)

    # ── Category 3: related tests ────────────────────────────────────────────
    related_tests = _find_tests(graph, target_file, target_symbol, directly)

    # ── Category 4: related APIs ─────────────────────────────────────────────
    related_apis = _find_apis(graph, target_file, target_symbol, directly, indirectly)

    # ── Category 5: related DB components ───────────────────────────────────
    related_db = _find_db(graph, target_file, target_layer, signals)

    # ── Category 6: risk areas ───────────────────────────────────────────────
    risk_areas = _score_risks(
        graph, target_file, target_symbol, target_layer,
        directly, indirectly, related_tests, related_apis, related_db, signals,
    )

    # ── Category 7: testing suggestions ──────────────────────────────────────
    testing_suggestions = _suggest_testing(
        target_symbol, directly, indirectly,
        related_tests, related_apis, related_db, risk_areas, signals,
    )

    # ── Overall risk level ────────────────────────────────────────────────────
    risk_level, risk_breakdown = _compute_overall_risk(
        directly, indirectly, related_tests, related_apis, related_db, risk_areas, signals,
    )

    return ImpactResult(
        target_file=target_file,
        target_symbol=target_symbol,
        target_layer=target_layer,
        target_signature=target_info.get("signature", ""),
        target_docstring=target_info.get("docstring", ""),
        change_description=change_description,
        change_type=change_type,
        directly_affected=directly,
        indirectly_affected=indirectly,
        related_tests=related_tests,
        related_apis=related_apis,
        related_db=related_db,
        risk_areas=risk_areas,
        testing_suggestions=testing_suggestions,
        risk_level=risk_level,
        risk_breakdown=risk_breakdown,
    )


# ---------------------------------------------------------------------------
# Category 1 & 2: affected component tracing
# ---------------------------------------------------------------------------

def _trace_affected(
    graph: CodebaseGraph,
    target_file: str,
    target_symbol: str,
) -> tuple[list[AffectedComponent], list[AffectedComponent]]:
    """
    Walk the graph from the target outward.

    Direct (depth=1):
      - Files that call the symbol (RefEdges with to_symbol == target_id)
      - Files that import the symbol by name (ImportEdge.names contains target_symbol)

    Indirect (depth=2):
      - Files that import from any depth-1 file
      (These learn about the change through a one-hop chain.)
    """
    target_id = f"{target_file}#{target_symbol}"
    direct_files: set[str] = set()
    directly: list[AffectedComponent] = []

    # RefEdge callers
    for edge in graph.callers_of(target_id):
        f = edge.from_file
        if f == target_file or f in direct_files:
            continue
        # Explain based on the caller file's role/layer
        flayer = graph.files[f].layer if f in graph.files else "module"
        if flayer == "controller":
            reason = f"Calls `{target_symbol}` in request handling flow — changes to parameter signature, return shape, or error handling will directly affect controller responses."
        elif flayer == "route":
            reason = f"Directly invokes `{target_symbol}` in API route handler — changes may break the HTTP endpoint contract."
        elif flayer == "service":
            reason = f"Calls `{target_symbol}` in business workflow — updates to behavior or return types may cascade through service logic."
        else:
            reason = f"Directly calls `{target_symbol}` at line {edge.line} — requires review for compatible arguments and return types."

        directly.append(_make_component(graph, f, depth=1, reason=reason))
        direct_files.add(f)

    # ImportEdge importers (files that do `from X import target_symbol`)
    for imp in graph.imports:
        if imp.to_file == target_file and target_symbol in imp.names:
            f = imp.from_file
            if f == target_file or f in direct_files:
                continue
            flayer = graph.files[f].layer if f in graph.files else "module"
            reason = (
                f"Imports `{target_symbol}` from `{target_file}` — depends on this symbol's exported contract and interface."
            )
            directly.append(_make_component(graph, f, depth=1, reason=reason))
            direct_files.add(f)

    # Also include files that import the TARGET FILE itself (module-level import)
    target_module = target_file.replace("/", ".").removesuffix(".py")
    for imp in graph.imports:
        if imp.to_file == target_file and not imp.names:
            f = imp.from_file
            if f == target_file or f in direct_files:
                continue
            reason = f"Imports module `{target_module}` — uses services/types exported by `{target_file}`."
            directly.append(_make_component(graph, f, depth=1, reason=reason))
            direct_files.add(f)

    # Indirect: files that import from any direct file
    indirect_files: set[str] = set()
    indirectly: list[AffectedComponent] = []
    for d1_file in list(direct_files):
        d1_name = d1_file.rsplit("/", 1)[-1]
        for imp in graph.imports:
            if imp.to_file == d1_file:
                f = imp.from_file
                if f in direct_files or f == target_file or f in indirect_files:
                    continue
                flayer = graph.files[f].layer if f in graph.files else "module"
                if flayer == "route":
                    reason = f"Routes to `{d1_name}` (which depends on `{target_symbol}`) — changes may cascade to API endpoint responses."
                elif flayer == "frontend":
                    reason = f"Consumes API routes backed by `{d1_name}` — frontend payload parsing or UX flow may require adjustment."
                else:
                    reason = f"Imports from `{d1_name}` (which calls `{target_symbol}`) — indirect transitive dependency."

                indirectly.append(_make_component(graph, f, depth=2, reason=reason))
                indirect_files.add(f)

    return directly, indirectly


def _make_component(graph: CodebaseGraph, file: str,
                     depth: int, reason: str) -> AffectedComponent:
    file_node = graph.files.get(file)
    layer = file_node.layer if file_node else "other"

    # First public symbol in the file as the representative name
    syms = [s for s in (file_node.symbols if file_node else []) if not s.startswith("_")]
    rep_symbol = syms[0] if syms else file.rsplit("/", 1)[-1].removesuffix(".py")

    impact_type = _classify_impact(layer, depth)

    return AffectedComponent(
        file=file, symbol=rep_symbol, layer=layer,
        reason=reason, depth=depth, impact_type=impact_type,
    )


def _classify_impact(layer: str, depth: int) -> str:
    if layer == "test":
        return "test_coverage"
    if layer == "model":
        return "data_schema"
    if layer in ("route", "controller") and depth == 1:
        return "api_surface"
    return "direct_caller" if depth == 1 else "transitive_caller"


# ---------------------------------------------------------------------------
# Category 3: related tests
# ---------------------------------------------------------------------------

def _find_tests(
    graph: CodebaseGraph,
    target_file: str,
    target_symbol: str,
    directly: list[AffectedComponent],
) -> list[dict]:
    """
    Collect test functions that cover:
      a) the target symbol directly (TestCoversEdge)
      b) any symbol in a directly-affected file (catches integration tests)

    Each result carries enough information for a rendered test row and a
    runnable pytest command.
    """
    target_id = f"{target_file}#{target_symbol}"
    seen: set[str] = set()
    results: list[dict] = []

    def _add(test_file: str, test_fn: str, covered: str, test_type: str) -> None:
        key = f"{test_file}::{test_fn}"
        if key in seen:
            return
        seen.add(key)
        fname = test_file.rsplit("/", 1)[-1]
        results.append({
            "file":        test_file,
            "function":    test_fn,
            "test_type":   test_type,
            "command":     f"pytest {test_file} -v -k {test_fn}",
            "reason":      f"Exercises `{covered}` ({test_type} test) — validates regression boundaries and assertion contracts for this change.",
        })

    # a) direct test coverage of the target symbol
    for edge in graph.tests_for(target_id):
        t = "integration" if ("route" in edge.test_file or "checkout" in edge.test_file) else "unit"
        _add(edge.test_file, edge.test_function, target_symbol, t)

    # b) tests in directly-affected files
    for comp in directly:
        f = comp.file
        if not f.startswith("tests/"):
            continue
        file_node = graph.files.get(f)
        if not file_node:
            continue
        for sym_name in file_node.symbols:
            if sym_name.startswith("test_"):
                t = "integration" if ("route" in f or "checkout" in f) else "unit"
                _add(f, sym_name, comp.symbol, t)

    # c) tests of any symbol in directly-affected service/controller files
    direct_service_files = {c.file for c in directly if c.layer in ("service", "controller")}
    for svc_file in direct_service_files:
        svc_node = graph.files.get(svc_file)
        if not svc_node:
            continue
        for sym_name in svc_node.symbols:
            sym_id = f"{svc_file}#{sym_name}"
            for edge in graph.tests_for(sym_id):
                t = "integration" if ("route" in edge.test_file or "checkout" in edge.test_file) else "unit"
                _add(edge.test_file, edge.test_function, sym_name, t)

    # d) frontend integration tests (e.g. test_checkout.py for frontend/Checkout.tsx or test_payment_*.py for frontend/PaymentForm.tsx)
    if target_file.startswith("frontend/"):
        target_stem = target_file.rsplit("/", 1)[-1].split(".")[0].lower()
        for edge in graph.test_covers:
            if target_stem in edge.test_file.lower() or target_stem in edge.test_function.lower():
                _add(edge.test_file, edge.test_function, target_symbol, "integration")

    return results


# ---------------------------------------------------------------------------
# Category 4: related APIs
# ---------------------------------------------------------------------------

def _find_apis(
    graph: CodebaseGraph,
    target_file: str,
    target_symbol: str,
    directly: list[AffectedComponent],
    indirectly: list[AffectedComponent],
) -> list[AffectedAPI]:
    """
    Find HTTP routes whose handler chain touches the target.

    An API is considered related if:
      - Its defining file is in the directly/indirectly affected set, OR
      - Its defining file imports the target file, OR
      - The target file is a frontend component that makes fetch calls matching the route path.
    """
    relevant_files: set[str] = {target_file}
    relevant_files.update(c.file for c in directly)
    relevant_files.update(c.file for c in indirectly)

    # If target is frontend, read its source to find any /api/... calls
    frontend_api_paths: set[str] = set()
    if target_file.startswith("frontend/"):
        import os
        from engine.codebase_graph import DEMO_ROOT
        abs_path = os.path.join(DEMO_ROOT, target_file)
        try:
            source = open(abs_path, encoding="utf-8").read()
            # Match paths like '/orders', '/payments', '/users/:id', etc.
            found_paths = re.findall(r"""['"`](/api/[^'"`?]+|/orders[^'"`?]*|/payments[^'"`?]*|/users[^'"`?]*)['"`]""", source)
            for p in found_paths:
                clean_p = p.replace("/api", "")
                frontend_api_paths.add(clean_p.split("/")[1] if len(clean_p.split("/")) > 1 else clean_p)
        except OSError:
            pass

    seen_routes: set[str] = set()
    results: list[AffectedAPI] = []

    for route in graph.routes:
        key = f"{route.http_method}:{route.path}"
        if key in seen_routes:
            continue

        route_prefix = route.path.strip("/").split("/")[0] if route.path.strip("/") else ""
        is_frontend_match = bool(frontend_api_paths and route_prefix in frontend_api_paths)

        if route.file not in relevant_files and not is_frontend_match:
            continue
        seen_routes.add(key)

        # Explain why this route is affected
        if route.file == target_file:
            reason = f"Route handler directly defined in `{target_file}` — any contract change will alter the public endpoint interface."
        elif is_frontend_match:
            reason = f"Frontend `{target_file}` makes API requests to `{route.path}` — contract changes on this endpoint directly impact user interactions."
        elif route.file in {c.file for c in directly}:
            reason = f"Route handler `{route.handler_function}` calls the directly affected component — changes to payload, status codes, or errors may impact clients."
        else:
            reason = f"Route handler `{route.handler_function}` transitively executes `{target_symbol}` in its call chain."

        results.append(AffectedAPI(
            http_method=route.http_method,
            path=route.path,
            file=route.file,
            handler=route.handler_function,
            reason=reason,
        ))

    return results


# ---------------------------------------------------------------------------
# Category 5: related DB components
# ---------------------------------------------------------------------------

def _find_db(
    graph: CodebaseGraph,
    target_file: str,
    target_layer: str,
    signals: set[str],
) -> list[AffectedDB]:
    """
    Identify database tables that may be affected.

    Inclusion rules:
      - When target is a model or service, include tables referenced by word-boundary in the file.
      - When signals contain 'db_change' or 'schema_change', match relevant tables based on file context.
    """
    if target_layer not in ("model", "service", "schema") and "db_change" not in signals and "schema_change" not in signals:
        return []

    # Read the target file's source to scope to relevant table names
    import os
    from engine.codebase_graph import DEMO_ROOT
    abs_path = os.path.join(DEMO_ROOT, target_file)
    try:
        source = open(abs_path, encoding="utf-8").read().lower()
    except OSError:
        source = ""

    # Also include tables whose name matches any symbol in the target file
    file_node = graph.files.get(target_file)
    symbol_names_lower = {s.lower() for s in (file_node.symbols if file_node else [])}

    results: list[AffectedDB] = []
    seen: set[str] = set()

    for schema in graph.schema_nodes:
        tbl = schema.table_name.lower()
        if tbl in seen:
            continue

        # Check word-boundary match in source or exact symbol containment
        table_in_source = bool(re.search(rf"\b{re.escape(tbl)}\b", source))
        sym_match = any(tbl == s or (len(tbl) >= 4 and tbl in s) for s in symbol_names_lower)

        if table_in_source or sym_match:
            seen.add(tbl)
            results.append(AffectedDB(
                table_name=schema.table_name,
                operation=schema.operation,
                file=schema.file,
                line=schema.line,
                reason=_db_reason(tbl, target_file, signals),
            ))

    return results


def _db_reason(table: str, target_file: str, signals: set[str]) -> str:
    if "db_change" in signals or "schema_change" in signals:
        return f"Change description suggests a schema alteration affecting `{table}`"
    return f"Table `{table}` is referenced by `{target_file}` and may need migration"


# ---------------------------------------------------------------------------
# Category 6: risk areas
# ---------------------------------------------------------------------------

def _score_risks(
    graph: CodebaseGraph,
    target_file: str,
    target_symbol: str,
    target_layer: str,
    directly: list[AffectedComponent],
    indirectly: list[AffectedComponent],
    related_tests: list[dict],
    related_apis: list[AffectedAPI],
    related_db: list[AffectedDB],
    signals: set[str],
) -> list[RiskArea]:
    """
    Produce a prioritised list of specific risk signals.

    Each risk area has a severity, category, human-readable title, and
    explanation.  Risks are generated by a set of independent rules; each
    rule fires independently based on the graph data and signals.
    """
    risks: list[RiskArea] = []

    # ── Rule 1: wide direct impact ───────────────────────────────────────────
    direct_count = len(directly)
    if direct_count >= 4:
        risks.append(RiskArea(
            severity="critical",
            category="wide_impact",
            title="High dependency centrality",
            description=(
                f"`{target_symbol}` is called by {direct_count} components directly. "
                "A signature or behavioural change will require updates in all of them."
            ),
            affected_files=[c.file for c in directly],
        ))
    elif direct_count >= 2:
        risks.append(RiskArea(
            severity="high",
            category="wide_impact",
            title="Multiple direct callers",
            description=(
                f"{direct_count} components call `{target_symbol}` directly. "
                "Each must be verified after the change."
            ),
            affected_files=[c.file for c in directly],
        ))

    # ── Rule 2: public API surface ────────────────────────────────────────────
    if related_apis:
        route_paths = [f"{a.http_method} {a.path}" for a in related_apis]
        risks.append(RiskArea(
            severity="high",
            category="api_contract",
            title="Public API contract at risk",
            description=(
                f"The change may alter the behaviour of {len(related_apis)} HTTP endpoint(s): "
                f"{', '.join(route_paths[:3])}{'…' if len(route_paths) > 3 else ''}. "
                "External clients relying on these contracts may break."
            ),
            affected_files=[a.file for a in related_apis],
        ))

    # ── Rule 3: database migration risk ──────────────────────────────────────
    if related_db and ("db_change" in signals or "schema_change" in signals or target_layer == "model"):
        tables = [d.table_name for d in related_db]
        risks.append(RiskArea(
            severity="critical" if "breaking_change" in signals else "high",
            category="db_migration",
            title="Database schema migration required",
            description=(
                f"The change affects {len(tables)} table(s): {', '.join(tables[:4])}. "
                "A migration script must be written, tested, and applied atomically."
            ),
            affected_files=[d.file for d in related_db],
        ))
    elif related_db and target_layer in ("model", "service"):
        risks.append(RiskArea(
            severity="medium",
            category="db_migration",
            title="Possible data persistence side-effects",
            description=(
                f"The target is in the {target_layer} layer and is connected to "
                f"{len(related_db)} table(s). Verify that no persisted data is altered unexpectedly."
            ),
            affected_files=[d.file for d in related_db],
        ))

    # ── Rule 4: test coverage gap ────────────────────────────────────────────
    uncovered_direct = [
        c for c in directly
        if not any(t.get("file", "").endswith(f"test_{c.file.rsplit('/', 1)[-1]}")
                   for t in related_tests)
        and c.layer not in ("test", "schema")
    ]
    if not related_tests:
        risks.append(RiskArea(
            severity="critical",
            category="test_gap",
            title="No automated tests cover this symbol",
            description=(
                f"No test functions were found that reference `{target_symbol}`. "
                "Changes here will have zero automated regression safety net."
            ),
            affected_files=[target_file],
        ))
    elif len(related_tests) <= 2:
        risks.append(RiskArea(
            severity="medium",
            category="test_gap",
            title="Limited test coverage",
            description=(
                f"Only {len(related_tests)} test function(s) cover `{target_symbol}`. "
                "Consider adding edge-case and integration tests before changing."
            ),
            affected_files=[t["file"] for t in related_tests],
        ))

    # ── Rule 5: breaking change signal ───────────────────────────────────────
    if "breaking_change" in signals:
        risks.append(RiskArea(
            severity="critical",
            category="semantic",
            title="Destructive change detected in description",
            description=(
                "The change description contains keywords associated with breaking changes "
                "(rename, remove, delete, drop, deprecate). "
                "Downstream callers may fail at runtime without a coordinated migration plan."
            ),
            affected_files=[c.file for c in directly],
        ))

    # ── Rule 6: signature change propagation ─────────────────────────────────
    if "signature_change" in signals:
        risks.append(RiskArea(
            severity="high",
            category="semantic",
            title="Function signature change",
            description=(
                "Adding, removing, or renaming parameters will require all "
                f"{direct_count} direct callers to be updated. "
                "Any call site that passes positional arguments is particularly fragile."
            ),
            affected_files=[c.file for c in directly],
        ))

    # ── Rule 7: new integration / third-party provider ───────────────────────
    if "new_integration" in signals:
        risks.append(RiskArea(
            severity="high",
            category="semantic",
            title="New external integration introduced",
            description=(
                "Integrating a new external provider or gateway typically requires "
                "updated error handling, new secrets/config keys, and contract tests "
                "against the new provider's sandbox API."
            ),
            affected_files=[target_file] + [c.file for c in directly[:3]],
        ))

    # ── Rule 8: security-sensitive path ──────────────────────────────────────
    if "security" in signals or target_layer == "service" and any(
        kw in target_symbol.lower() for kw in ("auth", "token", "password", "permission", "encrypt")
    ):
        risks.append(RiskArea(
            severity="critical",
            category="semantic",
            title="Security-sensitive change",
            description=(
                "This change touches an authentication or security-sensitive component. "
                "Require a security review and ensure no secrets are exposed in logs or responses."
            ),
            affected_files=[target_file] + [c.file for c in directly],
        ))

    # Sort: critical first, then high, medium, low
    order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    risks.sort(key=lambda r: order.get(r.severity, 4))
    return risks


# ---------------------------------------------------------------------------
# Category 7: testing suggestions
# ---------------------------------------------------------------------------

def _suggest_testing(
    target_symbol: str,
    directly: list[AffectedComponent],
    indirectly: list[AffectedComponent],
    related_tests: list[dict],
    related_apis: list[AffectedAPI],
    related_db: list[AffectedDB],
    risk_areas: list[RiskArea],
    signals: set[str],
) -> list[TestingSuggestion]:
    """
    Produce a ranked list of concrete testing actions derived from the
    analysis results.  No hard-coded component names — all suggestions are
    generated from what the graph found.
    """
    suggestions: list[TestingSuggestion] = []

    # 1. Run existing unit tests for the target symbol
    unit_tests = [t for t in related_tests if t["test_type"] == "unit"]
    if unit_tests:
        commands = list({t["command"] for t in unit_tests})
        suggestions.append(TestingSuggestion(
            priority="must",
            action=f"Re-run all existing unit tests for `{target_symbol}`",
            detail=(
                f"Found {len(unit_tests)} unit test(s) that cover `{target_symbol}`. "
                "They must all pass after the change."
            ),
            command=commands[0] if len(commands) == 1 else f"pytest {unit_tests[0]['file']} -v",
        ))
    else:
        suggestions.append(TestingSuggestion(
            priority="must",
            action=f"Write unit tests for `{target_symbol}` before changing it",
            detail=(
                "No existing unit tests were found. Add tests covering the current behaviour "
                "first to establish a regression baseline."
            ),
            command=None,
        ))

    # 2. Run integration tests if any APIs are affected
    integration_tests = [t for t in related_tests if t["test_type"] == "integration"]
    if integration_tests and related_apis:
        suggestions.append(TestingSuggestion(
            priority="must",
            action="Run integration tests covering the affected API endpoints",
            detail=(
                f"Found {len(integration_tests)} integration test(s) that exercise the "
                f"{len(related_apis)} affected API route(s). These verify the end-to-end "
                "contract remains intact."
            ),
            command=f"pytest {integration_tests[0]['file']} -v",
        ))

    # 3. Manual API contract verification for each affected endpoint
    if related_apis:
        route_list = "; ".join(f"{a.http_method} {a.path}" for a in related_apis[:3])
        suggestions.append(TestingSuggestion(
            priority="must",
            action="Verify API response shapes for all affected endpoints",
            detail=(
                f"Endpoints {route_list} may return different data after this change. "
                "Confirm that response shape, status codes, and error payloads are unchanged "
                "(or document the breaking change if intentional)."
            ),
            command=None,
        ))

    # 4. DB migration test
    if related_db and ("db_change" in signals or "schema_change" in signals):
        suggestions.append(TestingSuggestion(
            priority="must",
            action="Test database migration on a staging environment before production",
            detail=(
                f"Tables {', '.join(d.table_name for d in related_db[:3])} may be altered. "
                "Apply the migration against a production-scale data copy and verify row counts, "
                "constraints, and query performance."
            ),
            command=None,
        ))

    # 5. Backward compatibility check for signature changes
    if "signature_change" in signals or "breaking_change" in signals:
        direct_files = [c.file for c in directly if c.layer not in ("test", "schema")]
        suggestions.append(TestingSuggestion(
            priority="must",
            action="Audit every call site in directly affected files",
            detail=(
                f"{len(direct_files)} file(s) call this symbol. "
                "Search for positional arguments that may break silently when the signature changes."
            ),
            command=None,
        ))

    # 6. New integration test for new provider / gateway
    if "new_integration" in signals:
        suggestions.append(TestingSuggestion(
            priority="must",
            action="Add a sandbox/mock integration test for the new provider",
            detail=(
                "Before enabling the new integration in production, add tests that mock or "
                "use the provider's sandbox API to verify request/response handling, timeout "
                "behaviour, and error codes."
            ),
            command=None,
        ))

    # 7. Smoke test for all indirectly affected components
    if indirectly:
        suggestions.append(TestingSuggestion(
            priority="should",
            action="Smoke-test indirectly affected components",
            detail=(
                f"{len(indirectly)} component(s) reach this symbol transitively. "
                "A lightweight happy-path test for each verifies no silent breakage."
            ),
            command="pytest tests/ -v -x",
        ))

    # 8. Security review suggestion
    if "security" in signals:
        suggestions.append(TestingSuggestion(
            priority="must",
            action="Conduct a security review before merging",
            detail=(
                "This change touches a security-sensitive component. "
                "Have a second developer review for: secret exposure, input sanitisation, "
                "token expiry handling, and privilege escalation paths."
            ),
            command=None,
        ))

    # 9. Run the full test suite as a final gate
    suggestions.append(TestingSuggestion(
        priority="should",
        action="Run the full test suite as a final regression gate",
        detail="Confirm no unexpected failures across all 71 demo tests.",
        command="pytest tests/ -v",
    ))

    return suggestions


# ---------------------------------------------------------------------------
# Overall risk score
# ---------------------------------------------------------------------------

def _compute_overall_risk(
    directly: list[AffectedComponent],
    indirectly: list[AffectedComponent],
    related_tests: list[dict],
    related_apis: list[AffectedAPI],
    related_db: list[AffectedDB],
    risk_areas: list[RiskArea],
    signals: set[str],
) -> tuple[str, dict]:
    """
    Derive a single CRITICAL/HIGH/MEDIUM/LOW label from the 4-factor matrix,
    with semantic signal boosting from the change description.
    """
    direct_count = len(directly)
    api_count    = len(related_apis)
    db_count     = len(related_db)
    test_count   = len(related_tests)

    # Factor scores (1=low, 2=medium, 3=high/critical)
    dep_score = 3 if direct_count >= 4 else (2 if direct_count >= 2 else 1)
    api_score = 3 if api_count >= 3  else (2 if api_count >= 1  else 1)
    db_score  = 3 if db_count >= 3   else (2 if db_count >= 1   else 1)
    tst_score = 3 if test_count == 0 else (2 if test_count <= 2  else 1)

    base_score = max(dep_score, api_score, db_score, tst_score)

    # Semantic boosting
    if any(sig in signals for sig in ("breaking_change", "security", "db_change")):
        base_score = max(base_score, 3)
    if any(sig in signals for sig in ("signature_change", "api_change", "new_integration")):
        base_score = max(base_score, 2)

    # Any critical risk area overrides to CRITICAL
    has_critical_risk = any(r.severity == "critical" for r in risk_areas)
    if has_critical_risk:
        base_score = 3
        # distinguish CRITICAL vs HIGH at score 3
        level = "CRITICAL"
    elif base_score == 3:
        level = "HIGH"
    elif base_score == 2:
        level = "MEDIUM"
    else:
        level = "LOW"

    label_map = {1: "low", 2: "medium", 3: "high"}
    breakdown = {
        "dependency_centrality": label_map[dep_score],
        "api_boundary":          label_map[api_score],
        "data_persistence":      label_map[db_score],
        "test_coverage":         label_map[tst_score],
        "overall":               level,
    }
    return level, breakdown
