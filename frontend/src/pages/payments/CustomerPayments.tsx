import { useMutation, useQuery } from '@tanstack/react-query'
import { Link2, Trash2 } from 'lucide-react'
import { useState } from 'react'
import { get, remove } from '@/api/client'
import { Badge, Button, EmptyState, ErrorState, Select, Spinner, Table, Td, Th } from '@/components/common'
import { formatDate } from '@/helpers/date'
import { formatINR } from '@/helpers/money'
import { useLogin } from '@/login/LoginContext'
import { useRefreshMoney } from './finance'
import { NewInvoiceModal } from './NewInvoiceModal'
import { PaymentLinkModal } from './PaymentLinkModal'
import { RecordPaymentModal } from './RecordPaymentModal'
import { StatusBadge } from './shared'
import type { InvoiceRow, OverviewRow } from './types'

const FILTERS = [
  { value: 'open', label: 'Still to collect' },
  { value: 'overdue', label: 'Overdue' },
  { value: 'paid', label: 'Paid' },
  { value: '', label: 'All invoices' },
]

/** Money coming in: every invoice, with the two ways to collect it: send a payment link, or record an offline payment. */
export function CustomerPayments({ weddingId, weddings, adding, onCloseAdd }: { weddingId: number | null; weddings: OverviewRow[]; adding: boolean; onCloseAdd: () => void }) {
  const canEdit = useLogin().hasRole('PLANNER')
  const refresh = useRefreshMoney()
  const [filter, setFilter] = useState('open')
  const [linkFor, setLinkFor] = useState<InvoiceRow | null>(null)
  const [recordFor, setRecordFor] = useState<InvoiceRow | null>(null)

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['finance', 'invoices', weddingId ?? 'all', filter],
    queryFn: () => get<InvoiceRow[]>('/invoices/', { wedding: weddingId ?? undefined, status: filter || undefined }),
  })
  const everything = useQuery({
    queryKey: ['finance', 'invoices', weddingId ?? 'all', ''],
    queryFn: () => get<InvoiceRow[]>('/invoices/', { wedding: weddingId ?? undefined }),
    enabled: adding,
  })
  const del = useMutation({ mutationFn: (id: number) => remove(`/invoices/${id}/`), onSuccess: () => refresh() })

  return (
    <section className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="max-w-2xl text-sm text-slate-500">
          Collect from customers two ways: <b>send a payment link</b> (they pay online and it is recorded by itself) or <b>record a payment</b> you received in cash, UPI, bank transfer or cheque.
        </p>
        <div className="w-48">
          <Select aria-label="Show invoices" value={filter} onChange={(e) => setFilter(e.target.value)}>
            {FILTERS.map((f) => (
              <option key={f.value} value={f.value}>
                {f.label}
              </option>
            ))}
          </Select>
        </div>
      </div>

      {isLoading ? (
        <Spinner />
      ) : error || !data ? (
        <ErrorState message={error?.message ?? 'Could not load invoices'} onRetry={refetch} />
      ) : data.length === 0 ? (
        <EmptyState
          title={filter === 'open' ? 'Nothing to collect' : 'No invoices here'}
          hint={filter === 'open' ? 'Every invoice is paid. Use “New invoice” to ask a customer for money.' : 'Try another filter.'}
        />
      ) : (
        <Table>
          <thead>
            <tr>
              <Th>Customer</Th>
              <Th>For</Th>
              <Th>Due</Th>
              <Th className="text-right">Amount</Th>
              <Th className="text-right">To collect</Th>
              <Th>Status</Th>
              {canEdit && <Th className="text-right">Collect</Th>}
            </tr>
          </thead>
          <tbody>
            {data.map((invoice) => (
              <tr key={invoice.id}>
                <Td>
                  <div className="font-medium">{invoice.client_name}</div>
                  {weddingId === null && <div className="text-xs text-slate-500">{invoice.wedding_title}</div>}
                </Td>
                <Td>
                  <div>{invoice.type_label}</div>
                  {invoice.note && <div className="max-w-[14rem] truncate text-xs text-slate-500">{invoice.note}</div>}
                </Td>
                <Td className={invoice.overdue ? 'font-medium text-red-600' : ''}>{formatDate(invoice.due_date)}</Td>
                <Td className="text-right tabular-nums">
                  {formatINR(invoice.amount_paise)}
                  {invoice.paid_paise > 0 && <div className="text-xs text-emerald-600">{formatINR(invoice.paid_paise)} paid</div>}
                </Td>
                <Td className="text-right font-medium tabular-nums">{formatINR(invoice.remaining_paise)}</Td>
                <Td>
                  <StatusBadge status={invoice.status} overdue={invoice.overdue} />
                  {invoice.link?.status === 'ACTIVE' && (
                    <div className="mt-1">
                      <Badge tone="blue">Link sent</Badge>
                    </div>
                  )}
                </Td>
                {canEdit && (
                  <Td className="whitespace-nowrap text-right">
                    {invoice.remaining_paise > 0 ? (
                      <>
                        <Button onClick={() => setLinkFor(invoice)}>
                          <Link2 size={14} /> Payment link
                        </Button>{' '}
                        <Button variant="secondary" onClick={() => setRecordFor(invoice)}>
                          Record payment
                        </Button>
                      </>
                    ) : (
                      <span className="text-xs text-slate-400">Fully paid</span>
                    )}
                    {/* a fixed-width slot, so the buttons line up whether or not the delete icon is there */}
                    <span className="ml-1 inline-block w-9 align-middle">
                      {invoice.paid_paise === 0 && (
                        <Button
                          variant="ghost"
                          aria-label={`Delete ${invoice.type_label} for ${invoice.client_name}`}
                          title="Delete this invoice"
                          onClick={() => window.confirm('Delete this invoice? Only do this if it was made by mistake.') && del.mutate(invoice.id)}
                        >
                          <Trash2 size={14} />
                        </Button>
                      )}
                    </span>
                  </Td>
                )}
              </tr>
            ))}
          </tbody>
        </Table>
      )}
      {del.error && <p className="text-sm text-red-600">{del.error.message}</p>}

      {linkFor && <PaymentLinkModal invoice={linkFor} onClose={() => setLinkFor(null)} />}
      {recordFor && (
        <RecordPaymentModal
          title={`Record payment · ${recordFor.type_label}`}
          subtitle={`${recordFor.client_name} · ${recordFor.wedding_title}`}
          remaining={recordFor.remaining_paise}
          url={`/invoices/${recordFor.id}/payments/`}
          amountLabel="Amount received"
          onClose={() => setRecordFor(null)}
        />
      )}
      {adding && <NewInvoiceModal weddingId={weddingId} weddings={weddings} existing={everything.data ?? data ?? []} onClose={onCloseAdd} />}
    </section>
  )
}
