import { useMutation, useQuery } from '@tanstack/react-query'
import { useState, type FormEvent } from 'react'
import { get, post, remove } from '@/api/client'
import { Badge, Button, EmptyState, ErrorState, Input, Modal, Select, Spinner, Table, Td, Th } from '@/components/common'
import { formatDate } from '@/helpers/date'
import { formatINR, rupeesToPaise } from '@/helpers/money'
import { useLogin } from '@/login/LoginContext'
import { newIdempotencyKey, postWithKey, rupeeText, useRefreshFinance } from './finance'
import { StatusBadge } from './shared'
import { METHODS, type Expense, type Method, type Milestone } from './types'

interface VendorOption {
  id: number
  name: string
  category_name?: string
}

/** What one payment form pays: a whole bill or one instalment of it. */
type Target = { kind: 'expense'; expense: Expense } | { kind: 'milestone'; milestone: Milestone }

export function ExpenseSection({ weddingId }: { weddingId: number }) {
  const canEdit = useLogin().hasRole('PLANNER')
  const refresh = useRefreshFinance(weddingId)
  const [adding, setAdding] = useState(false)
  const [target, setTarget] = useState<Target | null>(null)
  const expenses = useQuery({
    queryKey: ['finance', weddingId, 'expenses'],
    queryFn: () => get<Expense[]>(`/weddings/${weddingId}/expenses/`),
  })
  const milestones = useQuery({
    queryKey: ['finance', weddingId, 'milestones'],
    queryFn: () => get<Milestone[]>(`/weddings/${weddingId}/milestones/`),
  })
  const del = useMutation({
    mutationFn: (id: number) => remove(`/expenses/${id}/`),
    onSuccess: () => refresh(),
  })

  return (
    <section className="space-y-6">
      <div className="space-y-3">
        <div className="flex items-center justify-between gap-2">
          <h2 className="text-lg font-semibold">Vendor expenses</h2>
          {canEdit && <Button onClick={() => setAdding(true)}>Add expense</Button>}
        </div>
        {expenses.isLoading ? (
          <Spinner />
        ) : expenses.error || !expenses.data ? (
          <ErrorState message={expenses.error?.message ?? 'Could not load expenses'} onRetry={expenses.refetch} />
        ) : expenses.data.length === 0 ? (
          <EmptyState title="No expenses yet" hint="Bills appear here when a vendor is chosen, or add one by hand." />
        ) : (
          <Table>
            <thead>
              <tr>
                <Th>Vendor</Th>
                <Th>Bill ref</Th>
                <Th>Due</Th>
                <Th className="text-right">Amount</Th>
                <Th className="text-right">Remaining</Th>
                <Th>Status</Th>
                {canEdit && <Th />}
              </tr>
            </thead>
            <tbody>
              {expenses.data.map((expense) => {
                return (
                  <tr key={expense.id}>
                    <Td>
                      <div className="font-medium">{expense.vendor_name || expense.description}</div>
                      <div className="text-xs text-slate-500">{expense.category}</div>
                    </Td>
                    <Td>{expense.bill_ref || '-'}</Td>
                    <Td className={expense.overdue ? 'font-medium text-red-600' : ''}>
                      {formatDate(expense.due_date)}
                      {expense.overdue && ' · overdue'}
                    </Td>
                    <Td className="text-right tabular-nums">{formatINR(expense.amount_paise)}</Td>
                    <Td className="text-right tabular-nums">{formatINR(expense.remaining_paise)}</Td>
                    <Td>
                      <StatusBadge status={expense.status} />
                    </Td>
                    {canEdit && (
                      <Td className="whitespace-nowrap text-right">
                        {expense.remaining_paise > 0 && (
                          <Button variant="secondary" onClick={() => setTarget({ kind: 'expense', expense })}>
                            Pay
                          </Button>
                        )}
                        {expense.paid_paise === 0 && (
                          <Button
                            variant="ghost"
                            aria-label={`Delete ${expense.description}`}
                            onClick={() => window.confirm('Delete this bill?') && del.mutate(expense.id)}
                          >
                            Delete
                          </Button>
                        )}
                      </Td>
                    )}
                  </tr>
                )
              })}
            </tbody>
          </Table>
        )}
        {del.error && <p className="text-sm text-red-600">{del.error.message}</p>}
      </div>

      <div className="space-y-3">
        <h2 className="text-lg font-semibold">Advance and final instalments</h2>
        {milestones.isLoading ? (
          <Spinner />
        ) : !milestones.data || milestones.data.length === 0 ? (
          <EmptyState title="No instalments yet" hint="Choosing a winning quotation plans an advance and a final instalment." />
        ) : (
          <Table>
            <thead>
              <tr>
                <Th>Vendor</Th>
                <Th>Part</Th>
                <Th>Due</Th>
                <Th className="text-right">Amount</Th>
                <Th className="text-right">Remaining</Th>
                <Th>Status</Th>
                {canEdit && <Th />}
              </tr>
            </thead>
            <tbody>
              {milestones.data.map((m) => (
                <tr key={m.id}>
                  <Td className="font-medium">{m.vendor_name}</Td>
                  <Td>{m.part_label}</Td>
                  <Td className={m.overdue ? 'font-medium text-red-600' : ''}>
                    {formatDate(m.due_date)}
                    {m.overdue && ' · overdue'}
                  </Td>
                  <Td className="text-right tabular-nums">{formatINR(m.amount_paise)}</Td>
                  <Td className="text-right tabular-nums">{formatINR(m.remaining_paise)}</Td>
                  <Td>{m.overdue ? <Badge tone="red">Overdue</Badge> : <StatusBadge status={m.status} />}</Td>
                  {canEdit && (
                    <Td className="text-right">
                      {m.remaining_paise > 0 && m.expense_id && (
                        <Button variant="secondary" onClick={() => setTarget({ kind: 'milestone', milestone: m })}>
                          Pay
                        </Button>
                      )}
                    </Td>
                  )}
                </tr>
              ))}
            </tbody>
          </Table>
        )}
      </div>

      {adding && <AddExpenseModal weddingId={weddingId} onClose={() => setAdding(false)} />}
      {target && <PayModal weddingId={weddingId} target={target} onClose={() => setTarget(null)} />}
    </section>
  )
}

