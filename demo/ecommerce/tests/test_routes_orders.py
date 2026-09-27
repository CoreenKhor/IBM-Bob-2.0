"""
Demo E-Commerce — Routes integration tests for orders endpoint.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import json
import pytest
from flask import Flask
from routes.orders import orders_bp
from services.order_service import calculate_order_total


def _make_app() -> Flask:
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(orders_bp)
    return app


def test_get_order_returns_totals():
    """GET /orders/1 returns order with subtotal, tax_amount, and total fields."""
    app = _make_app()
    with app.test_client() as client:
        res = client.get("/orders/1")
        assert res.status_code == 200
        data = json.loads(res.data)
        assert "order" in data
        assert "total" in data["order"]
        assert "subtotal" in data["order"]
        assert "tax_amount" in data["order"]


def test_get_order_not_found():
    """GET /orders/99999 returns 404."""
    app = _make_app()
    with app.test_client() as client:
        res = client.get("/orders/99999")
        assert res.status_code == 404


def test_create_order_returns_totals():
    """POST /orders creates an order and returns calculated totals."""
    app = _make_app()
    with app.test_client() as client:
        res = client.post("/orders", json={
            "user_id": 1,
            "items": [{"product_id": 101, "quantity": 1}],
            "shipping_address_id": 1,
        })
        assert res.status_code == 201
        data = json.loads(res.data)
        order_id = data["order"]["id"]
        # Totals must match what calculate_order_total returns
        expected = calculate_order_total(order_id)
        assert data["order"]["total"] == pytest.approx(expected["total"], abs=0.01)


def test_create_order_missing_fields():
    app = _make_app()
    with app.test_client() as client:
        res = client.post("/orders", json={})
        assert res.status_code == 400


def test_list_orders_requires_user_id():
    app = _make_app()
    with app.test_client() as client:
        res = client.get("/orders")
        assert res.status_code == 400


def test_cancel_order():
    app = _make_app()
    with app.test_client() as client:
        # Create then cancel
        create_res = client.post("/orders", json={
            "user_id": 1,
            "items": [{"product_id": 104, "quantity": 1}],
            "shipping_address_id": 1,
        })
        order_id = json.loads(create_res.data)["order"]["id"]
        cancel_res = client.delete(f"/orders/{order_id}")
        assert cancel_res.status_code == 200
        assert json.loads(cancel_res.data)["order"]["status"] == "cancelled"


def test_apply_discount_route():
    app = _make_app()
    with app.test_client() as client:
        create_res = client.post("/orders", json={
            "user_id": 1,
            "items": [{"product_id": 103, "quantity": 1}],
            "shipping_address_id": 1,
        })
        order_id = json.loads(create_res.data)["order"]["id"]
        disc_res = client.post(f"/orders/{order_id}/discount", json={"code": "FLAT20"})
        assert disc_res.status_code == 200
        data = json.loads(disc_res.data)
        assert data["order"]["discount_amount"] == 20.00


if __name__ == "__main__":
    test_get_order_returns_totals()
    test_create_order_returns_totals()
    test_cancel_order()
    print("All order route tests passed.")
