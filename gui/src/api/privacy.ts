import { apiGet, apiPut, apiPost, apiDelete } from './client'

export interface PrivacySettings {
  data_retention_days: number // 30, 90, 365, or 0 for forever
  analytics_opt_out: boolean
  marketing_emails_opt_out: boolean
  activity_logging_enabled: boolean
}

export interface PrivacySettingsUpdate {
  data_retention_days?: number
  analytics_opt_out?: boolean
  marketing_emails_opt_out?: boolean
  activity_logging_enabled?: boolean
}

export interface DataExportResponse {
  download_url: string
  expires_at: string
}

export interface DeleteAccountRequest {
  confirmation: string // User must type "DELETE"
}

export function getPrivacySettings(): Promise<PrivacySettings> {
  return apiGet<PrivacySettings>('/v1/users/me/privacy')
}

export function updatePrivacySettings(
  settings: PrivacySettingsUpdate
): Promise<PrivacySettings> {
  return apiPut<PrivacySettings>('/v1/users/me/privacy', settings)
}

export function exportUserData(): Promise<DataExportResponse> {
  return apiPost<DataExportResponse>('/v1/users/me/export')
}

export function deleteAccount(confirmation: string): Promise<void> {
  return apiDelete<void>(`/v1/users/me?confirmation=${encodeURIComponent(confirmation)}`)
}
