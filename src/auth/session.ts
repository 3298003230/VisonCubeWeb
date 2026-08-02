import { reactive, readonly } from 'vue'
import * as authApi from '../api/auth'
import { ApiError } from '../api/client'
import type { AuthSession, AuthUser, PasswordCredentials, RegisterCredentials } from '../api/types'

const STORAGE_KEY = 'visoncube.web.auth-session'
const EXPIRY_SAFETY_WINDOW_MS = 60_000

export type AuthStatus =
  | 'restoring'
  | 'signed_out'
  | 'email_verification'
  | 'authenticated'
  | 'restore_error'

interface AuthState {
  status: AuthStatus
  session: AuthSession | null
  restoreError: string
}

const state = reactive<AuthState>({
  status: 'restoring',
  session: null,
  restoreError: '',
})

let restorePromise: Promise<void> | null = null

export const authState = readonly(state)

export const hasVerifiedEmail = (user: AuthUser) =>
  Boolean(user.email?.trim() && user.email_verified_at?.trim())

const statusForSession = (session: AuthSession): AuthStatus =>
  hasVerifiedEmail(session.user) ? 'authenticated' : 'email_verification'

const isSessionShape = (value: unknown): value is AuthSession => {
  if (!value || typeof value !== 'object') return false
  const candidate = value as Partial<AuthSession>
  return Boolean(
    candidate.token
      && typeof candidate.token === 'string'
      && candidate.user
      && typeof candidate.user.username === 'string',
  )
}

const isSessionUsable = (session: AuthSession) => {
  if (!session.token || !session.user.username) return false
  if (!session.expires_at_ms || session.expires_at_ms <= 0) return true
  return Date.now() + EXPIRY_SAFETY_WINDOW_MS < session.expires_at_ms
}

const saveStoredSession = (session: AuthSession) => {
  try {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(session))
  } catch {
    // 浏览器禁用会话存储时，当前页面仍可继续使用内存中的登录状态。
  }
}

const clearStoredSession = () => {
  try {
    sessionStorage.removeItem(STORAGE_KEY)
  } catch {
    // 清理失败不能阻止当前页面退出登录。
  }
}

const readStoredSession = () => {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY)
    if (!raw) return null
    const session = JSON.parse(raw) as unknown
    return isSessionShape(session) ? session : null
  } catch {
    return null
  }
}

const setSession = (session: AuthSession) => {
  state.session = session
  state.status = statusForSession(session)
  state.restoreError = ''
  saveStoredSession(session)
  return session
}

const clearSession = () => {
  state.session = null
  state.status = 'signed_out'
  state.restoreError = ''
  clearStoredSession()
}

const restore = async () => {
  state.status = 'restoring'
  state.restoreError = ''

  const storedSession = readStoredSession()
  if (!storedSession || !isSessionUsable(storedSession)) {
    clearSession()
    return
  }

  try {
    const user = await authApi.me(storedSession.token)
    setSession({ ...storedSession, user })
  } catch (error) {
    if (error instanceof ApiError && error.status === 401) {
      clearSession()
      return
    }

    state.session = storedSession
    state.status = 'restore_error'
    state.restoreError = error instanceof Error ? error.message : '暂时无法验证登录状态'
  }
}

export const ensureSessionRestored = (force = false) => {
  if (!force && state.status !== 'restoring') return Promise.resolve()
  if (restorePromise) return restorePromise

  restorePromise = restore().finally(() => {
    restorePromise = null
  })
  return restorePromise
}

export const loginWithPassword = async (credentials: PasswordCredentials) =>
  setSession(await authApi.login(credentials))

export const registerAccount = async (credentials: RegisterCredentials) =>
  setSession(await authApi.register(credentials))

export const requestEmailLoginCode = (email: string) => authApi.requestEmailLoginCode(email)

export const loginWithEmailCode = async (email: string, code: string) =>
  setSession(await authApi.confirmEmailLogin(email, code))

export const requestPasswordResetCode = (email: string) => authApi.requestPasswordResetCode(email)

export const resetPassword = async (email: string, code: string, newPassword: string) =>
  setSession(await authApi.confirmPasswordReset(email, code, newPassword))

const requireSession = () => {
  if (!state.session || !isSessionUsable(state.session)) {
    clearSession()
    throw new ApiError(401, '登录状态已失效，请重新登录')
  }
  return state.session
}

export const requestEmailBindingCode = (email: string) => {
  const session = requireSession()
  return authApi.requestEmailBindingCode(session.token, email)
}

export const confirmEmailBinding = async (email: string, code: string) => {
  const session = requireSession()
  const user = await authApi.updateEmail(session.token, email, code)
  setSession({ ...session, user })
  return user
}

export const changePassword = async (oldPassword: string, newPassword: string) => {
  const session = requireSession()
  return setSession(await authApi.changePassword(session.token, oldPassword, newPassword))
}

export const signOut = async () => {
  const session = state.session
  clearSession()
  if (!session || !isSessionUsable(session)) return

  try {
    await authApi.logout(session.token)
  } catch {
    // 本地会话已经清除，服务端撤销失败不应阻止用户退出当前设备。
  }
}
