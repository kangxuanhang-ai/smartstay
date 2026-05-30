import { useEffect } from 'react'
import { Spin } from 'antd'
import { Navigate } from 'react-router-dom'
import { useAuthStore } from '../stores/authStore'
import apiClient from '../api/client'

export default function AuthGuard({ children }: { children: React.ReactNode }) {
  const user = useAuthStore((s) => s.user)
  const token = useAuthStore((s) => s.accessToken)
  const setUser = useAuthStore((s) => s.setUser)
  const logout = useAuthStore((s) => s.logout)

  useEffect(() => {
    if (token && !user) {
      apiClient.get('/api/auth/me')
        .then(({ data }) => setUser(data))
        .catch(() => logout())
    }
  }, [token, user, setUser, logout])

  if (!token) return <Navigate to="/login" />
  if (!user) return <div className="min-h-screen flex items-center justify-center"><Spin size="large" description="加载中..." /></div>

  return <>{children}</>
}
