import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { Spinner } from '@/components/common'
import { useLogin, type Role } from '@/login/LoginContext'

/** Wrap pages that need a logged-in user. Pass `roles` to limit them to certain roles. */
export function RequireLogin({ roles }: { roles?: Role[] }) {
  const { user, loading, hasRole } = useLogin()
  const location = useLocation()

  if (loading) return <Spinner />
  if (!user) return <Navigate to="/login" replace state={{ from: location.pathname }} />
  if (roles && !hasRole(...roles)) return <Navigate to="/" replace />
  return <Outlet />
}
