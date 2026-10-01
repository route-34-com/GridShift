import { Mail } from 'lucide-react'
import { PageLayout } from '@/components/PageLayout'
import { RunGate } from '@/components/RunGate'
import { ErrorView } from '@/components/StateViews'
import { Badge, type Tone } from '@/components/ui/badge'
import { Card, CardBody, CardHeader } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { useAsync } from '@/hooks/useAsync'
import { api } from '@/lib/api'
import type { RunSummary } from '@/lib/types'

const STATUS: Record<string, { tone: Tone; text: string }> = {
  sent: { tone: 'positive', text: 'Sent' },
  disabled: { tone: 'neutral', text: 'Email not configured' },
  skipped: { tone: 'neutral', text: 'Not sent (manual run)' },
  'no recipients': { tone: 'warning', text: 'No recipients' },
}

function Preview({ run }: { run: RunSummary }) {
  const html = useAsync(api.email, [run.id])
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
        <div className="overflow-hidden rounded-xl border border-border bg-[#f4f6f5]">
          <iframe title="Daily plan email preview" srcDoc={html.data} sandbox="" className="h-[1100px] w-full" />
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
