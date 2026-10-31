import { useQueryClient } from '@tanstack/react-query'
import { api } from '@/api/client'

/** A fresh key per payment attempt. The server returns the first payment again if the same key arrives twice. */
export function newIdempotencyKey(): string {
  return globalThis.crypto?.randomUUID?.() ?? `${Date.now()}-${Math.random().toString(16).slice(2)}`
}

export async function postWithKey<T>(url: string, body: unknown, key: string): Promise<T> {
  return (await api.post<T>(url, body, { headers: { 'Idempotency-Key': key } })).data
}

/** Refresh every money number after a change (the dashboard and client pages show the same figures). */
export function useRefreshMoney() {
  const queryClient = useQueryClient()
  return () =>
    Promise.all(
      ['finance', 'finance-overview', 'dashboard', 'clients', 'notifications'].map((key) =>
        queryClient.invalidateQueries({ queryKey: [key] }),
      ),
    )
}

/** "12,500" for a rupee amount typed in a box, from whole paise. */
export function rupeeText(paise: number): string {
  return paise % 100 === 0 ? String(paise / 100) : (paise / 100).toFixed(2)
}

/** The public address a customer opens, built from where this website is running. */
export function linkUrl(path: string): string {
  return `${window.location.origin}${path}`
}
