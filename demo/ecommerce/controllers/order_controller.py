"""
Demo E-Commerce — OrderController

Translates HTTP request data into OrderService calls and maps
service exceptions to HTTP status codes.

Blast-radius note: changes to OrderService.place_order() or
calculate_order_total() will require corresponding changes here,
propagating to routes/orders.py and all order-related tests.
"""

from __future__ import annotations

from services.order_service import (
    place_order,
    get_order_by_id,
    get_orders_for_user,
    cancel_order,
    apply_discount_code,
    calculate_order_total,
    OrderNotFoundError,
    InsufficientStockError,
)


class OrderController:
    """
    Controller for order operations.

    Responsibility: validate request data, call OrderService,
    return (response_dict, http_status_code) tuples.
    """

    @staticmethod
    def create(data: dict) -> tuple[dict, int]:
        """
        POST /orders — place a new order.

        Expected payload:
          { user_id, items: [{product_id, quantity}], shipping_address_id, discount_amount? }

        Called by:
          routes/orders.py → POST /orders
          Checkout frontend (final "Place Order" submit)
        """
        user_id = data.get("user_id")
        items = data.get("items", [])
        shipping_address_id = data.get("shipping_address_id")
        discount_amount = float(data.get("discount_amount", 0.0))

        if not user_id or not items or not shipping_address_id:
            return {"error": "user_id, items, and shipping_address_id are required"}, 400

        try:
            order = place_order(
                user_id=int(user_id),
                items=items,
                shipping_address_id=int(shipping_address_id),
                discount_amount=discount_amount,
            )
            return {"order": order, "message": "Order placed successfully"}, 201

        except InsufficientStockError as exc:
            return {"error": str(exc), "code": "insufficient_stock"}, 409
        except ValueError as exc:
            return {"error": str(exc)}, 400

    @staticmethod
    def get(order_id: int) -> tuple[dict, int]:
        """
        GET /orders/<id> — retrieve a single order with totals.

        Called by:
          routes/orders.py → GET /orders/<id>
          OrderPage frontend (order detail view)
          PaymentController (reads order before charging)
        """
        try:
            order = get_order_by_id(order_id)
            totals = calculate_order_total(order_id)
            return {"order": {**order, **totals}}, 200
        except OrderNotFoundError as exc:
            return {"error": str(exc)}, 404

    @staticmethod
    def list_for_user(user_id: int) -> tuple[dict, int]:
        """
        GET /orders?user_id=<id> — list orders for a user.

        Called by:
          routes/orders.py → GET /orders
          OrderPage frontend (order history)
          UserService.get_user_orders_summary()
        """
        orders = get_orders_for_user(user_id)
        return {"orders": orders, "count": len(orders)}, 200

    @staticmethod
    def cancel(order_id: int) -> tuple[dict, int]:
        """
        DELETE /orders/<id> — cancel an order.

        Called by:
          routes/orders.py → DELETE /orders/<id>
        """
        try:
            order = cancel_order(order_id)
            return {"order": order, "message": "Order cancelled"}, 200
        except OrderNotFoundError as exc:
            return {"error": str(exc)}, 404
        except ValueError as exc:
            return {"error": str(exc), "code": "invalid_status_transition"}, 409

    @staticmethod
    def apply_discount(order_id: int, data: dict) -> tuple[dict, int]:
        """
        POST /orders/<id>/discount — apply a discount code.

        Expected payload: { code }

        Called by:
          routes/orders.py → POST /orders/<id>/discount
          Checkout frontend (discount code input)
        """
        code = data.get("code", "").strip()
        if not code:
            return {"error": "Discount code is required"}, 400
        try:
            order = apply_discount_code(order_id, code)
            return {"order": order, "message": f"Discount code {code!r} applied"}, 200
        except OrderNotFoundError as exc:
            return {"error": str(exc)}, 404
        except ValueError as exc:
            return {"error": str(exc)}, 400
