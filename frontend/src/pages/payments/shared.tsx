import { Badge } from '@/components/common'
import type { LinkStatus, PayStatus } from './types'

const STATUS_TONE = { UNPAID: 'gray', PARTIAL: 'amber', PAID: 'green' } as const
const STATUS_LABEL = { UNPAID: 'Unpaid', PARTIAL: 'Part paid', PAID: 'Paid' } as const

export function StatusBadge({ status, overdue }: { status: PayStatus; overdue?: boolean }) {
  if (overdue && status !== 'PAID') return <Badge tone="red">Overdue</Badge>
  return <Badge tone={STATUS_TONE[status]}>{STATUS_LABEL[status]}</Badge>
}

const LINK_TONE = { ACTIVE: 'blue', PAID: 'green', CANCELLED: 'gray', EXPIRED: 'amber', SETTLED: 'gray' } as const
const LINK_LABEL = {
  ACTIVE: 'Waiting for payment',
  PAID: 'Paid',
  CANCELLED: 'Cancelled',
  EXPIRED: 'Expired',
  SETTLED: 'Invoice already paid',
} as const

export function LinkBadge({ status }: { status: LinkStatus }) {
  return <Badge tone={LINK_TONE[status]}>{LINK_LABEL[status]}</Badge>
}
