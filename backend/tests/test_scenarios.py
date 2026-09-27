"""
Comprehensive Automated Scenario Tests for Change Blast Radius Analyzer

Covers all 5 core scenarios:
1. Modify PaymentService to support a new payment provider.
2. Modify OrderService to change order-status handling.
3. Modify UserService to add a new user field.
4. Modify the payment database schema.
5. Modify the checkout frontend.

Ensures results are derived dynamically from graph relationships and logic.
"""

from __future__ import annotations
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from engine.codebase_graph import get_graph
from engine.target_resolver import resolve_target
from engine.impact_analyzer import run, ImpactResult
from engine.report_builder import build_report


@pytest.fixture(scope="module", autouse=True)
def fresh_graph():
    """Ensure graph is freshly initialized."""
    return get_graph(force_rebuild=True)


# ===========================================================================
# Scenario 1: Modify PaymentService to support a new payment provider
# ===========================================================================

class TestScenario1PaymentProvider:
    @classmethod
    def setup_class(cls):
        cls.file = "services/payment_service.py"
        cls.symbol = "process_payment"
        cls.desc = "Modify PaymentService to support a new payment provider and gateway webhook"
        cls.change_type = "api_change"
        cls.tinfo = resolve_target(cls.file, cls.symbol)
        cls.result: ImpactResult = run(cls.file, cls.symbol, cls.desc, cls.change_type, cls.tinfo)

    def test_target_resolved(self):
        assert self.tinfo.get("file") == "services/payment_service.py"
        assert self.tinfo.get("symbol") == "process_payment"
        assert self.tinfo.get("kind") in ("function", "async_function")

    def test_direct_callers_include_controller(self):
        direct_files = {c.file for c in self.result.directly_affected}
        assert "controllers/payment_controller.py" in direct_files

    def test_indirect_callers_include_routes(self):
        indirect_files = {c.file for c in self.result.indirectly_affected}
        assert "routes/payments.py" in indirect_files

    def test_related_apis_detected(self):
        routes = {a.path for a in self.result.related_apis}
        assert "/payments" in routes
        assert "/payments/order/<int:order_id>" in routes

    def test_related_db_scoped_to_payments(self):
        tables = {d.table_name for d in self.result.related_db}
        assert "payments" in tables

    def test_related_tests_present(self):
        test_fns = {t["function"] for t in self.result.related_tests}
        assert "test_process_payment_card_success" in test_fns
        assert len(self.result.related_tests) >= 5

    def test_risk_areas_highlight_new_integration(self):
        categories = {r.category for r in self.result.risk_areas}
        assert "api_contract" in categories
        assert "semantic" in categories
        titles = {r.title for r in self.result.risk_areas}
        assert any("external integration" in t.lower() or "integration" in t.lower() for t in titles)

    def test_testing_suggestions_have_commands(self):
        assert len(self.result.testing_suggestions) >= 4
        assert any(s.command and "pytest" in s.command for s in self.result.testing_suggestions)


# ===========================================================================
# Scenario 2: Modify OrderService to change order-status handling
# ===========================================================================

class TestScenario2OrderStatus:
    @classmethod
    def setup_class(cls):
        cls.file = "services/order_service.py"
        cls.symbol = "confirm_order"
        cls.desc = "Modify OrderService to change order-status transition handling and status validation"
        cls.change_type = "general"
        cls.tinfo = resolve_target(cls.file, cls.symbol)
        cls.result: ImpactResult = run(cls.file, cls.symbol, cls.desc, cls.change_type, cls.tinfo)

    def test_target_resolved(self):
        assert self.tinfo.get("file") == "services/order_service.py"
        assert self.tinfo.get("symbol") == "confirm_order"

    def test_direct_caller_includes_payment_service(self):
        direct_files = {c.file for c in self.result.directly_affected}
        assert "services/payment_service.py" in direct_files

    def test_indirect_caller_includes_payment_controller(self):
        indirect_files = {c.file for c in self.result.indirectly_affected}
        assert "controllers/payment_controller.py" in indirect_files

    def test_db_tables_match_orders(self):
        tables = {d.table_name for d in self.result.related_db}
        assert "orders" in tables

    def test_order_tests_covered(self):
        assert len(self.result.related_tests) >= 5
        test_files = {t["file"] for t in self.result.related_tests}
        assert any("test_order_service.py" in f for f in test_files)


# ===========================================================================
# Scenario 3: Modify UserService to add a new user field
# ===========================================================================

