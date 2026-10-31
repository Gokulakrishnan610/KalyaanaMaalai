import { Badge } from '@/components/common'
import type { PayStatus } from './types'

const STATUS_TONE = { UNPAID: 'gray', PARTIAL: 'amber', PAID: 'green' } as const
const STATUS_LABEL = { UNPAID: 'Unpaid', PARTIAL: 'Part paid', PAID: 'Paid' } as const

export function StatusBadge({ status }: { status: PayStatus }) {
  return <Badge tone={STATUS_TONE[status]}>{STATUS_LABEL[status]}</Badge>
}
