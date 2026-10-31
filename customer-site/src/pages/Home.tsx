import { useMutation, useQuery } from '@tanstack/react-query'
import { CalendarHeart, CheckCircle2, MessageCircle, Wallet } from 'lucide-react'
import { Link, Navigate, useNavigate, useSearchParams } from 'react-router-dom'
import { ApiError, get, post, TOKEN_KEY } from '@/api/client'
import { useAuth, type Portal } from '@/auth/AuthContext'
import { Logo } from '@/components/Logo'
import { Button, LinkButton, cn } from '@/components/ui'
import { SERVICES } from '@/data/content'
import { formatDate, formatDateTime, formatINR } from '@/helpers/money'

const JOURNEY = ['Request received', 'Planner in touch', 'Consultation', 'Proposal', 'Booked']

interface InvoiceRow {
  id: number
  label: string
  note: string
  wedding: string
  due_date: string | null
  amount_paise: number
  paid_paise: number
  remaining_paise: number
  status: 'UNPAID' | 'PARTIAL' | 'PAID'
}

const WHATSAPP = import.meta.env.VITE_WHATSAPP as string | undefined

/** The couple's own page: where the wedding stands, their details, and their payments. It refreshes by itself every 20 seconds. */
export default function Home() {
  const { logout } = useAuth()
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const loggedIn = Boolean(localStorage.getItem(TOKEN_KEY))

  const me = useQuery({ queryKey: ['me'], queryFn: () => get<Portal>('/portal/me/'), enabled: loggedIn, refetchInterval: 20_000 })
  const invoices = useQuery({
    queryKey: ['invoices'],
    queryFn: () => get<InvoiceRow[]>('/portal/invoices/'),
    enabled: loggedIn && Boolean(me.data?.is_client),
    refetchInterval: 20_000,
  })
  const pay = useMutation({
    mutationFn: (id: number) => post<{ path: string }>(`/portal/invoices/${id}/pay/`),
    onSuccess: (res) => navigate(res.path),
  })

  if (!loggedIn) return <Navigate to="/login" replace />
  if (me.isLoading || !me.data) return <div className="p-10 text-center text-stone-500">Loading…</div>
  const d = me.data
  const v = d.profile.values
  const due = (invoices.data ?? []).filter((i) => i.remaining_paise > 0)

  return (
    <div className="min-h-screen">
      <header className="border-b border-stone-200 bg-white">
        <div className="mx-auto flex h-16 max-w-5xl items-center justify-between px-5">
          <Logo />
          <div className="flex items-center gap-4 text-sm">
            <span className="hidden text-stone-600 sm:block">{d.customer.name}</span>
            <button onClick={() => { logout(); navigate('/') }} className="font-medium text-maroon-700 hover:underline">Log out</button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-5xl space-y-6 px-5 py-8">
        {params.get('welcome') && (
          <div className="flex items-start gap-3 rounded-2xl bg-emerald-50 p-4 text-emerald-800">
            <CheckCircle2 className="mt-0.5 shrink-0" size={20} />
            <p className="text-sm">Thank you! We have your details. A planner will contact you {v.preferred_contact === 'WHATSAPP' ? 'on WhatsApp' : v.preferred_contact === 'EMAIL' ? 'by email' : 'by phone'} soon.</p>
          </div>
        )}

        <div>
          <h1 className="font-serif text-3xl font-semibold text-maroon-900">Namaste, {d.customer.name.split(' ')[0]}</h1>
          <p className="text-stone-600">Here is where your wedding stands.</p>
        </div>

        <section className="rounded-3xl bg-white p-6 shadow-sm ring-1 ring-stone-200 md:p-8">
          <div className="flex items-center gap-2 text-sm font-semibold uppercase tracking-wide text-gold-500"><CalendarHeart size={16} /> Your wedding</div>
          <h2 className="mt-1 font-serif text-2xl text-maroon-900">{d.stage.label}</h2>
          <p className="text-stone-600">{d.stage.hint}</p>
          {d.stage.consultation_at && <p className="mt-2 text-sm font-medium text-maroon-700">Consultation: {formatDateTime(d.stage.consultation_at)}</p>}
          {d.stage.step >= 0 && (
            <ol className="mt-6 grid grid-cols-5 gap-2" aria-label="Wedding progress">
              {JOURNEY.map((name, i) => (
                <li key={name} className="text-center">
                  <div className={cn('mx-auto mb-2 h-2 rounded-full', i <= d.stage.step ? 'bg-maroon-600' : 'bg-stone-200')} />
                  <span className={cn('text-[11px] leading-tight sm:text-xs', i === d.stage.step ? 'font-semibold text-maroon-700' : 'text-stone-500')}>{name}</span>
                </li>
              ))}
            </ol>
          )}
        </section>

        <div className="grid gap-6 md:grid-cols-2">
          <section className="rounded-3xl bg-white p-6 shadow-sm ring-1 ring-stone-200">
            <div className="flex items-center justify-between">
              <h2 className="font-serif text-xl text-maroon-900">Your details</h2>
              <span className="text-sm font-semibold text-maroon-700">{d.profile.percent}% done</span>
            </div>
            <div className="mt-3 h-2 overflow-hidden rounded-full bg-stone-200">
              <div className="h-full rounded-full bg-maroon-600 transition-all" style={{ width: `${d.profile.percent}%` }} />
            </div>
            {!d.profile.complete ? (
              <>
                <p className="mt-4 text-sm text-stone-600">Still needed: {d.profile.missing.join(', ')}.</p>
                <LinkButton to="/start" className="mt-4">Complete my profile</LinkButton>
              </>
            ) : (
              <>
                <dl className="mt-4 space-y-1.5 text-sm">
                  <div className="flex justify-between gap-4"><dt className="text-stone-500">Partner</dt><dd className="font-medium">{v.partner_name}</dd></div>
                  <div className="flex justify-between gap-4"><dt className="text-stone-500">Date</dt><dd className="font-medium">{formatDate(v.wedding_date)}</dd></div>
                  <div className="flex justify-between gap-4"><dt className="text-stone-500">City</dt><dd className="font-medium">{v.venue_city}</dd></div>
                  <div className="flex justify-between gap-4"><dt className="text-stone-500">Guests</dt><dd className="font-medium">{v.guest_count}</dd></div>
                  <div className="flex justify-between gap-4"><dt className="text-stone-500">Help with</dt><dd className="text-right font-medium">{v.services_needed.map((c) => SERVICES.find((s) => s.code === c)?.label).join(', ')}</dd></div>
                </dl>
                <Link to="/start" className="mt-4 inline-block text-sm font-semibold text-maroon-700 hover:underline">Edit my details</Link>
              </>
            )}
          </section>

          <section className="rounded-3xl bg-white p-6 shadow-sm ring-1 ring-stone-200">
            <div className="flex items-center gap-2"><Wallet size={18} className="text-maroon-600" /><h2 className="font-serif text-xl text-maroon-900">Your payments</h2></div>
            {!d.is_client ? (
              <p className="mt-4 text-sm text-stone-600">Your payments will show up here once your wedding is booked with us. You will be able to pay online with one tap.</p>
            ) : invoices.isLoading ? (
              <p className="mt-4 text-sm text-stone-500">Loading…</p>
            ) : !invoices.data?.length ? (
              <p className="mt-4 text-sm text-stone-600">Nothing to pay right now.</p>
            ) : (
              <ul className="mt-4 divide-y divide-stone-100">
                {invoices.data.map((i) => (
                  <li key={i.id} className="flex flex-wrap items-center justify-between gap-3 py-3">
                    <div>
                      <div className="font-medium text-maroon-900">{i.label}</div>
                      <div className="text-xs text-stone-500">{i.due_date ? `Due ${formatDate(i.due_date)}` : i.wedding}{i.paid_paise > 0 && i.remaining_paise > 0 ? ` · ${formatINR(i.paid_paise)} paid` : ''}</div>
                    </div>
                    {i.remaining_paise > 0 ? (
                      <Button className="py-2" loading={pay.isPending && pay.variables === i.id} onClick={() => pay.mutate(i.id)}>Pay {formatINR(i.remaining_paise)}</Button>
                    ) : (
                      <span className="rounded-full bg-emerald-50 px-3 py-1 text-sm font-semibold text-emerald-700">Paid</span>
                    )}
                  </li>
                ))}
              </ul>
            )}
            {pay.error && <p role="alert" className="mt-3 text-sm text-red-600">{pay.error instanceof ApiError ? pay.error.message : 'Could not start the payment.'}</p>}
            {d.is_client && due.length === 0 && invoices.data && invoices.data.length > 0 && <p className="mt-3 text-sm text-emerald-700">You are all paid up. Thank you!</p>}
          </section>
        </div>

        <section className="flex flex-wrap items-center justify-between gap-4 rounded-3xl bg-maroon-900 p-6 text-white">
          <div>
            <h2 className="font-serif text-xl">Need to talk to us?</h2>
            <p className="text-sm text-white/75">Your planner will contact you. You can also message us any time.</p>
          </div>
          {WHATSAPP ? (
            <a href={`https://wa.me/${WHATSAPP}?text=${encodeURIComponent(`Hello, this is ${d.customer.name}`)}`} target="_blank" rel="noreferrer" className="inline-flex items-center gap-2 rounded-full bg-gold-500 px-6 py-3 text-sm font-semibold text-maroon-900 hover:bg-gold-400">
              <MessageCircle size={16} /> Chat on WhatsApp
            </a>
          ) : (
            <span className="text-sm text-white/60">Your planner has your number.</span>
          )}
        </section>
      </main>
    </div>
  )
}
