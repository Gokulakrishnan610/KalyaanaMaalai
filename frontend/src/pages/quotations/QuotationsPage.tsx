import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { Fragment, useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { get } from '@/api/client'
import { Badge, Button, EmptyState, ErrorState, SearchBox, Spinner, Table, Td, Th } from '@/components/common'
import { useDebouncedValue } from '@/hooks/useDebouncedValue'
import { formatDate } from '@/helpers/date'
import { NewRequestForm } from './NewRequestForm'
import type { QuotationRequest } from './types'

export default function QuotationsPage() {
  const navigate = useNavigate()
  const [creating, setCreating] = useState(false)
  const [expanded, setExpanded] = useState<number | null>(null)
  const [search, setSearch] = useState('')
  const debounced = useDebouncedValue(search.trim())
  const { data, isLoading, error, refetch, isFetching } = useQuery({
    queryKey: ['quotation-requests', 'all', debounced],
    queryFn: ({ signal }) => get<QuotationRequest[]>('/quotation-requests/', { q: debounced || undefined }, signal),
    placeholderData: keepPreviousData,
  })

  // one row per wedding, with that wedding's requirements (DJ, caterer, ...) inside it
  const weddings = useMemo(() => {
    const byWedding = new Map<number, { id: number; title: string; requests: QuotationRequest[] }>()
    for (const r of data ?? []) {
      const group = byWedding.get(r.wedding_id) ?? { id: r.wedding_id, title: r.wedding_title, requests: [] }
      group.requests.push(r)
      byWedding.set(r.wedding_id, group)
    }
    return [...byWedding.values()]
  }, [data])

  return (
    <div>
      <div className="mb-5 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold">Quotations</h1>
          <p className="text-sm text-slate-500">Ask vendors for prices, compare them side by side and pick the winner.</p>
        </div>
        <Button onClick={() => setCreating(true)}>+ New request</Button>
      </div>

      <SearchBox
        label="Search quotations"
        placeholder="Search wedding, couple or requirement"
        value={search}
        onChange={setSearch}
        busy={search.trim() !== debounced || isFetching}
        className="mb-4"
      />

      {isLoading && <Spinner />}
      {error && <ErrorState message={error.message} onRetry={refetch} />}
      {data && data.length === 0 && (
        <EmptyState
          title={debounced ? "No matching requests" : "No quotation requests yet"}
          hint="Start one for a caterer, decorator or any other vendor type."
          action={<Button onClick={() => setCreating(true)}>+ New request</Button>}
        />
      )}
      {data && data.length > 0 && (
        <Table>
          <thead>
            <tr>
              <Th>Wedding</Th>
              <Th>Requirements</Th>
              <Th>Still open</Th>
            </tr>
          </thead>
          <tbody>
            {weddings.map((w) => {
              const isOpen = expanded === w.id
              const openCount = w.requests.filter((r) => r.status === 'OPEN').length
              return (
                <Fragment key={w.id}>
                  <tr className="cursor-pointer hover:bg-slate-50" onClick={() => setExpanded(isOpen ? null : w.id)}>
                    <Td>
                      <button
                        type="button"
                        aria-expanded={isOpen}
                        className="flex items-center gap-2 font-medium text-brand-700"
                        onClick={(e) => {
                          e.stopPropagation()
                          setExpanded(isOpen ? null : w.id)
                        }}
                      >
                        <span aria-hidden="true" className={isOpen ? 'rotate-90 transition-transform' : 'transition-transform'}>
                          ▸
                        </span>
                        {w.title}
                      </button>
                    </Td>
                    <Td>{w.requests.length}</Td>
                    <Td>{openCount > 0 ? <Badge tone="amber">{openCount} open</Badge> : <Badge tone="green">All closed</Badge>}</Td>
                  </tr>
                  {isOpen && (
                    <tr>
                      <td colSpan={3} className="border-b border-slate-100 bg-slate-50 px-4 py-3">
                        <ul className="divide-y divide-slate-200 rounded-lg border border-slate-200 bg-white text-sm">
                          {w.requests.map((r) => (
                            <li key={r.id}>
                              <Link to={`/quotations/${r.id}`} className="flex flex-wrap items-center justify-between gap-3 px-4 py-3 hover:bg-slate-50">
                                <div>
                                  <div className="font-medium text-brand-700">{r.category_name}</div>
                                  <div className="text-xs text-slate-500">
                                    {r.guest_count ? `${r.guest_count} guests · ` : ''}quotes by {formatDate(r.due_date)}
                                  </div>
                                </div>
                                <div className="flex items-center gap-3">
                                  <span className="text-slate-600">
                                    {r.received_count} of {r.invited_count} received
                                  </span>
                                  <Badge tone={r.status === 'OPEN' ? 'amber' : 'green'}>{r.status === 'OPEN' ? 'Open' : 'Closed'}</Badge>
                                </div>
                              </Link>
                            </li>
                          ))}
                        </ul>
                      </td>
                    </tr>
                  )}
                </Fragment>
              )
            })}
          </tbody>
        </Table>
      )}

      {creating && <NewRequestForm onClose={() => setCreating(false)} onCreated={(r) => navigate(`/quotations/${r.id}`)} />}
    </div>
  )
}
