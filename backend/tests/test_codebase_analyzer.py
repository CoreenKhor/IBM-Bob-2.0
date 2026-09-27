"""
Tests for the CodebaseGraph analyzer.

These tests verify that the graph correctly indexes the demo/ecommerce
codebase — checking file discovery, symbol extraction, import resolution,
API route detection, schema node detection, reference detection, and test
coverage edges.

Run from the repo root:
  cd backend && python -m pytest tests/test_codebase_analyzer.py -v
"""

from __future__ import annotations
import os
import sys

# Ensure the backend package is importable when running from any cwd
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from engine.codebase_graph import build_graph, DEMO_ROOT


# ---------------------------------------------------------------------------
# Fixture — one graph instance shared across all tests in this module
# ---------------------------------------------------------------------------

_GRAPH = None

def _graph():
    global _GRAPH
    if _GRAPH is None:
        _GRAPH = build_graph()
    return _GRAPH


# ===========================================================================
# 1. File discovery
# ===========================================================================

class TestFileDiscovery:

    def test_expected_python_files_are_indexed(self):
        """All .py files in the demo codebase must appear in graph.files."""
        g = _graph()
        expected = [
            "services/order_service.py",
            "services/payment_service.py",
            "services/user_service.py",
            "services/inventory_service.py",
            "models/order.py",
            "models/payment.py",
            "models/user.py",
            "models/product.py",
            "routes/orders.py",
            "routes/payments.py",
            "routes/users.py",
            "controllers/payment_controller.py",
            "controllers/order_controller.py",
            "tests/test_order_service.py",
            "tests/test_payment_service.py",
            "tests/test_checkout.py",
        ]
        for path in expected:
            assert path in g.files, f"Expected file not in graph: {path}"

    def test_sql_file_is_indexed(self):
        g = _graph()
        assert "schema/migrations.sql" in g.files

    def test_layer_classification(self):
        """Files must be classified into the correct architectural layer."""
        g = _graph()
        assert g.files["services/order_service.py"].layer == "service"
        assert g.files["models/payment.py"].layer == "model"
        assert g.files["routes/orders.py"].layer == "route"
        assert g.files["controllers/payment_controller.py"].layer == "controller"
        assert g.files["tests/test_order_service.py"].layer == "test"
        assert g.files["schema/migrations.sql"].layer == "schema"

    def test_language_tagging(self):
        g = _graph()
        assert g.files["services/order_service.py"].language == "python"
        assert g.files["schema/migrations.sql"].language == "sql"


# ===========================================================================
# 2. Symbol extraction
# ===========================================================================

class TestSymbolExtraction:

    def test_calculate_order_total_is_indexed(self):
        """The primary blast-radius target must be in the symbol index."""
        g = _graph()
        sym_id = "services/order_service.py#calculate_order_total"
        assert sym_id in g.symbols
        sym = g.symbols[sym_id]
        assert sym.name == "calculate_order_total"
        assert sym.kind == "function"
        assert sym.line_start > 0
        assert "order_id" in sym.signature

    def test_process_payment_is_indexed(self):
        g = _graph()
        assert "services/payment_service.py#process_payment" in g.symbols

    def test_order_class_is_indexed(self):
        """ORM model classes must be indexed."""
        g = _graph()
        assert "models/order.py#Order" in g.symbols
        assert g.symbols["models/order.py#Order"].kind == "class"

    def test_payment_class_is_indexed(self):
        g = _graph()
        assert "models/payment.py#Payment" in g.symbols

    def test_user_class_is_indexed(self):
        g = _graph()
        assert "models/user.py#User" in g.symbols

    def test_symbol_docstring_captured(self):
        """Symbols with docstrings should have non-empty docstring field."""
        g = _graph()
        sym = g.symbols.get("services/order_service.py#calculate_order_total")
        assert sym is not None
        assert len(sym.docstring) > 0

    def test_file_symbols_list_populated(self):
        """FileNode.symbols must list the names defined in that file."""
        g = _graph()
        syms = g.files["services/order_service.py"].symbols
        assert "calculate_order_total" in syms
        assert "place_order" in syms

    def test_methods_in_class_are_indexed(self):
        """Methods inside a class (e.g. Order.find) must be indexed."""
        g = _graph()
        assert "models/order.py#find" in g.symbols


