import { useQuery } from '@tanstack/react-query'
import { get } from '@/api/client'

export type WeddingStatus = 'PLANNING' | 'CONFIRMED' | 'COMPLETED' | 'CANCELLED'
export type Stage = 'TO_PLAN' | 'IN_PROGRESS' | 'READY' | 'DONE'
export type Priority = 'LOW' | 'MEDIUM' | 'HIGH'

export interface Wedding {
  id: number
  title: string
  client: number
  client_name: string
  start_date: string
  end_date: string
  city: string
  guest_count: number
  contracted_guests: number
  per_guest_rate_paise: number
  budget_paise: number
  status: WeddingStatus
  progress_pct: number
  next_function_date: string | null
}

export interface WeddingFunction {
  id: number
  wedding: number
  name: string
  starts_at: string
  ends_at: string
  venue: number | null
  venue_name: string | null
  guest_count: number | null
}

export interface TeamMember {
  id: number
  user_id: number
  user_name: string
  role_label: string
}

export interface WeddingDetail extends Wedding {
  functions: WeddingFunction[]
  assignments: TeamMember[]
  task_counts: Record<Stage, number>
}

export interface Task {
  id: number
  wedding: number
  function: number | null
  function_name: string | null
  title: string
  description: string
  assigned_to: number | null
  assignee_name: string | null
  due_date: string | null
  stage: Stage
  priority: Priority
  category: string
  position: number
  is_overdue: boolean
}

export interface ScheduleItem {
  id: number
  function: number
  starts_at: string
  ends_at: string
  title: string
  responsible: number | null
  responsible_name: string | null
  vendor: number | null
  vendor_name: string | null
  notes: string
  warnings?: string[]
}

export interface Checkin {
  id: number
  vendor: number
  vendor_name: string
  function: number | null
  function_name: string | null
  scheduled_arrival: string
  actual_arrival: string | null
  grace_minutes: number
  status: 'PENDING' | 'ON_TIME' | 'LATE'
  delay_minutes: number | null
  token: string
  public_path: string
}

export interface StaffUser {
  id: number
  name: string
  role: string
}

export const ROLE_LABELS: Record<string, string> = {
  LEAD_PLANNER: 'Lead planner',
  COORDINATOR: 'Coordinator',
  DECOR_LEAD: 'Decor lead',
  VENDOR_LEAD: 'Vendor lead',
}

export const STAGES: { value: Stage; label: string }[] = [
  { value: 'TO_PLAN', label: 'To plan' },
  { value: 'IN_PROGRESS', label: 'In progress' },
  { value: 'READY', label: 'Ready' },
  { value: 'DONE', label: 'Done' },
]

export const WEDDING_STATUSES: { value: WeddingStatus; label: string; tone: 'gray' | 'blue' | 'green' | 'red' }[] = [
  { value: 'PLANNING', label: 'Planning', tone: 'blue' },
  { value: 'CONFIRMED', label: 'Confirmed', tone: 'green' },
  { value: 'COMPLETED', label: 'Completed', tone: 'gray' },
  { value: 'CANCELLED', label: 'Cancelled', tone: 'red' },
]

/** Staff list for dropdowns. Staff-role users may not read /users/, so an error just gives an empty list. */
export function useStaffUsers() {
  return useQuery({
    queryKey: ['users'],
    queryFn: () => get<StaffUser[]>('/users/').catch(() => [] as StaffUser[]),
    staleTime: 5 * 60_000,
  })
}

export function initials(name: string | null | undefined): string {
  return (name ?? '?')
    .split(/\s+/)
    .map((part) => part[0])
    .join('')
    .slice(0, 2)
    .toUpperCase()
}

export function formatTime(iso: string | null | undefined): string {
  if (!iso) return '-'
  return new Date(iso).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' })
}
