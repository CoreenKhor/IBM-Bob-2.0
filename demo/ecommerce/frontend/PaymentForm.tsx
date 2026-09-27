/**
 * Demo E-Commerce Frontend — PaymentForm Component
 *
 * Renders credit card input fields and submits to POST /payments.
 * Used inside Checkout (Step 2 — Payment).
 *
 * Blast-radius note: changes to PaymentService.process_payment() shape —
 * e.g. requiring `billing_address`, changing response fields, or altering
 * the `payment_method` enum values — will break this component and require
 * changes to:
 *   - Checkout.tsx (reads payment result, updates totals display)
 *   - OrderPage.tsx (displays payment confirmation banner)
 *   - test_checkout.py (simulates the full checkout flow)
 *   - test_payment_controller.py (tests the endpoint this POSTs to)
 *
 * Direct dependencies:
 *   - POST /payments  (PaymentController.charge → PaymentService.process_payment)
 *   - Payment model: { status, card_last_four, gateway_transaction_id }
 */

import { useState } from 'react';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface PaymentFormProps {
  orderId: number;
  userId: number;
  amount: number;
  onSuccess: () => void;
  onError: (message: string) => void;
}

interface PaymentResponse {
  payment: {
    id: number;
    order_id: number;
    status: string;
    gateway_transaction_id: string;
    card_last_four: string;
    amount: number;
  };
  message: string;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatCardNumber(raw: string): string {
  return raw.replace(/\D/g, '').slice(0, 16).replace(/(.{4})/g, '$1 ').trim();
}

function formatExpiry(raw: string): string {
  const digits = raw.replace(/\D/g, '').slice(0, 4);
  return digits.length > 2 ? `${digits.slice(0, 2)}/${digits.slice(2)}` : digits;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function PaymentForm({
  orderId,
  userId,
  amount,
  onSuccess,
  onError,
}: PaymentFormProps) {
  const [cardNumber, setCardNumber] = useState('');
  const [expiry, setExpiry] = useState('');
  const [cvv, setCvv] = useState('');
  const [cardHolder, setCardHolder] = useState('');
  const [paymentMethod, setPaymentMethod] = useState<'card' | 'paypal' | 'wallet'>('card');
  const [loading, setLoading] = useState(false);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});

  const validate = (): boolean => {
    const errors: Record<string, string> = {};
    if (paymentMethod === 'card') {
      const digits = cardNumber.replace(/\s/g, '');
      if (digits.length !== 16) errors.cardNumber = 'Card number must be 16 digits';
      if (!/^\d{2}\/\d{2}$/.test(expiry)) errors.expiry = 'Expiry must be MM/YY';
      if (cvv.length < 3) errors.cvv = 'CVV must be 3–4 digits';
      if (!cardHolder.trim()) errors.cardHolder = 'Cardholder name is required';
    }
    setFieldErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!validate()) return;

    setLoading(true);
    try {
      // Blast-radius target: process_payment() signature change → this payload breaks
      const res = await fetch('/api/payments', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          order_id: orderId,
          user_id: userId,
          payment_method: paymentMethod,
          card_last_four: cardNumber.replace(/\s/g, '').slice(-4),
          currency: 'USD',
        }),
      });

      const json = (await res.json()) as PaymentResponse | { error: string; decline_code?: string };

      if (!res.ok) {
        const errJson = json as { error: string; decline_code?: string };
        onError(errJson.error ?? 'Payment failed');
        return;
      }

      onSuccess();
    } catch {
      onError('Network error — please try again');
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {/* Payment method selector */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Payment Method
        </label>
        <div className="flex gap-3">
          {(['card', 'paypal', 'wallet'] as const).map((method) => (
            <button
              key={method}
              type="button"
              onClick={() => setPaymentMethod(method)}
              className={`px-4 py-2 text-sm rounded-lg border capitalize ${
                paymentMethod === method
                  ? 'border-blue-500 bg-blue-50 text-blue-700 font-medium'
                  : 'border-gray-300 text-gray-600 hover:bg-gray-50'
              }`}
            >
              {method === 'card' ? '💳 Card' : method === 'paypal' ? '🅿 PayPal' : '👛 Wallet'}
            </button>
          ))}
        </div>
      </div>

      {/* Card fields — only shown for card method */}
      {paymentMethod === 'card' && (
        <>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Cardholder Name
            </label>
            <input
              type="text"
              value={cardHolder}
              onChange={(e) => setCardHolder(e.target.value)}
              placeholder="Alice Johnson"
              className="w-full px-3 py-2 border border-gray-300 rounded text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
            />
            {fieldErrors.cardHolder && (
              <p className="text-xs text-red-600 mt-1">{fieldErrors.cardHolder}</p>
            )}
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Card Number
            </label>
            <input
              type="text"
              value={cardNumber}
              onChange={(e) => setCardNumber(formatCardNumber(e.target.value))}
              placeholder="4242 4242 4242 4242"
              inputMode="numeric"
              maxLength={19}
              className="w-full px-3 py-2 border border-gray-300 rounded font-mono text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
            />
            {fieldErrors.cardNumber && (
              <p className="text-xs text-red-600 mt-1">{fieldErrors.cardNumber}</p>
            )}
            <p className="text-xs text-gray-400 mt-1">
              Test: 4242… succeeds · 0000… declined · 1111… insufficient funds
            </p>
          </div>

          <div className="flex gap-4">
            <div className="flex-1">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Expiry
              </label>
              <input
                type="text"
                value={expiry}
                onChange={(e) => setExpiry(formatExpiry(e.target.value))}
                placeholder="MM/YY"
                maxLength={5}
                className="w-full px-3 py-2 border border-gray-300 rounded text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
              />
              {fieldErrors.expiry && (
                <p className="text-xs text-red-600 mt-1">{fieldErrors.expiry}</p>
              )}
            </div>
            <div className="w-28">
              <label className="block text-sm font-medium text-gray-700 mb-1">CVV</label>
              <input
                type="text"
                value={cvv}
                onChange={(e) => setCvv(e.target.value.replace(/\D/g, '').slice(0, 4))}
                placeholder="123"
                inputMode="numeric"
                maxLength={4}
                className="w-full px-3 py-2 border border-gray-300 rounded text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
              />
              {fieldErrors.cvv && (
                <p className="text-xs text-red-600 mt-1">{fieldErrors.cvv}</p>
              )}
            </div>
          </div>
        </>
      )}

      {/* Non-card methods — placeholder */}
      {paymentMethod !== 'card' && (
        <div className="p-4 bg-yellow-50 border border-yellow-200 rounded text-sm text-yellow-800">
          {paymentMethod === 'paypal'
            ? 'You will be redirected to PayPal to complete your payment.'
            : 'Your saved wallet balance will be charged.'}
        </div>
      )}

      {/* Amount display */}
      <div className="flex justify-between items-center py-2 border-t border-gray-100">
        <span className="text-sm text-gray-600">Amount to charge</span>
        <span className="text-lg font-bold text-gray-900">${amount.toFixed(2)}</span>
      </div>

      <button
        type="submit"
        disabled={loading}
        className="w-full py-3 bg-green-600 text-white font-semibold rounded-lg hover:bg-green-700 disabled:opacity-40 transition-colors"
      >
        {loading ? 'Processing…' : `Pay $${amount.toFixed(2)}`}
      </button>
    </form>
  );
}
