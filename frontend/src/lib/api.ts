import type {
  Account,
  AuditPage,
  Block,
  Config,
  DatasetInfo,
  DatasetName,
  Hour,
  LinkResult,
  Me,
  PeakRecord,
  Role,
  RunHeader,
  RunSummary,
  SetupStatus,
  Status,
  TodayHour,
  UserStatus,
} from './types'

export class ApiError extends Error {
  status: number

  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

type Listener = () => void
const unauthorized = new Set<Listener>()

export function onUnauthorized(listener: Listener): () => void {
  unauthorized.add(listener)
  return () => unauthorized.delete(listener)
}

async function errorFrom(response: Response): Promise<ApiError> {
  let detail = response.statusText || `Request failed with status ${response.status}`
  try {
    const body = await response.json()
    if (typeof body.detail === 'string') detail = body.detail
  } catch {
    return new ApiError(response.status, detail)
  }
  return new ApiError(response.status, detail)
}

async function send(path: string, init?: RequestInit): Promise<Response> {
  let response: Response
  try {
    response = await fetch(path, { credentials: 'same-origin', ...init })
  } catch {
    throw new ApiError(0, 'Cannot reach the GridShift API. Check that the backend is running.')
  }
  if (!response.ok) {
    const error = await errorFrom(response)
    if (response.status === 401 && !path.startsWith('/api/auth/')) unauthorized.forEach((listener) => listener())
    throw error
  }
  return response
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await send(path, init)
  const type = response.headers.get('content-type') ?? ''
  return (type.includes('application/json') ? response.json() : response.text()) as Promise<T>
}

function json<T>(path: string, method: string, body?: unknown): Promise<T> {
  return request<T>(path, {
    method,
    headers: { 'content-type': 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body),
  })
}

export async function download(path: string): Promise<string> {
  const response = await send(path)
  const disposition = response.headers.get('content-disposition') ?? ''
  const name = /filename="([^"]+)"/.exec(disposition)?.[1] ?? 'gridshift-export'
  const url = URL.createObjectURL(await response.blob())
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = name
  document.body.appendChild(anchor)
  anchor.click()
  anchor.remove()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
  return name
}

export function query(params: Record<string, string | number | undefined | null>): string {
  const search = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== '') search.set(key, String(value))
  }
  const text = search.toString()
  return text ? `?${text}` : ''
}

export const api = {
  status: () => request<Status>('/api/status'),
  latest: () => request<RunSummary>('/api/runs/latest'),
  hourly: () => request<{ plan: Hour[]; baseline: Hour[]; today?: TodayHour[] }>('/api/runs/latest/hourly'),
  blocks: () => request<{ plan: Block[]; baseline: Block[] }>('/api/runs/latest/blocks'),
  email: () => request<string>('/api/runs/latest/email'),
  runs: () => request<RunHeader[]>('/api/runs'),
  config: () => request<Config>('/api/config'),
  run: (email = false) => request<RunSummary>(`/api/runs?email=${email}`, { method: 'POST' }),
  peak: () => request<PeakRecord>('/api/peak'),
  dataset: () => request<DatasetInfo>('/api/dataset'),
  setDataset: (active: DatasetName) => json<DatasetInfo>('/api/dataset', 'PUT', { active }),
  uploadMeter: (file: File) => request<PeakRecord>('/api/meter', { method: 'POST', body: file, headers: { 'content-type': 'text/csv' } }),
}

export const auth = {
  setupStatus: () => request<SetupStatus>('/api/auth/setup'),
  setup: (body: { email: string; password: string; name?: string }) => json<Me>('/api/auth/setup', 'POST', body),
  login: (email: string, password: string) => json<Me>('/api/auth/login', 'POST', { email, password }),
  logout: () => json<{ ok: boolean }>('/api/auth/logout', 'POST'),
  me: () => request<Me>('/api/auth/me'),
  inviteDetails: (token: string) => json<{ email: string; name: string | null; role: Role }>('/api/auth/invite', 'POST', { token }),
  acceptInvite: (body: { token: string; password: string; name?: string }) => json<Me>('/api/auth/accept-invite', 'POST', body),
  forgot: (email: string) => json<{ message: string }>('/api/auth/forgot-password', 'POST', { email }),
  reset: (token: string, password: string) => json<{ ok: boolean }>('/api/auth/reset-password', 'POST', { token, password }),
  profile: (name: string) => json<Me>('/api/auth/profile', 'PUT', { name }),
  password: (current: string, next: string) => json<{ ok: boolean }>('/api/auth/password', 'POST', { current, new: next }),
}

export const admin = {
  users: () => request<Account[]>('/api/users'),
  mailStatus: () => request<{ configured: boolean; host: string | null; sender: string | null }>('/api/users/mail-status'),
  testEmail: () => json<{ ok: boolean; to: string }>('/api/users/test-email', 'POST'),
  invite: (body: { email: string; role: Role; name?: string }) => json<LinkResult & { id: number }>('/api/users/invite', 'POST', body),
  resendInvite: (id: number) => json<LinkResult>(`/api/users/${id}/resend-invite`, 'POST'),
  resetLink: (id: number) => json<LinkResult>(`/api/users/${id}/reset-link`, 'POST'),
  update: (id: number, body: { name?: string; role?: Role; status?: UserStatus }) => json<Account>(`/api/users/${id}`, 'PUT', body),
  remove: (id: number) => json<{ ok: boolean }>(`/api/users/${id}`, 'DELETE'),
  audit: (params: Record<string, string | number | undefined>) => request<AuditPage>(`/api/audit${query(params)}`),
  auditActions: () => request<{ action: string; summary: string }[]>('/api/audit/actions'),
}

export const exportsApi = {
  run: (name: string, format: 'pdf' | 'csv' | 'xlsx') => download(`/api/exports/run/${name}${query({ format })}`),
  users: (format: 'pdf' | 'csv' | 'xlsx') => download(`/api/exports/users${query({ format })}`),
  audit: (format: 'pdf' | 'csv' | 'xlsx', filters: Record<string, string | number | undefined>) => download(`/api/exports/audit${query({ format, ...filters })}`),
}
