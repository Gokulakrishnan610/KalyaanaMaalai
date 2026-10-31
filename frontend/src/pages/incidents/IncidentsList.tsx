import { useQuery } from '@tanstack/react-query'
import { Plus } from 'lucide-react'
import { useState } from 'react'
import { get, type Page } from '@/api/client'
import { Badge, Button, cn, EmptyState, ErrorState, Spinner, Table, Td, Th } from '@/components/common'
import { timeAgo } from '@/helpers/date'
import { IncidentDetail } from './IncidentDetail'
import { ReportIncidentForm } from './ReportIncidentForm'
import { severityInfo, statusInfo, type Incident } from './types'

type Tab = 'open' | 'resolved' | 'all'

/** Incidents for everyone, or for one wedding. Other people's changes appear here without a refresh. */
export function IncidentsList({ weddingId }: { weddingId?: number }) {
  const [tab, setTab] = useState<Tab>('open')
  const [reporting, setReporting] = useState(false)
  const [openId, setOpenId] = useState<number | null>(null)

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['incidents', 'list', weddingId ?? 'all'],
    queryFn: () => get<Page<Incident>>('/incidents/', { wedding: weddingId, page_size: 200 }),
  })

  const all = data?.results ?? []
  const shown = all.filter((i) => (tab === 'all' ? true : tab === 'open' ? i.is_open : !i.is_open))
  const count = (t: Tab) => all.filter((i) => (t === 'all' ? true : t === 'open' ? i.is_open : !i.is_open)).length

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div className="flex gap-1 border-b border-slate-200">
          {(['open', 'resolved', 'all'] as Tab[]).map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={cn(
                '-mb-px border-b-2 px-4 py-2 text-sm font-medium capitalize',
                tab === t ? 'border-brand-500 text-brand-600' : 'border-transparent text-slate-500 hover:text-slate-800',
              )}
            >
              {t} <span className="ml-1 text-xs text-slate-400">({count(t)})</span>
            </button>
          ))}
        </div>
        <Button onClick={() => setReporting(true)}>
          <Plus size={16} /> Report incident
        </Button>
      </div>

      {isLoading && <Spinner />}
      {error && <ErrorState message={error.message} onRetry={refetch} />}
      {data && shown.length === 0 && (
        <EmptyState title={tab === 'open' ? 'No open incidents' : 'Nothing here'} hint="When something goes wrong on the day, report it so the team sees it at once." />
      )}
      {shown.length > 0 && (
        <Table>
          <thead>
            <tr>
              <Th>Problem</Th>
              {!weddingId && <Th>Wedding</Th>}
              <Th>Severity</Th>
              <Th>Status</Th>
              <Th>Assigned to</Th>
              <Th>Reported</Th>
            </tr>
          </thead>
          <tbody>
            {shown.map((i) => (
              <tr key={i.id} className="cursor-pointer hover:bg-slate-50/70" onClick={() => setOpenId(i.id)}>
                <Td className="font-medium">{i.title}</Td>
                {!weddingId && <Td>{i.wedding_title}</Td>}
                <Td>
                  <Badge tone={severityInfo(i.severity).tone}>{severityInfo(i.severity).label}</Badge>
                </Td>
                <Td>
                  <Badge tone={statusInfo(i.status).tone}>{statusInfo(i.status).label}</Badge>
                </Td>
                <Td>{i.assigned_to_name || <span className="text-slate-400">-</span>}</Td>
                <Td className="text-slate-500">{timeAgo(i.created_at)}</Td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}

      {reporting && <ReportIncidentForm weddingId={weddingId} onClose={() => setReporting(false)} />}
      {openId && <IncidentDetail id={openId} onClose={() => setOpenId(null)} />}
    </div>
  )
}
