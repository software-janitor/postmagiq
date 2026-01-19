import { useState, useEffect } from 'react'
import { useNavigate, useSearchParams, Link } from 'react-router-dom'
import { useAuthStore } from '../../stores/authStore'
import AuthLayout from '../../components/layout/AuthLayout'

export default function AcceptInvite() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const token = searchParams.get('token')
  const { isAuthenticated, tokens } = useAuthStore()

  const [status, setStatus] = useState<'loading' | 'success' | 'error' | 'auth-required'>('loading')
  const [error, setError] = useState<string | null>(null)
  const [workspaceName, setWorkspaceName] = useState<string | null>(null)

  useEffect(() => {
    if (!token) {
      setStatus('error')
      setError('Invalid invite link')
      return
    }

    if (!isAuthenticated) {
      setStatus('auth-required')
      return
    }

    acceptInvite()
  }, [token, isAuthenticated])

  const acceptInvite = async () => {
    if (!token || !tokens?.access_token) return

    setStatus('loading')
    try {
      const response = await fetch(`/api/v1/invites/${token}/accept`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${tokens.access_token}`,
        },
      })

      if (!response.ok) {
        const data = await response.json().catch(() => ({}))
        throw new Error(data.detail || 'Failed to accept invite')
      }

      const membership = await response.json()
      setWorkspaceName(membership.workspace_id) // We'd need workspace name from API
      setStatus('success')

      // Redirect to workspace after short delay
      setTimeout(() => {
        navigate(`/w/${membership.workspace_id}`)
      }, 2000)
    } catch (err) {
      setStatus('error')
      setError(err instanceof Error ? err.message : 'Failed to accept invite')
    }
  }

  if (status === 'loading') {
    return (
      <AuthLayout>
        <div className="text-center py-8">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mx-auto mb-4"></div>
          <p className="text-zinc-400">Accepting invitation...</p>
        </div>
      </AuthLayout>
    )
  }

  if (status === 'auth-required') {
    return (
      <AuthLayout>
        <div className="text-center py-4">
          <h2 className="text-xl font-semibold text-white mb-4">Sign in to accept invite</h2>
          <p className="text-zinc-400 mb-6">
            You need to sign in or create an account to join this workspace.
          </p>
          <div className="space-y-3">
            <Link
              to={`/auth/login?redirect=${encodeURIComponent(`/auth/invite?token=${token}`)}`}
              className="block w-full py-2 px-4 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors text-center"
            >
              Sign in
            </Link>
            <Link
              to={`/auth/register?redirect=${encodeURIComponent(`/auth/invite?token=${token}`)}`}
              className="block w-full py-2 px-4 bg-zinc-700 hover:bg-zinc-600 text-white rounded-lg font-medium transition-colors text-center"
            >
              Create account
            </Link>
          </div>
        </div>
      </AuthLayout>
    )
  }

  if (status === 'error') {
    return (
      <AuthLayout>
        <div className="text-center py-4">
          <div className="w-12 h-12 bg-red-500/20 rounded-full flex items-center justify-center mx-auto mb-4">
            <svg className="w-6 h-6 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </div>
          <h2 className="text-xl font-semibold text-white mb-2">Unable to accept invite</h2>
          <p className="text-zinc-400 mb-6">{error}</p>
          <Link
            to="/"
            className="inline-block py-2 px-4 bg-zinc-700 hover:bg-zinc-600 text-white rounded-lg font-medium transition-colors"
          >
            Go to dashboard
          </Link>
        </div>
      </AuthLayout>
    )
  }

  return (
    <AuthLayout>
      <div className="text-center py-4">
        <div className="w-12 h-12 bg-green-500/20 rounded-full flex items-center justify-center mx-auto mb-4">
          <svg className="w-6 h-6 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
        </div>
        <h2 className="text-xl font-semibold text-white mb-2">Welcome to the team!</h2>
        <p className="text-zinc-400 mb-4">
          You've joined {workspaceName || 'the workspace'}. Redirecting...
        </p>
      </div>
    </AuthLayout>
  )
}
