import { defineStore } from 'pinia'
import { ref } from 'vue'
import { api } from '../api/client'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('token') ?? '')
  const displayName = ref(localStorage.getItem('displayName') ?? '')
  const role = ref(localStorage.getItem('role') ?? '')

  async function login(username: string, password: string) {
    const { data } = await api.post('/auth/login', { username, password })
    token.value = data.access_token
    displayName.value = data.display_name
    role.value = data.role
    localStorage.setItem('token', data.access_token)
    localStorage.setItem('displayName', data.display_name)
    localStorage.setItem('role', data.role)
  }

  function logout() {
    token.value = ''
    displayName.value = ''
    role.value = ''
    localStorage.removeItem('token')
    localStorage.removeItem('displayName')
    localStorage.removeItem('role')
  }

  return { token, displayName, role, login, logout }
})
