import type { BlastRadiusReport, RiskArea, TestingSuggestion, RelatedAPI, RelatedDB } from '../types'
import MermaidDiagram from './MermaidDiagram'

interface Props {
  report: BlastRadiusReport
}

// ── Style helpers ─────────────────────────────────────────────────────────────

const RISK_BADGE: Record<string, string> = {
  CRITICAL: 'bg-red-100 text-red-800 border-red-300',
  HIGH:     'bg-orange-100 text-orange-800 border-orange-300',
  MEDIUM:   'bg-yellow-100 text-yellow-800 border-yellow-300',
  LOW:      'bg-green-100 text-green-800 border-green-300',
}

const RISK_BANNER: Record<string, string> = {
  CRITICAL: 'border-red-400 bg-red-50',
  HIGH:     'border-orange-400 bg-orange-50',
  MEDIUM:   'border-yellow-400 bg-yellow-50',
  LOW:      'border-green-400 bg-green-50',
}

const SEV_BADGE: Record<string, string> = {
  critical: 'bg-red-100 text-red-700',
  high:     'bg-orange-100 text-orange-700',
  medium:   'bg-yellow-100 text-yellow-700',
  low:      'bg-green-100 text-green-700',
}

const PRI_BADGE: Record<string, string> = {
  must:     'bg-red-100 text-red-700',
  should:   'bg-orange-100 text-orange-700',
  consider: 'bg-blue-100 text-blue-700',
}

const LAYER_COLOR: Record<string, string> = {
  service:    'bg-blue-100 text-blue-700',
  model:      'bg-indigo-100 text-indigo-700',
  route:      'bg-purple-100 text-purple-700',
  controller: 'bg-pink-100 text-pink-700',
  test:       'bg-green-100 text-green-700',
  frontend:   'bg-teal-100 text-teal-700',
}

