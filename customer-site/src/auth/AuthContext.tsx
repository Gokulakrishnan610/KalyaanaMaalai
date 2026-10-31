import { useQueryClient } from '@tanstack/react-query'
import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from 'react'
import { post, TOKEN_KEY } from '@/api/client'

export interface Portal {
  customer: { id: number; name: string; email: string; phone: string }
  stage: { key: string; step: number; label: string; hint: string; consultation_at: string | null }
  profile: {
    percent: number
    complete: boolean
    missing: string[]
    values: {
      partner_name: string
      wedding_date: string | null
      venue_city: string
      guest_count: number | null
      budget_paise: number | null
      functions_wanted: string[]
      services_needed: string[]
      preferred_contact: string
      notes: string
    }
  }
  is_client: boolean
}

interface AuthState {
  loggedIn: boolean
  signup: (body: { name: string; email: string; phone: string; password: string }) => Promise<Portal>
  login: (email: string, password: string) => Promise<Portal>
  logout: () => void
}

const AuthContext = createContext<AuthState | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient()
  const [loggedIn, setLoggedIn] = useState(() => Boolean(localStorage.getItem(TOKEN_KEY)))

  // the server answers sign-up and login with the token plus the first copy of the person's data
  const finish = useCallback(
    (res: Portal & { token: string }) => {
      localStorage.setItem(TOKEN_KEY, res.token)
      queryClient.setQueryData(['me'], res)
      setLoggedIn(true)
      return res
    },
    [queryClient],
  )

  const value = useMemo<AuthState>(
    () => ({
      loggedIn,
      signup: async (body) => finish(await post('/portal/signup/', body)),
      login: async (email, password) => finish(await post('/portal/login/', { email, password })),
      logout: () => {
        localStorage.removeItem(TOKEN_KEY)
        queryClient.clear()
        setLoggedIn(false)
      },
    }),
    [loggedIn, finish, queryClient],
  )
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

// eslint-disable-next-line react-refresh/only-export-components
export function useAuth(): AuthState {
  const context = useContext(AuthContext)
  if (!context) throw new Error('useAuth must be used inside AuthProvider')
  return context
}
