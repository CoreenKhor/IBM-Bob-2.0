"""
Demo E-Commerce — PaymentService

Orchestrates payment processing, status transitions, and refunds.
This is the second most-central service in the blast-radius graph.

Blast-radius note: changes to `process_payment` (e.g. adding `currency`
validation, changing return shape, or adding fraud checks) will cascade to:
  controllers/payment_controller.py  (direct caller)
  routes/payments.py                 (via controller)
  services/order_service.confirm_order()  (called on success)
  models/payment.py                  (status transitions)
  PaymentForm / Checkout (frontend)  (reads payment status + error)
  test_payment_service.py            (unit tests)
  test_payment_controller.py         (integration tests)
  test_checkout.py                   (end-to-end checkout tests)
"""

from __future__ import annotations
import uuid
from typing import Optional

from models.payment import (
    Payment,
    PAYMENT_PENDING, PAYMENT_PROCESSING, PAYMENT_SUCCEEDED,
    PAYMENT_FAILED, PAYMENT_REFUNDED,
    METHOD_CARD, METHOD_PAYPAL, METHOD_WALLET,
)
from models.order import Order, STATUS_PAID, STATUS_REFUNDED


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class PaymentNotFoundError(Exception):
    pass


class PaymentAlreadyProcessedError(Exception):
    pass


class InvalidPaymentMethodError(Exception):
    pass


class PaymentDeclinedError(Exception):
    def __init__(self, message: str, decline_code: str = "generic_decline"):
        super().__init__(message)
        self.decline_code = decline_code


class RefundError(Exception):
    pass


# ---------------------------------------------------------------------------
# Payment gateway simulator
# ---------------------------------------------------------------------------

# Card numbers that trigger specific simulated responses (demo only)
_DECLINE_CARDS = {"0000", "9999"}
_INSUFFICIENT_FUNDS_CARDS = {"1111"}

VALID_PAYMENT_METHODS = {METHOD_CARD, METHOD_PAYPAL, METHOD_WALLET}


def _simulate_gateway_charge(
    amount: float,
    payment_method: str,
    card_last_four: str,
) -> dict:
    """
    Simulate a payment gateway response.

    Real systems call Stripe / PayPal APIs here. This stub returns
    deterministic results based on card_last_four for predictable testing.

    Blast-radius note: replacing this stub with a real gateway call changes
    the error surface of process_payment() and requires test mocking updates.
    """
    if card_last_four in _DECLINE_CARDS:
        return {
            "success": False,
            "decline_code": "card_declined",
            "message": "Your card was declined",
            "transaction_id": None,
        }
    if card_last_four in _INSUFFICIENT_FUNDS_CARDS:
        return {
            "success": False,
            "decline_code": "insufficient_funds",
            "message": "Insufficient funds",
            "transaction_id": None,
        }
    # All other cards succeed
    transaction_id = f"txn_{uuid.uuid4().hex[:12]}"
    return {
        "success": True,
        "decline_code": None,
        "message": "Approved",
        "transaction_id": transaction_id,
    }


# ---------------------------------------------------------------------------
# Service functions
# ---------------------------------------------------------------------------

def process_payment(
    order_id: int,
    user_id: int,
    payment_method: str,
    card_last_four: str = "",
    currency: str = "USD",
) -> dict:
    """
    Process a payment for an order.

    Steps:
      1. Validate payment method is accepted
      2. Validate order exists and is not already paid
      3. Read the order total from OrderService
      4. Create a Payment record in PENDING state
      5. Transition to PROCESSING and call the gateway
      6a. On success → mark SUCCEEDED, update order to PAID, confirm order
      6b. On failure → mark FAILED, raise PaymentDeclinedError

    Returns the final Payment dict.

    Called by:
      controllers/payment_controller.py → charge()
      Checkout frontend (via POST /payments)
    """
    from services.order_service import calculate_order_total, confirm_order

    if payment_method not in VALID_PAYMENT_METHODS:
        raise InvalidPaymentMethodError(
            f"Unsupported payment method: {payment_method!r}. "
            f"Accepted: {sorted(VALID_PAYMENT_METHODS)}"
        )

    order = Order.find(order_id)
    if order is None:
        raise ValueError(f"Order {order_id} not found")

    if order["status"] == STATUS_PAID:
        raise PaymentAlreadyProcessedError(f"Order {order_id} has already been paid")

    existing = Payment.find_by_order(order_id)
    if existing and existing["status"] == PAYMENT_SUCCEEDED:
        raise PaymentAlreadyProcessedError(
            f"A successful payment already exists for order {order_id}"
        )

    # Fetch the live total (not a stale cached value)
    totals = calculate_order_total(order_id)
    amount = totals["total"]

    # Create payment record in PENDING state
    payment = Payment.create(
        order_id=order_id,
        user_id=user_id,
        amount=amount,
        currency=currency,
        payment_method=payment_method,
        card_last_four=card_last_four,
    )
    payment_id = payment["id"]

    # Transition to PROCESSING
    Payment.update_status(payment_id, PAYMENT_PROCESSING)

    # Call gateway
    gateway_result = _simulate_gateway_charge(amount, payment_method, card_last_four)

    if gateway_result["success"]:
        final_payment = Payment.update_status(
            payment_id,
            PAYMENT_SUCCEEDED,
            gateway_transaction_id=gateway_result["transaction_id"],
            gateway_response={"code": "00", "message": gateway_result["message"]},
        )
        # Transition order to PAID and confirm
        Order.update_status(order_id, STATUS_PAID)
        confirm_order(order_id)
        return final_payment  # type: ignore[return-value]

    else:
        Payment.update_status(
            payment_id,
            PAYMENT_FAILED,
            gateway_response={
                "code": gateway_result["decline_code"],
                "message": gateway_result["message"],
            },
        )
        raise PaymentDeclinedError(
            gateway_result["message"],
            decline_code=gateway_result["decline_code"],
        )


def get_payment_for_order(order_id: int) -> dict:
    """
    Retrieve the payment record for an order.

    Called by:
      controllers/payment_controller.py → get_payment()
      OrderPage frontend (displays payment confirmation details)
    """
    payment = Payment.find_by_order(order_id)
    if payment is None:
        raise PaymentNotFoundError(f"No payment found for order {order_id}")
    return payment


def refund_payment(order_id: int, reason: str = "") -> dict:
    """
    Refund a successfully paid order.

    Steps:
      1. Locate the successful payment for the order
      2. Call gateway refund simulation
      3. Record refund on the Payment model
      4. Update order status to REFUNDED

    Called by:
      controllers/payment_controller.py → refund()
      routes/payments.py → POST /payments/<id>/refund
    """
    from services.order_service import cancel_order

    payment = Payment.find_by_order(order_id)
    if payment is None:
        raise PaymentNotFoundError(f"No payment found for order {order_id}")

    if payment["status"] != PAYMENT_SUCCEEDED:
        raise RefundError(
            f"Cannot refund a payment with status {payment['status']!r}"
        )

    # Simulate gateway refund (always succeeds in demo)
    refunded = Payment.record_refund(payment["id"], refund_amount=payment["amount"])
    Order.update_status(order_id, STATUS_REFUNDED)

    return refunded  # type: ignore[return-value]


def get_payment_history(user_id: int) -> list[dict]:
    """
    Return all payments for a user, newest first.

    Called by:
      routes/payments.py → GET /payments?user_id=...
      OrderPage frontend (payment history tab)
    """
    return Payment.find_by_user(user_id)
