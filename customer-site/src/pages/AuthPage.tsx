import { useState, type FormEvent } from 'react'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import { useAuth } from '@/auth/AuthContext'
import { ApiError } from '@/api/client'
import { Logo } from '@/components/Logo'
import { Button, Field } from '@/components/ui'

/** One screen for both "create account" and "log in". */
export default function AuthPage({ mode }: { mode: 'signup' | 'login' }) {
  const { loggedIn, signup, login } = useAuth()
  const navigate = useNavigate()
  const [form, setForm] = useState({ name: '', email: '', phone: '', password: '' })
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [message, setMessage] = useState('')
  const [busy, setBusy] = useState(false)
  const isSignup = mode === 'signup'
  const set = (key: keyof typeof form) => (e: { target: { value: string } }) => setForm((f) => ({ ...f, [key]: e.target.value }))

  // someone who is already logged in goes straight home; while we are still finishing a sign-up we wait, so the wizard opens
  if (loggedIn && !busy) return <Navigate to="/home" replace />

  const submit = async (event: FormEvent) => {
    event.preventDefault()
    const problems: Record<string, string> = {}
    if (isSignup && !form.name.trim()) problems.name = 'Please tell us your name'
    if (isSignup && !/^\d{10}$/.test(form.phone)) problems.phone = 'Enter a 10-digit mobile number'
    if (!/^\S+@\S+\.\S+$/.test(form.email)) problems.email = 'Enter a valid email'
    if (form.password.length < (isSignup ? 8 : 1)) problems.password = isSignup ? 'Use at least 8 characters' : 'Enter your password'
    setErrors(problems)
    setMessage('')
    if (Object.keys(problems).length) return
    setBusy(true)
    try {
      if (isSignup) {
        await signup(form)
        navigate('/start')
      } else {
        await login(form.email, form.password)
        navigate('/home')
      }
    } catch (e) {
      if (e instanceof ApiError) {
        setErrors(e.fields)
        setMessage(e.message)
      }
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="grid min-h-screen md:grid-cols-2">
      <aside className="relative hidden flex-col justify-between overflow-hidden bg-gradient-to-br from-maroon-900 via-maroon-700 to-maroon-500 p-12 text-white md:flex">
        <img src={isSignup ? '/photos/hero-2.jpg' : '/photos/hero-1.jpg'} alt="" className="absolute inset-0 h-full w-full object-cover" />
        <div className="absolute inset-0 bg-gradient-to-t from-maroon-900/90 via-maroon-900/50 to-maroon-900/30" />
        <div className="relative"><Logo light /></div>
        <div className="relative">
          <p className="font-serif text-4xl leading-snug">“Shaadi planning should feel like a celebration, not a to-do list.”</p>
          <p className="mt-4 text-white/70">Create your account and we will take care of the rest.</p>
        </div>
              </aside>

      <main className="flex items-center justify-center px-5 py-12">
        <form onSubmit={submit} noValidate className="w-full max-w-sm space-y-4">
          <div className="md:hidden"><Logo /></div>
          <div>
            <h1 className="font-serif text-3xl font-semibold text-maroon-900">{isSignup ? 'Create your account' : 'Welcome back'}</h1>
            <p className="mt-1 text-sm text-stone-600">{isSignup ? 'It is free and takes two minutes.' : 'Log in to see your wedding.'}</p>
          </div>
          {isSignup && <Field label="Your name" autoComplete="name" value={form.name} onChange={set('name')} error={errors.name} />}
          <Field label="Email" type="email" autoComplete="email" value={form.email} onChange={set('email')} error={errors.email} />
          {isSignup && <Field label="Mobile number" inputMode="numeric" maxLength={10} autoComplete="tel" value={form.phone} onChange={set('phone')} error={errors.phone} hint="We will call or WhatsApp you on this number" />}
          <Field label="Password" type="password" autoComplete={isSignup ? 'new-password' : 'current-password'} value={form.password} onChange={set('password')} error={errors.password} />
          {message && !Object.keys(errors).some((k) => ['name', 'email', 'phone', 'password'].includes(k)) && (
            <p role="alert" className="rounded-xl bg-red-50 p-3 text-sm text-red-700">{message}</p>
          )}
          {!isSignup && <p className="text-right text-sm"><Link to="/forgot" className="font-medium text-maroon-700 hover:underline">Forgot your password?</Link></p>}
          <Button type="submit" className="w-full" loading={busy}>
            {isSignup ? 'Create account' : 'Log in'}
          </Button>
          <p className="text-center text-sm text-stone-600">
            {isSignup ? (
              <>Already have an account? <Link to="/login" className="font-semibold text-maroon-700 hover:underline">Log in</Link></>
            ) : (
              <>New here? <Link to="/signup" className="font-semibold text-maroon-700 hover:underline">Create an account</Link></>
            )}
          </p>
        </form>
      </main>
    </div>
  )
}
