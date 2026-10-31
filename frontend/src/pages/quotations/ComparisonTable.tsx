import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Fragment, useState, type ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { get, post } from '@/api/client'
import { Badge, Button, Confetti, EmptyState, ErrorState, Input, Modal, Spinner, cn } from '@/components/common'
import { formatDate } from '@/helpers/date'
import { formatINR } from '@/helpers/money'
import { Stars } from '@/pages/vendors/Stars'
import type { ComparedQuotation, Comparison } from './types'

const LOWEST = 'bg-emerald-50 font-semibold text-emerald-800'
const stickyCell = 'sticky left-0 z-10 border-r border-slate-200 bg-white px-4 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-slate-500'
const cell = 'min-w-[13rem] border-b border-slate-100 px-4 py-2.5 align-top'

interface Props {
  requestId: number
}

function Row({ quotations, label, children }: { quotations: ComparedQuotation[]; label: ReactNode; children: (q: ComparedQuotation, index: number) => ReactNode }) {
  return (
    <tr>
      <th scope="row" className={stickyCell}>
        {label}
      </th>
      {quotations.map((q, i) => (
        <td key={q.id} className={cn(cell, q.status === 'REJECTED' && 'opacity-60')}>
          {children(q, i)}
        </td>
      ))}
    </tr>
  )
}

