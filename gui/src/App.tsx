import { Routes, Route, Navigate } from 'react-router-dom'
import { useEffect } from 'react'
import MainLayout from './components/layout/MainLayout'
import Dashboard from './pages/Dashboard'
import LiveWorkflow from './pages/LiveWorkflow'
import RunHistory from './pages/RunHistory'
import RunDetail from './pages/RunDetail'
import Editor from './pages/Editor'
import StoryWorkflow from './pages/StoryWorkflow'
import Settings from './pages/Settings'
import Onboarding from './pages/Onboarding'
import VoiceLearning from './pages/VoiceLearning'
import FinishedPosts from './pages/FinishedPosts'
import Strategy from './pages/Strategy'
import Strategies from './pages/Strategies'
import VoiceProfiles from './pages/VoiceProfiles'
import TeamSettings from './pages/TeamSettings'
import Approvals from './pages/Approvals'
import WhitelabelSettings from './pages/settings/WhitelabelSettings'
import PrivacySettings from './pages/settings/PrivacySettings'
import AdminAnalytics from './pages/admin/Analytics'

// Public pages (no auth required)
import Privacy from './pages/Privacy'
import Terms from './pages/Terms'

// Auth pages
import Login from './pages/auth/Login'
import Register from './pages/auth/Register'
import AcceptInvite from './pages/auth/AcceptInvite'
import ForgotPassword from './pages/auth/ForgotPassword'
import ResetPassword from './pages/auth/ResetPassword'

// Stores
import { useAuthStore } from './stores/authStore'
import { useWorkspaceStore } from './stores/workspaceStore'

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, tokens, fetchMe } = useAuthStore()

  useEffect(() => {
    if (tokens && !isAuthenticated) {
      fetchMe()
    }
  }, [tokens, isAuthenticated, fetchMe])

  if (!isAuthenticated && !tokens) {
    return <Navigate to="/auth/login" replace />
  }

  return <>{children}</>
}

function WorkspaceLoader({ children }: { children: React.ReactNode }) {
  const { fetchWorkspaces, workspaces } = useWorkspaceStore()
  const { isAuthenticated } = useAuthStore()

  useEffect(() => {
    if (isAuthenticated && workspaces.length === 0) {
      fetchWorkspaces()
    }
  }, [isAuthenticated, workspaces.length, fetchWorkspaces])

  return <>{children}</>
}

function App() {
  return (
    <Routes>
      {/* Public routes (no auth required) */}
      <Route path="/privacy" element={<Privacy />} />
      <Route path="/terms" element={<Terms />} />

      {/* Auth routes (no layout) */}
      <Route path="/auth/login" element={<Login />} />
      <Route path="/auth/register" element={<Register />} />
      <Route path="/auth/forgot-password" element={<ForgotPassword />} />
      <Route path="/auth/reset-password" element={<ResetPassword />} />
      <Route path="/auth/invite" element={<AcceptInvite />} />

      {/* Protected routes with layout */}
      <Route
        path="/*"
        element={
          <ProtectedRoute>
            <WorkspaceLoader>
              <MainLayout>
                <Routes>
                  <Route path="/" element={<Dashboard />} />
                  <Route path="/workflow" element={<LiveWorkflow />} />
                  <Route path="/story" element={<StoryWorkflow />} />
                  <Route path="/finished" element={<FinishedPosts />} />
                  <Route path="/runs" element={<RunHistory />} />
                  <Route path="/runs/:runId" element={<RunDetail />} />
                  <Route path="/editor" element={<Editor />} />
                  <Route path="/settings" element={<Settings />} />
                  <Route path="/onboarding" element={<Onboarding />} />
                  <Route path="/strategy" element={<Strategy />} />
                  <Route path="/strategies" element={<Strategies />} />
                  <Route path="/voice" element={<VoiceLearning />} />
                  <Route path="/voice-profiles" element={<VoiceProfiles />} />
                  <Route path="/team" element={<TeamSettings />} />
                  <Route path="/approvals" element={<Approvals />} />
                  <Route path="/settings/whitelabel" element={<WhitelabelSettings />} />
                  <Route path="/settings/privacy" element={<PrivacySettings />} />
                  <Route path="/admin/analytics" element={<AdminAnalytics />} />
                </Routes>
              </MainLayout>
            </WorkspaceLoader>
          </ProtectedRoute>
        }
      />
    </Routes>
  )
}

export default App
