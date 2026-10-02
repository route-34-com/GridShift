import { Loader2 } from 'lucide-react'
import { useEffect, useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { AuthLayout } from '@/components/AuthLayout'
import { PasswordRules, passwordProblem } from '@/components/PasswordRules'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Field, FormError, Input, PasswordInput } from '@/components/ui/field'
import { Skeleton } from '@/components/ui/skeleton'
import { useAuth } from '@/hooks/AuthContext'
import { useSubmit } from '@/hooks/useSubmit'
import { auth } from '@/lib/api'
import type { Role } from '@/lib/types'
import { linkToken } from './ResetPassword'

const ROLE_TEXT: Record<Role, string> = {
  admin: 'Admin: plans, exports, users and audit log',
  planner: 'Planner: can re-plan and export',
  viewer: 'Viewer: can see plans and export',
}

export function AcceptInvite() {
  const { signIn, signOut, me } = useAuth()
  const navigate = useNavigate()
  const [token] = useState(linkToken)
  const [invite, setInvite] = useState<{ email: string; name: string | null; role: Role } | null>(null)
  const [invalid, setInvalid] = useState<string | null>(token ? null : 'This invitation link is incomplete.')
  const [name, setName] = useState('')
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const { submit, busy, error, setError } = useSubmit(auth.acceptInvite)

  useEffect(() => {
    if (!token) return
    auth
      .inviteDetails(token)
      .then((found) => {
        setInvite(found)
        setName(found.name ?? '')
      })
      .catch((err: Error) => setInvalid(err.message))
  }, [token])

  const onSubmit = async (event: FormEvent) => {
    event.preventDefault()
    if (password !== confirm) return setError('The two passwords are not the same.')
    if (me) await signOut()
    const user = await submit({ token, password, name: name.trim() })
    if (user) {
      signIn(user)
      history.replaceState(null, '', '/')
      navigate('/', { replace: true })
    }
  }

  if (invalid) {
    return (
      <AuthLayout
        title="Invitation not valid"
        subtitle={invalid}
        footer={
          <Link to="/login" className="font-medium text-brand hover:underline">
            Go to sign in
          </Link>
        }
      >
        <p className="text-sm text-muted">Ask your GridShift admin to send a new invitation.</p>
      </AuthLayout>
    )
  }

  if (!invite) {
    return (
      <AuthLayout title="Checking your invitation…">
        <Skeleton className="h-40" />
      </AuthLayout>
    )
  }

  return (
    <AuthLayout title="Join GridShift" subtitle={<>Set a password for <span className="font-medium text-fg">{invite.email}</span> to activate your account.</>}>
      <form onSubmit={(e) => void onSubmit(e)} className="space-y-4" noValidate>
        <div className="flex items-center gap-2 text-sm">
          <Badge tone="brand">{invite.role}</Badge>
          <span className="text-muted">{ROLE_TEXT[invite.role]}</span>
        </div>
        <FormError message={error} />
        <Field label="Your name">{(id) => <Input id={id} autoComplete="name" value={name} onChange={(e) => setName(e.target.value)} />}</Field>
        <Field label="Password">{(id) => <PasswordInput id={id} autoComplete="new-password" value={password} onChange={(e) => setPassword(e.target.value)} />}</Field>
        <Field label="Confirm password">{(id) => <PasswordInput id={id} autoComplete="new-password" value={confirm} onChange={(e) => setConfirm(e.target.value)} />}</Field>
        <PasswordRules password={password} />
        <Button type="submit" variant="primary" className="w-full" disabled={busy || Boolean(passwordProblem(password)) || !confirm}>
          {busy && <Loader2 className="h-4 w-4 animate-spin" aria-hidden />}
          Activate account
        </Button>
      </form>
    </AuthLayout>
  )
}
