# Change Blast Radius Analyzer

> **IBM Bob 2.0 Hackathon** — Agentic Developer Workflow Accelerator  
> Helps developers understand what parts of a codebase will be affected **before** making a change.

---

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+

### 1. Backend (Flask)

```bash
cd backend
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
python app.py
# → Running on http://localhost:5000
```

### 2. Frontend (React + Vite)

```bash
cd frontend
npm install
npm run dev
# → Running on http://localhost:5173
```

Open **http://localhost:5173** in your browser.

---

## Project Structure

```
IBM-Bob-2.0/
├── backend/                  # Python + Flask analysis engine
│   ├── app.py                # Flask entry point
│   ├── requirements.txt      # Python dependencies
│   ├── env.example           # Environment variable template
│   ├── routes/
│   │   ├── tree.py           # GET /api/tree
│   │   └── analyze.py        # POST /api/analyze
│   └── engine/
│       ├── target_resolver.py   # Step 1 — AST symbol lookup
│       ├── dependency_tracer.py # Step 2 — caller/import tracing
│       ├── contract_checker.py  # Step 3 — API & DB contract detection
│       ├── test_mapper.py       # Step 4 — test file cross-reference
│       ├── risk_scorer.py       # Step 5 — blast radius risk score
│       └── report_builder.py   # Step 6 — report + Mermaid diagram
│
├── frontend/                 # React + Vite + Tailwind UI
│   ├── src/
│   │   ├── App.tsx           # Root layout
│   │   ├── api.ts            # Typed fetch helpers
│   │   ├── types.ts          # BlastRadiusReport TypeScript types
│   │   └── components/
│   │       ├── FileTree.tsx      # Sample codebase file tree sidebar
│   │       ├── AnalyzeForm.tsx   # Symbol + change description form
│   │       ├── MermaidDiagram.tsx # Mermaid graph renderer
│   │       └── ImpactReport.tsx  # Full report view
│   ├── package.json
│   └── vite.config.ts        # Vite with /api proxy to :5000
│
├── demo/
│   └── ecommerce/            # Fictional e-commerce codebase (analysis target)
│       ├── routes/           # Flask route handlers
│       ├── services/         # Business logic (order_service, inventory_service, auth_service)
│       ├── models/           # ORM-style model stubs
│       ├── schema/           # SQL migration file
│       └── tests/            # pytest test files
│
├── .agents/skills/           # IBM Bob 2.0 skill definitions
├── bob_sessions/             # Hackathon task-session screenshots
├── AGENTS.md                 # Bob IDE persistent context
└── .bobignore                # Bob indexing exclusions
```

---

## How It Works

1. **Select** a file from the demo/ecommerce sidebar.
2. **Name** a function or class (e.g. `calculate_order_total`).
3. **Describe** your proposed change.
4. Click **Analyze Blast Radius**.
5. The backend engine runs a 6-step pipeline:
   - Resolves the symbol via Python `ast`
   - Traces direct and transitive callers via regex
   - Detects API route and SQL schema hazards
   - Maps test files that reference the symbol
   - Scores overall risk (CRITICAL / HIGH / MEDIUM / LOW)
   - Builds a structured report with a Mermaid dependency graph
6. The frontend renders the **Impact Report** with risk badges, impacted component table, contract hazards, and validation commands.

---

## API Reference

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/health` | Health check |
| `GET` | `/api/tree` | Returns demo codebase file tree |
| `POST` | `/api/analyze` | Runs blast radius analysis |

### POST /api/analyze — Request Body
```json
{
  "target_file": "services/order_service.py",
  "target_symbol": "calculate_order_total",
  "change_description": "Add a tax_rate parameter",
  "change_type": "signature_change"
}
```

---

## Demo Scenario

The best demo scenario is:

- **File**: `services/order_service.py`
- **Symbol**: `calculate_order_total`
- **Change**: *"Add a tax_rate parameter and update return type"*
- **Expected blast radius**: `routes/orders.py` → `tests/test_order_service.py` → `tests/test_routes_orders.py` → `models/order.py` → `schema/migrations.sql`

---

## License

MIT — IBM Bob 2.0 Hackathon submission.
