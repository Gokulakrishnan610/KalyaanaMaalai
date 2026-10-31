import { useQuery } from '@tanstack/react-query'
import { get } from '@/api/client'
import { Card } from '@/components/common'
import { formatINR } from '@/helpers/money'
import type { Overview } from './types'

/** Four numbers: what to collect, what is collected, what to pay vendors, and the profit that leaves. */
export function StatCards({ weddingId }: { weddingId: number | null }) {
  // the server adds everything up, for all weddings or the one chosen
  const { data } = useQuery({ queryKey: ['finance-overview', weddingId ?? 'all'], queryFn: () => get<Overview>('/finance/overview/', { wedding: weddingId ?? undefined }) })
  const invoiced = data?.totals.invoiced_paise ?? 0
  const received = data?.totals.received_paise ?? 0
  const bills = data?.totals.planned_expense_paise ?? 0
  const paid = data?.totals.paid_expense_paise ?? 0
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
