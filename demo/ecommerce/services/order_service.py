"""
Demo E-Commerce — OrderService

Central business logic for order lifecycle management:
  place_order → calculate_order_total → confirm_order → cancel_order

This service is intentionally the most connected node in the graph.
Almost every other component depends on it directly or transitively.

Blast-radius note: changes to `calculate_order_total` (the PRIMARY demo target)
will cascade to:
  routes/orders.py           (direct caller via create + get endpoints)
  services/payment_service.py (reads total before charging)
  models/order.py            (persists computed totals)
  Checkout / OrderPage       (displays the total)
  test_order_service.py, test_payment_service.py, test_checkout.py

Changes to `place_order` additionally affect:
  services/user_service.py   (reads shipping address)
  services/inventory_service.py (reserves stock per item)
"""

from __future__ import annotations
from typing import Optional

from models.order import Order, STATUS_PENDING, STATUS_CONFIRMED, STATUS_CANCELLED
from models.product import Product
from models.user import User, Address

# Tax rate applied to all orders (8% — intentionally a named constant so
# a change here propagates to all dependent calculations)
TAX_RATE = 0.08


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class OrderNotFoundError(Exception):
    pass


class OrderAlreadyPaidError(Exception):
    pass


class InsufficientStockError(Exception):
    pass


# ---------------------------------------------------------------------------
# Service functions
# ---------------------------------------------------------------------------

def calculate_order_total(order_id: int) -> dict:
    """
    Calculate the subtotal, tax, discount, and grand total for an order.

    Returns a breakdown dict:
      { subtotal, tax_amount, discount_amount, total }

    This is the PRIMARY blast-radius demo target for the hackathon.
    Signature change (e.g. adding `coupon_code: str = ""`) ripples to
    every direct and transitive caller in the graph.

    Called by:
      place_order()                  (internal)
      routes/orders.py               (GET + POST handlers)
      services/payment_service.py    (reads total before charging)
    """
    order = Order.find(order_id)
    if not order:
        return {"subtotal": 0.0, "tax_amount": 0.0, "discount_amount": 0.0, "total": 0.0}

    subtotal = 0.0
    for item in order.get("items", []):
        product = Product.find(item["product_id"])
        if product:
            subtotal += product["price"] * item["quantity"]

    subtotal = round(subtotal, 2)
    discount_amount = round(order.get("discount_amount", 0.0), 2)
    tax_amount = round((subtotal - discount_amount) * TAX_RATE, 2)
    total = round(subtotal - discount_amount + tax_amount, 2)

    return {
        "subtotal": subtotal,
        "tax_amount": tax_amount,
        "discount_amount": discount_amount,
        "total": total,
    }


def place_order(user_id: int, items: list[dict],
                shipping_address_id: int,
                discount_amount: float = 0.0) -> dict:
    """
    Create a new order, reserve stock, and calculate totals.

    Steps:
      1. Validate user exists
      2. Validate shipping address belongs to user
      3. Check and reserve stock for each item (via InventoryService)
      4. Stamp unit prices from the product catalogue
      5. Persist the order via Order.create()
      6. Calculate totals via calculate_order_total()
      7. Persist totals back to the order record
      8. Return the fully hydrated order dict

    Called by:
      routes/orders.py → POST /orders
      Checkout frontend (final "Place Order" button)
    """
    from services.inventory_service import reserve_item, InsufficientStockError as StockError

    # Validate user
    user = User.find(user_id)
    if user is None:
        raise ValueError(f"User {user_id} not found")

    # Validate address belongs to user
    address = Address.find(shipping_address_id)
    if address is None or address["user_id"] != user_id:
        raise ValueError("Invalid or inaccessible shipping address")

    # Stamp unit prices and reserve stock
    stamped_items = []
    for item in items:
        product = Product.find(item["product_id"])
        if product is None:
            raise ValueError(f"Product {item['product_id']} not found")
        qty = item["quantity"]
        try:
            reserve_item(product_id=item["product_id"], quantity=qty)
        except StockError as exc:
            raise InsufficientStockError(str(exc)) from exc
        stamped_items.append({
            "product_id": item["product_id"],
            "quantity": qty,
            "unit_price": product["price"],
        })

    # Apply discount
    order_id = Order.create(
        user_id=user_id,
        items=stamped_items,
        shipping_address_id=shipping_address_id,
    )
    # Store discount before calculating totals
    if discount_amount:
        Order.update_totals(order_id, 0.0, 0.0, discount_amount, 0.0)

    totals = calculate_order_total(order_id)
    Order.update_totals(
        order_id,
        subtotal=totals["subtotal"],
        tax_amount=totals["tax_amount"],
        discount_amount=discount_amount,
        total=totals["total"],
    )

    order = Order.find(order_id)
    return order  # type: ignore[return-value]


