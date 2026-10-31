import { useMutation } from '@tanstack/react-query'
import { useState } from 'react'
import { Button, Input, Modal, Select } from '@/components/common'
import { formatINR, rupeesToPaise } from '@/helpers/money'
import { newIdempotencyKey, postWithKey, rupeeText, useRefreshMoney } from './finance'
import { METHODS, type Method } from './types'

interface Props {
  title: string
  /** who it is for, shown above the form */
  subtitle?: string
  remaining: number
  /** the endpoint that records the payment */
  url: string
  /** "Amount received" for customers, "Amount paid" for vendors */
  amountLabel: string
  defaultMethod?: Method
  onClose: () => void
}

/** Types in a payment made outside the website (cash, UPI, bank transfer, cheque). Used for customers and vendors. */
export function RecordPaymentModal({ title, subtitle, remaining, url, amountLabel, defaultMethod = 'UPI', onClose }: Props) {
  const refresh = useRefreshMoney()
  const [key] = useState(newIdempotencyKey) // one key per opening, so a double click records one payment
  const [amount, setAmount] = useState(rupeeText(remaining))
  const [method, setMethod] = useState<Method>(defaultMethod)
  const [reference, setReference] = useState('')
  const [paidOn, setPaidOn] = useState('')
  const paise = rupeesToPaise(amount)
  const over = paise > remaining
  const today = new Date().toISOString().slice(0, 10)

  const save = useMutation({
    mutationFn: () =>
      postWithKey(url, { amount_paise: paise, method, reference, ...(paidOn ? { paid_at: `${paidOn}T12:00:00Z` } : {}) }, key),
    onSuccess: async () => {
      await refresh()
      onClose()
    },
  })

  return (
    <Modal open title={title} onClose={onClose}>
      <form
        className="space-y-3"
        onSubmit={(e) => {
          e.preventDefault()
          save.mutate()
        }}
      >
        {subtitle && <p className="text-sm text-slate-600">{subtitle}</p>}
        <p className="text-sm text-slate-600">
          Still due: <b className="tabular-nums">{formatINR(remaining)}</b>
        </p>
        <Input
          label={`${amountLabel} (₹)`}
          inputMode="decimal"
          required
          value={amount}
          onChange={(e) => setAmount(e.target.value)}
          error={over ? 'More than is still due' : undefined}
        />
        <div className="grid grid-cols-2 gap-3">
          <Select label="How was it paid?" value={method} onChange={(e) => setMethod(e.target.value as Method)}>
            {METHODS.map((m) => (
              <option key={m.value} value={m.value}>
                {m.label}
              </option>
            ))}
          </Select>
          <Input label="Date paid" type="date" max={today} value={paidOn} onChange={(e) => setPaidOn(e.target.value)} />
        </div>
        <Input label="Reference (UTR, cheque number…)" value={reference} onChange={(e) => setReference(e.target.value)} />
        {save.error && (
          <p className="text-sm text-red-600" role="alert">
            {save.error.message}
          </p>
        )}
        <div className="flex justify-end gap-2 pt-2">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" loading={save.isPending} disabled={paise <= 0 || over}>
            Save payment {paise > 0 && !over ? formatINR(paise) : ''}
          </Button>
        </div>
      </form>
    </Modal>
  )
}
