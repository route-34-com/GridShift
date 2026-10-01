import type { Block, Config, Hour, RunHeader, RunSummary, Status } from './types'

export class ApiError extends Error {
  status: number

  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response
  try {
    response = await fetch(path, init)
  } catch {
    throw new ApiError(0, 'Cannot reach the GridShift API. Check that the backend is running.')
  }
  if (!response.ok) {
    let detail = response.statusText
    try {
      const body = await response.json()
      detail = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail)
    } catch {
      detail = detail || `Request failed with status ${response.status}`
    }
    throw new ApiError(response.status, detail)
  }
  const type = response.headers.get('content-type') ?? ''
  return (type.includes('application/json') ? response.json() : response.text()) as Promise<T>
}

export const api = {
  status: () => request<Status>('/api/status'),
  latest: () => request<RunSummary>('/api/runs/latest'),
  hourly: () => request<{ plan: Hour[]; baseline: Hour[] }>('/api/runs/latest/hourly'),
  blocks: () => request<{ plan: Block[]; baseline: Block[] }>('/api/runs/latest/blocks'),
  email: () => request<string>('/api/runs/latest/email'),
  runs: () => request<RunHeader[]>('/api/runs'),
  config: () => request<Config>('/api/config'),
  run: (email = false) => request<RunSummary>(`/api/runs?email=${email}`, { method: 'POST' }),
}
