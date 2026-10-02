import { Loader2, MailCheck } from 'lucide-react'
import { useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { AuthLayout } from '@/components/AuthLayout'
import { Button } from '@/components/ui/button'
import { Field, FormError, Input } from '@/components/ui/field'
import { useSubmit } from '@/hooks/useSubmit'
import { auth } from '@/lib/api'

export function ForgotPassword() {
  const [email, setEmail] = useState('')
  const [answer, setAnswer] = useState<string | null>(null)
  const { submit, busy, error } = useSubmit(auth.forgot)

  const onSubmit = async (event: FormEvent) => {
    event.preventDefault()
    const result = await submit(email.trim())
    if (result) setAnswer(result.message)
  }

  return (
    <AuthLayout
      title="Forgot your password?"
      subtitle="Enter your work email and we'll send you a link to choose a new one."
      footer={
        <Link to="/login" className="font-medium text-brand hover:underline">
          Back to sign in
        </Link>
      }
    >
      {answer ? (
        <div className="flex gap-3 rounded-lg border border-positive/30 bg-positive-soft p-4 text-sm text-fg" role="status">
          <MailCheck className="mt-0.5 h-5 w-5 shrink-0 text-positive" aria-hidden />
          <p>{answer}</p>
        </div>
      ) : (
        <form onSubmit={(e) => void onSubmit(e)} className="space-y-4" noValidate>
          <FormError message={error} />
          <Field label="Email">{(id) => <Input id={id} type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} />}</Field>
          <Button type="submit" variant="primary" className="w-full" disabled={busy || !email}>
            {busy && <Loader2 className="h-4 w-4 animate-spin" aria-hidden />}
            Send reset link
          </Button>
        </form>
      )}
    </AuthLayout>
  )
}
