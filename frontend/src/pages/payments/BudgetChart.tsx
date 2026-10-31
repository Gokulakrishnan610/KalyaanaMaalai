import { Bar, BarChart, CartesianGrid, Cell, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { Card, CardTitle, EmptyState } from '@/components/common'
import { formatINR } from '@/helpers/money'
import type { Financials } from './types'

const lakh = (rupees: number) => `₹${(rupees / 100000).toFixed(1)}L`
const tooltip = (value: unknown) => formatINR(Number(value) * 100)

export function BudgetChart({ data }: { data: Financials }) {
  const categories = data.by_category.map((c) => ({
    name: c.category,
    Planned: c.planned / 100,
    Paid: c.paid / 100,
  }))
  const overall = [
    { name: 'Budget', value: data.budget_paise / 100, fill: '#94a3b8' },
    { name: 'Invoiced', value: data.revenue.invoiced / 100, fill: '#38bdf8' },
    { name: 'Planned', value: data.expenses.planned / 100, fill: '#f59e0b' },
    { name: 'Paid', value: data.expenses.paid / 100, fill: '#fb7185' },
    { name: 'Est. profit', value: data.estimated_profit / 100, fill: data.estimated_profit < 0 ? '#dc2626' : '#10b981' },
    { name: 'Actual', value: data.actual_profit / 100, fill: data.actual_profit < 0 ? '#dc2626' : '#059669' },
  ]
  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <Card>
        <CardTitle>Planned vs paid, by category</CardTitle>
        {categories.length === 0 ? (
          <EmptyState title="No expenses yet" hint="Add a vendor bill to see it here." />
        ) : (
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={categories}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="name" tick={{ fontSize: 10 }} interval={0} />
                <YAxis tickFormatter={lakh} tick={{ fontSize: 11 }} width={56} />
                <Tooltip formatter={tooltip} />
                <Legend />
                <Bar dataKey="Planned" fill="#f59e0b" radius={[4, 4, 0, 0]} />
                <Bar dataKey="Paid" fill="#e5395c" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </Card>
      <Card>
        <CardTitle>Budget, spend and profit</CardTitle>
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={overall}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="name" tick={{ fontSize: 11 }} interval={0} />
              <YAxis tickFormatter={lakh} tick={{ fontSize: 11 }} width={56} />
              <Tooltip formatter={tooltip} />
              <Bar dataKey="value" name="Amount" radius={[4, 4, 0, 0]}>
                {overall.map((row) => (
                  <Cell key={row.name} fill={row.fill} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </Card>
    </div>
  )
}
