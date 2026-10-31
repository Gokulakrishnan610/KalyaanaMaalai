export interface VendorMe {
  vendor: { id: number; name: string; category: string; contact_person: string; phone: string; email: string; city: string; notes: string }
  rating: number | null
  ratings_count: number
}

export interface Booking {
  wedding: string
  city: string
  start_date: string
  end_date: string
  guest_count: number
  agreed_amount_paise: number
  schedule: { function: string; title: string; starts_at: string; ends_at: string; notes: string }[]
  arrivals: { function: string | null; expected_at: string; arrived_at: string | null; status: string; code: string }[]
}

export interface QuoteRequest {
  id: number
  wedding: string
  date: string
  city: string
  category: string
  requirements: string
  guest_count: number | null
  reply_by: string | null
  open: boolean
  my_quotation: { total_paise: number; price_per_plate_paise: number | null; menu_notes: string; valid_till: string | null; status: string } | null
}

export interface VendorPayments {
  bills: { id: number; wedding: string; description: string; amount_paise: number; paid_paise: number; remaining_paise: number; due_date: string | null; status: string }[]
  payments: { wedding: string; amount_paise: number; method: string; reference: string; paid_at: string }[]
}
