import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Copy, Check, FileText, Share2, X, Linkedin, AtSign, BookOpen, RefreshCw, RotateCcw, AlertTriangle } from 'lucide-react'
import { clsx } from 'clsx'
import { useThemeClasses } from '../hooks/useThemeClasses'
import { apiGet, apiPost, apiDelete } from '../api/client'
import { useWorkspaceStore } from '../stores/workspaceStore'

interface PublishInfo {
  platform: string
  published_at: string
  url: string | null
}

interface FinishedPost {
  post_id: string
  post_number: number
  chapter: number
  title: string
  content: string
  file_path: string
  publish_status: PublishInfo[]
}

const PLATFORM_CONFIG: Record<string, { name: string; icon: React.ReactNode; color: string }> = {
  linkedin: { name: 'LinkedIn', icon: <Linkedin className="w-4 h-4" />, color: 'bg-blue-600' },
  threads: { name: 'Threads', icon: <AtSign className="w-4 h-4" />, color: 'bg-zinc-600' },
  medium: { name: 'Medium', icon: <BookOpen className="w-4 h-4" />, color: 'bg-green-600' },
  x: { name: 'X', icon: <X className="w-4 h-4" />, color: 'bg-zinc-800' },
}

export default function FinishedPosts() {
  const theme = useThemeClasses()
  const { currentWorkspace } = useWorkspaceStore()
  const workspaceId = currentWorkspace?.id
  const [selectedPost, setSelectedPost] = useState<string | null>(null)
  const [copiedField, setCopiedField] = useState<string | null>(null)
  const [showPublishModal, setShowPublishModal] = useState(false)
  const [publishUrl, setPublishUrl] = useState('')
  const [selectedPlatform, setSelectedPlatform] = useState<string | null>(null)
  const [showResetModal, setShowResetModal] = useState(false)
  const [resetConfirmText, setResetConfirmText] = useState('')

  const queryClient = useQueryClient()

  const { data: postsData, isLoading, error } = useQuery({
    queryKey: ['finished-posts', workspaceId],
    queryFn: () => apiGet<{ posts: FinishedPost[] }>(`/v1/w/${workspaceId}/finished-posts`),
    enabled: !!workspaceId,
  })
  const posts = postsData?.posts

  const publishMutation = useMutation({
    mutationFn: ({ postId, platform, url }: { postId: string; platform: string; url?: string }) =>
      apiPost(`/v1/w/${workspaceId}/finished-posts/${postId}/publish`, { platform, url }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['finished-posts', workspaceId] })
      setShowPublishModal(false)
      setPublishUrl('')
      setSelectedPlatform(null)
    },
  })

  const unpublishMutation = useMutation({
    mutationFn: ({ postId, platform }: { postId: string; platform: string }) =>
      apiDelete(`/v1/w/${workspaceId}/finished-posts/${postId}/publish/${platform}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['finished-posts', workspaceId] })
    },
  })

  const resetPostMutation = useMutation({
    mutationFn: (postId: string) =>
      apiPost(`/v1/w/${workspaceId}/posts/${postId}/reset`, {}),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['finished-posts', workspaceId] })
      setShowResetModal(false)
      setResetConfirmText('')
      setSelectedPost(null)
    },
  })

  const handleCopy = async (text: string, field: string) => {
    await navigator.clipboard.writeText(text)
    setCopiedField(field)
    setTimeout(() => setCopiedField(null), 2000)
  }

  const handlePublish = () => {
    if (selectedPost && selectedPlatform) {
      publishMutation.mutate({
        postId: selectedPost,
        platform: selectedPlatform,
        url: publishUrl || undefined,
      })
    }
  }

  const selectedPostData = posts?.find(p => p.post_id === selectedPost)

  const isPublishedOn = (platform: string) =>
    selectedPostData?.publish_status.some(p => p.platform === platform) || false

  const getPublishInfo = (platform: string) =>
    selectedPostData?.publish_status.find(p => p.platform === platform)

  return (
    <div className="h-full flex gap-6">
      {/* Post List */}
      <div className="w-80 flex-shrink-0 bg-zinc-900 rounded-lg border border-zinc-800 overflow-hidden">
        <div className="p-4 border-b border-zinc-800">
          <h2 className="text-lg font-semibold text-white">Finished Posts</h2>
          <p className="text-sm text-zinc-400 mt-1">
            {posts?.length || 0} posts ready
          </p>
        </div>

        <div className="overflow-y-auto h-[calc(100%-80px)]">
          {!workspaceId ? (
            <div className="p-4 text-zinc-400">Select a workspace to view posts</div>
          ) : isLoading ? (
            <div className="p-4 text-zinc-400">Loading...</div>
          ) : error ? (
            <div className="p-4 text-red-400">Failed to load posts</div>
          ) : posts?.length === 0 ? (
            <div className="p-4 text-zinc-400">No finished posts yet</div>
          ) : (
            <div className="divide-y divide-zinc-800">
              {posts?.map((post) => (
                <button
                  key={post.post_id}
                  onClick={() => setSelectedPost(post.post_id)}
                  className={clsx(
                    'w-full p-4 text-left transition-colors',
                    selectedPost === post.post_id
                      ? clsx(theme.bgMuted, 'border-l-2', theme.border)
                      : 'hover:bg-zinc-800/50'
                  )}
                >
                  <div className="flex items-center justify-between mb-1">
                    <div className="flex items-center gap-2 text-xs text-zinc-500">
                      <span>Ch{post.chapter}</span>
                      <span>Post {post.post_number}</span>
                    </div>
                    {/* Platform badges */}
                    {post.publish_status.length > 0 && (
                      <div className="flex gap-1">
                        {post.publish_status.map((pub) => (
                          <span
                            key={pub.platform}
                            className={clsx(
                              'w-5 h-5 rounded flex items-center justify-center text-white',
                              PLATFORM_CONFIG[pub.platform]?.color || 'bg-zinc-600'
                            )}
                            title={`Published on ${PLATFORM_CONFIG[pub.platform]?.name}`}
                          >
                            {PLATFORM_CONFIG[pub.platform]?.icon}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                  <div className="text-white font-medium truncate">
                    {post.title}
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Post Content */}
      <div className="flex-1 space-y-4 overflow-y-auto">
        {selectedPostData ? (
          <>
            {/* Publish Status Card */}
            <div className="bg-zinc-900 rounded-lg border border-zinc-800 p-4">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <Share2 className={clsx('w-5 h-5', theme.iconPrimary)} />
                  <h3 className="font-semibold text-white">Publish Status</h3>
                </div>
                <button
                  onClick={() => setShowResetModal(true)}
                  className="px-3 py-1.5 bg-red-600/20 text-red-400 rounded-lg hover:bg-red-600/30 flex items-center gap-2 text-sm transition-colors border border-red-600/30"
                >
                  <RotateCcw className="w-4 h-4" />
                  Reset Post
                </button>
              </div>
              <div className="flex flex-wrap gap-2">
                {Object.entries(PLATFORM_CONFIG).map(([platform, config]) => {
                  const published = isPublishedOn(platform)
                  const info = getPublishInfo(platform)

                  return (
                    <div key={platform} className="relative group">
                      <button
                        onClick={() => {
                          if (published) {
                            if (confirm(`Remove ${config.name} publish status?`)) {
                              unpublishMutation.mutate({ postId: selectedPost!, platform })
                            }
                          } else {
                            setSelectedPlatform(platform)
                            setShowPublishModal(true)
                          }
                        }}
                        className={clsx(
                          'px-3 py-2 rounded-lg flex items-center gap-2 transition-all',
                          published
                            ? `${config.color} text-white`
                            : 'bg-zinc-800 text-zinc-400 hover:bg-zinc-700'
                        )}
                      >
                        {config.icon}
                        <span className="text-sm">{config.name}</span>
                        {published && <Check className="w-3 h-3" />}
                      </button>
                      {published && info?.url && (
                        <a
                          href={info.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className={clsx('absolute -bottom-6 left-0 text-xs hover:underline truncate max-w-[150px]', theme.textPrimary)}
                        >
                          View post
                        </a>
                      )}
                    </div>
                  )
                })}
              </div>
            </div>

            {/* Post Content */}
            <div className="bg-zinc-900 rounded-lg border border-zinc-800 overflow-hidden">
              <div className="p-4 border-b border-zinc-800 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <FileText className={clsx('w-5 h-5', theme.iconPrimary)} />
                  <h2 className="text-lg font-semibold text-white">Post Content</h2>
                </div>
                <button
                  onClick={() => handleCopy(selectedPostData.content, 'content')}
                  className={clsx('px-3 py-1.5 bg-zinc-800 text-white rounded-lg flex items-center gap-2 text-sm transition-colors', theme.bgHover)}
                >
                  {copiedField === 'content' ? (
                    <>
                      <Check className={clsx('w-4 h-4', theme.iconPrimary)} />
                      Copied!
                    </>
                  ) : (
                    <>
                      <Copy className="w-4 h-4" />
                      Copy Post
                    </>
                  )}
                </button>
              </div>
              <div className="p-6">
                <div className="text-xl font-bold text-white mb-4">
                  {selectedPostData.title}
                </div>
                <div className="text-zinc-300 whitespace-pre-wrap leading-relaxed">
                  {selectedPostData.content}
                </div>
              </div>
            </div>
          </>
        ) : (
          <div className="h-full flex items-center justify-center">
            <div className="text-center text-zinc-500">
              <FileText className="w-12 h-12 mx-auto mb-4 opacity-50" />
              <p>Select a post to view its content</p>
            </div>
          </div>
        )}
      </div>

      {/* Publish Modal */}
      {showPublishModal && selectedPlatform && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-zinc-900 rounded-lg border border-zinc-800 p-6 w-96">
            <h3 className="text-lg font-semibold text-white mb-4">
              Publish to {PLATFORM_CONFIG[selectedPlatform]?.name}
            </h3>
            <div className="space-y-4">
              <div>
                <label className="block text-sm text-zinc-400 mb-2">
                  Post URL (optional)
                </label>
                <input
                  type="url"
                  value={publishUrl}
                  onChange={(e) => setPublishUrl(e.target.value)}
                  placeholder="https://..."
                  className={clsx('w-full px-3 py-2 bg-zinc-800 border border-zinc-700 rounded-lg text-white focus:outline-none', theme.borderHover)}
                />
              </div>
              <div className="flex gap-3">
                <button
                  onClick={() => {
                    setShowPublishModal(false)
                    setPublishUrl('')
                    setSelectedPlatform(null)
                  }}
                  className="flex-1 px-4 py-2 bg-zinc-800 text-white rounded-lg hover:bg-zinc-700"
                >
                  Cancel
                </button>
                <button
                  onClick={handlePublish}
                  disabled={publishMutation.isPending}
                  className={clsx('flex-1 px-4 py-2 text-white rounded-lg disabled:opacity-50 bg-gradient-to-r', theme.gradient, theme.gradientHover)}
                >
                  {publishMutation.isPending ? 'Saving...' : 'Mark Published'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Reset Post Confirmation Modal */}
      {showResetModal && selectedPostData && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-zinc-900 rounded-lg border border-red-800 p-6 w-[420px]">
            <div className="flex items-center gap-3 mb-4">
              <div className="p-2 bg-red-600/20 rounded-full">
                <AlertTriangle className="w-6 h-6 text-red-400" />
              </div>
              <h3 className="text-lg font-semibold text-white">
                Reset Post {selectedPostData.post_number}?
              </h3>
            </div>

            <div className="bg-red-950/30 border border-red-800/50 rounded-lg p-4 mb-4">
              <p className="text-red-300 text-sm">
                This will permanently delete:
              </p>
              <ul className="text-red-400 text-sm mt-2 space-y-1 ml-4 list-disc">
                <li>All workflow outputs for this post</li>
                <li>Publish status on all platforms</li>
              </ul>
              <p className="text-red-300 text-sm mt-3">
                The post will return to "not started" status.
              </p>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-sm text-zinc-400 mb-2">
                  Type <span className="font-mono text-white bg-zinc-800 px-1 rounded">{selectedPostData.post_number}</span> to confirm
                </label>
                <input
                  type="text"
                  value={resetConfirmText}
                  onChange={(e) => setResetConfirmText(e.target.value)}
                  placeholder="Enter post number"
                  className="w-full px-3 py-2 bg-zinc-800 border border-zinc-700 rounded-lg text-white focus:outline-none focus:border-red-500"
                  autoFocus
                />
              </div>
              <div className="flex gap-3">
                <button
                  onClick={() => {
                    setShowResetModal(false)
                    setResetConfirmText('')
                  }}
                  className="flex-1 px-4 py-2 bg-zinc-800 text-white rounded-lg hover:bg-zinc-700"
                >
                  Cancel
                </button>
                <button
                  onClick={() => resetPostMutation.mutate(selectedPost!)}
                  disabled={resetConfirmText !== String(selectedPostData.post_number) || resetPostMutation.isPending}
                  className="flex-1 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-500 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                >
                  {resetPostMutation.isPending ? (
                    <>
                      <RefreshCw className="w-4 h-4 animate-spin" />
                      Resetting...
                    </>
                  ) : (
                    <>
                      <RotateCcw className="w-4 h-4" />
                      Reset Post
                    </>
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
