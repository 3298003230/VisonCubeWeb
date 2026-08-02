import { apiRequest } from './client'
import type {
  AuthSession,
  AuthUser,
  MessageResponse,
  PasswordCredentials,
  RegisterCredentials,
} from './types'

export const login = (credentials: PasswordCredentials) =>
  apiRequest<AuthSession>('/api/auth/login', { method: 'POST', body: credentials })

export const register = (credentials: RegisterCredentials) =>
  apiRequest<AuthSession>('/api/auth/register', { method: 'POST', body: credentials })

export const me = (token: string) => apiRequest<AuthUser>('/api/auth/me', { token })

export const requestEmailLoginCode = (email: string) =>
  apiRequest<MessageResponse>('/api/auth/email-login/request', {
    method: 'POST',
    body: { email },
  })

export const confirmEmailLogin = (email: string, code: string) =>
  apiRequest<AuthSession>('/api/auth/email-login/confirm', {
    method: 'POST',
    body: { email, code },
  })

export const requestPasswordResetCode = (email: string) =>
  apiRequest<MessageResponse>('/api/auth/password-reset/request', {
    method: 'POST',
    body: { email },
  })

export const confirmPasswordReset = (email: string, code: string, newPassword: string) =>
  apiRequest<AuthSession>('/api/auth/password-reset/confirm', {
    method: 'POST',
    body: { email, code, new_password: newPassword },
  })

export const requestEmailBindingCode = (token: string, email: string) =>
  apiRequest<MessageResponse>('/api/auth/email/bind/request', {
    method: 'POST',
    token,
    body: { email },
  })

export const updateEmail = (token: string, email: string, code: string) =>
  apiRequest<AuthUser>('/api/auth/email', {
    method: 'PUT',
    token,
    body: { email, code },
  })

export const changePassword = (token: string, oldPassword: string, newPassword: string) =>
  apiRequest<AuthSession>('/api/auth/change-password', {
    method: 'POST',
    token,
    body: { old_password: oldPassword, new_password: newPassword },
  })

export const logout = (token: string) =>
  apiRequest<MessageResponse>('/api/auth/logout', { method: 'POST', token })
