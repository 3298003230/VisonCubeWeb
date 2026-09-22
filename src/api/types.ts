export interface AuthUser {
  id: number
  username: string
  email: string | null
  email_verified_at: string | null
  role: string
  created_at?: string | null
  updated_at?: string | null
}

export interface AuthSession {
  token: string
  token_type: string
  expires_at: string
  expires_at_ms: number
  user: AuthUser
}

export interface PasswordCredentials {
  username: string
  password: string
}

export interface RegisterCredentials extends PasswordCredentials {
  email: string
}

export interface MessageResponse {
  message: string
}

export interface ClientReleaseInfo {
  client_id: string
  version: string
  display_version?: string
  min_version?: string
  force_update?: boolean
  file_name: string
  download_url: string
  feed_url?: string
  sha256?: string
  changelog?: string
  published_at?: string
}

export type LicensePlan = 'day' | 'week' | 'month'

export type LicenseState = 'none' | 'active' | 'expired' | 'unlimited'

export interface LicenseStatus {
  state: LicenseState
  is_unlimited: boolean
  activated_at: string | null
  expires_at: string | null
  server_time: string
  remaining_seconds: number | null
}

export interface RedeemLicenseResponse {
  message: string
  license: LicenseStatus
}

export interface LicenseBatchSummary {
  id: string
  plan: LicensePlan
  quantity: number
  unused_count: number
  redeemed_count: number
  revoked_count: number
  note: string | null
  created_at: string
  created_by: string
}

export interface CreateLicenseBatchRequest {
  plan: LicensePlan
  quantity: number
  note?: string
}

export interface CreateLicenseBatchResponse {
  batch: LicenseBatchSummary
  codes: string[]
}
