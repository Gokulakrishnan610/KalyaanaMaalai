export type Source = 'CALL' | 'INSTAGRAM' | 'WHATSAPP' | 'REFERRAL' | 'WEBSITE'
export type Status = 'NEW' | 'CONTACTED' | 'CONSULTATION' | 'PROPOSAL' | 'WON' | 'LOST'

export interface Enquiry {
  id: number
  couple_name: string
  phone: string
  email: string
  source: Source
  status: Status
  wedding_date: string | null
  guest_count: number | null
  budget_paise: number | null
  venue_city: string
  consultation_at: string | null
  notes: string
  client: number | null
  client_name: string | null
  owner: number | null
  owner_name: string | null
  created_at: string
}

export const SOURCES: { value: Source; label: string; icon: string }[] = [
  { value: 'CALL', label: 'Phone call', icon: '📞' },
  { value: 'INSTAGRAM', label: 'Instagram', icon: '📷' },
  { value: 'WHATSAPP', label: 'WhatsApp', icon: '💬' },
  { value: 'REFERRAL', label: 'Referral', icon: '🤝' },
  { value: 'WEBSITE', label: 'Website', icon: '🌐' },
]

export const STATUSES: { value: Status; label: string; tone: 'gray' | 'blue' | 'amber' | 'brand' | 'green' | 'red' }[] = [
  { value: 'NEW', label: 'New', tone: 'gray' },
  { value: 'CONTACTED', label: 'Contacted', tone: 'blue' },
  { value: 'CONSULTATION', label: 'Consultation', tone: 'amber' },
  { value: 'PROPOSAL', label: 'Proposal sent', tone: 'brand' },
  { value: 'WON', label: 'Won', tone: 'green' },
  { value: 'LOST', label: 'Lost', tone: 'red' },
]

export const sourceInfo = (source: Source) => SOURCES.find((s) => s.value === source)!
export const statusInfo = (status: Status) => STATUSES.find((s) => s.value === status)!
