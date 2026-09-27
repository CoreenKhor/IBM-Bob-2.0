"""
Demo E-Commerce — Payment Routes

HTTP surface for payment operations. All logic is delegated to PaymentController.
"""

from flask import Blueprint, request, jsonify
from controllers.payment_controller import PaymentController

payments_bp = Blueprint("payments", __name__)


@payments_bp.route("/payments", methods=["POST"])
def charge():
    """POST /payments — initiate a payment for an order."""
    data = request.get_json(silent=True) or {}
    body, status = PaymentController.charge(data)
    return jsonify(body), status


@payments_bp.route("/payments/order/<int:order_id>", methods=["GET"])
def get_payment(order_id: int):
    """GET /payments/order/<id> — retrieve payment status for an order."""
    body, status = PaymentController.get_payment(order_id)
    return jsonify(body), status


@payments_bp.route("/payments/order/<int:order_id>/refund", methods=["POST"])
def refund(order_id: int):
    """POST /payments/order/<id>/refund — refund a completed payment."""
    data = request.get_json(silent=True) or {}
    body, status = PaymentController.refund(order_id, data)
    return jsonify(body), status


@payments_bp.route("/payments", methods=["GET"])
def payment_history():
    """GET /payments?user_id=<id> — list all payments for a user."""
    user_id = request.args.get("user_id", type=int)
    if not user_id:
        return jsonify({"error": "user_id query parameter is required"}), 400
    body, status = PaymentController.history(user_id)
    return jsonify(body), status
