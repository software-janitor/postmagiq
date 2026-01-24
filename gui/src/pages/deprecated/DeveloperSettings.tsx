import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Key, Webhook, Plus, Trash2, Copy, Check, RotateCcw,
  Clock, AlertCircle, CheckCircle, XCircle, Eye
} from 'lucide-react'
import { apiGet, apiPost, apiDelete } from '../api/client'
import { useWorkspaceStore } from '../stores/workspaceStore'
import { usePermission } from '../hooks/usePermission'

// =============================================================================
// Types
// =============================================================================

interface APIKey {
  id: string
  name: string
  description: string | null
  key_prefix: string
  key?: string  // Only present on creation
  scopes: string
  rate_limit_per_minute: number
  rate_limit_per_day: number
  status: string
  expires_at: string | null
  last_used_at: string | null
  total_requests: number
  created_at: string
}

interface Webhook {
  id: string
  name: string
  description: string | null
  url: string
  events: string
  secret_prefix: string
  secret?: string  // Only present on creation
  status: string
  timeout_seconds: number
  max_retries: number
  retry_delay_seconds: number
  total_deliveries: number
  successful_deliveries: number
  failed_deliveries: number
  last_delivery_at: string | null
  created_at: string
}

interface WebhookDelivery {
  id: string
  webhook_id: string
  event_type: string
  status: string
  response_status_code: number | null
  delivered_at: string | null
  duration_ms: number | null
  attempt_number: number
  error_message: string | null
  created_at: string
}

// =============================================================================
// Component
// =============================================================================

export default function DeveloperSettings() {
  const { currentWorkspaceId } = useWorkspaceStore()
  const canManage = usePermission('admin')
  const [activeTab, setActiveTab] = useState<'api-keys' | 'webhooks'>('api-keys')

  if (!currentWorkspaceId) {
    return (
      <div className="text-center py-12 text-zinc-400">
        No workspace selected
      </div>
    )
  }

  if (!canManage) {
    return (
      <div className="text-center py-12 text-zinc-400">
        You don't have permission to manage developer settings
      </div>
    )
  }

  return (
    <div className="space-y-6 max-w-5xl">
      <div>
        <h1 className="text-2xl font-bold text-white">Developer Settings</h1>
        <p className="text-zinc-400 mt-1">Manage API keys and webhooks for programmatic access</p>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 p-1 bg-zinc-800 rounded-lg w-fit">
        <button
          onClick={() => setActiveTab('api-keys')}
          className={`flex items-center gap-2 px-4 py-2 rounded-md font-medium transition-colors ${
            activeTab === 'api-keys'
              ? 'bg-zinc-700 text-white'
              : 'text-zinc-400 hover:text-white'
          }`}
        >
          <Key className="w-4 h-4" />
          API Keys
        </button>
        <button
          onClick={() => setActiveTab('webhooks')}
          className={`flex items-center gap-2 px-4 py-2 rounded-md font-medium transition-colors ${
            activeTab === 'webhooks'
              ? 'bg-zinc-700 text-white'
              : 'text-zinc-400 hover:text-white'
          }`}
        >
          <Webhook className="w-4 h-4" />
          Webhooks
        </button>
      </div>

      {/* Tab content */}
      {activeTab === 'api-keys' ? (
        <APIKeysTab workspaceId={currentWorkspaceId} />
      ) : (
        <WebhooksTab workspaceId={currentWorkspaceId} />
      )}
    </div>
  )
}

// =============================================================================
// API Keys Tab
// =============================================================================

