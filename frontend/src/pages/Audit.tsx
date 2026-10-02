import { ChevronDown, ChevronLeft, ChevronRight, ChevronUp, Search, X } from 'lucide-react'
import { Fragment, useEffect, useMemo, useState } from 'react'
import { ExportMenu } from '@/components/ExportMenu'
import { PageLayout } from '@/components/PageLayout'
import { ErrorView } from '@/components/StateViews'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardBody } from '@/components/ui/card'
import { Field, Input, Select } from '@/components/ui/field'
import { Skeleton } from '@/components/ui/skeleton'
import { useAsync } from '@/hooks/useAsync'
import { admin, exportsApi } from '@/lib/api'
import { dateTime, num } from '@/lib/format'
import type { AuditEntry } from '@/lib/types'

const PAGE = 50
const CATEGORIES = [
  { value: '', label: 'All activity' },
  { value: 'auth', label: 'Sign-in & passwords' },
  { value: 'user', label: 'User management' },
  { value: 'account', label: 'Own account' },
  { value: 'plan', label: 'Planning runs' },
  { value: 'export', label: 'Exports' },
  { value: 'email', label: 'Emails' },
]

interface Filters {
  q: string
  category: string
  user_id: string
  outcome: string
  from: string
  to: string
}

const EMPTY: Filters = { q: '', category: '', user_id: '', outcome: '', from: '', to: '' }

function browser(agent: string): string {
  if (!agent) return '—'
  if (agent === 'GridShift scheduler') return agent
  const name = /Edg\//.test(agent) ? 'Edge' : /Chrome\//.test(agent) ? 'Chrome' : /Firefox\//.test(agent) ? 'Firefox' : /Safari\//.test(agent) ? 'Safari' : 'Other'
  const os = /Windows/.test(agent) ? 'Windows' : /Mac OS/.test(agent) ? 'macOS' : /Android/.test(agent) ? 'Android' : /iPhone|iPad/.test(agent) ? 'iOS' : /Linux/.test(agent) ? 'Linux' : ''
  return os ? `${name} on ${os}` : name
}

function value(v: unknown): string {
  if (v === null || v === undefined || v === '') return '—'
  if (typeof v === 'object') return JSON.stringify(v)
  return String(v)
}

