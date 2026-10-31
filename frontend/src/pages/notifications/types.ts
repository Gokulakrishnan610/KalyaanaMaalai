export type Severity = 'info' | 'warning' | 'critical'

export interface AppNotification {
  id: number
  message: string
  severity: Severity
  channel: string
  created_at: string
  is_read: boolean
}

export interface NotificationList {
  unread_count: number
  results: AppNotification[]
}

export const SEVERITY_DOT: Record<Severity, string> = {
  info: 'bg-sky-500',
  warning: 'bg-amber-500',
  critical: 'bg-red-500',
}
