import { useQuery, useQueryClient } from '@tanstack/react-query'
import { CircleCheck, Clock, ShieldCheck } from 'lucide-react'
import { useState, type ReactNode } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ApiError, get, post } from '@/api/client'
import { Logo } from '@/components/Logo'
import { Button } from '@/components/ui'
import { formatDate, formatDateTime, formatINR } from '@/helpers/money'

interface PublicLink {
  business: string
  couple: string
  wedding: string
  wedding_date: string
  for: string
  note: string
  due_date: string | null
  invoice_total_paise: number
  paid_so_far_paise: number
  amount_paise: number
  status: 'ACTIVE' | 'PAID' | 'CANCELLED' | 'EXPIRED' | 'SETTLED'
  expires_at: string
  demo_mode: boolean
  available: boolean
  receipt: { number: string; paid_at: string; amount_paise: number; reference: string } | null
}
interface Order { order_id: string; amount: number; currency: string; key_id: string; mock: boolean; mock_payment_id?: string; mock_signature?: string }
interface Checkout { razorpay_order_id: string; razorpay_payment_id: string; razorpay_signature: string }
type RazorpayCtor = new (options: Record<string, unknown>) => { open: () => void }

function loadCheckout(): Promise<void> {
  if ((window as unknown as { Razorpay?: RazorpayCtor }).Razorpay) return Promise.resolve()
  return new Promise((resolve, reject) => {
    const script = document.createElement('script')
    script.src = 'https://checkout.razorpay.com/v1/checkout.js'
    script.onload = () => resolve()
    script.onerror = () => reject(new Error('Could not load the payment window. Please check your internet and try again.'))
    document.body.appendChild(script)
  })
}

function Shell({ children }: { children: ReactNode }) {
  return (
    <div className="flex min-h-screen flex-col items-center bg-blush px-4 py-10">
      <div className="mb-6 text-center"><Logo /></div>
      <div className="w-full max-w-md rounded-3xl bg-white p-6 shadow-sm ring-1 ring-stone-200">{children}</div>
      <p className="mt-6 flex items-center gap-1.5 text-xs text-stone-500"><ShieldCheck size={14} /> Your card and bank details go to the payment gateway, never to us.</p>
    </div>
  )
}

const NOTICES: Record<string, string> = {
  EXPIRED: 'This payment link has expired. Please go back to your account and press Pay again.',
  CANCELLED: 'This payment link is no longer valid. Please go back to your account and press Pay again.',
  SETTLED: 'This invoice is already paid. Thank you!',
}

