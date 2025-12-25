import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import api from '../services/api'
import type { Case, CaseWithDetails, CaseNote, PaginatedResponse } from '../types'

interface CaseFilters {
  page?: number
  page_size?: number
  status?: string
  priority?: number
  assigned_to?: string
  search?: string
  follow_up_from?: string
  follow_up_to?: string
  has_follow_up?: boolean
  sort_by?: string
  sort_order?: 'asc' | 'desc'
}

export function useCases(filters: CaseFilters = {}) {
  return useQuery({
    queryKey: ['cases', filters],
    queryFn: async () => {
      const params = new URLSearchParams()
      if (filters.page) params.append('page', filters.page.toString())
      if (filters.page_size) params.append('page_size', filters.page_size.toString())
      if (filters.status) params.append('status', filters.status)
      if (filters.priority) params.append('priority', filters.priority.toString())
      if (filters.assigned_to) params.append('assigned_to', filters.assigned_to)
      if (filters.search) params.append('search', filters.search)
      if (filters.follow_up_from) params.append('follow_up_from', filters.follow_up_from)
      if (filters.follow_up_to) params.append('follow_up_to', filters.follow_up_to)
      if (filters.has_follow_up !== undefined) params.append('has_follow_up', filters.has_follow_up.toString())
      if (filters.sort_by) params.append('sort_by', filters.sort_by)
      if (filters.sort_order) params.append('sort_order', filters.sort_order)

      const response = await api.get<PaginatedResponse<Case>>(`/cases?${params}`)
      return response.data
    },
  })
}

export function useCase(id: string) {
  return useQuery({
    queryKey: ['case', id],
    queryFn: async () => {
      const response = await api.get<CaseWithDetails>(`/cases/${id}`)
      return response.data
    },
    enabled: !!id,
  })
}

export function useCaseStats() {
  return useQuery({
    queryKey: ['caseStats'],
    queryFn: async () => {
      const response = await api.get('/cases/stats')
      return response.data
    },
  })
}

export function useUpdateCase() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({ id, data }: { id: string; data: Partial<Case> }) => {
      const response = await api.put(`/cases/${id}`, data)
      return response.data
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['cases'] })
      queryClient.invalidateQueries({ queryKey: ['case', variables.id] })
      toast.success('Case updated successfully')
    },
    onError: (error: any) => {
      const message = error.response?.data?.detail || 'Failed to update case'
      toast.error(message)
    },
  })
}

export function useAssignCase() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({ caseId, agentId }: { caseId: string; agentId: string }) => {
      const response = await api.post(`/cases/${caseId}/assign`, { agent_id: agentId })
      return response.data
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['cases'] })
      queryClient.invalidateQueries({ queryKey: ['case', variables.caseId] })
      toast.success('Case assigned successfully')
    },
    onError: (error: any) => {
      const message = error.response?.data?.detail || 'Failed to assign case'
      toast.error(message)
    },
  })
}

export function useCaseNotes(caseId: string) {
  return useQuery({
    queryKey: ['caseNotes', caseId],
    queryFn: async () => {
      const response = await api.get<CaseNote[]>(`/cases/${caseId}/notes`)
      return response.data
    },
    enabled: !!caseId,
  })
}

export function useAddCaseNote() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({
      caseId,
      content,
      note_type = 'general',
    }: {
      caseId: string
      content: string
      note_type?: string
    }) => {
      const response = await api.post(`/cases/${caseId}/notes`, {
        content,
        note_type,
      })
      return response.data
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['caseNotes', variables.caseId] })
      toast.success('Note added successfully')
    },
    onError: (error: any) => {
      const message = error.response?.data?.detail || 'Failed to add note'
      toast.error(message)
    },
  })
}

interface CaseCreate {
  loan_id: string
  priority?: number
  case_type?: string
  tags?: string[]
}

export function useCreateCase() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (data: CaseCreate) => {
      const response = await api.post('/cases', data)
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['cases'] })
      queryClient.invalidateQueries({ queryKey: ['caseStats'] })
      toast.success('Case created successfully')
    },
    onError: (error: any) => {
      const message = error.response?.data?.detail || 'Failed to create case'
      toast.error(message)
    },
  })
}