function Detail({ entry }: { entry: AuditEntry }) {
  const detail = entry.detail ?? {}
  const before = detail.before as Record<string, unknown> | undefined
  const after = detail.after as Record<string, unknown> | undefined
  const rest = Object.entries(detail).filter(([k]) => k !== 'before' && k !== 'after')
  return (
    <div className="grid gap-4 bg-surface-2/60 px-4 py-4 text-sm md:grid-cols-2">
      <dl className="space-y-1.5">
        <div className="flex gap-3">
          <dt className="w-28 shrink-0 text-muted">Time (UTC)</dt>
          <dd className="font-mono text-xs text-fg">{entry.at}</dd>
        </div>
        <div className="flex gap-3">
          <dt className="w-28 shrink-0 text-muted">Action code</dt>
          <dd className="font-mono text-xs text-fg">{entry.action}</dd>
        </div>
        {entry.entity && (
          <div className="flex gap-3">
            <dt className="w-28 shrink-0 text-muted">Target</dt>
            <dd className="text-fg">
              {entry.entity} #{entry.entity_id}
            </dd>
          </div>
        )}
        <div className="flex gap-3">
          <dt className="w-28 shrink-0 text-muted">IP address</dt>
          <dd className="font-mono text-xs text-fg">{entry.ip || '—'}</dd>
        </div>
        <div className="flex gap-3">
          <dt className="w-28 shrink-0 text-muted">Browser</dt>
          <dd className="text-xs break-all text-fg">{entry.user_agent || '—'}</dd>
        </div>
      </dl>
      <div className="space-y-3">
        {before && after && (
          <table className="w-full text-xs">
            <thead>
              <tr className="text-left text-muted">
                <th className="pb-1 font-medium">Field</th>
                <th className="pb-1 font-medium">Before</th>
                <th className="pb-1 font-medium">After</th>
              </tr>
            </thead>
            <tbody>
              {Object.keys(after).map((key) => (
                <tr key={key}>
                  <td className="py-0.5 pr-3 text-muted">{key}</td>
                  <td className="py-0.5 pr-3 text-danger line-through">{value(before[key])}</td>
                  <td className="py-0.5 text-positive">{value(after[key])}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        {rest.length > 0 && (
          <dl className="space-y-1.5">
            {rest.map(([key, v]) => (
              <div key={key} className="flex gap-3">
                <dt className="w-32 shrink-0 text-muted">{key.replace(/_/g, ' ')}</dt>
                <dd className="min-w-0 text-xs break-all text-fg">{value(v)}</dd>
              </div>
            ))}
          </dl>
        )}
        {!before && rest.length === 0 && <p className="text-muted">No extra details.</p>}
      </div>
    </div>
  )
}

export function AuditPage() {
  const [filters, setFilters] = useState<Filters>(EMPTY)
  const [search, setSearch] = useState('')
  const [offset, setOffset] = useState(0)
  const [open, setOpen] = useState<number | null>(null)
  const users = useAsync(admin.users)

  useEffect(() => {
    const timer = setTimeout(() => {
      setFilters((f) => (f.q === search ? f : { ...f, q: search }))
      setOffset(0)
    }, 300)
    return () => clearTimeout(timer)
  }, [search])

  const params = useMemo(() => ({ ...filters, limit: PAGE, offset }), [filters, offset])
  const page = useAsync(() => admin.audit(params), [params])
  const active = Object.values(filters).some(Boolean)
  const total = page.data?.total ?? 0
  const set = (key: keyof Filters, v: string) => {
    setFilters((f) => ({ ...f, [key]: v }))
    setOffset(0)
  }
  const exportFilters = Object.fromEntries(Object.entries(filters).filter(([, v]) => v))

  return (
    <PageLayout
      title="Audit log"
      subtitle="Every sign-in, account change, planning run, export and email, with who, when and from where"
      planActions={false}
      actions={<ExportMenu label={active ? 'Export filtered' : 'Export'} options={[{ label: active ? 'Matching entries' : 'All entries', formats: ['xlsx', 'csv'], run: (f) => exportsApi.audit(f, exportFilters) }]} />}
    >
      <div className="space-y-4">
        <Card>
          <CardBody className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 2xl:grid-cols-6">
            <div className="sm:col-span-2 lg:col-span-1 2xl:col-span-2">
              <Field label="Search">
                {(id) => (
                  <div className="relative">
                    <Search className="pointer-events-none absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2 text-muted" aria-hidden />
                    <Input id={id} value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Email, IP, action or detail" className="pl-9" />
                  </div>
                )}
              </Field>
            </div>
            <Field label="Activity">
              {(id) => (
                <Select id={id} value={filters.category} onChange={(e) => set('category', e.target.value)}>
                  {CATEGORIES.map((c) => (
                    <option key={c.value} value={c.value}>
                      {c.label}
                    </option>
                  ))}
                </Select>
              )}
            </Field>
            <Field label="User">
              {(id) => (
                <Select id={id} value={filters.user_id} onChange={(e) => set('user_id', e.target.value)}>
                  <option value="">Everyone</option>
                  {(users.data ?? []).map((u) => (
                    <option key={u.id} value={u.id}>
                      {u.name ? `${u.name} (${u.email})` : u.email}
                    </option>
                  ))}
                </Select>
              )}
            </Field>
            <Field label="Outcome">
              {(id) => (
                <Select id={id} value={filters.outcome} onChange={(e) => set('outcome', e.target.value)}>
                  <option value="">Any</option>
                  <option value="success">Success</option>
                  <option value="failure">Failure</option>
                </Select>
              )}
            </Field>
            <div className="grid grid-cols-2 gap-2">
              <Field label="From">{(id) => <Input id={id} type="date" value={filters.from} max={filters.to || undefined} onChange={(e) => set('from', e.target.value)} />}</Field>
              <Field label="To">{(id) => <Input id={id} type="date" value={filters.to} min={filters.from || undefined} onChange={(e) => set('to', e.target.value)} />}</Field>
            </div>
          </CardBody>
        </Card>

        <div className="flex flex-wrap items-center justify-between gap-3 text-sm">
          <p className="text-muted">
            <span className="font-medium text-fg">{num(total)}</span> {total === 1 ? 'entry' : 'entries'}
            {active && ' match your filters'}
          </p>
          {active && (
            <Button
              size="sm"
              variant="ghost"
              onClick={() => {
                setFilters(EMPTY)
                setSearch('')
                setOffset(0)
              }}
            >
              <X className="h-4 w-4" aria-hidden /> Clear filters
            </Button>
          )}
        </div>

        {page.error ? (
          <ErrorView message={page.error.message} onRetry={() => void page.reload()} />
        ) : (
          <Card className="overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full min-w-[960px] text-sm">
                <thead>
                  <tr className="border-b border-border bg-surface-2/50 text-left text-xs text-muted">
                    <th className="px-4 py-2.5 font-medium">Time</th>
                    <th className="px-4 py-2.5 font-medium">User</th>
                    <th className="px-4 py-2.5 font-medium">What happened</th>
                    <th className="px-4 py-2.5 font-medium">Outcome</th>
                    <th className="px-4 py-2.5 font-medium">IP address</th>
                    <th className="px-4 py-2.5 font-medium">Browser</th>
                    <th className="w-10 px-4 py-2.5" />
                  </tr>
                </thead>
                <tbody>
                  {page.loading && !page.data
                    ? Array.from({ length: 6 }, (_, i) => (
                        <tr key={i}>
                          <td colSpan={7} className="px-4 py-2">
                            <Skeleton className="h-8" />
                          </td>
                        </tr>
                      ))
                    : (page.data?.entries ?? []).map((entry) => (
                        <Fragment key={entry.id}>
                          <tr
                            className="cursor-pointer border-b border-border transition-colors hover:bg-surface-2/50"
                            onClick={() => setOpen(open === entry.id ? null : entry.id)}
                            aria-expanded={open === entry.id}
                          >
                            <td className="px-4 py-2.5 whitespace-nowrap text-muted">{dateTime(entry.at)}</td>
                            <td className="px-4 py-2.5">
                              <p className="font-medium text-fg">{entry.user_name || entry.user_email || (entry.user_agent === 'GridShift scheduler' ? 'System' : 'Unknown visitor')}</p>
                              {entry.user_name && <p className="text-xs text-muted">{entry.user_email}</p>}
                            </td>
                            <td className="px-4 py-2.5">
                              <p className="text-fg">{entry.summary}</p>
                              <p className="font-mono text-[11px] text-muted">{entry.action}</p>
                            </td>
                            <td className="px-4 py-2.5">
                              <Badge tone={entry.outcome === 'success' ? 'positive' : 'danger'}>{entry.outcome}</Badge>
                            </td>
                            <td className="px-4 py-2.5 font-mono text-xs text-muted">{entry.ip || '—'}</td>
                            <td className="px-4 py-2.5 text-xs text-muted">{browser(entry.user_agent)}</td>
                            <td className="px-4 py-2.5 text-muted">
                              {open === entry.id ? <ChevronUp className="h-4 w-4" aria-hidden /> : <ChevronDown className="h-4 w-4" aria-hidden />}
                            </td>
                          </tr>
                          {open === entry.id && (
                            <tr className="border-b border-border">
                              <td colSpan={7} className="p-0">
                                <Detail entry={entry} />
                              </td>
                            </tr>
                          )}
                        </Fragment>
                      ))}
                  {page.data && page.data.entries.length === 0 && (
                    <tr>
                      <td colSpan={7} className="px-4 py-12 text-center text-muted">
                        No activity matches these filters.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
            {total > PAGE && (
              <div className="flex items-center justify-between border-t border-border px-4 py-3 text-sm">
                <p className="text-muted">
                  {offset + 1}–{Math.min(offset + PAGE, total)} of {num(total)}
                </p>
                <div className="flex gap-2">
                  <Button size="sm" disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - PAGE))}>
                    <ChevronLeft className="h-4 w-4" aria-hidden /> Newer
                  </Button>
                  <Button size="sm" disabled={offset + PAGE >= total} onClick={() => setOffset(offset + PAGE)}>
                    Older <ChevronRight className="h-4 w-4" aria-hidden />
                  </Button>
                </div>
              </div>
            )}
          </Card>
        )}
      </div>
    </PageLayout>
  )
}
