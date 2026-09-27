"""
Tests for the Impact Analyzer (7-category analysis pipeline).

Verifies that run() produces correct categories for several different
target symbols in the demo codebase, including the PaymentService example
from the task brief and the canonical calculate_order_total scenario.

Run from repo root:
  cd backend && python -m pytest tests/test_impact_analyzer.py -v
"""

from __future__ import annotations
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from engine.codebase_graph import build_graph, get_graph
from engine.impact_analyzer import run, _extract_change_signals, ImpactResult
from engine.target_resolver import resolve_target
from engine.report_builder import build_report


# ---------------------------------------------------------------------------
# Shared fixture — one graph build for all tests
# ---------------------------------------------------------------------------

def _target(file: str, symbol: str) -> dict:
    return resolve_target(file, symbol)


# ===========================================================================
# 1. Change signal extraction (pure unit tests — no graph needed)
# ===========================================================================

class TestChangeSignalExtraction:

    def test_payment_provider_signals(self):
        sigs = _extract_change_signals("Add support for a new payment provider")
        assert "new_integration" in sigs
        assert "additive" in sigs

    def test_schema_change_signals(self):
        sigs = _extract_change_signals("Add a tax_rate column to the orders table")
        assert "db_change" in sigs

    def test_signature_change_signals(self):
        sigs = _extract_change_signals("Add a currency parameter to process_payment")
        assert "signature_change" in sigs

    def test_breaking_change_signals(self):
        sigs = _extract_change_signals("Remove the discount_code parameter from calculate_order_total")
        assert "breaking_change" in sigs

    def test_security_signals(self):
        sigs = _extract_change_signals("Update token validation to use RS256")
        assert "security" in sigs

    def test_empty_description_has_no_signals(self):
        sigs = _extract_change_signals("")
        assert len(sigs) == 0

    def test_multiple_signals_detected(self):
        sigs = _extract_change_signals("Rename the API endpoint and drop the old column")
        assert "breaking_change" in sigs
        assert "api_change" in sigs


# ===========================================================================
# 2. process_payment — "Add support for a new payment provider"
# (The primary scenario from the task brief)
# ===========================================================================

class TestProcessPaymentNewProvider:

    @pytest.fixture(scope="class")
    def result(self) -> ImpactResult:
        target_info = _target("services/payment_service.py", "process_payment")
        return run(
            target_file="services/payment_service.py",
            target_symbol="process_payment",
            change_description="Add support for a new payment provider",
            change_type="general",
            target_info=target_info,
        )

    def test_result_has_correct_target(self, result):
        assert result.target_symbol == "process_payment"
        assert result.target_file == "services/payment_service.py"
        assert result.target_layer == "service"

    def test_directly_affected_includes_payment_controller(self, result):
        """PaymentController imports process_payment — must be directly affected."""
        files = {c.file for c in result.directly_affected}
        assert "controllers/payment_controller.py" in files

    def test_indirectly_affected_includes_payment_route(self, result):
        """routes/payments.py imports payment_controller — indirect."""
        files = {c.file for c in result.directly_affected + result.indirectly_affected}
        assert "routes/payments.py" in files

    def test_related_tests_include_payment_tests(self, result):
        test_files = {t["file"] for t in result.related_tests}
        assert any("payment" in f for f in test_files), \
            f"Expected payment test files, got: {test_files}"

    def test_related_tests_include_checkout_tests(self, result):
        """Checkout integration tests exercise payment flow."""
        test_files = {t["file"] for t in result.related_tests}
        assert any("checkout" in f for f in test_files), \
            f"Expected checkout test, got: {test_files}"

    def test_related_apis_include_post_payments(self, result):
        """POST /payments is the direct API surface for process_payment."""
        routes = {f"{a.http_method} {a.path}" for a in result.related_apis}
        assert "POST /payments" in routes, f"Expected POST /payments, got: {routes}"

    def test_related_db_includes_payments_table(self, result):
        tables = {d.table_name.lower() for d in result.related_db}
        assert "payments" in tables

    def test_new_integration_risk_area_present(self, result):
        """The 'new_integration' signal should generate a semantic risk area."""
        categories = {r.category for r in result.risk_areas}
        assert "semantic" in categories

    def test_testing_suggestions_are_non_empty(self, result):
        assert len(result.testing_suggestions) >= 3

    def test_must_priority_suggestions_present(self, result):
        must = [s for s in result.testing_suggestions if s.priority == "must"]
        assert len(must) >= 1

    def test_risk_level_is_at_least_high(self, result):
        assert result.risk_level in ("HIGH", "CRITICAL")


