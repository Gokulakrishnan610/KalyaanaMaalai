import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { ApiError, get, post, type Page } from '@/api/client'
import { Button, Input, Modal, Select } from '@/components/common'
import { SEVERITIES, type Incident } from './types'

/** Report a problem. Planners are alerted the moment it is saved. */
export function ReportIncidentForm({ weddingId, onClose }: { weddingId?: number; onClose: () => void }) {
  const queryClient = useQueryClient()
  const [wedding, setWedding] = useState(weddingId ? String(weddingId) : '')
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [severity, setSeverity] = useState('MEDIUM')
  const [error, setError] = useState('')

  const { data: weddings } = useQuery({
    queryKey: ['incident-wedding-options'],
    queryFn: () => get<Page<{ id: number; title: string }>>('/weddings/', { page_size: 100 }),
    enabled: !weddingId,
  })

  const save = useMutation({
    mutationFn: () => post<Incident>('/incidents/', { wedding: Number(wedding), title, description, severity }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['incidents'] })
      onClose()
    },
    onError: (e) => setError(e instanceof ApiError ? e.message : 'Could not reach the server'),
  })

  return (
    <Modal open title="Report an incident" onClose={onClose}>
      <form
        className="space-y-4"
        onSubmit={(e) => {
          e.preventDefault()
          setError('')
          save.mutate()
        }}
      >
        {!weddingId && (
          <Select label="Wedding" value={wedding} onChange={(e) => setWedding(e.target.value)} required>
            <option value="">Choose a wedding…</option>
            {weddings?.results.map((w) => (
              <option key={w.id} value={w.id}>
                {w.title}
              </option>
            ))}
          </Select>
        )}
        <Input label="What is the problem?" value={title} onChange={(e) => setTitle(e.target.value)} placeholder="e.g. Florist needs an extra generator" required />
        <label className="block text-sm">
          <span className="mb-1 block font-medium text-slate-700">Details</span>
          <textarea
            rows={3}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
          />
        </label>
        <Select label="How serious is it?" value={severity} onChange={(e) => setSeverity(e.target.value)}>
          {SEVERITIES.map((s) => (
            <option key={s.value} value={s.value}>
              {s.label}
            </option>
          ))}
        </Select>
        {error && <p role="alert" className="text-sm text-red-600">{error}</p>}
        <div className="flex justify-end gap-2">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" loading={save.isPending} disabled={!wedding || !title.trim()}>
            Report incident
          </Button>
        </div>
      </form>
    </Modal>
  )
}
