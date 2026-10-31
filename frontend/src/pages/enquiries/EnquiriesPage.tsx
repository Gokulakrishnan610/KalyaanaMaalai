import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { MoreVertical, Plus } from 'lucide-react'
import { useDeferredValue, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Badge, Button, cn, EmptyState, ErrorState, Select, Spinner, Table, Td, Th } from '@/components/common'
import { get, patch, type Page } from '@/api/client'
import { formatDate } from '@/helpers/date'
import { formatINR } from '@/helpers/money'
import { useLogin } from '@/login/LoginContext'
import { EnquiryBoard } from './EnquiryBoard'
import { EnquiryForm } from './EnquiryForm'
import { SOURCES, sourceInfo, STATUSES, statusInfo, type Enquiry, type Status } from './types'

type View = 'table' | 'board'
type Tab = Status | 'ALL'

function Avatar({ name }: { name: string | null }) {
  if (!name) return <span className="text-slate-400">-</span>
  const letters = name.split(' ').map((p) => p[0]).slice(0, 2).join('').toUpperCase()
  return (
    <span className="inline-flex items-center gap-2">
      <span className="flex h-7 w-7 items-center justify-center rounded-full bg-brand-100 text-[11px] font-semibold text-brand-700">{letters}</span>
      <span className="hidden text-sm xl:inline">{name.split(' ')[0]}</span>
    </span>
  )
}

