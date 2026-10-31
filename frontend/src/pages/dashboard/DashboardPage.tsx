import { useQuery } from '@tanstack/react-query'
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { Badge, Card, CardTitle, EmptyState, ErrorState, Spinner, Table, Td, Th } from '@/components/common'
import { get } from '@/api/client'
import { formatDate, formatDateTime } from '@/helpers/date'
import { formatINR } from '@/helpers/money'
import { useLogin } from '@/login/LoginContext'
import { sourceInfo, type Source } from '@/pages/enquiries/types'

interface Summary {
  active_enquiries: number
  enquiries_by_source: { source: Source; count: number }[]
  conversion_rate: number
  upcoming_weddings: { id: number; title: string; date: string }[]
  total_revenue_paise: number
  total_received_paise: number
  total_expenses_paise: number
  total_profit_paise: number
  outstanding_client_paise: number
  upcoming_vendor_payments: {
    expense_id: number
    wedding_title: string
    vendor_name: string
    description: string
    due_date: string
    outstanding_paise: number
    overdue: boolean
  }[]
  late_vendors_today: number
  upcoming_consultations: { id: number; couple_name: string; consultation_at: string }[]
  per_wedding: {
    wedding_id: number
    title: string
    client_name: string
    date: string
    revenue_paise: number
    expense_paise: number
    profit_paise: number
    margin_pct: number
    progress_pct: number
  }[]
}

function Kpi({ label, value, hint, tone }: { label: string; value: string; hint?: string; tone?: 'good' | 'bad' }) {
  const colour = tone === 'good' ? 'text-emerald-600' : tone === 'bad' ? 'text-red-600' : 'text-slate-900'
  return (
    <Card>
      <div className="text-sm text-slate-500">{label}</div>
      <div className={`mt-1 text-2xl font-semibold ${colour}`}>{value}</div>
      {hint && <div className="mt-1 text-xs text-slate-500">{hint}</div>}
    </Card>
  )
}

export default function DashboardPage() {
  const { hasRole } = useLogin()
  const allowed = hasRole('PLANNER')
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['dashboard'],
    queryFn: () => get<Summary>('/dashboard/summary/'),
    enabled: allowed,
  })

  if (!allowed) {
    return (
      <div>
        <h1 className="mb-4 text-2xl font-semibold">Dashboard</h1>
        <EmptyState title="The dashboard is for the founder and planners" hint="Use the menu to open your tasks and weddings." />
      </div>
    )
  }
  if (isLoading) return <Spinner />
  if (error || !data) return <ErrorState message={error?.message ?? 'Could not load the dashboard'} onRetry={refetch} />

  const chartData = data.enquiries_by_source.map((s) => ({ name: sourceInfo(s.source).label, count: s.count }))

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">Dashboard</h1>

      {data.late_vendors_today > 0 && (
        <div role="alert" className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm font-medium text-red-700">
          {data.late_vendors_today} vendor{data.late_vendors_today > 1 ? 's are' : ' is'} running late today.
        </div>
      )}

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Kpi label="Revenue (invoiced)" value={formatINR(data.total_revenue_paise)} hint={`${formatINR(data.total_received_paise)} received`} />
        <Kpi label="Expenses (vendor bills)" value={formatINR(data.total_expenses_paise)} />
        <Kpi label="Profit" value={formatINR(data.total_profit_paise)} tone={data.total_profit_paise >= 0 ? 'good' : 'bad'} />
        <Kpi label="Couples still owe us" value={formatINR(data.outstanding_client_paise)} />
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardTitle>Where enquiries come from</CardTitle>
          {chartData.length === 0 ? (
            <p className="py-8 text-center text-sm text-slate-500">No enquiries yet.</p>
          ) : (
            <div className="h-56">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} />
                  <XAxis dataKey="name" fontSize={12} />
                  <YAxis allowDecimals={false} fontSize={12} />
                  <Tooltip />
                  <Bar dataKey="count" name="Enquiries" fill="#c2185b" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
          <p className="mt-2 text-xs text-slate-500">
            {data.active_enquiries} open enquiries · {data.conversion_rate}% became clients
          </p>
        </Card>

        <Card>
          <CardTitle>Upcoming consultations</CardTitle>
          {data.upcoming_consultations.length === 0 ? (
            <p className="text-sm text-slate-500">None booked.</p>
          ) : (
            <ul className="space-y-2 text-sm">
              {data.upcoming_consultations.map((c) => (
                <li key={c.id} className="flex justify-between">
                  <span className="font-medium">{c.couple_name}</span>
                  <span className="text-slate-500">{formatDateTime(c.consultation_at)}</span>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>

      <div>
        <h2 className="mb-2 text-sm font-semibold text-slate-700">Profit per wedding</h2>
        {data.per_wedding.length === 0 ? (
          <EmptyState title="No weddings yet" hint="Convert an enquiry and start a wedding project." />
        ) : (
          <Table>
            <thead>
              <tr>
                <Th>Wedding</Th>
                <Th>Date</Th>
                <Th className="text-right">Revenue</Th>
                <Th className="text-right">Expenses</Th>
                <Th className="text-right">Profit</Th>
                <Th className="text-right">Margin</Th>
                <Th>Tasks done</Th>
              </tr>
            </thead>
            <tbody>
              {data.per_wedding.map((w) => (
                <tr key={w.wedding_id}>
                  <Td>
                    <div className="font-medium">{w.title}</div>
                    <div className="text-xs text-slate-500">{w.client_name}</div>
                  </Td>
                  <Td>{formatDate(w.date)}</Td>
                  <Td className="text-right">{formatINR(w.revenue_paise)}</Td>
                  <Td className="text-right">{formatINR(w.expense_paise)}</Td>
                  <Td className={`text-right font-medium ${w.profit_paise >= 0 ? 'text-emerald-600' : 'text-red-600'}`}>
                    {formatINR(w.profit_paise)}
                  </Td>
                  <Td className="text-right">{w.margin_pct}%</Td>
                  <Td>
                    <div className="h-2 w-24 overflow-hidden rounded-full bg-slate-200">
                      <div className="h-full bg-brand-500" style={{ width: `${w.progress_pct}%` }} />
                    </div>
                  </Td>
                </tr>
              ))}
            </tbody>
          </Table>
        )}
      </div>

      <Card>
        <CardTitle>Vendor payments due this week</CardTitle>
        {data.upcoming_vendor_payments.length === 0 ? (
          <p className="text-sm text-slate-500">Nothing due in the next 7 days.</p>
        ) : (
          <ul className="divide-y divide-slate-100 text-sm">
            {data.upcoming_vendor_payments.map((p) => (
              <li key={p.expense_id} className="flex flex-wrap items-center justify-between gap-2 py-2">
                <span>
                  <span className="font-medium">{p.vendor_name || p.description}</span>
                  <span className="text-slate-500"> · {p.wedding_title}</span>
                </span>
                <span className="flex items-center gap-3">
                  {formatDate(p.due_date)} {p.overdue && <Badge tone="red">Overdue</Badge>}
                  <span className="font-medium">{formatINR(p.outstanding_paise)}</span>
                </span>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  )
}
