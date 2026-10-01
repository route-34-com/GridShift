import { CalendarRange, Factory, LayoutDashboard, LineChart, Loader2, Mail, Moon, RefreshCw, Sun, X, Zap } from 'lucide-react'
import type { ReactNode } from 'react'
import { NavLink } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { useRun } from '@/hooks/RunContext'
import { useTheme } from '@/hooks/useTheme'
import { dateTime, relative } from '@/lib/format'
import { cn } from '@/lib/utils'

const NAV = [
  { to: '/', label: 'Overview', icon: LayoutDashboard },
  { to: '/forecast', label: 'Forecast', icon: LineChart },
  { to: '/schedule', label: 'Schedule', icon: CalendarRange },
  { to: '/email', label: 'Daily email', icon: Mail },
  { to: '/site', label: 'Site & machines', icon: Factory },
]

function Brand() {
  return (
    <div className="flex items-center gap-2.5">
      <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-[#0f3d2e]">
        <Zap className="h-5 w-5 text-[#34d399]" fill="currentColor" aria-hidden />
      </div>
      <div>
        <p className="text-[15px] leading-tight font-semibold text-fg">GridShift</p>
        <p className="text-xs leading-tight text-muted">Energy scheduling</p>
      </div>
    </div>
  )
}

function NavItems({ compact = false }: { compact?: boolean }) {
  return (
    <>
      {NAV.map(({ to, label, icon: Icon }) => (
        <NavLink
          key={to}
          to={to}
          end={to === '/'}
          className={({ isActive }) =>
            cn(
              'flex cursor-pointer items-center gap-3 rounded-lg text-sm font-medium transition-colors duration-200',
              compact ? 'shrink-0 px-3 py-2' : 'px-3 py-2.5',
              isActive ? 'bg-brand-soft text-brand' : 'text-muted hover:bg-surface-2 hover:text-fg',
            )
          }
        >
          <Icon className="h-4 w-4 shrink-0" aria-hidden />
          {label}
        </NavLink>
      ))}
    </>
  )
}

function ThemeToggle() {
  const [theme, toggle] = useTheme()
  return (
    <Button variant="ghost" size="icon" onClick={toggle} aria-label={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}>
      {theme === 'dark' ? <Sun className="h-4 w-4" aria-hidden /> : <Moon className="h-4 w-4" aria-hidden />}
    </Button>
  )
}

function RunButton() {
  const { running, runNow } = useRun()
  return (
    <Button variant="primary" onClick={() => void runNow()} disabled={running} aria-live="polite">
      {running ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> : <RefreshCw className="h-4 w-4" aria-hidden />}
      <span>{running ? 'Planning…' : 'Re-plan now'}</span>
    </Button>
  )
}

function RunError() {
  const { runError, dismissRunError } = useRun()
  if (!runError) return null
  return (
    <div role="alert" className="mb-6 flex items-start gap-3 rounded-lg border border-danger/30 bg-danger-soft px-4 py-3 text-sm">
      <p className="flex-1 text-fg">
        <span className="font-medium text-danger">Re-plan failed. </span>
        {runError} The last good plan is still shown.
      </p>
      <button type="button" onClick={dismissRunError} aria-label="Dismiss" className="cursor-pointer rounded text-muted hover:text-fg">
        <X className="h-4 w-4" aria-hidden />
      </button>
    </div>
  )
}

interface PageLayoutProps {
  title: string
  subtitle?: ReactNode
  children: ReactNode
}

export function PageLayout({ title, subtitle, children }: PageLayoutProps) {
  const { data } = useRun()
  const run = data?.run
  return (
    <div className="min-h-screen lg:pl-60">
      <aside className="fixed inset-y-0 left-0 z-20 hidden w-60 flex-col border-r border-border bg-surface px-4 py-5 lg:flex">
        <Brand />
        <nav className="mt-8 flex flex-col gap-1" aria-label="Main">
          <NavItems />
        </nav>
        {run && (
          <div className="mt-auto rounded-lg bg-surface-2 p-3 text-xs text-muted">
            <p className="font-medium text-fg">{run.site_name}</p>
            <p className="mt-1">Plan #{run.id} · {relative(run.created_at)}</p>
          </div>
        )}
      </aside>

      <header className="sticky top-0 z-10 border-b border-border bg-surface/90 backdrop-blur lg:hidden">
        <div className="flex items-center justify-between px-4 py-3">
          <Brand />
          <ThemeToggle />
        </div>
        <nav className="flex gap-1 overflow-x-auto px-3 pb-2" aria-label="Main">
          <NavItems compact />
        </nav>
      </header>

      <main className="mx-auto max-w-[1400px] px-4 py-6 sm:px-6 lg:px-8 lg:py-8">
        <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
          <div className="min-w-0">
            <h1 className="text-2xl font-semibold tracking-tight text-fg">{title}</h1>
            {subtitle && <div className="mt-1 text-sm text-muted">{subtitle}</div>}
          </div>
          <div className="flex items-center gap-2">
            {run && <span className="hidden text-xs text-muted sm:inline">Updated {dateTime(run.created_at)}</span>}
            <div className="hidden lg:block">
              <ThemeToggle />
            </div>
            <RunButton />
          </div>
        </div>
        <RunError />
        {children}
      </main>
    </div>
  )
}
