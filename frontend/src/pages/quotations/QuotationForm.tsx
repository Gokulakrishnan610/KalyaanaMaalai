import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useRef, useState, type DragEvent } from 'react'
import { api, post, ApiError } from '@/api/client'
import { Button, Input, Modal, Select, cn } from '@/components/common'
import { formatINR, paiseToRupees, rupeesToPaise } from '@/helpers/money'
import type { Quotation, QuotationDraft, QuotationRequest } from './types'

interface Props {
  request: QuotationRequest
  /** Set to change a quotation that was already entered. */
  quotation?: Quotation | null
  /** Pre-selected vendor when "Add quotation" was clicked on a vendor's row. */
  vendorId?: number
  onClose: () => void
}

interface Line {
  description: string
  qty: string
  price: string // rupees, as typed
}

type AiField = 'vendor' | 'total' | 'perPlate' | 'validTill' | 'menuNotes' | 'items'

const ALLOWED = ['application/pdf', 'image/jpeg', 'image/png']
const MAX_BYTES = 10 * 1024 * 1024
const AI_HIGHLIGHT = 'bg-amber-50 ring-2 ring-amber-300'

export function QuotationForm(props: Props) {
  return (
    <Modal open title={props.quotation ? 'Edit quotation' : 'Add quotation'} onClose={props.onClose} wide>
      <FormBody {...props} />
    </Modal>
  )
}

function rupees(paise: number | null | undefined): string {
  return paise == null ? '' : String(paiseToRupees(paise))
}

