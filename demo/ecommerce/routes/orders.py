"""
Demo E-Commerce — Order Routes

HTTP surface for order CRUD and lifecycle operations.
All logic is delegated to OrderController.
"""

from flask import Blueprint, request, jsonify
from controllers.order_controller import OrderController

orders_bp = Blueprint("orders", __name__)


@orders_bp.route("/orders", methods=["POST"])
def create_order():
    """POST /orders — place a new order."""
    data = request.get_json(silent=True) or {}
    body, status = OrderController.create(data)
    return jsonify(body), status


@orders_bp.route("/orders/<int:order_id>", methods=["GET"])
def get_order(order_id: int):
    """GET /orders/<id> — get order detail with live totals."""
    body, status = OrderController.get(order_id)
    return jsonify(body), status


@orders_bp.route("/orders", methods=["GET"])
def list_orders():
    """GET /orders?user_id=<id> — list orders for a user."""
    user_id = request.args.get("user_id", type=int)
    if not user_id:
        return jsonify({"error": "user_id query parameter is required"}), 400
    body, status = OrderController.list_for_user(user_id)
    return jsonify(body), status


@orders_bp.route("/orders/<int:order_id>", methods=["DELETE"])
def cancel_order(order_id: int):
    """DELETE /orders/<id> — cancel a pending or confirmed order."""
    body, status = OrderController.cancel(order_id)
    return jsonify(body), status


@orders_bp.route("/orders/<int:order_id>/discount", methods=["POST"])
def apply_discount(order_id: int):
    """POST /orders/<id>/discount — apply a discount code."""
    data = request.get_json(silent=True) or {}
    body, status = OrderController.apply_discount(order_id, data)
    return jsonify(body), status
