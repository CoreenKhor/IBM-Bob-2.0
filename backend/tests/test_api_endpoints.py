"""
Endpoint Integration Tests — Flask test client

Tests every route in the API layer using Flask's built-in test client.
These tests exercise the full HTTP stack (routing, validation, response
shape) without starting a real server.

Covered endpoints:
  GET  /api/health
  GET  /api/tree
  GET  /api/analyze/schema
  POST /api/analyze           ← primary focus
  GET  /api/symbols
  GET  /api/symbols/all
  GET  /api/symbols/layers
  GET  /api/graph
  GET  /api/graph/file

Run from repo root:
  cd backend && python -m pytest tests/test_api_endpoints.py -v
"""

from __future__ import annotations
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from app import create_app


# ---------------------------------------------------------------------------
# Shared test client fixture
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def client():
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


# ============================================================================
# Health check
# ============================================================================

class TestHealth:
    def test_health_returns_200(self, client):
        res = client.get("/api/health")
        assert res.status_code == 200

    def test_health_body(self, client):
        data = res_json(client.get("/api/health"))
        assert data["status"] == "ok"
        assert data["service"] == "blast-radius-analyzer"


# ============================================================================
# GET /api/tree
# ============================================================================

class TestTree:
    def test_tree_returns_200(self, client):
        res = client.get("/api/tree")
        assert res.status_code == 200

    def test_tree_has_root_key(self, client):
        data = res_json(client.get("/api/tree"))
        assert "root" in data
        assert data["root"] == "demo/ecommerce"

    def test_tree_files_is_list(self, client):
        data = res_json(client.get("/api/tree"))
        assert isinstance(data["files"], list)
        assert len(data["files"]) > 0

    def test_tree_entries_have_path_and_type(self, client):
        data = res_json(client.get("/api/tree"))
        for entry in data["files"][:5]:
            assert "path" in entry
            assert "type" in entry
            assert entry["type"] in ("file", "dir")


# ============================================================================
# GET /api/analyze/schema
# ============================================================================

class TestAnalyzeSchema:
    def test_schema_returns_200(self, client):
        assert client.get("/api/analyze/schema").status_code == 200

    def test_schema_has_ok_true(self, client):
        data = res_json(client.get("/api/analyze/schema"))
        assert data["ok"] is True

    def test_schema_lists_change_types(self, client):
        data = res_json(client.get("/api/analyze/schema"))
        assert "valid_change_types" in data
        assert "general" in data["valid_change_types"]
        assert "signature_change" in data["valid_change_types"]

    def test_schema_has_required_fields(self, client):
        data = res_json(client.get("/api/analyze/schema"))
        assert "schema" in data
        assert data["schema"]["required"] == ["target_file", "target_symbol"]


# ============================================================================
# POST /api/analyze — validation
# ============================================================================

