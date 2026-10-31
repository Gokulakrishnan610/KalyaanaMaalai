import { useQueryClient } from '@tanstack/react-query'
import { api } from '@/api/client'

/** A fresh key per payment attempt. The server returns the first payment again if the same key arrives twice. */
export function newIdempotencyKey(): string {
  return globalThis.crypto?.randomUUID?.() ?? `${Date.now()}-${Math.random().toString(16).slice(2)}`
}

export async function postWithKey<T>(url: string, body: unknown, key: string): Promise<T> {
  return (await api.post<T>(url, body, { headers: { 'Idempotency-Key': key } })).data
}

/** Refresh every finance number after a change (the dashboard shows the same figures). */
export function useRefreshFinance(weddingId: number) {
  const queryClient = useQueryClient()
  return () =>
    Promise.all([
      queryClient.invalidateQueries({ queryKey: ['finance', weddingId] }),
      queryClient.invalidateQueries({ queryKey: ['finance-overview'] }),
      queryClient.invalidateQueries({ queryKey: ['upcoming-payments'] }),
      queryClient.invalidateQueries({ queryKey: ['dashboard'] }),
      queryClient.invalidateQueries({ queryKey: ['notifications'] }),
    ])
}

/** "12,500" for a rupee amount typed in a box, from whole paise. */
export function rupeeText(paise: number): string {
  return paise % 100 === 0 ? String(paise / 100) : (paise / 100).toFixed(2)
}
