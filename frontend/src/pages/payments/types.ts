export type PayStatus = 'UNPAID' | 'PARTIAL' | 'PAID'
export type InvoiceType = 'DEPOSIT' | 'MILESTONE' | 'EXTRA_GUESTS' | 'FINAL'
/** What a person can type in. Online payments (RAZORPAY) are recorded by the system, never by hand. */
export type Method = 'UPI' | 'BANK' | 'CASH' | 'CHEQUE' | 'CARD'

export const METHODS: { value: Method; label: string }[] = [
  { value: 'UPI', label: 'UPI' },
  { value: 'BANK', label: 'Bank transfer' },
  { value: 'CASH', label: 'Cash' },
  { value: 'CHEQUE', label: 'Cheque' },
  { value: 'CARD', label: 'Card' },
]
export const methodLabel = (m: string) => (m === 'RAZORPAY' ? 'Online' : (METHODS.find((x) => x.value === m)?.label ?? m))

export const INVOICE_TYPES: { value: InvoiceType; label: string }[] = [
  { value: 'DEPOSIT', label: 'Booking deposit' },
  { value: 'MILESTONE', label: 'Instalment' },
  { value: 'FINAL', label: 'Final payment' },
  { value: 'EXTRA_GUESTS', label: 'Extra guest charges' },
]

export type LinkStatus = 'ACTIVE' | 'PAID' | 'CANCELLED' | 'EXPIRED' | 'SETTLED'

export interface PaymentLink {
  id: number
  invoice_id: number
  token: string
  path: string
  amount_paise: number
  status: LinkStatus
  expires_at: string
  created_at: string
  paid_at: string | null
  created_by_name: string
}

/** A customer invoice as listed on the Payments page. */
export interface InvoiceRow {
  id: number
  wedding_id: number
  wedding_title: string
  client_name: string
  client_phone: string
  client_email: string
  type: InvoiceType
  type_label: string
  amount_paise: number
  paid_paise: number
  remaining_paise: number
  due_date: string | null
  status: PayStatus
  overdue: boolean
  note: string
  link: PaymentLink | null
}

export interface Instalment {
  id: number
  vendor_name: string
  expense_id: number | null
  part: 'ADVANCE' | 'FINAL'
  part_label: string
  amount_paise: number
  paid_paise: number
  remaining_paise: number
  due_date: string | null
  status: PayStatus
  overdue: boolean
}

export interface VendorBill {
  id: number
  wedding_id: number
  wedding_title: string
  vendor_id: number | null
  vendor_name: string
  category: string
  description: string
  amount_paise: number
  paid_paise: number
  remaining_paise: number
  bill_ref: string
  due_date: string | null
  status: PayStatus
  overdue: boolean
  instalments: Instalment[]
  warnings?: string[]
}

export interface LedgerRow {
  id: number
  wedding_id: number
  wedding_title: string
  direction: 'IN' | 'OUT'
  party: string
  what: string
  amount_paise: number
  method: string
  reference: string
  paid_at: string
  source: 'MANUAL' | 'ONLINE' | 'LINK'
  recorded_by_name: string
  can_undo: boolean
}

export interface OverviewRow {
  wedding_id: number
  title: string
  client_name: string
  date: string
  invoiced_paise: number
  received_paise: number
  planned_expense_paise: number
  paid_expense_paise: number
  estimated_profit_paise: number
}

export interface Overview {
  totals: Record<string, number>
  weddings: OverviewRow[]
}

/** What the customer's public payment page shows. */
export interface PublicLink {
  business: string
  couple: string
  wedding: string
  wedding_date: string
  for: string
  note: string
  due_date: string | null
  invoice_total_paise: number
  paid_so_far_paise: number
  amount_paise: number
  status: LinkStatus
  expires_at: string
  demo_mode: boolean
  available: boolean
  receipt: { number: string; paid_at: string; amount_paise: number; reference: string } | null
}

export interface GatewayOrder {
  order_id: string
  amount: number
  currency: string
  key_id: string
  mock: boolean
  mock_payment_id?: string
  mock_signature?: string
}

/** The numbers the extra-guest charge needs, from /weddings/<id>/finance/. */
export interface WeddingMoney {
  wedding: { id: number; title: string; guest_count: number; contracted_guests: number; per_guest_rate_paise: number; budget_paise: number }
}
