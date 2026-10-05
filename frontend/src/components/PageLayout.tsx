import {
  CalendarRange,
  ChevronsUpDown,
  Factory,
  LayoutDashboard,
  LineChart,
  Loader2,
  LogOut,
  Mail,
  Moon,
  RefreshCw,
  ScrollText,
  Sun,
  UserCog,
  Users,
  X,
  Zap,
  type LucideIcon,
} from 'lucide-react'
import type { ReactNode } from 'react'
import { NavLink, useNavigate } from 'react-router-dom'
import { GermanyClock } from '@/components/GermanyClock'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { MenuContent, MenuItem, MenuRoot, MenuSeparator, MenuTrigger } from '@/components/ui/menu'
import { useAuth } from '@/hooks/AuthContext'
import { useRun } from '@/hooks/RunContext'
import { useTheme } from '@/hooks/useTheme'
import { dateTime, relative } from '@/lib/format'
import { cn } from '@/lib/utils'

interface NavEntry {
  to: string
  label: string
  icon: LucideIcon
  permission?: string
}

const SECTIONS: { title: string; items: NavEntry[] }[] = [
  {
    title: 'Planning',
    items: [
      { to: '/', label: 'Overview', icon: LayoutDashboard },
      { to: '/forecast', label: 'Forecast', icon: LineChart },
      { to: '/schedule', label: 'Schedule', icon: CalendarRange },
      { to: '/email', label: 'Daily email', icon: Mail },
      { to: '/site', label: 'Site & machines', icon: Factory },
    ],
  },
  {
    title: 'Admin',
    items: [
      { to: '/users', label: 'Users', icon: Users, permission: 'users.manage' },
      { to: '/audit', label: 'Audit log', icon: ScrollText, permission: 'audit.view' },
    ],
  },
]

function Brand() {
  return (
    <div className="flex items-center gap-2.5">
      <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-volt">
        <Zap className="h-5 w-5 text-volt-ink" fill="currentColor" aria-hidden />
      </div>
      <div>
        <p className="text-base leading-tight font-semibold tracking-tight text-nav-fg">GridShift</p>
        <p className="text-xs leading-tight text-nav-muted">Energy scheduling</p>
      </div>
    </div>
  )
}

function NavItems({ compact = false }: { compact?: boolean }) {
  const { can } = useAuth()
  const sections = SECTIONS.map((s) => ({ ...s, items: s.items.filter((i) => !i.permission || can(i.permission)) })).filter((s) => s.items.length)
  const link = ({ to, label, icon: Icon }: NavEntry) => (
    <NavLink
      key={to}
      to={to}
      end={to === '/'}
      className={({ isActive }) =>
        cn(
          'group relative flex cursor-pointer items-center gap-3 rounded-lg text-sm font-medium transition-colors duration-200',
          compact ? 'shrink-0 px-3 py-2' : 'px-3 py-2.5',
          isActive ? 'active bg-nav-active text-nav-fg' : 'text-nav-muted hover:bg-nav-hover hover:text-nav-fg',
        )
      }
    >
      <span aria-hidden className="absolute top-2 bottom-2 left-0 hidden w-[3px] rounded-r-full bg-volt group-[.active]:block" />
      <Icon className="h-4 w-4 shrink-0 group-[.active]:text-volt" aria-hidden />
      {label}
    </NavLink>
  )
  if (compact) return <>{sections.flatMap((s) => s.items).map(link)}</>
  return (
    <>
      {sections.map((section) => (
        <div key={section.title} className="space-y-1">
          <p className="px-3 pb-1 font-mono text-[11px] tracking-wider text-nav-muted/60 uppercase">{section.title}</p>
          {section.items.map(link)}
        </div>
      ))}
    </>
  )
}

function ThemeToggle() {
  const [theme, toggle] = useTheme()
  return (
    <Button variant="ghost" size="icon" className="text-nav-muted hover:bg-nav-hover hover:text-nav-fg" onClick={toggle} aria-label={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}>
      {theme === 'dark' ? <Sun className="h-4 w-4" aria-hidden /> : <Moon className="h-4 w-4" aria-hidden />}
    </Button>
  )
}

function initials(name: string | null, email: string): string {
  const source = name?.trim() || email
  const parts = source.split(/[\s@._-]+/).filter(Boolean)
  return ((parts[0]?.[0] ?? '') + (parts[1]?.[0] ?? '')).toUpperCase() || '?'
}

