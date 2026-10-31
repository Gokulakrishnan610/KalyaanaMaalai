export interface VendorCategory {
  id: number
  name: string
}

export interface Vendor {
  id: number
  name: string
  category_id: number
  category_name: string
  contact_person: string
  phone: string
  email: string
  city: string
  notes: string
  avg_rating: number | null
  weddings_count: number
  portal_account: 'none' | 'invited' | 'active'
  created_at: string
}

export interface Performance {
  avg_quality: number | null
  avg_pricing: number | null
  avg_punctuality_rating: number | null
  punctuality_pct: number | null
  avg_delay_min: number | null
  arrivals_counted: number
  ratings_count: number
  weddings_count: number
  score: number | null
}

export interface VendorProfile extends Vendor {
  weddings: {
    id: number
    title: string
    start_date: string
    status: string
    agreed_amount_paise: number
    quotation_id: number | null
  }[]
  ratings: {
    id: number
    wedding_id: number
    wedding_title: string
    punctuality: number
    quality: number
    pricing: number
    comment: string
  }[]
  quotations: {
    id: number
    request_id: number
    wedding_id: number
    wedding_title: string
    total_paise: number
    price_per_plate_paise: number | null
    status: 'RECEIVED' | 'SELECTED' | 'REJECTED'
    created_at: string
  }[]
  total_paid_paise: number
  performance: Performance
}

export interface WeddingVendor {
  id: number
  wedding_id: number
  vendor: { id: number; name: string }
  category: string
  agreed_amount_paise: number
  status: string
  quotation_id: number | null
  request_id: number | null
}
