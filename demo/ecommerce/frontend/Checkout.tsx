/**
 * Demo E-Commerce Frontend — Checkout Component
 *
 * Orchestrates the multi-step checkout flow:
 *   Step 1: Review cart items + apply discount code
 *   Step 2: Confirm shipping address (loaded from UserService)
 *   Step 3: Enter payment details (PaymentForm)
 *   Step 4: Order confirmation (reads from OrderPage)
 *
 * Blast-radius note: changes to OrderService.calculate_order_total()
 * (e.g. adding tax_rate or coupon_code) will break the totals display here.
 * Changes to PaymentService.process_payment() response shape will break
 * the confirmation step. Changes to User.default_address will break
 * the address pre-fill.
 *
 * Direct dependencies:
 *   - POST /orders          (OrderService via OrderController)
 *   - POST /orders/:id/discount  (OrderService.apply_discount_code)
 *   - POST /payments        (PaymentService via PaymentController)
 *   - GET  /users/:id       (UserService.get_user_profile)
 *   - <PaymentForm />       (renders payment card inputs)
 *   - <OrderPage />         (renders confirmation)
 */

import React, { useState, useEffect } from 'react';
import PaymentForm from './PaymentForm';
import OrderPage from './OrderPage';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface CartItem {
  product_id: number;
  name: string;
  price: number;
  quantity: number;
}

interface CheckoutTotals {
  subtotal: number;
  tax_amount: number;
  discount_amount: number;
  total: number;
}

interface ShippingAddress {
  id: number;
  line1: string;
  line2: string;
  city: string;
  state: string;
  zip_code: string;
  country: string;
}

interface CheckoutProps {
  userId: number;
  cartItems: CartItem[];
  onComplete: (orderId: number) => void;
}

type CheckoutStep = 'review' | 'address' | 'payment' | 'confirmation';

// ---------------------------------------------------------------------------
// Helper: fetch wrapper
// ---------------------------------------------------------------------------
const API_BASE = '/api';

async function apiPost<T>(path: string, body: object): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  const json = await res.json();
  if (!res.ok) throw new Error(json.error ?? `Request failed: ${res.status}`);
  return json;
}