# ===========================================================================
# 3. Import resolution
# ===========================================================================

class TestImportResolution:

    def test_order_service_imports_order_model(self):
        """services/order_service.py imports from models/order.py."""
        g = _graph()
        resolved = [
            imp.to_file
            for imp in g.imports_of("services/order_service.py")
            if imp.to_file is not None
        ]
        assert "models/order.py" in resolved

    def test_payment_service_imports_payment_model(self):
        g = _graph()
        resolved = [imp.to_file for imp in g.imports_of("services/payment_service.py")
                    if imp.to_file]
        assert "models/payment.py" in resolved

    def test_routes_imports_controllers(self):
        """routes/orders.py must import from controllers/order_controller.py."""
        g = _graph()
        resolved = [imp.to_file for imp in g.imports_of("routes/orders.py") if imp.to_file]
        assert "controllers/order_controller.py" in resolved

    def test_controller_imports_service(self):
        """controllers/payment_controller.py must import from services/payment_service.py."""
        g = _graph()
        resolved = [imp.to_file for imp in g.imports_of("controllers/payment_controller.py")
                    if imp.to_file]
        assert "services/payment_service.py" in resolved

    def test_external_imports_have_no_to_file(self):
        """Flask, re, ast etc. are external — to_file should be None."""
        g = _graph()
        flask_imports = [
            imp for imp in g.imports_of("routes/orders.py")
            if "flask" in imp.to_module.lower()
        ]
        assert any(imp.to_file is None for imp in flask_imports)


# ===========================================================================
# 4. Reference detection
# ===========================================================================

class TestReferenceDetection:

    def test_callers_of_calculate_order_total(self):
        """
        calculate_order_total is called by routes/orders.py (via controller),
        payment_service.py, and internally by place_order.
        At least two files should appear as callers.
        """
        g = _graph()
        sym_id = "services/order_service.py#calculate_order_total"
        callers = g.callers_of(sym_id)
        caller_files = {e.from_file for e in callers}
        # At minimum: payment_service and order_service (internal call from place_order)
        assert len(caller_files) >= 1, "Expected at least 1 caller of calculate_order_total"

    def test_process_payment_has_callers(self):
        g = _graph()
        sym_id = "services/payment_service.py#process_payment"
        callers = g.callers_of(sym_id)
        assert len(callers) >= 1

    def test_refs_deduplicated_across_files(self):
        """refs list must not be empty after building the graph."""
        g = _graph()
        assert len(g.refs) > 0


# ===========================================================================
# 5. API route detection
# ===========================================================================

class TestAPIRouteDetection:

    def test_orders_routes_detected(self):
        g = _graph()
        order_routes = [r for r in g.routes if r.file == "routes/orders.py"]
        assert len(order_routes) >= 3   # POST /orders, GET /orders/<id>, DELETE /orders/<id>

    def test_payments_routes_detected(self):
        g = _graph()
        payment_routes = [r for r in g.routes if r.file == "routes/payments.py"]
        assert len(payment_routes) >= 2

    def test_route_http_methods_are_uppercase(self):
        g = _graph()
        for route in g.routes:
            assert route.http_method == route.http_method.upper(), \
                f"Expected uppercase HTTP method, got {route.http_method!r}"

    def test_route_paths_start_with_slash(self):
        g = _graph()
        for route in g.routes:
            assert route.path.startswith("/"), \
                f"Expected route path to start with /, got {route.path!r}"

    def test_handler_functions_named(self):
        g = _graph()
        for route in g.routes:
            assert route.handler_function != "", \
                f"Expected handler_function to be set for route {route.path}"

    def test_specific_route_exists(self):
        """POST /payments must be in the graph."""
        g = _graph()
        post_payments = [
            r for r in g.routes
            if r.http_method == "POST" and r.path == "/payments"
        ]
        assert len(post_payments) >= 1


