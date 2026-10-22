import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export interface User {
  sub: string
  email: string
  username: string
  roles: string[]
}

export interface Part {
  id: number
  filename: string
  original_filename: string
  file_size: number
  status: 'uploaded' | 'processing' | 'ready' | 'failed'
  metadata: Record<string, unknown>
  created_at: string
}

export interface UnfoldJob {
  id: number
  part_id: number
  status: 'pending' | 'running' | 'completed' | 'failed'
  k_factor: number | null
  kerf: number
  created_at: string
  completed_at: string | null
  error_message: string | null
  result?: UnfoldResult
}

export interface BendRecord {
  bend_index: number
  angle_degrees: number
  direction: 'up' | 'down'
  inside_radius: number
  bend_allowance: number
  flange_length_side_a: number
  flange_length_side_b: number
  nearest_cut_distance: number
  bend_line_start: { x: number; y: number }
  bend_line_end: { x: number; y: number }
}

export interface UnfoldResult {
  profile_path: string
  bend_lines_path: string
  blank_area: number
  volume_conservation_ratio: number
  bend_count: number
  bends: BendRecord[]
}

interface AuthState {
  user: User | null
  accessToken: string | null
  isAuthenticated: boolean
  login: (user: User, token: string) => void
  logout: () void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      accessToken: null,
      isAuthenticated: false,
      login: (user, token) => set({ user, accessToken: token, isAuthenticated: true }),
      logout: () => set({ user: null, accessToken: null, isAuthenticated: false }),
    }),
    { name: 'auth-storage', partialize: (state) => ({ user: state.user, accessToken: state.accessToken, isAuthenticated: state.isAuthenticated }) }
  )
)

interface PartsState {
  parts: Part[]
  loading: boolean
  error: string | null
  setParts: (parts: Part[]) => void
  addPart: (part: Part) => void
  removePart: (id: number) => void
  setLoading: (loading: boolean) => void
  setError: (error: string | null) => void
}

export const usePartsStore = create<PartsState>((set) => ({
  parts: [],
  loading: false,
  error: null,
  setParts: (parts) => set({ parts }),
  addPart: (part) => set((state) => ({ parts: [part, ...state.parts] })),
  removePart: (id) => set((state) => ({ parts: state.parts.filter((p) => p.id !== id) })),
  setLoading: (loading) => set({ loading }),
  setError: (error) => set({ error }),
}))

interface UnfoldState {
  jobs: Record<number, UnfoldJob>
  setJob: (job: UnfoldJob) => void
  updateJob: (id: number, updates: Partial<UnfoldJob>) => void
}

export const useUnfoldStore = create<UnfoldState>((set) => ({
  jobs: {},
  setJob: (job) => set((state) => ({ jobs: { ...state.jobs, [job.id]: job } })),
  updateJob: (id, updates) => set((state) => ({ jobs: { ...state.jobs, [id]: { ...state.jobs[id], ...updates } } })),
}))