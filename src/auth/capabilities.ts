import { reactive, readonly } from 'vue'
import { ApiError } from '../api/client'
import { getLicenseAdminOverview } from '../api/licenses'
import { authState } from './session'

type CapabilityStatus = 'idle' | 'loading' | 'ready'

interface CapabilityState {
  status: CapabilityStatus
  canManageLicenses: boolean
  error: string
}

const state = reactive<CapabilityState>({
  status: 'idle',
  canManageLicenses: false,
  error: '',
})

let loadedToken = ''
let pending: Promise<void> | null = null

export const licenseCapabilities = readonly(state)

const reset = () => {
  loadedToken = ''
  state.status = 'idle'
  state.canManageLicenses = false
  state.error = ''
}

export const ensureLicenseCapabilities = async (force = false) => {
  const session = authState.session
  if (!session) {
    reset()
    return
  }

  if (!force && loadedToken === session.token && state.status === 'ready') return
  if (pending) return pending

  const token = session.token
  loadedToken = token
  state.status = 'loading'
  state.error = ''

  pending = getLicenseAdminOverview(token)
    .then(() => {
      if (loadedToken !== token) return
      state.canManageLicenses = true
    })
    .catch((error: unknown) => {
      if (loadedToken !== token) return
      state.canManageLicenses = false
      state.error = error instanceof ApiError && error.status < 500
        ? ''
        : error instanceof Error
          ? error.message
          : '授权能力暂时无法确认'
    })
    .finally(() => {
      if (loadedToken === token) state.status = 'ready'
      pending = null
    })

  return pending
}

