import { http } from './http'
import type { RunResponse } from '@/types/run'
import type { RequirementNode } from '@/types/requirement'

export function startAnalysisRun(projectId: string, supplement?: string): Promise<{ run_id: string }> {
  return http.post(`/api/v1/projects/${projectId}/analysis-runs`, { supplement: supplement || null })
}

export function getRun(runId: string): Promise<RunResponse> {
  return http.get(`/api/v1/runs/${runId}`)
}

export function retryRun(runId: string): Promise<{ run_id: string }> {
  return http.post(`/api/v1/runs/${runId}/retry`, {})
}

export function confirmRequirements(projectId: string, requirements: RequirementNode[]): Promise<{ stage: string }> {
  return http.put(`/api/v1/projects/${projectId}/confirmed-requirements`, { requirements })
}

export function getProjectRuns(projectId: string): Promise<{ items: RunResponse[]; total: number }> {
  return http.get(`/api/v1/projects/${projectId}/runs`)
}
