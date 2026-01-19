import { useState, useRef } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Target, Users, BookOpen, FileText, Loader2, RefreshCw, Calendar, ChevronDown, ChevronUp, Crosshair, Edit2, Check, X, BarChart3, Upload, TrendingUp, Eye, Heart, MessageCircle, Share2, MousePointer, ExternalLink } from 'lucide-react'
import { Link } from 'react-router-dom'
import { clsx } from 'clsx'
import { fetchExistingStrategy, ExistingChapter } from '../api/onboarding'
import { apiGet, apiPut } from '../api/client'
import { useWorkspaceStore } from '../stores/workspaceStore'
import { useThemeClasses } from '../hooks/useThemeClasses'
import AIAssistant from '../components/AIAssistant'
import ThemeIcon from '../components/ThemeIcon'

interface Post {
  id: string
  workspace_id: string
  post_number: number
  chapter_id: string
  topic: string
  shape: string | null
  cadence: string | null
  entry_point: string | null
  status: string
  guidance: string | null
  story_used: string | null
  published_url: string | null
  assignee_id: string | null
  due_date: string | null
  priority: number | null
  estimated_hours: number | null
}

interface AnalyticsImport {
  id: number
  platform_name: string
  filename: string
  import_date: string
  row_count: number | null
  status: string
  error_message: string | null
}

interface PostMetric {
  id: number
  post_id: number | null
  platform_name: string
  external_url: string | null
  post_date: string | null
  impressions: number | null
  engagement_count: number | null
  engagement_rate: number | null
  likes: number | null
  comments: number | null
  shares: number | null
  clicks: number | null
  metric_date: string
  impressions_delta: number | null
  reactions_delta: number | null
  last_updated: string | null
}

interface DailyMetric {
  id: number
  platform_name: string
  metric_date: string
  impressions: number | null
  engagements: number | null
}

interface FollowerMetric {
  id: number
  platform_name: string
  metric_date: string
  new_followers: number | null
  total_followers: number | null
}

interface AudienceDemographic {
  id: number
  platform_name: string
  category: string
  value: string
  percentage: number | null
  metric_date: string | null
}

interface AnalyticsSummary {
  total_impressions: number
  total_engagements: number
  total_likes: number
  total_comments: number
  total_shares: number
  total_clicks: number
  avg_engagement_rate: number | null
  post_count: number
  top_posts: PostMetric[]
}

