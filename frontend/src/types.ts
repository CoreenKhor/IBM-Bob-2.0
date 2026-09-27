/** Shared TypeScript types for the BlastRadiusReport structure. */

export interface FileEntry {
  path: string
  type: 'file' | 'dir'
}

export interface TreeResponse {
  root: string
  files: FileEntry[]
}

export interface AnalyzeRequest {
  target_file: string
  target_symbol: string
  change_description: string
  change_type: string
}

export interface ImpactedComponent {
  file: string
  symbol: string
  impact_type: 'direct_caller' | 'transitive_caller' | 'test_coverage' | 'data_schema'
  depth: number
  risk_level: 'high' | 'medium' | 'low'
  reason: string
}

export interface ContractHazard {
  type: 'api_contract' | 'db_schema'
  severity: 'high' | 'medium' | 'low'
  description: string
  file: string
  line: number
}

export interface RiskBreakdown {
  api_boundary: string
  data_persistence: string
  dependency_centrality: string
  test_coverage: string
  overall: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW'
}

export interface ValidationPlan {
  test_commands: string[]
  manual_checks: string[]
}

export interface Mitigation {
  feature_flag: string
  rollback_complexity: string
  rollback_note: string
  deployment_strategy: string
}

export interface ReportMeta {
  analyzed_target: string
  change_description: string
  change_type: string
  risk_level: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW'
  total_impacted_files: number
  direct_callers: number
  transitive_callers: number
  test_files_affected: number
  generated_at: string
}

export interface TargetInfo {
  file: string
  symbol: string
  kind?: string
  line_start: number
  line_end: number
  signature: string
  docstring?: string
}

// ── impact_categories — 7-category breakdown ─────────────────────────────────

export interface AffectedComponent {
  file: string
  symbol: string
  layer: string
  reason: string
  depth: number
  impact_type: string
}

export interface RelatedTest {
  file: string
  function: string
  test_type: string
  command: string
  reason: string
}

export interface RelatedAPI {
  http_method: string
  path: string
  file: string
  handler: string
  reason: string
}

export interface RelatedDB {
  table_name: string
  operation: string
  file: string
  line: number
  reason: string
}

export interface RiskArea {
  severity: 'critical' | 'high' | 'medium' | 'low'
  category: string
  title: string
  description: string
  affected_files: string[]
}

export interface TestingSuggestion {
  priority: 'must' | 'should' | 'consider'
  action: string
  detail: string
  command: string | null
}

export interface ImpactCategories {
  target: {
    file: string
    symbol: string
    layer: string
    signature: string
    docstring: string
  }
  change: {
    description: string
    type: string
  }
  risk_level: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW'
  risk_breakdown: RiskBreakdown
  directly_affected: AffectedComponent[]
  indirectly_affected: AffectedComponent[]
  related_tests: RelatedTest[]
  related_apis: RelatedAPI[]
  related_db: RelatedDB[]
  risk_areas: RiskArea[]
  testing_suggestions: TestingSuggestion[]
}

export interface BlastRadiusReport {
  meta: ReportMeta
  target: TargetInfo
  impacted_components: ImpactedComponent[]
  contract_hazards: ContractHazard[]
  risk_breakdown: RiskBreakdown
  validation_plan: ValidationPlan
  mitigation: Mitigation
  mermaid_diagram: string
  impact_categories: ImpactCategories
}