function Badge({ label, cls }: { label: string; cls: string }) {
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${cls}`}>
      {label}
    </span>
  )
}

function SectionCard({ title, count, accent, children }: {
  title: string
  count?: number
  accent?: string
  children: React.ReactNode
}) {
  return (
    <section className={`bg-white border rounded-xl p-5 shadow-sm ${accent ?? 'border-gray-200'}`}>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-sm font-semibold text-gray-900">{title}</h2>
        {count !== undefined && (
          <span className="text-xs font-medium text-gray-400 bg-gray-100 px-2 py-0.5 rounded-full">
            {count}
          </span>
        )}
      </div>
      {children}
    </section>
  )
}

// ── Sub-components ────────────────────────────────────────────────────────────

function RiskAreaItem({ area }: { area: RiskArea }) {
  return (
    <div className={`rounded-lg p-3 border ${SEV_BADGE[area.severity]?.replace('text-', 'border-').replace('bg-', 'bg-') ?? 'border-gray-200'} mb-2 last:mb-0`}>
      <div className="flex items-start gap-2">
        <Badge label={area.severity.toUpperCase()} cls={SEV_BADGE[area.severity] ?? ''} />
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-gray-800">{area.title}</p>
          <p className="text-xs text-gray-500 mt-0.5">{area.description}</p>
          {area.affected_files.length > 0 && (
            <div className="mt-1.5 flex flex-wrap gap-1">
              {area.affected_files.slice(0, 4).map((f) => (
                <code key={f} className="text-xs bg-gray-100 text-gray-600 px-1.5 py-0.5 rounded">
                  {f.split('/').pop()}
                </code>
              ))}
              {area.affected_files.length > 4 && (
                <span className="text-xs text-gray-400">+{area.affected_files.length - 4} more</span>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function SuggestionItem({ s }: { s: TestingSuggestion }) {
  return (
    <div className="flex items-start gap-3 py-2.5 border-b border-gray-100 last:border-0">
      <Badge label={s.priority.toUpperCase()} cls={PRI_BADGE[s.priority] ?? 'bg-gray-100 text-gray-600'} />
      <div className="flex-1 min-w-0">
        <p className="text-sm text-gray-800 font-medium">{s.action}</p>
        {s.detail && <p className="text-xs text-gray-500 mt-0.5">{s.detail}</p>}
        {s.command && (
          <code className="mt-1.5 block text-xs bg-gray-900 text-green-400 px-3 py-1.5 rounded font-mono">
            $ {s.command}
          </code>
        )}
      </div>
    </div>
  )
}

function APIRow({ api }: { api: RelatedAPI }) {
  const methodColor: Record<string, string> = {
    GET: 'bg-blue-100 text-blue-700',
    POST: 'bg-green-100 text-green-700',
    PUT: 'bg-yellow-100 text-yellow-700',
    PATCH: 'bg-orange-100 text-orange-700',
    DELETE: 'bg-red-100 text-red-700',
  }
  return (
    <div className="flex items-start gap-3 py-2 border-b border-gray-100 last:border-0">
      <Badge label={api.http_method} cls={methodColor[api.http_method] ?? 'bg-gray-100 text-gray-600'} />
      <div className="flex-1 min-w-0">
        <code className="text-sm font-mono text-gray-800">{api.path}</code>
        <p className="text-xs text-gray-500 mt-0.5">{api.reason}</p>
      </div>
      <code className="text-xs text-gray-400 font-mono shrink-0">{api.handler}</code>
    </div>
  )
}

function DBRow({ db }: { db: RelatedDB }) {
  return (
    <div className="flex items-start gap-3 py-2 border-b border-gray-100 last:border-0">
      <span className="text-sm">🗄</span>
      <div className="flex-1 min-w-0">
        <span className="text-sm font-medium font-mono text-gray-800">{db.table_name}</span>
        <Badge label={db.operation} cls="ml-2 bg-gray-100 text-gray-600" />
        <p className="text-xs text-gray-500 mt-0.5">{db.reason}</p>
      </div>
    </div>
  )
}

// ── Main component ────────────────────────────────────────────────────────────

export default function ImpactReport({ report }: Props) {
  const { meta, target, impact_categories: ic, mermaid_diagram, validation_plan, mitigation } = report
  const riskStyle = RISK_BADGE[meta.risk_level] ?? RISK_BADGE.MEDIUM
  const bannerStyle = RISK_BANNER[meta.risk_level] ?? RISK_BANNER.MEDIUM

  return (
    <div className="space-y-5">

      {/* ── Executive Summary Banner ───────────────────────────────────────── */}
      <section className={`border-l-4 rounded-xl p-5 shadow-sm ${bannerStyle}`}>
        <div className="flex flex-wrap items-center gap-2 mb-3">
          <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-bold border ${riskStyle}`}>
            {meta.risk_level} RISK
          </span>
          <span className="text-xs text-gray-600 bg-white/70 border border-gray-200 px-2.5 py-1 rounded-full">
            {meta.total_impacted_files} files affected
          </span>
          <span className="text-xs text-blue-700 bg-blue-50 border border-blue-200 px-2.5 py-1 rounded-full">
            {meta.direct_callers} direct callers
          </span>
          {meta.transitive_callers > 0 && (
            <span className="text-xs text-purple-700 bg-purple-50 border border-purple-200 px-2.5 py-1 rounded-full">
              {meta.transitive_callers} indirect
            </span>
          )}
          <span className="text-xs text-green-700 bg-green-50 border border-green-200 px-2.5 py-1 rounded-full">
            {meta.test_files_affected} test files
          </span>
        </div>
        <div className="text-sm text-gray-700 space-y-1">
          <p>
            <span className="font-medium">Target: </span>
            <code className="bg-white/80 border border-gray-200 px-1.5 py-0.5 rounded text-xs font-mono">
              {target.symbol}
            </code>
            {target.kind && (
              <Badge label={target.kind} cls="ml-2 bg-white/80 border border-gray-200 text-gray-600" />
            )}
          </p>
          <p>
            <span className="font-medium">File: </span>
            <code className="text-xs text-gray-600">{target.file}</code>
          </p>
          {meta.change_description && (
            <p><span className="font-medium">Change: </span>{meta.change_description}</p>
          )}
          {target.signature && (
            <p className="mt-1">
              <code className="text-xs bg-white/80 border border-gray-200 px-2 py-0.5 rounded font-mono text-gray-700">
                {target.signature}
              </code>
            </p>
          )}
        </div>
      </section>

      {/* ── Blast Radius Map ───────────────────────────────────────────────── */}
      <SectionCard title="Blast Radius Map">
        <MermaidDiagram diagram={mermaid_diagram} />
      </SectionCard>

      {/* ── Risk Areas ────────────────────────────────────────────────────── */}
      {ic.risk_areas.length > 0 && (
        <SectionCard
          title="⚠ Risk Areas"
          count={ic.risk_areas.length}
          accent="border-orange-200"
        >
          {ic.risk_areas.map((area, i) => (
            <RiskAreaItem key={i} area={area} />
          ))}
        </SectionCard>
      )}

      {/* ── Direct + Indirect Impact ──────────────────────────────────────── */}
      <SectionCard
        title="Directly Affected"
        count={ic.directly_affected.length}
      >
        {ic.directly_affected.length === 0 ? (
          <p className="text-sm text-gray-400">No directly affected components found.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs text-gray-400 uppercase border-b border-gray-100">
                  <th className="pb-2 pr-3">File</th>
                  <th className="pb-2 pr-3">Symbol</th>
                  <th className="pb-2 pr-3">Layer</th>
                  <th className="pb-2">Reason</th>
                </tr>
              </thead>
              <tbody>
                {ic.directly_affected.map((c, i) => (
                  <tr key={i} className="border-b border-gray-50 hover:bg-gray-50">
                    <td className="py-2 pr-3 font-mono text-xs text-gray-600 max-w-[160px] truncate">
                      {c.file.split('/').pop()}
                    </td>
                    <td className="py-2 pr-3 font-mono text-xs font-medium text-orange-700">{c.symbol}</td>
                    <td className="py-2 pr-3">
                      <Badge label={c.layer} cls={LAYER_COLOR[c.layer] ?? 'bg-gray-100 text-gray-600'} />
                    </td>
                    <td className="py-2 text-xs text-gray-500">{c.reason}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </SectionCard>

      {ic.indirectly_affected.length > 0 && (
        <SectionCard
          title="Indirectly Affected"
          count={ic.indirectly_affected.length}
        >
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs text-gray-400 uppercase border-b border-gray-100">
                  <th className="pb-2 pr-3">File</th>
                  <th className="pb-2 pr-3">Symbol</th>
                  <th className="pb-2 pr-3">Layer</th>
                  <th className="pb-2">Reason</th>
                </tr>
              </thead>
              <tbody>
                {ic.indirectly_affected.map((c, i) => (
                  <tr key={i} className="border-b border-gray-50 hover:bg-gray-50">
                    <td className="py-2 pr-3 font-mono text-xs text-gray-500 max-w-[160px] truncate">
                      {c.file.split('/').pop()}
                    </td>
                    <td className="py-2 pr-3 font-mono text-xs text-gray-600">{c.symbol}</td>
                    <td className="py-2 pr-3">
                      <Badge label={c.layer} cls={LAYER_COLOR[c.layer] ?? 'bg-gray-100 text-gray-600'} />
                    </td>
                    <td className="py-2 text-xs text-gray-400">{c.reason}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </SectionCard>
      )}

      {/* ── API Impact ────────────────────────────────────────────────────── */}
      {ic.related_apis.length > 0 && (
        <SectionCard
          title="API Surface Impact"
          count={ic.related_apis.length}
          accent="border-purple-200"
        >
          {ic.related_apis.map((api, i) => <APIRow key={i} api={api} />)}
        </SectionCard>
      )}

      {/* ── Database Impact ───────────────────────────────────────────────── */}
      {ic.related_db.length > 0 && (
        <SectionCard
          title="Database Impact"
          count={ic.related_db.length}
          accent="border-blue-200"
        >
          {ic.related_db.map((db, i) => <DBRow key={i} db={db} />)}
        </SectionCard>
      )}

      {/* ── Test Coverage ─────────────────────────────────────────────────── */}
      {ic.related_tests.length > 0 && (
        <SectionCard
          title="Tests to Run"
          count={ic.related_tests.length}
          accent="border-green-200"
        >
          <div className="space-y-1">
            {ic.related_tests.map((t, i) => (
              <div key={i} className="flex items-start gap-2 py-1.5 border-b border-gray-100 last:border-0">
                <span className="text-green-500 text-xs mt-0.5">✓</span>
                <div className="flex-1 min-w-0">
                  <p className="text-xs font-mono font-medium text-gray-700">{t.function}</p>
                  <p className="text-xs text-gray-400">{t.file.split('/').pop()} · {t.reason}</p>
                </div>
                {t.command && (
                  <code className="text-xs text-gray-400 font-mono shrink-0 hidden lg:block">
                    {t.command.split(' ').slice(0, 3).join(' ')}
                  </code>
                )}
              </div>
            ))}
          </div>
        </SectionCard>
      )}

      {/* ── Risk Breakdown Grid ───────────────────────────────────────────── */}
      <SectionCard title="Risk Breakdown">
        <dl className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          {Object.entries(ic.risk_breakdown)
            .filter(([k]) => k !== 'overall')
            .map(([key, val]) => (
              <div key={key} className="bg-gray-50 rounded-lg p-3 border border-gray-100">
                <dt className="text-xs text-gray-400 capitalize mb-1">{key.replace(/_/g, ' ')}</dt>
                <dd className={`text-sm font-semibold capitalize ${
                  val === 'high' || val === 'critical' ? 'text-red-600' :
                  val === 'medium' ? 'text-yellow-600' : 'text-green-600'
                }`}>{val as string}</dd>
              </div>
            ))}
        </dl>
      </SectionCard>

      {/* ── Testing Suggestions ───────────────────────────────────────────── */}
      <SectionCard title="Testing Suggestions" count={ic.testing_suggestions.length}>
        {ic.testing_suggestions.map((s, i) => <SuggestionItem key={i} s={s} />)}
        {/* Fallback from legacy validation_plan */}
        {ic.testing_suggestions.length === 0 && validation_plan.test_commands.length > 0 && (
          <div>
            <p className="text-xs font-medium text-gray-500 uppercase mb-2">Test Commands</p>
            <ul className="space-y-1">
              {validation_plan.test_commands.map((cmd, i) => (
                <li key={i} className="font-mono text-xs bg-gray-900 text-green-400 px-3 py-1.5 rounded">
                  $ {cmd}
                </li>
              ))}
            </ul>
          </div>
        )}
      </SectionCard>

      {/* ── Mitigation & Rollback ─────────────────────────────────────────── */}
      <SectionCard title="Mitigation & Rollback">
        <dl className="text-sm grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div className="bg-gray-50 rounded-lg p-3 border border-gray-100">
            <dt className="text-xs text-gray-400 mb-1">Feature Flag</dt>
            <dd className="font-mono text-xs text-gray-800 break-all">{mitigation.feature_flag}</dd>
          </div>
          <div className="bg-gray-50 rounded-lg p-3 border border-gray-100">
            <dt className="text-xs text-gray-400 mb-1">Deploy Strategy</dt>
            <dd className="text-sm font-semibold capitalize text-gray-800">{mitigation.deployment_strategy}</dd>
          </div>
          <div className="bg-gray-50 rounded-lg p-3 border border-gray-100">
            <dt className="text-xs text-gray-400 mb-1">Rollback Complexity</dt>
            <dd className={`text-sm font-semibold capitalize ${
              mitigation.rollback_complexity === 'high' ? 'text-red-600' : 'text-green-600'
            }`}>{mitigation.rollback_complexity}</dd>
          </div>
          <div className="bg-gray-50 rounded-lg p-3 border border-gray-100">
            <dt className="text-xs text-gray-400 mb-1">Rollback Note</dt>
            <dd className="text-xs text-gray-600">{mitigation.rollback_note}</dd>
          </div>
        </dl>
      </SectionCard>

    </div>
  )
}
