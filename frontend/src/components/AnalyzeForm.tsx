import { useState, useEffect } from 'react'
import { fetchSymbols } from '../api'

interface Props {
  targetFile: string
  onSubmit: (symbol: string, description: string, changeType: string) => void
  loading: boolean
}

const CHANGE_TYPES = [
  { value: 'general', label: 'General' },
  { value: 'signature_change', label: 'Signature Change' },
  { value: 'schema_change', label: 'Schema / DB Change' },
  { value: 'api_change', label: 'API Contract Change' },
  { value: 'refactor', label: 'Refactor' },
  { value: 'deletion', label: 'Deletion' },
  { value: 'new_feature', label: 'New Feature' },
]

// Quick-start demo scenarios
const DEMO_SCENARIOS = [
  {
    label: '💳 process_payment (HIGH risk)',
    file: 'services/payment_service.py',
    symbol: 'process_payment',
    description: 'Add support for a new payment provider',
    changeType: 'api_change',
  },
  {
    label: '🧾 calculate_order_total (CRITICAL risk)',
    file: 'services/order_service.py',
    symbol: 'calculate_order_total',
    description: 'Add a tax_rate parameter and update return type to include pre/post-tax totals',
    changeType: 'signature_change',
  },
]

export default function AnalyzeForm({ targetFile, onSubmit, loading }: Props) {
  const [symbol, setSymbol] = useState('')
  const [description, setDescription] = useState('')
  const [changeType, setChangeType] = useState('general')
  const [symbols, setSymbols] = useState<string[]>([])
  const [symbolsLoading, setSymbolsLoading] = useState(false)

  // Load symbols whenever the selected file changes
  useEffect(() => {
    if (!targetFile) {
      setSymbols([])
      return
    }
    setSymbolsLoading(true)
    fetchSymbols(targetFile)
      .then(setSymbols)
      .finally(() => setSymbolsLoading(false))
  }, [targetFile])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!symbol.trim()) return
    onSubmit(symbol.trim(), description.trim(), changeType)
  }

  const applyScenario = (scenario: typeof DEMO_SCENARIOS[0]) => {
    setSymbol(scenario.symbol)
    setDescription(scenario.description)
    setChangeType(scenario.changeType)
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">

      {/* Demo quick-start */}
      <div>
        <p className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-2">
          Demo Scenarios
        </p>
        <div className="space-y-1.5">
          {DEMO_SCENARIOS.map((s) => (
            <button
              key={s.symbol}
              type="button"
              onClick={() => applyScenario(s)}
              className="w-full text-left px-3 py-2 rounded-md border border-dashed border-gray-300 text-xs text-gray-600 hover:bg-blue-50 hover:border-blue-300 hover:text-blue-700 transition-colors"
            >
              {s.label}
            </button>
          ))}
        </div>
      </div>

      <hr className="border-gray-100" />

      {/* Selected file */}
      <div>
        <label className="block text-xs font-medium text-gray-500 uppercase tracking-wider mb-1">
          Selected File
        </label>
        <div className="px-3 py-2 bg-gray-50 rounded-md text-sm text-gray-600 font-mono border border-gray-200 truncate">
          {targetFile || <span className="text-gray-400">Pick a file from the sidebar →</span>}
        </div>
      </div>

      {/* Symbol picker */}
      <div>
        <label className="block text-xs font-medium text-gray-500 uppercase tracking-wider mb-1">
          Symbol / Function <span className="text-red-500 normal-case font-normal">*</span>
        </label>
        {symbols.length > 0 ? (
          <select
            value={symbol}
            onChange={(e) => setSymbol(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
          >
            <option value="">— choose a symbol —</option>
            {symbols.map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
        ) : (
          <input
            type="text"
            value={symbol}
            onChange={(e) => setSymbol(e.target.value)}
            placeholder={
              symbolsLoading
                ? 'Loading symbols…'
                : targetFile
                  ? 'No symbols found — type manually'
                  : 'e.g. process_payment'
            }
            className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        )}
      </div>

      {/* Change type */}
      <div>
        <label className="block text-xs font-medium text-gray-500 uppercase tracking-wider mb-1">
          Change Type
        </label>
        <select
          value={changeType}
          onChange={(e) => setChangeType(e.target.value)}
          className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
        >
          {CHANGE_TYPES.map((ct) => (
            <option key={ct.value} value={ct.value}>{ct.label}</option>
          ))}
        </select>
      </div>

      {/* Change description */}
      <div>
        <label className="block text-xs font-medium text-gray-500 uppercase tracking-wider mb-1">
          Describe the Proposed Change
        </label>
        <textarea
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          rows={3}
          placeholder="e.g. Add a tax_rate parameter and update the return type to include pre/post-tax totals"
          className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
        />
      </div>

      <button
        type="submit"
        disabled={!symbol.trim() || loading}
        className="w-full py-2.5 px-4 bg-blue-600 text-white text-sm font-semibold rounded-md hover:bg-blue-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
      >
        {loading ? (
          <span className="flex items-center justify-center gap-2">
            <span className="inline-block w-3 h-3 border-2 border-white/40 border-t-white rounded-full animate-spin" />
            Analyzing…
          </span>
        ) : '🔍 Analyze Blast Radius'}
      </button>
    </form>
  )
}
