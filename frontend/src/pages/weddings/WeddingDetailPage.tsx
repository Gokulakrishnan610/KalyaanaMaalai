import { useQuery } from '@tanstack/react-query'
import { Link, useParams, useSearchParams } from 'react-router-dom'
import { get } from '@/api/client'
import { Badge, cn, ErrorState, Spinner } from '@/components/common'
import { formatDate } from '@/helpers/date'
import { IncidentsList } from '@/pages/incidents/IncidentsList'
import { EventDayTab } from './EventDayTab'
import { FunctionsTab } from './FunctionsTab'
import { GuardedFinanceTab, GuardedVendorsTab } from './Guarded'
import { OverviewTab } from './OverviewTab'
import { ScheduleTab } from './ScheduleTab'
import { TasksTab } from './TasksTab'
import { WEDDING_STATUSES, type WeddingDetail } from './types'

const TABS = [
  { id: 'overview', label: 'Overview' },
  { id: 'functions', label: 'Functions' },
  { id: 'tasks', label: 'Tasks' },
  { id: 'schedule', label: 'Schedule' },
  { id: 'vendors', label: 'Vendors' },
  { id: 'finance', label: 'Finance' },
  { id: 'eventday', label: 'Event Day' },
  { id: 'incidents', label: 'Incidents' },
]

export default function WeddingDetailPage() {
  const { id } = useParams()
  const weddingId = Number(id)
  const [params, setParams] = useSearchParams()
  // the tab lives in the address (?tab=tasks), so a refresh or a shared link opens the same tab
  const tab = TABS.some((t) => t.id === params.get('tab')) ? params.get('tab')! : 'overview'

  const { data: wedding, isLoading, error, refetch } = useQuery({
    queryKey: ['wedding', weddingId],
    queryFn: () => get<WeddingDetail>(`/weddings/${weddingId}/`),
    enabled: Number.isFinite(weddingId),
  })

  if (isLoading) return <Spinner />
  if (error || !wedding) return <ErrorState message={error?.message ?? 'Wedding not found.'} onRetry={refetch} />

  const status = WEDDING_STATUSES.find((s) => s.value === wedding.status)

  return (
    <div>
      <Link to="/weddings" className="text-sm text-slate-500 hover:underline">
        ← All weddings
      </Link>
      <div className="mb-4 mt-1 flex flex-wrap items-center gap-3">
        <h1 className="text-2xl font-semibold">{wedding.title}</h1>
        <Badge tone={status?.tone}>{status?.label ?? wedding.status}</Badge>
        <span className="text-sm text-slate-500">
          {formatDate(wedding.start_date)} · {wedding.city}
        </span>
      </div>

      <div className="mb-5 flex gap-1 overflow-x-auto border-b border-slate-200 print:hidden" role="tablist">
        {TABS.map((t) => (
          <button
            key={t.id}
            role="tab"
            aria-selected={tab === t.id}
            onClick={() => setParams({ tab: t.id }, { replace: true })}
            className={cn(
              '-mb-px whitespace-nowrap border-b-2 px-4 py-2 text-sm font-medium',
              tab === t.id ? 'border-brand-500 text-brand-700' : 'border-transparent text-slate-500 hover:text-slate-800',
            )}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === 'overview' && <OverviewTab wedding={wedding} />}
      {tab === 'functions' && <FunctionsTab wedding={wedding} />}
      {tab === 'tasks' && <TasksTab wedding={wedding} />}
      {tab === 'schedule' && <ScheduleTab wedding={wedding} />}
      {tab === 'vendors' && <GuardedVendorsTab weddingId={wedding.id} />}
      {tab === 'finance' && <GuardedFinanceTab weddingId={wedding.id} />}
      {tab === 'eventday' && <EventDayTab wedding={wedding} />}
      {tab === 'incidents' && <IncidentsList weddingId={wedding.id} />}
    </div>
  )
}
