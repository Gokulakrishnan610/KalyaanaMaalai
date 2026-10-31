import { useQuery } from '@tanstack/react-query'
import { Plus } from 'lucide-react'
import { useState } from 'react'
import { get } from '@/api/client'
import { Button, cn } from '@/components/common'
import { useLogin } from '@/login/LoginContext'
import { CustomerPayments } from './CustomerPayments'
import { PaymentHistory } from './PaymentHistory'
import { StatCards } from './StatCards'
import type { InvoiceRow, Overview, VendorBill } from './types'
import { VendorPayments } from './VendorPayments'

type Tab = 'customers' | 'vendors' | 'history'

/**
 * Everything about money for all weddings, or for one: four numbers, then three sections.
 *   From customers: invoices, payment links, offline payments
 *   To vendors:     bills and instalments, offline payments
 *   History:        every payment, with undo for mistakes
 */
export function PaymentsWorkspace({ weddingId }: { weddingId: number | null }) {
  const canEdit = useLogin().hasRole('PLANNER')
  const [tab, setTab] = useState<Tab>('customers')
  const [adding, setAdding] = useState(false)
  const scope = weddingId ?? 'all'

  const overview = useQuery({ queryKey: ['finance-overview'], queryFn: () => get<Overview>('/finance/overview/') })
  // the same queries the sections use, so the tab badges cost nothing extra
  const invoices = useQuery({
    queryKey: ['finance', 'invoices', scope, 'open'],
    queryFn: () => get<InvoiceRow[]>('/invoices/', { wedding: weddingId ?? undefined, status: 'open' }),
  })
  const bills = useQuery({
    queryKey: ['finance', 'bills', scope, 'open'],
    queryFn: () => get<VendorBill[]>('/finance/vendor-bills/', { wedding: weddingId ?? undefined, status: 'open' }),
  })
  const lateFromCustomers = invoices.data?.filter((i) => i.overdue).length ?? 0
  const lateToVendors = bills.data?.filter((b) => b.overdue).length ?? 0

  const tabs: { id: Tab; label: string; late: number }[] = [
    { id: 'customers', label: 'From customers', late: lateFromCustomers },
    { id: 'vendors', label: 'To vendors', late: lateToVendors },
    { id: 'history', label: 'History', late: 0 },
  ]
  const weddings = overview.data?.weddings ?? []

  return (
    <div className="space-y-6">
      <StatCards weddingId={weddingId} />

      <div>
        <div className="mb-5 flex flex-wrap items-end justify-between gap-3 border-b border-slate-200">
          <div className="flex gap-1" role="tablist">
            {tabs.map((t) => (
              <button
                key={t.id}
                role="tab"
                aria-selected={tab === t.id}
                onClick={() => setTab(t.id)}
                className={cn(
                  '-mb-px flex items-center gap-2 border-b-2 px-4 py-2.5 text-sm font-medium',
                  tab === t.id ? 'border-brand-500 text-brand-600' : 'border-transparent text-slate-500 hover:text-slate-800',
                )}
              >
                {t.label}
                {t.late > 0 && <span className="rounded-full bg-red-100 px-2 text-xs font-semibold text-red-700">{t.late} overdue</span>}
              </button>
            ))}
          </div>
          {canEdit && tab !== 'history' && (
            <Button className="mb-2" onClick={() => setAdding(true)}>
              <Plus size={16} /> {tab === 'customers' ? 'New invoice' : 'Vendor bill'}
            </Button>
          )}
        </div>

        {tab === 'customers' && <CustomerPayments weddingId={weddingId} weddings={weddings} adding={adding} onCloseAdd={() => setAdding(false)} />}
        {tab === 'vendors' && <VendorPayments weddingId={weddingId} weddings={weddings} adding={adding} onCloseAdd={() => setAdding(false)} />}
        {tab === 'history' && <PaymentHistory weddingId={weddingId} />}
      </div>
    </div>
  )
}
