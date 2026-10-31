import { useQuery } from '@tanstack/react-query'
import { get } from '@/api/client'
import type { VendorCategory } from './types'

export function useVendorCategories() {
  return useQuery({ queryKey: ['vendor-categories'], queryFn: () => get<VendorCategory[]>('/vendor-categories/'), staleTime: 600_000 })
}
