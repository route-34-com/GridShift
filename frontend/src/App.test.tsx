import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import App from './App'
import { json, mockApi, run } from './test/mockApi'

afterEach(() => {
  vi.unstubAllGlobals()
  window.history.pushState({}, '', '/')
})

const SITE_CONFIG = {
  site: {
    name: 'Werk',
    latitude: 48.8,
    longitude: 9.2,
    solar: { kwp: 1500, tilt: 25, azimuth: 0, performance_ratio: 0.85 },
    wind: { rated_kw: 0, hub_height_m: 100, power_curve: [[0, 0], [30, 0]] },
    battery: { capacity_kwh: 1000, max_charge_kw: 500, max_discharge_kw: 500, efficiency: 0.95, min_soc: 0.1, initial_soc: 0.5 },
    grid: { max_import_kw: 2500, max_export_kw: 1500, fee_eur_per_kwh: 0.09, export_price_eur_per_kwh: 0.06, peak_charge_eur_per_kw_year: 120, peak_so_far_kw: 1200 },
    co2_kg_per_kwh: 0.38,
    email_recipients: [],
  },
  machines: [],
}
const SETTINGS_PEAK = { year: 2026, source: 'settings', at: null, settings_kw: 1200, meter_kw: null, charge_eur_per_kw_year: 120, meter: null }

