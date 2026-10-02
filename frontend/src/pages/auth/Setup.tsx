import { Loader2 } from 'lucide-react'
import { useState, type FormEvent } from 'react'
import { Navigate, useNavigate } from 'react-router-dom'
import { AuthLayout } from '@/components/AuthLayout'
import { PasswordRules, passwordProblem } from '@/components/PasswordRules'
import { Button } from '@/components/ui/button'
import { Field, FormError, Input, PasswordInput } from '@/components/ui/field'
import { useAuth } from '@/hooks/AuthContext'
import { useSubmit } from '@/hooks/useSubmit'
import { auth } from '@/lib/api'

export function Setup() {
  const { setup, me, signIn } = useAuth()
  const navigate = useNavigate()
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const { submit, busy, error, setError } = useSubmit(auth.setup)

  if (me) return <Navigate to="/" replace />
  if (setup && !setup.needed) return <Navigate to="/login" replace />

  const onSubmit = async (event: FormEvent) => {
    event.preventDefault()
    if (password !== confirm) return setError('The two passwords are not the same.')
    const user = await submit({ name: name.trim(), email: email.trim(), password })
    if (user) {
      signIn(user)
      navigate('/', { replace: true })
    }
  }

  if (setup && !setup.allowed) {
    return (
      <AuthLayout title="Finish setup on the server" subtitle="For security, the first admin account can only be created on the computer running GridShift.">
        <p className="text-sm text-muted">
          Open <span className="font-mono text-fg">http://127.0.0.1:8000</span> on that computer, or set <span className="font-mono text-fg">GRIDSHIFT_ALLOW_SETUP=true</span> in .env.
        </p>
      </AuthLayout>
    )
  }

  return (
    <AuthLayout title="Create the admin account" subtitle="This is the first account. You can invite your team after this.">
      <form onSubmit={(e) => void onSubmit(e)} className="space-y-4" noValidate>
        <FormError message={error} />
        <Field label="Your name">{(id) => <Input id={id} autoComplete="name" value={name} onChange={(e) => setName(e.target.value)} />}</Field>
        <Field label="Work email">{(id) => <Input id={id} type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} />}</Field>
        <Field label="Password">{(id) => <PasswordInput id={id} autoComplete="new-password" required value={password} onChange={(e) => setPassword(e.target.value)} />}</Field>
        <Field label="Confirm password">{(id) => <PasswordInput id={id} autoComplete="new-password" required value={confirm} onChange={(e) => setConfirm(e.target.value)} />}</Field>
        <PasswordRules password={password} />
        <Button type="submit" variant="primary" className="w-full" disabled={busy || !email || Boolean(passwordProblem(password)) || !confirm}>
          {busy && <Loader2 className="h-4 w-4 animate-spin" aria-hidden />}
          Create admin account
        </Button>
      </form>
    </AuthLayout>
  )
}
