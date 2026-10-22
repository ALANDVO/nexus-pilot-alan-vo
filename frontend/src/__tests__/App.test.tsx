import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import { Login } from '@/components/Login'
import { useAuthStore } from '@/types/api'
import * as api from '@/api/client'

vi.mock('@/api/client')
vi.mock('@/types/api', async () => {
  const actual = await vi.importActual('@/types/api')
  return {
    ...actual,
    useAuthStore: vi.fn()
  }
})

describe('Login', () => {
  const mockLogin = vi.fn()
  const mockSetState = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
    ;(useAuthStore as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
      login: mockLogin,
      logout: vi.fn(),
      user: null,
      accessToken: null,
      isAuthenticated: false
    })
  })

  it('renders login button', () => {
    render(
      <BrowserRouter>
        <Login />
      </BrowserRouter>
    )
    expect(screen.getByRole('button', { name: /sign in with keycloak/i })).toBeInTheDocument()
  })

  it('calls API login on button click', async () => {
    const mockAuthUrl = 'http://keycloak/auth?state=abc'
    ;(api.login as vi.Mock).mockResolvedValue({ auth_url: mockAuthUrl, state: 'abc' })

    render(
      <BrowserRouter>
        <Login />
      </BrowserRouter>
    )

    fireEvent.click(screen.getByRole('button', { name: /sign in with keycloak/i }))

    await waitFor(() => {
      expect(api.login).toHaveBeenCalled()
    })
  })

  it('shows error on login failure', async () => {
    ;(api.login as vi.Mock).mockRejectedValue(new Error('Network error'))

    render(
      <BrowserRouter>
        <Login />
      </BrowserRouter>
    )

    fireEvent.click(screen.getByRole('button', { name: /sign in with keycloak/i }))

    await waitFor(() => {
      expect(screen.getByText(/network error/i)).toBeInTheDocument()
    })
  })
})