class TestAnalyzeValidation:

    def test_empty_body_returns_400(self, client):
        res = client.post("/api/analyze", json={})
        assert res.status_code == 400
        data = res_json(res)
        assert data["ok"] is False
        assert "target_file" in data["error"]

    def test_missing_target_symbol_returns_400(self, client):
        res = client.post("/api/analyze", json={"target_file": "services/order_service.py"})
        assert res.status_code == 400
        data = res_json(res)
        assert "target_symbol" in data["error"]

    def test_missing_target_file_returns_400(self, client):
        res = client.post("/api/analyze", json={"target_symbol": "process_payment"})
        assert res.status_code == 400

    def test_invalid_change_type_returns_400(self, client):
        res = client.post("/api/analyze", json={
            "target_file":   "services/payment_service.py",
            "target_symbol": "process_payment",
            "change_type":   "invalid_type",
        })
        assert res.status_code == 400
        data = res_json(res)
        assert "change_type" in data["error"]

    def test_path_traversal_rejected(self, client):
        res = client.post("/api/analyze", json={
            "target_file":   "../../etc/passwd",
            "target_symbol": "anything",
        })
        assert res.status_code == 400
        data = res_json(res)
        assert data["ok"] is False

    def test_absolute_path_rejected(self, client):
        res = client.post("/api/analyze", json={
            "target_file":   "/etc/passwd",
            "target_symbol": "anything",
        })
        assert res.status_code == 400

    def test_unknown_file_returns_422_with_hint(self, client):
        res = client.post("/api/analyze", json={
            "target_file":   "services/does_not_exist.py",
            "target_symbol": "foo",
        })
        assert res.status_code == 422
        data = res_json(res)
        assert data["ok"] is False
        assert "hint" in data

    def test_unknown_symbol_returns_422_with_available(self, client):
        res = client.post("/api/analyze", json={
            "target_file":   "services/order_service.py",
            "target_symbol": "nonexistent_function",
        })
        assert res.status_code == 422
        data = res_json(res)
        assert data["ok"] is False
        assert "available_symbols" in data
        assert isinstance(data["available_symbols"], list)

    def test_description_too_long_returns_400(self, client):
        res = client.post("/api/analyze", json={
            "target_file":        "services/payment_service.py",
            "target_symbol":      "process_payment",
            "change_description": "x" * 1001,
        })
        assert res.status_code == 400

    def test_wrong_content_type_returns_415(self, client):
        res = client.post(
            "/api/analyze",
            data='{"target_file":"x","target_symbol":"y"}',
            content_type="text/plain",
        )
        assert res.status_code == 415
        data = res_json(res)
        assert data["ok"] is False

    def test_valid_change_types_accepted(self, client):
        """Each valid change_type should not cause a 400."""
        valid_types = [
            "general", "signature_change", "schema_change",
            "api_change", "refactor", "deletion", "new_feature",
        ]
        for ct in valid_types:
            res = client.post("/api/analyze", json={
                "target_file":   "services/payment_service.py",
                "target_symbol": "process_payment",
                "change_type":   ct,
            })
            # May be 200 or 422 (symbol not found) but not 400 (validation error)
            assert res.status_code != 400, \
                f"change_type={ct!r} should not return 400, got {res.status_code}"


# ============================================================================
# POST /api/analyze — PaymentService scenario (primary task scenario)
# ============================================================================

class TestAnalyzePaymentService:

    @pytest.fixture(scope="class")
    def report(self, client):
        res = client.post("/api/analyze", json={
            "target_file":        "services/payment_service.py",
            "target_symbol":      "process_payment",
            "change_description": "Add support for a new payment provider",
            "change_type":        "general",
        })
        assert res.status_code == 200
        return res_json(res)

    def test_response_ok_is_true(self, report):
        assert report["ok"] is True

    def test_response_has_report_key(self, report):
        assert "report" in report

    # ── meta ────────────────────────────────────────────────────────────────

    def test_meta_analyzed_target(self, report):
        meta = report["report"]["meta"]
        assert meta["analyzed_target"] == "services/payment_service.py#process_payment"

    def test_meta_risk_level_is_valid(self, report):
        level = report["report"]["meta"]["risk_level"]
        assert level in ("CRITICAL", "HIGH", "MEDIUM", "LOW")

    def test_meta_counts_are_non_negative(self, report):
        meta = report["report"]["meta"]
        assert meta["total_impacted_files"] >= 0
        assert meta["direct_callers"] >= 0

    # ── impact_categories ────────────────────────────────────────────────────

    def test_impact_categories_present(self, report):
        cats = report["report"]["impact_categories"]
        for key in ("directly_affected", "indirectly_affected", "related_tests",
                    "related_apis", "related_db", "risk_areas", "testing_suggestions"):
            assert key in cats, f"Missing category: {key}"

    def test_directly_affected_includes_payment_controller(self, report):
        files = {c["file"] for c in report["report"]["impact_categories"]["directly_affected"]}
        assert "controllers/payment_controller.py" in files

    def test_indirectly_affected_includes_payment_routes(self, report):
        all_files = (
            {c["file"] for c in report["report"]["impact_categories"]["directly_affected"]} |
            {c["file"] for c in report["report"]["impact_categories"]["indirectly_affected"]}
        )
        assert any("payments" in f for f in all_files), \
            f"Expected payments route in affected files. Got: {all_files}"

    def test_related_tests_have_required_fields(self, report):
        tests = report["report"]["impact_categories"]["related_tests"]
        assert len(tests) >= 1
        for t in tests:
            assert "file"      in t
            assert "function"  in t
            assert "test_type" in t
            assert "command"   in t
            assert "reason"    in t

    def test_related_tests_include_payment_tests(self, report):
        test_files = {t["file"] for t in report["report"]["impact_categories"]["related_tests"]}
        assert any("payment" in f for f in test_files)

    def test_related_apis_include_post_payments(self, report):
        routes = {
            f"{a['http_method']} {a['path']}"
            for a in report["report"]["impact_categories"]["related_apis"]
        }
        assert "POST /payments" in routes, f"Missing POST /payments in {routes}"

    def test_related_apis_have_required_fields(self, report):
        for api in report["report"]["impact_categories"]["related_apis"]:
            assert "http_method" in api
            assert "path"        in api
            assert "file"        in api
            assert "handler"     in api
            assert "reason"      in api

    def test_related_db_includes_payments_table(self, report):
        tables = {d["table_name"].lower() for d in report["report"]["impact_categories"]["related_db"]}
        assert "payments" in tables

    def test_related_db_have_required_fields(self, report):
        for db in report["report"]["impact_categories"]["related_db"]:
            assert "table_name" in db
            assert "operation"  in db
            assert "file"       in db
            assert "reason"     in db

    def test_risk_areas_have_severity(self, report):
        for ra in report["report"]["impact_categories"]["risk_areas"]:
            assert ra["severity"] in ("critical", "high", "medium", "low")

    def test_testing_suggestions_have_priority(self, report):
        sug = report["report"]["impact_categories"]["testing_suggestions"]
        assert len(sug) >= 2
        for s in sug:
            assert s["priority"] in ("must", "should", "consider")

    def test_mermaid_diagram_present(self, report):
        mermaid = report["report"]["mermaid_diagram"]
        assert "graph TD" in mermaid
        assert "process_payment" in mermaid

    def test_validation_plan_has_test_commands(self, report):
        vp = report["report"]["validation_plan"]
        assert isinstance(vp["test_commands"], list)
        assert len(vp["test_commands"]) >= 1

    def test_mitigation_deployment_strategy(self, report):
        strat = report["report"]["mitigation"]["deployment_strategy"]
        assert strat in ("canary", "standard")


