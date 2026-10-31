import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { get } from '@/api/client'
import { Badge, Card, CardTitle, EmptyState, ErrorState, Select, Spinner, Table, Td, Th } from '@/components/common'
import { formatDate } from '@/helpers/date'
import { formatINR } from '@/helpers/money'
import { FinanceTab } from './FinanceTab'
import type { Overview } from './types'
import { UpcomingPayments } from './UpcomingPayments'

const tone = (n: number) => (n < 0 ? 'text-red-600' : 'text-emerald-600')

/** The Finance page: profit of every wedding, what is due soon, and one wedding's full finances. */
export default function PaymentsPage() {
  const [picked, setPicked] = useState<number | null>(null)
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['finance-overview'],
    queryFn: () => get<Overview>('/finance/overview/'),
  })
  if (isLoading) return <Spinner />
  if (error || !data) return <ErrorState message={error?.message ?? 'Could not load finances'} onRetry={refetch} />

  // start on a wedding that actually has money in it
  const weddingId = picked ?? (data.weddings.find((w) => w.invoiced_paise > 0) ?? data.weddings[0])?.wedding_id ?? null
  const totals = data.totals
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Finance</h1>
        <p className="text-sm text-slate-500">Money in from couples, money out to vendors, and the profit on every wedding.</p>
      </div>

      <div className="grid gap-4 md:grid-cols-4">
        {[
          ['Invoiced', totals.invoiced_paise, ''],
          ['Received', totals.received_paise, 'text-emerald-600'],
          ['Planned expenses', totals.planned_expense_paise, ''],
          ['Estimated profit', totals.estimated_profit_paise, tone(totals.estimated_profit_paise)],
        ].map(([label, value, color]) => (
          <Card key={label as string}>
            <div className="text-xs text-slate-500">{label}</div>
            <div className={`text-2xl font-semibold tabular-nums ${color}`}>{formatINR(value as number)}</div>
          </Card>
        ))}
      </div>

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_24rem]">
        <div className="min-w-0">
          <CardTitle>Profit by wedding</CardTitle>
          {data.weddings.length === 0 ? (
            <EmptyState title="No weddings yet" hint="Finances appear once a wedding is created." />
          ) : (
            <Table>
              <thead>
                <tr>
                  <Th>Wedding</Th>
                  <Th>Date</Th>
                  <Th className="text-right">Invoiced</Th>
                  <Th className="text-right">Planned expenses</Th>
                  <Th className="text-right">Est. profit</Th>
                  <Th className="text-right">Margin</Th>
                </tr>
              </thead>
              <tbody>
                {data.weddings.map((w) => (
                  <tr
                    key={w.wedding_id}
                    className={`cursor-pointer hover:bg-slate-50 ${w.wedding_id === weddingId ? 'bg-brand-50/60' : ''}`}
                    onClick={() => setPicked(w.wedding_id)}
                  >
                    <Td>
                      <div className="font-medium">{w.title}</div>
                      <div className="text-xs text-slate-500">{w.client_name}</div>
                    </Td>
                    <Td>{formatDate(w.date)}</Td>
                    <Td className="text-right tabular-nums">{formatINR(w.invoiced_paise)}</Td>
                    <Td className="text-right tabular-nums">{formatINR(w.planned_expense_paise)}</Td>
                    <Td className={`text-right font-semibold tabular-nums ${tone(w.estimated_profit_paise)}`}>
                      {formatINR(w.estimated_profit_paise)}
                    </Td>
                    <Td className="text-right">
                      <Badge tone={w.margin_pct < 0 ? 'red' : w.margin_pct < 15 ? 'amber' : 'green'}>{w.margin_pct}%</Badge>
                    </Td>
                  </tr>
                ))}
              </tbody>
            </Table>
          )}
        </div>
        <UpcomingPayments />
      </div>

      {weddingId !== null && (
        <div className="space-y-4 border-t border-slate-200 pt-6">
          <div className="flex flex-wrap items-center gap-3">
            <h2 className="text-xl font-semibold">Wedding finances</h2>
            <div className="w-72">
              <Select aria-label="Choose a wedding" value={weddingId} onChange={(e) => setPicked(Number(e.target.value))}>
                {data.weddings.map((w) => (
                  <option key={w.wedding_id} value={w.wedding_id}>
                    {w.title}
                  </option>
                ))}
              </Select>
            </div>
          </div>
          <FinanceTab key={weddingId} weddingId={weddingId} />
        </div>
      )}
    </div>
  )
}
