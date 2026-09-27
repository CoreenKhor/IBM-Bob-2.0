"""
CodebaseGraph — Structured Representation of the Demo E-Commerce Codebase

Builds a complete in-memory graph of the codebase by analysing every .py and
.sql file in demo/ecommerce/.  The graph is computed ONCE on first use and
then cached; subsequent calls return the same object.

--- What is indexed and how ---

1. FILES
   Every .py and .sql file under demo/ecommerce/ becomes a FileNode.

2. SYMBOLS  (Python only)
   Python's built-in `ast` module parses each .py file.
   Top-level and class-level FunctionDef / AsyncFunctionDef / ClassDef nodes
   are turned into SymbolNodes.  Each symbol carries:
     - name, kind (function | class | method)
     - file, line_start, line_end
     - signature (first source line)
     - docstring (first string constant in body, if present)

3. IMPORTS
   `ast.Import` / `ast.ImportFrom` statements are collected verbatim, giving
   a list of ImportEdges: (importer_file, imported_module, imported_names).
   These are resolved to actual FileNodes where the module name matches a file
   in the codebase (e.g. `from services.order_service import …` → services/order_service.py).

4. SYMBOL REFERENCES
   A second regex pass searches every .py file for bare symbol-name usage
   (calls, attribute access) outside the defining file.
   This catches calls like `calculate_order_total(...)` that appear in files
   other than services/order_service.py, without requiring a full type-checker.

5. API ROUTES
   Regex detects Flask route decorators:
     @<name>.route("<path>", methods=[...])
   Each match becomes a RouteNode linked to the file and the decorated function.

6. DATABASE REFERENCES
   - In Python files: SQLAlchemy-style class bodies that reference column-type
     keywords (Integer, String, Boolean, Text, REAL, etc.) are tagged "orm_model".
   - In .sql files: every CREATE TABLE / ALTER TABLE statement becomes a
     SchemaNode.
   - Any Python file that calls .query / .filter / .execute / session usage
     is tagged with a "db_access" edge.

7. TEST RELATIONSHIPS
   Files whose name starts with `test_` are TestFileNodes.
   For each test function (def test_*), the source is scanned for references
   to non-test symbols; matched pairs become TestCoversEdges.

--- Graph node types ---

  FileNode        { path, language, layer, size_lines }
  SymbolNode      { id, name, kind, file, line_start, line_end, signature, docstring }
  ImportEdge      { from_file, to_module, to_file|None, names }
  RefEdge         { from_file, from_symbol, to_symbol, line, ref_type }
  RouteNode       { method, path, file, handler_function }
  SchemaNode      { table_name, operation, file, line }
  TestCoversEdge  { test_file, test_function, covered_symbol, covered_file }
"""

from __future__ import annotations

import ast
import os
import re
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Optional

# ---------------------------------------------------------------------------
# Path constant — demo codebase root
# ---------------------------------------------------------------------------
DEMO_ROOT = os.path.realpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "demo", "ecommerce")
)

# ---------------------------------------------------------------------------
# Layer classification rules (path prefix → architectural layer name)
# ---------------------------------------------------------------------------
_LAYER_RULES: list[tuple[str, str]] = [
    ("tests/",       "test"),
    ("routes/",      "route"),
    ("controllers/", "controller"),
    ("services/",    "service"),
    ("models/",      "model"),
    ("schema/",      "schema"),
    ("frontend/",    "frontend"),
]


def _classify_layer(rel_path: str) -> str:
    for prefix, layer in _LAYER_RULES:
        if rel_path.startswith(prefix):
            return layer
    return "other"


# ---------------------------------------------------------------------------
# Data classes (lightweight — plain dicts are also fine, but dataclasses give
# us dot-access and make the code self-documenting for the hackathon demo)
# ---------------------------------------------------------------------------

