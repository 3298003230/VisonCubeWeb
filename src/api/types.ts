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