export function ComparisonTable({ requestId }: Props) {
  const [choosing, setChoosing] = useState<ComparedQuotation | null>(null)
  const [celebrate, setCelebrate] = useState(false)
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['comparison', requestId],
    queryFn: () => get<Comparison>(`/quotation-requests/${requestId}/compare/`),
  })

  if (isLoading) return <Spinner label="Comparing quotations…" />
  if (error || !data) return <ErrorState message={error?.message ?? 'Could not load the comparison'} onRetry={refetch} />
  if (data.quotations.length === 0) {
    return <EmptyState title="No quotations to compare yet" hint="Add the first vendor's quotation and it will show up here." />
  }

  const { quotations, item_rows: rows, weights } = data
  const several = quotations.length > 1
  const selected = quotations.find((q) => q.status === 'SELECTED')
  const weightsText = `${Math.round(weights.price * 100)}% price, ${Math.round(weights.rating * 100)}% rating, ${Math.round(weights.punctuality * 100)}% punctuality`

  return (
    <div>
      <p className="mb-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-slate-500">
        <span>
          <span className="mr-1 inline-block h-2.5 w-2.5 rounded-sm bg-emerald-200 align-middle" />
          Lowest price
        </span>
        <span title={`Best value = ${weightsText}, each scaled across the quotations shown`} tabIndex={0} className="cursor-help underline decoration-dotted">
          How is “Best value” worked out?
        </span>
      </p>

      <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white shadow-sm">
        <table className="min-w-max border-collapse text-sm">
          <thead>
            <tr>
              <th className={cn(stickyCell, 'border-b border-slate-200 bg-slate-50 py-3')}>Vendor</th>
              {quotations.map((q) => (
                <th key={q.id} scope="col" className={cn(cell, 'border-b border-slate-200 bg-slate-50 py-3 text-left font-normal')}>
                  <Link to={`/vendors/${q.vendor.id}`} className="text-base font-semibold text-brand-700 hover:underline">
                    {q.vendor.name}
                  </Link>
                  <div className="mt-1.5 flex flex-wrap gap-1">
                    {q.status === 'SELECTED' && <Badge tone="green">Selected ✓</Badge>}
                    {q.status === 'REJECTED' && <Badge tone="red">Not chosen</Badge>}
                    {several && q.flags.best_value && (
                      <span title={`Best value: ${weightsText}. Score ${((q.score ?? 0) * 100).toFixed(0)}/100.`} tabIndex={0}>
                        <span className="badge-shine inline-block rounded-full"><Badge tone="brand">★ Best value</Badge></span>
                      </span>
                    )}
                    {q.flags.expired && <Badge tone="amber">Quote expired</Badge>}
                    {!q.typed_by_hand && <Badge tone="blue">Read by AI</Badge>}
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            <Row quotations={quotations} label="Total">
              {(q) => (
                <span className={cn('inline-block rounded px-1.5 py-0.5 text-lg', q.flags.lowest_total ? `${LOWEST} pulse-glow` : 'font-semibold')}>
                  {formatINR(q.total_paise)}
                  {q.flags.lowest_total && <span className="ml-2 text-xs font-medium">Lowest</span>}
                </span>
              )}
            </Row>
            <Row quotations={quotations} label="Price per plate">
              {(q) =>
                q.price_per_plate_paise ? (
                  <span className={cn('inline-block rounded px-1.5 py-0.5', q.flags.lowest_per_plate && LOWEST)}>
                    {formatINR(q.price_per_plate_paise)}
                    {q.flags.lowest_per_plate && <span className="ml-2 text-xs">Lowest</span>}
                  </span>
                ) : (
                  <span className="text-slate-400">—</span>
                )
              }
            </Row>
            <Row quotations={quotations} label={`Implied total${data.request.guest_count ? ` (${data.request.guest_count} guests)` : ''}`}>
              {(q) =>
                q.implied_total_paise != null ? (
                  formatINR(q.implied_total_paise)
                ) : (
                  <span className="text-slate-400">—</span>
                )
              }
            </Row>

            {rows.length > 0 && (
              <>
                <tr>
                  <th scope="colgroup" colSpan={quotations.length + 1} className="border-b border-slate-200 bg-slate-50 px-4 py-1.5 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
                    Line items
                  </th>
                </tr>
                {rows.map((row) => {
                  const quoted = row.values.filter((v) => v !== null)
                  const lowest = quoted.length > 1 ? Math.min(...quoted.map((v) => v!.total_paise)) : null
                  return (
                    <Fragment key={row.key}>
                      <Row quotations={quotations} label={row.description}>
                        {(_q, i) => {
                          const value = row.values[i]
                          if (!value) return <span className="text-xs italic text-slate-400">Not quoted</span>
                          return (
                            <span className={cn('inline-block rounded px-1.5 py-0.5', value.total_paise === lowest && LOWEST)}>
                              {formatINR(value.total_paise)}
                              <span className="ml-1.5 text-xs font-normal text-slate-500">
                                {value.qty} × {formatINR(value.unit_price_paise)}
                              </span>
                            </span>
                          )
                        }}
                      </Row>
                    </Fragment>
                  )
                })}
              </>
            )}

            <Row quotations={quotations} label="Menu notes">{(q) => (q.menu_notes ? <span className="whitespace-pre-line text-slate-600">{q.menu_notes}</span> : <span className="text-slate-400">—</span>)}</Row>
            <Row quotations={quotations} label="Valid till">
              {(q) => (
                <span className={cn(q.flags.expired && 'font-medium text-red-600')}>
                  {q.valid_till ? formatDate(q.valid_till) : '—'}
                  {q.flags.expired && ' (expired)'}
                </span>
              )}
            </Row>
            <Row quotations={quotations} label="Rating">{(q) => <Stars value={q.vendor.avg_rating} />}</Row>
            <Row quotations={quotations} label="On-time record">
              {(q) =>
                q.vendor.punctuality_pct == null ? (
                  <span className="text-slate-400">No check-ins yet</span>
                ) : (
                  `${q.vendor.punctuality_pct}% on time`
                )
              }
            </Row>
            <Row quotations={quotations} label="Their quotation">
              {(q) =>
                q.file_url ? (
                  <a href={q.file_url} target="_blank" rel="noreferrer" className="text-brand-700 hover:underline">
                    View file
                  </a>
                ) : (
                  <span className="text-slate-400">No file</span>
                )
              }
            </Row>
            <Row quotations={quotations} label="">
              {(q) =>
                q.status === 'SELECTED' ? (
                  <span className="font-medium text-emerald-700">Chosen vendor</span>
                ) : (
                  <Button variant={selected ? 'secondary' : 'primary'} onClick={() => setChoosing(q)}>
                    {selected ? 'Switch to this vendor' : 'Select this vendor'}
                  </Button>
                )
              }
            </Row>
          </tbody>
        </table>
      </div>

      {choosing && (
        <SelectModal
          requestId={requestId}
          quotation={choosing}
          current={selected}
          onClose={() => setChoosing(null)}
          onSelected={() => {
            setCelebrate(true)
            window.setTimeout(() => setCelebrate(false), 4200)
          }}
        />
      )}
      {celebrate && <Confetti />}
    </div>
  )
}

function SelectModal({
  requestId,
  quotation,
  current,
  onClose,
  onSelected,
}: {
  requestId: number
  quotation: ComparedQuotation
  current?: ComparedQuotation
  onClose: () => void
  onSelected: () => void
}) {
  const queryClient = useQueryClient()
  const [advance, setAdvance] = useState('30')
  const percent = Number(advance)
  const valid = advance !== '' && Number.isInteger(percent) && percent >= 0 && percent <= 100
  const advanceAmount = valid ? Math.round((quotation.total_paise * percent) / 100) : 0

  const select = useMutation({
    mutationFn: () => post(`/quotations/${quotation.id}/select/`, { advance_pct: percent }),
    onSuccess: () => {
      for (const key of [['comparison', requestId], ['quotation-request', requestId], ['quotation-requests'], ['wedding-vendors'], ['vendors']]) {
        queryClient.invalidateQueries({ queryKey: key })
      }
      onSelected()
      onClose()
    },
  })

  return (
    <Modal open title={current ? `Switch to ${quotation.vendor.name}?` : `Select ${quotation.vendor.name}?`} onClose={onClose}>
      <div className="space-y-3 text-sm">
        <p>
          {quotation.vendor.name} will be booked for <strong>{formatINR(quotation.total_paise)}</strong>.
          {current
            ? ` ${current.vendor.name} will be replaced, and its planned payments removed.`
            : ' The other vendors on this request will be marked as not chosen and the request will close.'}
        </p>
        <Input
          label="Advance to pay (% of the total)"
          type="number"
          min={0}
          max={100}
          value={advance}
          onChange={(e) => setAdvance(e.target.value)}
          error={advance !== '' && !valid ? 'Enter a whole number from 0 to 100' : undefined}
        />
        {valid && (
          <p className="rounded-lg bg-slate-50 px-3 py-2 text-slate-600">
            Advance {formatINR(advanceAmount)} due in 7 days, final {formatINR(quotation.total_paise - advanceAmount)} due 3 days before the wedding.
          </p>
        )}
        {select.error && (
          <p role="alert" className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-red-700">
            {select.error.message}
          </p>
        )}
        <div className="flex justify-end gap-2 pt-1">
          <Button variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button disabled={!valid} loading={select.isPending} onClick={() => select.mutate()}>
            {current ? 'Yes, switch vendor' : 'Yes, select vendor'}
          </Button>
        </div>
      </div>
    </Modal>
  )
}
