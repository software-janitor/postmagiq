import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Palette, Building2, Mail, Save, AlertCircle } from 'lucide-react'
import { useWorkspaceStore } from '../../stores/workspaceStore'
import {
  getWhitelabelConfig,
  updateWhitelabelConfig,
  uploadAsset,
  deleteAsset,
  WhitelabelConfigUpdate,
} from '../../api/whitelabel'
import ColorPicker from '../../components/settings/ColorPicker'
import LogoUpload from '../../components/settings/LogoUpload'

export default function WhitelabelSettings() {
  const { currentWorkspaceId } = useWorkspaceStore()
  const queryClient = useQueryClient()

  // Form state
  const [formData, setFormData] = useState<WhitelabelConfigUpdate>({
    company_name: null,
    primary_color: null,
    secondary_color: null,
    accent_color: null,
    portal_welcome_text: null,
    portal_footer_text: null,
    support_email: null,
  })
  const [isDirty, setIsDirty] = useState(false)
  const [uploadingLogo, setUploadingLogo] = useState(false)
  const [uploadingFavicon, setUploadingFavicon] = useState(false)

  // Fetch current config
  const { data: config, isLoading, error } = useQuery({
    queryKey: ['whitelabel', currentWorkspaceId],
    queryFn: () => getWhitelabelConfig(currentWorkspaceId!),
    enabled: !!currentWorkspaceId,
  })

  // Sync form data when config loads
  useEffect(() => {
    if (config) {
      setFormData({
        company_name: config.company_name,
        primary_color: config.primary_color,
        secondary_color: config.secondary_color,
        accent_color: config.accent_color,
        portal_welcome_text: config.portal_welcome_text,
        portal_footer_text: config.portal_footer_text,
        support_email: config.support_email,
      })
      setIsDirty(false)
    }
  }, [config])

  // Update mutation
  const updateMutation = useMutation({
    mutationFn: (data: WhitelabelConfigUpdate) =>
      updateWhitelabelConfig(currentWorkspaceId!, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['whitelabel', currentWorkspaceId] })
      setIsDirty(false)
    },
  })

  // Handle form field changes
  const handleChange = (field: keyof WhitelabelConfigUpdate, value: string | null) => {
    setFormData((prev) => ({ ...prev, [field]: value || null }))
    setIsDirty(true)
  }

  // Handle save
  const handleSave = () => {
    updateMutation.mutate(formData)
  }

  // Handle logo upload
  const handleLogoUpload = async (file: File) => {
    setUploadingLogo(true)
    try {
      await uploadAsset(currentWorkspaceId!, 'logo', file)
      queryClient.invalidateQueries({ queryKey: ['whitelabel', currentWorkspaceId] })
    } finally {
      setUploadingLogo(false)
    }
  }

  // Handle logo remove
  const handleLogoRemove = async () => {
    await deleteAsset(currentWorkspaceId!, 'logo')
    queryClient.invalidateQueries({ queryKey: ['whitelabel', currentWorkspaceId] })
  }

  // Handle favicon upload
  const handleFaviconUpload = async (file: File) => {
    setUploadingFavicon(true)
    try {
      await uploadAsset(currentWorkspaceId!, 'favicon', file)
      queryClient.invalidateQueries({ queryKey: ['whitelabel', currentWorkspaceId] })
    } finally {
      setUploadingFavicon(false)
    }
  }

  // Handle favicon remove
  const handleFaviconRemove = async () => {
    await deleteAsset(currentWorkspaceId!, 'favicon')
    queryClient.invalidateQueries({ queryKey: ['whitelabel', currentWorkspaceId] })
  }

  if (!currentWorkspaceId) {
    return (
      <div className="space-y-6 max-w-4xl">
        <h1 className="text-2xl font-bold text-white">White-label Settings</h1>
        <div className="bg-zinc-900 rounded-lg border border-zinc-800 p-8 text-center text-zinc-500">
          Please select a workspace first.
        </div>
      </div>
    )
  }

  if (isLoading) {
    return (
      <div className="space-y-6 max-w-4xl">
        <h1 className="text-2xl font-bold text-white">White-label Settings</h1>
        <div className="bg-zinc-900 rounded-lg border border-zinc-800 p-8 text-center text-zinc-500">
          Loading configuration...
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="space-y-6 max-w-4xl">
        <h1 className="text-2xl font-bold text-white">White-label Settings</h1>
        <div className="bg-red-900/20 border border-red-800 rounded-lg p-4 flex items-center gap-3 text-red-400">
          <AlertCircle className="w-5 h-5 flex-shrink-0" />
          <span>
            {error instanceof Error ? error.message : 'Failed to load configuration'}
          </span>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6 max-w-4xl">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-white">White-label Settings</h1>
        <button
          onClick={handleSave}
          disabled={!isDirty || updateMutation.isPending}
          className="flex items-center gap-2 px-4 py-2 bg-amber-600 hover:bg-amber-700 disabled:bg-zinc-700 disabled:text-zinc-500 text-white rounded-lg font-medium transition-colors"
        >
          <Save className="w-4 h-4" />
          {updateMutation.isPending ? 'Saving...' : 'Save Changes'}
        </button>
      </div>

      {updateMutation.isError && (
        <div className="bg-red-900/20 border border-red-800 rounded-lg p-4 flex items-center gap-3 text-red-400">
          <AlertCircle className="w-5 h-5 flex-shrink-0" />
          <span>
            {updateMutation.error instanceof Error
              ? updateMutation.error.message
              : 'Failed to save changes'}
          </span>
        </div>
      )}

      {updateMutation.isSuccess && !isDirty && (
        <div className="bg-green-900/20 border border-green-800 rounded-lg p-4 text-green-400">
          Changes saved successfully.
        </div>
      )}

      {/* Branding Section */}
      <div className="bg-zinc-900 rounded-lg border border-zinc-800">
        <div className="p-4 border-b border-zinc-800 flex items-center gap-2">
          <Building2 className="w-5 h-5 text-amber-400" />
          <h2 className="text-lg font-semibold text-white">Branding</h2>
        </div>
        <div className="p-6 space-y-6">
          {/* Company Name */}
          <div className="space-y-2">
            <label className="block text-sm font-medium text-zinc-300">Company Name</label>
            <input
              type="text"
              value={formData.company_name || ''}
              onChange={(e) => handleChange('company_name', e.target.value)}
              placeholder="Your Company Name"
              className="w-full max-w-md px-3 py-2 bg-zinc-800 border border-zinc-600 rounded-lg text-white placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-amber-500/50 focus:border-amber-500"
            />
          </div>

          {/* Logo Upload */}
          <LogoUpload
            label="Logo"
            description="Displayed in the header and login page. Recommended: 200x50px or wider."
            currentUrl={config?.logo_url || null}
            onUpload={handleLogoUpload}
            onRemove={handleLogoRemove}
            isUploading={uploadingLogo}
          />

          {/* Favicon Upload */}
          <LogoUpload
            label="Favicon"
            description="Browser tab icon. Recommended: 32x32px or 64x64px."
            currentUrl={config?.favicon_url || null}
            onUpload={handleFaviconUpload}
            onRemove={handleFaviconRemove}
            accept="image/png,image/x-icon,image/svg+xml"
            isUploading={uploadingFavicon}
          />
        </div>
      </div>

      {/* Colors Section */}
      <div className="bg-zinc-900 rounded-lg border border-zinc-800">
        <div className="p-4 border-b border-zinc-800 flex items-center gap-2">
          <Palette className="w-5 h-5 text-amber-400" />
          <h2 className="text-lg font-semibold text-white">Theme Colors</h2>
        </div>
        <div className="p-6 grid grid-cols-1 md:grid-cols-3 gap-6">
          <ColorPicker
            label="Primary Color"
            description="Main brand color for buttons and links"
            value={formData.primary_color}
            onChange={(color) => handleChange('primary_color', color)}
          />
          <ColorPicker
            label="Secondary Color"
            description="Accent color for highlights"
            value={formData.secondary_color}
            onChange={(color) => handleChange('secondary_color', color)}
          />
          <ColorPicker
            label="Accent Color"
            description="Used for notifications and alerts"
            value={formData.accent_color}
            onChange={(color) => handleChange('accent_color', color)}
          />
        </div>
      </div>

      {/* Portal Content Section */}
      <div className="bg-zinc-900 rounded-lg border border-zinc-800">
        <div className="p-4 border-b border-zinc-800 flex items-center gap-2">
          <Mail className="w-5 h-5 text-amber-400" />
          <h2 className="text-lg font-semibold text-white">Portal Content</h2>
        </div>
        <div className="p-6 space-y-6">
          {/* Welcome Text */}
          <div className="space-y-2">
            <label className="block text-sm font-medium text-zinc-300">Welcome Text</label>
            <p className="text-xs text-zinc-500">
              Displayed on the login page above the sign-in form
            </p>
            <textarea
              value={formData.portal_welcome_text || ''}
              onChange={(e) => handleChange('portal_welcome_text', e.target.value)}
              placeholder="Welcome to your content portal..."
              rows={3}
              className="w-full px-3 py-2 bg-zinc-800 border border-zinc-600 rounded-lg text-white placeholder-zinc-500 resize-none focus:outline-none focus:ring-2 focus:ring-amber-500/50 focus:border-amber-500"
            />
          </div>

          {/* Footer Text */}
          <div className="space-y-2">
            <label className="block text-sm font-medium text-zinc-300">Footer Text</label>
            <p className="text-xs text-zinc-500">
              Displayed in the footer of all pages
            </p>
            <textarea
              value={formData.portal_footer_text || ''}
              onChange={(e) => handleChange('portal_footer_text', e.target.value)}
              placeholder="Copyright 2024 Your Company. All rights reserved."
              rows={2}
              className="w-full px-3 py-2 bg-zinc-800 border border-zinc-600 rounded-lg text-white placeholder-zinc-500 resize-none focus:outline-none focus:ring-2 focus:ring-amber-500/50 focus:border-amber-500"
            />
          </div>

          {/* Support Email */}
          <div className="space-y-2">
            <label className="block text-sm font-medium text-zinc-300">Support Email</label>
            <p className="text-xs text-zinc-500">
              Contact email shown in help sections and error messages
            </p>
            <input
              type="email"
              value={formData.support_email || ''}
              onChange={(e) => handleChange('support_email', e.target.value)}
              placeholder="support@yourcompany.com"
              className="w-full max-w-md px-3 py-2 bg-zinc-800 border border-zinc-600 rounded-lg text-white placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-amber-500/50 focus:border-amber-500"
            />
          </div>
        </div>
      </div>

      {/* Preview hint */}
      <div className="bg-zinc-800/50 border border-zinc-700 rounded-lg p-4 text-sm text-zinc-400">
        <strong className="text-zinc-300">Note:</strong> Changes will be reflected for all users
        in this workspace after saving. Logo and favicon uploads are applied immediately.
      </div>
    </div>
  )
}
