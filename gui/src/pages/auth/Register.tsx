import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useAuthStore } from '../../stores/authStore'
import AuthLayout from '../../components/layout/AuthLayout'

export default function Register() {
  const navigate = useNavigate()
  const { register, isLoading, error } = useAuthStore()
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [localError, setLocalError] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLocalError(null)

    if (password !== confirmPassword) {
      setLocalError('Passwords do not match')
      return
    }

    if (password.length < 8) {
      setLocalError('Password must be at least 8 characters')
      return
    }

    try {
      await register(email, password, name || undefined)
      navigate('/')
    } catch {
      // Error is handled by the store
    }
  }

  const displayError = localError || error

  return (
    <AuthLayout>
      <h2 className="text-xl font-semibold text-white mb-6">Create account</h2>

      <form onSubmit={handleSubmit} className="space-y-4">
        {displayError && (
          <div className="p-3 bg-red-500/10 border border-red-500/50 rounded-lg text-red-400 text-sm">
            {displayError}
          </div>
        )}

        <div>
          <label htmlFor="name" className="block text-sm text-zinc-400 mb-1">
            Name (optional)
          </label>
          <input
            id="name"
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="w-full px-3 py-2 bg-zinc-800 border border-zinc-700 rounded-lg text-white focus:outline-none focus:border-blue-500"
            placeholder="Your name"
          />
        </div>

        <div>
          <label htmlFor="email" className="block text-sm text-zinc-400 mb-1">
            Email
          </label>
          <input
            id="email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            className="w-full px-3 py-2 bg-zinc-800 border border-zinc-700 rounded-lg text-white focus:outline-none focus:border-blue-500"
            placeholder="you@example.com"
          />
        </div>

        <div>
          <label htmlFor="password" className="block text-sm text-zinc-400 mb-1">
            Password
          </label>
          <input
            id="password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            className="w-full px-3 py-2 bg-zinc-800 border border-zinc-700 rounded-lg text-white focus:outline-none focus:border-blue-500"
            placeholder="••••••••"
          />
        </div>

        <div>
          <label htmlFor="confirmPassword" className="block text-sm text-zinc-400 mb-1">
            Confirm password
          </label>
          <input
            id="confirmPassword"
            type="password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            required
            className="w-full px-3 py-2 bg-zinc-800 border border-zinc-700 rounded-lg text-white focus:outline-none focus:border-blue-500"
            placeholder="••••••••"
          />
        </div>

        <button
          type="submit"
          disabled={isLoading}
          className="w-full py-2 px-4 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-800 disabled:cursor-not-allowed text-white rounded-lg font-medium transition-colors"
        >
          {isLoading ? 'Creating account...' : 'Create account'}
        </button>
      </form>

      <div className="mt-6 text-center text-sm text-zinc-400">
        Already have an account?{' '}
        <Link to="/auth/login" className="text-blue-400 hover:text-blue-300">
          Sign in
        </Link>
      </div>
    </AuthLayout>
  )
}
