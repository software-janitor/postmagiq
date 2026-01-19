import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { Shield, Download, Trash2, ChevronDown, ToggleLeft, ToggleRight } from 'lucide-react'
import {
  getPrivacySettings,
  updatePrivacySettings,
  exportUserData,
  deleteAccount,
  PrivacySettings as PrivacySettingsType,
} from '../../api/privacy'
import { useAuthStore } from '../../stores/authStore'
import ConfirmDeleteModal from '../../components/settings/ConfirmDeleteModal'

const RETENTION_OPTIONS = [
  { value: 30, label: '30 days' },
  { value: 90, label: '90 days' },
  { value: 365, label: '1 year' },
  { value: 0, label: 'Forever' },
]

export default function PrivacySettings() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { clear: clearAuth } = useAuthStore()

  const [showDeleteModal, setShowDeleteModal] = useState(false)
  const [deleteError, setDeleteError] = useState<string | null>(null)
  const [exportMessage, setExportMessage] = useState<string | null>(null)

  const { data: settings, isLoading } = useQuery({
    queryKey: ['privacy-settings'],
    queryFn: getPrivacySettings,
  })

  const updateMutation = useMutation({
    mutationFn: updatePrivacySettings,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['privacy-settings'] })
    },
  })

  const exportMutation = useMutation({
    mutationFn: exportUserData,
    onSuccess: (data) => {
      // Trigger download
      window.open(data.download_url, '_blank')
      setExportMessage('Your data export has been started. Download should begin shortly.')
      setTimeout(() => setExportMessage(null), 5000)
    },
    onError: (error: Error) => {
      setExportMessage(`Export failed: ${error.message}`)
    },
  })

  const deleteMutation = useMutation({
    mutationFn: deleteAccount,
    onSuccess: () => {
      clearAuth()
      navigate('/auth/login')
    },
    onError: (error: Error) => {
      setDeleteError(error.message)
    },
  })

  const handleToggle = (field: keyof PrivacySettingsType) => {
    if (!settings) return
    updateMutation.mutate({
      [field]: !settings[field],
    })
  }

  const handleRetentionChange = (value: number) => {
    updateMutation.mutate({ data_retention_days: value })
  }

  const handleExport = () => {
    setExportMessage(null)
    exportMutation.mutate()
  }

  const handleDeleteConfirm = () => {
    setDeleteError(null)
    deleteMutation.mutate('DELETE')
  }

  if (isLoading) {
    return (
      <div className="space-y-6 max-w-4xl">
        <h1 className="text-2xl font-bold text-white">Privacy Settings</h1>
        <div className="bg-zinc-900 rounded-lg border border-zinc-800 p-8 text-center text-zinc-400">
          Loading privacy settings...
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6 max-w-4xl">
      <div>
        <h1 className="text-2xl font-bold text-white">Privacy Settings</h1>
        <p className="text-zinc-400 mt-1">Manage your privacy preferences and data</p>
      </div>

      {/* Data Retention */}
      <div className="bg-zinc-900 rounded-lg border border-zinc-800">
        <div className="p-4 border-b border-zinc-800 flex items-center gap-2">
          <Shield className="w-5 h-5 text-amber-400" />
          <h2 className="text-lg font-semibold text-white">Data Retention</h2>
        </div>
        <div className="p-4 space-y-4">
          <p className="text-sm text-zinc-400">
            Choose how long we retain your activity data. This does not affect your published content.
          </p>
          <div className="relative w-full max-w-xs">
            <select
              value={settings?.data_retention_days ?? 365}
              onChange={(e) => handleRetentionChange(Number(e.target.value))}
              disabled={updateMutation.isPending}
              className="w-full px-3 py-2 bg-zinc-800 border border-zinc-700 rounded-lg text-white focus:outline-none focus:border-amber-500 appearance-none"
            >
              {RETENTION_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
            <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-500 pointer-events-none" />
          </div>
        </div>
      </div>

      {/* Privacy Toggles */}
      <div className="bg-zinc-900 rounded-lg border border-zinc-800">
        <div className="p-4 border-b border-zinc-800 flex items-center gap-2">
          <Shield className="w-5 h-5 text-amber-400" />
          <h2 className="text-lg font-semibold text-white">Privacy Preferences</h2>
        </div>
        <div className="divide-y divide-zinc-800">
          {/* Analytics Opt-out */}
          <div className="p-4 flex items-center justify-between">
            <div>
              <h3 className="text-white font-medium">Analytics</h3>
              <p className="text-sm text-zinc-400 mt-1">
                Allow us to collect anonymous usage data to improve the product
              </p>
            </div>
            <button
              onClick={() => handleToggle('analytics_opt_out')}
              disabled={updateMutation.isPending}
              className="text-amber-400 hover:text-amber-300 transition-colors"
            >
              {settings?.analytics_opt_out ? (
                <ToggleLeft className="w-10 h-10 text-zinc-600" />
              ) : (
                <ToggleRight className="w-10 h-10" />
              )}
            </button>
          </div>

          {/* Marketing Emails */}
          <div className="p-4 flex items-center justify-between">
            <div>
              <h3 className="text-white font-medium">Marketing Emails</h3>
              <p className="text-sm text-zinc-400 mt-1">
                Receive updates about new features, tips, and promotions
              </p>
            </div>
            <button
              onClick={() => handleToggle('marketing_emails_opt_out')}
              disabled={updateMutation.isPending}
              className="text-amber-400 hover:text-amber-300 transition-colors"
            >
              {settings?.marketing_emails_opt_out ? (
                <ToggleLeft className="w-10 h-10 text-zinc-600" />
              ) : (
                <ToggleRight className="w-10 h-10" />
              )}
            </button>
          </div>

          {/* Activity Logging */}
          <div className="p-4 flex items-center justify-between">
            <div>
              <h3 className="text-white font-medium">Activity Logging</h3>
              <p className="text-sm text-zinc-400 mt-1">
                Keep detailed logs of your activity for audit and security purposes
              </p>
            </div>
            <button
              onClick={() => handleToggle('activity_logging_enabled')}
              disabled={updateMutation.isPending}
              className="text-amber-400 hover:text-amber-300 transition-colors"
            >
              {settings?.activity_logging_enabled ? (
                <ToggleRight className="w-10 h-10" />
              ) : (
                <ToggleLeft className="w-10 h-10 text-zinc-600" />
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Data Export */}
      <div className="bg-zinc-900 rounded-lg border border-zinc-800">
        <div className="p-4 border-b border-zinc-800 flex items-center gap-2">
          <Download className="w-5 h-5 text-amber-400" />
          <h2 className="text-lg font-semibold text-white">Export Your Data</h2>
        </div>
        <div className="p-4 space-y-4">
          <p className="text-sm text-zinc-400">
            Download a copy of all your personal data including your profile, settings, and content.
          </p>
          {exportMessage && (
            <div
              className={`p-3 rounded-lg text-sm ${
                exportMessage.startsWith('Export failed')
                  ? 'bg-red-500/10 border border-red-500/50 text-red-400'
                  : 'bg-green-500/10 border border-green-500/50 text-green-400'
              }`}
            >
              {exportMessage}
            </div>
          )}
          <button
            onClick={handleExport}
            disabled={exportMutation.isPending}
            className="flex items-center gap-2 px-4 py-2 bg-amber-600 hover:bg-amber-700 disabled:bg-amber-800 text-white rounded-lg font-medium transition-colors"
          >
            <Download className="w-4 h-4" />
            {exportMutation.isPending ? 'Preparing export...' : 'Export my data'}
          </button>
        </div>
      </div>

      {/* Danger Zone */}
      <div className="bg-zinc-900 rounded-lg border border-red-500/30">
        <div className="p-4 border-b border-red-500/30 flex items-center gap-2">
          <Trash2 className="w-5 h-5 text-red-400" />
          <h2 className="text-lg font-semibold text-red-400">Danger Zone</h2>
        </div>
        <div className="p-4 space-y-4">
          <p className="text-sm text-zinc-400">
            Permanently delete your account and all associated data. This action cannot be undone.
          </p>
          <button
            onClick={() => setShowDeleteModal(true)}
            className="flex items-center gap-2 px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg font-medium transition-colors"
          >
            <Trash2 className="w-4 h-4" />
            Delete my account
          </button>
        </div>
      </div>

      {/* Delete Confirmation Modal */}
      <ConfirmDeleteModal
        isOpen={showDeleteModal}
        onClose={() => {
          setShowDeleteModal(false)
          setDeleteError(null)
        }}
        onConfirm={handleDeleteConfirm}
        isDeleting={deleteMutation.isPending}
        error={deleteError}
      />
    </div>
  )
}