@dataclass
class FileNode:
    path: str                    # relative to DEMO_ROOT, forward slashes
    language: str                # "python" | "sql" | "typescript" | "other"
    layer: str                   # architectural layer (service, model, test…)
    size_lines: int              # line count
    symbols: list[str] = field(default_factory=list)   # symbol names defined here


@dataclass
class SymbolNode:
    id: str                      # "<file>#<name>"  e.g. "services/order_service.py#calculate_order_total"
    name: str
    kind: str                    # "function" | "async_function" | "class" | "method"
    file: str
    line_start: int
    line_end: int
    signature: str
    docstring: str


@dataclass
class ImportEdge:
    from_file: str               # importer
    to_module: str               # raw module string from import statement
    to_file: Optional[str]       # resolved FileNode.path, or None if external
    names: list[str]             # imported names  ([] if `import module`)


@dataclass
class RefEdge:
    from_file: str
    from_symbol: str             # symbol id of caller (or "" if module-level)
    to_symbol: str               # symbol id of callee
    line: int
    ref_type: str                # "call" | "import" | "attribute"


@dataclass
class RouteNode:
    http_method: str             # "GET" | "POST" | "DELETE" | "PATCH" | …
    path: str                    # "/orders" | "/payments/order/<id>"
    file: str
    handler_function: str        # name of the decorated Python function


@dataclass
class SchemaNode:
    table_name: str
    operation: str               # "CREATE TABLE" | "ALTER TABLE" | "DROP TABLE"
    file: str
    line: int


@dataclass
class TestCoversEdge:
    test_file: str
    test_function: str
    covered_symbol: str          # symbol id
    covered_file: str


# ---------------------------------------------------------------------------
# The graph itself
# ---------------------------------------------------------------------------

@dataclass
class CodebaseGraph:
    """
    Complete structural model of the demo codebase.

    All collections are keyed for O(1) lookup where relevant.
    """
    # Primary collections
    files:   dict[str, FileNode]     = field(default_factory=dict)    # path → FileNode
    symbols: dict[str, SymbolNode]   = field(default_factory=dict)    # id   → SymbolNode

    # Edges / relationships
    imports:      list[ImportEdge]      = field(default_factory=list)
    refs:         list[RefEdge]         = field(default_factory=list)
    routes:       list[RouteNode]       = field(default_factory=list)
    schema_nodes: list[SchemaNode]      = field(default_factory=list)
    test_covers:  list[TestCoversEdge]  = field(default_factory=list)

    # Convenience indexes (built after initial population)
    _symbols_by_name:  dict[str, list[str]] = field(default_factory=dict)  # name → [symbol_ids]
    _refs_by_file:     dict[str, list[RefEdge]] = field(default_factory=dict)
    _imports_by_file:  dict[str, list[ImportEdge]] = field(default_factory=dict)
    _callers_of:       dict[str, list[RefEdge]] = field(default_factory=dict)  # symbol_id → edges
    _tests_for_symbol: dict[str, list[TestCoversEdge]] = field(default_factory=dict)

    def summary(self) -> dict:
        """Return a human-readable statistics dict."""
        return {
            "files":        len(self.files),
            "symbols":      len(self.symbols),
            "imports":      len(self.imports),
            "refs":         len(self.refs),
            "routes":       len(self.routes),
            "schema_nodes": len(self.schema_nodes),
            "test_covers":  len(self.test_covers),
        }

    def get_symbol(self, file: str, name: str) -> Optional[SymbolNode]:
        return self.symbols.get(f"{file}#{name}")

    def callers_of(self, symbol_id: str) -> list[RefEdge]:
        """Return all RefEdges where to_symbol == symbol_id."""
        return self._callers_of.get(symbol_id, [])

    def imports_of(self, file: str) -> list[ImportEdge]:
        return self._imports_by_file.get(file, [])

    def tests_for(self, symbol_id: str) -> list[TestCoversEdge]:
        return self._tests_for_symbol.get(symbol_id, [])

    def routes_for_file(self, file: str) -> list[RouteNode]:
        return [r for r in self.routes if r.file == file]

    def schema_for_table(self, table: str) -> list[SchemaNode]:
        return [s for s in self.schema_nodes if s.table_name.lower() == table.lower()]


