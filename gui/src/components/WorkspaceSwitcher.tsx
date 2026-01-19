import { useState, useRef, useEffect } from 'react'
import { ChevronDown, Plus, Check, Building2 } from 'lucide-react'
import { useWorkspaceStore, Workspace } from '../stores/workspaceStore'

export default function WorkspaceSwitcher() {
  const { workspaces, currentWorkspaceId, setCurrentWorkspace, isLoading } = useWorkspaceStore()
  const [isOpen, setIsOpen] = useState(false)
  const dropdownRef = useRef<HTMLDivElement>(null)

  const currentWorkspace = workspaces.find((w) => w.id === currentWorkspaceId)

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

  const handleSelect = (workspace: Workspace) => {
    setCurrentWorkspace(workspace.id)
    setIsOpen(false)
  }

  if (isLoading) {
    return (
      <div className="px-3 py-2 text-zinc-400 text-sm">
        Loading workspaces...
      </div>
    )
  }

  if (workspaces.length === 0) {
    return (
      <button
        className="flex items-center gap-2 px-3 py-2 bg-amber-600/20 text-amber-400 rounded-lg text-sm hover:bg-amber-600/30 w-full"
      >
        <Plus className="w-4 h-4" />
        Create Workspace
      </button>
    )
  }

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center justify-between w-full px-3 py-2 bg-zinc-900 border border-zinc-700 rounded-lg text-sm text-white hover:border-amber-600/50 transition-colors"
      >
        <div className="flex items-center gap-2 min-w-0">
          <Building2 className="w-4 h-4 text-amber-400 flex-shrink-0" />
          <span className="truncate">{currentWorkspace?.name || 'Select workspace'}</span>
        </div>
        <ChevronDown className={`w-4 h-4 text-zinc-400 flex-shrink-0 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
      </button>

      {isOpen && (
        <div className="absolute top-full left-0 right-0 mt-1 bg-zinc-900 border border-zinc-700 rounded-lg shadow-lg overflow-hidden z-50">
          <div className="max-h-64 overflow-y-auto">
            {workspaces.map((workspace) => (
              <button
                key={workspace.id}
                onClick={() => handleSelect(workspace)}
                className="flex items-center justify-between w-full px-3 py-2 text-sm text-left hover:bg-zinc-800 transition-colors"
              >
                <div className="min-w-0">
                  <div className="text-white truncate">{workspace.name}</div>
                  <div className="text-xs text-zinc-500">{workspace.member_count} members</div>
                </div>
                {workspace.id === currentWorkspaceId && (
                  <Check className="w-4 h-4 text-amber-400 flex-shrink-0" />
                )}
              </button>
            ))}
          </div>
          <div className="border-t border-zinc-700">
            <button
              className="flex items-center gap-2 w-full px-3 py-2 text-sm text-amber-400 hover:bg-zinc-800 transition-colors"
            >
              <Plus className="w-4 h-4" />
              Create workspace
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
