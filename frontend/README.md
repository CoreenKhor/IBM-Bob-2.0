# Frontend — React + Vite

Change Blast Radius Analyzer UI.

## Setup

```bash
npm install
npm run dev       # http://localhost:5173
npm run build     # production build → dist/
npm run lint      # ESLint
```

## Vite Proxy

All `/api/*` requests are proxied to `http://localhost:5000` (the Flask backend).  
Start the backend first, then the frontend dev server.

## Component Overview

| Component | Purpose |
|---|---|
| `App.tsx` | Root layout — loads file tree, manages state |
| `FileTree.tsx` | Sidebar file browser for demo/ecommerce |
| `AnalyzeForm.tsx` | Symbol name + change description form |
| `MermaidDiagram.tsx` | Renders Mermaid blast radius graph in-browser |
| `ImpactReport.tsx` | Full report view — risk badges, impact table, hazards |

## Types

All API types are defined in [`src/types.ts`](src/types.ts).  
The canonical shape is `BlastRadiusReport`.