export default function EnquiriesPage() {
  const queryClient = useQueryClient()
  const { hasRole } = useLogin()
  const canEdit = hasRole('PLANNER')
  const [params] = useSearchParams()

  const [view, setView] = useState<View>('table')
  const [tab, setTab] = useState<Tab>('ALL')
  const [source, setSource] = useState('')
  const [search, setSearch] = useState(params.get('q') ?? '') // the top-bar search arrives as ?q=
  const deferredSearch = useDeferredValue(search)
  // null = nothing open, 'new' = the add form, or the enquiry being viewed/edited
  const [open, setOpen] = useState<Enquiry | 'new' | null>(null)

  const queryKey = ['enquiries', source, deferredSearch]
  const { data, isLoading, error, refetch } = useQuery({
    queryKey,
    queryFn: () =>
      get<Page<Enquiry>>('/enquiries/', { page_size: 200, source: source || undefined, q: deferredSearch || undefined }),
  })

  // moving a card on the board updates the screen at once, and goes back if the server says no
  const move = useMutation({
    mutationFn: ({ enquiry, status }: { enquiry: Enquiry; status: Status }) =>
      patch<Enquiry>(`/enquiries/${enquiry.id}/`, { status }),
    onMutate: async ({ enquiry, status }) => {
      await queryClient.cancelQueries({ queryKey })
      const before = queryClient.getQueryData<Page<Enquiry>>(queryKey)
      if (before) {
        queryClient.setQueryData<Page<Enquiry>>(queryKey, {
          ...before,
          results: before.results.map((e) => (e.id === enquiry.id ? { ...e, status } : e)),
        })
      }
      return { before }
    },
    onError: (_e, _vars, context) => context?.before && queryClient.setQueryData(queryKey, context.before),
    onSettled: () => queryClient.invalidateQueries({ queryKey: ['enquiries'] }),
  })

  const all = data?.results ?? []
  const shown = view === 'table' && tab !== 'ALL' ? all.filter((e) => e.status === tab) : all
  const countFor = (status: Tab) => (status === 'ALL' ? all.length : all.filter((e) => e.status === status).length)

  return (
    <div>
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold">Enquiries</h1>
          <p className="text-sm text-slate-500">Manage and track all client enquiries, from first call to booking.</p>
        </div>
        {canEdit && (
          <Button onClick={() => setOpen('new')}>
            <Plus size={16} /> New enquiry
          </Button>
        )}
      </div>

      {view === 'table' && (
        <div className="mb-4 flex flex-wrap gap-1 border-b border-slate-200">
          {([{ value: 'ALL', label: 'All' }, ...STATUSES] as { value: Tab; label: string }[]).map((t) => (
            <button
              key={t.value}
              onClick={() => setTab(t.value)}
              className={cn(
                '-mb-px border-b-2 px-4 py-2 text-sm font-medium',
                tab === t.value ? 'border-brand-500 text-brand-600' : 'border-transparent text-slate-500 hover:text-slate-800',
              )}
            >
              {t.label} <span className="ml-1 text-xs text-slate-400">({countFor(t.value)})</span>
            </button>
          ))}
        </div>
      )}

      <div className="mb-4 flex flex-wrap items-center gap-3">
        <input
          aria-label="Search enquiries"
          placeholder="Search name or phone"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-64 rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
        />
        <div className="w-44">
          <Select aria-label="Filter by source" value={source} onChange={(e) => setSource(e.target.value)}>
            <option value="">All sources</option>
            {SOURCES.map((s) => (
              <option key={s.value} value={s.value}>
                {s.icon} {s.label}
              </option>
            ))}
          </Select>
        </div>
        <div className="ml-auto flex rounded-xl border border-slate-200 bg-white p-0.5 text-sm">
          {(['table', 'board'] as View[]).map((v) => (
            <button
              key={v}
              onClick={() => setView(v)}
              className={cn('rounded-lg px-3 py-1.5 capitalize', view === v ? 'bg-brand-500 text-white' : 'text-slate-600')}
            >
              {v}
            </button>
          ))}
        </div>
      </div>

      {isLoading && <Spinner />}
      {error && <ErrorState message={error.message} onRetry={refetch} />}
      {data && shown.length === 0 && (
        <EmptyState
          title="No enquiries found"
          hint={source || search || tab !== 'ALL' ? 'Try clearing the filters.' : 'Add the first one when a couple gets in touch.'}
          action={canEdit && !source && !search && tab === 'ALL' ? <Button onClick={() => setOpen('new')}>+ New enquiry</Button> : undefined}
        />
      )}

      {data && shown.length > 0 && view === 'board' && (
        <EnquiryBoard
          enquiries={shown}
          canEdit={canEdit}
          onOpen={setOpen}
          onMove={(enquiry, status) => move.mutate({ enquiry, status })}
        />
      )}

      {data && shown.length > 0 && view === 'table' && (
        <Table>
          <thead>
            <tr>
              <Th>Couple</Th>
              <Th>Wedding date</Th>
              <Th>City</Th>
              <Th>Guests</Th>
              <Th>Budget</Th>
              <Th>Source</Th>
              <Th>Status</Th>
              <Th>Assigned to</Th>
              <Th className="w-10" />
            </tr>
          </thead>
          <tbody>
            {shown.map((e) => (
              <tr key={e.id} className="cursor-pointer hover:bg-slate-50/70" onClick={() => setOpen(e)}>
                <Td>
                  <div className="font-medium">{e.couple_name}</div>
                  <div className="text-xs text-slate-500">{e.phone}</div>
                </Td>
                <Td>{formatDate(e.wedding_date)}</Td>
                <Td>{e.venue_city || '-'}</Td>
                <Td>{e.guest_count ?? '-'}</Td>
                <Td>{e.budget_paise ? formatINR(e.budget_paise) : '-'}</Td>
                <Td>
                  {sourceInfo(e.source).icon} {sourceInfo(e.source).label}
                </Td>
                <Td>
                  <Badge tone={statusInfo(e.status).tone}>{statusInfo(e.status).label}</Badge>
                </Td>
                <Td>
                  <Avatar name={e.owner_name} />
                </Td>
                <Td>
                  <MoreVertical size={16} className="text-slate-400" />
                </Td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}

      {open && <EnquiryForm key={open === 'new' ? 'new' : open.id} enquiry={open === 'new' ? null : open} onClose={() => setOpen(null)} />}
    </div>
  )
}
