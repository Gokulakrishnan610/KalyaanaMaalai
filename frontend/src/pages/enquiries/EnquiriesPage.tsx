import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { MoreVertical, Plus } from 'lucide-react'
import { useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Button, cn, EmptyState, ErrorState, Pager, SearchBox, Select, Spinner, StatusSelect, Table, Td, Th } from '@/components/common'
import { useDebouncedValue } from '@/hooks/useDebouncedValue'
import { get, patch, type Page } from '@/api/client'
import { formatDate, formatDateTime } from '@/helpers/date'
import { formatINR } from '@/helpers/money'
import { useLogin } from '@/login/LoginContext'
import { EnquiryBoard } from './EnquiryBoard'
import { EnquiryForm } from './EnquiryForm'
import { StarRating } from './StarRating'
import { SOURCES, sourceInfo, STATUSES, type Enquiry, type Status } from './types'

const PAGE_SIZE = 20 // the table shows 20 at a time; the board needs every card, so it loads up to 200

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
  const deferredSearch = useDebouncedValue(search.trim())
  const [page, setPage] = useState(1)
  const goBackToFirstPage = <T,>(setter: (value: T) => void) => (value: T) => {
    setter(value)
    setPage(1)
  }
  // null = nothing open, 'new' = the add form, or the enquiry being viewed/edited
  const [open, setOpen] = useState<Enquiry | 'new' | null>(null)

  const onTable = view === 'table'
  const queryKey = ['enquiries', { onTable, tab, source, q: deferredSearch, page }]
  const { data, isLoading, error, refetch, isFetching } = useQuery({
    queryKey,
    queryFn: ({ signal }) =>
      get<Page<Enquiry>>(
        '/enquiries/',
        onTable
          ? { page, page_size: PAGE_SIZE, status: tab === 'ALL' ? undefined : tab, source: source || undefined, q: deferredSearch || undefined }
          : { page_size: 200, source: source || undefined, q: deferredSearch || undefined },
        signal,
      ),
    placeholderData: keepPreviousData,
  })
  // the numbers on the tabs come from the server, because the table only holds one page
  const counts = useQuery({
    queryKey: ['enquiries', 'counts', source, deferredSearch],
    queryFn: ({ signal }) => get<Record<string, number>>('/enquiries/counts/', { source: source || undefined, q: deferredSearch || undefined }, signal),
    placeholderData: keepPreviousData,
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

  const shown = data?.results ?? []
  const countFor = (status: Tab) => counts.data?.[status] ?? 0

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
              onClick={() => {
                setTab(t.value)
                setPage(1)
              }}
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
        <SearchBox
          label="Search enquiries"
          placeholder="Search name, email or phone"
          value={search}
          onChange={goBackToFirstPage(setSearch)}
          busy={search.trim() !== deferredSearch || isFetching}
          className="w-64"
        />
        <div className="w-44">
          <Select aria-label="Filter by source" value={source} onChange={(e) => goBackToFirstPage(setSource)(e.target.value)}>
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
          // losing an enquiry needs a reason, so open the form with the Lost stage chosen
          onMove={(enquiry, status) => (status === 'LOST' ? setOpen({ ...enquiry, status, win_chance: 0 }) : move.mutate({ enquiry, status }))}
        />
      )}

      {data && shown.length > 0 && view === 'table' && (
        <Table>
          <thead>
            <tr>
              <Th>Couple</Th>
              <Th>Wedding date</Th>
              <Th>Budget</Th>
              <Th>Win chance</Th>
              <Th>Next follow-up</Th>
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
                  <div className="flex items-center gap-2 text-xs text-slate-500">
                    {e.phone} <StarRating value={e.priority} />
                  </div>
                </Td>
                <Td>{formatDate(e.wedding_date)}</Td>
                <Td>{e.budget_paise ? formatINR(e.budget_paise) : '-'}</Td>
                <Td>
                  <div className="flex items-center gap-2">
                    <div className="h-1.5 w-16 overflow-hidden rounded-full bg-slate-100">
                      <div className="h-full rounded-full bg-brand-500" style={{ width: `${e.win_chance}%` }} />
                    </div>
                    <span className="text-xs text-slate-600">{e.win_chance}%</span>
                  </div>
                </Td>
                <Td>
                  {e.next_follow_up ? (
                    <span className={new Date(e.next_follow_up) < new Date() ? 'font-medium text-red-600' : ''}>
                      {formatDateTime(e.next_follow_up)}
                    </span>
                  ) : (
                    <span className="text-slate-400">-</span>
                  )}
                </Td>
                <Td>
                  {sourceInfo(e.source).icon} {sourceInfo(e.source).label}
                </Td>
                <Td>
                  <StatusSelect
                    label={`Status of ${e.couple_name}`}
                    value={e.status}
                    options={STATUSES}
                    readOnly={!canEdit}
                    // losing an enquiry needs a reason, so that one opens the form with the Lost stage chosen
                    onChange={(next) => (next === 'LOST' ? setOpen({ ...e, status: next, win_chance: 0 }) : move.mutate({ enquiry: e, status: next }))}
                  />
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
      {data && onTable && <Pager page={page} pageSize={PAGE_SIZE} total={data.count} onPage={setPage} noun="enquiries" />}

      {open && <EnquiryForm key={open === 'new' ? 'new' : open.id} enquiry={open === 'new' ? null : open} onClose={() => setOpen(null)} />}
    </div>
  )
}
