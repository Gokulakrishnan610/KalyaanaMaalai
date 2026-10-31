import { useMutation, useQuery } from '@tanstack/react-query'
import { useState, type FormEvent } from 'react'
import { get, post } from '@/api/client'
import { Badge, Button, EmptyState, ErrorState, Input, Modal, Select, Spinner, Table, Td, Th } from '@/components/common'
import { formatDate } from '@/helpers/date'
import { formatINR, rupeesToPaise } from '@/helpers/money'
import { useLogin } from '@/login/LoginContext'
import { PayOnline } from './PayOnline'
import { newIdempotencyKey, postWithKey, rupeeText, useRefreshFinance } from './finance'
import { StatusBadge } from './shared'
import { INVOICE_TYPES, METHODS, type Financials, type Invoice, type InvoiceType, type Method } from './types'

interface Props {
  weddingId: number
  finance: Financials
}

export function InvoiceSection({ weddingId, finance }: Props) {
  const canEdit = useLogin().hasRole('PLANNER')
  const [adding, setAdding] = useState<InvoiceType | null>(null)
  const [paying, setPaying] = useState<Invoice | null>(null)
  const [online, setOnline] = useState<Invoice | null>(null)
  const [extraOpen, setExtraOpen] = useState(false)
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['finance', weddingId, 'invoices'],
    queryFn: () => get<Invoice[]>(`/weddings/${weddingId}/invoices/`),
  })
  const hasDeposit = data?.some((i) => i.type === 'DEPOSIT')

  return (
    <section className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-lg font-semibold">Client invoices</h2>
        {canEdit && (
          <div className="flex flex-wrap gap-2">
            {!hasDeposit && (
              <Button variant="secondary" onClick={() => setAdding('DEPOSIT')}>
                Collect deposit
              </Button>
            )}
            <Button variant="secondary" onClick={() => setExtraOpen(true)}>
              Extra guest charges
            </Button>
            <Button onClick={() => setAdding('MILESTONE')}>Add invoice</Button>
          </div>
        )}
      </div>

      {isLoading ? (
        <Spinner />
      ) : error || !data ? (
        <ErrorState message={error?.message ?? 'Could not load invoices'} onRetry={refetch} />
      ) : data.length === 0 ? (
        <EmptyState title="No invoices yet" hint="Collect the booking deposit to start." />
      ) : (
        <Table>
          <thead>
            <tr>
              <Th>Invoice</Th>
              <Th>Due</Th>
              <Th className="text-right">Amount</Th>
              <Th className="text-right">Paid</Th>
              <Th className="text-right">Remaining</Th>
              <Th>Status</Th>
              {canEdit && <Th />}
            </tr>
          </thead>
          <tbody>
            {data.map((invoice) => (
              <tr key={invoice.id}>
                <Td>
                  <div className="font-medium">{invoice.type_label}</div>
                  {invoice.note && <div className="max-w-xs truncate text-xs text-slate-500">{invoice.note}</div>}
                </Td>
                <Td>{formatDate(invoice.due_date)}</Td>
                <Td className="text-right tabular-nums">{formatINR(invoice.amount_paise)}</Td>
                <Td className="text-right tabular-nums">{formatINR(invoice.paid_paise)}</Td>
                <Td className="text-right tabular-nums">{formatINR(invoice.remaining_paise)}</Td>
                <Td>
                  <StatusBadge status={invoice.status} />
                </Td>
                {canEdit && (
                  <Td className="whitespace-nowrap text-right">
                    {invoice.remaining_paise > 0 && (
                      <>
                        <Button variant="ghost" onClick={() => setOnline(invoice)}>
                          Pay online
                        </Button>
                        <Button variant="secondary" onClick={() => setPaying(invoice)}>
                          Record payment
                        </Button>
                      </>
                    )}
                  </Td>
                )}
              </tr>
            ))}
          </tbody>
        </Table>
      )}

      {adding && <AddInvoiceModal weddingId={weddingId} initialType={adding} budget={finance.budget_paise} onClose={() => setAdding(null)} />}
      {paying && <RecordPaymentModal weddingId={weddingId} invoice={paying} onClose={() => setPaying(null)} />}
      {online && <PayOnline weddingId={weddingId} invoice={online} onClose={() => setOnline(null)} />}
      {extraOpen && <ExtraGuestsModal weddingId={weddingId} finance={finance} onClose={() => setExtraOpen(false)} />}
    </section>
  )
}

