import { useQuery } from '@tanstack/react-query'
import api from '../services/api'
import type { AuditLog, AuditLogDetail, AuditLogAction, AuditLogUser, PaginatedResponse } from '../types'

interface AuditLogFilters {
  page?: number
  page_size?: number
  user_id?: string
  action?: string
  category?: string
  entity_type?: string
  date_from?: string
  date_to?: string
  search?: string
}

export function useAuditLogs(filters: AuditLogFilters = {}) {
  return useQuery({
    queryKey: ['auditLogs', filters],
    queryFn: async () => {
      const params = new URLSearchParams()
      if (filters.page) params.append('page', filters.page.toString())
      if (filters.page_size) params.append('page_size', filters.page_size.toString())
      if (filters.user_id) params.append('user_id', filters.user_id)
      if (filters.action) params.append('action', filters.action)
      if (filters.category) params.append('category', filters.category)
      if (filters.entity_type) params.append('entity_type', filters.entity_type)
      if (filters.date_from) params.append('date_from', filters.date_from)
      if (filters.date_to) params.append('date_to', filters.date_to)
      if (filters.search) params.append('search', filters.search)

      const response = await api.get<PaginatedResponse<AuditLog>>(`/audit-logs?${params}`)
      return response.data
    },
  })
}

export function useAuditLog(id: string) {
  return useQuery({
    queryKey: ['auditLog', id],
    queryFn: async () => {
      const response = await api.get<AuditLogDetail>(`/audit-logs/${id}`)
      return response.data
    },
    enabled: !!id,
  })
}

export function useAuditLogActions() {
  return useQuery({
    queryKey: ['auditLogActions'],
    queryFn: async () => {
      const response = await api.get<{ actions: AuditLogAction[] }>('/audit-logs/actions/list')
      return response.data.actions
    },
    staleTime: 1000 * 60 * 60, // Cache for 1 hour
  })
}

export function useAuditLogUsers() {
  return useQuery({
    queryKey: ['auditLogUsers'],
    queryFn: async () => {
      const response = await api.get<{ users: AuditLogUser[] }>('/audit-logs/users/list')
      return response.data.users
    },
    staleTime: 1000 * 60 * 5, // Cache for 5 minutes
  })
}

export async function exportAuditLogsCSV(filters: Omit<AuditLogFilters, 'page' | 'page_size'>) {
  const params = new URLSearchParams()
  if (filters.user_id) params.append('user_id', filters.user_id)
  if (filters.action) params.append('action', filters.action)
  if (filters.category) params.append('category', filters.category)
  if (filters.entity_type) params.append('entity_type', filters.entity_type)
  if (filters.date_from) params.append('date_from', filters.date_from)
  if (filters.date_to) params.append('date_to', filters.date_to)
  if (filters.search) params.append('search', filters.search)

  const response = await api.get(`/audit-logs/export/csv?${params}`, {
    responseType: 'blob',
  })

  // Create download link
  const url = window.URL.createObjectURL(new Blob([response.data]))
  const link = document.createElement('a')
  link.href = url
  const today = new Date().toISOString().split('T')[0]
  link.setAttribute('download', `audit-logs-${today}.csv`)
  document.body.appendChild(link)
  link.click()
  link.remove()
  window.URL.revokeObjectURL(url)
}
