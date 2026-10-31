import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { get, patch, type Page } from '@/api/client'
import { Button, EmptyState, ErrorState, SearchBox, Select, Spinner, StatusSelect, Table, Td, Th } from '@/components/common'
import { useDebouncedValue } from '@/hooks/useDebouncedValue'
import { formatDate } from '@/helpers/date'
import { useLogin } from '@/login/LoginContext'
import { NewWeddingForm } from './NewWeddingForm'
import { WEDDING_STATUSES, type Wedding, type WeddingStatus } from './types'

const PAGE_SIZE = 20

export function ProgressBar({ pct }: { pct: number }) {
  return (
    <div className="flex items-center gap-2" title={`${pct}% of tasks done`}>
      <div className="h-2 w-24 overflow-hidden rounded-full bg-slate-200">
        <div className="h-full rounded-full bg-brand-500" style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs text-slate-500">{pct}%</span>
    </div>
  )
}

export default function WeddingsPage() {
  const { hasRole } = useLogin()
  const [params, setParams] = useSearchParams()
  const [status, setStatus] = useState('')
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const deferred = useDebouncedValue(search.trim())
  const queryClient = useQueryClient()

  // an enquiry or client page can link here as /weddings?clientId=3&guests=300&date=2027-02-10&budget=4500000
  const prefill = {
    clientId: params.get('clientId') ?? undefined,
    guests: params.get('guests') ?? undefined,
    date: params.get('date') ?? undefined,
    budget: params.get('budget') ?? undefined,
  }
  const hasPrefill = Object.values(prefill).some(Boolean)
  const [showForm, setShowForm] = useState(hasPrefill)

  const queryKey = ['weddings', status, deferred, page]
  const { data, isLoading, error, refetch, isFetching } = useQuery({
    queryKey,
    queryFn: ({ signal }) =>
      get<Page<Wedding>>('/weddings/', { status: status || undefined, q: deferred || undefined, page, limit: PAGE_SIZE }, signal),
    placeholderData: keepPreviousData,
  })

  // changing a status in the table shows at once, and goes back if the server says no
  const changeStatus = useMutation({
    mutationFn: ({ id, status }: { id: number; status: WeddingStatus }) => patch(`/weddings/${id}/`, { status }),
    onMutate: async ({ id, status }) => {
      await queryClient.cancelQueries({ queryKey: ['weddings'] })
      const before = queryClient.getQueryData<Page<Wedding>>(queryKey)
      if (before) {
        queryClient.setQueryData<Page<Wedding>>(queryKey, {
          ...before,
          results: before.results.map((w) => (w.id === id ? { ...w, status } : w)),
        })
      }
      return { before }
    },
    onError: (_e, _vars, context) => context?.before && queryClient.setQueryData(queryKey, context.before),
    onSettled: () => queryClient.invalidateQueries({ queryKey: ['weddings'] }),
  })
  const weddings = data?.results ?? []
  const pages = Math.max(1, Math.ceil((data?.count ?? 0) / PAGE_SIZE))

  const closeForm = () => {
    setShowForm(false)
    if (hasPrefill) setParams({}, { replace: true })
  }

  return (
    <div>
      <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold">Weddings</h1>
          <p className="text-sm text-slate-500">Every wedding we are planning, with how far along it is.</p>
        </div>
        {hasRole('PLANNER') && <Button onClick={() => setShowForm(true)}>New wedding</Button>}
      </div>

      <div className="mb-4 flex flex-wrap gap-3">
        <SearchBox
          label="Search weddings"
          placeholder="Search title, couple or city"
          value={search}
          onChange={(value) => {
            setSearch(value)
            setPage(1)
          }}
          busy={search.trim() !== deferred || isFetching}
        />
        <Select
          aria-label="Filter by status"
          value={status}
          onChange={(e) => {
            setStatus(e.target.value)
            setPage(1)
          }}
        >
          <option value="">All statuses</option>
          {WEDDING_STATUSES.map((s) => (
            <option key={s.value} value={s.value}>
              {s.label}
            </option>
          ))}
        </Select>
      </div>

      {isLoading && <Spinner />}
      {error && <ErrorState message={error.message} onRetry={refetch} />}
      {data && weddings.length === 0 && (
        <EmptyState title="No weddings found" hint="Start one with “New wedding”, or convert an enquiry." />
      )}
      {weddings.length > 0 && (
        <Table>
          <thead>
            <tr>
              <Th>Wedding</Th>
              <Th>Client</Th>
              <Th>Status</Th>
              <Th>Dates</Th>
              <Th>Guests</Th>
              <Th>Progress</Th>
              <Th>Next function</Th>
            </tr>
          </thead>
          <tbody>
            {weddings.map((w) => {
              return (
                <tr key={w.id} className="hover:bg-slate-50">
                  <Td>
                    <Link to={`/weddings/${w.id}`} className="font-medium text-brand-700 hover:underline">
                      {w.title}
                    </Link>
                    <div className="text-xs text-slate-500">{w.city}</div>
                  </Td>
                  <Td>{w.client_name}</Td>
                  <Td>
                    <StatusSelect
                      label={`Status of ${w.title}`}
                      value={w.status}
                      options={WEDDING_STATUSES}
                      readOnly={!hasRole('PLANNER')}
                      onChange={(next) => changeStatus.mutate({ id: w.id, status: next })}
                    />
                  </Td>
                  <Td>
                    {formatDate(w.start_date)}
                    {w.end_date !== w.start_date && <> – {formatDate(w.end_date)}</>}
                  </Td>
                  <Td>{w.guest_count}</Td>
                  <Td>
                    <ProgressBar pct={w.progress_pct} />
                  </Td>
                  <Td>{formatDate(w.next_function_date)}</Td>
                </tr>
              )
            })}
          </tbody>
        </Table>
      )}

      {pages > 1 && (
        <div className="mt-4 flex items-center justify-end gap-3 text-sm">
          <Button variant="secondary" disabled={page <= 1} onClick={() => setPage(page - 1)}>
            Previous
          </Button>
          <span>
            Page {page} of {pages}
          </span>
          <Button variant="secondary" disabled={page >= pages} onClick={() => setPage(page + 1)}>
            Next
          </Button>
        </div>
      )}

      {showForm && <NewWeddingForm prefill={prefill} onClose={closeForm} />}
    </div>
  )
}
