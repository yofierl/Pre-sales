export interface RequirementNode {
  id: string
  module: string
  submodule: string | null
  feature: string
  subfeature: string | null
  description: string
  source_refs: string[]
  pending_confirmation: boolean
  system_added: boolean
  suggested_roles: string[]
  complexity_weight: number
}

export interface AnalysisPayload {
  suggested_project_name: string | null
  overview: string
  requirements: RequirementNode[]
  conflicts: string[]
  unanswered_questions: string[]
}