function AddInvoiceModal({ weddingId, initialType, budget, onClose }: { weddingId: number; initialType: InvoiceType; budget: number; onClose: () => void }) {
  const refresh = useRefreshFinance(weddingId)
  const [type, setType] = useState<InvoiceType>(initialType)
  // a deposit is usually a fifth of the budget; the planner can change it
  const [amount, setAmount] = useState(initialType === 'DEPOSIT' && budget ? rupeeText(Math.round(budget / 5 / 100) * 100) : '')
  const [dueDate, setDueDate] = useState('')
  const [note, setNote] = useState('')
  const save = useMutation({
    mutationFn: () =>
      post(`/weddings/${weddingId}/invoices/`, { type, amount_paise: rupeesToPaise(amount), due_date: dueDate || null, note }),
    onSuccess: async () => {
      await refresh()
      onClose()
    },
  })
  const submit = (event: FormEvent) => {
    event.preventDefault()
    save.mutate()
  }
  return (
    <Modal open title={initialType === 'DEPOSIT' ? 'Collect booking deposit' : 'Add invoice'} onClose={onClose}>
      <form onSubmit={submit} className="space-y-3">
        <Select label="Type" value={type} onChange={(e) => setType(e.target.value as InvoiceType)}>
          {INVOICE_TYPES.map((t) => (
            <option key={t.value} value={t.value}>
              {t.label}
            </option>
          ))}
        </Select>
        <Input label="Amount (₹)" inputMode="decimal" required value={amount} onChange={(e) => setAmount(e.target.value)} />
        <Input label="Due date" type="date" value={dueDate} onChange={(e) => setDueDate(e.target.value)} />
        <Input label="Note" value={note} onChange={(e) => setNote(e.target.value)} />
        {save.error && <p className="text-sm text-red-600">{save.error.message}</p>}
        <div className="flex justify-end gap-2 pt-2">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" loading={save.isPending} disabled={rupeesToPaise(amount) <= 0}>
            Create invoice
          </Button>
        </div>
      </form>
    </Modal>
  )
}

function RecordPaymentModal({ weddingId, invoice, onClose }: { weddingId: number; invoice: Invoice; onClose: () => void }) {
  const refresh = useRefreshFinance(weddingId)
  const [key] = useState(newIdempotencyKey) // one key per opening, so a double click records one payment
  const [amount, setAmount] = useState(rupeeText(invoice.remaining_paise))
  const [method, setMethod] = useState<Method>('UPI')
  const [reference, setReference] = useState('')
  const paise = rupeesToPaise(amount)
  const over = paise > invoice.remaining_paise
  const save = useMutation({
    mutationFn: () => postWithKey(`/invoices/${invoice.id}/payments/`, { amount_paise: paise, method, reference }, key),
    onSuccess: async () => {
      await refresh()
      onClose()
    },
  })
  return (
    <Modal open title={`Record payment · ${invoice.type_label}`} onClose={onClose}>
      <form
        onSubmit={(e) => {
          e.preventDefault()
          save.mutate()
        }}
        className="space-y-3"
      >
        <p className="text-sm text-slate-600">
          Remaining on this invoice: <b className="tabular-nums">{formatINR(invoice.remaining_paise)}</b>
        </p>
        <Input label="Amount received (₹)" inputMode="decimal" required value={amount} onChange={(e) => setAmount(e.target.value)} error={over ? 'More than the remaining balance' : undefined} />
        <Select label="Method" value={method} onChange={(e) => setMethod(e.target.value as Method)}>
          {METHODS.map((m) => (
            <option key={m} value={m}>
              {m}
            </option>
          ))}
        </Select>
        <Input label="Reference (UTR, cheque no.)" value={reference} onChange={(e) => setReference(e.target.value)} />
        {save.error && <p className="text-sm text-red-600">{save.error.message}</p>}
        <div className="flex justify-end gap-2 pt-2">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" loading={save.isPending} disabled={paise <= 0 || over}>
            Record payment
          </Button>
        </div>
      </form>
    </Modal>
  )
}

function ExtraGuestsModal({ weddingId, finance, onClose }: { weddingId: number; finance: Financials; onClose: () => void }) {
  const refresh = useRefreshFinance(weddingId)
  const { contracted_guests, guest_count, per_guest_rate_paise } = finance.wedding
  const [guests, setGuests] = useState(String(guest_count))
  const actual = Number(guests)
  const extra = Math.max(0, (Number.isFinite(actual) ? actual : 0) - contracted_guests)
  const amount = extra * per_guest_rate_paise // preview only: the server works out the real invoice
  const save = useMutation({
    mutationFn: () => post(`/weddings/${weddingId}/invoices/extra-guests/`, { actual_guests: actual }),
    onSuccess: async () => {
      await refresh()
      onClose()
    },
  })
  return (
    <Modal open title="Extra guest charges" onClose={onClose}>
      <div className="space-y-3">
        <p className="text-sm text-slate-600">
          The agreement covers <b>{contracted_guests}</b> guests. Each extra guest is charged{' '}
          <b>{formatINR(per_guest_rate_paise)}</b>.
        </p>
        <Input label="Actual guests" type="number" min={0} value={guests} onChange={(e) => setGuests(e.target.value)} />
        <div className="rounded-xl bg-slate-50 p-3 text-sm">
          {extra > 0 ? (
            <>
              {extra} extra guests × {formatINR(per_guest_rate_paise)} = <b className="tabular-nums">{formatINR(amount)}</b>
            </>
          ) : (
            <span className="text-slate-500">No extra guests: nothing to charge.</span>
          )}
        </div>
        {per_guest_rate_paise === 0 && extra > 0 && <Badge tone="amber">This wedding has no per-guest rate yet</Badge>}
        {save.error && <p className="text-sm text-red-600">{save.error.message}</p>}
        <div className="flex justify-end gap-2 pt-2">
          <Button variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button loading={save.isPending} disabled={extra <= 0 || per_guest_rate_paise === 0} onClick={() => save.mutate()}>
            Create invoice
          </Button>
        </div>
      </div>
    </Modal>
  )
}
