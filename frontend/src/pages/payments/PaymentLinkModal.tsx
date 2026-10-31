import { useMutation, useQuery } from '@tanstack/react-query'
import { Copy, ExternalLink, Mail, MessageCircle } from 'lucide-react'
import { useState } from 'react'
import { get, post } from '@/api/client'
import { Button, Input, Modal, Select } from '@/components/common'
import { formatDateTime } from '@/helpers/date'
import { formatINR, rupeesToPaise } from '@/helpers/money'
import { linkUrl, rupeeText, useRefreshMoney } from './finance'
import { LinkBadge } from './shared'
import type { InvoiceRow, PaymentLink } from './types'

/** WhatsApp wants the number with the country code and no symbols. */
function whatsappNumber(phone: string): string {
  const digits = phone.replace(/\D/g, '')
  return digits.length === 10 ? `91${digits}` : digits
}

/** Makes a payment link for an invoice and helps send it. When the customer pays, the invoice updates by itself. */
export function PaymentLinkModal({ invoice: opened, onClose }: { invoice: InvoiceRow; onClose: () => void }) {
  const refresh = useRefreshMoney()
  // the invoice is read again whenever money arrives (the key starts with "finance"), so what this dialog says stays true
  const latest = useQuery({
    queryKey: ['finance', 'invoice', opened.id],
    queryFn: async () => (await get<InvoiceRow[]>('/invoices/', { wedding: opened.wedding_id })).find((i) => i.id === opened.id) ?? opened,
  })
  const invoice = latest.data ?? opened
  const [amount, setAmount] = useState(rupeeText(opened.remaining_paise))
  const [days, setDays] = useState('7')
  const [copied, setCopied] = useState('')
  const paise = rupeesToPaise(amount)
  const over = paise > invoice.remaining_paise

  // key starts with "finance", so a live "payment recorded" event refreshes this list the moment a customer pays
  const links = useQuery({ queryKey: ['finance', 'links', invoice.id], queryFn: () => get<PaymentLink[]>(`/invoices/${invoice.id}/payment-links/`) })
  const create = useMutation({
    mutationFn: () => post<PaymentLink>(`/invoices/${invoice.id}/payment-links/`, { amount_paise: paise, days: Number(days) }),
    onSuccess: async () => {
      await links.refetch()
      await refresh()
    },
  })
  const cancel = useMutation({
    mutationFn: (id: number) => post(`/payment-links/${id}/cancel/`),
    onSuccess: async () => {
      await links.refetch()
      await refresh()
    },
  })

  const message = (link: PaymentLink) =>
    `Hello ${invoice.client_name}, here is your secure payment link from Shaandaar Events for ${invoice.type_label.toLowerCase()} ` +
    `(${formatINR(link.amount_paise)}): ${linkUrl(link.path)}`
  const copy = async (link: PaymentLink) => {
    await navigator.clipboard?.writeText(linkUrl(link.path))
    setCopied(link.token)
    window.setTimeout(() => setCopied(''), 2000)
  }

  const waiting = links.data?.filter((l) => l.status === 'ACTIVE') ?? []
  const history = links.data?.filter((l) => l.status !== 'ACTIVE') ?? []
  const canCreate = invoice.remaining_paise > 0

  return (
    <Modal open title={`Payment link · ${invoice.client_name}`} onClose={onClose} wide>
      <div className="space-y-5 text-sm">
        <p className="text-slate-600">
          {invoice.type_label} · {invoice.wedding_title}. Still to collect: <b className="tabular-nums">{formatINR(invoice.remaining_paise)}</b>. Send the link to the
          customer: they see the amount, pay online, and this payment is recorded by itself.
        </p>

        {canCreate && (
          <form
            className="grid items-end gap-3 rounded-xl bg-slate-50 p-3 sm:grid-cols-[1fr_9rem_auto]"
            onSubmit={(e) => {
              e.preventDefault()
              create.mutate()
            }}
          >
            <Input label="Amount to ask for (₹)" inputMode="decimal" value={amount} onChange={(e) => setAmount(e.target.value)} error={over ? 'More than is still due' : undefined} />
            <Select label="Valid for" value={days} onChange={(e) => setDays(e.target.value)}>
              {[1, 3, 7, 14, 30].map((d) => (
                <option key={d} value={d}>
                  {d} day{d > 1 ? 's' : ''}
                </option>
              ))}
            </Select>
            <Button type="submit" loading={create.isPending} disabled={paise <= 0 || over}>
              Create link
            </Button>
          </form>
        )}
        {create.error && (
          <p role="alert" className="text-red-600">
            {create.error.message}
          </p>
        )}

        {waiting.map((link) => (
          <div key={link.id} className="space-y-3 rounded-xl border border-brand-100 bg-brand-50/40 p-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div>
                <b className="tabular-nums">{formatINR(link.amount_paise)}</b> <LinkBadge status={link.status} />
              </div>
              <span className="text-xs text-slate-500">Valid until {formatDateTime(link.expires_at)}</span>
            </div>
            <input
              readOnly
              aria-label="Payment link"
              value={linkUrl(link.path)}
              onFocus={(e) => e.currentTarget.select()}
              className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs"
            />
            <div className="flex flex-wrap gap-2">
              <Button variant="secondary" onClick={() => copy(link)}>
                <Copy size={14} /> {copied === link.token ? 'Copied' : 'Copy link'}
              </Button>
              <a
                className="inline-flex items-center gap-2 rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
                href={`https://wa.me/${whatsappNumber(invoice.client_phone)}?text=${encodeURIComponent(message(link))}`}
                target="_blank"
                rel="noreferrer"
              >
                <MessageCircle size={14} /> Send on WhatsApp
              </a>
              {invoice.client_email && (
                <a
                  className="inline-flex items-center gap-2 rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
                  href={`mailto:${invoice.client_email}?subject=${encodeURIComponent('Your payment link from Shaandaar Events')}&body=${encodeURIComponent(message(link))}`}
                >
                  <Mail size={14} /> Email
                </a>
              )}
              <a
                className="inline-flex items-center gap-2 rounded-xl px-3 py-2 text-sm text-slate-600 hover:bg-slate-100"
                href={linkUrl(link.path)}
                target="_blank"
                rel="noreferrer"
              >
                <ExternalLink size={14} /> Preview
              </a>
              <Button variant="ghost" loading={cancel.isPending && cancel.variables === link.id} onClick={() => cancel.mutate(link.id)}>
                Cancel link
              </Button>
            </div>
          </div>
        ))}

        {history.length > 0 && (
          <div>
            <div className="mb-1 font-medium text-slate-700">Earlier links</div>
            <ul className="divide-y divide-slate-100">
              {history.map((l) => (
                <li key={l.id} className="flex items-center justify-between gap-2 py-2">
                  <span className="tabular-nums">{formatINR(l.amount_paise)}</span>
                  <LinkBadge status={l.status} />
                  <span className="text-xs text-slate-500">{l.paid_at ? `Paid ${formatDateTime(l.paid_at)}` : `Made ${formatDateTime(l.created_at)}`}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
        {!canCreate && waiting.length === 0 && <p className="rounded-xl bg-emerald-50 p-3 text-emerald-700">This invoice is fully paid.</p>}
        <div className="flex justify-end">
          <Button variant="secondary" onClick={onClose}>
            Close
          </Button>
        </div>
      </div>
    </Modal>
  )
}
