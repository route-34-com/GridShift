import { KeyRound, Loader2, Mail, MoreHorizontal, Power, Send, Trash2, UserPlus } from 'lucide-react'
import { useState, type FormEvent } from 'react'
import { ExportMenu } from '@/components/ExportMenu'
import { LinkBox } from '@/components/LinkBox'
import { PageLayout } from '@/components/PageLayout'
import { ErrorView, LoadingView } from '@/components/StateViews'
import { Badge, type Tone } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardBody, CardHeader } from '@/components/ui/card'
import { Dialog } from '@/components/ui/dialog'
import { Field, FormError, Input, Select } from '@/components/ui/field'
import { MenuContent, MenuItem, MenuRoot, MenuSeparator, MenuTrigger } from '@/components/ui/menu'
import { useToast } from '@/hooks/Toasts'
import { useAsync } from '@/hooks/useAsync'
import { useSubmit } from '@/hooks/useSubmit'
import { admin, exportsApi } from '@/lib/api'
import { dateTime, relative } from '@/lib/format'
import type { Account, LinkResult, Role } from '@/lib/types'

const ROLES: { value: Role; label: string; help: string }[] = [
  { value: 'admin', label: 'Admin', help: 'Everything, including users and the audit log' },
  { value: 'planner', label: 'Planner', help: 'View, re-plan and export' },
  { value: 'viewer', label: 'Viewer', help: 'View and export' },
]

const STATUS_TONE: Record<Account['status'], Tone> = { active: 'positive', invited: 'info', disabled: 'neutral' }

function InviteDialog({ open, onClose, onDone }: { open: boolean; onClose: () => void; onDone: () => void }) {
  const [email, setEmail] = useState('')
  const [name, setName] = useState('')
  const [role, setRole] = useState<Role>('viewer')
  const [result, setResult] = useState<LinkResult | null>(null)
  const { submit, busy, error, setError } = useSubmit(admin.invite)

  const close = () => {
    setEmail('')
    setName('')
    setRole('viewer')
    setResult(null)
    setError(null)
    onClose()
  }

  const onSubmit = async (event: FormEvent) => {
    event.preventDefault()
    const sent = await submit({ email: email.trim(), name: name.trim(), role })
    if (sent) {
      setResult(sent)
      onDone()
    }
  }

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => !next && close()}
      title={result ? 'Invitation created' : 'Invite a user'}
      description={result ? undefined : 'They get an email with a link to set their password. The link works once and expires in 7 days.'}
      footer={
        result ? (
          <Button variant="primary" onClick={close}>
            Done
          </Button>
        ) : (
          <>
            <Button onClick={close}>Cancel</Button>
            <Button type="submit" form="invite-form" variant="primary" disabled={busy || !email}>
              {busy ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> : <Send className="h-4 w-4" aria-hidden />}
              Send invitation
            </Button>
          </>
        )
      }
    >
      {result ? (
        <LinkBox result={result} sentTo={email} />
      ) : (
        <form id="invite-form" onSubmit={(e) => void onSubmit(e)} className="space-y-4" noValidate>
          <FormError message={error} />
          <Field label="Email">{(id) => <Input id={id} type="email" autoFocus value={email} onChange={(e) => setEmail(e.target.value)} placeholder="name@company.de" />}</Field>
          <Field label="Name" hint="Optional. They can change it later.">
            {(id) => <Input id={id} value={name} onChange={(e) => setName(e.target.value)} />}
          </Field>
          <Field label="Role" hint={ROLES.find((r) => r.value === role)?.help}>
            {(id) => (
              <Select id={id} value={role} onChange={(e) => setRole(e.target.value as Role)}>
                {ROLES.map((r) => (
                  <option key={r.value} value={r.value}>
                    {r.label}
                  </option>
                ))}
              </Select>
            )}
          </Field>
        </form>
      )}
    </Dialog>
  )
}

interface Pending {
  title: string
  body: string
  confirm: string
  danger?: boolean
  action: () => Promise<unknown>
}

