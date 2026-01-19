import { apiGet } from './client'
import type { RunSummary, StateLogEntry, TokenBreakdown, ArtifactInfo } from '../types/api'

export function fetchRuns(): Promise<RunSummary[]> {
  return apiGet<RunSummary[]>('/runs')
}

export function fetchRun(runId: string): Promise<RunSummary> {
  return apiGet<RunSummary>(`/runs/${runId}`)
}

export function fetchStateLog(runId: string): Promise<StateLogEntry[]> {
  return apiGet<StateLogEntry[]>(`/runs/${runId}/states`)
}

export function fetchRunSummary(runId: string): Promise<{ summary: string }> {
  return apiGet<{ summary: string }>(`/runs/${runId}/summary`)
}

export function fetchTokenBreakdown(runId: string): Promise<TokenBreakdown> {
  return apiGet<TokenBreakdown>(`/runs/${runId}/tokens`)
}

export function fetchArtifacts(runId: string): Promise<ArtifactInfo[]> {
  return apiGet<ArtifactInfo[]>(`/runs/${runId}/artifacts`)
}

export function fetchArtifactContent(runId: string, path: string): Promise<{ content: string }> {
  return apiGet<{ content: string }>(`/runs/${runId}/artifacts/${encodeURIComponent(path)}`)
}