export default function Strategy() {
  const userId = 1  // Hardcode for now, will support multi-user later
  const [activeTab, setActiveTab] = useState<'content' | 'analytics'>('content')
  const [analyticsSubTab, setAnalyticsSubTab] = useState<'overview' | 'demographics' | 'timeseries'>('overview')
  const [expandedChapter, setExpandedChapter] = useState<string | null>(null)
  const [editingPost, setEditingPost] = useState<string | null>(null)
  const [editedTopic, setEditedTopic] = useState('')
  const [uploadingPlatform, setUploadingPlatform] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const queryClient = useQueryClient()
  const workspaceId = useWorkspaceStore((s) => s.currentWorkspaceId)
  const theme = useThemeClasses()

  const { data: strategy, isLoading, error, refetch } = useQuery({
    queryKey: ['strategy', workspaceId],
    queryFn: () => fetchExistingStrategy(),
    enabled: !!workspaceId,
  })

  // Fetch posts for the expanded chapter
  const { data: allPosts } = useQuery({
    queryKey: ['posts', workspaceId],
    queryFn: () => apiGet<Post[]>(`/v1/w/${workspaceId}/posts`),
    enabled: !!workspaceId,
  })

  // Analytics queries
  const { data: analyticsSummary, isLoading: analyticsLoading, refetch: refetchAnalytics } = useQuery({
    queryKey: ['analytics-summary', userId],
    queryFn: () => apiGet<AnalyticsSummary>(`/analytics/users/${userId}/summary`),
    enabled: activeTab === 'analytics',
  })

  const { data: analyticsImports } = useQuery({
    queryKey: ['analytics-imports', userId],
    queryFn: () => apiGet<{ imports: AnalyticsImport[] }>(`/analytics/users/${userId}/imports`),
    enabled: activeTab === 'analytics',
  })

  // Daily metrics for time series
  const { data: dailyMetrics } = useQuery({
    queryKey: ['analytics-daily', userId],
    queryFn: () => apiGet<{ metrics: DailyMetric[] }>(`/analytics/users/${userId}/daily`),
    enabled: activeTab === 'analytics' && analyticsSubTab === 'timeseries',
  })

  // Follower metrics
  const { data: followerMetrics } = useQuery({
    queryKey: ['analytics-followers', userId],
    queryFn: () => apiGet<{ metrics: FollowerMetric[]; latest_total: number | null }>(`/analytics/users/${userId}/followers`),
    enabled: activeTab === 'analytics',
  })

  // Audience demographics
  const { data: audienceDemographics } = useQuery({
    queryKey: ['analytics-demographics', userId],
    queryFn: () => apiGet<{ demographics: AudienceDemographic[] }>(`/analytics/users/${userId}/demographics`),
    enabled: activeTab === 'analytics' && analyticsSubTab === 'demographics',
  })

  // Update post mutation
  const updatePostMutation = useMutation({
    mutationFn: ({ postId, topic }: { postId: string; topic: string }) =>
      apiPut(`/v1/w/${workspaceId}/posts/${postId}`, { topic }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['posts', workspaceId] })
      setEditingPost(null)
      setEditedTopic('')
    },
  })

  // Analytics upload mutation
  const uploadAnalyticsMutation = useMutation({
    mutationFn: async ({ platform, file }: { platform: string; file: File }) => {
      const formData = new FormData()
      formData.append('user_id', String(userId))
      formData.append('platform', platform)
      formData.append('file', file)

      const response = await fetch('/api/analytics/import', {
        method: 'POST',
        body: formData,
      })
      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || 'Upload failed')
      }
      return response.json()
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['analytics-summary', userId] })
      queryClient.invalidateQueries({ queryKey: ['analytics-imports', userId] })
      setUploadingPlatform(null)
    },
    onError: () => {
      setUploadingPlatform(null)
    },
  })

  const startEditing = (post: Post) => {
    setEditingPost(post.id)
    setEditedTopic(post.topic)
  }

  const saveEdit = (postId: string) => {
    updatePostMutation.mutate({ postId, topic: editedTopic })
  }

  const cancelEdit = () => {
    setEditingPost(null)
    setEditedTopic('')
  }

  const handleUploadClick = (platform: string) => {
    setUploadingPlatform(platform)
    fileInputRef.current?.click()
  }

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file && uploadingPlatform) {
      uploadAnalyticsMutation.mutate({ platform: uploadingPlatform, file })
    }
    // Reset file input
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  const formatNumber = (num: number | null | undefined): string => {
    if (num === null || num === undefined) return '0'
    if (num >= 1000000) return `${(num / 1000000).toFixed(1)}M`
    if (num >= 1000) return `${(num / 1000).toFixed(1)}K`
    return num.toString()
  }

  const getPlatformColor = (platform: string) => {
    switch (platform) {
      case 'linkedin': return 'bg-blue-600 hover:bg-blue-500'
      case 'threads': return 'bg-fuchsia-600 hover:bg-fuchsia-500'
      case 'x':
      case 'twitter': return 'bg-zinc-600 hover:bg-zinc-500'
      default: return 'bg-zinc-600 hover:bg-zinc-500'
    }
  }

  const getPlatformIcon = (platform: string) => {
    switch (platform) {
      case 'linkedin': return 'in'
      case 'threads': return '@'
      case 'x':
      case 'twitter': return 'X'
      default: return '?'
    }
  }

  const getChapterPosts = (chapterId: string) => {
    return allPosts?.filter(p => p.chapter_id === chapterId)?.sort((a, b) => a.post_number - b.post_number) || []
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'published': return 'bg-green-600/20 text-green-400'
      case 'ready': return 'bg-blue-600/20 text-blue-400'
      case 'needs_story': return 'bg-yellow-600/20 text-yellow-400'
      default: return 'bg-zinc-600/20 text-zinc-400'
    }
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 className={clsx('w-8 h-8 animate-spin', theme.textPrimary)} />
        <span className="ml-3 text-zinc-400">Loading strategy...</span>
      </div>
    )
  }

  if (error || !strategy?.exists) {
    return (
      <div className="flex flex-col items-center justify-center h-full space-y-4">
        <ThemeIcon className={clsx('w-16 h-16', theme.textMuted)} />
        <h2 className="text-xl font-semibold text-white">No Strategy Found</h2>
        <p className="text-zinc-400">Set up your content strategy to get started.</p>
        <Link
          to="/onboarding"
          className={clsx('px-6 py-3 text-white rounded-lg bg-gradient-to-r', theme.gradient, theme.gradientHover)}
        >
          Create Strategy
        </Link>
      </div>
    )
  }

  const { goal, chapters, summary } = strategy
  const progressPercent = summary ? (summary.completed_posts / summary.total_posts) * 100 : 0

  return (
    <div className="space-y-6 max-w-5xl">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <ThemeIcon className={clsx('w-8 h-8', theme.iconPrimary)} />
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-2xl font-bold text-white">Content Strategy</h1>
              <span className={clsx(
                'px-2 py-0.5 text-xs font-semibold rounded-full uppercase',
                goal?.strategy_type === 'daily' && 'bg-blue-600/20 text-blue-400',
                goal?.strategy_type === 'campaign' && 'bg-purple-600/20 text-purple-400',
                (!goal?.strategy_type || goal?.strategy_type === 'series') && theme.bgMuted, theme.textPrimary
              )}>
                {goal?.strategy_type || 'series'}
              </span>
            </div>
            <p className="text-sm text-zinc-500">
              {goal?.target_audience || 'Your content strategy'}
            </p>
          </div>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => refetch()}
            className="px-4 py-2 bg-zinc-800 text-zinc-300 rounded-lg hover:bg-zinc-700 flex items-center gap-2"
          >
            <RefreshCw className="w-4 h-4" />
            Refresh
          </button>
          <Link
            to="/onboarding"
            className={clsx('px-4 py-2 text-white rounded-lg bg-gradient-to-r', theme.gradient, theme.gradientHover)}
          >
            Edit Strategy
          </Link>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-zinc-800">
        <button
          onClick={() => setActiveTab('content')}
          className={clsx(
            'px-4 py-2 text-sm font-medium rounded-t-lg transition-colors flex items-center gap-2',
            activeTab === 'content'
              ? clsx('bg-zinc-800 border-b-2', theme.textPrimary, theme.border)
              : 'text-zinc-400 hover:text-white hover:bg-zinc-800/50'
          )}
        >
          <BookOpen className="w-4 h-4" />
          Content Plan
        </button>
        <button
          onClick={() => setActiveTab('analytics')}
          className={clsx(
            'px-4 py-2 text-sm font-medium rounded-t-lg transition-colors flex items-center gap-2',
            activeTab === 'analytics'
              ? clsx('bg-zinc-800 border-b-2', theme.textPrimary, theme.border)
              : 'text-zinc-400 hover:text-white hover:bg-zinc-800/50'
          )}
        >
          <BarChart3 className="w-4 h-4" />
          Analytics
        </button>
      </div>

      {/* Hidden file input for uploads */}
      <input
        type="file"
        ref={fileInputRef}
        onChange={handleFileChange}
        accept=".csv,.xls,.xlsx"
        className="hidden"
      />

      {activeTab === 'content' && (
      <>
      {/* Overview Card */}
      <div className="bg-gradient-to-br from-zinc-900 to-zinc-800 border border-zinc-700 rounded-xl p-6">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left: What this is */}
          <div className="lg:col-span-2 space-y-4">
            {/* Signature Thesis */}
            <div>
              <div className={clsx('flex items-center gap-2 mb-2', theme.textPrimary)}>
                <Target className="w-4 h-4" />
                <span className="text-xs font-semibold uppercase tracking-wide">Core Message</span>
              </div>
              <p className="text-xl text-white font-medium leading-relaxed">
                {goal?.signature_thesis}
              </p>
            </div>

            {/* Meta info */}
            <div className="flex flex-wrap gap-4 pt-2">
              {goal?.positioning && (
                <div className="flex items-center gap-2">
                  <Crosshair className="w-4 h-4 text-zinc-500" />
                  <span className="text-sm text-zinc-400">
                    <span className="text-zinc-500">Positioning:</span> {goal.positioning}
                  </span>
                </div>
              )}
              {goal?.target_audience && (
                <div className="flex items-center gap-2">
                  <Users className="w-4 h-4 text-zinc-500" />
                  <span className="text-sm text-zinc-400">
                    <span className="text-zinc-500">Audience:</span> {goal.target_audience}
                  </span>
                </div>
              )}
            </div>
          </div>

          {/* Right: Progress */}
          <div className="bg-zinc-800/50 rounded-lg p-4 space-y-3">
            <div className="text-center">
              <div className={clsx('text-4xl font-bold', theme.textPrimary)}>
                {summary?.completed_posts || 0}
                <span className="text-xl text-zinc-500">/{summary?.total_posts || 0}</span>
              </div>
              <div className="text-sm text-zinc-500">posts completed</div>
            </div>

            {/* Progress bar */}
            <div className="h-2 bg-zinc-700 rounded-full overflow-hidden">
              <div
                className={clsx('h-full bg-gradient-to-r transition-all', theme.gradient)}
                style={{ width: `${progressPercent}%` }}
              />
            </div>

            <div className="flex justify-between text-xs text-zinc-500">
              {(!goal?.strategy_type || goal?.strategy_type === 'series') ? (
                <>
                  <span>{summary?.total_chapters || 0} chapters</span>
                  <span>{summary?.weeks_total || 0} weeks</span>
                </>
              ) : (
                <span>{goal?.strategy_type === 'daily' ? 'Daily posts' : 'Campaign'}</span>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* How it works - only show if platform uses enemies */}
      {chapters?.some((c: ExistingChapter) => c.theme) && chapters?.some((c: ExistingChapter) => c.theme) && (
        <div className="bg-zinc-900/50 border border-zinc-800 rounded-lg p-4">
          <p className="text-sm text-zinc-400">
            <span className={clsx(theme.textPrimary, 'font-medium')}>How this works:</span>{' '}
            Chapters with an "enemy" attack a specific misconception.
            Posts tell stories from your experience that illustrate why the enemy is wrong.
            Not all posts need an enemy - Field Notes are observations without a thesis.
          </p>
        </div>
      )}

      {/* Chapters - only for series strategies */}
      {(!goal?.strategy_type || goal?.strategy_type === 'series') && (
      <div className="space-y-3">
        <div className="flex items-center gap-2 px-1">
          <BookOpen className={clsx('w-5 h-5', theme.iconPrimary)} />
          <h2 className="text-lg font-semibold text-white">Chapters</h2>
        </div>

        <div className="space-y-2">
          {chapters?.map((chapter: ExistingChapter) => {
            const isExpanded = expandedChapter === chapter.id
            const progress = chapter.post_count > 0
              ? (chapter.completed_count / chapter.post_count) * 100
              : 0
            const isComplete = chapter.completed_count === chapter.post_count

            return (
              <div
                key={chapter.id}
                className={clsx(
                  'bg-zinc-900 border rounded-lg overflow-hidden transition-colors',
                  isExpanded ? theme.border : 'border-zinc-800'
                )}
              >
                {/* Chapter header - clickable */}
                <button
                  onClick={() => setExpandedChapter(isExpanded ? null : chapter.id)}
                  className="w-full p-4 flex items-center gap-4 text-left hover:bg-zinc-800/50 transition-colors"
                >
                  {/* Chapter number */}
                  <div className={clsx(
                    'w-10 h-10 rounded-lg flex items-center justify-center font-bold text-sm',
                    isComplete
                      ? 'bg-green-600/20 text-green-400'
                      : clsx(theme.bgMuted, theme.textPrimary)
                  )}>
                    {chapter.chapter_number}
                  </div>

                  {/* Title and meta */}
                  <div className="flex-1 min-w-0">
                    <h3 className="text-white font-medium truncate">{chapter.title}</h3>
                    <div className="flex items-center gap-3 text-sm text-zinc-500">
                      <span className="flex items-center gap-1">
                        <Calendar className="w-3 h-3" />
                        Weeks {chapter.weeks_start}-{chapter.weeks_end}
                      </span>
                      {chapters?.some((c: ExistingChapter) => c.theme) && chapter.theme && (
                        <>
                          <span>•</span>
                          <span className={clsx(theme.textMuted)}>Enemy: {chapter.theme}</span>
                        </>
                      )}
                    </div>
                  </div>

                  {/* Progress */}
                  <div className="flex items-center gap-3">
                    <div className="text-right">
                      <div className="flex items-center gap-1 text-sm">
                        <FileText className="w-4 h-4 text-zinc-500" />
                        <span className={theme.textPrimary}>{chapter.completed_count}</span>
                        <span className="text-zinc-500">/{chapter.post_count}</span>
                      </div>
                    </div>
                    {isExpanded ? (
                      <ChevronUp className="w-5 h-5 text-zinc-500" />
                    ) : (
                      <ChevronDown className="w-5 h-5 text-zinc-500" />
                    )}
                  </div>
                </button>

                {/* Progress bar */}
                <div className="h-1 bg-zinc-800">
                  <div
                    className={clsx(
                      'h-full transition-all',
                      isComplete
                        ? 'bg-green-500'
                        : clsx('bg-gradient-to-r', theme.gradient)
                    )}
                    style={{ width: `${progress}%` }}
                  />
                </div>

                {/* Expanded details */}
                {isExpanded && (
                  <div className="p-4 pt-3 border-t border-zinc-800 bg-zinc-950/50">
                    <div className="space-y-3">
                      {/* Enemy description - only show if platform uses enemies and chapter has one */}
                      {chapters?.some((c: ExistingChapter) => c.theme) && chapter.theme && (
                        <div>
                          <div className="text-xs font-semibold text-red-400 uppercase tracking-wide mb-1">
                            The Enemy
                          </div>
                          <p className="text-sm text-zinc-300">{chapter.theme}</p>
                          {chapter.theme_description && (
                            <p className="text-sm text-zinc-500 mt-1">{chapter.theme_description}</p>
                          )}
                        </div>
                      )}

                      {/* Chapter goal */}
                      <div>
                        <div className="text-xs font-semibold text-green-400 uppercase tracking-wide mb-1">
                          Goal
                        </div>
                        <p className="text-sm text-zinc-400">
                          {chapters?.some((c: ExistingChapter) => c.theme) && chapter.theme ? (
                            <>Write {chapter.post_count} posts showing why "{chapter.theme.toLowerCase()}" fails, using specific stories from your experience.</>
                          ) : (
                            <>Write {chapter.post_count} posts for this chapter.</>
                          )}
                        </p>
                      </div>

                      {/* Posts List */}
                      <div>
                        <div className={clsx('text-xs font-semibold uppercase tracking-wide mb-2', theme.textPrimary)}>
                          Posts
                        </div>
                        <div className="space-y-1">
                          {getChapterPosts(chapter.id).map((post) => (
                            <div
                              key={post.id}
                              className="flex items-center gap-2 p-2 bg-zinc-800/50 rounded-lg group"
                            >
                              <span className="text-xs text-zinc-500 w-8">#{post.post_number}</span>
                              {editingPost === post.id ? (
                                <div className="flex-1 flex items-center gap-2">
                                  <input
                                    type="text"
                                    value={editedTopic}
                                    onChange={(e) => setEditedTopic(e.target.value)}
                                    className={clsx('flex-1 px-2 py-1 bg-zinc-900 border border-zinc-700 rounded text-sm text-white focus:outline-none', theme.borderHover)}
                                    autoFocus
                                    onKeyDown={(e) => {
                                      if (e.key === 'Enter') saveEdit(post.id)
                                      if (e.key === 'Escape') cancelEdit()
                                    }}
                                  />
                                  <button
                                    onClick={() => saveEdit(post.id)}
                                    disabled={updatePostMutation.isPending}
                                    className="p-1 text-green-400 hover:bg-green-600/20 rounded"
                                  >
                                    <Check className="w-4 h-4" />
                                  </button>
                                  <button
                                    onClick={cancelEdit}
                                    className="p-1 text-red-400 hover:bg-red-600/20 rounded"
                                  >
                                    <X className="w-4 h-4" />
                                  </button>
                                </div>
                              ) : (
                                <>
                                  <span className={clsx(
                                    'flex-1 text-sm',
                                    post.topic === 'TBD' ? 'text-yellow-400 italic' : 'text-zinc-300'
                                  )}>
                                    {post.topic}
                                  </span>
                                  <span className={clsx(
                                    'px-2 py-0.5 text-xs rounded',
                                    getStatusColor(post.status)
                                  )}>
                                    {post.status.replace('_', ' ')}
                                  </span>
                                  <button
                                    onClick={() => startEditing(post)}
                                    className={clsx('p-1 text-zinc-500 opacity-0 group-hover:opacity-100 transition-opacity', theme.borderHover)}
                                    title="Edit topic"
                                  >
                                    <Edit2 className="w-3 h-3" />
                                  </button>
                                </>
                              )}
                            </div>
                          ))}
                        </div>
                      </div>

                      {/* Action */}
                      <div className="pt-2">
                        <Link
                          to={`/story?chapter=${chapter.id}`}
                          className={clsx('inline-flex items-center gap-2 px-4 py-2 text-white text-sm rounded-lg bg-gradient-to-r', theme.gradient, theme.gradientHover)}
                        >
                          <FileText className="w-4 h-4" />
                          Write Next Post
                        </Link>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )
          })}
        </div>
      </div>
      )}

      {/* Daily strategy - simple write button */}
      {goal?.strategy_type === 'daily' && (
        <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-6 text-center">
          <h2 className="text-lg font-semibold text-white mb-2">Daily Content</h2>
          <p className="text-zinc-400 mb-4">
            Write your next daily post to build your audience.
          </p>
          <Link
            to="/story"
            className={clsx('inline-flex items-center gap-2 px-6 py-3 text-white rounded-lg bg-gradient-to-r', theme.gradient, theme.gradientHover)}
          >
            <FileText className="w-5 h-5" />
            Write Next Post
          </Link>
        </div>
      )}
      </>
      )}

      {/* Analytics Tab */}
      {activeTab === 'analytics' && (
        <div className="space-y-6">
          {/* Upload Section */}
          <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-6">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h2 className="text-lg font-semibold text-white flex items-center gap-2">
                  <Upload className={clsx('w-5 h-5', theme.iconPrimary)} />
                  Import Analytics
                </h2>
                <p className="text-sm text-zinc-500 mt-1">
                  Upload analytics exports (CSV, XLS, or XLSX)
                </p>
              </div>
              <button
                onClick={() => refetchAnalytics()}
                className="px-3 py-1.5 bg-zinc-800 text-zinc-300 rounded-lg hover:bg-zinc-700 flex items-center gap-2 text-sm"
              >
                <RefreshCw className="w-4 h-4" />
                Refresh
              </button>
            </div>

            {/* Platform Upload Buttons */}
            <div className="flex flex-wrap gap-3">
              {[
                { id: 'linkedin', name: 'LinkedIn', icon: 'in' },
                { id: 'threads', name: 'Threads', icon: '@' },
                { id: 'x', name: 'X / Twitter', icon: 'X' },
              ].map((platform) => (
                <button
                  key={platform.id}
                  onClick={() => handleUploadClick(platform.id)}
                  disabled={uploadAnalyticsMutation.isPending && uploadingPlatform === platform.id}
                  className={clsx(
                    'px-4 py-2 rounded-lg text-white font-medium flex items-center gap-2 transition-colors',
                    getPlatformColor(platform.id),
                    uploadAnalyticsMutation.isPending && uploadingPlatform === platform.id && 'opacity-50 cursor-not-allowed'
                  )}
                >
                  {uploadAnalyticsMutation.isPending && uploadingPlatform === platform.id ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <span className="w-5 h-5 flex items-center justify-center text-xs font-bold bg-white/20 rounded">
                      {platform.icon}
                    </span>
                  )}
                  Upload {platform.name}
                </button>
              ))}
            </div>

            {/* Upload Error */}
            {uploadAnalyticsMutation.isError && (
              <div className="mt-4 p-3 bg-red-900/20 border border-red-800 rounded-lg text-red-400 text-sm">
                Upload failed: {(uploadAnalyticsMutation.error as Error).message}
              </div>
            )}

            {/* Recent Imports */}
            {analyticsImports?.imports && analyticsImports.imports.length > 0 && (
              <div className="mt-6">
                <h3 className="text-sm font-medium text-zinc-400 mb-3">Recent Imports</h3>
                <div className="space-y-2">
                  {analyticsImports.imports.slice(0, 5).map((imp) => (
                    <div
                      key={imp.id}
                      className="flex items-center justify-between p-3 bg-zinc-800/50 rounded-lg"
                    >
                      <div className="flex items-center gap-3">
                        <span className={clsx(
                          'w-8 h-8 flex items-center justify-center rounded text-xs font-bold',
                          getPlatformColor(imp.platform_name),
                          'text-white'
                        )}>
                          {getPlatformIcon(imp.platform_name)}
                        </span>
                        <div>
                          <div className="text-sm text-white">{imp.filename}</div>
                          <div className="text-xs text-zinc-500">
                            {new Date(imp.import_date).toLocaleDateString()}
                          </div>
                        </div>
                      </div>
                      <div className="flex items-center gap-3">
                        <span className="text-sm text-zinc-400">
                          {imp.row_count || 0} rows
                        </span>
                        <span className={clsx(
                          'px-2 py-0.5 text-xs rounded',
                          imp.status === 'processed' ? 'bg-green-600/20 text-green-400' :
                          imp.status === 'error' ? 'bg-red-600/20 text-red-400' :
                          'bg-yellow-600/20 text-yellow-400'
                        )}>
                          {imp.status}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Analytics Sub-tabs */}
          <div className="flex gap-2 border-b border-zinc-800 pb-1">
            {[
              { id: 'overview', label: 'Overview' },
              { id: 'demographics', label: 'Demographics' },
              { id: 'timeseries', label: 'Time Series' },
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setAnalyticsSubTab(tab.id as 'overview' | 'demographics' | 'timeseries')}
                className={clsx(
                  'px-4 py-2 text-sm font-medium rounded-t-lg transition-colors',
                  analyticsSubTab === tab.id
                    ? 'bg-zinc-800 text-white border-t border-l border-r border-zinc-700'
                    : 'text-zinc-400 hover:text-white'
                )}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {/* Overview Tab */}
          {analyticsSubTab === 'overview' && (
            <>
              {analyticsLoading ? (
                <div className="flex items-center justify-center py-12">
                  <Loader2 className={clsx('w-8 h-8 animate-spin', theme.textPrimary)} />
                  <span className="ml-3 text-zinc-400">Loading analytics...</span>
                </div>
              ) : analyticsSummary && analyticsSummary.post_count > 0 ? (
                <>
                  <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                    <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-4">
                      <div className="flex items-center gap-2 text-zinc-400 mb-2">
                        <Eye className="w-4 h-4" />
                        <span className="text-xs uppercase tracking-wide">Impressions</span>
                      </div>
                      <div className="text-2xl font-bold text-white">
                        {formatNumber(analyticsSummary.total_impressions)}
                      </div>
                    </div>

                    <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-4">
                      <div className="flex items-center gap-2 text-zinc-400 mb-2">
                        <TrendingUp className="w-4 h-4" />
                        <span className="text-xs uppercase tracking-wide">Engagements</span>
                      </div>
                      <div className="text-2xl font-bold text-white">
                        {formatNumber(analyticsSummary.total_engagements)}
                      </div>
                    </div>

                    <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-4">
                      <div className="flex items-center gap-2 text-zinc-400 mb-2">
                        <Users className="w-4 h-4" />
                        <span className="text-xs uppercase tracking-wide">Followers</span>
                      </div>
                      <div className="text-2xl font-bold text-white">
                        {formatNumber(followerMetrics?.latest_total || 0)}
                      </div>
                    </div>

                    <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-4">
                      <div className="flex items-center gap-2 text-zinc-400 mb-2">
                        <BarChart3 className="w-4 h-4" />
                        <span className="text-xs uppercase tracking-wide">Avg. Engagement</span>
                      </div>
                      <div className="text-2xl font-bold text-white">
                        {analyticsSummary.avg_engagement_rate?.toFixed(2) || '0'}%
                      </div>
                    </div>
                  </div>

                  {/* Secondary Metrics */}
                  <div className="grid grid-cols-4 gap-4">
                    <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-4 flex items-center gap-3">
                      <Heart className="w-5 h-5 text-pink-400" />
                      <div>
                        <div className="text-lg font-bold text-white">
                          {formatNumber(analyticsSummary.total_likes)}
                        </div>
                        <div className="text-xs text-zinc-500">Likes</div>
                      </div>
                    </div>

                    <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-4 flex items-center gap-3">
                      <MessageCircle className="w-5 h-5 text-blue-400" />
                      <div>
                        <div className="text-lg font-bold text-white">
                          {formatNumber(analyticsSummary.total_comments)}
                        </div>
                        <div className="text-xs text-zinc-500">Comments</div>
                      </div>
                    </div>

                    <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-4 flex items-center gap-3">
                      <Share2 className="w-5 h-5 text-green-400" />
                      <div>
                        <div className="text-lg font-bold text-white">
                          {formatNumber(analyticsSummary.total_shares)}
                        </div>
                        <div className="text-xs text-zinc-500">Shares</div>
                      </div>
                    </div>

                    <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-4 flex items-center gap-3">
                      <MousePointer className={clsx('w-5 h-5', theme.iconPrimary)} />
                      <div>
                        <div className="text-lg font-bold text-white">
                          {formatNumber(analyticsSummary.total_clicks)}
                        </div>
                        <div className="text-xs text-zinc-500">Clicks</div>
                      </div>
                    </div>
                  </div>

                  {/* Top Performing Posts */}
                  {analyticsSummary.top_posts && analyticsSummary.top_posts.length > 0 && (
                    <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-6">
                      <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                        <TrendingUp className="w-5 h-5 text-green-400" />
                        Top Performing Posts
                      </h2>
                      <div className="space-y-3">
                        {analyticsSummary.top_posts.map((post, idx) => (
                          <div
                            key={post.id}
                            className="flex items-center gap-4 p-4 bg-zinc-800/50 rounded-lg"
                          >
                            <div className={clsx('w-8 h-8 flex items-center justify-center rounded-lg font-bold', theme.bgMuted, theme.textPrimary)}>
                              #{idx + 1}
                            </div>
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center gap-2">
                                <span className={clsx(
                                  'px-2 py-0.5 text-xs rounded font-medium',
                                  getPlatformColor(post.platform_name),
                                  'text-white'
                                )}>
                                  {post.platform_name}
                                </span>
                                {post.metric_date && (
                                  <span className="text-xs text-zinc-500">
                                    {new Date(post.metric_date).toLocaleDateString()}
                                  </span>
                                )}
                              </div>
                              {post.external_url && (
                                <a
                                  href={post.external_url}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="text-sm text-blue-400 hover:underline flex items-center gap-1 mt-1 truncate"
                                >
                                  View post <ExternalLink className="w-3 h-3" />
                                </a>
                              )}
                            </div>
                            <div className="flex items-center gap-6 text-sm">
                              <div className="text-center">
                                <div className="text-white font-medium">{formatNumber(post.impressions)}</div>
                                {post.impressions_delta && post.impressions_delta > 0 && (
                                  <div className="text-xs text-green-400">+{formatNumber(post.impressions_delta)}</div>
                                )}
                                <div className="text-xs text-zinc-500">views</div>
                              </div>
                              <div className="text-center">
                                <div className="text-white font-medium">{formatNumber(post.engagement_count)}</div>
                                <div className="text-xs text-zinc-500">engages</div>
                              </div>
                              <div className="text-center">
                                <div className="text-white font-medium">{post.engagement_rate?.toFixed(1) || '0'}%</div>
                                <div className="text-xs text-zinc-500">rate</div>
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </>
              ) : (
                <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-12 text-center">
                  <BarChart3 className={clsx('w-12 h-12 mx-auto mb-4', theme.textMuted)} />
                  <h3 className="text-lg font-medium text-white mb-2">No Analytics Data Yet</h3>
                  <p className="text-zinc-400">
                    Upload your first analytics CSV to see insights about your content performance.
                  </p>
                </div>
              )}
            </>
          )}

          {/* Demographics Tab */}
          {analyticsSubTab === 'demographics' && (
            <div className="space-y-6">
              {audienceDemographics?.demographics && audienceDemographics.demographics.length > 0 ? (
                <>
                  {/* Group demographics by category */}
                  {['job_title', 'location', 'industry', 'seniority', 'company_size'].map((category) => {
                    const categoryData = audienceDemographics.demographics.filter(d => d.category === category)
                    if (categoryData.length === 0) return null

                    const categoryLabels: Record<string, string> = {
                      job_title: 'Job Titles',
                      job_function: 'Job Functions',
                      location: 'Locations',
                      industry: 'Industries',
                      seniority: 'Seniority',
                      company_size: 'Company Size',
                    }

                    return (
                      <div key={category} className="bg-zinc-900 border border-zinc-800 rounded-xl p-6">
                        <h3 className="text-lg font-semibold text-white mb-4">
                          {categoryLabels[category] || category}
                        </h3>
                        <div className="space-y-3">
                          {categoryData.slice(0, 10).map((demo, idx) => (
                            <div key={idx} className="flex items-center gap-4">
                              <div className="flex-1">
                                <div className="flex items-center justify-between mb-1">
                                  <span className="text-sm text-white">{demo.value}</span>
                                  <span className="text-sm text-zinc-400">{demo.percentage?.toFixed(1)}%</span>
                                </div>
                                <div className="h-2 bg-zinc-800 rounded-full overflow-hidden">
                                  <div
                                    className={clsx('h-full rounded-full bg-gradient-to-r', theme.gradient)}
                                    style={{ width: `${Math.min(demo.percentage || 0, 100)}%` }}
                                  />
                                </div>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )
                  })}
                </>
              ) : (
                <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-12 text-center">
                  <Users className={clsx('w-12 h-12 mx-auto mb-4', theme.textMuted)} />
                  <h3 className="text-lg font-medium text-white mb-2">No Demographics Data Yet</h3>
                  <p className="text-zinc-400">
                    Upload a LinkedIn Content Export with the DEMOGRAPHICS sheet to see audience breakdowns.
                  </p>
                </div>
              )}
            </div>
          )}

          {/* Time Series Tab */}
          {analyticsSubTab === 'timeseries' && (
            <div className="space-y-6">
              {dailyMetrics?.metrics && dailyMetrics.metrics.length > 0 ? (
                <>
                  {/* Daily Impressions */}
                  <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-6">
                    <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                      <Eye className="w-5 h-5 text-blue-400" />
                      Daily Impressions
                    </h3>
                    <div className="space-y-2">
                      {dailyMetrics.metrics.slice(0, 14).reverse().map((metric, idx) => (
                        <div key={idx} className="flex items-center gap-4">
                          <span className="text-xs text-zinc-500 w-20">
                            {new Date(metric.metric_date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                          </span>
                          <div className="flex-1 h-4 bg-zinc-800 rounded-full overflow-hidden">
                            <div
                              className="h-full bg-blue-500 rounded-full"
                              style={{
                                width: `${Math.min(
                                  ((metric.impressions || 0) / Math.max(...dailyMetrics.metrics.map(m => m.impressions || 0))) * 100,
                                  100
                                )}%`
                              }}
                            />
                          </div>
                          <span className="text-sm text-white w-16 text-right">
                            {formatNumber(metric.impressions)}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Daily Engagements */}
                  <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-6">
                    <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                      <TrendingUp className="w-5 h-5 text-green-400" />
                      Daily Engagements
                    </h3>
                    <div className="space-y-2">
                      {dailyMetrics.metrics.slice(0, 14).reverse().map((metric, idx) => (
                        <div key={idx} className="flex items-center gap-4">
                          <span className="text-xs text-zinc-500 w-20">
                            {new Date(metric.metric_date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                          </span>
                          <div className="flex-1 h-4 bg-zinc-800 rounded-full overflow-hidden">
                            <div
                              className="h-full bg-green-500 rounded-full"
                              style={{
                                width: `${Math.min(
                                  ((metric.engagements || 0) / Math.max(...dailyMetrics.metrics.map(m => m.engagements || 0), 1)) * 100,
                                  100
                                )}%`
                              }}
                            />
                          </div>
                          <span className="text-sm text-white w-16 text-right">
                            {formatNumber(metric.engagements)}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                </>
              ) : followerMetrics?.metrics && followerMetrics.metrics.length > 0 ? (
                <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-6">
                  <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                    <Users className="w-5 h-5 text-purple-400" />
                    Follower Growth
                  </h3>
                  <div className="space-y-2">
                    {followerMetrics.metrics.slice(0, 14).reverse().map((metric, idx) => (
                      <div key={idx} className="flex items-center gap-4">
                        <span className="text-xs text-zinc-500 w-20">
                          {new Date(metric.metric_date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                        </span>
                        <div className="flex-1">
                          <span className="text-sm text-white">
                            {formatNumber(metric.total_followers)} followers
                          </span>
                          {metric.new_followers && metric.new_followers > 0 && (
                            <span className="text-xs text-green-400 ml-2">
                              +{metric.new_followers}
                            </span>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              ) : (
                <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-12 text-center">
                  <BarChart3 className={clsx('w-12 h-12 mx-auto mb-4', theme.textMuted)} />
                  <h3 className="text-lg font-medium text-white mb-2">No Time Series Data Yet</h3>
                  <p className="text-zinc-400">
                    Upload LinkedIn Content Exports with ENGAGEMENT or FOLLOWERS sheets to see trends over time.
                  </p>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* AI Assistant */}
      <AIAssistant context="strategy" />
    </div>
  )
}
