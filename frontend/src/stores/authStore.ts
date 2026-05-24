import { create } from 'zustand'

interface User {
  id: string
  id_card: string
  phone: string
  name: string
  role: 'guest' | 'front_desk' | 'manager' | 'admin'
  is_first_login: boolean
}

interface AuthState {
  accessToken: string | null
  refreshToken: string | null
  user: User | null
  login: (access: string, refresh: string) => void
  setUser: (user: User) => void
  logout: () => void
}

export const useAuthStore = create<AuthState>((set) => ({
  accessToken: localStorage.getItem('access_token'),
  refreshToken: localStorage.getItem('refresh_token'),
  user: null,
  login: (access, refresh) => {
    localStorage.setItem('access_token', access)
    localStorage.setItem('refresh_token', refresh)
    set({ accessToken: access, refreshToken: refresh })
  },
  setUser: (user) => set({ user }),
  logout: () => {
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    set({ accessToken: null, refreshToken: null, user: null })
  },
}))
