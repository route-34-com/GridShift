import { Loader2 } from 'lucide-react'
import { useState, type FormEvent } from 'react'
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom'
import { AuthLayout } from '@/components/AuthLayout'
import { Button } from '@/components/ui/button'
import { Field, FormError, Input, PasswordInput } from '@/components/ui/field'
import { useAuth } from '@/hooks/AuthContext'
import { useSubmit } from '@/hooks/useSubmit'
import { auth } from '@/lib/api'

export function Login() {
  const { me, setup, signIn } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const { submit, busy, error } = useSubmit(auth.login)
  const next = (location.state as { from?: string } | null)?.from ?? '/'

  if (setup?.needed) return <Navigate to="/setup" replace />
  if (me) return <Navigate to={next} replace />

  const onSubmit = async (event: FormEvent) => {
    event.preventDefault()
    const user = await submit(email.trim(), password)
    if (user) {
      signIn(user)
      navigate(next, { replace: true })
    }
  }

  return (
    <AuthLayout title="Sign in" subtitle="Welcome back. Sign in to see this week's energy plan.">
      <form onSubmit={(e) => void onSubmit(e)} className="space-y-4" noValidate>
        <FormError message={error} />
        <Field label="Email">{(id) => <Input id={id} type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} />}</Field>
        <Field label="Password">
          {(id) => <PasswordInput id={id} autoComplete="current-password" required value={password} onChange={(e) => setPassword(e.target.value)} />}
        </Field>
        <div className="flex justify-end">
          <Link to="/forgot-password" className="text-sm font-medium text-brand hover:underline">
            Forgot password?
          </Link>
        </div>
        <Button type="submit" variant="primary" className="w-full" disabled={busy || !email || !password}>
          {busy && <Loader2 className="h-4 w-4 animate-spin" aria-hidden />}
          Sign in
        </Button>
      </form>
    </AuthLayout>
  )
}
