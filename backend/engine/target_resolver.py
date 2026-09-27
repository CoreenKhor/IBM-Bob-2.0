"""
Step 1 — Target Resolver

Uses the CodebaseGraph to locate a named symbol in the demo codebase.
Falls back to direct AST parsing for symbols not yet in the cached graph.
"""

from __future__ import annotations
import ast
import os
import re
from engine.codebase_graph import get_graph, DEMO_ROOT


def resolve_target(target_file: str, target_symbol: str) -> dict:
    """
    Locate target_symbol inside target_file using the cached CodebaseGraph.

    Returns:
      { file, symbol, line_start, line_end, signature, docstring }
    or
      { error: "..." }
    """
    # Guard against path traversal
    abs_path = os.path.realpath(os.path.join(DEMO_ROOT, target_file))
    if not abs_path.startswith(DEMO_ROOT):
        return {"error": "Path traversal detected — target_file must be inside demo codebase"}
    if not os.path.isfile(abs_path):
        return {"error": f"File not found: {target_file}"}

    graph = get_graph()
    sym = graph.get_symbol(target_file, target_symbol)

    if sym:
        return {
            "file":       sym.file,
            "symbol":     sym.name,
            "kind":       sym.kind,
            "line_start": sym.line_start,
            "line_end":   sym.line_end,
            "signature":  sym.signature,
            "docstring":  sym.docstring,
        }

    # Symbol not in graph (file added after graph was built, or typo check)
    # Fall back to direct parse for Python, or regex for TS/JS.
    try:
        source = open(abs_path, encoding="utf-8").read()
    except OSError as exc:
        return {"error": f"Cannot read {target_file}: {exc}"}

    ext = os.path.splitext(target_file)[1].lower()
    if ext == ".py":
        try:
            tree = ast.parse(source)
            defined = [
                n.name for n in ast.walk(tree)
                if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
            ]
        except SyntaxError as exc:
            return {"error": f"Cannot parse {target_file}: {exc}"}
    else:
        fn_re = re.compile(
            r"""^(?:export\s+(?:default\s+)?)?(?:function|class|const|let)\s+([A-Za-z_][A-Za-z0-9_]*)""",
            re.MULTILINE,
        )
        defined = fn_re.findall(source)

    hint = f"  Available symbols: {', '.join(sorted(set(defined)))}" if defined else ""
    return {"error": f"Symbol '{target_symbol}' not found in {target_file}.{hint}"}