class TestScenario3UserField:
    @classmethod
    def setup_class(cls):
        cls.file = "services/user_service.py"
        cls.symbol = "register_user"
        cls.desc = "Modify UserService to add a new user field loyalty_tier and registration validation"
        cls.change_type = "schema_change"
        cls.tinfo = resolve_target(cls.file, cls.symbol)
        cls.result: ImpactResult = run(cls.file, cls.symbol, cls.desc, cls.change_type, cls.tinfo)

    def test_target_resolved(self):
        assert self.tinfo.get("file") == "services/user_service.py"
        assert self.tinfo.get("symbol") == "register_user"

    def test_direct_caller_includes_user_routes(self):
        direct_files = {c.file for c in self.result.directly_affected}
        assert "routes/users.py" in direct_files

    def test_related_apis_include_user_endpoints(self):
        paths = {a.path for a in self.result.related_apis}
        assert "/users/register" in paths
        assert "/users/login" in paths

    def test_db_tables_include_users(self):
        tables = {d.table_name for d in self.result.related_db}
        assert "users" in tables

    def test_schema_migration_risk_detected(self):
        categories = {r.category for r in self.result.risk_areas}
        assert "db_migration" in categories

    def test_testing_suggestions_include_migration(self):
        actions = [s.action.lower() for s in self.result.testing_suggestions]
        assert any("database migration" in a or "migration" in a for a in actions)


# ===========================================================================
# Scenario 4: Modify the payment database schema
# ===========================================================================

class TestScenario4PaymentSchema:
    @classmethod
    def setup_class(cls):
        cls.file = "models/payment.py"
        cls.symbol = "Payment"
        cls.desc = "Modify the payment database schema to add payment_method_type column and gateway fields"
        cls.change_type = "schema_change"
        cls.tinfo = resolve_target(cls.file, cls.symbol)
        cls.result: ImpactResult = run(cls.file, cls.symbol, cls.desc, cls.change_type, cls.tinfo)

    def test_target_resolved(self):
        assert self.tinfo.get("file") == "models/payment.py"
        assert self.tinfo.get("symbol") == "Payment"
        assert self.tinfo.get("kind") == "class"

    def test_direct_caller_includes_payment_service(self):
        direct_files = {c.file for c in self.result.directly_affected}
        assert "services/payment_service.py" in direct_files

    def test_indirect_caller_includes_payment_controller(self):
        indirect_files = {c.file for c in self.result.indirectly_affected}
        assert "controllers/payment_controller.py" in indirect_files

    def test_db_tables_scoped_to_payments(self):
        tables = {d.table_name for d in self.result.related_db}
        assert "payments" in tables

    def test_risk_severity_high_or_critical(self):
        assert self.result.risk_level in ("HIGH", "CRITICAL")
        categories = {r.category for r in self.result.risk_areas}
        assert "db_migration" in categories


# ===========================================================================
# Scenario 5: Modify the checkout frontend
# ===========================================================================

class TestScenario5CheckoutFrontend:
    @classmethod
    def setup_class(cls):
        cls.file = "frontend/Checkout.tsx"
        cls.symbol = "Checkout"
        cls.desc = "Modify the checkout frontend UI to support alternative payment methods and order statuses"
        cls.change_type = "refactor"
        cls.tinfo = resolve_target(cls.file, cls.symbol)
        cls.result: ImpactResult = run(cls.file, cls.symbol, cls.desc, cls.change_type, cls.tinfo)

    def test_target_resolved_from_typescript(self):
        assert self.tinfo.get("file") == "frontend/Checkout.tsx"
        assert self.tinfo.get("symbol") == "Checkout"
        assert self.tinfo.get("kind") == "function"

    def test_related_apis_include_checkout_endpoints(self):
        paths = {a.path for a in self.result.related_apis}
        assert "/orders" in paths
        assert "/orders/<int:order_id>/discount" in paths

    def test_related_tests_include_checkout_integration_tests(self):
        assert len(self.result.related_tests) >= 1
        test_files = {t["file"] for t in self.result.related_tests}
        assert any("test_checkout.py" in f for f in test_files)

    def test_report_builder_serializes_cleanly(self):
        d = build_report(self.result)
        assert d["target"]["file"] == "frontend/Checkout.tsx"
        assert d["target"]["symbol"] == "Checkout"
        assert len(d["impact_categories"]["related_apis"]) >= 2
        assert len(d["impact_categories"]["testing_suggestions"]) >= 2
