import { useMutation, useQuery } from '@tanstack/react-query'
import { ChevronDown, ChevronRight, Trash2 } from 'lucide-react'
import { Fragment, useState, type FormEvent } from 'react'
import { get, post, remove } from '@/api/client'
import { Button, EmptyState, ErrorState, Input, Modal, Select, Spinner, Table, Td, Th } from '@/components/common'
import { formatDate } from '@/helpers/date'
import { formatINR, rupeesToPaise } from '@/helpers/money'
import { useLogin } from '@/login/LoginContext'
import { useRefreshMoney } from './finance'
import { RecordPaymentModal } from './RecordPaymentModal'
import { StatusBadge } from './shared'
import type { Instalment, OverviewRow, VendorBill } from './types'

const FILTERS = [
  { value: 'open', label: 'Still to pay' },
  { value: 'overdue', label: 'Overdue' },
  { value: 'paid', label: 'Paid' },
  { value: 'all', label: 'All bills' },
]

type Target = { kind: 'bill'; bill: VendorBill } | { kind: 'instalment'; bill: VendorBill; part: Instalment }

/** Money going out: every vendor bill with its advance and final instalments. Vendors are paid offline, so you record what you paid. */
export function VendorPayments({ weddingId, weddings, adding, onCloseAdd }: { weddingId: number | null; weddings: OverviewRow[]; adding: boolean; onCloseAdd: () => void }) {
  const canEdit = useLogin().hasRole('PLANNER')
  const refresh = useRefreshMoney()
  const [filter, setFilter] = useState('open')
  const [open, setOpen] = useState<Set<number>>(new Set())
  const [target, setTarget] = useState<Target | null>(null)

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['finance', 'bills', weddingId ?? 'all'],
    queryFn: () => get<VendorBill[]>('/finance/vendor-bills/', { wedding: weddingId ?? undefined }),
  })
  const del = useMutation({ mutationFn: (id: number) => remove(`/expenses/${id}/`), onSuccess: () => refresh() })

  const shown = (data ?? []).filter((b) =>
    filter === 'open' ? b.status !== 'PAID' : filter === 'overdue' ? b.overdue : filter === 'paid' ? b.status === 'PAID' : true,
  )
  const toggle = (id: number) =>
    setOpen((current) => {
      const next = new Set(current)
      if (!next.delete(id)) next.add(id)
      return next
    })

  return (
    <section className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="max-w-2xl text-sm text-slate-500">
          What we owe vendors. Open a bill to see its advance and final instalments. When you pay a vendor, <b>record the payment</b> here so the balance stays right.
        </p>
        <div className="w-44">
          <Select aria-label="Show bills" value={filter} onChange={(e) => setFilter(e.target.value)}>
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
        <ErrorState message={error?.message ?? 'Could not load vendor bills'} onRetry={refetch} />
      ) : shown.length === 0 ? (
        <EmptyState title={filter === 'open' ? 'Nothing to pay' : 'No bills here'} hint="Bills appear when a vendor is chosen, or add one with “Vendor bill”." />
      ) : (
        <Table>
          <thead>
            <tr>
              <Th className="w-8" />
              <Th>Vendor</Th>
              <Th>Bill ref</Th>
              <Th>Due</Th>
              <Th className="text-right">Amount</Th>
              <Th className="text-right">To pay</Th>
              <Th>Status</Th>
              {canEdit && <Th className="text-right">Pay</Th>}
            </tr>
          </thead>
          <tbody>
            {shown.map((bill) => (
              <Fragment key={bill.id}>
                <tr>
                  <Td>
                    {bill.instalments.length > 0 && (
                      <button aria-label={open.has(bill.id) ? 'Hide instalments' : 'Show instalments'} onClick={() => toggle(bill.id)} className="text-slate-400 hover:text-slate-700">
                        {open.has(bill.id) ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
                      </button>
                    )}
                  </Td>
                  <Td>
                    <div className="font-medium">{bill.vendor_name || bill.description}</div>
                    <div className="text-xs text-slate-500">
                      {bill.category}
                      {weddingId === null && ` · ${bill.wedding_title}`}
                    </div>
                  </Td>
                  <Td>{bill.bill_ref || '-'}</Td>
                  <Td className={bill.overdue ? 'font-medium text-red-600' : ''}>{formatDate(bill.due_date)}</Td>
                  <Td className="text-right tabular-nums">{formatINR(bill.amount_paise)}</Td>
                  <Td className="text-right font-medium tabular-nums">{formatINR(bill.remaining_paise)}</Td>
                  <Td>
                    <StatusBadge status={bill.status} overdue={bill.overdue} />
                  </Td>
                  {canEdit && (
                    <Td className="whitespace-nowrap text-right">
                      {bill.remaining_paise > 0 && (
                        <Button variant="secondary" onClick={() => setTarget({ kind: 'bill', bill })}>
                          Record payment
                        </Button>
                      )}
                      <span className="ml-1 inline-block w-9 align-middle">
                        {bill.paid_paise === 0 && (
                          <Button
                            variant="ghost"
                            aria-label={`Delete bill ${bill.description}`}
                            title="Delete this bill"
                            onClick={() => window.confirm('Delete this bill? Only do this if it was added by mistake.') && del.mutate(bill.id)}
                          >
                            <Trash2 size={14} />
                          </Button>
                        )}
                      </span>
                    </Td>
                  )}
                </tr>
                {open.has(bill.id) &&
                  bill.instalments.map((part) => (
                    <tr key={part.id} className="bg-slate-50/60 text-slate-600">
                      <Td />
                      <Td className="pl-6">{part.part_label} payment</Td>
                      <Td />
                      <Td className={part.overdue ? 'font-medium text-red-600' : ''}>{formatDate(part.due_date)}</Td>
                      <Td className="text-right tabular-nums">{formatINR(part.amount_paise)}</Td>
                      <Td className="text-right tabular-nums">{formatINR(part.remaining_paise)}</Td>
                      <Td>
                        <StatusBadge status={part.status} overdue={part.overdue} />
                      </Td>
                      {canEdit && (
                        <Td className="text-right">
                          {part.remaining_paise > 0 && (
                            <Button variant="ghost" onClick={() => setTarget({ kind: 'instalment', bill, part })}>
                              Record payment
                            </Button>
                          )}
                        </Td>
                      )}
                    </tr>
                  ))}
              </Fragment>
            ))}
          </tbody>
        </Table>
      )}
      {del.error && <p className="text-sm text-red-600">{del.error.message}</p>}

      {target && (
        <RecordPaymentModal
          title={target.kind === 'bill' ? `Record payment · ${target.bill.vendor_name || target.bill.description}` : `Record ${target.part.part_label.toLowerCase()} payment · ${target.bill.vendor_name}`}
          subtitle={target.bill.wedding_title}
          remaining={target.kind === 'bill' ? target.bill.remaining_paise : target.part.remaining_paise}
          url={target.kind === 'bill' ? `/expenses/${target.bill.id}/payments/` : `/milestones/${target.part.id}/pay/`}
          amountLabel="Amount paid"
          defaultMethod="BANK"
          onClose={() => setTarget(null)}
        />
      )}
      {adding && <AddBillModal weddingId={weddingId} weddings={weddings} onClose={onCloseAdd} />}
    </section>
  )
}

