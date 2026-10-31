import { useQuery } from '@tanstack/react-query'
import { get } from '@/api/client'
import { ErrorState, Spinner } from '@/components/common'
import { BudgetChart } from './BudgetChart'
import { ExpenseSection } from './ExpenseSection'
import { InvoiceSection } from './InvoiceSection'
import { SummaryCards } from './SummaryCards'
import type { Financials } from './types'
import { UpcomingPayments } from './UpcomingPayments'

/**
 * The money side of one wedding: summary, client invoices, vendor bills, instalments and charts.
 * Member 2 puts it on the wedding page:  <FinanceTab weddingId={wedding.id} />
 */
export function FinanceTab({ weddingId }: { weddingId: number }) {
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['finance', weddingId, 'summary'],
    queryFn: () => get<Financials>(`/weddings/${weddingId}/finance/`),
  })
  if (isLoading) return <Spinner />
  if (error || !data) return <ErrorState message={error?.message ?? 'Could not load the finances'} onRetry={refetch} />

  return (
    <div className="space-y-8">
      <SummaryCards data={data} />
      <BudgetChart data={data} />
      <div className="grid gap-8 xl:grid-cols-[minmax(0,1fr)_22rem]">
        <div className="min-w-0 space-y-8">
          <InvoiceSection weddingId={weddingId} finance={data} />
          <ExpenseSection weddingId={weddingId} />
        </div>
        <UpcomingPayments items={data.upcoming_payments} showWedding={false} />
      </div>
    </div>
  )
}

export default FinanceTab
