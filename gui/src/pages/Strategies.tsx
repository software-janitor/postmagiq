import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Target, BookOpen, FileText, Trash2, Plus, ChevronRight, Calendar, Loader2 } from 'lucide-react'
import ThemeIcon from '../components/ThemeIcon'
import { Link } from 'react-router-dom'
import { clsx } from 'clsx'
import { fetchExistingStrategy, ExistingChapter } from '../api/onboarding'
import { apiDelete } from '../api/client'
import { useWorkspaceStore } from '../stores/workspaceStore'
import { useThemeClasses } from '../hooks/useThemeClasses'

interface StrategyListItem {
  id: string
  name: string
  type: 'series' | 'daily' | 'campaign'
  thesis: string | null
  chapterCount: number
  postCount: number
  completedCount: number
}

export default function Strategies() {
  const theme = useThemeClasses()
  const [selectedStrategyId, setSelectedStrategyId] = useState<string | null>(null)
  const [showDeleteModal, setShowDeleteModal] = useState<string | null>(null)
  const queryClient = useQueryClient()
  const workspaceId = useWorkspaceStore((s) => s.currentWorkspaceId)

  // Fetch strategy for current workspace
  const { data: strategy, isLoading, error } = useQuery({
    queryKey: ['strategy', workspaceId],
    queryFn: () => fetchExistingStrategy(),
    enabled: !!workspaceId,
  })

  const deleteMutation = useMutation({
    mutationFn: (goalId: string) =>
      apiDelete<{ goal_id: string; chapters_deleted: number; posts_deleted: number }>(
        `/v1/w/${workspaceId}/goals/${goalId}`
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['strategy'] })
      setShowDeleteModal(null)
      setSelectedStrategyId(null)
    },
  })

  // Convert to list format for future multi-strategy support
  const strategies: StrategyListItem[] = strategy?.exists && strategy.goal ? [{
    id: strategy.goal.id,
    name: strategy.goal.signature_thesis?.split('.')[0] || 'Content Strategy',
    type: strategy.goal.strategy_type || 'series',
    thesis: strategy.goal.signature_thesis || null,
    chapterCount: strategy.summary?.total_chapters || 0,
    postCount: strategy.summary?.total_posts || 0,
    completedCount: strategy.summary?.completed_posts || 0,
  }] : []

  const selectedStrategy = strategies.find(s => s.id === selectedStrategyId) || strategies[0]

  return (
    <div className="h-full flex gap-6">
      {/* Strategy List */}
      <div className="w-80 flex-shrink-0 bg-zinc-900 rounded-lg border border-zinc-800 overflow-hidden">
        <div className="p-4 border-b border-zinc-800 flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold text-white">Strategies</h2>
            <p className="text-sm text-zinc-400 mt-1">
              {strategies.length} {strategies.length === 1 ? 'strategy' : 'strategies'}
            </p>
          </div>
          <Link
            to="/onboarding"
            className={clsx('p-2 text-white rounded-lg transition-colors bg-gradient-to-r', theme.gradient, theme.gradientHover)}
            title="Create New Strategy"
          >
            <Plus className="w-5 h-5" />
          </Link>
        </div>

        <div className="overflow-y-auto h-[calc(100%-80px)]">
          {isLoading ? (
            <div className="p-4 text-zinc-400">Loading...</div>
          ) : error ? (
            <div className="p-4 text-red-400">Failed to load strategies</div>
          ) : strategies.length === 0 ? (
            <div className="p-8 text-center">
              <ThemeIcon className={clsx('w-12 h-12 mx-auto mb-3', theme.textMuted)} />
              <p className="text-zinc-400 mb-4">No strategies yet</p>
              <Link
                to="/onboarding"
                className={clsx('inline-flex items-center gap-2 px-4 py-2 text-white rounded-lg bg-gradient-to-r', theme.gradient, theme.gradientHover)}
              >
                <Plus className="w-4 h-4" />
                Create Strategy
              </Link>
            </div>
          ) : (
            <div className="divide-y divide-zinc-800">
              {strategies.map((strat) => {
                const progress = strat.postCount > 0
                  ? (strat.completedCount / strat.postCount) * 100
                  : 0

                return (
                  <button
                    key={strat.id}
                    onClick={() => setSelectedStrategyId(strat.id)}
                    className={clsx(
                      'w-full p-4 text-left transition-colors',
                      selectedStrategy?.id === strat.id
                        ? clsx(theme.bgMuted, 'border-l-2', theme.border)
                        : 'hover:bg-zinc-800/50'
                    )}
                  >
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <Target className={clsx('w-4 h-4', theme.textPrimary)} />
                        <span className="text-white font-medium truncate">{strat.name}</span>
                      </div>
                      <span className={clsx(
                        'text-xs px-2 py-0.5 rounded',
                        strat.type === 'series'
                          ? 'bg-blue-600/20 text-blue-400'
                          : 'bg-green-600/20 text-green-400'
                      )}>
                        {strat.type}
                      </span>
                    </div>

                    <div className="flex items-center gap-3 text-xs text-zinc-500 mb-2">
                      <span className="flex items-center gap-1">
                        <BookOpen className="w-3 h-3" />
                        {strat.chapterCount} chapters
                      </span>
                      <span className="flex items-center gap-1">
                        <FileText className="w-3 h-3" />
                        {strat.completedCount}/{strat.postCount} posts
                      </span>
                    </div>

                    {/* Progress bar */}
                    <div className="h-1 bg-zinc-800 rounded-full overflow-hidden">
                      <div
                        className={clsx('h-full bg-gradient-to-r', theme.gradient)}
                        style={{ width: `${progress}%` }}
                      />
                    </div>
                  </button>
                )
              })}
            </div>
          )}
        </div>
      </div>

      {/* Strategy Details */}
      <div className="flex-1 space-y-4 overflow-y-auto">
        {selectedStrategy && strategy?.exists ? (
          <>
            {/* Header */}
            <div className="bg-zinc-900 rounded-lg border border-zinc-800 p-6">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-4">
                  <div className={clsx('w-14 h-14 rounded-xl flex items-center justify-center bg-gradient-to-br', theme.gradient)}>
                    <Target className="w-7 h-7 text-white" />
                  </div>
                  <div>
                    <h2 className="text-xl font-bold text-white">{selectedStrategy.name}</h2>
                    <div className="flex items-center gap-2 mt-1">
                      <span className={clsx(
                        'text-xs px-2 py-0.5 rounded',
                        selectedStrategy.type === 'series'
                          ? 'bg-blue-600/20 text-blue-400'
                          : 'bg-green-600/20 text-green-400'
                      )}>
                        {selectedStrategy.type === 'series' ? 'Series Strategy' : 'Daily Strategy'}
                      </span>
                    </div>
                  </div>
                </div>
                <div className="flex gap-2">
                  <Link
                    to="/strategy"
                    className="px-4 py-2 bg-zinc-800 text-white rounded-lg hover:bg-zinc-700 flex items-center gap-2"
                  >
                    View Details
                    <ChevronRight className="w-4 h-4" />
                  </Link>
                  <button
                    onClick={() => setShowDeleteModal(selectedStrategy.id)}
                    className="p-2 text-zinc-400 hover:text-red-400 hover:bg-red-600/10 rounded-lg transition-colors"
                    title="Delete Strategy"
                  >
                    <Trash2 className="w-5 h-5" />
                  </button>
                </div>
              </div>

              {/* Thesis */}
              {strategy.goal?.signature_thesis && (
                <div className="bg-zinc-800/50 rounded-lg p-4">
                  <div className={clsx('text-xs uppercase tracking-wide mb-1', theme.textPrimary)}>Core Message</div>
                  <p className="text-white">{strategy.goal.signature_thesis}</p>
                </div>
              )}
            </div>

            {/* Stats */}
            <div className="grid grid-cols-4 gap-4">
              <div className="bg-zinc-900 rounded-lg border border-zinc-800 p-4">
                <div className="text-zinc-400 text-sm mb-1">Chapters</div>
                <div className="text-2xl font-bold text-white">{selectedStrategy.chapterCount}</div>
              </div>
              <div className="bg-zinc-900 rounded-lg border border-zinc-800 p-4">
                <div className="text-zinc-400 text-sm mb-1">Total Posts</div>
                <div className="text-2xl font-bold text-white">{selectedStrategy.postCount}</div>
              </div>
              <div className="bg-zinc-900 rounded-lg border border-zinc-800 p-4">
                <div className="text-zinc-400 text-sm mb-1">Completed</div>
                <div className="text-2xl font-bold text-green-400">{selectedStrategy.completedCount}</div>
              </div>
              <div className="bg-zinc-900 rounded-lg border border-zinc-800 p-4">
                <div className="text-zinc-400 text-sm mb-1">Progress</div>
                <div className={clsx('text-2xl font-bold', theme.textPrimary)}>
                  {selectedStrategy.postCount > 0
                    ? Math.round((selectedStrategy.completedCount / selectedStrategy.postCount) * 100)
                    : 0}%
                </div>
              </div>
            </div>

            {/* Strategy Info */}
            <div className="grid grid-cols-2 gap-4">
              {strategy.goal?.positioning && (
                <div className="bg-zinc-900 rounded-lg border border-zinc-800 p-4">
                  <div className="text-xs text-zinc-400 uppercase tracking-wide mb-2">Positioning</div>
                  <div className="text-white">{strategy.goal.positioning}</div>
                </div>
              )}
              {strategy.goal?.target_audience && (
                <div className="bg-zinc-900 rounded-lg border border-zinc-800 p-4">
                  <div className="text-xs text-zinc-400 uppercase tracking-wide mb-2">Target Audience</div>
                  <div className="text-white">{strategy.goal.target_audience}</div>
                </div>
              )}
              {strategy.goal?.content_style && (
                <div className="bg-zinc-900 rounded-lg border border-zinc-800 p-4">
                  <div className="text-xs text-zinc-400 uppercase tracking-wide mb-2">Content Style</div>
                  <div className="text-white capitalize">{strategy.goal.content_style}</div>
                </div>
              )}
            </div>

            {/* Chapters Preview */}
            {strategy.chapters && strategy.chapters.length > 0 && (
              <div className="bg-zinc-900 rounded-lg border border-zinc-800 overflow-hidden">
                <div className="p-4 border-b border-zinc-800 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <BookOpen className={clsx('w-5 h-5', theme.iconPrimary)} />
                    <h3 className="font-semibold text-white">Chapters</h3>
                  </div>
                  <Link
                    to="/strategy"
                    className={clsx('text-sm', theme.textPrimary, theme.borderHover)}
                  >
                    View All
                  </Link>
                </div>
                <div className="divide-y divide-zinc-800">
                  {strategy.chapters.slice(0, 4).map((chapter: ExistingChapter) => {
                    const progress = chapter.post_count > 0
                      ? (chapter.completed_count / chapter.post_count) * 100
                      : 0
                    return (
                      <div key={chapter.id} className="p-4 flex items-center gap-4">
                        <div className={clsx(
                          'w-8 h-8 rounded-lg flex items-center justify-center font-bold text-sm',
                          chapter.completed_count === chapter.post_count
                            ? 'bg-green-600/20 text-green-400'
                            : clsx(theme.bgMuted, theme.textPrimary)
                        )}>
                          {chapter.chapter_number}
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="text-white font-medium truncate">{chapter.title}</div>
                          <div className="flex items-center gap-2 text-xs text-zinc-500">
                            <span className="flex items-center gap-1">
                              <Calendar className="w-3 h-3" />
                              Weeks {chapter.weeks_start}-{chapter.weeks_end}
                            </span>
                            <span>
                              {chapter.completed_count}/{chapter.post_count} posts
                            </span>
                          </div>
                        </div>
                        <div className="w-24">
                          <div className="h-1.5 bg-zinc-800 rounded-full overflow-hidden">
                            <div
                              className={clsx(
                                'h-full',
                                chapter.completed_count === chapter.post_count
                                  ? 'bg-green-500'
                                  : clsx('bg-gradient-to-r', theme.gradient)
                              )}
                              style={{ width: `${progress}%` }}
                            />
                          </div>
                        </div>
                      </div>
                    )
                  })}
                </div>
              </div>
            )}
          </>
        ) : (
          <div className="h-full flex items-center justify-center">
            <div className="text-center text-zinc-500">
              <ThemeIcon className={clsx('w-12 h-12 mx-auto mb-4', theme.textMuted)} />
              <p>Select a strategy to view details</p>
            </div>
          </div>
        )}
      </div>

      {/* Delete Confirmation Modal */}
      {showDeleteModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-zinc-900 rounded-lg border border-zinc-800 p-6 w-96">
            <h3 className="text-lg font-semibold text-white mb-2">Delete Strategy?</h3>
            <p className="text-zinc-400 mb-4">
              This will delete the strategy and all {selectedStrategy?.postCount || 0} posts.
              This action cannot be undone.
            </p>
            {deleteMutation.isError && (
              <p className="text-red-400 text-sm mb-4">
                Failed to delete: {deleteMutation.error?.message || 'Unknown error'}
              </p>
            )}
            <div className="flex gap-3">
              <button
                onClick={() => setShowDeleteModal(null)}
                disabled={deleteMutation.isPending}
                className="flex-1 px-4 py-2 bg-zinc-800 text-white rounded-lg hover:bg-zinc-700 disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                onClick={() => deleteMutation.mutate(showDeleteModal)}
                disabled={deleteMutation.isPending}
                className="flex-1 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-500 disabled:opacity-50 flex items-center justify-center gap-2"
              >
                {deleteMutation.isPending ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Deleting...
                  </>
                ) : (
                  'Delete'
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
