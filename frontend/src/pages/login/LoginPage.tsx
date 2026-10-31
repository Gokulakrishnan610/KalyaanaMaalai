import { zodResolver } from '@hookform/resolvers/zod'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { Navigate, useLocation, useNavigate } from 'react-router-dom'
import { z } from 'zod'
import { Button, Emblem, Input } from '@/components/common'
import { useLogin } from '@/login/LoginContext'
import { ApiError, post, VENDOR_TOKEN_KEY } from '@/api/client'

const schema = z.object({
  email: z.string().email('Enter a valid email'),
  password: z.string().min(1, 'Password is required'),
})
type Form = z.infer<typeof schema>

export default function LoginPage() {
  const { user, login } = useLogin()
  const navigate = useNavigate()
  const location = useLocation()
  const [error, setError] = useState('')
  const {
    register,
    handleSubmit,
    setValue,
    formState: { errors, isSubmitting },
  } = useForm<Form>({ resolver: zodResolver(schema) })

  if (user) return <Navigate to="/" replace />
  if (localStorage.getItem(VENDOR_TOKEN_KEY)) return <Navigate to="/vendor" replace />

  const onSubmit = async (values: Form) => {
    setError('')
    try {
      await login(values.email, values.password)
      navigate((location.state as { from?: string } | null)?.from ?? '/', { replace: true })
    } catch (e) {
      if (!(e instanceof ApiError) || (e.status !== 400 && e.status !== 401)) return setError('Could not reach the server')
      // not one of our team: maybe a vendor, who signs in on this same page
      try {
        const res = await post<{ token: string }>('/portal/vendor/login/', values)
        localStorage.setItem(VENDOR_TOKEN_KEY, res.token)
        navigate('/vendor', { replace: true })
      } catch {
        setError('Wrong email or password.')
      }
    }
  }

  return (
    <div className="relative isolate flex min-h-full items-center justify-center overflow-hidden bg-gradient-to-br from-[#fff1f3] via-[#f6efff] to-[#fff4dc] p-4">
      <div className="aurora pointer-events-none absolute inset-0 -z-10" aria-hidden="true">
        <span className="-left-20 -top-10 h-96 w-96 bg-brand-500/40" />
        <span className="-right-10 top-1/4 h-[26rem] w-[26rem] bg-violet-400/40" style={{ animationDelay: '-8s' }} />
        <span className="-bottom-20 left-1/4 h-80 w-80 bg-amber-300/50" style={{ animationDelay: '-14s' }} />
      </div>
      {/* little sparkles */}
      {[['12%', '18%', 0], ['82%', '14%', 0.8], ['24%', '78%', 1.6], ['72%', '72%', 2.2], ['50%', '8%', 1.2]].map(([x, y, d], i) => (
        <svg key={i} viewBox="0 0 24 24" className="twinkle pointer-events-none absolute h-5 w-5 text-amber-400" style={{ left: x as string, top: y as string, animationDelay: `${d}s` }} aria-hidden="true">
          <path fill="currentColor" d="M12 0l2.6 9.4L24 12l-9.4 2.6L12 24l-2.6-9.4L0 12l9.4-2.6z" />
        </svg>
      ))}
      <div className="w-full max-w-sm rounded-3xl border border-white/70 bg-white/75 p-7 shadow-2xl shadow-brand-500/10 backdrop-blur-xl" style={{ animation: 'pop 0.7s cubic-bezier(0.2, 0.9, 0.3, 1.1) both' }}>
        <div className="mb-4 flex items-center gap-3">
          <Emblem className="float h-14 w-14" />
          <div>
            <h1 className="bg-gradient-to-r from-brand-700 via-brand-500 to-violet-600 bg-[length:200%_auto] bg-clip-text text-2xl font-bold text-transparent" style={{ animation: 'gradient-pan 6s linear infinite' }}>
              KalyaanaMaalai
            </h1>
            <p className="text-xs text-slate-500">Shaandaar Events · wedding planning</p>
          </div>
        </div>
        <p className="mb-5 text-sm text-slate-500">Welcome back. Team members and vendors sign in here.</p>
        <form className="space-y-4" onSubmit={handleSubmit(onSubmit)} noValidate>
          <Input label="Email" type="email" autoComplete="username" error={errors.email?.message} {...register('email')} />
          <Input
            label="Password"
            type="password"
            autoComplete="current-password"
            error={errors.password?.message}
            {...register('password')}
          />
          {error && (
            <p role="alert" className="text-sm text-red-600">
              {error}
            </p>
          )}
          <Button type="submit" className="w-full" loading={isSubmitting}>
            Sign in
          </Button>
        </form>
        {import.meta.env.DEV && (
          <div className="mt-5 border-t border-slate-100 pt-4 text-xs text-slate-500">
            Demo logins (dev only):
            {['founder', 'planner', 'staff'].map((r) => (
              <button
                key={r}
                type="button"
                className="ml-2 underline"
                onClick={() => {
                  setValue('email', `${r}@shaandaar.demo`)
                  setValue('password', 'Demo@12345')
                }}
              >
                {r}
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
