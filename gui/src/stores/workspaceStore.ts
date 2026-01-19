import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { apiGet } from '../api/client'

export type WorkspaceRole = 'owner' | 'admin' | 'editor' | 'viewer'

export interface Workspace {
  id: string
  name: string
  slug: string
  description: string | null
  role: WorkspaceRole
  member_count: number
}

interface WorkspaceState {
  workspaces: Workspace[]
  currentWorkspaceId: string | null
  isLoading: boolean
  error: string | null

  // Computed
  currentWorkspace: Workspace | null

  // Actions
  setWorkspaces: (workspaces: Workspace[]) => void
  setCurrentWorkspace: (workspaceId: string | null) => void
  fetchWorkspaces: () => Promise<void>
  clear: () => void
}

export const useWorkspaceStore = create<WorkspaceState>()(
  persist(
    (set, get) => ({
      workspaces: [],
      currentWorkspaceId: null,
      isLoading: false,
      error: null,

      currentWorkspace: null as Workspace | null,

      setWorkspaces: (workspaces) => {
        const { currentWorkspaceId } = get()
        const currentWorkspace = workspaces.find((w) => w.id === currentWorkspaceId) ?? null
        set({ workspaces, currentWorkspace })
      },

      setCurrentWorkspace: (workspaceId) => {
        const { workspaces } = get()
        const currentWorkspace = workspaces.find((w) => w.id === workspaceId) ?? null
        set({ currentWorkspaceId: workspaceId, currentWorkspace })
      },

      fetchWorkspaces: async () => {
        set({ isLoading: true, error: null })
        try {
          const workspaces = await apiGet<Workspace[]>('/v1/workspaces')

          // Auto-select first workspace if none selected
          const { currentWorkspaceId } = get()
          let selectedId = currentWorkspaceId
          if (!selectedId && workspaces.length > 0) {
            selectedId = workspaces[0].id
          }

          const currentWorkspace = workspaces.find((w) => w.id === selectedId) ?? null
          set({ workspaces, isLoading: false, currentWorkspaceId: selectedId, currentWorkspace })
        } catch (error) {
          set({
            isLoading: false,
            error: error instanceof Error ? error.message : 'Failed to fetch workspaces',
          })
        }
      },

      clear: () => set({
        workspaces: [],
        currentWorkspaceId: null,
        currentWorkspace: null,
        error: null,
      }),
    }),
    {
      name: 'workspace-storage',
      partialize: (state) => ({
        currentWorkspaceId: state.currentWorkspaceId,
      }),
    }
  )
)

// Helper to get current workspace ID for API requests
export function getCurrentWorkspaceId(): string | null {
  return useWorkspaceStore.getState().currentWorkspaceId
}
