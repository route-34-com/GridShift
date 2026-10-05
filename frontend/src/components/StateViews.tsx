import { AlertTriangle, CalendarClock, Database, FlaskConical, Loader2, RefreshCw } from 'lucide-react'
import type { ReactNode } from 'react'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'

export function LoadingView() {
  return (
    <div className="space-y-6" role="status" aria-label="Loading">
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {Array.from({ length: 4 }, (_, i) => (
          <Skeleton key={i} className="h-[104px]" />
        ))}
      </div>
      <Skeleton className="h-[340px]" />
      <div className="grid gap-4 lg:grid-cols-2">
        <Skeleton className="h-[260px]" />
        <Skeleton className="h-[260px]" />
      </div>
    </div>
  )
}

interface MessageProps {
  title: string
  message: ReactNode
  action?: ReactNode
}

function Message({ icon, title, message, action }: MessageProps & { icon: ReactNode }) {
  return (
    <Card className="mx-auto flex max-w-xl flex-col items-center px-6 py-14 text-center">
      <div className="flex h-12 w-12 items-center justify-center rounded-full bg-surface-2">{icon}</div>
      <h2 className="mt-4 text-lg font-semibold text-fg">{title}</h2>
      <div className="mt-2 text-sm leading-relaxed text-muted">{message}</div>
      {action && <div className="mt-6">{action}</div>}
    </Card>
  )
}

export function ErrorView({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <Message
      icon={<AlertTriangle className="h-6 w-6 text-danger" aria-hidden />}
      title="Something went wrong"
      message={message}
      action={
        onRetry && (
          <Button onClick={onRetry}>
            <RefreshCw className="h-4 w-4" aria-hidden /> Try again
          </Button>
        )
      }
    />
  )
}

export function EmptyView({ running, onRun }: { running: boolean; onRun: () => void }) {
  return (
    <Message
      icon={<CalendarClock className="h-6 w-6 text-brand" aria-hidden />}
      title="No plan yet"
      message="Run the planner to fetch tomorrow's day-ahead prices and the 7-day weather forecast, then build the first schedule. It takes about 10 seconds."
      action={
        <Button variant="primary" onClick={onRun} disabled={running}>
          {running ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> : <RefreshCw className="h-4 w-4" aria-hidden />}
          {running ? 'Planning…' : 'Create first plan'}
        </Button>
      }
    />
  )
}

export function NoRealDataView({ canSwitch, onUseSample }: { canSwitch: boolean; onUseSample: () => void }) {
  return (
    <Message
      icon={<Database className="h-6 w-6 text-brand" aria-hidden />}
      title="Your real data isn't set up yet"
      message={
        <>
          Sample data is switched off, and there's no site set up for your company yet. GridShift needs the site details, the machine list and
          the load history in the data folder (<code>data/live</code>). Until then, switch sample data back on to explore with the Holcim sample.
        </>
      }
      action={
        canSwitch ? (
          <Button variant="primary" onClick={onUseSample}>
            <FlaskConical className="h-4 w-4" aria-hidden /> Turn sample data on
          </Button>
        ) : (
          <p className="text-xs text-muted">Ask an admin to turn sample data on.</p>
        )
      }
    />
  )
}
