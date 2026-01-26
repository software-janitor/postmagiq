import { apiPost, apiGet } from './client'

export interface WorkflowStatus {
  running: boolean
  run_id: string | null
  current_state: string | null
  story: string | null
  started_at: string | null
  awaiting_approval: boolean
}

export interface ExecuteResult {
  run_id: string
  status: string
  error?: string
}

export interface ApprovalResult {
  status: string
  error?: string
}

export async function getWorkflowStatus(): Promise<WorkflowStatus> {
  return apiGet<WorkflowStatus>('/workflow/status')
}

export interface StartWorkflowParams {
  story: string
  inputPath?: string
  config?: string
  content?: string
  workspaceId?: string
}

export async function startWorkflow(params: StartWorkflowParams): Promise<ExecuteResult> {
  return apiPost<ExecuteResult>('/workflow/execute', {
    story: params.story,
    input_path: params.inputPath,
    config: params.config,
    content: params.content,
    workspace_id: params.workspaceId,
  })
}

export async function abortWorkflow(): Promise<ExecuteResult> {
  return apiPost<ExecuteResult>('/workflow/abort')
}

export async function stepWorkflow(
  story: string,
  step: string,
  runId?: string
): Promise<ExecuteResult> {
  return apiPost<ExecuteResult>('/workflow/step', {
    story,
    step,
    run_id: runId,
  })
}

export async function submitApproval(
  decision: 'approved' | 'feedback' | 'abort',
  feedback?: string
): Promise<ApprovalResult> {
  const result = await apiPost<ApprovalResult>('/workflow/approve', {
    decision,
    feedback,
  })
  // API returns 200 with error field on failure
  if ('error' in result && result.error) {
    throw new Error(result.error as string)
  }
  return result
}

export async function pauseWorkflow(): Promise<ExecuteResult> {
  return apiPost<ExecuteResult>('/workflow/pause')
}

export async function resumeWorkflow(): Promise<ExecuteResult> {
  return apiPost<ExecuteResult>('/workflow/resume')
}

export interface WorkflowRun {
  id: number
  user_id: number
  run_id: string
  story: string
  status: string
  current_state: string | null
  final_state: string | null
  total_tokens: number
  total_cost_usd: number
  started_at: string | null
  completed_at: string | null
  error: string | null
}

export interface WorkflowOutputs {
  review?: string
  processed?: string
  draft?: Record<string, string>
  audit?: Record<string, string>
  final_audit?: Record<string, string>
  final?: string
}

export interface LatestRunResponse {
  run: WorkflowRun | null
  outputs: WorkflowOutputs
}

export async function getLatestRunForStory(story: string): Promise<LatestRunResponse> {
  return apiGet<LatestRunResponse>(`/workflow/story/${story}/latest`)
}

export interface WorkflowState {
  id: string
  type: string
  description: string
  agents?: string[]
}

export async function getWorkflowStates(): Promise<{ states: WorkflowState[] }> {
  return apiGet<{ states: WorkflowState[] }>('/config/states')
}
