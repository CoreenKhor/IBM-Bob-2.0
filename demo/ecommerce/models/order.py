"""
Demo E-Commerce — Order & OrderItem Models

Represents the `orders` and `order_items` tables.

Relationships:
  - Order belongs-to User (via user_id)
  - Order has-many OrderItems (via order_items.order_id)
  - Order has-one Payment (via payments.order_id)
  - OrderItem belongs-to Product (via product_id)

Blast-radius note: changes to Order (e.g. adding a `discount_code` or
`tax_rate` field) cascade to:
  OrderService.calculate_order_total()  → routes/orders.py
  PaymentService.process_payment()      → routes/payments.py
  Checkout (frontend)                   → PaymentForm (frontend)
  test_order_service.py, test_payment_service.py, test_checkout.py
"""

from __future__ import annotations
from datetime import datetime, timezone
from typing import Optional

# ---------------------------------------------------------------------------
# Order status constants
# ---------------------------------------------------------------------------
STATUS_PENDING    = "pending"
STATUS_CONFIRMED  = "confirmed"
STATUS_PAID       = "paid"
STATUS_SHIPPED    = "shipped"
STATUS_DELIVERED  = "delivered"
STATUS_CANCELLED  = "cancelled"
STATUS_REFUNDED   = "refunded"

VALID_STATUSES = {
    STATUS_PENDING, STATUS_CONFIRMED, STATUS_PAID,
    STATUS_SHIPPED, STATUS_DELIVERED, STATUS_CANCELLED, STATUS_REFUNDED,
}

# ---------------------------------------------------------------------------
# In-memory store
# ---------------------------------------------------------------------------
_orders: dict[int, dict] = {
    1: {
        "id": 1,
        "user_id": 1,
        "status": STATUS_PAID,
        "subtotal": 194.97,
        "tax_amount": 15.60,
        "discount_amount": 0.0,
        "total": 210.57,
        "shipping_address_id": 1,
        "created_at": "2024-06-01T09:00:00Z",
        "updated_at": "2024-06-01T09:05:00Z",
    },
    2: {
        "id": 2,
        "user_id": 2,
        "status": STATUS_PENDING,
        "subtotal": 359.97,
        "tax_amount": 28.80,
        "discount_amount": 36.00,
        "total": 352.77,
        "shipping_address_id": 2,
        "created_at": "2024-06-15T14:00:00Z",
        "updated_at": "2024-06-15T14:00:00Z",
    },
    3: {
        "id": 3,
        "user_id": 1,
        "status": STATUS_CONFIRMED,
        "subtotal": 49.99,
        "tax_amount": 4.00,
        "discount_amount": 0.0,
        "total": 53.99,
        "shipping_address_id": 1,
        "created_at": "2024-07-01T11:30:00Z",
        "updated_at": "2024-07-01T11:31:00Z",
    },
}

_order_items: dict[int, list[dict]] = {
    1: [
        {"id": 1, "order_id": 1, "product_id": 101, "quantity": 2, "unit_price": 79.99},
        {"id": 2, "order_id": 1, "product_id": 102, "quantity": 1, "unit_price": 34.99},
    ],
    2: [
        {"id": 3, "order_id": 2, "product_id": 103, "quantity": 3, "unit_price": 119.99},
    ],
    3: [
        {"id": 4, "order_id": 3, "product_id": 104, "quantity": 1, "unit_price": 49.99},
    ],
}

_next_order_id = 10
_next_item_id  = 20


class Order:
    """
    ORM-style model for the `orders` table.

    Central node in the blast-radius graph: referenced by OrderService,
    PaymentService, PaymentController, OrderController, and all checkout flows.
    """

    @staticmethod
    def find(order_id: int) -> Optional[dict]:
        """SELECT * FROM orders WHERE id = :order_id."""
        order = _orders.get(order_id)
        if order is None:
            return None
        # Attach items inline (mirrors a JOIN in SQL)
        return {**order, "items": _order_items.get(order_id, [])}

    @staticmethod
    def find_by_user(user_id: int) -> list[dict]:
        """SELECT * FROM orders WHERE user_id = :user_id ORDER BY created_at DESC."""
        return [
            {**o, "items": _order_items.get(o["id"], [])}
            for o in sorted(_orders.values(), key=lambda x: x["created_at"], reverse=True)
            if o["user_id"] == user_id
        ]

    @staticmethod
    def create(user_id: int, items: list[dict], shipping_address_id: int) -> int:
        """
        INSERT INTO orders (...) VALUES (...); INSERT INTO order_items ...
        Returns the new order_id.
        """
        global _next_order_id, _next_item_id
        now = datetime.now(timezone.utc).isoformat()
        order_id = _next_order_id
        _orders[order_id] = {
            "id": order_id,
            "user_id": user_id,
            "status": STATUS_PENDING,
            "subtotal": 0.0,
            "tax_amount": 0.0,
            "discount_amount": 0.0,
            "total": 0.0,
            "shipping_address_id": shipping_address_id,
            "created_at": now,
            "updated_at": now,
        }
        order_items = []
        for item in items:
            order_items.append({
                "id": _next_item_id,
                "order_id": order_id,
                "product_id": item["product_id"],
                "quantity": item["quantity"],
                "unit_price": item.get("unit_price", 0.0),
            })
            _next_item_id += 1
        _order_items[order_id] = order_items
        _next_order_id += 1
        return order_id

    @staticmethod
    def update_totals(order_id: int, subtotal: float, tax_amount: float,
                      discount_amount: float, total: float) -> None:
        """UPDATE orders SET subtotal=..., tax_amount=..., total=... WHERE id=:order_id."""
        if order_id in _orders:
            now = datetime.now(timezone.utc).isoformat()
            _orders[order_id].update({
                "subtotal": subtotal,
                "tax_amount": tax_amount,
                "discount_amount": discount_amount,
                "total": total,
                "updated_at": now,
            })

    @staticmethod
    def update_status(order_id: int, status: str) -> Optional[dict]:
        """UPDATE orders SET status=:status WHERE id=:order_id."""
        if status not in VALID_STATUSES:
            raise ValueError(f"Invalid order status: {status!r}")
        order = _orders.get(order_id)
        if order is None:
            return None
        order["status"] = status
        order["updated_at"] = datetime.now(timezone.utc).isoformat()
        return order

    @staticmethod
    def all() -> list[dict]:
        """SELECT * FROM orders ORDER BY created_at DESC."""
        return [
            {**o, "items": _order_items.get(o["id"], [])}
            for o in sorted(_orders.values(), key=lambda x: x["created_at"], reverse=True)
        ]


class OrderItem:
    """ORM-style model for the `order_items` table."""

    @staticmethod
    def find_by_order(order_id: int) -> list[dict]:
        """SELECT * FROM order_items WHERE order_id = :order_id."""
        return _order_items.get(order_id, [])
