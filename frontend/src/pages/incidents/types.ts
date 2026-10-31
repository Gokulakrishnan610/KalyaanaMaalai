export type Severity = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL'
export type IncidentStatus = 'OPEN' | 'ASSIGNED' | 'IN_PROGRESS' | 'RESOLVED'

export interface Incident {
  id: number
  wedding: number
  wedding_title: string
  vendor: number | null
  vendor_name: string
  title: string
  description: string
  severity: Severity
  status: IncidentStatus
  is_open: boolean
  reported_by: number | null
  reported_by_name: string
  assigned_to: number | null
  assigned_to_name: string
  created_at: string
  updated_at: string
  resolved_at: string | null
}

export interface IncidentDetail extends Incident {
  updates: { id: number; author_name: string; message: string; created_at: string }[]
}

export const SEVERITIES: { value: Severity; label: string; tone: 'gray' | 'amber' | 'red' | 'brand' }[] = [
  { value: 'LOW', label: 'Low', tone: 'gray' },
  { value: 'MEDIUM', label: 'Medium', tone: 'amber' },
  { value: 'HIGH', label: 'High', tone: 'brand' },
  { value: 'CRITICAL', label: 'Critical', tone: 'red' },
]

export const STATUSES: { value: IncidentStatus; label: string; tone: 'gray' | 'blue' | 'amber' | 'green' }[] = [
  { value: 'OPEN', label: 'Open', tone: 'gray' },
  { value: 'ASSIGNED', label: 'Assigned', tone: 'blue' },
  { value: 'IN_PROGRESS', label: 'In progress', tone: 'amber' },
  { value: 'RESOLVED', label: 'Resolved', tone: 'green' },
]

export const severityInfo = (s: Severity) => SEVERITIES.find((x) => x.value === s)!
export const statusInfo = (s: IncidentStatus) => STATUSES.find((x) => x.value === s)!
