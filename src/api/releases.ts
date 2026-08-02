import { apiRequest } from './client'
import type { ClientReleaseInfo } from './types'

export const getClientRelease = (clientId: string) =>
  apiRequest<ClientReleaseInfo>(`/api/releases/${encodeURIComponent(clientId)}`)
