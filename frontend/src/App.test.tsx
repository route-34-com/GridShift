import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import App from './App'
import { json, mockApi, run } from './test/mockApi'

afterEach(() => {
  vi.unstubAllGlobals()
  window.history.pushState({}, '', '/')
})

describe('App', () => {
  it('shows savings and alerts on the overview', async () => {
    mockApi()
    render(<App />)
    expect(await screen.findByText('Saved this week')).toBeInTheDocument()
    expect(screen.getAllByText(run.site_name).length).toBeGreaterThan(0)
    expect(screen.getByText('7-day outlook')).toBeInTheDocument()
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

  it('switches the schedule between plan and baseline', async () => {
    mockApi()
    window.history.pushState({}, '', '/schedule')
    render(<App />)
    const baseline = await screen.findByRole('radio', { name: 'Run-as-needed' })
    await userEvent.click(baseline)
    await waitFor(() => expect(baseline).toHaveAttribute('aria-checked', 'true'))
  })
})
