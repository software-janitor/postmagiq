import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { CreditCard, Check, Zap, Settings2 } from 'lucide-react'
import { clsx } from 'clsx'
import { apiGet, apiPost } from '../api/client'
import { useWorkspaceStore } from '../stores/workspaceStore'
import { useThemeClasses } from '../hooks/useThemeClasses'
import { useEffectiveFlags } from '../stores/flagsStore'
import UsageBar from '../components/UsageBar'
import BillingSection from '../components/BillingSection'
import NotificationSettings from '../components/NotificationSettings'
import WorkflowConfigSelector from '../components/WorkflowConfigSelector'

interface UsageSummary {
  period_start: string
  period_end: string
  posts: { used: number; limit: number; overage: number; unlimited: boolean }
  storage: { used_bytes: number; limit_bytes: number; used_gb: number; limit_gb: number; unlimited: boolean }
  api_calls: { used: number; limit: number; unlimited: boolean }
  subscription: { tier_name: string; tier_slug: string; status: string; overage_enabled: boolean }
}

interface Tier {
  id: string
  name: string
  slug: string
  description: string | null
  price_monthly: number
  price_yearly: number
  posts_per_month: number
  workspaces_limit: number
  members_per_workspace: number
  storage_gb: number
  overage_enabled: boolean
  priority_support: boolean
  api_access: boolean
  white_label: boolean
}

