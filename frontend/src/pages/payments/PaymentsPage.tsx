import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { get } from '@/api/client'
import { Select } from '@/components/common'
import { PaymentsWorkspace } from './PaymentsWorkspace'
import type { Overview } from './types'

/** The Payments page: choose all weddings or one, then collect from customers, pay vendors, or look back. */
export default function PaymentsPage() {
  const [wedding, setWedding] = useState('')
  const { data } = useQuery({ queryKey: ['finance-overview'], queryFn: () => get<Overview>('/finance/overview/') })
  const weddingId = wedding ? Number(wedding) : null

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold">Payments</h1>
          <p className="text-sm text-slate-500">Collect from customers, pay vendors, and keep every rupee recorded.</p>
        </div>
        <div className="w-72">
          <Select aria-label="Wedding" value={wedding} onChange={(e) => setWedding(e.target.value)}>
            <option value="">All weddings</option>
            {data?.weddings.map((w) => (
              <option key={w.wedding_id} value={w.wedding_id}>
                {w.title}
              </option>
            ))}
          </Select>
        </div>
      </div>
      <PaymentsWorkspace key={wedding || 'all'} weddingId={weddingId} />
    </div>
  )
}
