/**
 * Demo E-Commerce Frontend — OrderPage Component
 *
 * Displays a single order's full detail including:
 *   - Order status badge
 *   - Line items with quantities and unit prices
 *   - Subtotal / discount / tax / total breakdown
 *   - Payment confirmation section (reads from GET /payments/order/:id)
 *   - Order history list (reads from GET /orders?user_id=:id)
 *
 * Blast-radius note: changes to Order model fields (e.g. adding
 * `estimated_delivery`, changing `status` enum values) will break
 * the status badge rendering here. Changes to Payment.gateway_transaction_id
 * or payment.status will break the payment confirmation section.
 * Changes to OrderService.get_orders_for_user() return shape will break
 * the order history list.
 *
 * Direct dependencies:
 *   - GET /orders/:id           (OrderController.get → OrderService)
 *   - GET /payments/order/:id   (PaymentController.get_payment → PaymentService)
 *   - GET /orders?user_id=:id   (OrderController.list_for_user → OrderService)
 *   - calculate_order_total()   (totals embedded in order response)
 */

import { useState, useEffect } from 'react';

// ---------------------------------------------------------------------------
// Types (mirror BlastRadiusReport types for consistency)
// ---------------------------------------------------------------------------

interface OrderItem {
  id: number;
  product_id: number;
  quantity: number;
  unit_price: number;
}

interface Order {
  id: number;
  user_id: number;
  status: string;
  subtotal: number;
  tax_amount: number;
  discount_amount: number;
  total: number;
  shipping_address_id: number;
  items: OrderItem[];
  created_at: string;
}

interface Payment {
  id: number;
  order_id: number;
  status: string;
  payment_method: string;
  card_last_four: string;
  amount: number;
  gateway_transaction_id: string | null;
  created_at: string;
}

interface OrderPageProps {
  orderId: number;
  userId: number;
}

// ---------------------------------------------------------------------------
// Status display helpers
// Blast-radius: adding/renaming a status in models/order.py STATUS_* constants
// breaks these maps and requires a frontend update.
// ---------------------------------------------------------------------------

const STATUS_LABELS: Record<string, string> = {
  pending:    'Pending',
  confirmed:  'Confirmed',
  paid:       'Paid',
  shipped:    'Shipped',
  delivered:  'Delivered',
  cancelled:  'Cancelled',
  refunded:   'Refunded',
};

const STATUS_STYLES: Record<string, string> = {
  pending:    'bg-yellow-100 text-yellow-800',
  confirmed:  'bg-blue-100 text-blue-800',
  paid:       'bg-green-100 text-green-800',
  shipped:    'bg-indigo-100 text-indigo-800',
  delivered:  'bg-emerald-100 text-emerald-800',
  cancelled:  'bg-gray-100 text-gray-600',
  refunded:   'bg-red-100 text-red-800',
};

