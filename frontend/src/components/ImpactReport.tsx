import { useState } from 'react'
import type { BlastRadiusReport, RiskArea, TestingSuggestion, RelatedAPI, RelatedDB, AffectedComponent, RelatedTest } from '../types'
import MermaidDiagram from './MermaidDiagram'

interface Props {
  report: BlastRadiusReport
}

// ── Style mappings ────────────────────────────────────────────────────────────

const RISK_BADGE: Record<string, { bg: string; text: string; border: string; glow: string }> = {
  CRITICAL: { bg: 'bg-red-500/10', text: 'text-red-700 dark:text-red-400', border: 'border-red-300', glow: 'shadow-red-100' },
  HIGH:     { bg: 'bg-orange-500/10', text: 'text-orange-700 dark:text-orange-400', border: 'border-orange-300', glow: 'shadow-orange-100' },
  MEDIUM:   { bg: 'bg-amber-500/10', text: 'text-amber-700 dark:text-amber-400', border: 'border-amber-300', glow: 'shadow-amber-100' },
  LOW:      { bg: 'bg-emerald-500/10', text: 'text-emerald-700 dark:text-emerald-400', border: 'border-emerald-300', glow: 'shadow-emerald-100' },
}

const RISK_BANNER: Record<string, { border: string; bg: string; gradient: string }> = {
  CRITICAL: { border: 'border-l-red-500', bg: 'bg-red-50/40', gradient: 'from-red-500/5 to-transparent' },
  HIGH:     { border: 'border-l-orange-500', bg: 'bg-orange-50/40', gradient: 'from-orange-500/5 to-transparent' },
  MEDIUM:   { border: 'border-l-amber-500', bg: 'bg-amber-50/40', gradient: 'from-amber-500/5 to-transparent' },
  LOW:      { border: 'border-l-emerald-500', bg: 'bg-emerald-50/40', gradient: 'from-emerald-500/5 to-transparent' },
}

const SEV_CONFIG: Record<string, { badge: string; border: string; icon: string }> = {
  critical: { badge: 'bg-red-100 text-red-700 border-red-200', border: 'border-red-200 bg-red-50/30', icon: '🚨' },
  high:     { badge: 'bg-orange-100 text-orange-700 border-orange-200', border: 'border-orange-200 bg-orange-50/30', icon: '⚠️' },
  medium:   { badge: 'bg-amber-100 text-amber-700 border-amber-200', border: 'border-amber-200 bg-amber-50/30', icon: '⚡' },
  low:      { badge: 'bg-emerald-100 text-emerald-700 border-emerald-200', border: 'border-emerald-200 bg-emerald-50/30', icon: 'ℹ️' },
}

const PRI_CONFIG: Record<string, { badge: string; label: string }> = {
  must:     { badge: 'bg-red-600 text-white font-bold', label: 'MUST TEST' },
  should:   { badge: 'bg-orange-500 text-white font-semibold', label: 'SHOULD TEST' },
  consider: { badge: 'bg-blue-500 text-white', label: 'CONSIDER' },
}

const LAYER_CONFIG: Record<string, { label: string; badge: string; icon: string }> = {
  service:    { label: 'Service', badge: 'bg-blue-50 text-blue-700 border-blue-200', icon: '⚙️' },
  model:      { label: 'Model', badge: 'bg-indigo-50 text-indigo-700 border-indigo-200', icon: '📦' },
  route:      { label: 'Route / API', badge: 'bg-purple-50 text-purple-700 border-purple-200', icon: '🛣️' },
  controller: { label: 'Controller', badge: 'bg-pink-50 text-pink-700 border-pink-200', icon: '🎛️' },
  test:       { label: 'Test Suite', badge: 'bg-emerald-50 text-emerald-700 border-emerald-200', icon: '🧪' },
  frontend:   { label: 'Frontend UI', badge: 'bg-teal-50 text-teal-700 border-teal-200', icon: '🖼️' },
}

// ── Generic Card / Accordion ──────────────────────────────────────────────────