function UserMenu({ compact = false }: { compact?: boolean }) {
  const { me, signOut } = useAuth()
  const navigate = useNavigate()
  if (!me) return null
  const avatar = (
    <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-white/10 text-xs font-semibold text-nav-fg ring-1 ring-white/15">{initials(me.name, me.email)}</span>
  )
  return (
    <MenuRoot>
      <MenuTrigger asChild>
        {compact ? (
          <button type="button" aria-label="Account menu" className="cursor-pointer rounded-full">
            {avatar}
          </button>
        ) : (
          <button type="button" className="flex w-full cursor-pointer items-center gap-3 rounded-lg p-2 text-left transition-colors hover:bg-nav-hover">
            {avatar}
            <span className="min-w-0 flex-1">
              <span className="block truncate text-sm font-medium text-nav-fg">{me.name || me.email}</span>
              <span className="block truncate text-xs text-nav-muted capitalize">{me.role}</span>
            </span>
            <ChevronsUpDown className="h-4 w-4 text-nav-muted" aria-hidden />
          </button>
        )}
      </MenuTrigger>
      <MenuContent align={compact ? 'end' : 'start'}>
        <div className="px-2.5 py-2">
          <p className="truncate text-sm font-medium text-fg">{me.name || me.email}</p>
          <p className="truncate text-xs text-muted">{me.email}</p>
        </div>
        <MenuSeparator />
        <MenuItem onSelect={() => navigate('/account')}>
          <UserCog className="h-4 w-4 text-muted" aria-hidden /> Account & password
        </MenuItem>
        <MenuItem
          danger
          onSelect={() => {
            void signOut().then(() => navigate('/login', { replace: true }))
          }}
        >
          <LogOut className="h-4 w-4" aria-hidden /> Sign out
        </MenuItem>
      </MenuContent>
    </MenuRoot>
  )
}

function RunButton() {
  const { running, runNow } = useRun()
  const { can } = useAuth()
  if (!can('plan.run')) return null
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
  actions?: ReactNode
  planActions?: boolean
  children: ReactNode
}

export function PageLayout({ title, subtitle, actions, planActions = true, children }: PageLayoutProps) {
  const { data } = useRun()
  const run = data?.run
  return (
    <div className="min-h-screen lg:pl-64">
      <aside className="nav-surface fixed inset-y-0 left-0 z-20 hidden w-64 flex-col px-4 py-5 lg:flex">
        <Brand />
        <nav className="mt-8 flex flex-col gap-6" aria-label="Main">
          <NavItems />
        </nav>
        <div className="mt-auto space-y-3">
          <GermanyClock />
          {run && (
            <div className="rounded-xl border border-nav-line bg-nav-hover p-3 text-xs text-nav-muted">
              <p className="font-medium text-nav-fg">{run.site_name}</p>
              <p className="mt-1 font-mono text-[11px]">
                Plan #{run.id} · {relative(run.created_at)}
              </p>
            </div>
          )}
          <div className="flex items-center gap-1 border-t border-nav-line pt-3">
            <div className="min-w-0 flex-1">
              <UserMenu />
            </div>
            <ThemeToggle />
          </div>
        </div>
      </aside>

      <header className="nav-surface sticky top-0 z-10 lg:hidden">
        <div className="flex items-center justify-between px-4 py-3">
          <Brand />
          <div className="flex items-center gap-1">
            <GermanyClock compact className="mr-1" />
            <ThemeToggle />
            <UserMenu compact />
          </div>
        </div>
        <nav className="flex gap-1 overflow-x-auto px-3 pb-2" aria-label="Main">
          <NavItems compact />
        </nav>
      </header>

      <main className="rise w-full px-4 py-6 sm:px-6 lg:px-10 lg:py-9 2xl:px-12">
        <div className="mb-7 flex flex-wrap items-end justify-between gap-4">
          <div className="min-w-0 flex-1 basis-[26rem]">
            <div className="flex items-center gap-3">
              <h1 className="text-[28px] leading-tight font-semibold tracking-[-0.025em] text-fg">{title}</h1>
              {run && planActions && run.status === 'attention' && <Badge tone="warning">Needs attention</Badge>}
            </div>
            {subtitle && <div className="mt-1 text-sm text-muted">{subtitle}</div>}
          </div>
          <div className="flex flex-wrap items-center gap-2">
            {run && planActions && <span className="hidden font-mono text-xs text-muted xl:inline">Updated {dateTime(run.created_at)}</span>}
            {actions}
            {planActions && <RunButton />}
          </div>
        </div>
        {planActions && <RunError />}
        {children}
      </main>
    </div>
  )
}
