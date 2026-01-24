import { useState, useRef, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { ChevronDown, Check, Zap, Server, Cloud } from 'lucide-react'
import { apiGet } from '../api/client'

interface WorkflowConfig {
  id: string
  name: string
  slug: string
  description: string | null
  environment: 'production' | 'development' | 'staging'
  features: string[] | null
  tier_required: string | null
  enabled: boolean
  is_default: boolean
  created_at: string
}

interface WorkflowConfigListResponse {
  configs: WorkflowConfig[]
  default_slug: string | null
}

interface WorkflowConfigSelectorProps {
  value: string | null
  onChange: (slug: string) => void
  className?: string
}

const environmentIcons: Record<string, typeof Zap> = {
  production: Cloud,
  development: Server,
  staging: Zap,
}

export default function WorkflowConfigSelector({
  value,
  onChange,
  className = '',
}: WorkflowConfigSelectorProps) {
  const [isOpen, setIsOpen] = useState(false)
  const dropdownRef = useRef<HTMLDivElement>(null)

  const { data, isLoading, error } = useQuery({
    queryKey: ['workflow-configs'],
    queryFn: () => apiGet<WorkflowConfigListResponse>('/workflow-configs'),
    staleTime: 60000, // Cache for 1 minute
  })

  const configs = data?.configs || []
  const defaultSlug = data?.default_slug
  const selectedConfig = configs.find((c) => c.slug === value) ||
    configs.find((c) => c.slug === defaultSlug)

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const handleSelect = (config: WorkflowConfig) => {
    onChange(config.slug)
    setIsOpen(false)
  }

  if (isLoading) {
    return (
      <div className={`px-3 py-2 text-zinc-400 text-sm bg-zinc-900 border border-zinc-700 rounded-lg ${className}`}>
        Loading configs...
      </div>
    )
  }

  if (error) {
    return (
      <div className={`px-3 py-2 text-red-400 text-sm bg-zinc-900 border border-red-700/50 rounded-lg ${className}`}>
        Failed to load configs
      </div>
    )
  }

  if (configs.length === 0) {
    return (
      <div className={`px-3 py-2 text-zinc-400 text-sm bg-zinc-900 border border-zinc-700 rounded-lg ${className}`}>
        No workflow configs available
      </div>
    )
  }

  const Icon = selectedConfig ? environmentIcons[selectedConfig.environment] || Cloud : Cloud

  return (
    <div className={`relative ${className}`} ref={dropdownRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center justify-between w-full px-3 py-2 bg-zinc-900 border border-zinc-700 rounded-lg text-sm text-white hover:border-amber-600/50 transition-colors"
      >
        <div className="flex items-center gap-2 min-w-0">
          <Icon className="w-4 h-4 text-amber-400 flex-shrink-0" />
          <span className="truncate">{selectedConfig?.name || 'Select workflow'}</span>
        </div>
        <ChevronDown className={`w-4 h-4 text-zinc-400 flex-shrink-0 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
      </button>

      {isOpen && (
        <div className="absolute top-full left-0 right-0 mt-1 bg-zinc-900 border border-zinc-700 rounded-lg shadow-lg overflow-hidden z-50">
          <div className="max-h-64 overflow-y-auto">
            {configs.map((config) => {
              const ConfigIcon = environmentIcons[config.environment] || Cloud
              return (
                <button
                  key={config.id}
                  onClick={() => handleSelect(config)}
                  className="flex items-center justify-between w-full px-3 py-2 text-sm text-left hover:bg-zinc-800 transition-colors"
                >
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <ConfigIcon className="w-4 h-4 text-zinc-400 flex-shrink-0" />
                      <span className="text-white truncate">{config.name}</span>
                      {config.is_default && (
                        <span className="px-1.5 py-0.5 text-xs bg-amber-600/20 text-amber-400 rounded">
                          Default
                        </span>
                      )}
                    </div>
                    {config.description && (
                      <div className="text-xs text-zinc-500 mt-0.5 truncate pl-6">
                        {config.description}
                      </div>
                    )}
                  </div>
                  {config.slug === (value || defaultSlug) && (
                    <Check className="w-4 h-4 text-amber-400 flex-shrink-0 ml-2" />
                  )}
                </button>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}
