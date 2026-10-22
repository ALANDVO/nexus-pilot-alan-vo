import axios, { AxiosInstance, AxiosError } from 'axios'
import { useAuthStore } from '@/types/api'

const API_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'

class ApiClient {
  private client: AxiosInstance

  constructor() {
    this.client = axios.create({
      baseURL: API_URL,
      headers: { 'Content-Type': 'application/json' },
      timeout: 30000,
    })

    this.client.interceptors.request.use((config) => {
      const token = useAuthStore.getState().accessToken
      if (token) {
        config.headers.Authorization = `Bearer ${token}`
      }
      return config
    })

    this.client.interceptors.response.use(
      (response) => response,
      (error: AxiosError) => {
        if (error.response?.status === 401) {
          useAuthStore.getState().logout()
          window.location.href = '/login'
        }
        return Promise.reject(error)
      }
    )
  }

  async get<T>(url: string, params?: Record<string, unknown>) {
    return this.client.get<T>(url, { params })
  }

  async post<T>(url: string, data?: unknown) {
    return this.client.post<T>(url, data)
  }

  async delete<T>(url: string) {
    return this.client.delete<T>(url)
  }

  async upload<T>(url: string, file: File, onProgress?: (progress: number) => void) {
    const formData = new FormData()
    formData.append('file', file)
    return this.client.post<T>(url, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: (e) => {
        if (e.total && onProgress) onProgress(Math.round((e.loaded * 100) / e.total))
      },
    })
  }

  async download(url: string, filename: string) {
    const response = await this.client.get(url, { responseType: 'blob' })
    const blob = new Blob([response.data])
    const link = document.createElement('a')
    link.href = URL.createObjectURL(blob)
    link.download = filename
    link.click()
    URL.revokeObjectURL(link.href)
  }
}

export const api = new ApiClient()

export async function login(): Promise<{ auth_url: string; state: string }> {
  const response = await api.get<{ auth_url: string; state: string }>('/auth/login')
  return response.data
}

export async function getMe() {
  const response = await api.get('/auth/me')
  return response.data
}

export async function listParts(skip = 0, limit = 20, status?: string) {
  const response = await api.get('/api/parts', { skip, limit, status_filter: status })
  return response.data
}

export async function uploadPart(file: File, onProgress?: (p: number) => void) {
  const response = await api.upload('/api/parts', file, onProgress)
  return response.data
}

export async function getPart(id: number) {
  const response = await api.get(`/api/parts/${id}`)
  return response.data
}

export async function deletePart(id: number) {
  await api.delete(`/api/parts/${id}`)
}

export async function startUnfold(partId: number, kFactor = 0.33, kerf = 0.0, bendTable?: Record<string, unknown>) {
  const response = await api.post(`/api/parts/${partId}/unfold`, { k_factor: kFactor, kerf, bend_table: bendTable })
  return response.data
}

export async function getUnfoldResult(partId: number, jobId: number) {
  const response = await api.get(`/api/parts/${partId}/unfold/${jobId}`)
  return response.data
}

export async function downloadUnfoldProfile(partId: number, jobId: number) {
  await api.download(`/api/parts/${partId}/unfold/${jobId}/profile`, `unfold_${jobId}_profile.dxf`)
}

export async function downloadUnfoldBendLines(partId: number, jobId: number) {
  await api.download(`/api/parts/${partId}/unfold/${jobId}/bendlines`, `unfold_${jobId}_bendlines.dxf`)
}

export async function logout() {
  await api.post('/auth/logout')
}