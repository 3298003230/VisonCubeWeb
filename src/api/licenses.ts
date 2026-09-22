import { apiRequest } from './client'
import type {
  CreateLicenseBatchRequest,
  CreateLicenseBatchResponse,
  LicenseBatchSummary,
  LicenseStatus,
  RedeemLicenseResponse,
} from './types'

export const getLicenseStatus = (token: string) =>
  apiRequest<LicenseStatus>('/api/licenses/me', { token })

export const redeemLicense = (token: string, code: string) =>
  apiRequest<RedeemLicenseResponse>('/api/licenses/redeem', {
    method: 'POST',
    token,
    body: { code },
  })

export const listLicenseBatches = (token: string) =>
  apiRequest<LicenseBatchSummary[]>('/api/licenses/admin/batches?limit=50', { token })

export const createLicenseBatch = (token: string, request: CreateLicenseBatchRequest) =>
  apiRequest<CreateLicenseBatchResponse>('/api/licenses/admin/batches', {
    method: 'POST',
    token,
    body: request,
  })
