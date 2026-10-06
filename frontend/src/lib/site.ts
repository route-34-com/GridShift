import type { SiteConfig } from './types'

/** A new site starts with no solar, wind or battery so nothing is assumed. */
export const EMPTY_SITE: SiteConfig = {
  name: '',
  latitude: 51.0,
  longitude: 10.0,
  solar: { kwp: 0, tilt: 30, azimuth: 0, performance_ratio: 0.85 },
  wind: { rated_kw: 0, hub_height_m: 100, power_curve: [[0, 0], [30, 0]] },
  battery: { capacity_kwh: 0, max_charge_kw: 0, max_discharge_kw: 0, efficiency: 0.95, min_soc: 0.1, initial_soc: 0.5 },
  grid: { max_import_kw: 1000, max_export_kw: 0, fee_eur_per_kwh: 0, export_price_eur_per_kwh: 0, peak_charge_eur_per_kw_year: 0, peak_so_far_kw: 0 },
  co2_kg_per_kwh: 0.38,
  email_recipients: [],
}
