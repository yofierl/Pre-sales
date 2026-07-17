import { http } from './http'

export interface MaterialItem {
  id: string
  project_id: string
  original_name: string
  file_size: number
  mime_type: string
  parse_status: string
  parse_error: string | null
  created_at: string
}

export interface MaterialListResponse {
  items: MaterialItem[]
  total: number
}

export function getMaterials(projectId: string): Promise<MaterialListResponse> {
  return http.get(`/api/v1/projects/${projectId}/materials`)
}

export function uploadMaterial(projectId: string, file: File): Promise<MaterialItem> {
  const formData = new FormData()
  formData.append('file', file)
  return fetch(`/api/v1/projects/${projectId}/materials`, {
    method: 'POST',
    body: formData,
  }).then(async (res) => {
    if (!res.ok) {
      const text = await res.text().catch(() => '')
      throw new Error(`HTTP ${res.status}: ${text || res.statusText}`)
    }
    return res.json()
  })
}

export function deleteMaterial(projectId: string, materialId: string): Promise<void> {
  return http.delete(`/api/v1/projects/${projectId}/materials/${materialId}`)
}
