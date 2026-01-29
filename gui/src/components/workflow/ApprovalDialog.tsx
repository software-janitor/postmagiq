import { useState, useCallback, useMemo } from 'react'
import { Check, X, MessageSquare, SkipForward } from 'lucide-react'
import { submitApproval } from '../../api/workflow'

interface ApprovalDialogProps {
  content: string | null
  onClose: () => void
}

export default function ApprovalDialog({ content, onClose }: ApprovalDialogProps) {
  const [feedback, setFeedback] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const isCircuitBreak = useMemo(
    () => content?.startsWith('Quality Score:') ?? false,
    [content]
  )

  const handleApprove = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      await submitApproval('approved')
      onClose()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to submit approval')
    } finally {
      setLoading(false)
    }
  }, [onClose])

  const handleFeedback = useCallback(async () => {
    // For circuit break, feedback is optional (user can just retry)
    // For normal approval, feedback is required
    if (!isCircuitBreak && !feedback.trim()) {
      setError('Please provide feedback')
      return
    }
    setLoading(true)
    setError(null)
    try {
      await submitApproval('feedback', feedback || '')
      onClose()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to submit feedback')
    } finally {
      setLoading(false)
    }
  }, [feedback, onClose, isCircuitBreak])

  const handleAbort = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      await submitApproval('abort')
      onClose()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to abort')
    } finally {
      setLoading(false)
    }
  }, [onClose])

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-slate-800 rounded-lg border border-slate-700 max-w-3xl w-full mx-4 max-h-[80vh] flex flex-col">
        <div className="px-6 py-4 border-b border-slate-700">
          <h2 className="text-xl font-bold text-white">
            {isCircuitBreak ? 'Quality Improvement Needed' : 'Human Approval Required'}
          </h2>
          {isCircuitBreak && (
            <p className="text-sm text-slate-400 mt-1">
              The post hasn't reached the quality threshold after multiple attempts.
            </p>
          )}
        </div>

        <div className="flex-1 overflow-auto p-6">
          {content && (
            <div className="bg-slate-900 rounded-lg p-4 mb-4 max-h-64 overflow-auto">
              <pre className="text-sm text-slate-300 whitespace-pre-wrap font-mono">
                {content}
              </pre>
            </div>
          )}

          <div className="space-y-2">
            <label className="block text-sm text-slate-400">
              {isCircuitBreak
                ? 'Provide guidance to improve the post (optional)'
                : 'Feedback (optional for revisions)'}
            </label>
            <textarea
              value={feedback}
              onChange={(e) => setFeedback(e.target.value)}
              placeholder={isCircuitBreak
                ? "e.g., 'Focus on making it more conversational' or 'Remove the em-dashes'"
                : "Provide feedback for revisions..."}
              className="w-full px-3 py-2 bg-slate-700 text-white rounded-lg border border-slate-600 focus:border-blue-500 focus:outline-none resize-none"
              rows={3}
            />
          </div>

          {error && (
            <div className="mt-4 bg-red-900/50 border border-red-700 text-red-200 px-4 py-2 rounded-lg">
              {error}
            </div>
          )}
        </div>

        <div className="px-6 py-4 border-t border-slate-700 flex justify-end gap-3">
          <button
            onClick={handleAbort}
            disabled={loading}
            className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-500 flex items-center gap-2 disabled:opacity-50"
          >
            <X className="w-4 h-4" /> Abort
          </button>
          {isCircuitBreak ? (
            <>
              <button
                onClick={handleFeedback}
                disabled={loading}
                className="px-4 py-2 bg-amber-600 text-white rounded-lg hover:bg-amber-500 flex items-center gap-2 disabled:opacity-50"
              >
                <MessageSquare className="w-4 h-4" /> {feedback.trim() ? 'Try Again with Guidance' : 'Try Again'}
              </button>
              <button
                onClick={handleApprove}
                disabled={loading}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-500 flex items-center gap-2 disabled:opacity-50"
              >
                <SkipForward className="w-4 h-4" /> Publish As-Is
              </button>
            </>
          ) : (
            <>
              <button
                onClick={handleFeedback}
                disabled={loading || !feedback.trim()}
                className="px-4 py-2 bg-amber-600 text-white rounded-lg hover:bg-amber-500 flex items-center gap-2 disabled:opacity-50"
              >
                <MessageSquare className="w-4 h-4" /> Request Changes
              </button>
              <button
                onClick={handleApprove}
                disabled={loading}
                className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-500 flex items-center gap-2 disabled:opacity-50"
              >
                <Check className="w-4 h-4" /> Approve
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
