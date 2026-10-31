import { useQuery } from '@tanstack/react-query'
import {
  AlertTriangle,
  ArrowRight,
  Bell,
  CalendarHeart,
  FileText,
  IndianRupee,
  ListChecks,
  Receipt,
  Store,
  Truck,
  UserPlus,
  Wallet,
  type LucideIcon,
} from 'lucide-react'
import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { get } from '@/api/client'
import { Badge, CountUp, EmptyState, ErrorState, Panel, ShowMore, Spinner } from '@/components/common'
import { formatDate, formatDateTime, timeAgo } from '@/helpers/date'
import { formatINR } from '@/helpers/money'
import { useLogin } from '@/login/LoginContext'
import { sourceInfo, type Source } from '@/pages/enquiries/types'

interface Summary {
  active_enquiries: number
  open_incidents: number
  critical_incidents: number
  recent_incidents: { id: number; title: string; wedding_title: string; severity: string; status: string; assigned_to_name: string }[]
  overdue_follow_ups: number
  pipeline_expected_paise: number
  upcoming_follow_ups: { id: number; enquiry_id: number; couple_name: string; kind: string; summary: string; due_at: string; overdue: boolean }[]
  enquiries_by_source: { source: Source; count: number }[]
  conversion_rate: number
  total_weddings: number
  ongoing_weddings: number
  open_tasks: number
  overdue_tasks: number
  recent_activity: { kind: 'enquiry' | 'payment' | 'vendor' | 'alert'; text: string; at: string }[]
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

function Kpi({ label, value, hint, icon: Icon, to }: { label: string; value: ReactNode; hint: ReactNode; icon: LucideIcon; to: string }) {
  return (
    <Link to={to} className="lift group rounded-xl border border-slate-200 bg-white p-5 shadow-xs">
      <div className="flex items-center justify-between text-sm text-slate-500">
        {label}
        <Icon size={16} className="text-slate-400" />
      </div>
      <div className="num mt-2 truncate text-2xl font-semibold tracking-tight text-slate-900">{value}</div>
      <div className="mt-1 text-xs text-slate-500">{hint}</div>
    </Link>
  )
}

const QUICK_LINKS: { to: string; label: string; icon: LucideIcon }[] = [
  { to: '/enquiries', label: 'New enquiry', icon: UserPlus },
  { to: '/weddings', label: 'Weddings', icon: CalendarHeart },
  { to: '/vendors', label: 'Vendors', icon: Store },
  { to: '/quotations', label: 'Quotations', icon: FileText },
]

function greeting() {
  const hour = new Date().getHours()
  return hour < 12 ? 'Good morning' : hour < 17 ? 'Good afternoon' : 'Good evening'
}

const ACTIVITY_ICON: Record<Summary['recent_activity'][number]['kind'], { icon: LucideIcon; tint: string }> = {
  enquiry: { icon: UserPlus, tint: 'bg-sky-50 text-sky-600' },
  payment: { icon: IndianRupee, tint: 'bg-emerald-50 text-emerald-600' },
  vendor: { icon: Truck, tint: 'bg-amber-50 text-amber-600' },
  alert: { icon: Bell, tint: 'bg-rose-50 text-rose-600' },
}

const Empty = ({ children }: { children: ReactNode }) => <p className="py-6 text-center text-sm text-slate-500">{children}</p>

export default function DashboardPage() {
  const { user, hasRole } = useLogin()
  const allowed = hasRole('PLANNER')
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['dashboard'],
    queryFn: () => get<Summary>('/dashboard/summary/'),
    enabled: allowed,
    refetchInterval: 30_000, // keeps the activity feed fresh
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

  // the wedding coming up soonest, for the line under the greeting
  const today = new Date().toISOString().slice(0, 10)
  const upcoming = [...data.per_wedding].filter((w) => w.date >= today).sort((a, b) => a.date.localeCompare(b.date))
  const next = upcoming[0] ?? null
  const days = next ? Math.ceil((new Date(next.date).getTime() - Date.now()) / 86_400_000) : null
  const sourceData = data.enquiries_by_source.map((s) => ({ name: sourceInfo(s.source).label, count: s.count }))
  // only weddings with money on them, biggest first, so the chart is not mostly empty columns
  const moneyData = data.per_wedding
    .filter((w) => w.revenue_paise || w.expense_paise)
    .sort((a, b) => b.revenue_paise - a.revenue_paise)
    .slice(0, 6)
    .map((w) => ({ name: w.client_name || w.title, Revenue: w.revenue_paise / 100, Expenses: w.expense_paise / 100 }))
  const alerts = [
    data.late_vendors_today > 0 && { text: `${data.late_vendors_today} vendor${data.late_vendors_today > 1 ? 's are' : ' is'} running late today`, to: '/weddings' },
    data.critical_incidents > 0 && { text: `${data.critical_incidents} serious incident${data.critical_incidents > 1 ? 's need' : ' needs'} attention`, to: '/incidents' },
    data.overdue_follow_ups > 0 && { text: `${data.overdue_follow_ups} follow-up${data.overdue_follow_ups > 1 ? 's are' : ' is'} overdue`, to: '/enquiries' },
  ].filter(Boolean) as { text: string; to: string }[]

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-sm text-slate-500">{new Date().toLocaleDateString('en-IN', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' })}</p>
          <h1 className="mt-0.5 text-2xl font-semibold tracking-tight text-slate-900">{greeting()}, {user?.name.split(' ')[0]}</h1>
          <p className="mt-1 text-sm text-slate-600">
            {next && days !== null
              ? <>Next up: <Link to={`/weddings/${next.wedding_id}`} className="font-medium text-slate-900 hover:text-brand-700">{next.title}</Link> in {days} day{days === 1 ? '' : 's'}, {next.progress_pct}% planned.</>
              : 'No weddings are lined up yet.'}
            {data.active_enquiries > 0 && <> {data.active_enquiries} open enquiries worth about {formatINR(data.pipeline_expected_paise)}.</>}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          {QUICK_LINKS.map(({ to, label, icon: Icon }, i) => (
            <Link
              key={to}
              to={to}
              className={i === 0
                ? 'inline-flex h-9 items-center gap-2 rounded-lg bg-brand-600 px-4 text-sm font-medium text-white shadow-xs hover:bg-brand-700'
                : 'inline-flex h-9 items-center gap-2 rounded-lg border border-slate-300 bg-white px-3 text-sm font-medium text-slate-700 shadow-xs hover:bg-slate-50'}
            >
              <Icon size={15} /> {label}
            </Link>
          ))}
        </div>
      </div>

      {alerts.length > 0 && (
        <div role="alert" className="flex flex-wrap gap-2">
          {alerts.map((a) => (
            <Link key={a.text} to={a.to} className="inline-flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm font-medium text-red-700 hover:bg-red-100">
              <AlertTriangle size={15} /> {a.text} <ArrowRight size={14} />
            </Link>
          ))}
        </div>
      )}

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Kpi to="/weddings" label="Weddings" value={<CountUp value={data.total_weddings} />} hint={`${data.ongoing_weddings} ongoing`} icon={CalendarHeart} />
        <Kpi to="/payments" label="Revenue" value={<CountUp value={data.total_revenue_paise} format={formatINR} />} hint={`${formatINR(data.total_received_paise)} received so far`} icon={Wallet} />
        <Kpi to="/payments" label="Expenses" value={<CountUp value={data.total_expenses_paise} format={formatINR} />} hint={<>Profit <span className="font-medium text-emerald-700">{formatINR(data.total_profit_paise)}</span></>} icon={Receipt} />
        <Kpi
          to="/weddings"
          label="Open tasks"
          value={<CountUp value={data.open_tasks} />}
          hint={data.overdue_tasks ? <span className="font-medium text-red-600">{data.overdue_tasks} overdue</span> : 'None overdue'}
          icon={ListChecks}
        />
      </div>

      <div className="grid items-start gap-6 xl:grid-cols-3">
        <Panel title="Revenue and expenses by wedding" className="xl:col-span-2">
          {moneyData.length === 0 ? (
            <Empty>Nothing to compare yet.</Empty>
          ) : (
            <div style={{ height: 56 + moneyData.length * 44 }}>
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={moneyData} layout="vertical" margin={{ left: 8, right: 16 }} barGap={2}>
                  <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#e2e8f0" />
                  <XAxis type="number" fontSize={11} stroke="#94a3b8" tickFormatter={(v: number) => (v >= 100000 ? `${v / 100000}L` : String(v))} />
                  <YAxis type="category" dataKey="name" width={130} fontSize={12} stroke="#64748b" tickLine={false} axisLine={false} />
                  <Tooltip formatter={(v) => formatINR(Number(v) * 100)} cursor={{ fill: '#f1f5f9' }} />
                  <Legend iconType="circle" iconSize={8} wrapperStyle={{ fontSize: 12 }} />
                  <Bar dataKey="Revenue" fill="#9c1c40" radius={[0, 4, 4, 0]} barSize={12} />
                  <Bar dataKey="Expenses" fill="#94a3b8" radius={[0, 4, 4, 0]} barSize={12} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
        </Panel>

        <Panel
          title="Recent activity"
          action={<span className="flex items-center gap-1.5 text-xs text-emerald-600"><span className="h-1.5 w-1.5 animate-pulse rounded-full bg-emerald-500" /> Live</span>}
        >
          {data.recent_activity.length === 0 ? (
            <Empty>Nothing has happened yet.</Empty>
          ) : (
            <ShowMore
              items={data.recent_activity}
              limit={5}
              noun="older updates"
              render={(item, index) => {
                const { icon: Icon, tint } = ACTIVITY_ICON[item.kind]
                return (
                  <li key={index} className="flex items-start gap-3 text-sm">
                    <span className={`mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-lg ${tint}`}><Icon size={14} /></span>
                    <span className="min-w-0 flex-1">
                      <span className="block leading-snug text-slate-700">{item.text}</span>
                      <span className="text-xs text-slate-400">{timeAgo(item.at)}</span>
                    </span>
                  </li>
                )
              }}
            />
          )}
        </Panel>
      </div>

      <div className="grid gap-6 lg:grid-cols-2 xl:grid-cols-3">
        <Panel title="Upcoming weddings" count={upcoming.length} to="/weddings">
          {upcoming.length === 0 ? (
            <Empty>No weddings coming up. Convert an enquiry to start one.</Empty>
          ) : (
            <ShowMore
              items={upcoming}
              limit={4}
              to="/weddings"
              noun="weddings"
              className="space-y-4"
              render={(w) => (
                <li key={w.wedding_id}>
                  <div className="flex items-center justify-between gap-2 text-sm">
                    <Link to={`/weddings/${w.wedding_id}`} className="truncate font-medium text-slate-900 hover:text-brand-700">{w.title}</Link>
                    <span className="num text-xs text-slate-500">{w.progress_pct}%</span>
                  </div>
                  <div className="text-xs text-slate-500">{formatDate(w.date)}</div>
                  <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-slate-100">
                    <div className="bar-grow h-full rounded-full bg-brand-600" style={{ width: `${Math.max(w.progress_pct, 2)}%` }} />
                  </div>
                </li>
              )}
            />
          )}
        </Panel>

        <Panel title="Follow-ups" count={data.upcoming_follow_ups.length} action={data.overdue_follow_ups > 0 ? <Badge tone="red">{data.overdue_follow_ups} overdue</Badge> : undefined}>
          {data.upcoming_follow_ups.length === 0 ? (
            <Empty>Nothing planned. Add follow-ups on an enquiry.</Empty>
          ) : (
            <ShowMore
              items={data.upcoming_follow_ups}
              limit={4}
              noun="follow-ups"
              render={(f) => (
                <li key={f.id} className="text-sm">
                  <div className="flex justify-between gap-2">
                    <Link to={`/enquiries?q=${encodeURIComponent(f.couple_name)}`} className="font-medium text-slate-900 hover:text-brand-700">{f.couple_name}</Link>
                    <span className={f.overdue ? 'num shrink-0 text-xs font-medium text-red-600' : 'num shrink-0 text-xs text-slate-500'}>{formatDateTime(f.due_at)}</span>
                  </div>
                  <div className="text-xs text-slate-500">{f.summary}</div>
                </li>
              )}
            />
          )}
        </Panel>

        <Panel title="Vendor payments this week" count={data.upcoming_vendor_payments.length} to="/payments">
          {data.upcoming_vendor_payments.length === 0 ? (
            <Empty>Nothing due in the next 7 days.</Empty>
          ) : (
            <ShowMore
              items={data.upcoming_vendor_payments}
              limit={4}
              to="/payments"
              noun="payments"
              render={(p) => (
                <li key={p.expense_id} className="flex items-start justify-between gap-3 text-sm">
                  <span className="min-w-0">
                    <span className="block truncate font-medium text-slate-900">{p.vendor_name || p.description}</span>
                    <span className="block truncate text-xs text-slate-500">{p.wedding_title} · {formatDate(p.due_date)}</span>
                  </span>
                  <span className="shrink-0 text-right">
                    <span className="num block font-medium text-slate-900">{formatINR(p.outstanding_paise)}</span>
                    {p.overdue && <Badge tone="red">Overdue</Badge>}
                  </span>
                </li>
              )}
            />
          )}
        </Panel>

        <Panel title="Open incidents" count={data.open_incidents} to="/incidents">
          {data.recent_incidents.length === 0 ? (
            <Empty>All clear. Nothing is open.</Empty>
          ) : (
            <ShowMore
              items={data.recent_incidents}
              limit={3}
              to="/incidents"
              noun="incidents"
              render={(i) => (
                <li key={i.id} className="text-sm">
                  <div className="flex items-center justify-between gap-2">
                    <span className="truncate font-medium text-slate-900">{i.title}</span>
                    <Badge tone={i.severity === 'CRITICAL' ? 'red' : i.severity === 'HIGH' ? 'amber' : 'gray'}>{i.severity.toLowerCase()}</Badge>
                  </div>
                  <div className="text-xs text-slate-500">{i.wedding_title} · {i.assigned_to_name ? `with ${i.assigned_to_name}` : 'not assigned yet'}</div>
                </li>
              )}
            />
          )}
        </Panel>

        <Panel title="Upcoming consultations" count={data.upcoming_consultations.length} to="/enquiries">
          {data.upcoming_consultations.length === 0 ? (
            <Empty>None booked.</Empty>
          ) : (
            <ShowMore
              items={data.upcoming_consultations}
              limit={4}
              noun="consultations"
              render={(c) => (
                <li key={c.id} className="flex justify-between gap-2 text-sm">
                  <span className="font-medium text-slate-900">{c.couple_name}</span>
                  <span className="num text-xs text-slate-500">{formatDateTime(c.consultation_at)}</span>
                </li>
              )}
            />
          )}
        </Panel>

        <Panel title="Where enquiries come from">
          {sourceData.length === 0 ? (
            <Empty>No enquiries yet.</Empty>
          ) : (
            <>
              <ul className="space-y-2.5">
                {[...sourceData].sort((a, b) => b.count - a.count).map((s) => {
                  const max = Math.max(...sourceData.map((x) => x.count))
                  return (
                    <li key={s.name} className="text-sm">
                      <div className="flex justify-between"><span className="text-slate-700">{s.name}</span><span className="num text-slate-500">{s.count}</span></div>
                      <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-slate-100"><div className="h-full rounded-full bg-slate-400" style={{ width: `${(s.count / max) * 100}%` }} /></div>
                    </li>
                  )
                })}
              </ul>
              <p className="mt-4 text-xs text-slate-500">{data.conversion_rate}% of enquiries became clients</p>
            </>
          )}
        </Panel>
      </div>
    </div>
  )
}
