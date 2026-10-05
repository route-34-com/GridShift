import { vi } from 'vitest'
import fixture from './run.json'

type Handler = (init?: RequestInit) => Response

const json = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status, headers: { 'content-type': 'application/json' } })

export const run = fixture

const PERMISSIONS = {
  admin: ['audit.view', 'config.view', 'email.test', 'export', 'meter.upload', 'plan.run', 'plan.view', 'users.manage'],
  planner: ['config.view', 'export', 'meter.upload', 'plan.run', 'plan.view'],
  viewer: ['config.view', 'export', 'plan.view'],
}

export type TestRole = keyof typeof PERMISSIONS

export function me(role: TestRole = 'admin') {
  return { id: 1, email: `${role}@example.com`, name: `Test ${role}`, role, status: 'active', created_at: null, last_login_at: null, permissions: PERMISSIONS[role] }
}

export function mockApi(overrides: Record<string, Handler> = {}, role: TestRole | null = 'admin') {
  const routes: Record<string, Handler> = {
    '/api/auth/setup': () => json({ needed: false, allowed: true, email: false }),
    '/api/auth/me': () => (role ? json(me(role)) : json({ detail: 'Please sign in.' }, 401)),
    '/api/status': () => json({ running: false, latest: { id: run.id, status: run.status }, last_failure: null }),
    '/api/runs/latest': () => json(run),
    '/api/runs/latest/hourly': () => json({ plan: run.hourly, baseline: run.baseline_hourly }),
    '/api/runs/latest/blocks': () => json({ plan: run.blocks, baseline: run.baseline_blocks }),
    '/api/runs/latest/email': () => new Response('<p>email</p>', { headers: { 'content-type': 'text/html' } }),
    ...overrides,
  }
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const path = String(input).split('?')[0]
    const handler = routes[path]
    if (!handler) return json({ detail: `unmocked ${path}` }, 500)
    return handler(init)
  })
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

export { json }
