export type Source = 'CALL' | 'INSTAGRAM' | 'WHATSAPP' | 'REFERRAL' | 'WEBSITE'
export type LostReason = 'BUDGET' | 'COMPETITOR' | 'DATE' | 'NO_RESPONSE' | 'OTHER'
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
  expected_revenue_paise: number | null
  win_chance: number
  priority: number
  expected_close_date: string | null
  lost_reason: LostReason | ''
  next_follow_up: string | null
  partner_name: string
  functions_wanted: string[]
  services_needed: string[]
  preferred_contact: string
  profile_complete: boolean
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

export const LOST_REASONS: { value: LostReason; label: string }[] = [
  { value: 'BUDGET', label: 'Budget too low' },
  { value: 'COMPETITOR', label: 'Chose another planner' },
  { value: 'DATE', label: 'Date not available' },
  { value: 'NO_RESPONSE', label: 'No response' },
  { value: 'OTHER', label: 'Other' },
]

/** How likely a couple is to book at each stage (same numbers as the backend). */
export const STAGE_WIN_CHANCE: Record<Status, number> = {
  NEW: 10,
  CONTACTED: 20,
  CONSULTATION: 40,
  PROPOSAL: 60,
  WON: 100,
  LOST: 0,
}

export interface FollowUp {
  id: number
  enquiry: number
  enquiry_name: string
  kind: 'CALL' | 'MEETING' | 'WHATSAPP' | 'EMAIL' | 'TODO'
  summary: string
  due_at: string
  done_at: string | null
  is_overdue: boolean
}

export const FOLLOW_UP_KINDS: { value: FollowUp['kind']; label: string; icon: string }[] = [
  { value: 'CALL', label: 'Call', icon: '📞' },
  { value: 'MEETING', label: 'Meeting', icon: '🤝' },
  { value: 'WHATSAPP', label: 'WhatsApp', icon: '💬' },
  { value: 'EMAIL', label: 'Email', icon: '✉️' },
  { value: 'TODO', label: 'To do', icon: '✅' },
]

/** The couple's own answers from the customer website (labels for the codes the backend stores). */
export const WEBSITE_SERVICES: Record<string, string> = {
  VENUE: 'Venue', CATERING: 'Catering', DECOR: 'Decor and stage', PHOTOGRAPHY: 'Photo and video', MAKEUP: 'Makeup',
  MUSIC: 'Music and DJ', MEHENDI: 'Mehendi', INVITATIONS: 'Invitations', TRANSPORT: 'Transport', STAY: 'Guest stay',
}
export const WEBSITE_FUNCTIONS: Record<string, string> = {
  ENGAGEMENT: 'Engagement', MEHENDI: 'Mehendi', HALDI: 'Haldi', SANGEET: 'Sangeet', WEDDING: 'Wedding', RECEPTION: 'Reception',
}
export const CONTACT_LABELS: Record<string, string> = { CALL: 'Phone call', WHATSAPP: 'WhatsApp', EMAIL: 'Email' }
