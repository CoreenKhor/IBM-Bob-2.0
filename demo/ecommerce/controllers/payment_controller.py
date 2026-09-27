"""
Demo E-Commerce — PaymentController

Translates HTTP request data into PaymentService calls and maps
service exceptions to HTTP status codes.

This is the direct bridge between the Flask routes and PaymentService.
Every public method here is called by exactly one route handler.

Blast-radius note: changes to PaymentService.process_payment() signature
or exception types will require corresponding changes here, propagating to
routes/payments.py and all payment-related tests.
"""

from __future__ import annotations

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


class PaymentController:
    """
    Controller for payment operations.

    Responsibility: validate request data, call PaymentService,
    return (response_dict, http_status_code) tuples.
    """

    @staticmethod
    def charge(data: dict) -> tuple[dict, int]:
        """
        POST /payments — initiate a payment for an order.

        Expected payload:
          { order_id, user_id, payment_method, card_last_four?, currency? }

        Returns (payment_dict, 201) on success.
        Returns (error_dict, 4xx) on failure.
        """
        order_id = data.get("order_id")
        user_id = data.get("user_id")
        payment_method = data.get("payment_method", "")
        card_last_four = data.get("card_last_four", "")
        currency = data.get("currency", "USD")

        if not order_id or not user_id:
            return {"error": "order_id and user_id are required"}, 400

        try:
            payment = process_payment(
                order_id=int(order_id),
                user_id=int(user_id),
                payment_method=payment_method,
                card_last_four=str(card_last_four),
                currency=currency,
            )
            return {"payment": payment, "message": "Payment successful"}, 201

        except InvalidPaymentMethodError as exc:
            return {"error": str(exc), "code": "invalid_payment_method"}, 400
        except PaymentAlreadyProcessedError as exc:
            return {"error": str(exc), "code": "already_paid"}, 409
        except PaymentDeclinedError as exc:
            return {
                "error": str(exc),
                "code": "payment_declined",
                "decline_code": exc.decline_code,
            }, 402
        except ValueError as exc:
            return {"error": str(exc)}, 404

    @staticmethod
    def get_payment(order_id: int) -> tuple[dict, int]:
        """
        GET /payments/order/<order_id> — retrieve payment details for an order.

        Called by:
          OrderPage frontend — displays confirmation banner
          PaymentForm — shows receipt after successful charge
        """
        try:
            payment = get_payment_for_order(order_id)
            return {"payment": payment}, 200
        except PaymentNotFoundError as exc:
            return {"error": str(exc)}, 404

    @staticmethod
    def refund(order_id: int, data: dict) -> tuple[dict, int]:
        """
        POST /payments/order/<order_id>/refund — refund a completed payment.

        Expected payload: { reason? }

        Called by:
          routes/payments.py → POST /payments/order/<id>/refund
        """
        reason = data.get("reason", "")
        try:
            refunded = refund_payment(order_id=order_id, reason=reason)
            return {"payment": refunded, "message": "Refund processed"}, 200
        except PaymentNotFoundError as exc:
            return {"error": str(exc)}, 404
        except RefundError as exc:
            return {"error": str(exc), "code": "refund_error"}, 409

    @staticmethod
    def history(user_id: int) -> tuple[dict, int]:
        """
        GET /payments?user_id=<id> — payment history for a user.

        Called by:
          routes/payments.py → GET /payments
          OrderPage frontend (payment history tab)
        """
        payments = get_payment_history(user_id)
        return {"payments": payments, "count": len(payments)}, 200
