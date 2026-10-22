import { describe, it, expect, vi, beforeEach } from 'vitest'
import { api } from '@/api/client'

vi.mock('axios')

import axios from 'axios'
const mockedAxios = vi.mocked(axios)

describe('API Client', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockedAxios.create.mockReturnValue({
      get: vi.fn(),
      post: vi.fn(),
      delete: vi.fn(),
      interceptors: {
        request: { use: vi.fn() },
        response: { use: vi.fn() }
      }
    } as any)
  })

  it('creates axios instance with correct base URL', () => {
    expect(axios.create).toHaveBeenCalledWith(expect.objectContaining({
      baseURL: expect.stringContaining('8000')
    }))
  })

  it('login returns auth URL and state', async () => {
    const mockClient = mockedAxios.create.mock.results[0].value
    mockClient.get.mockResolvedValue({ data: { auth_url: 'http://auth', state: 'abc' } })

    const result = await api.login()

    expect(result).toEqual({ auth_url: 'http://auth', state: 'abc' })
    expect(mockClient.get).toHaveBeenCalledWith('/auth/login')
  })

  it('getMe calls /auth/me', async () => {
    const mockClient = mockedAxios.create.mock.results[0].value
    mockClient.get.mockResolvedValue({ data: { sub: '123', email: 'test@test.com' } })

    const result = await api.getMe()

    expect(result).toEqual({ sub: '123', email: 'test@test.com' })
  })

  it('listParts passes query params', async () => {
    const mockClient = mockedAxios.create.mock.results[0].value
    mockClient.get.mockResolvedValue({ data: { parts: [] } })

    await api.listParts(0, 10, 'ready')

    expect(mockClient.get).toHaveBeenCalledWith('/api/parts', { params: { skip: 0, limit: 10, status_filter: 'ready' } })
  })

  it('uploadPart uses FormData', async () => {
    const mockClient = mockedAxios.create.mock.results[0].value
    mockClient.post.mockResolvedValue({ data: { id: 1 } })

    const file = new File(['content'], 'test.step', { type: 'application/step' })
    const result = await api.upload(file)

    expect(result).toEqual({ id: 1 })
    expect(mockClient.post).toHaveBeenCalledWith('/api/parts', expect.any(FormData), expect.any(Object))
  })

  it('startUnfold posts correct payload', async () => {
    const mockClient = mockedAxios.create.mock.results[0].value
    mockClient.post.mockResolvedValue({ data: { job_id: 1, status: 'pending' } })

    const result = await api.startUnfold(1, 0.33, 0.1)

    expect(result).toEqual({ job_id: 1, status: 'pending' })
    expect(mockClient.post).toHaveBeenCalledWith('/api/parts/1/unfold', { k_factor: 0.33, kerf: 0.1, bend_table: undefined })
  })
})