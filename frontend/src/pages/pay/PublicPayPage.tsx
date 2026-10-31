import { useQuery, useQueryClient } from '@tanstack/react-query'
import { CircleCheck, Clock, ShieldCheck } from 'lucide-react'
import { useState, type ReactNode } from 'react'
import { useParams } from 'react-router-dom'
import { ApiError, get, post } from '@/api/client'
import { Button, Spinner } from '@/components/common'
import { formatDate, formatDateTime } from '@/helpers/date'
import { formatINR } from '@/helpers/money'
import type { GatewayOrder, PublicLink } from '@/pages/payments/types'
import { loadCheckout, openCheckout, type CheckoutResponse } from './razorpay'

function Shell({ business, children }: { business?: string; children: ReactNode }) {
  return (
    <div className="flex min-h-full flex-col items-center bg-brand-50 px-4 py-10">
      <div className="mb-6 text-center">
        <div className="text-xl font-semibold text-brand-700">{business ?? 'Shaandaar Events'}</div>
        <div className="text-sm text-slate-500">Secure payment</div>
      </div>
      <div className="w-full max-w-md rounded-2xl border border-slate-200/70 bg-white p-6 shadow-sm">{children}</div>
      <p className="mt-6 flex items-center gap-1.5 text-xs text-slate-500">
        <ShieldCheck size={14} /> Your card and bank details are handled by the payment gateway and never reach us.
      </p>
    </div>
  )
}

const NOTICES: Record<string, { title: string; text: string }> = {
  EXPIRED: { title: 'This link has expired', text: 'Please ask us for a new payment link.' },
  CANCELLED: { title: 'This link is no longer valid', text: 'Please ask us for a new payment link.' },
  SETTLED: { title: 'This invoice is already paid', text: 'Nothing more to pay here. Thank you!' },
}

