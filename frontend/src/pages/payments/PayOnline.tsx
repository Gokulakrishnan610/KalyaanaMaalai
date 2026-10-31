import { useMutation } from '@tanstack/react-query'
import { useEffect, useRef, useState } from 'react'
import { post } from '@/api/client'
import { Button, Modal, Spinner } from '@/components/common'
import { formatINR } from '@/helpers/money'
import { useRefreshFinance } from './finance'
import type { Invoice, RazorpayOrder } from './types'

interface CheckoutResponse {
  razorpay_order_id: string
  razorpay_payment_id: string
  razorpay_signature: string
}

interface RazorpayWindow {
  Razorpay?: new (options: Record<string, unknown>) => { open: () => void; on: (event: string, cb: (r: unknown) => void) => void }
}

const CHECKOUT_SRC = 'https://checkout.razorpay.com/v1/checkout.js'

function loadCheckout(): Promise<void> {
  if ((window as RazorpayWindow).Razorpay) return Promise.resolve()
  return new Promise((resolve, reject) => {
    const script = document.createElement('script')
    script.src = CHECKOUT_SRC
    script.onload = () => resolve()
    script.onerror = () => reject(new Error('Could not load Razorpay. Check your internet connection, or record the payment by hand.'))
    document.body.appendChild(script)
  })
}

/**
 * "Pay online": asks the server for an order, then opens Razorpay's test checkout (or a demo checkout while
 * the server is in mock mode). The server checks the signature and records exactly one payment.
 * Test card 4111 1111 1111 1111 with any future expiry and CVV; UPI id success@razorpay.
 */
export function PayOnline({ weddingId, invoice, onClose }: { weddingId: number; invoice: Invoice; onClose: () => void }) {
  const refresh = useRefreshFinance(weddingId)
  const [order, setOrder] = useState<RazorpayOrder | null>(null)
  const [done, setDone] = useState(false)
  const started = useRef(false)

  const verify = useMutation({
    mutationFn: (body: CheckoutResponse) => post(`/invoices/${invoice.id}/razorpay/verify/`, body),
    onSuccess: async () => {
      setDone(true)
      await refresh()
    },
  })

  const create = useMutation({
    mutationFn: () => post<RazorpayOrder>(`/invoices/${invoice.id}/razorpay/order/`),
    onSuccess: async (created) => {
      setOrder(created)
      if (created.mock) return
      try {
        await loadCheckout()
        const checkout = new (window as RazorpayWindow).Razorpay!({
          key: created.key_id,
          amount: created.amount,
          currency: created.currency,
          order_id: created.order_id,
          name: 'Shaandaar Events',
          description: invoice.type_label,
          handler: (response: CheckoutResponse) => verify.mutate(response),
          modal: { ondismiss: onClose },
        })
        checkout.open()
      } catch (error) {
        verify.reset()
        create.reset()
        setLoadError(error instanceof Error ? error.message : 'Could not open Razorpay.')
      }
    },
  })
  const [loadError, setLoadError] = useState('')

  useEffect(() => {
    if (started.current) return
    started.current = true
    create.mutate()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const message = loadError || create.error?.message || verify.error?.message
  return (
    <Modal open title={`Pay online · ${invoice.type_label}`} onClose={onClose}>
      <div className="space-y-4 text-sm">
        {done ? (
          <>
            <p className="rounded-xl bg-emerald-50 p-3 text-emerald-700">Payment received and recorded. Thank you!</p>
            <div className="flex justify-end">
              <Button onClick={onClose}>Close</Button>
            </div>
          </>
        ) : message ? (
          <>
            <p className="rounded-xl bg-red-50 p-3 text-red-700" role="alert">
              {message}
            </p>
            <p className="text-slate-600">You can close this and use “Record payment” to enter it by hand.</p>
            <div className="flex justify-end">
              <Button variant="secondary" onClick={onClose}>
                Close
              </Button>
            </div>
          </>
        ) : order?.mock ? (
          <>
            <p className="rounded-xl bg-amber-50 p-3 text-amber-800">
              Demo checkout: the server is in mock mode, so no real money moves. Add Razorpay test keys to use the real test checkout.
            </p>
            <p>
              Pay <b className="tabular-nums">{formatINR(order.amount)}</b> for this invoice?
            </p>
            <div className="flex justify-end gap-2">
              <Button variant="secondary" onClick={onClose}>
                Cancel
              </Button>
              <Button
                loading={verify.isPending}
                onClick={() =>
                  verify.mutate({
                    razorpay_order_id: order.order_id,
                    razorpay_payment_id: order.mock_payment_id!,
                    razorpay_signature: order.mock_signature!,
                  })
                }
              >
                Pay {formatINR(order.amount)} (demo)
              </Button>
            </div>
          </>
        ) : (
          <div className="flex items-center gap-3 text-slate-600">
            <Spinner /> {verify.isPending ? 'Confirming your payment…' : 'Opening Razorpay…'}
          </div>
        )}
      </div>
    </Modal>
  )
}