function ConfirmDialog({ pending, onClose }: { pending: Pending | null; onClose: () => void }) {
  const { submit, busy, error, setError } = useSubmit(async () => pending?.action())
  return (
    <Dialog
      open={Boolean(pending)}
      onOpenChange={(next) => {
        if (!next) {
          setError(null)
          onClose()
        }
      }}
      title={pending?.title ?? ''}
      description={pending?.body}
      footer={
        <>
          <Button onClick={onClose}>Cancel</Button>
          <Button
            variant="primary"
            className={pending?.danger ? 'bg-danger text-white' : ''}
            disabled={busy}
            onClick={() => void submit().then((done) => done !== undefined && onClose())}
          >
            {busy && <Loader2 className="h-4 w-4 animate-spin" aria-hidden />}
            {pending?.confirm}
          </Button>
        </>
      }
    >
      <FormError message={error} />
    </Dialog>
  )
}

function UserRow({ user, onChanged, onConfirm, onLink }: { user: Account; onChanged: () => void; onConfirm: (p: Pending) => void; onLink: (r: LinkResult, to: string, title: string) => void }) {
  const { notify } = useToast()
  const [saving, setSaving] = useState(false)

  const changeRole = async (role: Role) => {
    setSaving(true)
    try {
      await admin.update(user.id, { role })
      notify(`${user.email} is now ${role}.`)
      onChanged()
    } catch (err) {
      notify(err instanceof Error ? err.message : String(err), 'error')
    } finally {
      setSaving(false)
    }
  }

  const sendLink = async (kind: 'invite' | 'reset') => {
    try {
      const result = kind === 'invite' ? await admin.resendInvite(user.id) : await admin.resetLink(user.id)
      onLink(result, user.email, kind === 'invite' ? 'Invitation resent' : 'Reset link created')
    } catch (err) {
      notify(err instanceof Error ? err.message : String(err), 'error')
    }
  }

  return (
    <tr className="border-b border-border last:border-0">
      <td className="py-3 pr-4">
        <div className="flex items-center gap-3">
          <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-surface-2 text-xs font-semibold text-muted">
            {(user.name || user.email).slice(0, 2).toUpperCase()}
          </span>
          <div className="min-w-0">
            <p className="truncate font-medium text-fg">
              {user.name || '—'} {user.you && <Badge tone="brand">You</Badge>}
            </p>
            <p className="truncate text-xs text-muted">{user.email}</p>
          </div>
        </div>
      </td>
      <td className="py-3 pr-4">
        {user.you ? (
          <span className="text-sm text-fg capitalize">{user.role}</span>
        ) : (
          <Select aria-label={`Role for ${user.email}`} value={user.role} disabled={saving} onChange={(e) => void changeRole(e.target.value as Role)} className="h-9 w-32">
            {ROLES.map((r) => (
              <option key={r.value} value={r.value}>
                {r.label}
              </option>
            ))}
          </Select>
        )}
      </td>
      <td className="py-3 pr-4">
        <Badge tone={STATUS_TONE[user.status]}>{user.status}</Badge>
      </td>
      <td className="py-3 pr-4 text-sm text-muted" title={user.last_login_at ? dateTime(user.last_login_at) : undefined}>
        {user.last_login_at ? relative(user.last_login_at) : 'Never'}
      </td>
      <td className="py-3 pr-4 text-sm text-muted">{dateTime(user.created_at)}</td>
      <td className="py-3 text-right">
        {!user.you && (
          <MenuRoot>
            <MenuTrigger asChild>
              <Button variant="ghost" size="icon" aria-label={`Actions for ${user.email}`}>
                <MoreHorizontal className="h-4 w-4" aria-hidden />
              </Button>
            </MenuTrigger>
            <MenuContent>
              {user.status === 'invited' && (
                <MenuItem onSelect={() => void sendLink('invite')}>
                  <Mail className="h-4 w-4 text-muted" aria-hidden /> Resend invitation
                </MenuItem>
              )}
              {user.status === 'active' && (
                <MenuItem onSelect={() => void sendLink('reset')}>
                  <KeyRound className="h-4 w-4 text-muted" aria-hidden /> Send password reset link
                </MenuItem>
              )}
              {user.status !== 'invited' && (
                <MenuItem
                  onSelect={() =>
                    onConfirm({
                      title: user.status === 'active' ? `Switch off ${user.email}?` : `Switch on ${user.email}?`,
                      body: user.status === 'active' ? 'They are signed out right away and cannot sign in until switched back on.' : 'They can sign in again with their password.',
                      confirm: user.status === 'active' ? 'Switch off' : 'Switch on',
                      danger: user.status === 'active',
                      action: () => admin.update(user.id, { status: user.status === 'active' ? 'disabled' : 'active' }).then(onChanged),
                    })
                  }
                >
                  <Power className="h-4 w-4 text-muted" aria-hidden /> {user.status === 'active' ? 'Switch off account' : 'Switch on account'}
                </MenuItem>
              )}
              <MenuSeparator />
              <MenuItem
                danger
                onSelect={() =>
                  onConfirm({
                    title: `Remove ${user.email}?`,
                    body: 'This deletes the account and signs them out. Their past actions stay in the audit log. This cannot be undone.',
                    confirm: 'Remove user',
                    danger: true,
                    action: () => admin.remove(user.id).then(onChanged),
                  })
                }
              >
                <Trash2 className="h-4 w-4" aria-hidden /> Remove user
              </MenuItem>
            </MenuContent>
          </MenuRoot>
        )}
      </td>
    </tr>
  )
}

