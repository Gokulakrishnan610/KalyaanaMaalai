export interface RequestVendor {
  id: number
  name: string
  phone: string
  email: string
  received: boolean
  quotation_id: number | null
}

export interface QuotationRequest {
  id: number
  wedding_id: number
  wedding_title: string
  category_id: number
  category_name: string
  requirements: string
  guest_count: number | null
  due_date: string | null
  status: 'OPEN' | 'CLOSED'
  sent_at: string | null
  created_at: string
  invited_vendor_ids: number[]
  invited_vendors: RequestVendor[]
  received_count: number
  invited_count: number
  warnings?: string[]
}

export interface QuotationItem {
  id?: number
  description: string
  qty: number
  unit_price_paise: number
  total_paise?: number
}

export type QuotationStatus = 'RECEIVED' | 'SELECTED' | 'REJECTED'

export interface Quotation {
  id: number
  request_id: number
  vendor: { id: number; name: string }
  total_paise: number
  price_per_plate_paise: number | null
  implied_total_paise: number | null
  menu_notes: string
  valid_till: string | null
  file_url: string | null
  ai_extracted: boolean
  status: QuotationStatus
  items: QuotationItem[]
  created_at: string
}

export interface RequestDetail extends QuotationRequest {
  quotations: Quotation[]
}

export interface ComparedQuotation {
  id: number
  status: QuotationStatus
  vendor: { id: number; name: string; city: string; avg_rating: number | null; punctuality_pct: number | null }
  total_paise: number
  price_per_plate_paise: number | null
  implied_total_paise: number | null
  menu_notes: string
  valid_till: string | null
  file_url: string | null
  typed_by_hand: boolean
  score: number | null
  flags: { lowest_total: boolean; lowest_per_plate: boolean; expired: boolean; best_value: boolean }
}

export interface Comparison {
  request: { id: number; wedding_id: number; category: string; guest_count: number | null; status: string }
  weights: { price: number; rating: number; punctuality: number }
  quotations: ComparedQuotation[]
  item_rows: {
    key: string
    description: string
    values: ({ qty: number; unit_price_paise: number; total_paise: number } | null)[]
  }[]
}

/** The fields the AI reader may fill in. Everything is optional because the PDF may not have it all. */
export interface QuotationDraft {
  vendor_name?: string
  total_paise?: number
  price_per_plate_paise?: number
  menu_notes?: string
  valid_till?: string
  confidence?: number
  warnings?: string[]
  items?: { description?: string; qty?: number; quantity?: number; unit_price_paise?: number }[]
}