# ============================================================================
# POST /api/analyze — OrderService scenario (signature change)
# ============================================================================

class TestAnalyzeOrderService:

    @pytest.fixture(scope="class")
    def report(self, client):
        res = client.post("/api/analyze", json={
            "target_file":        "services/order_service.py",
            "target_symbol":      "calculate_order_total",
            "change_description": "Add a tax_rate parameter",
            "change_type":        "signature_change",
        })
        assert res.status_code == 200
        return res_json(res)

    def test_target_correct(self, report):
        assert report["report"]["meta"]["analyzed_target"] == \
            "services/order_service.py#calculate_order_total"

    def test_risk_is_high_or_critical(self, report):
        assert report["report"]["meta"]["risk_level"] in ("HIGH", "CRITICAL")

    def test_signature_change_risk_area(self, report):
        categories = {
            ra["category"]
            for ra in report["report"]["impact_categories"]["risk_areas"]
        }
        # signature_change signal → "semantic" risk category
        assert "semantic" in categories

    def test_test_commands_are_runnable_pytest(self, report):
        for cmd in report["report"]["validation_plan"]["test_commands"]:
            assert cmd.startswith("pytest"), f"Expected pytest command, got: {cmd}"


# ============================================================================
# GET /api/symbols
# ============================================================================

class TestSymbolsEndpoint:

    def test_symbols_requires_path(self, client):
        res = client.get("/api/symbols")
        assert res.status_code == 400

    def test_symbols_unknown_file_returns_404(self, client):
        res = client.get("/api/symbols?path=services/does_not_exist.py")
        assert res.status_code == 404
        data = res_json(res)
        assert data["ok"] is False
        assert "available_files" in data

    def test_symbols_payment_service(self, client):
        res = client.get("/api/symbols?path=services/payment_service.py")
        assert res.status_code == 200
        data = res_json(res)
        assert data["ok"] is True
        assert data["file"] == "services/payment_service.py"
        names = [s["name"] for s in data["symbols"]]
        assert "process_payment" in names
        assert "refund_payment"  in names

    def test_symbols_have_required_fields(self, client):
        data = res_json(client.get("/api/symbols?path=services/order_service.py"))
        for sym in data["symbols"]:
            assert "name"       in sym
            assert "kind"       in sym
            assert "signature"  in sym
            assert "line_start" in sym

    def test_symbols_sorted_by_line(self, client):
        data = res_json(client.get("/api/symbols?path=services/order_service.py"))
        lines = [s["line_start"] for s in data["symbols"]]
        assert lines == sorted(lines)

    def test_symbols_kind_filter(self, client):
        data = res_json(client.get("/api/symbols?path=models/order.py&kind=class"))
        for sym in data["symbols"]:
            assert sym["kind"] == "class"

    def test_symbols_traversal_rejected(self, client):
        res = client.get("/api/symbols?path=../../etc/passwd")
        assert res.status_code == 400

    def test_symbols_all_endpoint(self, client):
        data = res_json(client.get("/api/symbols/all"))
        assert data["ok"] is True
        assert data["count"] > 50
        assert isinstance(data["symbols"], list)

    def test_symbols_all_layer_filter(self, client):
        data = res_json(client.get("/api/symbols/all?layer=service"))
        for sym in data["symbols"]:
            assert sym["layer"] == "service"

    def test_symbols_layers_endpoint(self, client):
        data = res_json(client.get("/api/symbols/layers"))
        assert data["ok"] is True
        for layer in ("service", "model", "route", "controller", "test"):
            assert layer in data["layers"], f"Missing layer: {layer}"