/** The page a customer lands on from a payment link: it shows what to pay, takes the payment, shows a receipt. */
export default function PublicPayPage() {
  const { token } = useParams()
  const queryClient = useQueryClient()
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState('')
  const key = ['public-pay', token]

  const { data, isLoading, error } = useQuery({
    queryKey: key,
    queryFn: () => get<PublicLink>(`/pay/${token}/`),
    retry: false,
  })

  if (isLoading) return <Shell><Spinner /></Shell>
  if (error || !data) {
    return (
      <Shell>
        <h1 className="text-lg font-semibold">This payment link is not valid</h1>
        <p className="mt-2 text-sm text-slate-600">Please check the link you were sent, or ask Shaandaar Events to send it again.</p>
      </Shell>
    )
  }

  // the server confirms the payment itself, so nothing here has to be updated by hand
  const confirm = async (response: CheckoutResponse) => {
    try {
      queryClient.setQueryData(key, await post<PublicLink>(`/pay/${token}/verify/`, response))
    } catch (e) {
      setMessage(e instanceof ApiError ? e.message : 'We could not confirm your payment. If money was deducted, please contact us.')
    } finally {
      setBusy(false)
    }
  }

  const pay = async () => {
    setBusy(true)
    setMessage('')
    try {
      const order = await post<GatewayOrder>(`/pay/${token}/order/`)
      if (order.mock) {
        await confirm({ razorpay_order_id: order.order_id, razorpay_payment_id: order.mock_payment_id!, razorpay_signature: order.mock_signature! })
        return
      }
      await loadCheckout()
      openCheckout({
        key: order.key_id,
        amount: order.amount,
        currency: order.currency,
        order_id: order.order_id,
        name: data.business,
        description: data.for,
        prefill: { name: data.couple },
        handler: (response: CheckoutResponse) => void confirm(response),
        modal: { ondismiss: () => setBusy(false) },
      })
    } catch (e) {
      setMessage(e instanceof ApiError ? e.message : e instanceof Error ? e.message : 'Something went wrong. Please try again.')
      setBusy(false)
      queryClient.invalidateQueries({ queryKey: key })
    }
  }

  if (data.status === 'PAID' && data.receipt) {
    return (
      <Shell business={data.business}>
        <div className="text-center">
          <CircleCheck size={48} className="mx-auto text-emerald-500" />
          <h1 className="mt-3 text-xl font-semibold">Payment received</h1>
          <p className="text-sm text-slate-500">Thank you, {data.couple}!</p>
        </div>
        <dl className="mt-5 space-y-2 border-t border-slate-100 pt-4 text-sm">
          {[
            ['Amount paid', formatINR(data.receipt.amount_paise)],
            ['For', `${data.for} · ${data.wedding}`],
            ['Receipt number', data.receipt.number],
            ['Paid on', formatDateTime(data.receipt.paid_at)],
            ['Payment reference', data.receipt.reference || '-'],
          ].map(([label, value]) => (
            <div key={label} className="flex justify-between gap-4">
              <dt className="text-slate-500">{label}</dt>
              <dd className="text-right font-medium">{value}</dd>
            </div>
          ))}
        </dl>
        <Button variant="secondary" className="mt-5 w-full print:hidden" onClick={() => window.print()}>
          Print receipt
        </Button>
      </Shell>
    )
  }

  const notice = NOTICES[data.status]
  if (notice) {
    return (
      <Shell business={data.business}>
        <Clock size={36} className="text-slate-400" />
        <h1 className="mt-2 text-lg font-semibold">{notice.title}</h1>
        <p className="mt-1 text-sm text-slate-600">{notice.text}</p>
      </Shell>
    )
  }

  const left = data.invoice_total_paise - data.paid_so_far_paise
  return (
    <Shell business={data.business}>
      <p className="text-sm text-slate-500">Payment request for</p>
      <h1 className="text-lg font-semibold">{data.couple}</h1>
      <p className="text-sm text-slate-500">
        {data.wedding} · {formatDate(data.wedding_date)}
      </p>

      <div className="my-5 rounded-2xl bg-brand-50 p-5 text-center">
        <div className="text-sm text-slate-600">{data.for}</div>
        <div className="mt-1 text-4xl font-semibold tabular-nums text-brand-700">{formatINR(data.amount_paise)}</div>
        {data.note && <div className="mt-1 text-xs text-slate-500">{data.note}</div>}
      </div>

      <dl className="mb-5 space-y-1.5 text-sm">
        <div className="flex justify-between">
          <dt className="text-slate-500">Invoice total</dt>
          <dd className="tabular-nums">{formatINR(data.invoice_total_paise)}</dd>
        </div>
        <div className="flex justify-between">
          <dt className="text-slate-500">Already paid</dt>
          <dd className="tabular-nums">{formatINR(data.paid_so_far_paise)}</dd>
        </div>
        <div className="flex justify-between">
          <dt className="text-slate-500">Balance after this payment</dt>
          <dd className="tabular-nums">{formatINR(Math.max(0, left - data.amount_paise))}</dd>
        </div>
        {data.due_date && (
          <div className="flex justify-between">
            <dt className="text-slate-500">Due date</dt>
            <dd>{formatDate(data.due_date)}</dd>
          </div>
        )}
      </dl>

      {data.demo_mode && data.available && (
        <p className="mb-3 rounded-xl bg-amber-50 p-3 text-xs text-amber-800">
          Demo mode: no real money moves. Pressing the button below pretends to pay, and the payment is recorded.
        </p>
      )}
      {!data.available ? (
        <p className="rounded-xl bg-amber-50 p-3 text-sm text-amber-800">
          Online payments are not switched on yet. Please contact Shaandaar Events to pay.
        </p>
      ) : (
        <Button className="w-full py-3 text-base" loading={busy} onClick={pay}>
          Pay {formatINR(data.amount_paise)}
        </Button>
      )}
      {message && (
        <p role="alert" className="mt-3 rounded-xl bg-red-50 p-3 text-sm text-red-700">
          {message}
        </p>
      )}
      <p className="mt-4 text-center text-xs text-slate-400">Link valid until {formatDateTime(data.expires_at)}</p>
    </Shell>
  )
}
