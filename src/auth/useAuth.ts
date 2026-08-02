import { computed } from 'vue'
import {
  authState,
  changePassword,
  confirmEmailBinding,
  ensureSessionRestored,
  hasVerifiedEmail,
  loginWithEmailCode,
  loginWithPassword,
  registerAccount,
  requestEmailBindingCode,
  requestEmailLoginCode,
  requestPasswordResetCode,
  resetPassword,
  signOut,
} from './session'

export const useAuth = () => ({
  state: authState,
  user: computed(() => authState.session?.user ?? null),
  isAuthenticated: computed(() => Boolean(authState.session && hasVerifiedEmail(authState.session.user))),
  ensureSessionRestored,
  loginWithPassword,
  loginWithEmailCode,
  registerAccount,
  requestEmailLoginCode,
  requestPasswordResetCode,
  resetPassword,
  requestEmailBindingCode,
  confirmEmailBinding,
  changePassword,
  signOut,
})