function ExpandableCard({
  title,
  subtitle,
  icon,
  count,
  accent = 'border-gray-200',
  defaultExpanded = true,
  badgeText,
  badgeColor,
  children,
}: {
  title: string
  subtitle?: string
  icon: string
  count?: number
  accent?: string
  defaultExpanded?: boolean
  badgeText?: string
  badgeColor?: string
  children: React.ReactNode
}) {
  const [expanded, setExpanded] = useState(defaultExpanded)

  return (
    <section className={`bg-white border rounded-xl shadow-xs transition-all duration-150 overflow-hidden ${accent}`}>
      <button
        type="button"
        onClick={() => setExpanded(!expanded)}
        className="w-full px-5 py-4 flex items-center justify-between text-left hover:bg-gray-50/70 transition-colors cursor-pointer select-none"
      >
        <div className="flex items-center gap-3 min-w-0">
          <span className="text-xl shrink-0 p-1 rounded-md bg-gray-50 border border-gray-100">{icon}</span>
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <h2 className="text-sm font-bold text-gray-900 tracking-tight">{title}</h2>
              {count !== undefined && (
                <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-gray-100 text-gray-700">
                  {count}
                </span>
              )}
              {badgeText && (
                <span className={`text-[10px] font-bold px-2 py-0.5 rounded border uppercase tracking-wider ${badgeColor ?? 'bg-gray-100 text-gray-700'}`}>
                  {badgeText}
                </span>
              )}
            </div>
            {subtitle && <p className="text-xs text-gray-500 mt-0.5 truncate">{subtitle}</p>}
          </div>
        </div>
        <div className="flex items-center gap-2 shrink-0 ml-3 text-gray-400">
          <span className="text-xs font-medium text-gray-400">{expanded ? 'Collapse' : 'Expand'}</span>
          <span className="text-xs">{expanded ? '▲' : '▼'}</span>
        </div>
      </button>

      {expanded && <div className="px-5 pb-5 pt-2 border-t border-gray-100">{children}</div>}
    </section>
  )
}

// ── Item Cards ────────────────────────────────────────────────────────────────

function ComponentCard({ comp, isDirect }: { comp: AffectedComponent; isDirect: boolean }) {
  const layer = LAYER_CONFIG[comp.layer] ?? { label: comp.layer, badge: 'bg-gray-100 text-gray-700', icon: '📄' }

  return (
    <div className={`p-3.5 rounded-lg border transition-all ${
      isDirect
        ? 'bg-orange-50/30 border-orange-200 hover:border-orange-300'
        : 'bg-gray-50/40 border-gray-200 hover:border-gray-300'
    }`}>
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2 min-w-0">
          <span className="text-sm shrink-0">{layer.icon}</span>
          <span className="font-mono text-xs font-bold text-gray-900 truncate">
            {comp.symbol}
          </span>
          <span className={`text-[10px] px-1.5 py-0.5 rounded font-medium border ${layer.badge}`}>
            {layer.label}
          </span>
          {comp.depth !== undefined && comp.depth > 0 && (
            <span className="text-[10px] px-1.5 py-0.5 rounded bg-gray-100 text-gray-600 font-mono">
              depth: {comp.depth}
            </span>
          )}
        </div>
        <code className="text-[11px] text-gray-500 bg-white border border-gray-200 px-2 py-0.5 rounded font-mono shrink-0 truncate max-w-[200px]">
          {comp.file}
        </code>
      </div>

      <div className="mt-2.5 pt-2 border-t border-gray-200/50 flex items-start gap-2">
        <span className="text-orange-500 font-bold text-xs shrink-0 select-none">→</span>
        <p className="text-xs text-gray-700 leading-relaxed font-normal">
          <span className="font-semibold text-gray-900">Why affected: </span>
          {comp.reason}
        </p>
      </div>
    </div>
  )
}

