import { useState } from 'react'
import { AlertTriangle, X } from 'lucide-react'

interface ConfirmDeleteModalProps {
  isOpen: boolean
  onClose: () => void
  onConfirm: () => void
  isDeleting: boolean
  error: string | null
}

export default function ConfirmDeleteModal({
  isOpen,
  onClose,
  onConfirm,
  isDeleting,
  error,
}: ConfirmDeleteModalProps) {
  const [confirmText, setConfirmText] = useState('')

  const handleClose = () => {
    setConfirmText('')
    onClose()
  }

  const handleConfirm = () => {
    if (confirmText === 'DELETE') {
      onConfirm()
    }
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-zinc-900 rounded-lg border border-zinc-800 w-full max-w-md p-6">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-red-500/20 rounded-lg flex items-center justify-center">
              <AlertTriangle className="w-5 h-5 text-red-400" />
            </div>
            <h3 className="text-lg font-semibold text-white">Delete Account</h3>
          </div>
          <button
            onClick={handleClose}
            className="p-2 text-zinc-400 hover:text-white hover:bg-zinc-800 rounded-lg transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="space-y-4">
          <div className="p-4 bg-red-500/10 border border-red-500/30 rounded-lg">
            <p className="text-red-400 text-sm font-medium mb-2">
              Warning: This action cannot be undone
            </p>
            <p className="text-zinc-400 text-sm">
              Deleting your account will permanently remove:
            </p>
            <ul className="mt-2 space-y-1 text-sm text-zinc-400">
              <li className="flex items-center gap-2">
                <span className="w-1 h-1 bg-red-400 rounded-full" />
                All your personal data and settings
              </li>
              <li className="flex items-center gap-2">
                <span className="w-1 h-1 bg-red-400 rounded-full" />
                Your workspace memberships
              </li>
              <li className="flex items-center gap-2">
                <span className="w-1 h-1 bg-red-400 rounded-full" />
                Your content and drafts (unless owned by workspaces)
              </li>
              <li className="flex items-center gap-2">
                <span className="w-1 h-1 bg-red-400 rounded-full" />
                Your authentication credentials
              </li>
            </ul>
          </div>

          {error && (
            <div className="p-3 bg-red-500/10 border border-red-500/50 rounded-lg text-red-400 text-sm">
              {error}
            </div>
          )}

          <div>
            <label className="block text-sm text-zinc-400 mb-2">
              To confirm, type <span className="text-white font-mono">DELETE</span> below:
            </label>
            <input
              type="text"
              value={confirmText}
              onChange={(e) => setConfirmText(e.target.value)}
              placeholder="Type DELETE to confirm"
              className="w-full px-3 py-2 bg-zinc-800 border border-zinc-700 rounded-lg text-white focus:outline-none focus:border-red-500 font-mono"
              autoComplete="off"
            />
          </div>

          <div className="flex gap-3 pt-2">
            <button
              type="button"
              onClick={handleClose}
              disabled={isDeleting}
              className="flex-1 px-4 py-2 bg-zinc-800 hover:bg-zinc-700 disabled:bg-zinc-800 text-white rounded-lg font-medium transition-colors"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={handleConfirm}
              disabled={confirmText !== 'DELETE' || isDeleting}
              className="flex-1 px-4 py-2 bg-red-600 hover:bg-red-700 disabled:bg-red-900 disabled:text-red-400 text-white rounded-lg font-medium transition-colors"
            >
              {isDeleting ? 'Deleting...' : 'Delete Account'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