describe('App', () => {
  it('shows savings and alerts on the overview', async () => {
    mockApi()
    render(<App />)
    expect(await screen.findByText('Saved this week')).toBeInTheDocument()
    expect(screen.getAllByText(run.site_name).length).toBeGreaterThan(0)
    expect(screen.getByText('7-day outlook')).toBeInTheDocument()
  })

  it('shows the highest grid draw against the yearly record', async () => {
    const { optimized } = run.summary
    const withPeak = {
      ...run,
      summary: {
        ...run.summary,
        optimized: { ...optimized, peak_charge_eur: 0, total_cost_eur: optimized.cost_eur },
        peak_savings_eur: 0,
        peak: {
          year: 2026,
          record_kw: 2000,
          source: 'meter',
          at: '2026-02-16T06:15:00+00:00',
          settings_kw: 1200,
          meter_kw: 2000,
          charge_eur_per_kw_year: 120,
          annual_eur: 240000,
          monthly_eur: 20000,
          meter: null,
        },
      },
    }
    mockApi({ '/api/runs/latest': () => json(withPeak) })
    render(<App />)
    expect(await screen.findByText(/Under this year's 2,000 kW record/)).toBeInTheDocument()
    expect(screen.getByText('Peak charge per month')).toBeInTheDocument()
    expect(screen.getByText('€20,000')).toBeInTheDocument()
  })

  it('offers to create the first plan when none exists', async () => {
    const fetchMock = mockApi({
      '/api/runs/latest': () => json({ detail: 'No plan yet. Run the planner to create the first one.' }, 404),
      '/api/runs/latest/hourly': () => json({ detail: 'No plan yet.' }, 404),
      '/api/runs/latest/blocks': () => json({ detail: 'No plan yet.' }, 404),
      '/api/runs': () => json({ detail: 'Planning run failed: simulated outage' }, 502),
    })
    render(<App />)
    const button = await screen.findByRole('button', { name: /create first plan/i })
    await userEvent.click(button)
    expect(await screen.findByRole('alert')).toHaveTextContent('simulated outage')
    expect(fetchMock).toHaveBeenCalledWith('/api/runs?email=false', expect.objectContaining({ method: 'POST' }))
  })

  it('explains when the API is unreachable', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => Promise.reject(new TypeError('Failed to fetch'))))
    render(<App />)
    expect(await screen.findByText(/cannot reach the gridshift api/i)).toBeInTheDocument()
  })

  it('shows the last failure above the empty state', async () => {
    mockApi({
      '/api/status': () => json({ running: false, latest: { id: 1, status: 'failed' }, last_failure: { status: 'failed', error: 'weather down', created_at: '2026-10-01T11:30:00Z' } }),
      '/api/runs/latest': () => json({ detail: 'No plan yet.' }, 404),
      '/api/runs/latest/hourly': () => json({ detail: 'No plan yet.' }, 404),
      '/api/runs/latest/blocks': () => json({ detail: 'No plan yet.' }, 404),
    })
    render(<App />)
    expect(await screen.findByText(/last planning run failed: weather down/i)).toBeInTheDocument()
  })

  it('uploads meter data and shows the new yearly peak', async () => {
    let peak: Record<string, unknown> = { ...SETTINGS_PEAK, record_kw: 1200, annual_eur: 144000, monthly_eur: 12000 }
    const metered = {
      ...SETTINGS_PEAK,
      record_kw: 1248,
      source: 'meter',
      at: '2026-02-16T06:15:00+00:00',
      meter_kw: 1248,
      annual_eur: 149760,
      monthly_eur: 12480,
      meter: { rows: 26204, start: '2025-12-31T23:00:00+00:00', end: '2026-09-30T21:45:00+00:00', interval_minutes: 15, rows_this_year: 26204 },
    }
    const fetchMock = mockApi({
      '/api/config': () => json(SITE_CONFIG),
      '/api/peak': () => json(peak),
      '/api/meter': () => {
        peak = metered
        return json(metered)
      },
    })
    window.history.pushState({}, '', '/site')
    render(<App />)
    expect(await screen.findByText('€12,000')).toBeInTheDocument()
    const input = document.getElementById('meter-file') as HTMLInputElement
    await userEvent.upload(input, new File(['timestamp,import_kw\n'], 'meter.csv', { type: 'text/csv' }))
    expect(await screen.findByRole('status')).toHaveTextContent('Highest draw in 2026: 1,248 kW')
    expect(await screen.findByText('€12,480')).toBeInTheDocument()
    expect(fetchMock).toHaveBeenCalledWith('/api/meter', expect.objectContaining({ method: 'POST' }))
  })

  it('shows the peak to viewers without the upload button', async () => {
    const peak = { ...SETTINGS_PEAK, record_kw: 1200, annual_eur: 144000, monthly_eur: 12000 }
    mockApi({ '/api/config': () => json(SITE_CONFIG), '/api/peak': () => json(peak) }, 'viewer')
    window.history.pushState({}, '', '/site')
    render(<App />)
    expect(await screen.findByText('€12,000')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /Upload meter data/ })).not.toBeInTheDocument()
  })

  it('shows sunlight and wind on the forecast', async () => {
    const hourly = run.hourly.map((h, i) => ({ ...h, sunlight_w_m2: i % 24 === 12 ? 650 : 0, cloud_cover_pct: 30, wind_ms: 6, temperature_c: 12 }))
    mockApi({
      '/api/config': () => json(SITE_CONFIG),
      '/api/runs/latest/hourly': () => json({ plan: hourly, baseline: hourly }),
    })
    window.history.pushState({}, '', '/forecast')
    render(<App />)
    await userEvent.click(await screen.findByRole('tab', { name: /Sunlight/ }))
    expect(await screen.findByText(/Brightest hour 650 W\/m², 30% cloud cover on average/)).toBeInTheDocument()
    await userEvent.click(screen.getByRole('tab', { name: /Wind/ }))
    expect(screen.getByRole('tab', { name: /Wind/ })).toHaveAttribute('aria-selected', 'true')
    expect(screen.getByText(/No wind turbine is configured/)).toBeInTheDocument()
  })

  it('narrows the forecast to tomorrow', async () => {
    mockApi({ '/api/config': () => json(SITE_CONFIG) })
    window.history.pushState({}, '', '/forecast')
    render(<App />)
    expect(await screen.findByText(/expected over the week/)).toBeInTheDocument()
    await userEvent.selectOptions(screen.getByRole('combobox', { name: 'Time range' }), 'Today + tomorrow')
    expect(await screen.findByText(/expected for tomorrow/)).toBeInTheDocument()
    expect(window.location.search).toContain('range=day')
  })

  it('asks for a re-plan when a stored run has no weather', async () => {
    mockApi({ '/api/config': () => json(SITE_CONFIG) })
    window.history.pushState({}, '', '/forecast')
    render(<App />)
    await userEvent.click(await screen.findByRole('tab', { name: /Sunlight/ }))
    expect(await screen.findByText(/appear here after the next re-plan/)).toBeInTheDocument()
  })

  it('switches the Germany clock between 24 and 12 hours', async () => {
    mockApi()
    render(<App />)
    const twelve = await screen.findByRole('radio', { name: '12h' })
    expect(screen.getByRole('radio', { name: '24h' })).toHaveAttribute('aria-checked', 'true')
    await userEvent.click(twelve)
    expect(twelve).toHaveAttribute('aria-checked', 'true')
    expect(localStorage.getItem('gridshift-clock')).toBe('12h')
    expect(screen.getByLabelText('Date and time in Germany')).toHaveTextContent(/[AP]M/)
    await userEvent.click(screen.getByRole('radio', { name: '24h' }))
    expect(localStorage.getItem('gridshift-clock')).toBe('24h')
  })

  it('shows the sample data switch and label', async () => {
    const sample = { active: 'sample', switchable: true, sample: { available: true }, live: { available: false } }
    const fetchMock = mockApi({ '/api/dataset': (init) => json(init?.method === 'PUT' ? { ...sample, active: 'live' } : sample) })
    render(<App />)
    const toggle = await screen.findByRole('switch', { name: 'Sample data' })
    expect(toggle).toHaveAttribute('aria-checked', 'true')
    expect(screen.getAllByText('Sample data').length).toBeGreaterThan(1)
    await userEvent.click(toggle)
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith('/api/dataset', expect.objectContaining({ method: 'PUT', body: JSON.stringify({ active: 'live' }) })))
  })

  it('lets viewers see but not flip the switch', async () => {
    mockApi({ '/api/dataset': () => json({ active: 'sample', switchable: true, sample: { available: true }, live: { available: false } }) }, 'viewer')
    render(<App />)
    expect(await screen.findByRole('switch', { name: 'Sample data' })).toBeDisabled()
  })

  it('explains when real data is not set up', async () => {
    mockApi({
      '/api/dataset': () => json({ active: 'live', switchable: true, sample: { available: true }, live: { available: false } }),
      '/api/runs/latest': () => json({ detail: 'No plan yet.' }, 404),
      '/api/status': () => json({ running: false, latest: null, last_failure: null }),
    })
    render(<App />)
    expect(await screen.findByText("Your real data isn't set up yet")).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Turn sample data on/ })).toBeInTheDocument()
  })

  it('switches the schedule between plan and baseline', async () => {
    mockApi()
    window.history.pushState({}, '', '/schedule')
    render(<App />)
    const baseline = await screen.findByRole('radio', { name: 'Run-as-needed' })
    await userEvent.click(baseline)
    await waitFor(() => expect(baseline).toHaveAttribute('aria-checked', 'true'))
  })
})
