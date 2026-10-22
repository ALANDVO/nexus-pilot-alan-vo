import { useEffect, useState } from 'react'
import { login as apiLogin } from '@/api/client'
import { useAuthStore } from '@/types/api'

export function Login() {
  const { login } = useAuthStore()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleLogin = async () => {
    setLoading(true)
    setError(null)
    try {
      const { auth_url } = await apiLogin()
      window.location.href = auth_url
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Login failed')
      setLoading(false)
    }
  }

  useEffect(() => {
    // Check if returning from OIDC callback with token in hash
    const hash = window.location.hash.substring(1)
    const params = new URLSearchParams(hash)
    const token = params.get('access_token')
    const state = params.get('state')

    if (token && state) {
      // Token will be picked up by useAuth hook
      window.history.replaceState({}, document.title, window.location.pathname)
    }
  }, [])

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50">
      <div className="card w-full max-w-md">
        <div className="text-center mb-8">
          <h1 className="text-2xl font-bold text-slate-900">nexus-pilot</h1>
          <p className="text-slate-500 mt-1">Give your agent CAD superpowers</p>
        </div>

        {error && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 text-red-700 rounded-lg text-sm">
            {error}
          </div>
        )}

        <button
          onClick={handleLogin}
          disabled={loading}
          className="btn btn-primary w-full py-3"
        >
          {loading ? 'Redirecting...' : 'Sign in with Keycloak'}
        </button>

        <p className="text-center text-sm text-slate-500 mt-6">
          Authenticates via Keycloak OIDC with PKCE
        </p>
      </div>
    </div>
  )
}