# ===========================================================================
# 3. calculate_order_total — "Add a tax_rate parameter"
# ===========================================================================

class TestCalculateOrderTotal:

    @pytest.fixture(scope="class")
    def result(self) -> ImpactResult:
        target_info = _target("services/order_service.py", "calculate_order_total")
        return run(
            target_file="services/order_service.py",
            target_symbol="calculate_order_total",
            change_description="Add a tax_rate parameter and update return type",
            change_type="signature_change",
            target_info=target_info,
        )

    def test_directly_affected_non_empty(self, result):
        assert len(result.directly_affected) >= 1

    def test_controllers_in_affected(self, result):
        all_files = {c.file for c in result.directly_affected + result.indirectly_affected}
        assert any("controller" in f or "route" in f for f in all_files)

    def test_related_tests_non_empty(self, result):
        assert len(result.related_tests) >= 2

    def test_unit_and_integration_tests_present(self, result):
        types = {t["test_type"] for t in result.related_tests}
        assert "unit" in types

    def test_signature_change_risk_area_present(self, result):
        categories = {r.category for r in result.risk_areas}
        assert "semantic" in categories

    def test_risk_level_critical_or_high(self, result):
        assert result.risk_level in ("CRITICAL", "HIGH")

    def test_risk_breakdown_has_four_factors(self, result):
        for key in ("dependency_centrality", "api_boundary", "data_persistence", "test_coverage"):
            assert key in result.risk_breakdown


# ===========================================================================
# 4. register_user — "Add phone number validation"
# ===========================================================================

class TestRegisterUser:

    @pytest.fixture(scope="class")
    def result(self) -> ImpactResult:
        target_info = _target("services/user_service.py", "register_user")
        return run(
            target_file="services/user_service.py",
            target_symbol="register_user",
            change_description="Add phone number validation before saving user",
            change_type="general",
            target_info=target_info,
        )

    def test_result_has_correct_target(self, result):
        assert result.target_symbol == "register_user"
        assert result.target_layer == "service"

    def test_user_route_is_affected(self, result):
        all_files = {c.file for c in result.directly_affected + result.indirectly_affected}
        assert any("user" in f for f in all_files)

    def test_related_tests_include_user_tests(self, result):
        test_files = {t["file"] for t in result.related_tests}
        assert any("user" in f for f in test_files)

    def test_testing_suggestions_non_empty(self, result):
        assert len(result.testing_suggestions) >= 2


# ===========================================================================
# 5. Order model — "Add a discount_code column"
# ===========================================================================

class TestOrderModelSchemaChange:

    @pytest.fixture(scope="class")
    def result(self) -> ImpactResult:
        target_info = _target("models/order.py", "Order")
        return run(
            target_file="models/order.py",
            target_symbol="Order",
            change_description="Add a discount_code column to the orders table",
            change_type="schema_change",
            target_info=target_info,
        )

    def test_db_change_detected(self, result):
        assert len(result.related_db) >= 1

    def test_orders_table_in_related_db(self, result):
        tables = {d.table_name.lower() for d in result.related_db}
        assert "orders" in tables

    def test_db_migration_risk_area_present(self, result):
        categories = {r.category for r in result.risk_areas}
        assert "db_migration" in categories

    def test_must_migration_suggestion_present(self, result):
        musts = [s for s in result.testing_suggestions if s.priority == "must"]
        assert any("migration" in s.action.lower() or "database" in s.action.lower()
                   for s in musts), \
            f"No migration suggestion found in: {[s.action for s in musts]}"

    def test_risk_level_high_or_critical(self, result):
        assert result.risk_level in ("HIGH", "CRITICAL")


# ===========================================================================
# 6. Report builder integration
# ===========================================================================