const PAYMENT_STATUS_LABELS: Record<string, string> = {
  pending:    'Pending',
  processing: 'Processing',
  succeeded:  '✓ Paid',
  failed:     '✗ Failed',
  refunded:   'Refunded',
  cancelled:  'Cancelled',
};

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function OrderPage({ orderId, userId }: OrderPageProps) {
  const [order, setOrder] = useState<Order | null>(null);
  const [payment, setPayment] = useState<Payment | null>(null);
  const [history, setHistory] = useState<Order[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      setError('');
      try {
        // Parallel fetches — changes to any endpoint response shape break parsing below
        const [orderRes, paymentRes, historyRes] = await Promise.all([
          fetch(`/api/orders/${orderId}`),
          fetch(`/api/payments/order/${orderId}`),
          fetch(`/api/orders?user_id=${userId}`),
        ]);

        // Blast-radius: OrderController.get() return shape change → parse error
        const orderData = await orderRes.json();
        if (orderRes.ok) setOrder(orderData.order);

        // Blast-radius: PaymentController.get_payment() return shape change → parse error
        const paymentData = await paymentRes.json();
        if (paymentRes.ok) setPayment(paymentData.payment);

        // Blast-radius: get_orders_for_user() return shape change → history fails
        const historyData = await historyRes.json();
        if (historyRes.ok) setHistory(historyData.orders ?? []);
      } catch {
        setError('Failed to load order details');
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [orderId, userId]);

  if (loading) {
    return (
      <div className="text-center py-12 text-gray-400">
        <div className="text-4xl mb-4 animate-pulse">📦</div>
        <p>Loading order details…</p>
      </div>
    );
  }

  if (error || !order) {
    return (
      <div className="p-4 bg-red-50 border border-red-200 rounded text-sm text-red-700">
        {error || 'Order not found'}
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Confirmation banner */}
      <div className="bg-green-50 border border-green-200 rounded-lg p-5 text-center">
        <div className="text-3xl mb-2">🎉</div>
        <h2 className="text-lg font-bold text-green-800">Order Placed Successfully!</h2>
        <p className="text-sm text-green-700 mt-1">
          Order #{order.id} — {new Date(order.created_at).toLocaleDateString()}
        </p>
      </div>

      {/* Order status */}
      <div className="bg-white border border-gray-200 rounded-lg p-5">
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-semibold text-gray-900">Order #{order.id}</h3>
          <span
            className={`px-3 py-1 rounded-full text-xs font-semibold ${
              STATUS_STYLES[order.status] ?? 'bg-gray-100 text-gray-600'
            }`}
          >
            {STATUS_LABELS[order.status] ?? order.status}
          </span>
        </div>

        {/* Line items */}
        <ul className="divide-y divide-gray-100 mb-4">
          {order.items.map((item) => (
            <li key={item.id} className="flex justify-between py-2 text-sm">
              <span className="text-gray-700">
                Product #{item.product_id}{' '}
                <span className="text-gray-400">× {item.quantity}</span>
              </span>
              <span className="font-medium">
                ${(item.unit_price * item.quantity).toFixed(2)}
              </span>
            </li>
          ))}
        </ul>

        {/* Totals — Blast-radius: calculate_order_total() shape change → values wrong */}
        <div className="text-sm space-y-1 border-t border-gray-100 pt-3">
          <div className="flex justify-between text-gray-600">
            <span>Subtotal</span>
            <span>${order.subtotal.toFixed(2)}</span>
          </div>
          {order.discount_amount > 0 && (
            <div className="flex justify-between text-green-600">
              <span>Discount</span>
              <span>−${order.discount_amount.toFixed(2)}</span>
            </div>
          )}
          <div className="flex justify-between text-gray-600">
            <span>Tax (8%)</span>
            <span>${order.tax_amount.toFixed(2)}</span>
          </div>
          <div className="flex justify-between font-bold text-gray-900 text-base border-t border-gray-200 pt-2">
            <span>Total</span>
            <span>${order.total.toFixed(2)}</span>
          </div>
        </div>
      </div>

      {/* Payment details — Blast-radius: payment model changes break this section */}
      {payment && (
        <div className="bg-white border border-gray-200 rounded-lg p-5">
          <h3 className="font-semibold text-gray-900 mb-3">Payment</h3>
          <dl className="text-sm space-y-2">
            <div className="flex justify-between">
              <dt className="text-gray-500">Status</dt>
              <dd className="font-medium">
                {PAYMENT_STATUS_LABELS[payment.status] ?? payment.status}
              </dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-gray-500">Method</dt>
              <dd className="capitalize">{payment.payment_method}</dd>
            </div>
            {payment.card_last_four && (
              <div className="flex justify-between">
                <dt className="text-gray-500">Card</dt>
                <dd className="font-mono">•••• {payment.card_last_four}</dd>
              </div>
            )}
            {payment.gateway_transaction_id && (
              <div className="flex justify-between">
                <dt className="text-gray-500">Transaction ID</dt>
                <dd className="font-mono text-xs text-gray-600">
                  {payment.gateway_transaction_id}
                </dd>
              </div>
            )}
            <div className="flex justify-between font-semibold">
              <dt>Amount Charged</dt>
              <dd>${payment.amount.toFixed(2)}</dd>
            </div>
          </dl>
        </div>
      )}

      {/* Order history */}
      {history.length > 1 && (
        <div className="bg-white border border-gray-200 rounded-lg p-5">
          <h3 className="font-semibold text-gray-900 mb-3">
            Your Orders ({history.length})
          </h3>
          <ul className="divide-y divide-gray-100">
            {history.slice(0, 5).map((o) => (
              <li key={o.id} className="flex justify-between items-center py-2 text-sm">
                <div>
                  <span className="font-medium">Order #{o.id}</span>
                  <span className="text-gray-400 ml-2">
                    {new Date(o.created_at).toLocaleDateString()}
                  </span>
                </div>
                <div className="flex items-center gap-3">
                  <span
                    className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                      STATUS_STYLES[o.status] ?? 'bg-gray-100 text-gray-600'
                    }`}
                  >
                    {STATUS_LABELS[o.status] ?? o.status}
                  </span>
                  <span className="font-semibold">${o.total.toFixed(2)}</span>
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