function AddExpenseModal({ weddingId, onClose }: { weddingId: number; onClose: () => void }) {
  const refresh = useRefreshFinance(weddingId)
  const vendors = useQuery({ queryKey: ['vendors', 'options'], queryFn: () => get<{ results: VendorOption[] }>('/vendors/', { page_size: 100 }) })
  const [form, setForm] = useState({ vendor_id: '', category: '', description: '', amount: '', bill_ref: '', due_date: '' })
  const [warnings, setWarnings] = useState<string[]>([])
  const set = (field: keyof typeof form) => (value: string) => setForm((f) => ({ ...f, [field]: value }))

  const save = useMutation({
    mutationFn: () =>
      post<{ warnings: string[] }>(`/weddings/${weddingId}/expenses/`, {
        vendor_id: form.vendor_id ? Number(form.vendor_id) : null,
        category: form.category,
        description: form.description,
        amount_paise: rupeesToPaise(form.amount),
        bill_ref: form.bill_ref,
        due_date: form.due_date || null,
      }),
    onSuccess: async (saved) => {
      await refresh()
      if (saved.warnings?.length) setWarnings(saved.warnings) // saved, but worth a second look
      else onClose()
    },
  })

  if (warnings.length) {
    return (
      <Modal open title="Expense saved" onClose={onClose}>
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
    <Modal open title="Add expense" onClose={onClose}>
      <form onSubmit={submit} className="space-y-3">
        <Select
          label="Vendor"
          value={form.vendor_id}
          onChange={(e) => {
            const vendor = vendors.data?.results.find((v) => String(v.id) === e.target.value)
            set('vendor_id')(e.target.value)
            if (vendor && !form.category) set('category')(vendor.category_name ?? '')
          }}
        >
          <option value="">No vendor (e.g. venue or fuel)</option>
          {vendors.data?.results.map((v) => (
            <option key={v.id} value={v.id}>
              {v.name}
            </option>
          ))}
        </Select>
        <Input label="Category" required value={form.category} onChange={(e) => set('category')(e.target.value)} placeholder="Caterer, Decor, Venue…" />
        <Input label="Description" required value={form.description} onChange={(e) => set('description')(e.target.value)} />
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
          <Button type="submit" loading={save.isPending} disabled={rupeesToPaise(form.amount) <= 0}>
            Save expense
          </Button>
        </div>
      </form>
    </Modal>
  )
}

function PayModal({ weddingId, target, onClose }: { weddingId: number; target: Target; onClose: () => void }) {
  const refresh = useRefreshFinance(weddingId)
  const [key] = useState(newIdempotencyKey) // made once when the modal opens: a double click or retry pays once
  const remaining = target.kind === 'expense' ? target.expense.remaining_paise : target.milestone.remaining_paise
  const title = target.kind === 'expense' ? target.expense.vendor_name || target.expense.description : `${target.milestone.vendor_name} · ${target.milestone.part_label.toLowerCase()}`
  const [amount, setAmount] = useState(rupeeText(remaining))
  const [method, setMethod] = useState<Method>('BANK')
  const [reference, setReference] = useState('')
  const paise = rupeesToPaise(amount)
  const over = paise > remaining

  const pay = useMutation({
    mutationFn: () => {
      const body = { amount_paise: paise, method, reference }
      const url = target.kind === 'expense' ? `/expenses/${target.expense.id}/payments/` : `/milestones/${target.milestone.id}/pay/`
      return postWithKey(url, body, key)
    },
    onSuccess: async () => {
      await refresh()
      onClose()
    },
  })
  return (
    <Modal open title={`Pay ${title}`} onClose={onClose}>
      <form
        onSubmit={(e) => {
          e.preventDefault()
          pay.mutate()
        }}
        className="space-y-3"
      >
        <p className="text-sm text-slate-600">
          Remaining to pay: <b className="tabular-nums">{formatINR(remaining)}</b>
        </p>
        <Input label="Amount (₹)" inputMode="decimal" required value={amount} onChange={(e) => setAmount(e.target.value)} error={over ? 'More than the remaining balance' : undefined} />
        <Select label="Method" value={method} onChange={(e) => setMethod(e.target.value as Method)}>
          {METHODS.map((m) => (
            <option key={m} value={m}>
              {m}
            </option>
          ))}
        </Select>
        <Input label="Reference (UTR, cheque no.)" value={reference} onChange={(e) => setReference(e.target.value)} />
        {pay.error && (
          <p className="text-sm text-red-600" role="alert">
            {pay.error.message}
          </p>
        )}
        <div className="flex justify-end gap-2 pt-2">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" loading={pay.isPending} disabled={paise <= 0 || over}>
            Pay {paise > 0 && !over ? formatINR(paise) : ''}
          </Button>
        </div>
      </form>
    </Modal>
  )
}