# ============================================================================
# GET /api/graph
# ============================================================================

class TestGraphEndpoint:

    def test_graph_returns_200(self, client):
        assert client.get("/api/graph").status_code == 200

    def test_graph_summary_keys(self, client):
        data = res_json(client.get("/api/graph"))
        assert "summary" in data
        for key in ("files", "symbols", "imports", "routes", "schema_nodes"):
            assert key in data["summary"]

    def test_graph_has_routes(self, client):
        data = res_json(client.get("/api/graph"))
        assert len(data["routes"]) >= 5

    def test_graph_file_detail(self, client):
        res = client.get("/api/graph/file?path=services/payment_service.py")
        assert res.status_code == 200
        data = res_json(res)
        assert "defined_symbols" in data
        sym_names = [s["name"] for s in data["defined_symbols"]]
        assert "process_payment" in sym_names

    def test_graph_file_missing_returns_404(self, client):
        res = client.get("/api/graph/file?path=nonexistent.py")
        assert res.status_code == 404

    def test_graph_file_missing_path_returns_400(self, client):
        res = client.get("/api/graph/file")
        assert res.status_code == 400


# ============================================================================
# CORS headers
# ============================================================================

class TestCORS:

    def test_analyze_cors_header_present(self, client):
        """The frontend dev server (localhost:5173) must be able to call the API."""
        res = client.options(
            "/api/analyze",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "POST",
            },
        )
        # Flask-CORS should add Access-Control-Allow-Origin
        origin = res.headers.get("Access-Control-Allow-Origin", "")
        assert origin in ("*", "http://localhost:5173"), \
            f"Expected CORS header, got: {origin!r}"

    def test_symbols_cors_header_present(self, client):
        res = client.get(
            "/api/symbols?path=services/order_service.py",
            headers={"Origin": "http://localhost:5173"},
        )
        origin = res.headers.get("Access-Control-Allow-Origin", "")
        assert origin in ("*", "http://localhost:5173")


# ============================================================================
# Response envelope consistency
# ============================================================================

class TestResponseEnvelope:
    """All success responses should have ok=True; all errors ok=False."""

    def test_successful_analyze_has_ok_true(self, client):
        res = client.post("/api/analyze", json={
            "target_file":   "services/payment_service.py",
            "target_symbol": "process_payment",
        })
        assert res.status_code == 200
        assert res_json(res)["ok"] is True

    def test_error_analyze_has_ok_false(self, client):
        res = client.post("/api/analyze", json={})
        assert res_json(res)["ok"] is False

    def test_symbols_success_has_ok_true(self, client):
        res = client.get("/api/symbols?path=services/order_service.py")
        assert res_json(res)["ok"] is True

    def test_symbols_error_has_ok_false(self, client):
        res = client.get("/api/symbols?path=nonexistent.py")
        assert res_json(res)["ok"] is False

    def test_analyze_schema_has_ok_true(self, client):
        res = client.get("/api/analyze/schema")
        assert res_json(res)["ok"] is True


# ============================================================================
# Helpers
# ============================================================================

def res_json(res) -> dict:
    """Decode a Flask test response as JSON, with a clear assertion on failure."""
    try:
        return json.loads(res.data)
    except json.JSONDecodeError:
        raise AssertionError(
            f"Response is not valid JSON (status {res.status_code}):\n{res.data[:500]}"
        )