function MailWarning() {
  const status = useAsync(admin.mailStatus)
  if (!status.data || status.data.configured) return null
  return (
    <div className="rounded-lg border border-warning/30 bg-warning-soft px-4 py-3 text-sm text-fg">
      <span className="font-medium text-warning">Email isn't set up.</span> Invitations and reset links are shown here for you to copy. Add the SMTP settings to <span className="font-mono">.env</span> and restart GridShift to send them by email.
    </div>
  )
}

export function UsersPage() {
  const users = useAsync(admin.users)
  const [inviting, setInviting] = useState(false)
  const [pending, setPending] = useState<Pending | null>(null)
  const [link, setLink] = useState<{ result: LinkResult; to: string; title: string } | null>(null)
  const counts = (users.data ?? []).reduce<Record<string, number>>((acc, u) => ({ ...acc, [u.status]: (acc[u.status] ?? 0) + 1 }), {})

  return (
    <PageLayout
      title="Users"
      subtitle="Invite people, set their role, and switch accounts on or off"
      planActions={false}
      actions={
        <>
          <ExportMenu options={[{ label: 'User list', formats: ['pdf', 'xlsx', 'csv'], run: (f) => exportsApi.users(f) }]} />
          <Button variant="primary" onClick={() => setInviting(true)}>
            <UserPlus className="h-4 w-4" aria-hidden /> Invite user
          </Button>
        </>
      }
    >
      <div className="space-y-6">
        <MailWarning />
        {users.loading && !users.data ? (
          <LoadingView />
        ) : users.error ? (
          <ErrorView message={users.error.message} onRetry={() => void users.reload()} />
        ) : (
          <Card>
            <CardHeader
              title={`${users.data?.length ?? 0} ${users.data?.length === 1 ? 'account' : 'accounts'}`}
              description={`${counts.active ?? 0} active · ${counts.invited ?? 0} invited · ${counts.disabled ?? 0} switched off`}
            />
            <CardBody className="overflow-x-auto">
              <table className="w-full min-w-[820px] text-sm">
                <thead>
                  <tr className="border-b border-border text-left text-xs text-muted">
                    <th className="py-2 pr-4 font-medium">User</th>
                    <th className="py-2 pr-4 font-medium">Role</th>
                    <th className="py-2 pr-4 font-medium">Status</th>
                    <th className="py-2 pr-4 font-medium">Last sign-in</th>
                    <th className="py-2 pr-4 font-medium">Added</th>
                    <th className="py-2 font-medium" />
                  </tr>
                </thead>
                <tbody>
                  {(users.data ?? []).map((user) => (
                    <UserRow key={user.id} user={user} onChanged={() => void users.reload()} onConfirm={setPending} onLink={(result, to, title) => setLink({ result, to, title })} />
                  ))}
                </tbody>
              </table>
            </CardBody>
          </Card>
        )}
      </div>
      <InviteDialog open={inviting} onClose={() => setInviting(false)} onDone={() => void users.reload()} />
      <ConfirmDialog pending={pending} onClose={() => setPending(null)} />
      <Dialog open={Boolean(link)} onOpenChange={(next) => !next && setLink(null)} title={link?.title ?? ''} footer={<Button variant="primary" onClick={() => setLink(null)}>Done</Button>}>
        {link && <LinkBox result={link.result} sentTo={link.to} />}
      </Dialog>
    </PageLayout>
  )
}
