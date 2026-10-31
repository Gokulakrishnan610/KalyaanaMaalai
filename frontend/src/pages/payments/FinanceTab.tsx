import { PaymentsWorkspace } from './PaymentsWorkspace'

/**
 * The Finance tab on a wedding's page: the same three sections as the Payments page, for just this wedding.
 * The wedding page loads it automatically:  <FinanceTab weddingId={wedding.id} />
 */
export function FinanceTab({ weddingId }: { weddingId: number }) {
  return <PaymentsWorkspace key={weddingId} weddingId={weddingId} />
}

export default FinanceTab
