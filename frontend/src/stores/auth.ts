import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

import { apiRequest } from '../services/api'
import type { AuthResponse, User } from '../types/auth'

interface LoginPayload {
  identifier: string
  password: string
}

interface RegisterPayload {
  full_name: string
  email?: string
  phone?: string
  password: string
}

export const useAuthStore = defineStore('auth', () => {
  const accessToken = ref<string | null>(null)
  const user = ref<User | null>(null)
  const isAuthenticated = computed(() => Boolean(accessToken.value && user.value))

  function applyAuth(data: AuthResponse) {
    accessToken.value = data.access_token
    user.value = data.user
  }

  async function login(payload: LoginPayload) {
    applyAuth(await apiRequest<AuthResponse>('/auth/login', { method: 'POST', body: JSON.stringify(payload) }))
  }

  async function register(payload: RegisterPayload) {
    applyAuth(await apiRequest<AuthResponse>('/auth/register', { method: 'POST', body: JSON.stringify(payload) }))
  }

  async function restoreSession() {
    try {
      applyAuth(await apiRequest<AuthResponse>('/auth/refresh', { method: 'POST' }))
    } catch {
      accessToken.value = null
      user.value = null
    }
  }

  async function logout() {
    await apiRequest<void>('/auth/logout', { method: 'POST' }, accessToken.value ?? undefined).catch(() => undefined)
    accessToken.value = null
    user.value = null
  }

  return { accessToken, user, isAuthenticated, login, register, restoreSession, logout }
})