function AddBillModal({ weddingId, weddings, onClose }: { weddingId: number | null; weddings: OverviewRow[]; onClose: () => void }) {
  const refresh = useRefreshMoney()
  const vendors = useQuery({ queryKey: ['vendors', 'options'], queryFn: () => get<{ results: { id: number; name: string; category_name?: string }[] }>('/vendors/', { page_size: 100 }) })
  const [form, setForm] = useState({ wedding: weddingId ? String(weddingId) : '', vendor_id: '', category: '', description: '', amount: '', bill_ref: '', due_date: '' })
  const [warnings, setWarnings] = useState<string[]>([])
  const set = (field: keyof typeof form) => (value: string) => setForm((f) => ({ ...f, [field]: value }))

  const save = useMutation({
    mutationFn: () =>
      post<{ warnings: string[] }>(`/weddings/${form.wedding}/expenses/`, {
        vendor_id: form.vendor_id ? Number(form.vendor_id) : null,
        category: form.category,
        description: form.description,
        amount_paise: rupeesToPaise(form.amount),
        bill_ref: form.bill_ref,
        due_date: form.due_date || null,
      }),
    onSuccess: async (saved) => {
      await refresh()
      if (saved.warnings?.length) setWarnings(saved.warnings)
      else onClose()
    },
  })

  if (warnings.length) {
    return (
      <Modal open title="Bill saved" onClose={onClose}>
        <div className="space-y-3 text-sm">
          {warnings.map((w) => (
            <p key={w} className="rounded-xl bg-amber-50 p-3 text-amber-800">
              {w}
            </p>
          ))}
          <div className="flex justify-end">
            <Button onClick={onClose}>OK</Button>
          </div>
        </div>
      </Modal>
    )
  }
  const submit = (event: FormEvent) => {
    event.preventDefault()
    save.mutate()
  }
  return (
    <Modal open title="Add a vendor bill" onClose={onClose}>
      <form onSubmit={submit} className="space-y-3">
        {weddingId === null && (
          <Select label="Wedding" required value={form.wedding} onChange={(e) => set('wedding')(e.target.value)}>
            <option value="">Choose a wedding…</option>
            {weddings.map((w) => (
              <option key={w.wedding_id} value={w.wedding_id}>
                {w.title}
              </option>
            ))}
          </Select>
        )}
        <Select
          label="Vendor"
          value={form.vendor_id}
          onChange={(e) => {
            const vendor = vendors.data?.results.find((v) => String(v.id) === e.target.value)
            set('vendor_id')(e.target.value)
            if (vendor && !form.category) set('category')(vendor.category_name ?? '')
          }}
        >
          <option value="">No vendor (for example venue or fuel)</option>
          {vendors.data?.results.map((v) => (
            <option key={v.id} value={v.id}>
              {v.name}
            </option>
          ))}
        </Select>
        <Input label="Category" required value={form.category} onChange={(e) => set('category')(e.target.value)} placeholder="Caterer, Decor, Venue…" />
        <Input label="What is it for?" required value={form.description} onChange={(e) => set('description')(e.target.value)} />
        <div className="grid grid-cols-2 gap-3">
          <Input label="Amount (₹)" inputMode="decimal" required value={form.amount} onChange={(e) => set('amount')(e.target.value)} />
          <Input label="Due date" type="date" value={form.due_date} onChange={(e) => set('due_date')(e.target.value)} />
        </div>
        <Input label="Bill reference" value={form.bill_ref} onChange={(e) => set('bill_ref')(e.target.value)} />
        {save.error && (
          <p className="text-sm text-red-600" role="alert">
            {save.error.message}
          </p>
        )}
        <div className="flex justify-end gap-2 pt-2">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" loading={save.isPending} disabled={!form.wedding || rupeesToPaise(form.amount) <= 0}>
            Save bill
          </Button>
        </div>
      </form>
    </Modal>
  )
}
