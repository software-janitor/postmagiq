import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { Eye, EyeOff } from 'lucide-react'
import { useAuthStore } from '../../stores/authStore'
import AuthLayout from '../../components/layout/AuthLayout'
import { useThemeClasses } from '../../hooks/useThemeClasses'

// Test accounts for development (password: password123)
const TEST_ACCOUNTS = [
  { email: 'owner@example.com', role: 'Owner', color: 'bg-purple-600' },
]

export default function Login() {
  const navigate = useNavigate()
  const { login, isLoading, error } = useAuthStore()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const theme = useThemeClasses()

  const handleTestLogin = (testEmail: string) => {
    setEmail(testEmail)
    setPassword('password123')
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      await login(email, password)
      navigate('/')
    } catch {
      // Error is handled by the store
    }
  }

  return (
    <AuthLayout>
      <h2 className="text-xl font-semibold text-white mb-6">Sign in</h2>

      <form onSubmit={handleSubmit} className="space-y-4">
        {error && (
          <div className="p-3 bg-red-500/10 border border-red-500/50 rounded-lg text-red-400 text-sm">
            {error}
          </div>
        )}

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
            className={`w-full px-3 py-2 bg-zinc-800 border border-zinc-700 rounded-lg text-white focus:outline-none focus:${theme.border}`}
            placeholder="you@example.com"
          />
        </div>

        <div>
          <label htmlFor="password" className="block text-sm text-zinc-400 mb-1">
            Password
          </label>
          <div className="relative">
            <input
              id="password"
              type={showPassword ? 'text' : 'password'}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              className={`w-full px-3 py-2 pr-10 bg-zinc-800 border border-zinc-700 rounded-lg text-white focus:outline-none focus:${theme.border}`}
              placeholder="••••••••"
            />
            <button
              type="button"
              onClick={() => setShowPassword(!showPassword)}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-zinc-400 hover:text-zinc-300"
            >
              {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
            </button>
          </div>
        </div>

        <button
          type="submit"
          disabled={isLoading}
          className={`w-full py-2 px-4 bg-gradient-to-r ${theme.gradient} ${theme.gradientHover} ${theme.gradientDisabled} disabled:cursor-not-allowed text-white rounded-lg font-medium transition-all shadow-lg ${theme.shadow}`}
        >
          {isLoading ? 'Signing in...' : 'Sign in'}
        </button>

        <div className="text-right">
          <Link to="/auth/forgot-password" className={`text-sm text-zinc-400 hover:${theme.textPrimary}`}>
            Forgot password?
          </Link>
        </div>
      </form>

      <div className="mt-6 text-center text-sm text-zinc-400">
        Don't have an account?{' '}
        <Link to="/auth/register" className={`${theme.textPrimary} hover:opacity-80`}>
          Sign up
        </Link>
      </div>

      {/* Dev Test Accounts */}
      <div className="mt-8 pt-6 border-t border-zinc-700">
        <p className="text-xs text-zinc-500 mb-3 text-center">Quick Login (Dev Only)</p>
        <div className="grid grid-cols-2 gap-2">
          {TEST_ACCOUNTS.map((account) => (
            <button
              key={account.email}
              type="button"
              onClick={() => handleTestLogin(account.email)}
              className={`px-3 py-1.5 ${account.color} hover:opacity-90 text-white text-xs rounded font-medium transition-opacity`}
            >
              {account.role}
            </button>
          ))}
        </div>
      </div>
    </AuthLayout>
  )
}
