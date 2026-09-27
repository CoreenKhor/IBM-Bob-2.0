"""
Demo E-Commerce — Tests for PaymentService

Tests the core payment processing, refund, and history functions.

Blast-radius coverage: if PaymentService.process_payment() signature or
behaviour changes, these tests will fail, surfacing the impact immediately.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from services.payment_service import (
    process_payment,
    get_payment_for_order,
    refund_payment,
    get_payment_history,
    PaymentNotFoundError,
    PaymentAlreadyProcessedError,
    InvalidPaymentMethodError,
    PaymentDeclinedError,
    RefundError,
)
from models.payment import PAYMENT_SUCCEEDED, PAYMENT_FAILED, PAYMENT_REFUNDED
from models.order import Order, STATUS_PAID, STATUS_REFUNDED


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_fresh_order() -> int:
    """Create a clean pending order for payment tests."""
    from services.order_service import place_order
    order_id = place_order(
        user_id=1,
        items=[{"product_id": 101, "quantity": 1}],
        shipping_address_id=1,
    )["id"]
    return order_id


# ---------------------------------------------------------------------------
# process_payment — success paths
# ---------------------------------------------------------------------------

def test_process_payment_card_success():
    """A standard card ending in 4242 should succeed.

    After process_payment() the order transitions:
      pending → paid (Order.update_status) → confirmed (confirm_order).
    STATUS_CONFIRMED is the final resting state after a successful payment.
    """
    order_id = _make_fresh_order()
    payment = process_payment(
        order_id=order_id,
        user_id=1,
        payment_method="card",
        card_last_four="4242",
    )
    assert payment["status"] == PAYMENT_SUCCEEDED
    assert payment["gateway_transaction_id"] is not None

    order = Order.find(order_id)
    # confirm_order() is called after STATUS_PAID, so the visible status is confirmed
    from models.order import STATUS_CONFIRMED
    assert order["status"] == STATUS_CONFIRMED


def test_process_payment_paypal_success():
    """PayPal payment method should succeed (no card required)."""
    order_id = _make_fresh_order()
    payment = process_payment(
        order_id=order_id,
        user_id=1,
        payment_method="paypal",
    )
    assert payment["status"] == PAYMENT_SUCCEEDED


def test_process_payment_wallet_success():
    """Wallet payment method should succeed."""
    order_id = _make_fresh_order()
    payment = process_payment(
        order_id=order_id,
        user_id=1,
        payment_method="wallet",
    )
    assert payment["status"] == PAYMENT_SUCCEEDED


# ---------------------------------------------------------------------------
# process_payment — decline paths
# ---------------------------------------------------------------------------

def test_process_payment_card_declined():
    """Card ending in 0000 should be declined; order must NOT be set to PAID."""
    order_id = _make_fresh_order()
    with pytest.raises(PaymentDeclinedError) as exc_info:
        process_payment(
            order_id=order_id,
            user_id=1,
            payment_method="card",
            card_last_four="0000",
        )
    assert exc_info.value.decline_code == "card_declined"
    order = Order.find(order_id)
    assert order["status"] != STATUS_PAID


def test_process_payment_insufficient_funds():
    """Card ending in 1111 should be declined with insufficient_funds code."""
    order_id = _make_fresh_order()
    with pytest.raises(PaymentDeclinedError) as exc_info:
        process_payment(
            order_id=order_id,
            user_id=1,
            payment_method="card",
            card_last_four="1111",
        )
    assert exc_info.value.decline_code == "insufficient_funds"


# ---------------------------------------------------------------------------
# process_payment — validation
# ---------------------------------------------------------------------------

def test_process_payment_invalid_method():
    """An unsupported payment method should raise InvalidPaymentMethodError."""
    order_id = _make_fresh_order()
    with pytest.raises(InvalidPaymentMethodError):
        process_payment(
            order_id=order_id,
            user_id=1,
            payment_method="bitcoin",
        )


def test_process_payment_already_paid():
    """Attempting to pay an already-paid order raises PaymentAlreadyProcessedError."""
    order_id = _make_fresh_order()
    # First payment — succeeds
    process_payment(order_id=order_id, user_id=1, payment_method="card", card_last_four="4242")
    # Second attempt — must fail
    with pytest.raises(PaymentAlreadyProcessedError):
        process_payment(order_id=order_id, user_id=1, payment_method="card", card_last_four="4242")


def test_process_payment_nonexistent_order():
    """Paying a non-existent order raises ValueError."""
    with pytest.raises(ValueError, match="not found"):
        process_payment(order_id=99999, user_id=1, payment_method="card")


# ---------------------------------------------------------------------------
# get_payment_for_order
# ---------------------------------------------------------------------------

def test_get_payment_for_order_succeeds():
    """Should return the payment record after a successful charge."""
    order_id = _make_fresh_order()
    process_payment(order_id=order_id, user_id=1, payment_method="card", card_last_four="4242")
    payment = get_payment_for_order(order_id)
    assert payment["order_id"] == order_id
    assert payment["status"] == PAYMENT_SUCCEEDED


def test_get_payment_for_order_not_found():
    """Should raise PaymentNotFoundError for an order with no payment."""
    order_id = _make_fresh_order()  # never paid
    with pytest.raises(PaymentNotFoundError):
        get_payment_for_order(order_id)


# ---------------------------------------------------------------------------
# refund_payment
# ---------------------------------------------------------------------------

def test_refund_payment_succeeds():
    """Refunding a paid order should set payment to REFUNDED and order to REFUNDED."""
    order_id = _make_fresh_order()
    process_payment(order_id=order_id, user_id=1, payment_method="card", card_last_four="4242")
    refunded = refund_payment(order_id)
    assert refunded["status"] == PAYMENT_REFUNDED
    order = Order.find(order_id)
    assert order["status"] == STATUS_REFUNDED


def test_refund_payment_not_paid():
    """
    Attempting to refund an order with no successful payment raises an error.

    If the order was never charged → PaymentNotFoundError.
    If the order was declined     → RefundError (payment exists but status != succeeded).
    Both correctly prevent a refund being issued.
    """
    order_id = _make_fresh_order()
    # No payment has been attempted → PaymentNotFoundError is the correct response
    with pytest.raises((RefundError, PaymentNotFoundError)):
        refund_payment(order_id)


def test_refund_amount_matches_charged():
    """Refund amount should equal the original payment amount."""
    order_id = _make_fresh_order()
    payment = process_payment(
        order_id=order_id, user_id=1, payment_method="card", card_last_four="4242"
    )
    refunded = refund_payment(order_id)
    assert refunded["refund_amount"] == payment["amount"]


# ---------------------------------------------------------------------------
# get_payment_history
# ---------------------------------------------------------------------------

def test_get_payment_history_returns_list():
    """Should return a list of payments for a user."""
    history = get_payment_history(user_id=1)
    assert isinstance(history, list)


if __name__ == "__main__":
    test_process_payment_card_success()
    test_process_payment_card_declined()
    test_process_payment_invalid_method()
    test_process_payment_already_paid()
    test_refund_payment_succeeds()
    print("All payment service tests passed.")
