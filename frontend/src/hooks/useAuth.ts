import { useEffect, useCallback } from 'react'
import { useAuthStore } from '@/types/api'
import { getMe, logout as apiLogout } from '@/api/client'

export function useAuth() {
  const { user, accessToken, isAuthenticated, login, logout } = useAuthStore()

  const checkAuth = useCallback(async () => {
    if (!accessToken) return false
    try {
      const data = await getMe()
      login(data, accessToken)
      return true
    } catch {
      logout()
      return false
    }
  }, [accessToken, login, logout])

  useEffect(() => {
    // Check for token in URL hash (from OIDC callback)
    const hash = window.location.hash.substring(1)
    const params = new URLSearchParams(hash)
    const token = params.get('access_token')
    const state = params.get('state')

    if (token && state) {
      // Store token and fetch user
      useAuthStore.setState({ accessToken: token, isAuthenticated: true })
      // Clean up URL
      window.history.replaceState({}, document.title, window.location.pathname)
    }
  }, [])

  useEffect(() => {
    if (accessToken && !user) {
      checkAuth()
    }
  }, [accessToken, user, checkAuth])

  const handleLogout = useCallback(async () => {
    try {
      await apiLogout()
    } catch {
      // Ignore logout API errors
    }
    logout()
    window.location.href = '/'
  }, [logout])

  return { user, isAuthenticated, login, logout: handleLogout, checkAuth }
}