def get_order_by_id(order_id: int) -> dict:
    """
    Return a fully hydrated order dict.

    Called by:
      routes/orders.py → GET /orders/<id>
      services/payment_service.charge_order() (validates order before charging)
      OrderPage frontend
    """
    order = Order.find(order_id)
    if order is None:
        raise OrderNotFoundError(f"Order {order_id} not found")
    return order


def get_orders_for_user(user_id: int) -> list[dict]:
    """
    Return all orders for a user, newest first.

    Called by:
      routes/orders.py → GET /orders?user_id=...
      services/user_service.get_user_orders_summary()
      OrderPage frontend (order history list)
    """
    return Order.find_by_user(user_id)


def confirm_order(order_id: int) -> dict:
    """
    Transition an order from `pending` → `confirmed` after payment succeeds.

    Called by:
      services/payment_service.process_payment() (on PAYMENT_SUCCEEDED)
    """
    order = Order.find(order_id)
    if order is None:
        raise OrderNotFoundError(f"Order {order_id} not found")

    updated = Order.update_status(order_id, STATUS_CONFIRMED)
    return updated  # type: ignore[return-value]


def cancel_order(order_id: int) -> dict:
    """
    Cancel a pending or confirmed order and release reserved stock.

    Called by:
      routes/orders.py → DELETE /orders/<id>
      services/payment_service.refund_payment() (if order is refunded)
    """
    from services.inventory_service import release_item

    order = Order.find(order_id)
    if order is None:
        raise OrderNotFoundError(f"Order {order_id} not found")

    if order["status"] not in {STATUS_PENDING, STATUS_CONFIRMED}:
        raise ValueError(f"Cannot cancel order with status {order['status']!r}")

    # Release stock
    for item in order.get("items", []):
        release_item(product_id=item["product_id"], quantity=item["quantity"])

    updated = Order.update_status(order_id, STATUS_CANCELLED)
    return updated  # type: ignore[return-value]


def apply_discount_code(order_id: int, code: str) -> dict:
    """
    Apply a discount code to a pending order and recalculate totals.

    Supported codes (demo):
      SAVE10  → 10% off subtotal
      FLAT20  → $20 off
      WELCOME → 5% off for new customers

    Called by:
      routes/orders.py → POST /orders/<id>/discount
      Checkout frontend → discount code input field
    """
    order = Order.find(order_id)
    if order is None:
        raise OrderNotFoundError(f"Order {order_id} not found")
    if order["status"] != STATUS_PENDING:
        raise ValueError("Discount codes can only be applied to pending orders")

    # Calculate subtotal to compute percentage discounts
    temp = calculate_order_total(order_id)
    subtotal = temp["subtotal"]

    discount_map: dict[str, float] = {
        "SAVE10":  round(subtotal * 0.10, 2),
        "FLAT20":  20.00,
        "WELCOME": round(subtotal * 0.05, 2),
    }
    discount_amount = discount_map.get(code.upper(), 0.0)
    if discount_amount == 0.0:
        raise ValueError(f"Invalid or expired discount code: {code!r}")

    # Persist discount and recalculate
    Order.update_totals(order_id, subtotal, 0.0, discount_amount, 0.0)
    totals = calculate_order_total(order_id)
    Order.update_totals(
        order_id,
        subtotal=totals["subtotal"],
        tax_amount=totals["tax_amount"],
        discount_amount=discount_amount,
        total=totals["total"],
    )
    return Order.find(order_id)  # type: ignore[return-value]