/** Where a couple lands to pay: from their account's Pay button or from a link sent on WhatsApp. */
export default function Pay() {
  const { token } = useParams()
  const queryClient = useQueryClient()
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState('')
  const key = ['pay', token]
  const { data, isLoading, error } = useQuery({ queryKey: key, queryFn: () => get<PublicLink>(`/pay/${token}/`), retry: false })

  if (isLoading) return <Shell><p className="py-8 text-center text-stone-500">Loading…</p></Shell>
  if (error || !data) return <Shell><h1 className="font-serif text-xl text-maroon-900">This payment link is not valid</h1><p className="mt-2 text-sm text-stone-600">Please check the link, or go to <Link to="/home" className="font-semibold text-maroon-700">your account</Link>.</p></Shell>

  const confirm = async (response: Checkout) => {
    try {
      queryClient.setQueryData(key, await post<PublicLink>(`/pay/${token}/verify/`, response))
      queryClient.invalidateQueries({ queryKey: ['invoices'] })
    } catch (e) {
      setMessage(e instanceof ApiError ? e.message : 'We could not confirm your payment. If money was deducted, please contact us.')
    } finally {
      setBusy(false)
    }
  }

  const start = async () => {
    setBusy(true)
    setMessage('')
    try {
      const order = await post<Order>(`/pay/${token}/order/`)
      if (order.mock) {
        await confirm({ razorpay_order_id: order.order_id, razorpay_payment_id: order.mock_payment_id!, razorpay_signature: order.mock_signature! })
        return
      }
      await loadCheckout()
      const Razorpay = (window as unknown as { Razorpay: RazorpayCtor }).Razorpay
      new Razorpay({
        key: order.key_id, amount: order.amount, currency: order.currency, order_id: order.order_id,
        name: data.business, description: data.for, prefill: { name: data.couple },
        handler: (r: Checkout) => void confirm(r),
        modal: { ondismiss: () => setBusy(false) },
      }).open()
    } catch (e) {
      setMessage(e instanceof ApiError ? e.message : e instanceof Error ? e.message : 'Something went wrong. Please try again.')
      setBusy(false)
    }
  }

  if (data.status === 'PAID' && data.receipt) {
    return (
      <Shell>
        <div className="text-center">
          <CircleCheck size={48} className="mx-auto text-emerald-500" />
          <h1 className="mt-3 font-serif text-2xl text-maroon-900">Payment received</h1>
          <p className="text-sm text-stone-500">Thank you, {data.couple}!</p>
        </div>
        <dl className="mt-5 space-y-2 border-t border-stone-100 pt-4 text-sm">
          {[['Amount paid', formatINR(data.receipt.amount_paise)], ['For', data.for], ['Receipt number', data.receipt.number], ['Paid on', formatDateTime(data.receipt.paid_at)]].map(([l, v]) => (
            <div key={l} className="flex justify-between gap-4"><dt className="text-stone-500">{l}</dt><dd className="font-medium">{v}</dd></div>
          ))}
        </dl>
        <div className="mt-5 flex gap-3 print:hidden">
          <Button look="outline" className="flex-1" onClick={() => window.print()}>Print receipt</Button>
          <Link to="/home" className="flex-1 rounded-full bg-maroon-600 px-6 py-3 text-center text-sm font-semibold text-white hover:bg-maroon-700">My account</Link>
        </div>
      </Shell>
    )
  }

  if (NOTICES[data.status]) {
    return <Shell><Clock size={36} className="text-stone-400" /><p className="mt-3 text-stone-700">{NOTICES[data.status]}</p><Link to="/home" className="mt-4 inline-block text-sm font-semibold text-maroon-700">Go to my account</Link></Shell>
  }

  return (
    <Shell>
      <p className="text-sm text-stone-500">Payment for</p>
      <h1 className="font-serif text-2xl text-maroon-900">{data.couple}</h1>
      <p className="text-sm text-stone-500">{data.wedding} · {formatDate(data.wedding_date)}</p>
      <div className="my-5 rounded-2xl bg-maroon-50 p-5 text-center">
        <div className="text-sm text-stone-600">{data.for}</div>
        <div className="mt-1 font-serif text-4xl font-semibold text-maroon-700">{formatINR(data.amount_paise)}</div>
        {data.note && <div className="mt-1 text-xs text-stone-500">{data.note}</div>}
      </div>
      <dl className="mb-5 space-y-1.5 text-sm">
        <div className="flex justify-between"><dt className="text-stone-500">Invoice total</dt><dd>{formatINR(data.invoice_total_paise)}</dd></div>
        <div className="flex justify-between"><dt className="text-stone-500">Already paid</dt><dd>{formatINR(data.paid_so_far_paise)}</dd></div>
        {data.due_date && <div className="flex justify-between"><dt className="text-stone-500">Due date</dt><dd>{formatDate(data.due_date)}</dd></div>}
      </dl>
      {data.demo_mode && data.available && <p className="mb-3 rounded-xl bg-amber-50 p-3 text-xs text-amber-800">Demo mode: no real money moves. The button below pretends to pay.</p>}
      {!data.available ? <p className="rounded-xl bg-amber-50 p-3 text-sm text-amber-800">Online payment is not switched on yet. Please contact us to pay.</p> : <Button className="w-full py-3 text-base" loading={busy} onClick={start}>Pay {formatINR(data.amount_paise)}</Button>}
      {message && <p role="alert" className="mt-3 rounded-xl bg-red-50 p-3 text-sm text-red-700">{message}</p>}
      <p className="mt-4 text-center text-xs text-stone-400">Link valid until {formatDateTime(data.expires_at)}</p>
    </Shell>
  )
}
