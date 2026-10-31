import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { post } from '@/api/client'
import { Button, Modal } from '@/components/common'
import { StarPicker } from './Stars'

interface Props {
  vendorId: number
  vendorName: string
  weddingId: number
  /** The rating given earlier, so editing starts from it. */
  existing?: { punctuality: number; quality: number; pricing: number; comment: string }
  onClose: () => void
}

/** Rate how a vendor did at one wedding. Rating again replaces the earlier rating. */
export function RateVendorModal({ vendorId, vendorName, weddingId, existing, onClose }: Props) {
  const queryClient = useQueryClient()
  const [scores, setScores] = useState({
    punctuality: existing?.punctuality ?? 0,
    quality: existing?.quality ?? 0,
    pricing: existing?.pricing ?? 0,
  })
  const [comment, setComment] = useState(existing?.comment ?? '')
  const ready = scores.punctuality > 0 && scores.quality > 0 && scores.pricing > 0

  const save = useMutation({
    mutationFn: () => post(`/vendors/${vendorId}/ratings/`, { wedding_id: weddingId, ...scores, comment }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['vendors'] })
      queryClient.invalidateQueries({ queryKey: ['vendor-profile', String(vendorId)] })
      queryClient.invalidateQueries({ queryKey: ['wedding-vendors'] })
      onClose()
    },
  })

  return (
    <Modal open title={`Rate ${vendorName}`} onClose={onClose}>
      <div className="space-y-3">
        <StarPicker label="Punctuality" value={scores.punctuality} onChange={(n) => setScores((s) => ({ ...s, punctuality: n }))} />
        <StarPicker label="Quality of work" value={scores.quality} onChange={(n) => setScores((s) => ({ ...s, quality: n }))} />
        <StarPicker label="Value for money" value={scores.pricing} onChange={(n) => setScores((s) => ({ ...s, pricing: n }))} />
        <label className="block text-sm">
          <span className="mb-1 block font-medium text-slate-700">Comment (optional)</span>
          <textarea
            rows={3}
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
          />
        </label>
        {save.error && (
          <p role="alert" className="text-sm text-red-600">
            {save.error.message}
          </p>
        )}
        <div className="flex justify-end gap-2 pt-1">
          <Button variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button disabled={!ready} loading={save.isPending} onClick={() => save.mutate()}>
            Save rating
          </Button>
        </div>
      </div>
    </Modal>
  )
}
