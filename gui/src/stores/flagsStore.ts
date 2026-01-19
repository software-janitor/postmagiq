import { create } from 'zustand'
import { useAuthStore } from './authStore'

export interface FeatureFlags {
  show_internal_workflow: boolean
  show_image_tools: boolean
  show_ai_personas: boolean
  show_live_workflow: boolean
  show_state_editor: boolean
  show_approvals: boolean
  show_teams: boolean
  show_strategy_admin: boolean
  show_costs: boolean
  max_circuit_breaker: number
}

// Default flags for unauthenticated users (most restrictive)
const DEFAULT_FLAGS: FeatureFlags = {
  show_internal_workflow: false,
  show_image_tools: false,
  show_ai_personas: false,
  show_live_workflow: false,
  show_state_editor: false,
  show_approvals: false,
  show_teams: false,
  show_strategy_admin: false,
  show_costs: false,
  max_circuit_breaker: 1,
}

// User-level flags (for when owner toggles to user view)
const USER_FLAGS: FeatureFlags = {
  show_internal_workflow: false,
  show_image_tools: false,
  show_ai_personas: false,
  show_live_workflow: false,
  show_state_editor: false,
  show_approvals: false,
  show_teams: false,
  show_strategy_admin: false,
  show_costs: false,
  max_circuit_breaker: 1,
}

interface FlagsState {
  serverFlags: FeatureFlags  // Flags from server (based on actual role)
  isLoading: boolean
  error: string | null
  lastFetched: number | null

  // Actions
  fetchFlags: () => Promise<void>
  clearFlags: () => void

  // Computed - respects viewAsUser toggle
  getEffectiveFlags: () => FeatureFlags
}

const API_BASE = '/api/v1'

export const useFlagsStore = create<FlagsState>()((set, get) => ({
  serverFlags: DEFAULT_FLAGS,
  isLoading: false,
  error: null,
  lastFetched: null,

  fetchFlags: async () => {
    const tokens = useAuthStore.getState().tokens
    if (!tokens?.access_token) {
      set({ serverFlags: DEFAULT_FLAGS, error: null })
      return
    }

    // Don't refetch if we fetched recently (within 5 minutes)
    const { lastFetched } = get()
    if (lastFetched && Date.now() - lastFetched < 5 * 60 * 1000) {
      return
    }

    set({ isLoading: true, error: null })

    try {
      const response = await fetch(`${API_BASE}/auth/me/flags`, {
        headers: {
          'Authorization': `Bearer ${tokens.access_token}`,
        },
      })

      if (!response.ok) {
        if (response.status === 401) {
          // Try to refresh token
          const refreshed = await useAuthStore.getState().refresh()
          if (refreshed) {
            return get().fetchFlags()
          }
        }
        throw new Error('Failed to fetch flags')
      }

      const flags = await response.json()
      set({
        serverFlags: flags,
        isLoading: false,
        lastFetched: Date.now(),
      })
    } catch (error) {
      set({
        isLoading: false,
        error: error instanceof Error ? error.message : 'Failed to fetch flags',
        serverFlags: DEFAULT_FLAGS,
      })
    }
  },

  clearFlags: () => set({
    serverFlags: DEFAULT_FLAGS,
    error: null,
    lastFetched: null,
  }),

  // Get effective flags respecting viewAsUser toggle
  getEffectiveFlags: () => {
    const { user, viewAsUser } = useAuthStore.getState()

    // If owner is viewing as user, return user-level flags
    if (viewAsUser && user?.role === 'owner') {
      return USER_FLAGS
    }

    // Otherwise return server-provided flags
    return get().serverFlags
  },
}))

// Hook to get effective flags (respects viewAsUser toggle)
export function useEffectiveFlags(): FeatureFlags {
  const serverFlags = useFlagsStore((state) => state.serverFlags)
  const user = useAuthStore((state) => state.user)
  const viewAsUser = useAuthStore((state) => state.viewAsUser)

  // If owner is viewing as user, return user-level flags
  if (viewAsUser && user?.role === 'owner') {
    return USER_FLAGS
  }

  return serverFlags
}

// Helper hooks for common flag checks (all respect viewAsUser)
export function useIsOwner(): boolean {
  const user = useAuthStore((state) => state.user)
  const viewAsUser = useAuthStore((state) => state.viewAsUser)
  // When viewing as user, pretend not to be owner for UI purposes
  if (viewAsUser) return false
  return user?.role === 'owner'
}

export function useCanShowCosts(): boolean {
  const flags = useEffectiveFlags()
  return flags.show_costs
}

export function useCanShowImageTools(): boolean {
  const flags = useEffectiveFlags()
  return flags.show_image_tools
}

export function useCanShowWorkflowInternals(): boolean {
  const flags = useEffectiveFlags()
  return flags.show_internal_workflow
}

export function useCanShowTeams(): boolean {
  const flags = useEffectiveFlags()
  return flags.show_teams
}

export function useCanShowApprovals(): boolean {
  const flags = useEffectiveFlags()
  return flags.show_approvals
}

export function useCanShowAIPersonas(): boolean {
  const flags = useEffectiveFlags()
  return flags.show_ai_personas
}