function APIKeysTab({ workspaceId }: { workspaceId: string }) {
  const queryClient = useQueryClient()
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [newKeyName, setNewKeyName] = useState('')
  const [newKeyDescription, setNewKeyDescription] = useState('')
  const [newKeyScopes, setNewKeyScopes] = useState('')
  const [newKeyExpiry, setNewKeyExpiry] = useState('')
  const [createdKey, setCreatedKey] = useState<string | null>(null)
  const [copiedKey, setCopiedKey] = useState(false)

  const { data: apiKeys, isLoading } = useQuery({
    queryKey: ['api-keys', workspaceId],
    queryFn: () => apiGet<APIKey[]>(`/v1/w/${workspaceId}/api-keys`),
  })

  const createMutation = useMutation({
    mutationFn: (data: {
      name: string
      description?: string
      scopes?: string[]
      expires_in_days?: number
    }) => apiPost<APIKey>(`/v1/w/${workspaceId}/api-keys`, data),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['api-keys', workspaceId] })
      if (data.key) {
        setCreatedKey(data.key)
      } else {
        setShowCreateModal(false)
        resetForm()
      }
    },
  })

  const revokeMutation = useMutation({
    mutationFn: (keyId: string) => apiDelete(`/v1/w/${workspaceId}/api-keys/${keyId}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['api-keys', workspaceId] })
    },
  })

  const resetForm = () => {
    setNewKeyName('')
    setNewKeyDescription('')
    setNewKeyScopes('')
    setNewKeyExpiry('')
    setCreatedKey(null)
    setCopiedKey(false)
  }

  const handleCreate = (e: React.FormEvent) => {
    e.preventDefault()
    createMutation.mutate({
      name: newKeyName,
      description: newKeyDescription || undefined,
      scopes: newKeyScopes ? newKeyScopes.split(',').map(s => s.trim()) : undefined,
      expires_in_days: newKeyExpiry ? parseInt(newKeyExpiry) : undefined,
    })
  }

  const handleCopyKey = async () => {
    if (createdKey) {
      await navigator.clipboard.writeText(createdKey)
      setCopiedKey(true)
      setTimeout(() => setCopiedKey(false), 2000)
    }
  }

  const handleRevoke = (key: APIKey) => {
    if (confirm(`Revoke API key "${key.name}"? This cannot be undone.`)) {
      revokeMutation.mutate(key.id)
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-white">API Keys</h2>
        <button
          onClick={() => setShowCreateModal(true)}
          className="flex items-center gap-2 px-4 py-2 bg-amber-600 hover:bg-amber-700 text-white rounded-lg font-medium transition-colors"
        >
          <Plus className="w-4 h-4" />
          Create API Key
        </button>
      </div>

      <div className="bg-zinc-900 rounded-lg border border-zinc-800">
        {isLoading ? (
          <div className="p-8 text-center text-zinc-400">Loading...</div>
        ) : !apiKeys?.length ? (
          <div className="p-8 text-center text-zinc-400">
            No API keys created yet. Create one to get started.
          </div>
        ) : (
          <div className="divide-y divide-zinc-800">
            {apiKeys.map((key) => (
              <div key={key.id} className="p-4 flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <div className="w-10 h-10 bg-zinc-800 rounded-lg flex items-center justify-center">
                    <Key className="w-5 h-5 text-amber-400" />
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-white font-medium">{key.name}</span>
                      <span className="px-2 py-0.5 bg-zinc-800 text-zinc-400 text-xs rounded font-mono">
                        {key.key_prefix}...
                      </span>
                      {key.status === 'active' ? (
                        <span className="flex items-center gap-1 px-2 py-0.5 bg-green-500/20 text-green-400 text-xs rounded">
                          <CheckCircle className="w-3 h-3" />
                          Active
                        </span>
                      ) : (
                        <span className="flex items-center gap-1 px-2 py-0.5 bg-red-500/20 text-red-400 text-xs rounded">
                          <XCircle className="w-3 h-3" />
                          {key.status}
                        </span>
                      )}
                    </div>
                    <div className="flex items-center gap-4 text-sm text-zinc-400 mt-1">
                      <span>{key.total_requests.toLocaleString()} requests</span>
                      {key.last_used_at && (
                        <span>Last used {new Date(key.last_used_at).toLocaleDateString()}</span>
                      )}
                      {key.expires_at && (
                        <span className="flex items-center gap-1">
                          <Clock className="w-3 h-3" />
                          Expires {new Date(key.expires_at).toLocaleDateString()}
                        </span>
                      )}
                    </div>
                  </div>
                </div>

                {key.status === 'active' && (
                  <button
                    onClick={() => handleRevoke(key)}
                    disabled={revokeMutation.isPending}
                    className="p-2 text-zinc-400 hover:text-red-400 hover:bg-red-500/10 rounded-lg transition-colors"
                    title="Revoke key"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Create modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-zinc-900 rounded-lg border border-zinc-800 w-full max-w-md p-6">
            {createdKey ? (
              <div className="space-y-4">
                <h3 className="text-lg font-semibold text-white">API Key Created</h3>
                <div className="p-3 bg-amber-500/10 border border-amber-500/50 rounded-lg text-amber-400 text-sm">
                  <AlertCircle className="w-4 h-4 inline-block mr-2" />
                  Copy this key now. You won't be able to see it again.
                </div>
                <div className="flex items-center gap-2">
                  <input
                    type="text"
                    value={createdKey}
                    readOnly
                    className="flex-1 px-3 py-2 bg-zinc-800 border border-zinc-700 rounded-lg text-white font-mono text-sm"
                  />
                  <button
                    onClick={handleCopyKey}
                    className="p-2 bg-zinc-800 hover:bg-zinc-700 text-white rounded-lg transition-colors"
                    title="Copy to clipboard"
                  >
                    {copiedKey ? <Check className="w-5 h-5 text-green-400" /> : <Copy className="w-5 h-5" />}
                  </button>
                </div>
                <button
                  onClick={() => {
                    setShowCreateModal(false)
                    resetForm()
                  }}
                  className="w-full px-4 py-2 bg-amber-600 hover:bg-amber-700 text-white rounded-lg font-medium transition-colors"
                >
                  Done
                </button>
              </div>
            ) : (
              <>
                <h3 className="text-lg font-semibold text-white mb-4">Create API Key</h3>
                <form onSubmit={handleCreate} className="space-y-4">
                  <div>
                    <label className="block text-sm text-zinc-400 mb-1">Name</label>
                    <input
                      type="text"
                      value={newKeyName}
                      onChange={(e) => setNewKeyName(e.target.value)}
                      required
                      className="w-full px-3 py-2 bg-zinc-800 border border-zinc-700 rounded-lg text-white focus:outline-none focus:border-amber-500"
                      placeholder="Production API Key"
                    />
                  </div>
                  <div>
                    <label className="block text-sm text-zinc-400 mb-1">Description (optional)</label>
                    <input
                      type="text"
                      value={newKeyDescription}
                      onChange={(e) => setNewKeyDescription(e.target.value)}
                      className="w-full px-3 py-2 bg-zinc-800 border border-zinc-700 rounded-lg text-white focus:outline-none focus:border-amber-500"
                      placeholder="Used for CI/CD pipeline"
                    />
                  </div>
                  <div>
                    <label className="block text-sm text-zinc-400 mb-1">Scopes (comma-separated, optional)</label>
                    <input
                      type="text"
                      value={newKeyScopes}
                      onChange={(e) => setNewKeyScopes(e.target.value)}
                      className="w-full px-3 py-2 bg-zinc-800 border border-zinc-700 rounded-lg text-white focus:outline-none focus:border-amber-500"
                      placeholder="content:read, content:write"
                    />
                  </div>
                  <div>
                    <label className="block text-sm text-zinc-400 mb-1">Expiration (days, optional)</label>
                    <input
                      type="number"
                      value={newKeyExpiry}
                      onChange={(e) => setNewKeyExpiry(e.target.value)}
                      min="1"
                      max="365"
                      className="w-full px-3 py-2 bg-zinc-800 border border-zinc-700 rounded-lg text-white focus:outline-none focus:border-amber-500"
                      placeholder="90"
                    />
                  </div>
                  <div className="flex gap-3 pt-2">
                    <button
                      type="button"
                      onClick={() => {
                        setShowCreateModal(false)
                        resetForm()
                      }}
                      className="flex-1 px-4 py-2 bg-zinc-800 hover:bg-zinc-700 text-white rounded-lg font-medium transition-colors"
                    >
                      Cancel
                    </button>
                    <button
                      type="submit"
                      disabled={createMutation.isPending}
                      className="flex-1 px-4 py-2 bg-amber-600 hover:bg-amber-700 disabled:bg-amber-800 text-white rounded-lg font-medium transition-colors"
                    >
                      {createMutation.isPending ? 'Creating...' : 'Create Key'}
                    </button>
                  </div>
                </form>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

// =============================================================================
// Webhooks Tab
// =============================================================================

function WebhooksTab({ workspaceId }: { workspaceId: string }) {
  const queryClient = useQueryClient()
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [showDeliveriesModal, setShowDeliveriesModal] = useState<string | null>(null)
  const [newWebhookName, setNewWebhookName] = useState('')
  const [newWebhookUrl, setNewWebhookUrl] = useState('')
  const [newWebhookEvents, setNewWebhookEvents] = useState('')
  const [createdSecret, setCreatedSecret] = useState<string | null>(null)
  const [copiedSecret, setCopiedSecret] = useState(false)

  const { data: webhooks, isLoading } = useQuery({
    queryKey: ['webhooks', workspaceId],
    queryFn: () => apiGet<Webhook[]>(`/v1/w/${workspaceId}/webhooks`),
  })

  const { data: deliveries } = useQuery({
    queryKey: ['webhook-deliveries', workspaceId, showDeliveriesModal],
    queryFn: () => apiGet<WebhookDelivery[]>(`/v1/w/${workspaceId}/webhooks/${showDeliveriesModal}/deliveries`),
    enabled: !!showDeliveriesModal,
  })

  const createMutation = useMutation({
    mutationFn: (data: {
      name: string
      url: string
      events: string[]
    }) => apiPost<Webhook>(`/v1/w/${workspaceId}/webhooks`, data),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['webhooks', workspaceId] })
      if (data.secret) {
        setCreatedSecret(data.secret)
      } else {
        setShowCreateModal(false)
        resetForm()
      }
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (webhookId: string) => apiDelete(`/v1/w/${workspaceId}/webhooks/${webhookId}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['webhooks', workspaceId] })
    },
  })

  const rotateSecretMutation = useMutation({
    mutationFn: (webhookId: string) =>
      apiPost<Webhook>(`/v1/w/${workspaceId}/webhooks/${webhookId}/rotate-secret`, {}),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['webhooks', workspaceId] })
      if (data.secret) {
        setCreatedSecret(data.secret)
      }
    },
  })

  const resetForm = () => {
    setNewWebhookName('')
    setNewWebhookUrl('')
    setNewWebhookEvents('')
    setCreatedSecret(null)
    setCopiedSecret(false)
  }

  const handleCreate = (e: React.FormEvent) => {
    e.preventDefault()
    createMutation.mutate({
      name: newWebhookName,
      url: newWebhookUrl,
      events: newWebhookEvents.split(',').map(s => s.trim()).filter(Boolean),
    })
  }

  const handleCopySecret = async () => {
    if (createdSecret) {
      await navigator.clipboard.writeText(createdSecret)
      setCopiedSecret(true)
      setTimeout(() => setCopiedSecret(false), 2000)
    }
  }

  const handleDelete = (webhook: Webhook) => {
    if (confirm(`Delete webhook "${webhook.name}"?`)) {
      deleteMutation.mutate(webhook.id)
    }
  }

  const handleRotateSecret = (webhook: Webhook) => {
    if (confirm(`Rotate secret for "${webhook.name}"? The old secret will stop working immediately.`)) {
      rotateSecretMutation.mutate(webhook.id)
    }
  }

  const availableEvents = [
    'post.created', 'post.updated', 'post.published', 'post.deleted',
    'approval.requested', 'approval.approved', 'approval.rejected',
    'workflow.started', 'workflow.completed', 'workflow.failed',
  ]

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-white">Webhooks</h2>
        <button
          onClick={() => setShowCreateModal(true)}
          className="flex items-center gap-2 px-4 py-2 bg-amber-600 hover:bg-amber-700 text-white rounded-lg font-medium transition-colors"
        >
          <Plus className="w-4 h-4" />
          Add Webhook
        </button>
      </div>

      <div className="bg-zinc-900 rounded-lg border border-zinc-800">
        {isLoading ? (
          <div className="p-8 text-center text-zinc-400">Loading...</div>
        ) : !webhooks?.length ? (
          <div className="p-8 text-center text-zinc-400">
            No webhooks configured yet. Add one to receive event notifications.
          </div>
        ) : (
          <div className="divide-y divide-zinc-800">
            {webhooks.map((webhook) => (
              <div key={webhook.id} className="p-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    <div className="w-10 h-10 bg-zinc-800 rounded-lg flex items-center justify-center">
                      <Webhook className="w-5 h-5 text-blue-400" />
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="text-white font-medium">{webhook.name}</span>
                        {webhook.status === 'active' ? (
                          <span className="flex items-center gap-1 px-2 py-0.5 bg-green-500/20 text-green-400 text-xs rounded">
                            <CheckCircle className="w-3 h-3" />
                            Active
                          </span>
                        ) : (
                          <span className="flex items-center gap-1 px-2 py-0.5 bg-zinc-500/20 text-zinc-400 text-xs rounded">
                            {webhook.status}
                          </span>
                        )}
                      </div>
                      <div className="text-sm text-zinc-400 mt-1 font-mono">{webhook.url}</div>
                      <div className="flex items-center gap-4 text-sm text-zinc-400 mt-1">
                        <span className="text-green-400">{webhook.successful_deliveries} delivered</span>
                        {webhook.failed_deliveries > 0 && (
                          <span className="text-red-400">{webhook.failed_deliveries} failed</span>
                        )}
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => setShowDeliveriesModal(webhook.id)}
                      className="p-2 text-zinc-400 hover:text-white hover:bg-zinc-800 rounded-lg transition-colors"
                      title="View deliveries"
                    >
                      <Eye className="w-4 h-4" />
                    </button>
                    <button
                      onClick={() => handleRotateSecret(webhook)}
                      disabled={rotateSecretMutation.isPending}
                      className="p-2 text-zinc-400 hover:text-amber-400 hover:bg-amber-500/10 rounded-lg transition-colors"
                      title="Rotate secret"
                    >
                      <RotateCcw className="w-4 h-4" />
                    </button>
                    <button
                      onClick={() => handleDelete(webhook)}
                      disabled={deleteMutation.isPending}
                      className="p-2 text-zinc-400 hover:text-red-400 hover:bg-red-500/10 rounded-lg transition-colors"
                      title="Delete webhook"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>

                <div className="mt-3 flex flex-wrap gap-2">
                  {webhook.events.split(',').map((event) => (
                    <span
                      key={event}
                      className="px-2 py-0.5 bg-zinc-800 text-zinc-300 text-xs rounded"
                    >
                      {event.trim()}
                    </span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Create modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-zinc-900 rounded-lg border border-zinc-800 w-full max-w-md p-6">
            {createdSecret ? (
              <div className="space-y-4">
                <h3 className="text-lg font-semibold text-white">Webhook Created</h3>
                <div className="p-3 bg-amber-500/10 border border-amber-500/50 rounded-lg text-amber-400 text-sm">
                  <AlertCircle className="w-4 h-4 inline-block mr-2" />
                  Copy this signing secret now. You won't be able to see it again.
                </div>
                <div className="flex items-center gap-2">
                  <input
                    type="text"
                    value={createdSecret}
                    readOnly
                    className="flex-1 px-3 py-2 bg-zinc-800 border border-zinc-700 rounded-lg text-white font-mono text-sm"
                  />
                  <button
                    onClick={handleCopySecret}
                    className="p-2 bg-zinc-800 hover:bg-zinc-700 text-white rounded-lg transition-colors"
                    title="Copy to clipboard"
                  >
                    {copiedSecret ? <Check className="w-5 h-5 text-green-400" /> : <Copy className="w-5 h-5" />}
                  </button>
                </div>
                <button
                  onClick={() => {
                    setShowCreateModal(false)
                    resetForm()
                  }}
                  className="w-full px-4 py-2 bg-amber-600 hover:bg-amber-700 text-white rounded-lg font-medium transition-colors"
                >
                  Done
                </button>
              </div>
            ) : (
              <>
                <h3 className="text-lg font-semibold text-white mb-4">Add Webhook</h3>
                <form onSubmit={handleCreate} className="space-y-4">
                  <div>
                    <label className="block text-sm text-zinc-400 mb-1">Name</label>
                    <input
                      type="text"
                      value={newWebhookName}
                      onChange={(e) => setNewWebhookName(e.target.value)}
                      required
                      className="w-full px-3 py-2 bg-zinc-800 border border-zinc-700 rounded-lg text-white focus:outline-none focus:border-amber-500"
                      placeholder="Production Webhook"
                    />
                  </div>
                  <div>
                    <label className="block text-sm text-zinc-400 mb-1">URL</label>
                    <input
                      type="url"
                      value={newWebhookUrl}
                      onChange={(e) => setNewWebhookUrl(e.target.value)}
                      required
                      className="w-full px-3 py-2 bg-zinc-800 border border-zinc-700 rounded-lg text-white focus:outline-none focus:border-amber-500"
                      placeholder="https://your-server.com/webhook"
                    />
                  </div>
                  <div>
                    <label className="block text-sm text-zinc-400 mb-1">Events</label>
                    <div className="flex flex-wrap gap-2 p-2 bg-zinc-800 border border-zinc-700 rounded-lg max-h-32 overflow-y-auto">
                      {availableEvents.map((event) => {
                        const selected = newWebhookEvents.split(',').map(s => s.trim()).includes(event)
                        return (
                          <button
                            key={event}
                            type="button"
                            onClick={() => {
                              const events = newWebhookEvents.split(',').map(s => s.trim()).filter(Boolean)
                              if (selected) {
                                setNewWebhookEvents(events.filter(e => e !== event).join(', '))
                              } else {
                                setNewWebhookEvents([...events, event].join(', '))
                              }
                            }}
                            className={`px-2 py-1 text-xs rounded transition-colors ${
                              selected
                                ? 'bg-amber-600 text-white'
                                : 'bg-zinc-700 text-zinc-300 hover:bg-zinc-600'
                            }`}
                          >
                            {event}
                          </button>
                        )
                      })}
                    </div>
                  </div>
                  <div className="flex gap-3 pt-2">
                    <button
                      type="button"
                      onClick={() => {
                        setShowCreateModal(false)
                        resetForm()
                      }}
                      className="flex-1 px-4 py-2 bg-zinc-800 hover:bg-zinc-700 text-white rounded-lg font-medium transition-colors"
                    >
                      Cancel
                    </button>
                    <button
                      type="submit"
                      disabled={createMutation.isPending || !newWebhookEvents}
                      className="flex-1 px-4 py-2 bg-amber-600 hover:bg-amber-700 disabled:bg-amber-800 text-white rounded-lg font-medium transition-colors"
                    >
                      {createMutation.isPending ? 'Creating...' : 'Create Webhook'}
                    </button>
                  </div>
                </form>
              </>
            )}
          </div>
        </div>
      )}

      {/* Deliveries modal */}
      {showDeliveriesModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-zinc-900 rounded-lg border border-zinc-800 w-full max-w-2xl p-6 max-h-[80vh] overflow-hidden flex flex-col">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-white">Delivery History</h3>
              <button
                onClick={() => setShowDeliveriesModal(null)}
                className="p-2 text-zinc-400 hover:text-white hover:bg-zinc-800 rounded-lg transition-colors"
              >
                <XCircle className="w-5 h-5" />
              </button>
            </div>

            <div className="overflow-y-auto flex-1">
              {!deliveries?.length ? (
                <div className="p-8 text-center text-zinc-400">No deliveries yet</div>
              ) : (
                <div className="space-y-2">
                  {deliveries.map((delivery) => (
                    <div
                      key={delivery.id}
                      className="p-3 bg-zinc-800 rounded-lg flex items-center justify-between"
                    >
                      <div className="flex items-center gap-3">
                        {delivery.status === 'success' ? (
                          <CheckCircle className="w-5 h-5 text-green-400" />
                        ) : delivery.status === 'failed' ? (
                          <XCircle className="w-5 h-5 text-red-400" />
                        ) : (
                          <Clock className="w-5 h-5 text-amber-400" />
                        )}
                        <div>
                          <div className="text-white font-medium">{delivery.event_type}</div>
                          <div className="text-sm text-zinc-400">
                            {new Date(delivery.created_at).toLocaleString()}
                            {delivery.duration_ms && ` - ${delivery.duration_ms}ms`}
                          </div>
                        </div>
                      </div>
                      <div className="text-right">
                        {delivery.response_status_code && (
                          <span className={`font-mono text-sm ${
                            delivery.response_status_code < 300 ? 'text-green-400' : 'text-red-400'
                          }`}>
                            {delivery.response_status_code}
                          </span>
                        )}
                        {delivery.error_message && (
                          <div className="text-xs text-red-400 max-w-[200px] truncate" title={delivery.error_message}>
                            {delivery.error_message}
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
