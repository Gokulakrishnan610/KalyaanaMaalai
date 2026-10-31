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
    <div className="flex min-h-full items-center justify-center bg-[#f6f7f9] p-4">
      <div className="w-full max-w-sm rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
        <div className="mb-6 flex items-center gap-3">
          <Emblem className="h-10 w-10" />
          <div>
            <h1 className="text-lg font-semibold tracking-tight text-slate-900">KalyaanaMaalai</h1>
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
