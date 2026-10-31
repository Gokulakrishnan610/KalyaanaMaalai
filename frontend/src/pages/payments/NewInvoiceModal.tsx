import { useMutation, useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { get, post } from '@/api/client'
import { Badge, Button, Input, Modal, Select } from '@/components/common'
import { formatINR, rupeesToPaise } from '@/helpers/money'
import { rupeeText, useRefreshMoney } from './finance'
import { INVOICE_TYPES, type InvoiceRow, type InvoiceType, type OverviewRow, type WeddingMoney } from './types'

interface Props {
  /** the wedding when the page is already about one wedding, otherwise the planner picks */
  weddingId: number | null
  weddings: OverviewRow[]
  existing: InvoiceRow[]
  onClose: () => void
}

/** Asks a customer for money: a deposit, an instalment, the final payment, or the charge for extra guests. */
export function NewInvoiceModal({ weddingId, weddings, existing, onClose }: Props) {
  const refresh = useRefreshMoney()
  const [wedding, setWedding] = useState(weddingId ? String(weddingId) : '')
  const hasDeposit = existing.some((i) => i.wedding_id === Number(wedding) && i.type === 'DEPOSIT')
  const [type, setType] = useState<InvoiceType>('DEPOSIT')
  const [amount, setAmount] = useState('')
  const [dueDate, setDueDate] = useState('')
  const [note, setNote] = useState('')
  const [guests, setGuests] = useState('')

  const money = useQuery({
    queryKey: ['finance', 'wedding-money', wedding],
    queryFn: () => get<WeddingMoney>(`/weddings/${wedding}/finance/`),
    enabled: Boolean(wedding),
  })
  const w = money.data?.wedding
  const actual = Number(guests || w?.guest_count || 0)
  const extra = Math.max(0, actual - (w?.contracted_guests ?? 0))
  const extraAmount = extra * (w?.per_guest_rate_paise ?? 0)

  const pickWedding = (id: string) => {
    setWedding(id)
    setGuests('')
  }
  const pickType = (next: InvoiceType) => {
    setType(next)
    // a deposit is usually a fifth of the budget: a starting point the planner can change
    if (next === 'DEPOSIT' && w?.budget_paise && !amount) setAmount(rupeeText(Math.round(w.budget_paise / 5 / 100) * 100))
  }

  const save = useMutation({
    mutationFn: () =>
      type === 'EXTRA_GUESTS'
        ? post(`/weddings/${wedding}/invoices/extra-guests/`, { actual_guests: actual, due_date: dueDate || null })
        : post(`/weddings/${wedding}/invoices/`, { type, amount_paise: rupeesToPaise(amount), due_date: dueDate || null, note }),
    onSuccess: async () => {
      await refresh()
      onClose()
    },
  })

  const ready = Boolean(wedding) && (type === 'EXTRA_GUESTS' ? extra > 0 && extraAmount > 0 : rupeesToPaise(amount) > 0) && !(type === 'DEPOSIT' && hasDeposit)

  return (
    <Modal open title="New invoice" onClose={onClose}>
      <form
        className="space-y-3"
        onSubmit={(e) => {
          e.preventDefault()
          save.mutate()
        }}
      >
        {weddingId === null && (
          <Select label="Wedding" value={wedding} onChange={(e) => pickWedding(e.target.value)} required>
            <option value="">Choose a wedding…</option>
            {weddings.map((x) => (
              <option key={x.wedding_id} value={x.wedding_id}>
                {x.title}
              </option>
            ))}
          </Select>
        )}
        <Select label="What is it for?" value={type} onChange={(e) => pickType(e.target.value as InvoiceType)}>
          {INVOICE_TYPES.map((t) => (
            <option key={t.value} value={t.value} disabled={t.value === 'DEPOSIT' && hasDeposit}>
              {t.label}
              {t.value === 'DEPOSIT' && hasDeposit ? ' (already made)' : ''}
            </option>
          ))}
        </Select>

        {type === 'EXTRA_GUESTS' ? (
          <div className="space-y-2">
            <Input label="Actual guests" type="number" min={0} value={guests || String(w?.guest_count ?? '')} onChange={(e) => setGuests(e.target.value)} />
            <div className="rounded-xl bg-slate-50 p-3 text-sm">
              {!w ? (
                <span className="text-slate-500">Choose a wedding first.</span>
              ) : extra > 0 ? (
                <>
                  {extra} extra guests ({actual} actual, {w.contracted_guests} agreed) × {formatINR(w.per_guest_rate_paise)} ={' '}
                  <b className="tabular-nums">{formatINR(extraAmount)}</b>
                </>
              ) : (
                <span className="text-slate-500">No extra guests, so nothing to charge.</span>
              )}
            </div>
            {w && w.per_guest_rate_paise === 0 && <Badge tone="amber">This wedding has no per-guest rate yet</Badge>}
          </div>
        ) : (
          <>
            <Input label="Amount (₹)" inputMode="decimal" required value={amount} onChange={(e) => setAmount(e.target.value)} />
            <Input label="Note (shown to the customer)" value={note} onChange={(e) => setNote(e.target.value)} />
          </>
        )}
        <Input label="Due date" type="date" value={dueDate} onChange={(e) => setDueDate(e.target.value)} />
        {save.error && (
          <p className="text-sm text-red-600" role="alert">
            {save.error.message}
          </p>
        )}
        <div className="flex justify-end gap-2 pt-2">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" loading={save.isPending} disabled={!ready}>
            Create invoice
          </Button>
        </div>
      </form>
    </Modal>
  )
}
