import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import { get, post, TOKEN_KEY } from '@/api/client'

export type Role = 'FOUNDER' | 'PLANNER' | 'STAFF'

export interface User {
  id: number
  name: string
  email: string
  role: Role
}

interface LoginState {
  user: User | null
  loading: boolean
  login: (email: string, password: string) => Promise<void>
  logout: () => void
  /** True if the user has one of these roles. The founder can do everything. */
  hasRole: (...roles: Role[]) => boolean
}

const LoginContext = createContext<LoginState | null>(null)

export function LoginProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(() => Boolean(localStorage.getItem(TOKEN_KEY)))

  // if a token is saved from an earlier visit, find out who it belongs to
  useEffect(() => {
    if (!localStorage.getItem(TOKEN_KEY)) return
    get<User>('/auth/me/')
      .then(setUser)
      .catch(() => localStorage.removeItem(TOKEN_KEY))
      .finally(() => setLoading(false))
  }, [])

  const login = useCallback(async (email: string, password: string) => {
    const res = await post<{ access: string; user: User }>('/auth/login/', { email, password })
    localStorage.setItem(TOKEN_KEY, res.access)
    setUser(res.user)
  }, [])

  const logout = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY)
    setUser(null)
  }, [])

  const value = useMemo<LoginState>(
    () => ({
      user,
      loading,
      login,
      logout,
      hasRole: (...roles) => !!user && (user.role === 'FOUNDER' || roles.includes(user.role)),
    }),
    [user, loading, login, logout],
  )

  return <LoginContext.Provider value={value}>{children}</LoginContext.Provider>
}

// eslint-disable-next-line react-refresh/only-export-components
export function useLogin(): LoginState {
  const context = useContext(LoginContext)
  if (!context) throw new Error('useLogin must be used inside LoginProvider')
  return context
}