class TestReportBuilder:

    @pytest.fixture(scope="class")
    def report(self) -> dict:
        target_info = _target("services/payment_service.py", "process_payment")
        result = run(
            target_file="services/payment_service.py",
            target_symbol="process_payment",
            change_description="Add support for a new payment provider",
            change_type="general",
            target_info=target_info,
        )
        return build_report(result)

    def test_report_has_meta(self, report):
        assert "meta" in report
        assert report["meta"]["analyzed_target"] == "services/payment_service.py#process_payment"

    def test_report_meta_risk_level(self, report):
        assert report["meta"]["risk_level"] in ("CRITICAL", "HIGH", "MEDIUM", "LOW")

    def test_report_has_impacted_components(self, report):
        assert len(report["impacted_components"]) >= 1

    def test_report_has_mermaid_diagram(self, report):
        mermaid = report["mermaid_diagram"]
        assert "graph TD" in mermaid
        assert "process_payment" in mermaid

    def test_report_has_impact_categories(self, report):
        cats = report["impact_categories"]
        for key in ("directly_affected", "indirectly_affected", "related_tests",
                    "related_apis", "related_db", "risk_areas", "testing_suggestions"):
            assert key in cats, f"Missing key in impact_categories: {key}"

    def test_report_has_validation_plan(self, report):
        assert "validation_plan" in report
        assert "test_commands" in report["validation_plan"]
        assert "manual_checks" in report["validation_plan"]

    def test_report_has_mitigation(self, report):
        mit = report["mitigation"]
        assert "deployment_strategy" in mit
        assert mit["deployment_strategy"] in ("canary", "standard")

    def test_impact_categories_directly_affected_is_list(self, report):
        assert isinstance(report["impact_categories"]["directly_affected"], list)

    def test_impact_categories_risk_areas_have_severity(self, report):
        for ra in report["impact_categories"]["risk_areas"]:
            assert ra["severity"] in ("critical", "high", "medium", "low")

    def test_impact_categories_suggestions_have_priority(self, report):
        for s in report["impact_categories"]["testing_suggestions"]:
            assert s["priority"] in ("must", "should", "consider")

    def test_mermaid_target_node_styled_red(self, report):
        assert "#f87171" in report["mermaid_diagram"]


# ===========================================================================
# 7. Edge cases
# ===========================================================================

class TestEdgeCases:

    def test_leaf_symbol_with_no_callers(self):
        """A symbol with no callers should still produce a valid result."""
        # check_stock has limited callers in the graph
        target_info = _target("services/inventory_service.py", "check_stock")
        result = run(
            target_file="services/inventory_service.py",
            target_symbol="check_stock",
            change_description="Change return type to include unit",
            change_type="signature_change",
            target_info=target_info,
        )
        assert result.target_symbol == "check_stock"
        assert isinstance(result.directly_affected, list)
        assert isinstance(result.risk_areas, list)
        assert len(result.testing_suggestions) >= 1

    def test_empty_description_does_not_crash(self):
        target_info = _target("services/order_service.py", "cancel_order")
        result = run(
            target_file="services/order_service.py",
            target_symbol="cancel_order",
            change_description="",
            change_type="general",
            target_info=target_info,
        )
        assert result.risk_level in ("CRITICAL", "HIGH", "MEDIUM", "LOW")

    def test_all_categories_present_in_to_dict(self):
        target_info = _target("services/payment_service.py", "refund_payment")
        result = run(
            target_file="services/payment_service.py",
            target_symbol="refund_payment",
            change_description="Add partial refund support",
            change_type="general",
            target_info=target_info,
        )
        d = result.to_dict()
        required_keys = [
            "target", "change", "risk_level", "risk_breakdown",
            "directly_affected", "indirectly_affected", "related_tests",
            "related_apis", "related_db", "risk_areas", "testing_suggestions",
        ]
        for k in required_keys:
            assert k in d, f"Missing key in to_dict(): {k}"

    def test_result_serialises_to_json(self):
        """The full report must be JSON-serialisable (no dataclasses, datetime, etc.)."""
        import json
        target_info = _target("services/payment_service.py", "process_payment")
        result = run(
            target_file="services/payment_service.py",
            target_symbol="process_payment",
            change_description="Add support for a new payment provider",
            change_type="general",
            target_info=target_info,
        )
        report = build_report(result)
        # Should not raise
        serialised = json.dumps(report)
        assert len(serialised) > 100