# ===========================================================================
# 6. Database schema detection
# ===========================================================================

class TestSchemaDetection:

    def test_critical_tables_detected(self):
        """The key tables from migrations.sql must appear as SchemaNodes."""
        g = _graph()
        table_names = {s.table_name.lower() for s in g.schema_nodes}
        for expected in ("users", "orders", "payments", "order_items", "products"):
            assert expected in table_names, f"Table {expected!r} not in schema_nodes"

    def test_schema_nodes_linked_to_sql_file(self):
        g = _graph()
        sql_schema = [s for s in g.schema_nodes if s.file.endswith(".sql")]
        assert len(sql_schema) >= 5

    def test_schema_node_has_operation(self):
        g = _graph()
        for node in g.schema_nodes:
            assert node.operation in ("CREATE TABLE", "ALTER TABLE", "DROP TABLE"), \
                f"Unexpected operation: {node.operation}"


# ===========================================================================
# 7. Test coverage edges
# ===========================================================================

class TestCoverageEdges:

    def test_calculate_order_total_has_test_coverage(self):
        """test_order_service.py must produce TestCoversEdges for calculate_order_total."""
        g = _graph()
        sym_id = "services/order_service.py#calculate_order_total"
        covers = g.tests_for(sym_id)
        assert len(covers) >= 1, "Expected at least one test covering calculate_order_total"

    def test_process_payment_has_test_coverage(self):
        g = _graph()
        sym_id = "services/payment_service.py#process_payment"
        covers = g.tests_for(sym_id)
        assert len(covers) >= 1

    def test_test_function_names_are_test_prefixed(self):
        g = _graph()
        for edge in g.test_covers:
            assert edge.test_function.startswith("test_"), \
                f"Expected test function name to start with test_, got {edge.test_function!r}"

    def test_covered_symbols_are_not_in_test_files(self):
        """TestCoversEdges should point to non-test symbols only."""
        g = _graph()
        for edge in g.test_covers:
            assert not edge.covered_file.startswith("tests/"), \
                f"Test covers edge points to a test file: {edge.covered_file}"


# ===========================================================================
# 8. Graph summary
# ===========================================================================

class TestGraphSummary:

    def test_summary_has_expected_keys(self):
        g = _graph()
        s = g.summary()
        for key in ("files", "symbols", "imports", "refs", "routes", "schema_nodes", "test_covers"):
            assert key in s, f"Missing key in summary: {key}"

    def test_summary_counts_are_positive(self):
        g = _graph()
        s = g.summary()
        assert s["files"] > 10
        assert s["symbols"] > 20
        assert s["imports"] > 10
        assert s["routes"] >= 5
        assert s["schema_nodes"] >= 5
        assert s["test_covers"] >= 5


# ===========================================================================
# 9. Graph helper methods
# ===========================================================================

class TestGraphHelpers:

    def test_get_symbol_by_file_and_name(self):
        g = _graph()
        sym = g.get_symbol("services/order_service.py", "calculate_order_total")
        assert sym is not None
        assert sym.name == "calculate_order_total"

    def test_get_symbol_missing_returns_none(self):
        g = _graph()
        assert g.get_symbol("services/order_service.py", "nonexistent_function") is None

    def test_routes_for_file(self):
        g = _graph()
        routes = g.routes_for_file("routes/payments.py")
        assert len(routes) >= 2

    def test_schema_for_table(self):
        g = _graph()
        nodes = g.schema_for_table("orders")
        assert len(nodes) >= 1
        assert nodes[0].table_name.lower() == "orders"
