import type { TreeResponse, BlastRadiusReport, AnalyzeRequest } from './types'

const BASE = '/api'

export async function fetchTree(): Promise<TreeResponse> {
  const res = await fetch(`${BASE}/tree`)
  if (!res.ok) throw new Error(`GET /api/tree failed: ${res.status}`)
  return res.json()
}

export async function fetchSymbols(filePath: string): Promise<string[]> {
  const res = await fetch(`${BASE}/symbols?path=${encodeURIComponent(filePath)}`)
  if (!res.ok) return []
  const data = await res.json()
  // The backend returns an array of { name, kind, signature, ... } objects
  return ((data.symbols ?? []) as { name: string }[]).map((s) => s.name)
}

export async function fetchAnalysis(payload: AnalyzeRequest): Promise<BlastRadiusReport> {
  const res = await fetch(`${BASE}/analyze`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error((err as { error?: string }).error ?? `POST /api/analyze failed: ${res.status}`)
  }
  const data = await res.json()
  return data.report as BlastRadiusReport
}
