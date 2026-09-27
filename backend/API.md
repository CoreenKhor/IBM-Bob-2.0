# Change Blast Radius Analyzer — API Reference

> Base URL: `http://localhost:5000/api`  
> All endpoints return `Content-Type: application/json`.  
> CORS is open (`*`) for all `/api/*` routes — the Vite dev server on `:5173` can call directly.

---

## Table of Contents

1. [Health Check](#1-health-check)
2. [File Tree](#2-file-tree)
3. [Analyze Schema](#3-analyze-schema)
4. [**POST /analyze** — Core endpoint](#4-post-analyze--core-endpoint)
5. [Symbols](#5-symbols)
6. [Graph (codebase index)](#6-graph)
7. [Error Response Shape](#7-error-response-shape)
8. [Example: PaymentService scenario](#8-full-example--paymentservice)
9. [Frontend Integration](#9-frontend-integration)

---

## 1. Health Check

```
GET /api/health
```

**Response 200**
```json
{ "status": "ok", "service": "blast-radius-analyzer" }
```

---

## 2. File Tree

```
GET /api/tree
```

Returns the file tree of `demo/ecommerce/` for rendering in the sidebar.

**Response 200**
```json
{
  "root": "demo/ecommerce",
  "files": [
    { "path": "controllers/order_controller.py", "type": "file" },
    { "path": "controllers",                     "type": "dir"  }
  ]
}
```

---

## 3. Analyze Schema

```
GET /api/analyze/schema
```

Returns the JSON schema for the `POST /api/analyze` request body.  
Use this to populate dropdown menus and validate forms in the frontend.

**Response 200**
```json
{
  "ok": true,
  "schema": {
    "description": "POST /api/analyze request body",
    "type": "object",
    "required": ["target_file", "target_symbol"],
    "properties": { ... }
  },
  "valid_change_types": [
    "api_change", "deletion", "general", "new_feature",
    "refactor", "schema_change", "signature_change"
  ]
}
```

---

## 4. POST /analyze — Core Endpoint

```
POST /api/analyze
Content-Type: application/json
```

Runs a full Change Blast Radius Analysis for the specified symbol and returns a `BlastRadiusReport`.

### Request Body

| Field               | Type   | Required | Default   | Description |
|---------------------|--------|----------|-----------|-------------|
| `target_file`       | string | ✅        | —         | Path relative to `demo/ecommerce/` e.g. `"services/payment_service.py"` |
| `target_symbol`     | string | ✅        | —         | Name of the function or class e.g. `"process_payment"` |
| `change_description`| string | ❌        | `""`      | Free-text description of the proposed change — enriches risk scoring |
| `change_type`       | string | ❌        | `"general"` | One of the valid change types listed below |

**Valid `change_type` values**

| Value              | When to use |
|--------------------|-------------|
| `general`          | Default — no specific category |
| `signature_change` | Adding, removing, or renaming function parameters |
| `schema_change`    | Adding columns, tables, or altering DB schema |
| `api_change`       | Changing route paths, HTTP methods, or response shapes |
| `refactor`         | Internal restructuring with no intended behaviour change |
| `deletion`         | Removing a function, class, or endpoint |
| `new_feature`      | Introducing a net-new capability |

### Response 200

```json
{
  "ok": true,
  "report": {
    "meta": {
      "analyzed_target":      "services/payment_service.py#process_payment",
      "change_description":   "Add support for a new payment provider",
      "change_type":          "general",
      "risk_level":           "HIGH",
      "total_impacted_files": 8,
      "direct_callers":       2,
      "transitive_callers":   3,
      "test_files_affected":  5,
      "generated_at":         "2025-07-20T10:30:00Z"
    },

    "target": {
      "file":      "services/payment_service.py",
      "symbol":    "process_payment",
      "kind":      "service",
      "signature": "def process_payment(order_id: int, user_id: int, ...) -> dict:",
      "docstring": "Process a payment for an order. Steps: ..."
    },

    "risk_breakdown": {
      "dependency_centrality": "high",
      "api_boundary":          "high",
      "data_persistence":      "medium",
      "test_coverage":         "low",
      "overall":               "HIGH"
    },

    "impacted_components": [
      {
        "file":        "controllers/payment_controller.py",
        "symbol":      "PaymentController",
        "impact_type": "api_surface",
        "depth":       1,
        "risk_level":  "high",
        "reason":      "Directly calls or references `process_payment`"
      }
    ],

    "contract_hazards": [
      {
        "type":        "api_contract",
        "severity":    "high",
        "description": "POST `/payments` — Handler in a directly affected file",
        "file":        "routes/payments.py",
        "line":        0
      },
      {
        "type":        "db_schema",
        "severity":    "medium",
        "description": "Table `payments` (CREATE TABLE) in `schema/migrations.sql` ...",
        "file":        "schema/migrations.sql",
        "line":        87
      }
    ],

    "validation_plan": {
      "test_commands": [
        "pytest tests/test_payment_service.py -v -k test_process_payment_card_success",
        "pytest tests/test_checkout.py -v"
      ],
      "manual_checks": [
        "Add a sandbox/mock integration test for the new provider",
        "Verify API response shapes for all affected endpoints"
      ]
    },

    "mitigation": {
      "feature_flag":        "enable_process_payment_change",
      "rollback_complexity": "high",
      "rollback_note":       "DB migration rollback required",
      "deployment_strategy": "canary"
    },

    "mermaid_diagram": "graph TD\n  process_payment[...]\n  ...",

    "impact_categories": {
      "target":  { ... },
      "change":  { "description": "...", "type": "general" },
      "risk_level": "HIGH",
      "risk_breakdown": { ... },

      "directly_affected": [
        {
          "file":        "controllers/payment_controller.py",
          "symbol":      "PaymentController",
          "layer":       "controller",
          "reason":      "Directly calls or references `process_payment`",
          "depth":       1,
          "impact_type": "api_surface"
        }
      ],

      "indirectly_affected": [
        {
          "file":        "routes/payments.py",
          "symbol":      "charge",
          "layer":       "route",
          "reason":      "Imports from `controllers/payment_controller.py`",
          "depth":       2,
          "impact_type": "transitive_caller"
        }
      ],

      "related_tests": [
        {
          "file":      "tests/test_payment_service.py",
          "function":  "test_process_payment_card_success",
          "test_type": "unit",
          "command":   "pytest tests/test_payment_service.py -v -k test_process_payment_card_success",
          "reason":    "Unit test covering `process_payment`"
        },
        {
          "file":      "tests/test_checkout.py",
          "function":  "test_checkout_full_happy_path",
          "test_type": "integration",
          "command":   "pytest tests/test_checkout.py -v -k test_checkout_full_happy_path",
          "reason":    "Integration test covering `process_payment`"
        }
      ],

      "related_apis": [
        {
          "http_method": "POST",
          "path":        "/payments",
          "file":        "routes/payments.py",
          "handler":     "charge",
          "reason":      "Handler `charge` in a directly affected file"
        },
        {
          "http_method": "POST",
          "path":        "/payments/order/<order_id>/refund",
          "file":        "routes/payments.py",
          "handler":     "refund",
          "reason":      "Handler `refund` in a directly affected file"
        }
      ],

      "related_db": [
        {
          "table_name": "payments",
          "operation":  "CREATE TABLE",
          "file":       "schema/migrations.sql",
          "line":       87,
          "reason":     "Table `payments` is referenced by `services/payment_service.py`"
        }
      ],

      "risk_areas": [
        {
          "severity":       "high",
          "category":       "wide_impact",
          "title":          "Multiple direct callers",
          "description":    "2 components call `process_payment` directly ...",
          "affected_files": ["controllers/payment_controller.py", "services/order_service.py"]
        },
        {
          "severity":       "high",
          "category":       "api_contract",
          "title":          "Public API contract at risk",
          "description":    "The change may alter the behaviour of 3 HTTP endpoint(s): ...",
          "affected_files": ["routes/payments.py"]
        },
        {
          "severity":       "high",
          "category":       "semantic",
          "title":          "New external integration introduced",
          "description":    "Integrating a new external provider ...",
          "affected_files": ["services/payment_service.py", "controllers/payment_controller.py"]
        }
      ],

      "testing_suggestions": [
        {
          "priority": "must",
          "action":   "Re-run all existing unit tests for `process_payment`",
          "detail":   "Found 4 unit test(s) that cover `process_payment`. They must all pass after the change.",
          "command":  "pytest tests/test_payment_service.py -v -k test_process_payment_card_success"
        },
        {
          "priority": "must",
          "action":   "Add a sandbox/mock integration test for the new provider",
          "detail":   "Before enabling the new integration in production ...",
          "command":  null
        },
        {
          "priority": "should",
          "action":   "Run the full test suite as a final regression gate",
          "detail":   "Confirm no unexpected failures across all 71 demo tests.",
          "command":  "pytest tests/ -v"
        }
      ]
    }
  }
}
```

### Error Responses

| Code | `ok` | When |
|------|------|------|
| `400` | false | Missing `target_file` / `target_symbol`, invalid `change_type`, description too long, path traversal attempt |
| `415` | false | Request body sent without `Content-Type: application/json` |
| `422` | false | Symbol not found in the specified file — `available_symbols` hint is included |
| `500` | false | Unexpected engine error — `detail` field contains a truncated traceback |

**400 example**
```json
{
  "ok": false,
  "error": "change_type must be one of: api_change, deletion, general, new_feature, refactor, schema_change, signature_change. Got: 'bad_type'",
  "schema": "/api/analyze/schema"
}
```

**422 example**
```json
{
  "ok": false,
  "error": "Symbol 'foo' not found in services/payment_service.py.",
  "available_symbols": ["process_payment", "get_payment_for_order", "refund_payment", ...],
  "hint": "Check that target_symbol is one of the symbols defined in services/payment_service.py. Call GET /api/symbols?path=<file> to see all available symbols."
}
```

---

## 5. Symbols

### List symbols in a file

```
GET /api/symbols?path=<file>[&kind=<kind>]
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `path`    | ✅        | Relative path inside `demo/ecommerce/` |
| `kind`    | ❌        | Filter by `function` \| `class` \| `method` |

**Response 200**
```json
{
  "ok": true,
  "file": "services/payment_service.py",
  "layer": "service",
  "count": 7,
  "symbols": [
    {
      "name":              "process_payment",
      "kind":              "function",
      "signature":         "def process_payment(order_id: int, user_id: int, payment_method: str, ...)",
      "line_start":        104,
      "line_end":          177,
      "docstring_preview": "Process a payment for an order. Steps: ..."
    }
  ]
}
```

### List all symbols across the codebase

```
GET /api/symbols/all[?layer=<layer>]
```

### List files grouped by layer

```
GET /api/symbols/layers
```

Returns files grouped under `service`, `model`, `controller`, `route`, `test`, `schema`.

---

## 6. Graph

```
GET /api/graph                    — full codebase index (summary + all nodes)
GET /api/graph/file?path=<file>   — all relationships for a specific file
```

The graph endpoint exposes the raw `CodebaseGraph` used by the analyzer,
useful for debugging and for building visualisations.

---

## 7. Error Response Shape

All error responses follow a consistent envelope:

```json
{
  "ok":    false,
  "error": "Human-readable error message",
  // Optional additional context keys:
  "hint":              "...",
  "available_symbols": ["..."],
  "schema":            "/api/analyze/schema"
}
```

---

## 8. Full Example — PaymentService

### curl

```bash
curl -X POST http://localhost:5000/api/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "target_file":        "services/payment_service.py",
    "target_symbol":      "process_payment",
    "change_description": "Add support for a new payment provider",
    "change_type":        "general"
  }'
```

### fetch (JavaScript / TypeScript)

```ts
const response = await fetch("http://localhost:5000/api/analyze", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    target_file:        "services/payment_service.py",
    target_symbol:      "process_payment",
    change_description: "Add support for a new payment provider",
    change_type:        "general",
  }),
});

const { ok, report } = await response.json();
// report.meta.risk_level     → "HIGH"
// report.impact_categories   → { directly_affected, related_tests, ... }
```

### Python (requests)

```python
import requests

resp = requests.post("http://localhost:5000/api/analyze", json={
    "target_file":        "services/payment_service.py",
    "target_symbol":      "process_payment",
    "change_description": "Add support for a new payment provider",
    "change_type":        "general",
})
report = resp.json()["report"]
print(report["meta"]["risk_level"])  # HIGH
```

---

## 9. Frontend Integration

The Vite dev server (`:5173`) proxies all `/api/*` requests to `:5000`
via `vite.config.ts`:

```ts
server: {
  proxy: {
    '/api': { target: 'http://localhost:5000', changeOrigin: true }
  }
}
```

So the frontend calls `/api/analyze` (no port) and Vite forwards to Flask.
CORS headers (`Access-Control-Allow-Origin: *`) are also set on every Flask
response, so direct browser calls to `:5000` work too.

### Recommended call sequence from the frontend

```
1. GET /api/tree                          → populate file tree sidebar
2. GET /api/symbols?path=<selected file>  → populate symbol dropdown
3. GET /api/analyze/schema                → populate change_type dropdown
4. POST /api/analyze                      → run analysis on form submit
5. Render report.impact_categories        → display 7-category result
```