function FormBody({ request, quotation, vendorId, onClose }: Props) {
  const queryClient = useQueryClient()
  const fileInput = useRef<HTMLInputElement>(null)
  const [vendor, setVendor] = useState(String(quotation?.vendor.id ?? vendorId ?? ''))
  const [perPlate, setPerPlate] = useState(rupees(quotation?.price_per_plate_paise))
  const [total, setTotal] = useState(rupees(quotation?.total_paise))
  const [validTill, setValidTill] = useState(quotation?.valid_till ?? '')
  const [menuNotes, setMenuNotes] = useState(quotation?.menu_notes ?? '')
  const [lines, setLines] = useState<Line[]>(
    quotation?.items.map((i) => ({ description: i.description, qty: String(i.qty), price: rupees(i.unit_price_paise) })) ?? [],
  )
  const [file, setFile] = useState<File | null>(null)
  const [fileError, setFileError] = useState('')
  const [dragging, setDragging] = useState(false)
  const [aiFields, setAiFields] = useState<Set<AiField>>(new Set())
  const [aiMessage, setAiMessage] = useState('')

  const filledLines = lines.filter((l) => l.description.trim())
  const itemsTotal = filledLines.reduce((sum, l) => sum + (Number(l.qty) || 0) * rupeesToPaise(l.price), 0)
  const hasItems = filledLines.length > 0
  const guests = request.guest_count
  const impliedTotal = !hasItems && perPlate && guests ? rupeesToPaise(perPlate) * guests : null

  const edited = (field: AiField) =>
    setAiFields((current) => {
      if (!current.has(field)) return current
      const next = new Set(current)
      next.delete(field)
      return next
    })
  const mark = (field: AiField) => (aiFields.has(field) ? AI_HIGHLIGHT : '')

  function chooseFile(chosen: File | null) {
    setFileError('')
    if (!chosen) return setFile(null)
    if (!ALLOWED.includes(chosen.type)) return setFileError('Upload a PDF, JPG or PNG file.')
    if (chosen.size > MAX_BYTES) return setFileError('The file is larger than 10 MB.')
    setFile(chosen)
  }

  function onDrop(e: DragEvent) {
    e.preventDefault()
    setDragging(false)
    chooseFile(e.dataTransfer.files[0] ?? null)
  }

  const extract = useMutation({
    mutationFn: async () => {
      const body = new FormData()
      body.append('file', file!)
      return (await api.post<{ draft: QuotationDraft }>('/quotations/extract/', body)).data.draft
    },
    onSuccess: (draft) => {
      const filled = new Set<AiField>()
      const match = request.invited_vendors.find(
        (v) => draft.vendor_name && v.name.toLowerCase().includes(draft.vendor_name.toLowerCase().split(' ')[0]),
      )
      if (match && !vendor) {
        setVendor(String(match.id))
        filled.add('vendor')
      }
      if (draft.price_per_plate_paise != null) {
        setPerPlate(rupees(draft.price_per_plate_paise))
        filled.add('perPlate')
      }
      if (draft.total_paise != null) {
        setTotal(rupees(draft.total_paise))
        filled.add('total')
      }
      if (draft.valid_till) {
        setValidTill(draft.valid_till)
        filled.add('validTill')
      }
      if (draft.menu_notes) {
        setMenuNotes(draft.menu_notes)
        filled.add('menuNotes')
      }
      if (draft.items?.length) {
        setLines(
          draft.items.map((i) => ({
            description: i.description ?? '',
            qty: String(i.qty ?? i.quantity ?? 1),
            price: rupees(i.unit_price_paise ?? 0),
          })),
        )
        filled.add('items')
      }
      setAiFields(filled)
      setAiMessage(
        filled.size
          ? 'Filled in by AI. Check every highlighted field against the PDF before saving.'
          : 'The AI could not find anything to fill in. Please type the quotation in.',
      )
    },
    onError: (error) => setAiMessage(`${error.message} You can still type the quotation in.`),
  })

  const save = useMutation({
    mutationFn: async () => {
      const saved = await post<Quotation>(`/quotation-requests/${request.id}/quotations/`, {
        vendor_id: Number(vendor),
        price_per_plate_paise: perPlate ? rupeesToPaise(perPlate) : null,
        ...(hasItems ? {} : total ? { total_paise: rupeesToPaise(total) } : {}),
        menu_notes: menuNotes,
        valid_till: validTill || null,
        items: filledLines.map((l) => ({
          description: l.description.trim(),
          qty: Number(l.qty) || 1,
          unit_price_paise: rupeesToPaise(l.price),
        })),
        ai_extracted: aiFields.size > 0,
      })
      if (file) {
        const body = new FormData()
        body.append('file', file)
        try {
          await api.post(`/quotations/${saved.id}/upload/`, body)
        } catch (error) {
          throw new Error(`The quotation was saved, but the file was not uploaded: ${(error as Error).message}`)
        }
      }
      return saved
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['quotation-request', request.id] })
      queryClient.invalidateQueries({ queryKey: ['comparison', request.id] })
      queryClient.invalidateQueries({ queryKey: ['quotation-requests'] })
      onClose()
    },
    onError: () => {
      queryClient.invalidateQueries({ queryKey: ['quotation-request', request.id] })
      queryClient.invalidateQueries({ queryKey: ['comparison', request.id] })
    },
  })
  const errors = save.error instanceof ApiError ? save.error.fields : {}

  const setLine = (index: number, patch: Partial<Line>) =>
    setLines((current) => current.map((l, i) => (i === index ? { ...l, ...patch } : l)))

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault()
        save.mutate()
      }}
      className="space-y-4"
    >
      <div
        onDragOver={(e) => {
          e.preventDefault()
          setDragging(true)
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        className={cn('rounded-xl border-2 border-dashed p-4 text-center text-sm', dragging ? 'border-brand-500 bg-brand-50' : 'border-slate-300 bg-slate-50')}
      >
        <input
          ref={fileInput}
          type="file"
          accept=".pdf,.jpg,.jpeg,.png,application/pdf,image/jpeg,image/png"
          className="sr-only"
          aria-label="Quotation file"
          onChange={(e) => chooseFile(e.target.files?.[0] ?? null)}
        />
        {file ? (
          <p className="font-medium text-slate-700">
            {file.name} <span className="font-normal text-slate-500">({(file.size / 1024).toFixed(0)} KB)</span>
          </p>
        ) : (
          <p className="text-slate-600">Drop the vendor's PDF here (PDF, JPG or PNG, up to 10 MB)</p>
        )}
        <div className="mt-2 flex flex-wrap justify-center gap-2">
          <Button type="button" variant="secondary" onClick={() => fileInput.current?.click()}>
            {file ? 'Choose a different file' : 'Choose file'}
          </Button>
          <Button type="button" disabled={!file} loading={extract.isPending} onClick={() => extract.mutate()}>
            ✨ Extract with AI
          </Button>
        </div>
        {fileError && <p role="alert" className="mt-2 text-xs text-red-600">{fileError}</p>}
        {aiMessage && (
          <p role="status" className="mt-2 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-left text-sm text-amber-800">
            {aiMessage}
          </p>
        )}
      </div>

      <div className="grid gap-3 sm:grid-cols-3">
        <Select
          label="Vendor"
          required
          value={vendor}
          disabled={!!quotation}
          className={mark('vendor')}
          error={errors.vendor_id}
          onChange={(e) => {
            setVendor(e.target.value)
            edited('vendor')
          }}
        >
          <option value="">Choose…</option>
          {request.invited_vendors.map((v) => (
            <option key={v.id} value={v.id}>
              {v.name}
              {v.received && !quotation ? ' (already quoted — will replace)' : ''}
            </option>
          ))}
        </Select>
        <Input
          label="Price per plate (₹)"
          inputMode="decimal"
          value={perPlate}
          className={mark('perPlate')}
          error={errors.price_per_plate_paise}
          onChange={(e) => {
            setPerPlate(e.target.value)
            edited('perPlate')
          }}
        />
        <Input
          label="Valid till"
          type="date"
          value={validTill}
          className={mark('validTill')}
          error={errors.valid_till}
          onChange={(e) => {
            setValidTill(e.target.value)
            edited('validTill')
          }}
        />
      </div>

      <div>
        <div className="mb-1 flex items-center justify-between">
          <span className="text-sm font-medium text-slate-700">Line items (optional)</span>
          <Button type="button" variant="ghost" onClick={() => setLines((l) => [...l, { description: '', qty: '1', price: '' }])}>
            + Add line
          </Button>
        </div>
        {lines.length > 0 && (
          <div className={cn('space-y-2 rounded-lg p-2', mark('items'))}>
            {lines.map((line, index) => (
              <div key={index} className="grid grid-cols-[1fr_5rem_7rem_auto] items-center gap-2">
                <input
                  aria-label={`Item ${index + 1} description`}
                  placeholder="e.g. Welcome drinks"
                  value={line.description}
                  onChange={(e) => {
                    setLine(index, { description: e.target.value })
                    edited('items')
                  }}
                  className="rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-brand-500"
                />
                <input
                  aria-label={`Item ${index + 1} quantity`}
                  type="number"
                  min={1}
                  value={line.qty}
                  onChange={(e) => {
                    setLine(index, { qty: e.target.value })
                    edited('items')
                  }}
                  className="rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-brand-500"
                />
                <input
                  aria-label={`Item ${index + 1} price each in rupees`}
                  placeholder="₹ each"
                  inputMode="decimal"
                  value={line.price}
                  onChange={(e) => {
                    setLine(index, { price: e.target.value })
                    edited('items')
                  }}
                  className="rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-brand-500"
                />
                <button
                  type="button"
                  aria-label={`Remove item ${index + 1}`}
                  onClick={() => setLines((l) => l.filter((_, i) => i !== index))}
                  className="px-1 text-slate-400 hover:text-red-600"
                >
                  ✕
                </button>
              </div>
            ))}
          </div>
        )}
        {errors.items && <p className="mt-1 text-xs text-red-600">{errors.items}</p>}
      </div>

      <div className="grid gap-3 sm:grid-cols-2">
        <div>
          <Input
            label={hasItems ? 'Total (₹) — from the line items' : 'Total (₹)'}
            inputMode="decimal"
            disabled={hasItems}
            value={hasItems ? String(paiseToRupees(itemsTotal)) : total}
            className={mark('total')}
            error={errors.total_paise}
            placeholder={impliedTotal ? `${paiseToRupees(impliedTotal)} (price per plate × guests)` : ''}
            onChange={(e) => {
              setTotal(e.target.value)
              edited('total')
            }}
          />
          {impliedTotal != null && (
            <p className="mt-1 text-xs text-slate-500">
              {formatINR(rupeesToPaise(perPlate))} × {guests} guests = {formatINR(impliedTotal)}. Leave the total empty to use this.
            </p>
          )}
        </div>
        <label className="block text-sm">
          <span className="mb-1 block font-medium text-slate-700">Menu notes</span>
          <textarea
            rows={3}
            value={menuNotes}
            onChange={(e) => {
              setMenuNotes(e.target.value)
              edited('menuNotes')
            }}
            className={cn(
              'w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100',
              mark('menuNotes'),
            )}
          />
        </label>
      </div>

      {save.error && Object.keys(errors).length === 0 && (
        <p role="alert" className="text-sm text-red-600">
          {save.error.message}
        </p>
      )}
      <div className="flex justify-end gap-2">
        <Button type="button" variant="secondary" onClick={onClose}>
          Cancel
        </Button>
        <Button type="submit" loading={save.isPending} disabled={!vendor || (!hasItems && !total && !impliedTotal)}>
          Save quotation
        </Button>
      </div>
    </form>
  )
}
