import { useState, type FormEvent } from 'react'
import { useSearchParams } from 'react-router-dom'
import { ApiError, post, TOKEN_KEY } from '@/api/client'
import { Logo } from '@/components/Logo'
import { Button, Field } from '@/components/ui'

/** The page behind the link in the welcome email: choose a password, and you are logged in. */
export default function SetPassword() {
  const [params] = useSearchParams()
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    setBusy(true)
    setError('')
    try {
      const res = await post<{ token: string }>('/portal/set-password/', { token: params.get('token') ?? '', password })
      localStorage.setItem(TOKEN_KEY, res.token)
      window.location.assign('/home')
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Something went wrong. Please try again.')
      setBusy(false)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-ivory px-5">
      <form onSubmit={submit} className="w-full max-w-sm space-y-4 rounded-3xl bg-white p-8 shadow-sm ring-1 ring-stone-200">
        <Logo />
        <div>
          <h1 className="font-serif text-2xl font-semibold text-maroon-900">Choose your password</h1>
          <p className="mt-1 text-sm text-stone-600">You will use it to log in and see your wedding.</p>
        </div>
        <Field label="New password" type="password" autoComplete="new-password" value={password} onChange={(e) => setPassword(e.target.value)} hint="At least 8 characters" />
        {error && <p role="alert" className="rounded-xl bg-red-50 p-3 text-sm text-red-700">{error}</p>}
        <Button type="submit" className="w-full" loading={busy}>Save and continue</Button>
      </form>
    </div>
  )
}