async function apiGet<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`);
  const json = await res.json();
  if (!res.ok) throw new Error(json.error ?? `Request failed: ${res.status}`);
  return json;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

const STEPS: CheckoutStep[] = ['review', 'address', 'payment', 'confirmation'];

export default function Checkout({ userId, cartItems, onComplete }: CheckoutProps) {
  const [step, setStep] = useState<CheckoutStep>('review');
  const [orderId, setOrderId] = useState<number | null>(null);
  const [totals, setTotals] = useState<CheckoutTotals>({
    subtotal: 0,
    tax_amount: 0,
    discount_amount: 0,
    total: 0,
  });
  const [address, setAddress] = useState<ShippingAddress | null>(null);
  const [discountCode, setDiscountCode] = useState('');
  const [discountMessage, setDiscountMessage] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  // Calculate local subtotal from cart for display before order is created
  const localSubtotal = cartItems.reduce(
    (sum, item) => sum + item.price * item.quantity,
    0
  );

  // Load default shipping address
  useEffect(() => {
    apiGet<{ user: { default_address: ShippingAddress } }>(`/users/${userId}`)
      .then((data) => setAddress(data.user.default_address))
      .catch(() => {/* no address pre-filled */});
  }, [userId]);

  // Step 1: Place the order (creates it in PENDING state)
  const handlePlaceOrder = async () => {
    if (!address) {
      setError('Please add a shipping address before continuing.');
      return;
    }
    setLoading(true);
    setError('');
    try {
      // Blast-radius target: place_order signature change breaks this call
      const data = await apiPost<{ order: { id: number } & CheckoutTotals }>(
        '/orders',
        {
          user_id: userId,
          items: cartItems.map((i) => ({
            product_id: i.product_id,
            quantity: i.quantity,
          })),
          shipping_address_id: address.id,
        }
      );
      const newOrderId = data.order.id;
      setOrderId(newOrderId);
      setTotals({
        subtotal: data.order.subtotal,
        tax_amount: data.order.tax_amount,
        discount_amount: data.order.discount_amount,
        total: data.order.total,
      });
      setStep('payment');
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to place order');
    } finally {
      setLoading(false);
    }
  };

  // Apply discount code to the pending order
  const handleApplyDiscount = async () => {
    if (!orderId || !discountCode.trim()) return;
    setLoading(true);
    setDiscountMessage('');
    try {
      // Blast-radius target: apply_discount_code return shape change breaks this
      const data = await apiPost<{ order: { id: number } & CheckoutTotals }>(
        `/orders/${orderId}/discount`,
        { code: discountCode }
      );
      setTotals({
        subtotal: data.order.subtotal,
        tax_amount: data.order.tax_amount,
        discount_amount: data.order.discount_amount,
        total: data.order.total,
      });
      setDiscountMessage(`Code "${discountCode}" applied!`);
    } catch (e) {
      setDiscountMessage(e instanceof Error ? e.message : 'Invalid code');
    } finally {
      setLoading(false);
    }
  };

  // Payment success callback from PaymentForm
  const handlePaymentSuccess = () => {
    if (orderId) {
      onComplete(orderId);
      setStep('confirmation');
    }
  };

  const stepIndex = STEPS.indexOf(step);

  return (
    <div className="max-w-2xl mx-auto p-6 space-y-6">
      {/* Progress bar */}
      <div className="flex items-center gap-2 text-sm">
        {(['Review', 'Address', 'Payment', 'Confirmation'] as const).map(
          (label, idx) => (
            <React.Fragment key={label}>
              <span
                className={`font-medium ${
                  idx <= stepIndex ? 'text-blue-600' : 'text-gray-400'
                }`}
              >
                {idx + 1}. {label}
              </span>
              {idx < 3 && <span className="text-gray-300">›</span>}
            </React.Fragment>
          )
        )}
      </div>

      {error && (
        <div className="p-3 bg-red-50 border border-red-200 rounded text-sm text-red-700">
          {error}
        </div>
      )}

      {/* ── Step 1: Review ── */}
      {step === 'review' && (
        <div className="space-y-4">
          <h2 className="text-lg font-semibold">Review Your Order</h2>

          <ul className="divide-y divide-gray-100 border border-gray-200 rounded-lg">
            {cartItems.map((item) => (
              <li key={item.product_id} className="flex justify-between px-4 py-3 text-sm">
                <span>
                  {item.name}{' '}
                  <span className="text-gray-400">× {item.quantity}</span>
                </span>
                <span className="font-medium">
                  ${(item.price * item.quantity).toFixed(2)}
                </span>
              </li>
            ))}
          </ul>

          {/* Totals summary (pre-order — local calculation) */}
          <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 text-sm space-y-1">
            <div className="flex justify-between">
              <span className="text-gray-600">Subtotal</span>
              <span>${localSubtotal.toFixed(2)}</span>
            </div>
            <div className="flex justify-between text-xs text-gray-400">
              <span>Tax (8%) and discounts calculated at next step</span>
            </div>
          </div>

          {/* Shipping address preview */}
          {address && (
            <div className="text-sm text-gray-600 border border-gray-200 rounded-lg p-4">
              <p className="font-medium text-gray-800 mb-1">Ships to:</p>
              <p>{address.line1}</p>
              {address.line2 && <p>{address.line2}</p>}
              <p>{address.city}, {address.state} {address.zip_code}</p>
            </div>
          )}

          <button
            onClick={handlePlaceOrder}
            disabled={loading || cartItems.length === 0}
            className="w-full py-3 bg-blue-600 text-white font-semibold rounded-lg hover:bg-blue-700 disabled:opacity-40"
          >
            {loading ? 'Creating order…' : 'Continue to Payment'}
          </button>
        </div>
      )}

      {/* ── Step 2: Payment ── */}
      {step === 'payment' && orderId && (
        <div className="space-y-4">
          <h2 className="text-lg font-semibold">Payment</h2>

          {/* Live totals from the server (post-order-creation) */}
          {/* Blast-radius: calculate_order_total return shape change breaks this */}
          <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 text-sm space-y-1">
            <div className="flex justify-between">
              <span className="text-gray-600">Subtotal</span>
              <span>${totals.subtotal.toFixed(2)}</span>
            </div>
            {totals.discount_amount > 0 && (
              <div className="flex justify-between text-green-600">
                <span>Discount</span>
                <span>−${totals.discount_amount.toFixed(2)}</span>
              </div>
            )}
            <div className="flex justify-between">
              <span className="text-gray-600">Tax</span>
              <span>${totals.tax_amount.toFixed(2)}</span>
            </div>
            <div className="flex justify-between font-semibold text-base border-t border-gray-200 pt-2 mt-1">
              <span>Total</span>
              <span>${totals.total.toFixed(2)}</span>
            </div>
          </div>

          {/* Discount code input */}
          <div className="flex gap-2">
            <input
              type="text"
              value={discountCode}
              onChange={(e) => setDiscountCode(e.target.value)}
              placeholder="Discount code (SAVE10, FLAT20, WELCOME)"
              className="flex-1 px-3 py-2 border border-gray-300 rounded text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
            />
            <button
              onClick={handleApplyDiscount}
              disabled={loading}
              className="px-4 py-2 bg-gray-100 hover:bg-gray-200 text-sm font-medium rounded border border-gray-300"
            >
              Apply
            </button>
          </div>
          {discountMessage && (
            <p className={`text-sm ${discountMessage.includes('!') ? 'text-green-600' : 'text-red-600'}`}>
              {discountMessage}
            </p>
          )}

          {/* PaymentForm handles card input and POST /payments */}
          {/* Blast-radius: PaymentService.process_payment() changes break this */}
          <PaymentForm
            orderId={orderId}
            userId={userId}
            amount={totals.total}
            onSuccess={handlePaymentSuccess}
            onError={(msg) => setError(msg)}
          />
        </div>
      )}

      {/* ── Step 3: Confirmation ── */}
      {step === 'confirmation' && orderId && (
        <OrderPage orderId={orderId} userId={userId} />
      )}
    </div>
  );
}
