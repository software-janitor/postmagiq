import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { CheckCircle, XCircle, Clock, MessageSquare, User } from 'lucide-react'
import { useState } from 'react'
import { apiGet, apiPost } from '../api/client'
import { useWorkspaceStore } from '../stores/workspaceStore'

interface ApprovalRequest {
  id: string
  post_id: string
  workspace_id: string
  stage_id: string
  submitted_by_id: string
  assigned_approver_id: string | null
  decided_by_id: string | null
  status: string
  submitted_at: string
  decided_at: string | null
  decision_notes: string | null
  content_version: number | null
  created_at: string
}

interface ApprovalStage {
  id: string
  name: string
  order: number
}

interface ApprovalDecisionRequest {
  notes?: string
}

export default function ApprovalQueue() {
  const { currentWorkspaceId } = useWorkspaceStore()
  const queryClient = useQueryClient()
  const [selectedRequest, setSelectedRequest] = useState<ApprovalRequest | null>(null)
  const [decisionNotes, setDecisionNotes] = useState('')
  const [showModal, setShowModal] = useState(false)

  const { data: pendingApprovals, isLoading } = useQuery({
    queryKey: ['pending-approvals', currentWorkspaceId],
    queryFn: () => apiGet<ApprovalRequest[]>(`/v1/w/${currentWorkspaceId}/approvals/pending`),
    enabled: !!currentWorkspaceId,
  })

  const { data: stages } = useQuery({
    queryKey: ['approval-stages', currentWorkspaceId],
    queryFn: () => apiGet<ApprovalStage[]>(`/v1/w/${currentWorkspaceId}/approvals/stages`),
    enabled: !!currentWorkspaceId,
  })

  const approveMutation = useMutation({
    mutationFn: ({ requestId, notes }: { requestId: string; notes?: string }) =>
      apiPost<ApprovalRequest>(
        `/v1/w/${currentWorkspaceId}/approvals/requests/${requestId}/approve`,
        { notes } as ApprovalDecisionRequest
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pending-approvals'] })
      setShowModal(false)
      setSelectedRequest(null)
      setDecisionNotes('')
    },
  })

  const rejectMutation = useMutation({
    mutationFn: ({ requestId, notes }: { requestId: string; notes: string }) =>
      apiPost<ApprovalRequest>(
        `/v1/w/${currentWorkspaceId}/approvals/requests/${requestId}/reject`,
        { notes } as ApprovalDecisionRequest
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pending-approvals'] })
      setShowModal(false)
      setSelectedRequest(null)
      setDecisionNotes('')
    },
  })

  const requestChangesMutation = useMutation({
    mutationFn: ({ requestId, notes }: { requestId: string; notes: string }) =>
      apiPost<ApprovalRequest>(
        `/v1/w/${currentWorkspaceId}/approvals/requests/${requestId}/request-changes`,
        { notes } as ApprovalDecisionRequest
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pending-approvals'] })
      setShowModal(false)
      setSelectedRequest(null)
      setDecisionNotes('')
    },
  })

  const getStageName = (stageId: string) => {
    return stages?.find((s) => s.id === stageId)?.name || 'Unknown Stage'
  }

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  const handleApprove = () => {
    if (selectedRequest) {
      approveMutation.mutate({ requestId: selectedRequest.id, notes: decisionNotes || undefined })
    }
  }

  const handleReject = () => {
    if (selectedRequest && decisionNotes.trim()) {
      rejectMutation.mutate({ requestId: selectedRequest.id, notes: decisionNotes })
    }
  }

  const handleRequestChanges = () => {
    if (selectedRequest && decisionNotes.trim()) {
      requestChangesMutation.mutate({ requestId: selectedRequest.id, notes: decisionNotes })
    }
  }

  const openReviewModal = (request: ApprovalRequest) => {
    setSelectedRequest(request)
    setDecisionNotes('')
    setShowModal(true)
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-8 text-zinc-400">
        <Clock className="w-5 h-5 animate-spin mr-2" />
        Loading approvals...
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-white">Pending Approvals</h2>
        <span className="px-2 py-1 bg-amber-500/20 text-amber-400 rounded text-sm">
          {pendingApprovals?.length || 0} pending
        </span>
      </div>

      {pendingApprovals && pendingApprovals.length > 0 ? (
        <div className="space-y-3">
          {pendingApprovals.map((request) => (
            <div
              key={request.id}
              className="p-4 bg-zinc-800/50 rounded-lg border border-zinc-700 hover:border-zinc-600 transition-colors"
            >
              <div className="flex items-start justify-between">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="px-2 py-0.5 bg-blue-500/20 text-blue-400 rounded text-xs">
                      {getStageName(request.stage_id)}
                    </span>
                    <span className="text-zinc-400 text-sm">
                      v{request.content_version || 1}
                    </span>
                  </div>
                  <div className="flex items-center gap-4 text-sm text-zinc-400">
                    <span className="flex items-center gap-1">
                      <Clock className="w-3 h-3" />
                      {formatDate(request.submitted_at)}
                    </span>
                    {request.assigned_approver_id && (
                      <span className="flex items-center gap-1">
                        <User className="w-3 h-3" />
                        Assigned
                      </span>
                    )}
                  </div>
                </div>
                <button
                  onClick={() => openReviewModal(request)}
                  className="px-3 py-1.5 bg-amber-600 hover:bg-amber-700 text-white rounded text-sm font-medium transition-colors"
                >
                  Review
                </button>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="text-center py-8 text-zinc-400">
          <CheckCircle className="w-8 h-8 mx-auto mb-2 opacity-50" />
          <p>No pending approvals</p>
          <p className="text-sm">All content has been reviewed</p>
        </div>
      )}

      {/* Review Modal */}
      {showModal && selectedRequest && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-zinc-900 rounded-lg border border-zinc-700 w-full max-w-lg mx-4">
            <div className="p-4 border-b border-zinc-700">
              <h3 className="text-lg font-semibold text-white">Review Content</h3>
              <p className="text-sm text-zinc-400">
                Stage: {getStageName(selectedRequest.stage_id)}
              </p>
            </div>

            <div className="p-4 space-y-4">
              <div>
                <label className="block text-sm text-zinc-400 mb-2">
                  <MessageSquare className="w-4 h-4 inline mr-1" />
                  Decision Notes
                </label>
                <textarea
                  value={decisionNotes}
                  onChange={(e) => setDecisionNotes(e.target.value)}
                  placeholder="Add feedback or notes (required for reject/request changes)"
                  className="w-full px-3 py-2 bg-zinc-800 border border-zinc-600 rounded-lg text-white placeholder:text-zinc-500 focus:border-amber-500 focus:outline-none"
                  rows={4}
                />
              </div>
            </div>

            <div className="p-4 border-t border-zinc-700 flex items-center justify-between">
              <button
                onClick={() => setShowModal(false)}
                className="px-4 py-2 text-zinc-400 hover:text-white transition-colors"
              >
                Cancel
              </button>
              <div className="flex items-center gap-2">
                <button
                  onClick={handleReject}
                  disabled={!decisionNotes.trim() || rejectMutation.isPending}
                  className="flex items-center gap-1 px-3 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg text-sm font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <XCircle className="w-4 h-4" />
                  Reject
                </button>
                <button
                  onClick={handleRequestChanges}
                  disabled={!decisionNotes.trim() || requestChangesMutation.isPending}
                  className="flex items-center gap-1 px-3 py-2 bg-amber-600 hover:bg-amber-700 text-white rounded-lg text-sm font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <MessageSquare className="w-4 h-4" />
                  Request Changes
                </button>
                <button
                  onClick={handleApprove}
                  disabled={approveMutation.isPending}
                  className="flex items-center gap-1 px-3 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg text-sm font-medium transition-colors disabled:opacity-50"
                >
                  <CheckCircle className="w-4 h-4" />
                  Approve
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
