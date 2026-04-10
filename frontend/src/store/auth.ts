import { create } from 'zustand'

interface UserInfo {
  id: number
  username: string
  real_name?: string
  role_id?: number
}

interface AuthStore {
  token: string | null
  user: UserInfo | null
  setToken: (token: string) => void
  setUser: (user: UserInfo) => void
  logout: () => void
}

export const useAuthStore = create<AuthStore>((set) => ({
  token: localStorage.getItem('token'),
  user: null,
  setToken: (token) => {
    localStorage.setItem('token', token)
    set({ token })
  },
  setUser: (user) => set({ user }),
  logout: () => {
    localStorage.removeItem('token')
    set({ token: null, user: null })
  },
}))