# ---------------------------------------------------------------------------
# Builder
# ---------------------------------------------------------------------------

class CodebaseGraphBuilder:
    """
    Walks the demo codebase and populates a CodebaseGraph.

    Designed for single-use: call .build() to get a fully populated graph.
    """

    def __init__(self, root: str = DEMO_ROOT):
        self._root = os.path.realpath(root)
        self._graph = CodebaseGraph()

    def build(self) -> CodebaseGraph:
        """Run all analysis passes and return the completed graph."""
        python_files: list[tuple[str, str]] = []   # (rel_path, source)
        sql_files:    list[tuple[str, str]] = []
        js_ts_files:  list[tuple[str, str]] = []

        # ── Pass 0: discover files ──────────────────────────────────────────
        for dirpath, dirnames, filenames in os.walk(self._root):
            dirnames[:] = sorted(
                d for d in dirnames
                if not d.startswith((".", "__"))
            )
            for fname in sorted(filenames):
                abs_path = os.path.join(dirpath, fname)
                rel_path = os.path.relpath(abs_path, self._root).replace("\\", "/")
                ext = os.path.splitext(fname)[1].lower()

                try:
                    source = open(abs_path, encoding="utf-8").read()
                except OSError:
                    continue

                lines = source.count("\n") + 1
                lang = {"py": "python", "sql": "sql", "ts": "typescript",
                        "tsx": "typescript", "js": "javascript"}.get(ext.lstrip("."), "other")

                node = FileNode(
                    path=rel_path,
                    language=lang,
                    layer=_classify_layer(rel_path),
                    size_lines=lines,
                )
                self._graph.files[rel_path] = node

                if ext == ".py":
                    python_files.append((rel_path, source))
                elif ext == ".sql":
                    sql_files.append((rel_path, source))
                elif ext in (".ts", ".tsx", ".js", ".jsx"):
                    js_ts_files.append((rel_path, source))

        # ── Pass 1: extract symbols and imports ─────────────────────────────
        for rel_path, source in python_files:
            self._parse_python_file(rel_path, source)
        for rel_path, source in js_ts_files:
            self._parse_jsts_file(rel_path, source)

        # ── Pass 2: SQL schema nodes ─────────────────────────────────────────
        for rel_path, source in sql_files:
            self._parse_sql_file(rel_path, source)

        # ── Pass 3: reference detection (over .py and .ts/.tsx files) ───────
        all_symbol_names = {sym.name for sym in self._graph.symbols.values()}
        for rel_path, source in python_files + js_ts_files:
            self._detect_refs(rel_path, source, all_symbol_names)

        # ── Pass 4: API route detection ──────────────────────────────────────
        for rel_path, source in python_files:
            self._detect_routes(rel_path, source)

        # ── Pass 5: test relationship detection ──────────────────────────────
        for rel_path, source in python_files:
            if rel_path.startswith("tests/"):
                self._detect_test_covers(rel_path, source, all_symbol_names)

        # ── Pass 6: build lookup indexes ─────────────────────────────────────
        self._build_indexes()

        return self._graph

    # -------------------------------------------------------------------------
    # Pass 1 helpers — AST analysis
    # -------------------------------------------------------------------------

    def _parse_python_file(self, rel_path: str, source: str) -> None:
        """Extract symbols and imports from a single Python file."""
        try:
            tree = ast.parse(source, filename=rel_path)
        except SyntaxError:
            return

        lines = source.splitlines()

        # Imports
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                module = node.module or ""
                names  = [alias.name for alias in node.names]
                to_file = self._resolve_module(module)
                self._graph.imports.append(ImportEdge(
                    from_file=rel_path,
                    to_module=module,
                    to_file=to_file,
                    names=names,
                ))
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    to_file = self._resolve_module(alias.name)
                    self._graph.imports.append(ImportEdge(
                        from_file=rel_path,
                        to_module=alias.name,
                        to_file=to_file,
                        names=[],
                    ))

        # Top-level and class-member symbols
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self._add_symbol(rel_path, node, lines, kind_prefix="")
            elif isinstance(node, ast.ClassDef):
                self._add_symbol(rel_path, node, lines, kind_prefix="")
                # Methods inside the class
                for child in node.body:
                    if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        self._add_symbol(rel_path, child, lines, kind_prefix="method")

    def _add_symbol(self, rel_path: str, node: ast.AST, lines: list[str],
                     kind_prefix: str) -> None:
        if isinstance(node, ast.ClassDef):
            kind = "class"
        elif isinstance(node, ast.AsyncFunctionDef):
            kind = "async_function"
        else:
            kind = "method" if kind_prefix == "method" else "function"

        name: str = node.name  # type: ignore[attr-defined]
        sig_line = node.lineno - 1  # type: ignore[attr-defined]
        signature = lines[sig_line].strip() if sig_line < len(lines) else ""
        docstring = ast.get_docstring(node) or ""  # type: ignore[arg-type]

        sym = SymbolNode(
            id=f"{rel_path}#{name}",
            name=name,
            kind=kind,
            file=rel_path,
            line_start=node.lineno,  # type: ignore[attr-defined]
            line_end=node.end_lineno or node.lineno,  # type: ignore[attr-defined]
            signature=signature,
            docstring=docstring[:200],   # truncate for readability
        )
        # Deduplicate: if a name appears multiple times (overloads etc.) keep first
        if sym.id not in self._graph.symbols:
            self._graph.symbols[sym.id] = sym
            self._graph.files[rel_path].symbols.append(name)

    def _resolve_module(self, module: str) -> Optional[str]:
        """
        Try to match a Python module string to a file in the demo codebase.

        e.g. "services.order_service" → "services/order_service.py"
             "models.payment"         → "models/payment.py"
             "flask"                  → None  (external)
        """
        candidate = module.replace(".", "/") + ".py"
        if candidate in self._graph.files:
            return candidate
        # Try just the last component (handles `from order_service import …`)
        parts = module.split(".")
        for depth in range(len(parts)):
            tail = "/".join(parts[depth:]) + ".py"
            if tail in self._graph.files:
                return tail
        return None   # external library

    def _parse_jsts_file(self, rel_path: str, source: str) -> None:
        """Extract exported components, functions, and imports from a JS/TS file."""
        lines = source.splitlines()
        dir_name = os.path.dirname(rel_path).replace("\\", "/")

        # Regex for ES6 imports: import ... from './PaymentForm' or '@/components/...'
        # e.g. import PaymentForm from './PaymentForm';
        #      import { useState, useEffect } from 'react';
        import_re = re.compile(r"""import\s+(?:(\w+)|\{([^}]+)\})\s+from\s+['"]([^'"]+)['"]""")
        for match in import_re.finditer(source):
            default_name = match.group(1)
            named_imports = match.group(2)
            module_path = match.group(3)

            names = []
            if default_name:
                names.append(default_name)
            if named_imports:
                names.extend([n.strip().split(" as ")[0].strip() for n in named_imports.split(",") if n.strip()])

            # Resolve relative import to codebase file
            to_file = None
            if module_path.startswith("."):
                candidate_base = os.path.normpath(os.path.join(dir_name, module_path)).replace("\\", "/")
                for ext in (".tsx", ".ts", ".jsx", ".js"):
                    cand = f"{candidate_base}{ext}"
                    if cand in self._graph.files:
                        to_file = cand
                        break

            self._graph.imports.append(ImportEdge(
                from_file=rel_path,
                to_module=module_path,
                to_file=to_file,
                names=names,
            ))

        # Regex for exported functions, classes, and component declarations
        # e.g. export default function Checkout(...)
        #      export function PaymentForm(...)
        #      function formatExpiry(...)
        #      const Checkout = (...) =>
        fn_re = re.compile(
            r"""^(?:export\s+(?:default\s+)?)?(?:function|class|const|let)\s+([A-Za-z_][A-Za-z0-9_]*)""",
            re.MULTILINE,
        )


        for i, line in enumerate(lines, start=1):
            m = fn_re.search(line)
            if m:
                name = m.group(1)
                # Skip react hooks or standard utility names if they are shadowed
                if name in ("useState", "useEffect", "useCallback", "useMemo", "useRef"):
                    continue
                sym = SymbolNode(
                    id=f"{rel_path}#{name}",
                    name=name,
                    kind="function" if "function" in line or "=>" in line else "class",
                    file=rel_path,
                    line_start=i,
                    line_end=i,
                    signature=line.strip()[:100],
                    docstring="",
                )
                if sym.id not in self._graph.symbols:
                    self._graph.symbols[sym.id] = sym
                    self._graph.files[rel_path].symbols.append(name)

    def _parse_sql_file(self, rel_path: str, source: str) -> None:
        for i, line in enumerate(source.splitlines(), start=1):
            m = re.search(
                r"\b(CREATE|ALTER|DROP)\s+TABLE\s+(?:IF\s+(?:NOT\s+)?EXISTS\s+)?(\w+)",
                line, re.IGNORECASE,
            )
            if m:
                self._graph.schema_nodes.append(SchemaNode(
                    table_name=m.group(2),
                    operation=m.group(1).upper() + " TABLE",
                    file=rel_path,
                    line=i,
                ))

    # -------------------------------------------------------------------------
    # Pass 3 — Reference detection
    # -------------------------------------------------------------------------

    # Patterns that indicate a symbol is used:
    #   symbol_name(    ← function call
    #   symbol_name.    ← attribute / method access
    #   import symbol_name  (already captured as ImportEdge but also as RefEdge)
    _REF_PATTERN = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*(?:\(|\.)")

    def _detect_refs(self, rel_path: str, source: str,
                      all_names: set[str]) -> None:
        """
        Scan each line for references to known symbol names.
        Only record a reference when the name belongs to a DIFFERENT file.
        """
        in_block_comment = False
        lines = source.splitlines()
        for lineno, line in enumerate(lines, start=1):
            stripped = line.strip()

            # Handle Python docstrings
            if stripped.startswith('"""') or stripped.startswith("'''"):
                if stripped.count('"""') % 2 == 1 or stripped.count("'''") % 2 == 1:
                    in_block_comment = not in_block_comment
                continue
            if in_block_comment:
                if '"""' in stripped or "'''" in stripped:
                    in_block_comment = False
                continue

            # Handle JS/TS multiline comments
            if stripped.startswith("/*") or stripped.startswith("/**"):
                if "*/" not in stripped:
                    in_block_comment = True
                continue
            if stripped.startswith("*") or stripped.startswith("*/"):
                if "*/" in stripped:
                    in_block_comment = False
                continue

            # Skip single line comments
            if stripped.startswith("#") or stripped.startswith("//"):
                continue

            for m in self._REF_PATTERN.finditer(line):
                name = m.group(1)
                if name not in all_names:
                    continue
                # Find which file(s) define this symbol
                for sym_id, sym in self._graph.symbols.items():
                    if sym.name == name and sym.file != rel_path:
                        ref_type = "call" if "(" in m.group(0) else "attribute"
                        self._graph.refs.append(RefEdge(
                            from_file=rel_path,
                            from_symbol="",   # refined in index build
                            to_symbol=sym_id,
                            line=lineno,
                            ref_type=ref_type,
                        ))
                        break  # one edge per call site per line

    # -------------------------------------------------------------------------
    # Pass 4 — API route detection
    # -------------------------------------------------------------------------

    _ROUTE_DEC = re.compile(
        r"""@\w+\.route\(\s*['"]([^'"]+)['"]\s*(?:,\s*methods\s*=\s*\[([^\]]*)\])?\s*\)""",
        re.DOTALL,
    )
    _HANDLER_DEF = re.compile(r"""^def\s+(\w+)\s*\(""", re.MULTILINE)

    def _detect_routes(self, rel_path: str, source: str) -> None:
        """Detect @blueprint.route decorators and link to their handler function."""
        for dec_match in self._ROUTE_DEC.finditer(source):
            route_path  = dec_match.group(1)
            methods_raw = dec_match.group(2) or "'GET'"
            methods = [
                m.strip().strip("\"'").upper()
                for m in methods_raw.split(",")
                if m.strip().strip("\"'")
            ]
            # The def statement follows immediately after the decorator block
            after = source[dec_match.end():]
            handler_match = self._HANDLER_DEF.search(after[:200])
            handler_name  = handler_match.group(1) if handler_match else "unknown"

            for method in methods:
                self._graph.routes.append(RouteNode(
                    http_method=method,
                    path=route_path,
                    file=rel_path,
                    handler_function=handler_name,
                ))

    # -------------------------------------------------------------------------
    # Pass 5 — Test coverage edges
    # -------------------------------------------------------------------------

    def _detect_test_covers(self, rel_path: str, source: str,
                              all_names: set[str]) -> None:
        """
        For each test_ function, find which non-test symbols it references.
        Emits TestCoversEdge(test_file, test_fn, covered_symbol, covered_file).
        """
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return

        lines = source.splitlines()
        for node in tree.body:
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if not node.name.startswith("test_"):
                continue

            fn_source = "\n".join(lines[node.lineno - 1 : node.end_lineno])
            seen: set[str] = set()
            for m in self._REF_PATTERN.finditer(fn_source):
                name = m.group(1)
                if name not in all_names or name in seen:
                    continue
                # Find the defining symbol in a non-test file
                for sym_id, sym in self._graph.symbols.items():
                    if sym.name == name and not sym.file.startswith("tests/"):
                        self._graph.test_covers.append(TestCoversEdge(
                            test_file=rel_path,
                            test_function=node.name,
                            covered_symbol=sym_id,
                            covered_file=sym.file,
                        ))
                        seen.add(name)
                        break

    # -------------------------------------------------------------------------
    # Pass 6 — Build lookup indexes
    # -------------------------------------------------------------------------

    def _build_indexes(self) -> None:
        g = self._graph

        # symbols_by_name
        for sym_id, sym in g.symbols.items():
            g._symbols_by_name.setdefault(sym.name, []).append(sym_id)

        # imports_by_file
        for edge in g.imports:
            g._imports_by_file.setdefault(edge.from_file, []).append(edge)

        # refs_by_file and callers_of
        for edge in g.refs:
            g._refs_by_file.setdefault(edge.from_file, []).append(edge)
            g._callers_of.setdefault(edge.to_symbol, []).append(edge)

        # tests_for_symbol
        for edge in g.test_covers:
            g._tests_for_symbol.setdefault(edge.covered_symbol, []).append(edge)


# ---------------------------------------------------------------------------
# Module-level cache — the graph is built once per process
# ---------------------------------------------------------------------------

_CACHED_GRAPH: Optional[CodebaseGraph] = None


def get_graph(force_rebuild: bool = False) -> CodebaseGraph:
    """
    Return the singleton CodebaseGraph, building it on first call.

    Pass force_rebuild=True in tests to get a fresh graph.
    """
    global _CACHED_GRAPH
    if _CACHED_GRAPH is None or force_rebuild:
        _CACHED_GRAPH = CodebaseGraphBuilder().build()
    return _CACHED_GRAPH


def build_graph(root: str = DEMO_ROOT) -> CodebaseGraph:
    """Build and return a graph for a specific root (useful for tests)."""
    return CodebaseGraphBuilder(root).build()
