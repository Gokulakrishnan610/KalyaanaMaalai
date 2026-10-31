import { useQuery } from '@tanstack/react-query'
import { get } from '@/api/client'
import { Card } from '@/components/common'
import { formatINR } from '@/helpers/money'
import type { Overview } from './types'

/** Four numbers: what to collect, what is collected, what to pay vendors, and the profit that leaves. */
export function StatCards({ weddingId }: { weddingId: number | null }) {
  const { data } = useQuery({ queryKey: ['finance-overview'], queryFn: () => get<Overview>('/finance/overview/') })
  const rows = (data?.weddings ?? []).filter((w) => weddingId === null || w.wedding_id === weddingId)
  const sum = (field: 'invoiced_paise' | 'received_paise' | 'planned_expense_paise' | 'paid_expense_paise') =>
    rows.reduce((total, w) => total + w[field], 0)

  const invoiced = sum('invoiced_paise')
  const received = sum('received_paise')
  const bills = sum('planned_expense_paise')
  const paid = sum('paid_expense_paise')
  const cards = [
    { label: 'Still to collect', value: invoiced - received, hint: `of ${formatINR(invoiced)} invoiced`, tone: invoiced - received > 0 ? 'text-amber-600' : '' },
    { label: 'Collected', value: received, hint: 'received from customers', tone: 'text-emerald-600' },
    { label: 'Still to pay vendors', value: bills - paid, hint: `of ${formatINR(bills)} in bills`, tone: '' },
    { label: 'Expected profit', value: invoiced - bills, hint: 'invoiced minus vendor bills', tone: invoiced - bills < 0 ? 'text-red-600' : 'text-emerald-600' },
  ]
  return (
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      {cards.map((c) => (
        <Card key={c.label}>
          <div className="text-sm text-slate-500">{c.label}</div>
          <div className={`mt-1 text-2xl font-semibold tabular-nums ${c.tone}`}>{data ? formatINR(c.value) : '…'}</div>
          <div className="mt-1 text-xs text-slate-500">{c.hint}</div>
        </Card>
      ))}
    </div>
  )
}