function RiskAreaCard({ area }: { area: RiskArea }) {
  const cfg = SEV_CONFIG[area.severity] ?? SEV_CONFIG.medium

  return (
    <div className={`rounded-xl p-4 border ${cfg.border} shadow-2xs`}>
      <div className="flex items-start gap-3">
        <span className="text-lg shrink-0 mt-0.5">{cfg.icon}</span>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap mb-1">
            <span className={`text-[10px] px-2 py-0.5 rounded-md font-bold uppercase tracking-wider border ${cfg.badge}`}>
              {area.severity}
            </span>
            <span className="text-xs font-semibold text-gray-800">{area.title}</span>
          </div>
          <p className="text-xs text-gray-600 leading-relaxed">{area.description}</p>
          {area.affected_files.length > 0 && (
            <div className="mt-2.5 flex flex-wrap items-center gap-1.5 pt-2 border-t border-gray-200/50">
              <span className="text-[11px] font-medium text-gray-500">Affected files:</span>
              {area.affected_files.map((f) => (
                <code key={f} className="text-[11px] bg-white border border-gray-200 text-gray-700 px-1.5 py-0.5 rounded font-mono">
                  {f.split('/').pop()}
                </code>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function APICard({ api }: { api: RelatedAPI }) {
  const methodColors: Record<string, string> = {
    GET: 'bg-blue-600 text-white',
    POST: 'bg-emerald-600 text-white',
    PUT: 'bg-amber-600 text-white',
    PATCH: 'bg-orange-600 text-white',
    DELETE: 'bg-rose-600 text-white',
  }

  return (
    <div className="p-3.5 rounded-lg border border-purple-200 bg-purple-50/20 hover:border-purple-300 transition-colors">
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2 min-w-0">
          <span className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded ${methodColors[api.http_method] ?? 'bg-gray-600 text-white'}`}>
            {api.http_method}
          </span>
          <code className="text-xs font-mono font-semibold text-gray-900 truncate">{api.path}</code>
        </div>
        <span className="text-[11px] font-mono text-gray-500 bg-white border border-gray-200 px-2 py-0.5 rounded shrink-0">
          {api.handler}
        </span>
      </div>
      <p className="text-xs text-gray-600 mt-2 pl-1 leading-relaxed">
        <span className="text-purple-600 font-medium">Route Binding: </span>{api.reason}
      </p>
    </div>
  )
}

function DBCard({ db }: { db: RelatedDB }) {
  return (
    <div className="p-3.5 rounded-lg border border-blue-200 bg-blue-50/20 hover:border-blue-300 transition-colors">
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <span className="text-base">🗄️</span>
          <span className="font-mono text-xs font-bold text-gray-900">{db.table_name}</span>
          <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded bg-blue-100 text-blue-800 font-semibold">
            {db.operation}
          </span>
        </div>
        <span className="text-[11px] font-mono text-gray-500 bg-white border border-gray-200 px-2 py-0.5 rounded">
          {db.file}:{db.line}
        </span>
      </div>
      <p className="text-xs text-gray-600 mt-2 pl-6 leading-relaxed">{db.reason}</p>
    </div>
  )
}

function TestItem({ test }: { test: RelatedTest }) {
  return (
    <div className="p-3 rounded-lg border border-emerald-200 bg-emerald-50/20 hover:border-emerald-300 transition-colors">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2 min-w-0">
          <span className="text-emerald-600 text-sm">🧪</span>
          <span className="font-mono text-xs font-bold text-gray-900 truncate">{test.function}</span>
          <span className="text-[10px] px-1.5 py-0.5 rounded bg-emerald-100 text-emerald-800 font-medium">
            {test.test_type}
          </span>
        </div>
        <code className="text-[11px] text-gray-500 font-mono shrink-0">{test.file}</code>
      </div>
      <p className="text-xs text-gray-600 mt-1.5 pl-6">{test.reason}</p>
      {test.command && (
        <div className="mt-2 pl-6">
          <code className="inline-block text-[11px] bg-gray-900 text-emerald-400 px-2.5 py-1 rounded font-mono">
            $ {test.command}
          </code>
        </div>
      )}
    </div>
  )
}

function SuggestionCard({ s }: { s: TestingSuggestion }) {
  const pri = PRI_CONFIG[s.priority] ?? PRI_CONFIG.consider

  return (
    <div className="p-3.5 rounded-lg border border-gray-200 bg-white hover:shadow-xs transition-shadow">
      <div className="flex items-start gap-3">
        <span className={`text-[9px] px-2 py-0.5 rounded shrink-0 mt-0.5 ${pri.badge}`}>
          {pri.label}
        </span>
        <div className="flex-1 min-w-0">
          <h4 className="text-xs font-bold text-gray-900">{s.action}</h4>
          {s.detail && <p className="text-xs text-gray-600 mt-1 leading-relaxed">{s.detail}</p>}
          {s.command && (
            <div className="mt-2">
              <code className="inline-block text-[11px] bg-gray-900 text-emerald-400 px-3 py-1.5 rounded-md font-mono">
                $ {s.command}
              </code>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

// ── Main Component ────────────────────────────────────────────────────────────

export default function ImpactReport({ report }: Props) {
  const { meta, target, impact_categories: ic, mermaid_diagram, validation_plan, mitigation } = report
  const riskBadge = RISK_BADGE[meta.risk_level] ?? RISK_BADGE.MEDIUM
  const banner = RISK_BANNER[meta.risk_level] ?? RISK_BANNER.MEDIUM

  return (
    <div className="space-y-4 pb-12">

      {/* ── 1. Executive Summary & Blast Metrics Banner ─────────────────────── */}
      <section className={`border-l-4 rounded-xl p-5 shadow-xs bg-white border border-gray-200 ${banner.border}`}>
        <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
          <div className="flex items-center gap-2.5">
            <span className={`inline-flex items-center px-3 py-1 rounded-lg text-xs font-black tracking-wider uppercase border ${riskBadge.bg} ${riskBadge.text} ${riskBadge.border}`}>
              💥 {meta.risk_level} RISK
            </span>
            <span className="text-xs text-gray-500 font-medium">
              Blast Radius Analysis
            </span>
          </div>
          <div className="text-[11px] text-gray-400 font-mono">
            {meta.generated_at ? new Date(meta.generated_at).toLocaleTimeString() : 'Live Scan'}
          </div>
        </div>

        {/* Target details */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 p-3.5 bg-gray-50/80 rounded-lg border border-gray-100 text-xs">
          <div>
            <span className="text-gray-400 font-medium">Target Component:</span>
            <div className="flex items-center gap-1.5 mt-0.5">
              <span className="font-mono font-bold text-gray-900 text-sm">{target.symbol}</span>
              {target.kind && (
                <span className="text-[10px] px-1.5 py-0.2 rounded bg-white border border-gray-200 text-gray-600 uppercase">
                  {target.kind}
                </span>
              )}
            </div>
            <p className="text-gray-500 font-mono mt-0.5 truncate">{target.file}</p>
          </div>
          <div>
            <span className="text-gray-400 font-medium">Proposed Change:</span>
            <p className="font-medium text-gray-800 mt-0.5 leading-relaxed">
              {meta.change_description || 'No description provided'}
            </p>
            {target.signature && (
              <code className="text-[11px] text-gray-600 bg-white border border-gray-200 px-2 py-0.5 rounded font-mono block mt-1 truncate">
                {target.signature}
              </code>
            )}
          </div>
        </div>

        {/* Key Metrics Counters */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 mt-3.5">
          <div className="bg-white border border-gray-200 rounded-lg p-3 text-center">
            <div className="text-lg font-black text-gray-900">{meta.total_impacted_files}</div>
            <div className="text-[11px] font-medium text-gray-500 uppercase tracking-wide">Files Impacted</div>
          </div>
          <div className="bg-white border border-orange-200 rounded-lg p-3 text-center bg-orange-50/20">
            <div className="text-lg font-black text-orange-700">{meta.direct_callers}</div>
            <div className="text-[11px] font-medium text-orange-800 uppercase tracking-wide">Direct Callers</div>
          </div>
          <div className="bg-white border border-purple-200 rounded-lg p-3 text-center bg-purple-50/20">
            <div className="text-lg font-black text-purple-700">{meta.transitive_callers}</div>
            <div className="text-[11px] font-medium text-purple-800 uppercase tracking-wide">Indirect Callers</div>
          </div>
          <div className="bg-white border border-emerald-200 rounded-lg p-3 text-center bg-emerald-50/20">
            <div className="text-lg font-black text-emerald-700">{meta.test_files_affected}</div>
            <div className="text-[11px] font-medium text-emerald-800 uppercase tracking-wide">Affected Tests</div>
          </div>
        </div>
      </section>

      {/* ── 2. Visual Dependency & Blast Radius Map ─────────────────────────── */}
      <ExpandableCard
        title="Visual Blast Radius Map"
        subtitle="End-to-end dependency graph showing upstream callers, API ingress, and affected data sinks"
        icon="🗺️"
        accent="border-blue-200"
      >
        <div className="p-2 bg-gray-50/50 rounded-lg border border-gray-100">
          <MermaidDiagram diagram={mermaid_diagram} />
        </div>
      </ExpandableCard>

      {/* ── 3. Risk Areas & Hazard Alerts ──────────────────────────────────── */}
      {ic.risk_areas.length > 0 && (
        <ExpandableCard
          title="Critical Risk Areas & Contract Hazards"
          subtitle="Potential breaking hazards, unhandled schema changes, or missing safeguards"
          icon="🚨"
          count={ic.risk_areas.length}
          accent="border-red-200"
          badgeText="Requires Attention"
          badgeColor="bg-red-100 text-red-800 border-red-200"
        >
          <div className="space-y-2.5">
            {ic.risk_areas.map((area, i) => (
              <RiskAreaCard key={i} area={area} />
            ))}
          </div>
        </ExpandableCard>
      )}

      {/* ── 4. Directly Affected Components ────────────────────────────────── */}
      <ExpandableCard
        title="Directly Affected Components"
        subtitle="Modules, controllers, and functions directly calling or referencing the modified symbol"
        icon="🎯"
        count={ic.directly_affected.length}
        accent="border-orange-200"
      >
        {ic.directly_affected.length === 0 ? (
          <p className="text-xs text-gray-500 py-2">No direct callers detected in the indexed codebase.</p>
        ) : (
          <div className="grid grid-cols-1 gap-2">
            {ic.directly_affected.map((c, i) => (
              <ComponentCard key={i} comp={c} isDirect={true} />
            ))}
          </div>
        )}
      </ExpandableCard>

      {/* ── 5. Indirectly Affected Components ──────────────────────────────── */}
      {ic.indirectly_affected.length > 0 && (
        <ExpandableCard
          title="Indirectly Affected Components (Transitive)"
          subtitle="Upstream callers and downstream dependencies impacted across multi-hop calls"
          icon="⛓️"
          count={ic.indirectly_affected.length}
          accent="border-purple-200"
          defaultExpanded={false}
        >
          <div className="grid grid-cols-1 gap-2">
            {ic.indirectly_affected.map((c, i) => (
              <ComponentCard key={i} comp={c} isDirect={false} />
            ))}
          </div>
        </ExpandableCard>
      )}

      {/* ── 6. APIs & Database Components Side-by-Side ─────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* APIs */}
        <ExpandableCard
          title="API Endpoints Ingress"
          subtitle="Public or internal routes exposed to this change"
          icon="🛣️"
          count={ic.related_apis.length}
          accent="border-purple-200"
        >
          {ic.related_apis.length === 0 ? (
            <p className="text-xs text-gray-400 py-1">No API routes directly dependent on this component.</p>
          ) : (
            <div className="space-y-2">
              {ic.related_apis.map((api, i) => (
                <APICard key={i} api={api} />
              ))}
            </div>
          )}
        </ExpandableCard>

        {/* Database */}
        <ExpandableCard
          title="Database Persistence"
          subtitle="Impacted database tables, models, and queries"
          icon="🗄️"
          count={ic.related_db.length}
          accent="border-blue-200"
        >
          {ic.related_db.length === 0 ? (
            <p className="text-xs text-gray-400 py-1">No database operations impacted.</p>
          ) : (
            <div className="space-y-2">
              {ic.related_db.map((db, i) => (
                <DBCard key={i} db={db} />
              ))}
            </div>
          )}
        </ExpandableCard>
      </div>

      {/* ── 7. Related Tests ─────────────────────────────────────────────────── */}
      {ic.related_tests.length > 0 && (
        <ExpandableCard
          title="Related Test Suites"
          subtitle="Existing test files covering the target and its callers"
          icon="🧪"
          count={ic.related_tests.length}
          accent="border-emerald-200"
        >
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5">
            {ic.related_tests.map((test, i) => (
              <TestItem key={i} test={test} />
            ))}
          </div>
        </ExpandableCard>
      )}

      {/* ── 8. Recommended Testing & Validation Plan ────────────────────────── */}
      <ExpandableCard
        title="Recommended Testing & Validation Plan"
        subtitle="Actionable steps and test execution commands recommended before deployment"
        icon="📋"
        count={ic.testing_suggestions.length}
        accent="border-indigo-200"
      >
        <div className="space-y-2.5">
          {ic.testing_suggestions.map((s, i) => (
            <SuggestionCard key={i} s={s} />
          ))}
          {ic.testing_suggestions.length === 0 && validation_plan.test_commands.length > 0 && (
            <div className="space-y-1.5">
              {validation_plan.test_commands.map((cmd, i) => (
                <code key={i} className="block text-xs bg-gray-900 text-emerald-400 px-3 py-2 rounded-lg font-mono">
                  $ {cmd}
                </code>
              ))}
            </div>
          )}
        </div>
      </ExpandableCard>

      {/* ── 9. Mitigation & Safe Rollback Strategy ───────────────────────────── */}
      <ExpandableCard
        title="Mitigation & Safe Deployment Strategy"
        subtitle="Rollback feasibility, feature flag recommendations, and deployment safeguards"
        icon="🛡️"
        accent="border-teal-200"
        defaultExpanded={false}
      >
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          <div className="bg-gray-50/70 p-3 rounded-lg border border-gray-200">
            <span className="text-[10px] font-bold text-gray-500 uppercase tracking-wider block mb-1">Feature Flag</span>
            <code className="text-xs font-mono font-bold text-gray-800 break-all">{mitigation.feature_flag || 'None'}</code>
          </div>
          <div className="bg-gray-50/70 p-3 rounded-lg border border-gray-200">
            <span className="text-[10px] font-bold text-gray-500 uppercase tracking-wider block mb-1">Deployment Strategy</span>
            <span className="text-xs font-semibold text-gray-800">{mitigation.deployment_strategy || 'Standard Rollout'}</span>
          </div>
          <div className="bg-gray-50/70 p-3 rounded-lg border border-gray-200">
            <span className="text-[10px] font-bold text-gray-500 uppercase tracking-wider block mb-1">Rollback Complexity</span>
            <span className={`text-xs font-bold uppercase ${
              mitigation.rollback_complexity === 'high' ? 'text-red-600' :
              mitigation.rollback_complexity === 'medium' ? 'text-amber-600' : 'text-emerald-600'
            }`}>
              {mitigation.rollback_complexity || 'Low'}
            </span>
          </div>
          <div className="bg-gray-50/70 p-3 rounded-lg border border-gray-200">
            <span className="text-[10px] font-bold text-gray-500 uppercase tracking-wider block mb-1">Rollback Note</span>
            <p className="text-xs text-gray-600 leading-tight">{mitigation.rollback_note || 'Revert commit safe.'}</p>
          </div>
        </div>
      </ExpandableCard>

    </div>
  )
}
