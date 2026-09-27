"""
Demo E-Commerce — Tests for the Checkout Flow (Integration)

Simulates the full end-to-end checkout path:
  place_order → apply_discount → process_payment → confirm_order

These tests cross OrderService, PaymentService, and both controllers,
making them the highest-value blast-radius surface in the test suite.

Blast-radius coverage:
  - calculate_order_total() changes → totals assertions fail
  - process_payment() changes       → payment assertions fail
  - Payment model changes           → status/field assertions fail
  - Order model status changes      → order status assertions fail
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import json
import pytest
from flask import Flask
from routes.orders import orders_bp
from routes.payments import payments_bp
from routes.users import users_bp
from services.order_service import calculate_order_total
from services.payment_service import get_payment_for_order
from models.order import STATUS_PAID, STATUS_CONFIRMED, STATUS_REFUNDED
from models.payment import PAYMENT_SUCCEEDED, PAYMENT_REFUNDED


# ---------------------------------------------------------------------------
# Flask test app
# ---------------------------------------------------------------------------

def _make_app() -> Flask:
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(orders_bp)
    app.register_blueprint(payments_bp)
    app.register_blueprint(users_bp)
    return app


# ---------------------------------------------------------------------------
# Full checkout flow — happy path
# ---------------------------------------------------------------------------

def test_checkout_full_happy_path():
    """
    Happy path: POST /orders → POST /payments → order is PAID.

    This test is the most comprehensive blast-radius surface.
    Any change to calculate_order_total(), process_payment(), or the
    Order/Payment models will break at least one assertion here.
    """
    app = _make_app()
    with app.test_client() as client:
        # Step 1: Place an order
        order_res = client.post("/orders", json={
            "user_id": 1,
            "items": [{"product_id": 101, "quantity": 1}],
            "shipping_address_id": 1,
        })
        assert order_res.status_code == 201
        order_data = json.loads(order_res.data)
        order_id = order_data["order"]["id"]
        assert order_id > 0

        # Step 2: Pay for the order
        # Blast-radius: process_payment() signature change → this payload breaks
        pay_res = client.post("/payments", json={
            "order_id": order_id,
            "user_id": 1,
            "payment_method": "card",
            "card_last_four": "4242",
        })
        assert pay_res.status_code == 201
        pay_data = json.loads(pay_res.data)
        assert pay_data["payment"]["status"] == PAYMENT_SUCCEEDED

        # Step 3: Verify order moved to PAID + CONFIRMED
        order_detail_res = client.get(f"/orders/{order_id}")
        assert order_detail_res.status_code == 200
        order_detail = json.loads(order_detail_res.data)
        assert order_detail["order"]["status"] == STATUS_CONFIRMED


def test_checkout_with_discount_code():
    """
    Checkout with a SAVE10 discount: total should reflect 10% off subtotal.

    Blast-radius: apply_discount_code() or calculate_order_total() change
    will break the amount comparison below.
    """
    app = _make_app()
    with app.test_client() as client:
        # Place order
        order_res = client.post("/orders", json={
            "user_id": 1,
            "items": [{"product_id": 103, "quantity": 1}],  # 119.99
            "shipping_address_id": 1,
        })
        assert order_res.status_code == 201
        order_id = json.loads(order_res.data)["order"]["id"]

        # Apply discount
        disc_res = client.post(f"/orders/{order_id}/discount", json={"code": "SAVE10"})
        assert disc_res.status_code == 200
        disc_data = json.loads(disc_res.data)
        assert disc_data["order"]["discount_amount"] > 0

        # Pay
        totals = calculate_order_total(order_id)
        pay_res = client.post("/payments", json={
            "order_id": order_id,
            "user_id": 1,
            "payment_method": "card",
            "card_last_four": "4242",
        })
        assert pay_res.status_code == 201
        pay_data = json.loads(pay_res.data)
        # Payment amount must match the discounted total
        assert pay_data["payment"]["amount"] == pytest.approx(totals["total"], abs=0.01)


def test_checkout_card_declined():
    """
    Checkout with a declined card should return 402 and NOT mark order as PAID.

    Blast-radius: PaymentDeclinedError exception type or HTTP code change
    breaks this test. PaymentController.charge() mapping is the bridge.
    """
    app = _make_app()
    with app.test_client() as client:
        order_res = client.post("/orders", json={
            "user_id": 2,
            "items": [{"product_id": 102, "quantity": 1}],
            "shipping_address_id": 2,
        })
        assert order_res.status_code == 201
        order_id = json.loads(order_res.data)["order"]["id"]

        pay_res = client.post("/payments", json={
            "order_id": order_id,
            "user_id": 2,
            "payment_method": "card",
            "card_last_four": "0000",  # declined card
        })
        assert pay_res.status_code == 402
        error_data = json.loads(pay_res.data)
        assert error_data["code"] == "payment_declined"
        assert error_data["decline_code"] == "card_declined"


def test_checkout_invalid_payment_method():
    """
    An unsupported payment_method should return 400.

    Blast-radius: VALID_PAYMENT_METHODS set change in PaymentService
    alters which methods are accepted.
    """
    app = _make_app()
    with app.test_client() as client:
        order_res = client.post("/orders", json={
            "user_id": 1,
            "items": [{"product_id": 104, "quantity": 1}],
            "shipping_address_id": 1,
        })
        order_id = json.loads(order_res.data)["order"]["id"]

        pay_res = client.post("/payments", json={
            "order_id": order_id,
            "user_id": 1,
            "payment_method": "crypto",  # not supported
        })
        assert pay_res.status_code == 400
        assert json.loads(pay_res.data)["code"] == "invalid_payment_method"


def test_checkout_refund_flow():
    """
    Full refund flow: pay → refund → order is REFUNDED, payment is REFUNDED.

    Blast-radius: refund_payment() changes break POST /payments/order/:id/refund
    and the OrderPage frontend's payment status display.
    """
    app = _make_app()
    with app.test_client() as client:
        # Place + pay
        order_res = client.post("/orders", json={
            "user_id": 1,
            "items": [{"product_id": 105, "quantity": 1}],
            "shipping_address_id": 1,
        })
        order_id = json.loads(order_res.data)["order"]["id"]
        client.post("/payments", json={
            "order_id": order_id,
            "user_id": 1,
            "payment_method": "card",
            "card_last_four": "4242",
        })

        # Refund
        refund_res = client.post(f"/payments/order/{order_id}/refund",
                                 json={"reason": "Customer requested"})
        assert refund_res.status_code == 200
        refund_data = json.loads(refund_res.data)
        assert refund_data["payment"]["status"] == PAYMENT_REFUNDED


def test_checkout_get_payment_after_success():
    """
    GET /payments/order/:id should return the payment after checkout.

    Blast-radius: PaymentController.get_payment() return shape change
    breaks OrderPage.tsx's payment section rendering.
    """
    app = _make_app()
    with app.test_client() as client:
        order_res = client.post("/orders", json={
            "user_id": 2,
            "items": [{"product_id": 103, "quantity": 1}],
            "shipping_address_id": 2,
        })
        order_id = json.loads(order_res.data)["order"]["id"]
        client.post("/payments", json={
            "order_id": order_id,
            "user_id": 2,
            "payment_method": "wallet",
        })

        get_res = client.get(f"/payments/order/{order_id}")
        assert get_res.status_code == 200
        data = json.loads(get_res.data)
        assert "payment" in data
        assert data["payment"]["status"] == PAYMENT_SUCCEEDED


def test_checkout_duplicate_payment_rejected():
    """
    A second payment attempt on an already-paid order returns 409.

    Blast-radius: PaymentAlreadyProcessedError or HTTP 409 mapping change
    breaks this contract.
    """
    app = _make_app()
    with app.test_client() as client:
        order_res = client.post("/orders", json={
            "user_id": 1,
            "items": [{"product_id": 102, "quantity": 1}],
            "shipping_address_id": 1,
        })
        order_id = json.loads(order_res.data)["order"]["id"]
        # First payment
        client.post("/payments", json={
            "order_id": order_id, "user_id": 1,
            "payment_method": "card", "card_last_four": "4242",
        })
        # Second payment
        res = client.post("/payments", json={
            "order_id": order_id, "user_id": 1,
            "payment_method": "card", "card_last_four": "4242",
        })
        assert res.status_code == 409
        assert json.loads(res.data)["code"] == "already_paid"


if __name__ == "__main__":
    test_checkout_full_happy_path()
    test_checkout_with_discount_code()
    test_checkout_card_declined()
    test_checkout_refund_flow()
    test_checkout_duplicate_payment_rejected()
    print("All checkout integration tests passed.")
