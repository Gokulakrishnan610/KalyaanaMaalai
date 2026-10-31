import { useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { post } from '@/api/client'
import { Logo } from '@/components/Logo'
import { Button, Field } from '@/components/ui'

export default function ForgotPassword() {
  const [email, setEmail] = useState('')
  const [sent, setSent] = useState(false)
  const [busy, setBusy] = useState(false)

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    setBusy(true)
    await post('/portal/forgot-password/', { email }).catch(() => undefined)
    setSent(true)
    setBusy(false)
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-ivory px-5">
      <form onSubmit={submit} className="w-full max-w-sm space-y-4 rounded-3xl bg-white p-8 shadow-sm ring-1 ring-stone-200">
        <Logo />
        <h1 className="font-serif text-2xl font-semibold text-maroon-900">Forgot your password?</h1>
        {sent ? (
          <p className="text-sm text-stone-600">If that email has an account, we have sent a link to choose a new password. Check your inbox.</p>
        ) : (
          <>
            <p className="text-sm text-stone-600">Enter your email and we will send you a link.</p>
            <Field label="Email" type="email" autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} />
            <Button type="submit" className="w-full" loading={busy} disabled={!email}>Send the link</Button>
          </>
        )}
        <p className="text-center text-sm"><Link to="/login" className="font-semibold text-maroon-700 hover:underline">Back to log in</Link></p>
      </form>
    </div>
  )
}
