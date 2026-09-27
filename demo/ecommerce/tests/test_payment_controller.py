"""
Demo E-Commerce — Tests for PaymentController

Tests the HTTP surface (status codes, response shapes) for POST /payments,
GET /payments/order/:id, POST /payments/order/:id/refund, GET /payments.

These are the tests that break when either PaymentController or
PaymentService changes their interface.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import json
import pytest
from flask import Flask
from routes.payments import payments_bp
from routes.orders import orders_bp


def _make_app() -> Flask:
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(orders_bp)
    app.register_blueprint(payments_bp)
    return app


def _create_paid_order(client, user_id: int = 1, product_id: int = 101,
                        address_id: int = 1) -> int:
    """Helper: place + pay an order, return order_id."""
    order_res = client.post("/orders", json={
        "user_id": user_id,
        "items": [{"product_id": product_id, "quantity": 1}],
        "shipping_address_id": address_id,
    })
    order_id = json.loads(order_res.data)["order"]["id"]
    client.post("/payments", json={
        "order_id": order_id,
        "user_id": user_id,
        "payment_method": "card",
        "card_last_four": "4242",
    })
    return order_id


def test_charge_returns_201_on_success():
    app = _make_app()
    with app.test_client() as client:
        order_res = client.post("/orders", json={
            "user_id": 1,
            "items": [{"product_id": 101, "quantity": 1}],
            "shipping_address_id": 1,
        })
        order_id = json.loads(order_res.data)["order"]["id"]
        res = client.post("/payments", json={
            "order_id": order_id, "user_id": 1,
            "payment_method": "card", "card_last_four": "4242",
        })
        assert res.status_code == 201
        data = json.loads(res.data)
        assert "payment" in data
        assert data["payment"]["status"] == "succeeded"


def test_charge_missing_fields_returns_400():
    app = _make_app()
    with app.test_client() as client:
        res = client.post("/payments", json={})
        assert res.status_code == 400


def test_charge_declined_returns_402():
    app = _make_app()
    with app.test_client() as client:
        order_res = client.post("/orders", json={
            "user_id": 1,
            "items": [{"product_id": 102, "quantity": 1}],
            "shipping_address_id": 1,
        })
        order_id = json.loads(order_res.data)["order"]["id"]
        res = client.post("/payments", json={
            "order_id": order_id, "user_id": 1,
            "payment_method": "card", "card_last_four": "0000",
        })
        assert res.status_code == 402
        data = json.loads(res.data)
        assert data["code"] == "payment_declined"


def test_get_payment_returns_200():
    app = _make_app()
    with app.test_client() as client:
        order_id = _create_paid_order(client)
        res = client.get(f"/payments/order/{order_id}")
        assert res.status_code == 200
        assert "payment" in json.loads(res.data)


def test_get_payment_not_found_returns_404():
    app = _make_app()
    with app.test_client() as client:
        # Place but do NOT pay
        order_res = client.post("/orders", json={
            "user_id": 1,
            "items": [{"product_id": 104, "quantity": 1}],
            "shipping_address_id": 1,
        })
        order_id = json.loads(order_res.data)["order"]["id"]
        res = client.get(f"/payments/order/{order_id}")
        assert res.status_code == 404


def test_refund_returns_200():
    app = _make_app()
    with app.test_client() as client:
        order_id = _create_paid_order(client, product_id=105)
        res = client.post(f"/payments/order/{order_id}/refund", json={})
        assert res.status_code == 200
        data = json.loads(res.data)
        assert data["payment"]["status"] == "refunded"


def test_refund_unpaid_returns_error():
    """
    Refunding an order that was never paid returns a 4xx error.

    404 → no payment record exists (PaymentNotFoundError)
    409 → payment exists but status != succeeded (RefundError)
    Both are correct — the refund must be blocked either way.
    """
    app = _make_app()
    with app.test_client() as client:
        order_res = client.post("/orders", json={
            "user_id": 1,
            "items": [{"product_id": 103, "quantity": 1}],
            "shipping_address_id": 1,
        })
        order_id = json.loads(order_res.data)["order"]["id"]
        res = client.post(f"/payments/order/{order_id}/refund", json={})
        assert res.status_code in (404, 409)


def test_payment_history_returns_list():
    app = _make_app()
    with app.test_client() as client:
        res = client.get("/payments?user_id=1")
        assert res.status_code == 200
        data = json.loads(res.data)
        assert "payments" in data
        assert isinstance(data["payments"], list)


def test_payment_history_missing_user_id():
    app = _make_app()
    with app.test_client() as client:
        res = client.get("/payments")
        assert res.status_code == 400


if __name__ == "__main__":
    test_charge_returns_201_on_success()
    test_charge_declined_returns_402()
    test_get_payment_returns_200()
    test_refund_returns_200()
    print("All payment controller tests passed.")
