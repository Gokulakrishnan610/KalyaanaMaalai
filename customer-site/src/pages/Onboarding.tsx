import { useMutation, useQuery } from '@tanstack/react-query'
import { Check } from 'lucide-react'
import { useState } from 'react'
import { Navigate, useNavigate } from 'react-router-dom'
import { ApiError, get, patch, TOKEN_KEY } from '@/api/client'
import type { Portal } from '@/auth/AuthContext'
import { Logo } from '@/components/Logo'
import { Button, Chip, Field, cn } from '@/components/ui'
import { CONTACTS, FUNCTIONS, SERVICES } from '@/data/content'
import { rupeesToPaise } from '@/helpers/money'

const TITLES = ['About you', 'The wedding', 'What you need', 'Anything else']

const toggle = (list: string[], code: string) => (list.includes(code) ? list.filter((c) => c !== code) : [...list, code])

/** The profile wizard: four short steps, each one saved as soon as you press Next. What is filled here appears in our planners' CRM. */
export default function Onboarding() {
  const navigate = useNavigate()
  const loggedIn = Boolean(localStorage.getItem(TOKEN_KEY))
  const { data } = useQuery({ queryKey: ['me'], queryFn: () => get<Portal>('/portal/me/'), enabled: loggedIn })
  const v = data?.profile.values

  const [step, setStep] = useState(0)
  const [form, setForm] = useState<Record<string, string | string[]> | null>(null)
  const [message, setMessage] = useState('')

  // hooks must all come before any early return, so this sits here and takes the fields as an argument
  const save = useMutation({
    mutationFn: (fields: Record<string, unknown>) => patch<Portal>('/portal/profile/', fields),
    onSuccess: () => {
      setMessage('')
      if (step < TITLES.length - 1) setStep(step + 1)
      else navigate('/home?welcome=1')
    },
    onError: (e) => setMessage(e instanceof ApiError ? e.message : 'Something went wrong. Please try again.'),
  })

  if (!loggedIn) return <Navigate to="/login" replace />
  if (!data || !v) return <div className="p-10 text-center text-stone-500">Loading…</div>

  // start from what is already saved, so someone coming back sees their earlier answers
  const f = form ?? {
    partner_name: v.partner_name,
    preferred_contact: v.preferred_contact,
    wedding_date: v.wedding_date ?? '',
    venue_city: v.venue_city,
    guest_count: v.guest_count ? String(v.guest_count) : '',
    budget: v.budget_paise ? String(v.budget_paise / 100) : '',
    functions_wanted: v.functions_wanted,
    services_needed: v.services_needed,
    notes: v.notes,
  }
  const set = (key: string, value: string | string[]) => setForm({ ...f, [key]: value })
  const text = (key: string) => String(f[key] ?? '')
  const list = (key: string) => (f[key] as string[]) ?? []

  const fieldsForStep = (): Record<string, unknown> => {
    if (step === 0) return { partner_name: text('partner_name'), preferred_contact: text('preferred_contact') }
    if (step === 1)
      return {
        wedding_date: text('wedding_date') || null,
        venue_city: text('venue_city'),
        guest_count: text('guest_count') ? Number(text('guest_count')) : null,
        budget_paise: text('budget') ? rupeesToPaise(text('budget')) : null,
        functions_wanted: list('functions_wanted'),
      }
    if (step === 2) return { services_needed: list('services_needed') }
    return { notes: text('notes') }
  }

  const last = step === TITLES.length - 1
  const today = new Date().toISOString().slice(0, 10)

  return (
    <div className="min-h-full bg-ivory">
      <header className="border-b border-stone-200 bg-white">
        <div className="mx-auto flex h-16 max-w-3xl items-center justify-between px-5">
          <Logo />
          <button onClick={() => navigate('/home')} className="text-sm text-stone-500 hover:text-maroon-700">Skip for now</button>
        </div>
      </header>

      <main className="mx-auto max-w-3xl px-5 py-10">
        <ol className="mb-8 flex items-center gap-2" aria-label="Progress">
          {TITLES.map((t, i) => (
            <li key={t} className="flex flex-1 items-center gap-2">
              <span className={cn('flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-sm font-semibold', i < step ? 'bg-gold-500 text-maroon-900' : i === step ? 'bg-maroon-600 text-white' : 'bg-stone-200 text-stone-500')}>
                {i < step ? <Check size={16} /> : i + 1}
              </span>
              <span className={cn('hidden text-sm sm:block', i === step ? 'font-semibold text-maroon-900' : 'text-stone-500')}>{t}</span>
              {i < TITLES.length - 1 && <span className="h-px flex-1 bg-stone-300" />}
            </li>
          ))}
        </ol>

        <div className="rounded-3xl bg-white p-6 shadow-sm ring-1 ring-stone-200 md:p-10">
          {step === 0 && (
            <div className="space-y-6">
              <div>
                <h1 className="font-serif text-3xl font-semibold text-maroon-900">Welcome, {data.customer.name.split(' ')[0]}</h1>
                <p className="mt-1 text-stone-600">Let us know a little about you. Everything here helps our planner prepare for your call.</p>
              </div>
              <Field label="Your partner's name" value={text('partner_name')} onChange={(e) => set('partner_name', e.target.value)} />
              <div>
                <p className="mb-2 text-sm font-medium text-stone-700">How should we contact you?</p>
                <div className="flex flex-wrap gap-2">
                  {CONTACTS.map((c) => (
                    <Chip key={c.code} selected={text('preferred_contact') === c.code} onClick={() => set('preferred_contact', c.code)}>
                      {c.label}
                    </Chip>
                  ))}
                </div>
              </div>
            </div>
          )}

          {step === 1 && (
            <div className="space-y-6">
              <div>
                <h1 className="font-serif text-3xl font-semibold text-maroon-900">About the wedding</h1>
                <p className="mt-1 text-stone-600">A rough idea is enough. We can change anything later.</p>
              </div>
              <div className="grid gap-4 sm:grid-cols-2">
                <Field label="Wedding date" type="date" min={today} value={text('wedding_date')} onChange={(e) => set('wedding_date', e.target.value)} />
                <Field label="City" value={text('venue_city')} onChange={(e) => set('venue_city', e.target.value)} placeholder="Where will it be?" />
                <Field label="Number of guests" type="number" min={1} value={text('guest_count')} onChange={(e) => set('guest_count', e.target.value)} />
                <Field label="Budget in ₹ (optional)" inputMode="numeric" value={text('budget')} onChange={(e) => set('budget', e.target.value)} hint="Only so we can suggest what fits" />
              </div>
              <div>
                <p className="mb-2 text-sm font-medium text-stone-700">Which functions do you want?</p>
                <div className="flex flex-wrap gap-2">
                  {FUNCTIONS.map((fn) => (
                    <Chip key={fn.code} selected={list('functions_wanted').includes(fn.code)} onClick={() => set('functions_wanted', toggle(list('functions_wanted'), fn.code))}>
                      {fn.label}
                    </Chip>
                  ))}
                </div>
              </div>
            </div>
          )}

          {step === 2 && (
            <div className="space-y-6">
              <div>
                <h1 className="font-serif text-3xl font-semibold text-maroon-900">What do you need help with?</h1>
                <p className="mt-1 text-stone-600">Pick everything that applies.</p>
              </div>
              <div className="grid gap-3 sm:grid-cols-2">
                {SERVICES.map(({ code, label, text: hint, icon: Icon }) => {
                  const on = list('services_needed').includes(code)
                  return (
                    <button
                      key={code}
                      type="button"
                      aria-pressed={on}
                      onClick={() => set('services_needed', toggle(list('services_needed'), code))}
                      className={cn('flex items-center gap-4 rounded-2xl border p-4 text-left transition', on ? 'border-maroon-600 bg-maroon-50 ring-2 ring-maroon-600/20' : 'border-stone-200 hover:border-maroon-500')}
                    >
                      <span className={cn('flex h-11 w-11 shrink-0 items-center justify-center rounded-full', on ? 'bg-maroon-600 text-white' : 'bg-stone-100 text-stone-600')}>
                        <Icon size={20} />
                      </span>
                      <span>
                        <span className="block font-semibold text-maroon-900">{label}</span>
                        <span className="block text-xs text-stone-500">{hint}</span>
                      </span>
                    </button>
                  )
                })}
              </div>
            </div>
          )}

          {step === 3 && (
            <div className="space-y-6">
              <div>
                <h1 className="font-serif text-3xl font-semibold text-maroon-900">Anything else we should know?</h1>
                <p className="mt-1 text-stone-600">Themes, traditions, special requests. Anything at all.</p>
              </div>
              <textarea
                rows={5}
                value={text('notes')}
                onChange={(e) => set('notes', e.target.value)}
                className="w-full rounded-xl border border-stone-300 p-4 text-base outline-none focus:border-maroon-500 focus:ring-4 focus:ring-maroon-100"
                placeholder="For example: a traditional South Indian ceremony with a small sangeet."
              />
              <dl className="space-y-1.5 rounded-2xl bg-ivory p-5 text-sm">
                <div className="flex justify-between gap-4"><dt className="text-stone-500">Couple</dt><dd className="font-medium">{data.customer.name} &amp; {text('partner_name') || '-'}</dd></div>
                <div className="flex justify-between gap-4"><dt className="text-stone-500">Date and city</dt><dd className="font-medium">{text('wedding_date') || '-'} · {text('venue_city') || '-'}</dd></div>
                <div className="flex justify-between gap-4"><dt className="text-stone-500">Guests</dt><dd className="font-medium">{text('guest_count') || '-'}</dd></div>
                <div className="flex justify-between gap-4"><dt className="text-stone-500">Needs help with</dt><dd className="text-right font-medium">{list('services_needed').length ? list('services_needed').map((c) => SERVICES.find((s) => s.code === c)?.label).join(', ') : '-'}</dd></div>
              </dl>
            </div>
          )}

          {message && <p role="alert" className="mt-6 rounded-xl bg-red-50 p-3 text-sm text-red-700">{message}</p>}

          <div className="mt-8 flex items-center justify-between">
            <Button look="ghost" onClick={() => setStep(step - 1)} disabled={step === 0}>Back</Button>
            <Button loading={save.isPending} onClick={() => save.mutate(fieldsForStep())}>{last ? 'Finish' : 'Save and continue'}</Button>
          </div>
        </div>
      </main>
    </div>
  )
}
