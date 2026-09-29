import { apiRequest } from './client'
import type {
  CreateLicenseBatchRequest,
  CreateLicenseBatchResponse,
  LicenseAdminOverview,
  LicenseAuditEntry,
  LicenseBatchSummary,
  LicenseCodeStatus,
  LicenseCodeSummary,
  LicenseEntitlementSummary,
  LicenseStatus,
  PagedResponse,
  RedeemLicenseResponse,
  RevokeLicenseBatchResponse,
  RevokeLicenseCodeResponse,
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

export const getLicenseAdminOverview = (token: string) =>
  apiRequest<LicenseAdminOverview>('/api/licenses/admin/overview', { token })

export const listLicenseBatchCodes = (
  token: string,
  batchId: string,
  status: LicenseCodeStatus | null,
  limit = 100,
  offset = 0,
) => {
  const query = new URLSearchParams({ limit: String(limit), offset: String(offset) })
  if (status) query.set('status', status)
  return apiRequest<PagedResponse<LicenseCodeSummary>>(
    `/api/licenses/admin/batches/${encodeURIComponent(batchId)}/codes?${query}`,
    { token },
  )
}

export const revokeLicenseCode = (token: string, codeId: number, reason?: string) =>
  apiRequest<RevokeLicenseCodeResponse>(`/api/licenses/admin/codes/${codeId}/revoke`, {
    method: 'POST',
    token,
    body: reason ? { reason } : {},
  })

export const revokeLicenseBatch = (token: string, batchId: string, reason?: string) =>
  apiRequest<RevokeLicenseBatchResponse>(
    `/api/licenses/admin/batches/${encodeURIComponent(batchId)}/revoke`,
    {
      method: 'POST',
      token,
      body: reason ? { reason } : {},
    },
  )

export const listLicenseEntitlements = (token: string, limit = 100, offset = 0) => {
  const query = new URLSearchParams({ limit: String(limit), offset: String(offset) })
  return apiRequest<PagedResponse<LicenseEntitlementSummary>>(
    `/api/licenses/admin/entitlements?${query}`,
    { token },
  )
}

export const listLicenseAudit = (token: string, limit = 100, offset = 0) => {
  const query = new URLSearchParams({ limit: String(limit), offset: String(offset) })
  return apiRequest<PagedResponse<LicenseAuditEntry>>(`/api/licenses/admin/audit?${query}`, { token })
}
