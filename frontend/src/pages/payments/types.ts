export type PayStatus = 'UNPAID' | 'PARTIAL' | 'PAID'
export type InvoiceType = 'DEPOSIT' | 'MILESTONE' | 'EXTRA_GUESTS' | 'FINAL'
export type Method = 'CASH' | 'UPI' | 'BANK' | 'CARD' | 'RAZORPAY'

export const METHODS: Method[] = ['UPI', 'BANK', 'CASH', 'CARD']

export const INVOICE_TYPES: { value: InvoiceType; label: string }[] = [
  { value: 'DEPOSIT', label: 'Booking deposit' },
  { value: 'MILESTONE', label: 'Instalment' },
  { value: 'EXTRA_GUESTS', label: 'Extra guests' },
  { value: 'FINAL', label: 'Final payment' },
]

export interface UpcomingPayment {
  kind: 'milestone' | 'expense'
  id: number
  expense_id: number
  wedding_id: number
  wedding_title: string
  vendor_name: string
  description: string
  due_date: string
  outstanding_paise: number
  overdue: boolean
}

export interface Financials {
  wedding: {
    id: number
    title: string
    client_name: string
    guest_count: number
    contracted_guests: number
    per_guest_rate_paise: number
    budget_paise: number
  }
  revenue: { invoiced: number; received: number; outstanding: number }
  expenses: { planned: number; paid: number; outstanding: number }
  estimated_profit: number
  actual_profit: number
  margin_pct: number
  actual_margin_pct: number
  budget_paise: number
  by_category: { category: string; planned: number; paid: number }[]
  upcoming_payments: UpcomingPayment[]
}

export interface Invoice {
  id: number
  wedding_id: number
  type: InvoiceType
  type_label: string
  amount_paise: number
  paid_paise: number
  remaining_paise: number
  due_date: string | null
  status: PayStatus
  note: string
}

export interface Expense {
  id: number
  wedding_id: number
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
  warnings?: string[]
}

export interface Milestone {
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

export interface OverviewRow {
  wedding_id: number
  title: string
  client_name: string
  date: string
  status: string
  budget_paise: number
  invoiced_paise: number
  received_paise: number
  planned_expense_paise: number
  paid_expense_paise: number
  estimated_profit_paise: number
  actual_profit_paise: number
  margin_pct: number
}

export interface Overview {
  totals: Record<string, number>
  weddings: OverviewRow[]
}

export interface RazorpayOrder {
  order_id: string
  amount: number
  currency: string
  key_id: string
  mock: boolean
  mock_payment_id?: string
  mock_signature?: string
}
