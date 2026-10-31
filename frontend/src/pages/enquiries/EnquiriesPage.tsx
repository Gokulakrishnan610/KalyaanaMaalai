import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useDeferredValue, useState } from 'react'
import { Badge, Button, cn, EmptyState, ErrorState, Select, Spinner, Table, Td, Th } from '@/components/common'
import { get, patch, type Page } from '@/api/client'
import { formatDate } from '@/helpers/date'
import { formatINR } from '@/helpers/money'
import { useLogin } from '@/login/LoginContext'
import { EnquiryBoard } from './EnquiryBoard'
import { EnquiryForm } from './EnquiryForm'
import { SOURCES, sourceInfo, statusInfo, type Enquiry, type Status } from './types'

type View = 'board' | 'table'

export default function EnquiriesPage() {
  const queryClient = useQueryClient()
  const { hasRole } = useLogin()
  const canEdit = hasRole('PLANNER')

  const [view, setView] = useState<View>('board')
  const [source, setSource] = useState('')
  const [search, setSearch] = useState('')
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

  const enquiries = data?.results ?? []

  return (
    <div>
      <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold">Enquiries</h1>
          <p className="text-sm text-slate-500">Every couple who got in touch, from first call to booking.</p>
        </div>
        {canEdit && <Button onClick={() => setOpen('new')}>+ New enquiry</Button>}
      </div>

      <div className="mb-4 flex flex-wrap items-end gap-3">
        <input
          aria-label="Search enquiries"
          placeholder="Search name or phone"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-64 rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
        />
        <div className="w-48">
          <Select aria-label="Filter by source" value={source} onChange={(e) => setSource(e.target.value)}>
            <option value="">All sources</option>
            {SOURCES.map((s) => (
              <option key={s.value} value={s.value}>
                {s.icon} {s.label}
              </option>
            ))}
          </Select>
        </div>
        <div className="ml-auto flex rounded-lg border border-slate-300 bg-white p-0.5 text-sm">
          {(['board', 'table'] as View[]).map((v) => (
            <button
              key={v}
              onClick={() => setView(v)}
              className={cn('rounded-md px-3 py-1.5 capitalize', view === v ? 'bg-brand-600 text-white' : 'text-slate-600')}
            >
              {v}
            </button>
          ))}
        </div>
      </div>

      {isLoading && <Spinner />}
      {error && <ErrorState message={error.message} onRetry={refetch} />}
      {data && enquiries.length === 0 && (
        <EmptyState
          title="No enquiries found"
          hint={source || search ? 'Try clearing the filters.' : 'Add the first one when a couple gets in touch.'}
          action={canEdit && !source && !search ? <Button onClick={() => setOpen('new')}>+ New enquiry</Button> : undefined}
        />
      )}

      {data && enquiries.length > 0 && view === 'board' && (
        <EnquiryBoard
          enquiries={enquiries}
          canEdit={canEdit}
          onOpen={setOpen}
          onMove={(enquiry, status) => move.mutate({ enquiry, status })}
        />
      )}

      {data && enquiries.length > 0 && view === 'table' && (
        <Table>
          <thead>
            <tr>
              <Th>Couple</Th>
              <Th>Source</Th>
              <Th>Stage</Th>
              <Th>Wedding date</Th>
              <Th>Guests</Th>
              <Th>Budget</Th>
              <Th>Consultation</Th>
            </tr>
          </thead>
          <tbody>
            {enquiries.map((e) => (
              <tr key={e.id} className="cursor-pointer hover:bg-slate-50" onClick={() => setOpen(e)}>
                <Td className="font-medium">{e.couple_name}</Td>
                <Td>
                  {sourceInfo(e.source).icon} {sourceInfo(e.source).label}
                </Td>
                <Td>
                  <Badge tone={statusInfo(e.status).tone}>{statusInfo(e.status).label}</Badge>
                </Td>
                <Td>{formatDate(e.wedding_date)}</Td>
                <Td>{e.guest_count ?? '-'}</Td>
                <Td>{e.budget_paise ? formatINR(e.budget_paise) : '-'}</Td>
                <Td>{formatDate(e.consultation_at)}</Td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}

      {open && <EnquiryForm key={open === 'new' ? 'new' : open.id} enquiry={open === 'new' ? null : open} onClose={() => setOpen(null)} />}
    </div>
  )
}
