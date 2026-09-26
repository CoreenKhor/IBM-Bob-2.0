# Automated Testing & Coverage Plan

## 1. Test Suite Summary

| Parameter | Details |
| :--- | :--- |
| **Component Under Test** | `[src/services/billing.ts](file:///src/services/billing.ts)` |
| **Test Framework** | Jest / Vitest / PyTest |
| **Total Test Cases Added** | `<count>` tests |
| **Coverage Delta** | From `42%` $\longrightarrow$ `94%` |
| **Execution Status** | `ALL PASSING (GREEN)` |

---

## 2. Test Scenarios Implemented

| Scenario ID | Test Case Description | Category | Expected Result |
| :--- | :--- | :--- | :--- |
| `TC-01` | Calculates tax for standard domestic order | Happy Path | Tax = 6% |
| `TC-02` | Applies promo discount code correctly | Business Logic | Deducts discount up to subtotal |
| `TC-03` | Rejects expired coupon code | Boundary / Error | Throws `CouponExpiredError` |
| `TC-04` | Handles network timeout from external payment gateway | Fault Injection | Retries 3x then falls back to queue |
| `TC-05` | Rejects negative order quantities | Input Validation | Returns 400 Bad Request |

---

## 3. Synthetic Test Data Fixture Sample

```typescript
export const createMockOrder = (overrides = {}) => ({
  id: 'ord_mock_12345',
  userId: 'usr_synthetic_01',
  items: [
    { sku: 'ITEM-A', unitPrice: 25.00, quantity: 2 }
  ],
  currency: 'USD',
  createdAt: new Date('2026-01-01T00:00:00Z'),
  ...overrides,
});
```

---

## 4. Execution Commands

```bash
# Run the specific generated test file
npm test -- tests/services/billing.test.ts --coverage

# Run in watch mode during development
npm test -- tests/services/billing.test.ts --watch
```
