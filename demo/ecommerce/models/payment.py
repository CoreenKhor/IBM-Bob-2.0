"""
Demo E-Commerce — Payment Model

Represents the `payments` table. Tracks every payment attempt
against an order, including status, gateway response, and refunds.

Relationships:
  - Payment belongs-to Order (via order_id)
  - Payment belongs-to User (via user_id)

Blast-radius note: changes to this model (e.g. adding `payment_method_type`,
altering `status` enum, or adding `refund_amount`) cascade to:
  PaymentService.process_payment()    → PaymentController.charge()
  PaymentService.refund_payment()     → PaymentController.refund()
  OrderService.confirm_order()        (reads payment status to confirm)
  Checkout / PaymentForm (frontend)   (displays payment status)
  test_payment_service.py, test_payment_controller.py, test_checkout.py
"""

from __future__ import annotations
from datetime import datetime, timezone
from typing import Optional

# ---------------------------------------------------------------------------
# Payment status constants
# ---------------------------------------------------------------------------
PAYMENT_PENDING    = "pending"
PAYMENT_PROCESSING = "processing"
PAYMENT_SUCCEEDED  = "succeeded"
PAYMENT_FAILED     = "failed"
PAYMENT_REFUNDED   = "refunded"
PAYMENT_CANCELLED  = "cancelled"

VALID_PAYMENT_STATUSES = {
    PAYMENT_PENDING, PAYMENT_PROCESSING,
    PAYMENT_SUCCEEDED, PAYMENT_FAILED,
    PAYMENT_REFUNDED, PAYMENT_CANCELLED,
}

# Payment method types
METHOD_CARD   = "card"
METHOD_PAYPAL = "paypal"
METHOD_WALLET = "wallet"

# ---------------------------------------------------------------------------
# In-memory store
# ---------------------------------------------------------------------------
_payments: dict[int, dict] = {
    1: {
        "id": 1,
        "order_id": 1,
        "user_id": 1,
        "amount": 210.57,
        "currency": "USD",
        "status": PAYMENT_SUCCEEDED,
        "payment_method": METHOD_CARD,
        "card_last_four": "4242",
        "gateway_transaction_id": "txn_001_abc123",
        "gateway_response": {"code": "00", "message": "Approved"},
        "refund_amount": 0.0,
        "created_at": "2024-06-01T09:01:00Z",
        "updated_at": "2024-06-01T09:01:05Z",
    },
}

_next_payment_id = 10


class Payment:
    """
    ORM-style model for the `payments` table.

    This is the PRIMARY blast-radius demo target for payment-related changes.
    Every field here is referenced by PaymentService, PaymentController,
    OrderService, and the frontend checkout flow.
    """

    @staticmethod
    def find(payment_id: int) -> Optional[dict]:
        """SELECT * FROM payments WHERE id = :payment_id."""
        return _payments.get(payment_id)

    @staticmethod
    def find_by_order(order_id: int) -> Optional[dict]:
        """SELECT * FROM payments WHERE order_id = :order_id LIMIT 1."""
        return next(
            (p for p in _payments.values() if p["order_id"] == order_id),
            None,
        )

    @staticmethod
    def find_by_user(user_id: int) -> list[dict]:
        """SELECT * FROM payments WHERE user_id = :user_id ORDER BY created_at DESC."""
        return sorted(
            [p for p in _payments.values() if p["user_id"] == user_id],
            key=lambda p: p["created_at"],
            reverse=True,
        )

    @staticmethod
    def create(
        order_id: int,
        user_id: int,
        amount: float,
        currency: str,
        payment_method: str,
        card_last_four: str = "",
    ) -> dict:
        """INSERT INTO payments (...) VALUES (...) RETURNING *."""
        global _next_payment_id
        now = datetime.now(timezone.utc).isoformat()
        payment: dict = {
            "id": _next_payment_id,
            "order_id": order_id,
            "user_id": user_id,
            "amount": amount,
            "currency": currency,
            "status": PAYMENT_PENDING,
            "payment_method": payment_method,
            "card_last_four": card_last_four,
            "gateway_transaction_id": None,
            "gateway_response": None,
            "refund_amount": 0.0,
            "created_at": now,
            "updated_at": now,
        }
        _payments[_next_payment_id] = payment
        _next_payment_id += 1
        return payment

    @staticmethod
    def update_status(
        payment_id: int,
        status: str,
        gateway_transaction_id: Optional[str] = None,
        gateway_response: Optional[dict] = None,
    ) -> Optional[dict]:
        """UPDATE payments SET status=..., gateway_transaction_id=... WHERE id=:payment_id."""
        if status not in VALID_PAYMENT_STATUSES:
            raise ValueError(f"Invalid payment status: {status!r}")
        payment = _payments.get(payment_id)
        if payment is None:
            return None
        payment["status"] = status
        payment["updated_at"] = datetime.now(timezone.utc).isoformat()
        if gateway_transaction_id is not None:
            payment["gateway_transaction_id"] = gateway_transaction_id
        if gateway_response is not None:
            payment["gateway_response"] = gateway_response
        return payment

    @staticmethod
    def record_refund(payment_id: int, refund_amount: float) -> Optional[dict]:
        """
        UPDATE payments SET refund_amount=..., status='refunded' WHERE id=:payment_id.

        Blast-radius note: adding `partial_refund` logic here would ripple to
        PaymentService.refund_payment(), PaymentController.refund(), OrderService,
        and all refund-related tests.
        """
        payment = _payments.get(payment_id)
        if payment is None:
            return None
        payment["refund_amount"] = refund_amount
        payment["status"] = PAYMENT_REFUNDED
        payment["updated_at"] = datetime.now(timezone.utc).isoformat()
        return payment

    @staticmethod
    def all() -> list[dict]:
        """SELECT * FROM payments ORDER BY created_at DESC."""
        return sorted(_payments.values(), key=lambda p: p["created_at"], reverse=True)