export default function Settings() {
  const theme = useThemeClasses()
  const flags = useEffectiveFlags()
  const { currentWorkspaceId, currentRole } = useWorkspaceStore()
  const [selectedWorkflowConfig, setSelectedWorkflowConfig] = useState<string | null>(null)

  const canChangeWorkflowConfig = currentRole === 'owner' || currentRole === 'admin'

  const { data: usage, isLoading: usageLoading } = useQuery({
    queryKey: ['usage', currentWorkspaceId],
    queryFn: () => apiGet<UsageSummary>(`/v1/w/${currentWorkspaceId}/usage`),
    enabled: !!currentWorkspaceId,
  })

  const { data: tiers } = useQuery({
    queryKey: ['tiers', currentWorkspaceId],
    queryFn: () => apiGet<Tier[]>(`/v1/w/${currentWorkspaceId}/usage/tiers`),
    enabled: !!currentWorkspaceId,
  })

  const { data: agents } = useQuery({
    queryKey: ['agents'],
    queryFn: () => apiGet<{ agents: Array<{ name: string; enabled: boolean; context_window: number; cost_per_1k: { input: number; output: number } }> }>('/config/agents'),
  })

  const { data: personas } = useQuery({
    queryKey: ['personas'],
    queryFn: () => apiGet<{ personas: Array<{ name: string; path: string }> }>('/config/personas'),
  })

  return (
    <div className="space-y-6 max-w-4xl">
      <h1 className="text-2xl font-bold text-white">Settings</h1>

      {/* Usage & Billing */}
      <div className="bg-zinc-900 rounded-lg border border-zinc-800">
        <div className="p-4 border-b border-zinc-800 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <CreditCard className={clsx('w-5 h-5', theme.iconPrimary)} />
            <h2 className="text-lg font-semibold text-white">Usage & Billing</h2>
          </div>
          {usage?.subscription && (
            <span className={clsx('px-3 py-1 rounded-full text-sm font-medium', theme.bgMuted, theme.textPrimary)}>
              {usage.subscription.tier_name}
            </span>
          )}
        </div>
        <div className="p-4 space-y-6">
          {usageLoading ? (
            <div className="text-zinc-400">Loading usage data...</div>
          ) : usage ? (
            <>
              {/* Current Period */}
              <div className="text-sm text-zinc-400">
                Billing period: {new Date(usage.period_start).toLocaleDateString()} -{' '}
                {new Date(usage.period_end).toLocaleDateString()}
              </div>

              {/* Usage Bars */}
              <div className="space-y-4">
                <UsageBar
                  label="Posts Created"
                  used={usage.posts.used}
                  limit={usage.posts.limit}
                  unlimited={usage.posts.unlimited}
                />
                <UsageBar
                  label="Storage"
                  used={usage.storage.used_gb}
                  limit={usage.storage.limit_gb}
                  unit="GB"
                  unlimited={usage.storage.unlimited}
                />
                <UsageBar
                  label="API Calls"
                  used={usage.api_calls.used}
                  limit={usage.api_calls.limit}
                  unlimited={usage.api_calls.unlimited}
                />
              </div>

              {/* Overage Notice */}
              {usage.posts.overage > 0 && (
                <div className={clsx('p-3 rounded-lg text-sm', theme.bgMuted, theme.textPrimary)}>
                  You have {usage.posts.overage} overage posts this period.
                  {usage.subscription.overage_enabled
                    ? ' Additional charges may apply.'
                    : ' Consider upgrading your plan.'}
                </div>
              )}
            </>
          ) : (
            <div className="text-zinc-400">No workspace selected</div>
          )}
        </div>
      </div>

      {/* Available Plans */}
      {tiers && tiers.length > 0 && (
        <div className="bg-zinc-900 rounded-lg border border-zinc-800">
          <div className="p-4 border-b border-zinc-800">
            <h2 className="text-lg font-semibold text-white">Available Plans</h2>
          </div>
          <div className="p-4">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {tiers.map((tier) => {
                const isCurrent = tier.slug === usage?.subscription?.tier_slug
                return (
                  <div
                    key={tier.id}
                    className={clsx(
                      'p-4 rounded-lg border',
                      isCurrent
                        ? clsx(theme.border, theme.bgMuted)
                        : 'border-zinc-700 bg-zinc-800/50'
                    )}
                  >
                    <div className="flex items-center justify-between mb-2">
                      <h3 className="text-lg font-semibold text-white">{tier.name}</h3>
                      {isCurrent && (
                        <span className={clsx('text-xs px-2 py-0.5 rounded-full font-medium bg-gradient-to-r text-white', theme.gradient)}>
                          Current
                        </span>
                      )}
                    </div>
                    <div className="text-2xl font-bold text-white mb-1">
                      ${tier.price_monthly}
                      <span className="text-sm text-zinc-400 font-normal">/mo</span>
                    </div>
                    <p className="text-sm text-zinc-400 mb-4">{tier.description}</p>
                    <ul className="space-y-2 text-sm">
                      <li className="flex items-center gap-2 text-zinc-300">
                        <Check className="w-4 h-4 text-green-400" />
                        {tier.posts_per_month === 0
                          ? 'Unlimited posts'
                          : `${tier.posts_per_month} posts/month`}
                      </li>
                      <li className="flex items-center gap-2 text-zinc-300">
                        <Check className="w-4 h-4 text-green-400" />
                        {tier.workspaces_limit} workspace{tier.workspaces_limit > 1 ? 's' : ''}
                      </li>
                      <li className="flex items-center gap-2 text-zinc-300">
                        <Check className="w-4 h-4 text-green-400" />
                        {tier.members_per_workspace} team member{tier.members_per_workspace > 1 ? 's' : ''}
                      </li>
                      <li className="flex items-center gap-2 text-zinc-300">
                        <Check className="w-4 h-4 text-green-400" />
                        {tier.storage_gb} GB storage
                      </li>
                      {tier.priority_support && (
                        <li className="flex items-center gap-2 text-zinc-300">
                          <Zap className={clsx('w-4 h-4', theme.iconPrimary)} />
                          Priority support
                        </li>
                      )}
                      {tier.api_access && (
                        <li className="flex items-center gap-2 text-zinc-300">
                          <Check className="w-4 h-4 text-green-400" />
                          API access
                        </li>
                      )}
                    </ul>
                    {!isCurrent && (
                      <button className={clsx('w-full mt-4 px-4 py-2 text-white rounded-lg font-medium transition-colors bg-gradient-to-r', theme.gradient, theme.gradientHover)}>
                        Upgrade
                      </button>
                    )}
                  </div>
                )
              })}
            </div>
          </div>
        </div>
      )}

      {/* Payment Methods & Invoices */}
      <BillingSection />

      {/* Notification Preferences */}
      <NotificationSettings />

      {/* Workflow Configuration */}
      <div className="bg-zinc-900 rounded-lg border border-zinc-800">
        <div className="p-4 border-b border-zinc-800 flex items-center gap-2">
          <Settings2 className={clsx('w-5 h-5', theme.iconPrimary)} />
          <h2 className="text-lg font-semibold text-white">Workflow Configuration</h2>
        </div>
        <div className="p-4 space-y-4">
          <div>
            <label className="block text-sm text-zinc-400 mb-2">
              Default Workflow Config
            </label>
            <p className="text-sm text-zinc-500 mb-3">
              Select the default workflow configuration for this workspace. This determines which AI models and settings are used when running workflows.
            </p>
            {canChangeWorkflowConfig ? (
              <WorkflowConfigSelector
                value={selectedWorkflowConfig}
                onChange={setSelectedWorkflowConfig}
                className="w-full max-w-md"
              />
            ) : (
              <div className="text-sm text-zinc-500">
                Only workspace owners and admins can change the workflow configuration.
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Agents */}
      <div className="bg-slate-800 rounded-lg border border-slate-700">
        <div className="p-4 border-b border-slate-700">
          <h2 className="text-lg font-semibold text-white">Agents</h2>
        </div>
        <div className="p-4">
          <table className="w-full">
            <thead>
              <tr className="text-left text-sm text-slate-400">
                <th className="pb-2">Agent</th>
                <th className="pb-2">Status</th>
                <th className="pb-2">Context Window</th>
                <th className="pb-2">Cost (Input)</th>
                <th className="pb-2">Cost (Output)</th>
              </tr>
            </thead>
            <tbody className="text-white">
              {agents?.agents.map((agent) => (
                <tr key={agent.name}>
                  <td className="py-2 font-medium">{agent.name}</td>
                  <td className="py-2">
                    <span className={`px-2 py-1 rounded text-xs ${
                      agent.enabled ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'
                    }`}>
                      {agent.enabled ? 'Enabled' : 'Disabled'}
                    </span>
                  </td>
                  <td className="py-2 text-slate-300">
                    {agent.context_window?.toLocaleString() || '-'}
                  </td>
                  <td className="py-2 text-slate-300">
                    ${agent.cost_per_1k?.input?.toFixed(5) || '-'}/1k
                  </td>
                  <td className="py-2 text-slate-300">
                    ${agent.cost_per_1k?.output?.toFixed(5) || '-'}/1k
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Personas */}
      {flags.show_ai_personas && (
        <div className="bg-slate-800 rounded-lg border border-slate-700">
          <div className="p-4 border-b border-slate-700">
            <h2 className="text-lg font-semibold text-white">Personas</h2>
          </div>
          <div className="p-4">
            <table className="w-full">
              <thead>
                <tr className="text-left text-sm text-slate-400">
                  <th className="pb-2">Name</th>
                  <th className="pb-2">Path</th>
                </tr>
              </thead>
              <tbody className="text-white">
                {personas?.personas.map((persona) => (
                  <tr key={persona.name}>
                    <td className="py-2 font-medium">{persona.name}</td>
                    <td className="py-2 text-slate-300 font-mono text-sm">{persona.path}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Circuit Breaker */}
      <div className="bg-slate-800 rounded-lg border border-slate-700">
        <div className="p-4 border-b border-slate-700">
          <h2 className="text-lg font-semibold text-white">Circuit Breaker Limits</h2>
        </div>
        <div className="p-4 grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm text-slate-400 mb-1">State Visit Limit</label>
            <input
              type="number"
              defaultValue={3}
              className="w-full px-3 py-2 bg-slate-900 border border-slate-600 rounded-lg text-white"
            />
          </div>
          <div>
            <label className="block text-sm text-slate-400 mb-1">Transition Limit</label>
            <input
              type="number"
              defaultValue={20}
              className="w-full px-3 py-2 bg-slate-900 border border-slate-600 rounded-lg text-white"
            />
          </div>
          <div>
            <label className="block text-sm text-slate-400 mb-1">Timeout (seconds)</label>
            <input
              type="number"
              defaultValue={1800}
              className="w-full px-3 py-2 bg-slate-900 border border-slate-600 rounded-lg text-white"
            />
          </div>
          <div>
            <label className="block text-sm text-slate-400 mb-1">Cost Limit ($)</label>
            <input
              type="number"
              step="0.01"
              defaultValue={5.00}
              className="w-full px-3 py-2 bg-slate-900 border border-slate-600 rounded-lg text-white"
            />
          </div>
        </div>
      </div>
    </div>
  )
}
