import { useMutation } from '@tanstack/react-query'
import { useState, type DragEvent } from 'react'
import { api } from '@/api/client'
import { Badge, Button, Input, Modal } from '@/components/common'
import { formatINR, paiseToRupees, rupeesToPaise } from '@/helpers/money'

const ALLOWED = ['application/pdf', 'image/jpeg', 'image/png']
const MAX_BYTES = 10 * 1024 * 1024

/** What the AI reader found, in paise. Everything may be missing; the user can edit it before using it. */
export interface ExtractedQuotation {
  vendor_name: string
  total_paise: number
  price_per_plate_paise: number | null
  guest_count: number | null
  valid_till: string | null
  menu_notes: string
  confidence: number
  warnings: string[]
  items: { description: string; qty: number; unit_price_paise: number }[]
}

interface Props {
  open: boolean
  onClose: () => void
  /** Called with the (possibly edited) values when the user clicks "Use these values". */
  onUse: (data: ExtractedQuotation) => void
}

const rupees = (paise: number | null) => (paise == null ? '' : String(paiseToRupees(paise)))

/** Upload a quotation PDF or photo, check what the AI found, fix anything wrong, then hand the values to a form. */
export function AIExtractModal({ open, onClose, onUse }: Props) {
  const [file, setFile] = useState<File | null>(null)
  const [fileError, setFileError] = useState('')
  const [dragging, setDragging] = useState(false)
  const [draft, setDraft] = useState<ExtractedQuotation | null>(null)
  // the editable copies, in rupees as typed
  const [form, setForm] = useState({ vendor: '', total: '', perPlate: '', guests: '', validTill: '', notes: '' })
  const [items, setItems] = useState<{ description: string; qty: string; price: string }[]>([])

  const read = useMutation({
    mutationFn: async () => {
      const body = new FormData()
      body.append('file', file!)
      return (await api.post<{ draft: ExtractedQuotation }>('/ai/extract-quotation/', body)).data.draft
    },
    onSuccess: (found) => {
      setDraft(found)
      setForm({
        vendor: found.vendor_name,
        total: rupees(found.total_paise),
        perPlate: rupees(found.price_per_plate_paise),
        guests: found.guest_count == null ? '' : String(found.guest_count),
        validTill: found.valid_till ?? '',
        notes: found.menu_notes,
      })
      setItems(found.items.map((i) => ({ description: i.description, qty: String(i.qty), price: rupees(i.unit_price_paise) })))
    },
  })

  const set = (field: keyof typeof form) => (value: string) => setForm((f) => ({ ...f, [field]: value }))
  const choose = (chosen: File | null) => {
    setFileError('')
    if (!chosen) return setFile(null)
    if (!ALLOWED.includes(chosen.type)) return setFileError('Upload a PDF, JPG or PNG file.')
    if (chosen.size > MAX_BYTES) return setFileError('The file is larger than 10 MB.')
    setFile(chosen)
  }
  const onDrop = (event: DragEvent) => {
    event.preventDefault()
    setDragging(false)
    choose(event.dataTransfer.files[0] ?? null)
  }
  const reset = () => {
    setDraft(null)
    setFile(null)
    read.reset()
  }
  const close = () => {
    reset()
    onClose()
  }

  const use = () => {
    if (!draft) return
    onUse({
      ...draft,
      vendor_name: form.vendor,
      total_paise: rupeesToPaise(form.total),
      price_per_plate_paise: form.perPlate ? rupeesToPaise(form.perPlate) : null,
      guest_count: form.guests ? Number(form.guests) : null,
      valid_till: form.validTill || null,
      menu_notes: form.notes,
      items: items
        .filter((i) => i.description.trim())
        .map((i) => ({ description: i.description.trim(), qty: Number(i.qty) || 1, unit_price_paise: rupeesToPaise(i.price) })),
    })
    close()
  }

  const confidence = draft ? Math.round(draft.confidence * 100) : 0
  return (
    <Modal open={open} title="Read a quotation with AI" onClose={close} wide>
      {!draft ? (
        <div className="space-y-4">
          <label
            onDragOver={(e) => {
              e.preventDefault()
              setDragging(true)
            }}
            onDragLeave={() => setDragging(false)}
            onDrop={onDrop}
            className={`flex cursor-pointer flex-col items-center justify-center gap-1 rounded-xl border-2 border-dashed px-6 py-10 text-center text-sm ${dragging ? 'border-brand-500 bg-brand-50' : 'border-slate-300 bg-slate-50'}`}
          >
            <span className="font-medium">{file ? file.name : 'Drop the vendor’s PDF or photo here'}</span>
            <span className="text-slate-500">{file ? `${(file.size / 1024).toFixed(0)} KB` : 'or click to choose a file (PDF, JPG or PNG, up to 10 MB)'}</span>
            <input type="file" accept=".pdf,image/jpeg,image/png" className="sr-only" onChange={(e) => choose(e.target.files?.[0] ?? null)} />
          </label>
          {fileError && <p className="text-sm text-red-600">{fileError}</p>}
          {read.error && (
            <p className="rounded-xl bg-red-50 p-3 text-sm text-red-700" role="alert">
              {read.error.message} You can still type the quotation in by hand.
            </p>
          )}
          {read.isPending && (
            <div aria-live="polite" className="space-y-2">
              <div className="h-2 overflow-hidden rounded-full bg-slate-100">
                <div className="h-full w-1/3 animate-pulse rounded-full bg-brand-500" />
              </div>
              <p className="text-sm text-slate-500">Reading your file… this takes a few seconds.</p>
            </div>
          )}
          <div className="flex justify-end gap-2">
            <Button variant="secondary" onClick={close}>
              Cancel
            </Button>
            <Button disabled={!file} loading={read.isPending} onClick={() => read.mutate()}>
              Read quotation
            </Button>
          </div>
        </div>
      ) : (
        <div className="space-y-4">
          <div className="flex items-center gap-2 text-sm">
            <span>Confidence</span>
            <Badge tone={confidence >= 80 ? 'green' : confidence >= 50 ? 'amber' : 'red'}>{confidence}%</Badge>
            <span className="text-slate-500">Check every field against the document before using it.</span>
          </div>
          {draft.warnings.map((w) => (
            <p key={w} className="rounded-xl bg-amber-50 p-3 text-sm text-amber-800">
              {w}
            </p>
          ))}
          <div className="grid gap-3 sm:grid-cols-2">
            <Input label="Vendor" value={form.vendor} onChange={(e) => set('vendor')(e.target.value)} />
            <Input label="Total (₹)" inputMode="decimal" value={form.total} onChange={(e) => set('total')(e.target.value)} />
            <Input label="Price per plate (₹)" inputMode="decimal" value={form.perPlate} onChange={(e) => set('perPlate')(e.target.value)} />
            <Input label="Guests" type="number" value={form.guests} onChange={(e) => set('guests')(e.target.value)} />
            <Input label="Valid till" type="date" value={form.validTill} onChange={(e) => set('validTill')(e.target.value)} />
            <Input label="Menu notes" value={form.notes} onChange={(e) => set('notes')(e.target.value)} />
          </div>
          {items.length > 0 && (
            <div>
              <div className="mb-1 text-sm font-medium text-slate-700">Line items</div>
              <div className="space-y-2">
                {items.map((item, index) => (
                  <div key={index} className="grid grid-cols-[1fr_5rem_8rem_auto] items-end gap-2">
                    <Input aria-label="Description" value={item.description} onChange={(e) => setItems((l) => l.map((x, i) => (i === index ? { ...x, description: e.target.value } : x)))} />
                    <Input aria-label="Quantity" inputMode="decimal" value={item.qty} onChange={(e) => setItems((l) => l.map((x, i) => (i === index ? { ...x, qty: e.target.value } : x)))} />
                    <Input aria-label="Unit price (₹)" inputMode="decimal" value={item.price} onChange={(e) => setItems((l) => l.map((x, i) => (i === index ? { ...x, price: e.target.value } : x)))} />
                    <span className="pb-2 text-right text-xs tabular-nums text-slate-500">
                      {formatINR(Math.round((Number(item.qty) || 0) * rupeesToPaise(item.price)))}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
          <div className="flex justify-between gap-2 pt-2">
            <Button variant="ghost" onClick={reset}>
              Try another file
            </Button>
            <div className="flex gap-2">
              <Button variant="secondary" onClick={close}>
                Cancel
              </Button>
              <Button onClick={use}>Use these values</Button>
            </div>
          </div>
        </div>
      )}
    </Modal>
  )
}
