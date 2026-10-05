export type AlertLevel = 'error' | 'warning' | 'info'

export interface Alert {
  kind: string
  level: AlertLevel
  message: string
}

export interface Metrics {
  cost_eur: number
  // Absent in runs stored before peak charges were added.
  peak_charge_eur?: number
  total_cost_eur?: number
  import_kwh: number
  export_kwh: number
  renewable_used_kwh: number
  renewable_share: number
  co2_avoided_kg: number
  peak_import_kw: number
  unmet_kwh: number
}

export interface Day {
  date: string
  label: string
  start: string
  cost_eur: number
  baseline_cost_eur: number
  savings_eur: number
  renewable_kwh: number
  renewable_share: number
  avg_price: number
  price_estimated: boolean
  flexible_kwh: number
  outlook: string
  battery_note: string
}

export interface MachineSummary {
  id: string
  name: string
  type: 'always_on' | 'daily_quota' | 'deadline'
  power_kw: number
  scheduled_hours?: number
  required_hours?: number
  avg_price?: number | null
  baseline_avg_price?: number | null
}

export interface RunSummary {
  id: number
  created_at: string
  horizon_start: string
  horizon_end: string
  status: 'ok' | 'attention'
  site_name: string
  solver: { status: string; gap: number }
  summary: {
    optimized: Metrics
    baseline: Metrics
    savings_eur: number
    savings_pct: number
    peak_savings_eur?: number
    peak?: PeakRecord
  }
  daily: Day[]
  machines: MachineSummary[]
  alerts: Alert[]
  warnings: string[]
  sources: Record<string, string>
  email: { status: string; recipients: string[]; subject?: string }
  timezone: string
}

export interface Hour {
  ts: string
  price: number
  price_source: 'actual' | 'estimate'
  solar: number
  wind: number
  demand: number
  flexible: number
  charge: number
  discharge: number
  soc: number
  grid_import: number
  grid_export: number
  curtail: number
  unmet: number
}

export interface Block {
  machine_id: string
  machine_name: string
  start: string
  end: string
  hours: number
  energy_kwh: number
  avg_price: number
  renewable_share: number
  reason: string
}

export interface RunHeader {
  id: number
  created_at: string
  horizon_start: string
  status: 'ok' | 'attention' | 'failed'
}

export interface Status {
  running: boolean
  latest: RunHeader | null
  last_failure: { created_at: string; error: string; status: 'failed' } | null
}

export interface SiteConfig {
  name: string
  latitude: number
  longitude: number
  solar: { kwp: number; tilt: number; azimuth: number; performance_ratio: number }
  wind: { rated_kw: number; hub_height_m: number; power_curve: [number, number][] }
  battery: {
    capacity_kwh: number
    max_charge_kw: number
    max_discharge_kw: number
    efficiency: number
    min_soc: number
    initial_soc: number
  }
  grid: {
    max_import_kw: number
    max_export_kw: number
    fee_eur_per_kwh: number
    export_price_eur_per_kwh: number
    peak_charge_eur_per_kw_year: number
    peak_so_far_kw: number
  }
  co2_kg_per_kwh: number
  email_recipients: string[]
}

export interface MachineConfig {
  id: string
  name: string
  type: 'always_on' | 'daily_quota' | 'deadline'
  power_kw: number
  min_run_hours: number
  hours_per_day?: number
  total_hours?: number
  due?: string | null
  due_in_hours?: number | null
  earliest_start?: string | null
  start_in_hours?: number | null
}

export interface Config {
  site: SiteConfig
  machines: MachineConfig[]
}

export type Role = 'admin' | 'planner' | 'viewer'
export type UserStatus = 'active' | 'invited' | 'disabled'

export interface Me {
  id: number
  email: string
  name: string | null
  role: Role
  status: UserStatus
  created_at: string | null
  last_login_at: string | null
  permissions: string[]
}

export interface Account {
  id: number
  email: string
  name: string | null
  role: Role
  status: UserStatus
  created_at: string
  last_login_at: string | null
  you?: boolean
}

export interface LinkResult {
  emailed: boolean
  link?: string
  warning?: string
}

export interface AuditEntry {
  id: number
  at: string
  user_id: number | null
  user_email: string | null
  user_name: string | null
  action: string
  outcome: 'success' | 'failure'
  entity: string | null
  entity_id: string | null
  summary: string
  detail: Record<string, unknown> | null
  ip: string
  user_agent: string
}

export interface AuditPage {
  total: number
  entries: AuditEntry[]
}

export interface SetupStatus {
  needed: boolean
  allowed: boolean
  email: boolean
}

export interface PeakRecord {
  year: number
  record_kw: number
  source: 'meter' | 'settings'
  at: string | null
  settings_kw: number
  meter_kw: number | null
  charge_eur_per_kw_year: number
  annual_eur: number
  monthly_eur: number
  meter: { rows: number; start: string; end: string; interval_minutes: number; rows_this_year: number } | null
}
