import { Card } from '@/components/common'
import { formatINR } from '@/helpers/money'
import type { Financials } from './types'

function Stat({ label, value, tone }: { label: string; value: string; tone?: string }) {
  return (
    <div>
      <div className="text-xs text-slate-500">{label}</div>
      <div className={`text-lg font-semibold tabular-nums ${tone ?? ''}`}>{value}</div>
    </div>
  )
}

export function SummaryCards({ data }: { data: Financials }) {
  const { revenue, expenses } = data
  const profitTone = (n: number) => (n < 0 ? 'text-red-600' : 'text-emerald-600')
  return (
    <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
      <Card>
        <div className="mb-3 text-sm font-semibold text-slate-700">Revenue</div>
        <div className="grid grid-cols-3 gap-2">
          <Stat label="Invoiced" value={formatINR(revenue.invoiced)} />
          <Stat label="Received" value={formatINR(revenue.received)} tone="text-emerald-600" />
          <Stat label="Outstanding" value={formatINR(revenue.outstanding)} tone={revenue.outstanding ? 'text-amber-600' : ''} />
        </div>
      </Card>
      <Card>
        <div className="mb-3 text-sm font-semibold text-slate-700">Expenses</div>
        <div className="grid grid-cols-3 gap-2">
          <Stat label="Planned" value={formatINR(expenses.planned)} />
          <Stat label="Paid" value={formatINR(expenses.paid)} />
          <Stat label="Outstanding" value={formatINR(expenses.outstanding)} tone={expenses.outstanding ? 'text-amber-600' : ''} />
        </div>
      </Card>
      <Card>
        <div className="mb-3 text-sm font-semibold text-slate-700">Profit</div>
        <div className="grid grid-cols-2 gap-2">
          <Stat label="Estimated" value={formatINR(data.estimated_profit)} tone={profitTone(data.estimated_profit)} />
          <Stat label="Actual so far" value={formatINR(data.actual_profit)} tone={profitTone(data.actual_profit)} />
        </div>
        <p className="mt-2 text-xs text-slate-500">Estimated = invoiced − planned expenses. Actual = received − paid.</p>
      </Card>
      <Card>
        <div className="mb-3 text-sm font-semibold text-slate-700">Margin</div>
        <div className={`text-3xl font-semibold tabular-nums ${profitTone(data.estimated_profit)}`}>{data.margin_pct}%</div>
        <p className="mt-2 text-xs text-slate-500">
          Budget {formatINR(data.budget_paise)}
          {data.budget_paise > 0 && expenses.planned > data.budget_paise && (
            <span className="ml-1 font-medium text-red-600">· planned spend is over budget</span>
          )}
        </p>
      </Card>
    </div>
  )
}
