import { CheckCircle2, Loader2 } from 'lucide-react'
import { useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { AuthLayout } from '@/components/AuthLayout'
import { PasswordRules, passwordProblem } from '@/components/PasswordRules'
import { Button } from '@/components/ui/button'
import { Field, FormError, PasswordInput } from '@/components/ui/field'
import { useSubmit } from '@/hooks/useSubmit'
import { auth } from '@/lib/api'

export function linkToken(): string {
  return new URLSearchParams(window.location.hash.slice(1)).get('t') ?? ''
}

export function ResetPassword() {
  const [token] = useState(linkToken)
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [done, setDone] = useState(false)
  const { submit, busy, error, setError } = useSubmit(auth.reset)
  const back = (
    <Link to="/login" className="font-medium text-brand hover:underline">
      Back to sign in
    </Link>
  )

  const onSubmit = async (event: FormEvent) => {
    event.preventDefault()
    if (password !== confirm) return setError('The two passwords are not the same.')
    if (await submit(token, password)) {
      setDone(true)
      history.replaceState(null, '', window.location.pathname)
    }
  }

  if (!token) {
    return (
      <AuthLayout title="This link is incomplete" subtitle="Open the reset link from your email again, or ask for a new one." footer={back}>
        <Link to="/forgot-password" className="text-sm font-medium text-brand hover:underline">
          Request a new reset link
        </Link>
      </AuthLayout>
    )
  }

  if (done) {
    return (
      <AuthLayout title="Password changed" footer={back}>
        <div className="flex gap-3 rounded-lg border border-positive/30 bg-positive-soft p-4 text-sm text-fg" role="status">
          <CheckCircle2 className="mt-0.5 h-5 w-5 shrink-0 text-positive" aria-hidden />
          <p>Your new password is set and you were signed out everywhere else. Sign in with it now.</p>
        </div>
      </AuthLayout>
    )
  }

  return (
    <AuthLayout title="Choose a new password" subtitle="The link works once and expires 1 hour after it was sent." footer={back}>
      <form onSubmit={(e) => void onSubmit(e)} className="space-y-4" noValidate>
        <FormError message={error} />
        <Field label="New password">{(id) => <PasswordInput id={id} autoComplete="new-password" value={password} onChange={(e) => setPassword(e.target.value)} />}</Field>
        <Field label="Confirm new password">{(id) => <PasswordInput id={id} autoComplete="new-password" value={confirm} onChange={(e) => setConfirm(e.target.value)} />}</Field>
        <PasswordRules password={password} />
        <Button type="submit" variant="primary" className="w-full" disabled={busy || Boolean(passwordProblem(password)) || !confirm}>
          {busy && <Loader2 className="h-4 w-4 animate-spin" aria-hidden />}
          Set new password
        </Button>
        {error?.includes('expired') && (
          <Link to="/forgot-password" className="block text-center text-sm font-medium text-brand hover:underline">
            Request a new reset link
          </Link>
        )}
      </form>
    </AuthLayout>
  )
}
