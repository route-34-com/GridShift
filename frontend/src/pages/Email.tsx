import { Mail } from 'lucide-react'
import { PageLayout } from '@/components/PageLayout'
import { RunGate } from '@/components/RunGate'
import { ErrorView } from '@/components/StateViews'
import { Badge, type Tone } from '@/components/ui/badge'
import { Card, CardBody, CardHeader } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { useAsync } from '@/hooks/useAsync'
import { useIsDark } from '@/hooks/useTheme'
import { api } from '@/lib/api'
import type { RunSummary } from '@/lib/types'

const STATUS: Record<string, { tone: Tone; text: string }> = {
  sent: { tone: 'positive', text: 'Sent' },
  disabled: { tone: 'neutral', text: 'Email not configured' },
  skipped: { tone: 'neutral', text: 'Not sent (manual run)' },
  'no recipients': { tone: 'warning', text: 'No recipients' },
}

const SCROLLBAR = (thumb: string) =>
  `html{scrollbar-width:thin;scrollbar-color:${thumb} transparent}::-webkit-scrollbar{width:10px;height:10px}` +
  `::-webkit-scrollbar-thumb{background:${thumb};border:3px solid transparent;border-radius:999px;background-clip:content-box}`

/** The email's own light colours and their dark-mode stand-ins, so the preview follows the dashboard theme. */
const DARK: [string, string, string][] = [
  ['background', '#ffffff', '#0e1528'],
  ['background', '#f4f6f5', '#070c18'],
  ['background', '#f4f8f6', '#151d33'],
  ['background', '#e8f5ee', '#0f2a22'],
  ['background', '#fff4e5', '#2a1d0b'],
  ['color', '#1c2421', '#e6ecf7'],
  ['color', '#5b6b64', '#97a3bd'],
  ['color', '#3d4a44', '#c3cbdc'],
  ['color', '#7a8a83', '#8a97b6'],
  ['color', '#2c6b4f', '#6ee7b7'],
  ['color', '#17663f', '#34d399'],
  ['color', '#8a4b00', '#fbbf24'],
  ['color', '#5c3900', '#fcd34d'],
  ['border', '#e3e8e5', '#243052'],
  ['border', '#f0f2f1', '#1c2540'],
  ['border', '#f5c98b', '#6b4a12'],
]

function darkCss(): string {
  return DARK.map(([prop, from, to]) => {
    if (prop === 'border') return `[style*="${from}"]{border-color:${to}!important}`
    return `[style*="${prop}:${from}"]{${prop}:${to}!important}`
  }).join('')
}

/** Style the preview document: thin scrollbar always, dark palette when the dashboard is dark. */
function themed(html: string, dark: boolean): string {
  const css = dark ? SCROLLBAR('#2d3b5e') + 'html{color-scheme:dark;background:#070c18}' + darkCss() : SCROLLBAR('#c3cbdb')
  return `${html}<style>${css}</style>`
}

function Preview({ run }: { run: RunSummary }) {
  const html = useAsync(api.email, [run.id])
  const dark = useIsDark()
  const status = run.email.status.startsWith('failed')
    ? { tone: 'danger' as Tone, text: 'Delivery failed' }
    : (STATUS[run.email.status] ?? { tone: 'neutral' as Tone, text: run.email.status })
  return (
    <div className="space-y-6">
      <Card>
        <CardHeader
          title="Daily plan email"
          description="Sent to the plant team after each daily run at about 13:30, once prices for tomorrow are published."
          action={<Badge tone={status.tone}>{status.text}</Badge>}
        />
        <CardBody className="space-y-2 pt-3 text-sm">
          <p className="flex flex-wrap items-center gap-2 text-muted">
            <Mail className="h-4 w-4" aria-hidden />
            To: <span className="text-fg">{run.email.recipients.join(', ') || 'no recipients configured'}</span>
          </p>
          {run.email.status.startsWith('failed') && <p className="text-danger">{run.email.status}</p>}
        </CardBody>
      </Card>
      {html.error ? (
        <ErrorView message={html.error.message} onRetry={() => void html.reload()} />
      ) : html.loading || !html.data ? (
        <Skeleton className="h-[900px]" />
      ) : (
        <div className="overflow-hidden rounded-lg border border-border bg-bg">
          <iframe title="Daily plan email preview" srcDoc={themed(html.data, dark)} sandbox="" className="h-[1100px] w-full" />
        </div>
      )}
    </div>
  )
}

export function Email() {
  return (
    <PageLayout title="Daily email" subtitle="What the plant manager receives every afternoon">
      <RunGate>{({ run }) => <Preview run={run} />}</RunGate>
    </PageLayout>
  )
}
