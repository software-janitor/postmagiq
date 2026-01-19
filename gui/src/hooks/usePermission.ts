import { useWorkspaceStore, WorkspaceRole } from '../stores/workspaceStore'

// Scope definitions matching backend api/auth/scopes.py
export type Scope =
  | 'content:read'
  | 'content:write'
  | 'strategy:read'
  | 'strategy:write'
  | 'workflow:read'
  | 'workflow:execute'
  | 'team:read'
  | 'team:manage'
  | 'billing:read'
  | 'billing:manage'
  | 'workspace:settings'
  | 'workspace:delete'
  | 'workspace:users'
  | 'admin'

// Role to scopes mapping (must match backend ROLE_SCOPES)
const ROLE_SCOPES: Record<WorkspaceRole, Set<Scope>> = {
  owner: new Set([
    'content:read',
    'content:write',
    'strategy:read',
    'strategy:write',
    'workflow:read',
    'workflow:execute',
    'team:read',
    'team:manage',
    'billing:read',
    'billing:manage',
    'workspace:settings',
    'workspace:delete',
    'workspace:users',
    'admin',
  ]),
  admin: new Set([
    'content:read',
    'content:write',
    'strategy:read',
    'strategy:write',
    'workflow:read',
    'workflow:execute',
    'team:read',
    'team:manage',
    'billing:read',
    'workspace:settings',
    'workspace:users',
  ]),
  editor: new Set([
    'content:read',
    'content:write',
    'strategy:read',
    'workflow:read',
    'workflow:execute',
    'team:read',
  ]),
  viewer: new Set([
    'content:read',
    'strategy:read',
    'workflow:read',
    'team:read',
    'billing:read',
  ]),
}

/**
 * Hook to check if the current user has a specific permission scope
 * in the current workspace.
 */
export function usePermission(scope: Scope): boolean {
  const { workspaces, currentWorkspaceId } = useWorkspaceStore()
  const currentWorkspace = workspaces.find((w) => w.id === currentWorkspaceId)

  if (!currentWorkspace) {
    return false
  }

  const roleScopes = ROLE_SCOPES[currentWorkspace.role]
  return roleScopes?.has(scope) ?? false
}

/**
 * Hook to check multiple permissions at once.
 * Returns true if the user has ALL of the specified scopes.
 */
export function usePermissions(scopes: Scope[]): boolean {
  const { workspaces, currentWorkspaceId } = useWorkspaceStore()
  const currentWorkspace = workspaces.find((w) => w.id === currentWorkspaceId)

  if (!currentWorkspace) {
    return false
  }

  const roleScopes = ROLE_SCOPES[currentWorkspace.role]
  if (!roleScopes) return false

  return scopes.every((scope) => roleScopes.has(scope))
}

/**
 * Hook to check if the user has any of the specified permissions.
 * Returns true if the user has AT LEAST ONE of the specified scopes.
 */
export function useAnyPermission(scopes: Scope[]): boolean {
  const { workspaces, currentWorkspaceId } = useWorkspaceStore()
  const currentWorkspace = workspaces.find((w) => w.id === currentWorkspaceId)

  if (!currentWorkspace) {
    return false
  }

  const roleScopes = ROLE_SCOPES[currentWorkspace.role]
  if (!roleScopes) return false

  return scopes.some((scope) => roleScopes.has(scope))
}

/**
 * Get the current user's role in the current workspace.
 */
export function useCurrentRole(): WorkspaceRole | null {
  const { workspaces, currentWorkspaceId } = useWorkspaceStore()
  const currentWorkspace = workspaces.find((w) => w.id === currentWorkspaceId)
  return currentWorkspace?.role ?? null
}
