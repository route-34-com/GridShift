import { Check, Loader2 } from 'lucide-react'
import { useState, type FormEvent } from 'react'
import { PageLayout } from '@/components/PageLayout'
import { PasswordRules, passwordProblem } from '@/components/PasswordRules'
import { Button } from '@/components/ui/button'
import { Card, CardBody, CardHeader } from '@/components/ui/card'
import { Field, FormError, Input, PasswordInput } from '@/components/ui/field'
import { useAuth } from '@/hooks/AuthContext'
import { useToast } from '@/hooks/Toasts'
import { useSubmit } from '@/hooks/useSubmit'
import { auth } from '@/lib/api'
import { dateTime } from '@/lib/format'

const PERMISSION_TEXT: Record<string, string> = {
  'plan.view': 'See plans, forecasts and schedules',
  'plan.run': 'Re-plan',
  'meter.upload': 'Upload meter data',
  export: 'Download exports',
  'config.view': 'See site and machine setup',
  'users.manage': 'Invite and manage users',
  'audit.view': 'See the audit log',
  'email.test': 'Send test emails',
}

function Profile() {
  const { me, signIn } = useAuth()
  const { notify } = useToast()
  const [name, setName] = useState(me?.name ?? '')
  const { submit, busy, error } = useSubmit(auth.profile)
  if (!me) return null
  const onSubmit = async (event: FormEvent) => {
    event.preventDefault()
    const updated = await submit(name.trim())
    if (updated) {
      signIn(updated)
      notify('Profile saved.')
    }
  }
  return (
    <Card>
      <CardHeader title="Profile" description="How your name appears to others and in the audit log" />
      <CardBody>
        <form onSubmit={(e) => void onSubmit(e)} className="space-y-4">
          <FormError message={error} />
          <Field label="Name">{(id) => <Input id={id} value={name} onChange={(e) => setName(e.target.value)} />}</Field>
          <Field label="Email" hint="Ask an admin if your email changes.">
            {(id) => <Input id={id} value={me.email} disabled />}
          </Field>
          <Button type="submit" variant="primary" disabled={busy || name.trim() === (me.name ?? '')}>
            {busy && <Loader2 className="h-4 w-4 animate-spin" aria-hidden />}
            Save profile
          </Button>
        </form>
      </CardBody>
    </Card>
  )
}

function Password() {
  const { notify } = useToast()
  const [current, setCurrent] = useState('')
  const [next, setNext] = useState('')
  const [confirm, setConfirm] = useState('')
  const { submit, busy, error, setError } = useSubmit(auth.password)
  const onSubmit = async (event: FormEvent) => {
    event.preventDefault()
    if (next !== confirm) return setError('The two new passwords are not the same.')
    if (await submit(current, next)) {
      setCurrent('')
      setNext('')
      setConfirm('')
      notify('Password changed. Other devices were signed out.')
    }
  }
  return (
    <Card>
      <CardHeader title="Change password" description="You stay signed in here; every other device is signed out." />
      <CardBody>
        <form onSubmit={(e) => void onSubmit(e)} className="space-y-4" noValidate>
          <FormError message={error} />
          <Field label="Current password">{(id) => <PasswordInput id={id} autoComplete="current-password" value={current} onChange={(e) => setCurrent(e.target.value)} />}</Field>
          <Field label="New password">{(id) => <PasswordInput id={id} autoComplete="new-password" value={next} onChange={(e) => setNext(e.target.value)} />}</Field>
          <Field label="Confirm new password">{(id) => <PasswordInput id={id} autoComplete="new-password" value={confirm} onChange={(e) => setConfirm(e.target.value)} />}</Field>
          <PasswordRules password={next} />
          <Button type="submit" variant="primary" disabled={busy || !current || Boolean(passwordProblem(next)) || !confirm}>
            {busy && <Loader2 className="h-4 w-4 animate-spin" aria-hidden />}
            Change password
          </Button>
        </form>
      </CardBody>
    </Card>
  )
}

export function AccountPage() {
  const { me } = useAuth()
  if (!me) return null
  return (
    <PageLayout title="Account" subtitle="Your profile, password and access" planActions={false}>
      <div className="grid gap-6 xl:grid-cols-3">
        <div className="space-y-6 xl:col-span-2">
          <Profile />
          <Password />
        </div>
        <Card className="h-fit">
          <CardHeader title="Your access" description={<span className="capitalize">Role: {me.role}</span>} />
          <CardBody className="space-y-4 text-sm">
            <ul className="space-y-1.5">
              {me.permissions.map((p) => (
                <li key={p} className="flex items-center gap-2 text-fg">
                  <Check className="h-4 w-4 text-positive" aria-hidden /> {PERMISSION_TEXT[p] ?? p}
                </li>
              ))}
            </ul>
            <p className="text-muted">Last sign-in: {me.last_login_at ? dateTime(me.last_login_at) : 'now'}</p>
          </CardBody>
        </Card>
      </div>
    </PageLayout>
  )
}
