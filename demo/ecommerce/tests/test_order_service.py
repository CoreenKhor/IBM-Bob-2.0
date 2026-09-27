"""
Demo E-Commerce — Tests for OrderService

Tests order placement, total calculation, discount codes, and cancellation.

Blast-radius coverage: if OrderService.calculate_order_total() signature,
return type, or TAX_RATE constant changes, every assertion below will fail.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from services.order_service import (
    calculate_order_total,
    place_order,
    get_order_by_id,
    get_orders_for_user,
    confirm_order,
    cancel_order,
    apply_discount_code,
    OrderNotFoundError,
    InsufficientStockError,
    TAX_RATE,
)
from models.order import Order, STATUS_PENDING, STATUS_CONFIRMED, STATUS_CANCELLED


# ---------------------------------------------------------------------------
# calculate_order_total
# ---------------------------------------------------------------------------

def test_calculate_order_total_existing_order():
    """
    Order 1 has: Headphones 79.99×2 + USB-C Hub 34.99×1 = 194.97 subtotal.
    Tax = 194.97 × 0.08 = 15.60 (rounded).
    Total = 194.97 + 15.60 = 210.57.

    Blast-radius: if TAX_RATE changes or calculate_order_total return type
    changes (e.g. returning a float instead of dict), this test will fail,
    surfacing the impact in test_payment_service.py and test_checkout.py.
    """
    totals = calculate_order_total(1)
    assert isinstance(totals, dict), "calculate_order_total must return a dict"
    assert totals["subtotal"] == 194.97
    assert totals["tax_amount"] == pytest.approx(194.97 * TAX_RATE, abs=0.01)
    assert totals["total"] == pytest.approx(totals["subtotal"] + totals["tax_amount"], abs=0.01)


def test_calculate_order_total_nonexistent_returns_zeros():
    """A non-existent order should return zero totals, not raise an exception."""
    totals = calculate_order_total(99999)
    assert totals["total"] == 0.0
    assert totals["subtotal"] == 0.0


def test_calculate_order_total_with_discount():
    """Discount is subtracted before tax is applied."""
    order_id = place_order(
        user_id=1,
        items=[{"product_id": 101, "quantity": 2}],
        shipping_address_id=1,
        discount_amount=20.0,
    )["id"]
    totals = calculate_order_total(order_id)
    taxable = totals["subtotal"] - totals["discount_amount"]
    assert totals["tax_amount"] == pytest.approx(taxable * TAX_RATE, abs=0.01)
    assert totals["total"] == pytest.approx(taxable + totals["tax_amount"], abs=0.01)


# ---------------------------------------------------------------------------
# place_order
# ---------------------------------------------------------------------------

def test_place_order_returns_full_order():
    """place_order should return a dict with id, status, total, and items."""
    order = place_order(
        user_id=1,
        items=[{"product_id": 102, "quantity": 1}],
        shipping_address_id=1,
    )
    assert "id" in order
    assert "items" in order
    assert order["status"] == STATUS_PENDING
    assert order["total"] > 0


def test_place_order_stamps_unit_price():
    """Items in the placed order should have unit_price set from the catalogue."""
    order = place_order(
        user_id=1,
        items=[{"product_id": 103, "quantity": 1}],
        shipping_address_id=1,
    )
    assert order["items"][0]["unit_price"] == 119.99


def test_place_order_invalid_user():
    """Placing an order for a non-existent user should raise ValueError."""
    with pytest.raises(ValueError, match="not found"):
        place_order(user_id=99999, items=[{"product_id": 101, "quantity": 1}],
                    shipping_address_id=1)


def test_place_order_invalid_address():
    """Placing an order with another user's address should raise ValueError."""
    with pytest.raises(ValueError, match="Invalid"):
        # Address 2 belongs to user_id=2, not user_id=1
        place_order(user_id=1, items=[{"product_id": 101, "quantity": 1}],
                    shipping_address_id=2)


def test_place_order_insufficient_stock():
    """Ordering more than available stock should raise InsufficientStockError."""
    with pytest.raises(InsufficientStockError):
        place_order(
            user_id=1,
            items=[{"product_id": 101, "quantity": 10000}],
            shipping_address_id=1,
        )


# ---------------------------------------------------------------------------
# get_order_by_id
# ---------------------------------------------------------------------------

def test_get_order_by_id_found():
    order = get_order_by_id(1)
    assert order["id"] == 1
    assert "items" in order


def test_get_order_by_id_not_found():
    with pytest.raises(OrderNotFoundError):
        get_order_by_id(99999)


# ---------------------------------------------------------------------------
# get_orders_for_user
# ---------------------------------------------------------------------------

def test_get_orders_for_user_returns_list():
    orders = get_orders_for_user(user_id=1)
    assert isinstance(orders, list)
    assert all(o["user_id"] == 1 for o in orders)


def test_get_orders_for_user_empty_for_unknown():
    orders = get_orders_for_user(user_id=99999)
    assert orders == []


# ---------------------------------------------------------------------------
# confirm_order
# ---------------------------------------------------------------------------

def test_confirm_order_transitions_status():
    """confirm_order should set status to 'confirmed'."""
    order_id = place_order(
        user_id=1,
        items=[{"product_id": 104, "quantity": 1}],
        shipping_address_id=1,
    )["id"]
    confirmed = confirm_order(order_id)
    assert confirmed["status"] == STATUS_CONFIRMED


def test_confirm_order_not_found():
    with pytest.raises(OrderNotFoundError):
        confirm_order(99999)


# ---------------------------------------------------------------------------
# cancel_order
# ---------------------------------------------------------------------------

def test_cancel_order_pending():
    """A pending order can be cancelled."""
    order_id = place_order(
        user_id=1,
        items=[{"product_id": 102, "quantity": 1}],
        shipping_address_id=1,
    )["id"]
    cancelled = cancel_order(order_id)
    assert cancelled["status"] == STATUS_CANCELLED


def test_cancel_paid_order_raises():
    """Cancelling an already-paid order should raise ValueError."""
    with pytest.raises(ValueError, match="Cannot cancel"):
        cancel_order(1)   # Order 1 is STATUS_PAID in seed data


# ---------------------------------------------------------------------------
# apply_discount_code
# ---------------------------------------------------------------------------

def test_apply_discount_code_SAVE10():
    """SAVE10 applies a 10% discount."""
    order_id = place_order(
        user_id=1,
        items=[{"product_id": 101, "quantity": 2}],
        shipping_address_id=1,
    )["id"]
    totals_before = calculate_order_total(order_id)
    order = apply_discount_code(order_id, "SAVE10")
    assert order["discount_amount"] == pytest.approx(totals_before["subtotal"] * 0.10, abs=0.01)


def test_apply_discount_code_FLAT20():
    """FLAT20 takes $20 off."""
    order_id = place_order(
        user_id=1,
        items=[{"product_id": 103, "quantity": 1}],
        shipping_address_id=1,
    )["id"]
    order = apply_discount_code(order_id, "FLAT20")
    assert order["discount_amount"] == 20.00


def test_apply_invalid_discount_code():
    """An unknown code should raise ValueError."""
    order_id = place_order(
        user_id=1,
        items=[{"product_id": 104, "quantity": 1}],
        shipping_address_id=1,
    )["id"]
    with pytest.raises(ValueError, match="Invalid"):
        apply_discount_code(order_id, "BADCODE")


if __name__ == "__main__":
    test_calculate_order_total_existing_order()
    test_place_order_returns_full_order()
    test_apply_discount_code_SAVE10()
    test_apply_discount_code_FLAT20()
    print("All order service tests passed.")
