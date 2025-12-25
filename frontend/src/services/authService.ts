import api from './api'
import type { User } from '../types'

interface LoginResponse {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
}

interface LoginRequest {
  email: string
  password: string
}

export const authService = {
  async login(data: LoginRequest): Promise<{ user: User; tokens: LoginResponse }> {
    const response = await api.post<LoginResponse>('/auth/login', data)
    const tokens = response.data

    // Set token temporarily to get user info
    api.defaults.headers.common['Authorization'] = `Bearer ${tokens.access_token}`

    const userResponse = await api.get<User>('/auth/me')

    return {
      user: userResponse.data,
      tokens,
    }
  },

  async getCurrentUser(): Promise<User> {
    const response = await api.get<User>('/auth/me')
    return response.data
  },

  async changePassword(currentPassword: string, newPassword: string): Promise<void> {
    await api.post('/auth/change-password', {
      current_password: currentPassword,
      new_password: newPassword,
    })
  },

  async register(data: {
    email: string
    password: string
    first_name: string
    last_name?: string
    organization_name: string
    organization_type: string
  }): Promise<LoginResponse> {
    const response = await api.post<LoginResponse>('/auth/register', data)
    return response.data
  },
}
