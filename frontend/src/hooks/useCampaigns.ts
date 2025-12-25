import { useMutation, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import api from '../services/api'

interface CampaignCreate {
  name: string
  description?: string
  campaign_type: string
  scheduled_start?: string
  scheduled_end?: string
  allowed_start_time?: string
  allowed_end_time?: string
  allowed_days?: string[]
  ai_enabled?: boolean
  ai_language?: string
  max_attempts_per_borrower?: number
  concurrent_calls?: number
  priority?: number
}

export function useCreateCampaign() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (data: CampaignCreate) => {
      const response = await api.post('/campaigns', data)
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['campaigns'] })
      toast.success('Campaign created successfully')
    },
    onError: (error: any) => {
      const message = error.response?.data?.detail || 'Failed to create campaign'
      toast.error(message)
    },
  })
}

export function useStartCampaign() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (campaignId: string) => {
      const response = await api.post(`/campaigns/${campaignId}/start`)
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['campaigns'] })
      toast.success('Campaign started')
    },
    onError: (error: any) => {
      const message = error.response?.data?.detail || 'Failed to start campaign'
      toast.error(message)
    },
  })
}

export function usePauseCampaign() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (campaignId: string) => {
      const response = await api.post(`/campaigns/${campaignId}/pause`)
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['campaigns'] })
      toast.success('Campaign paused')
    },
    onError: (error: any) => {
      const message = error.response?.data?.detail || 'Failed to pause campaign'
      toast.error(message)
    },
  })
}

export function useCancelCampaign() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (campaignId: string) => {
      const response = await api.post(`/campaigns/${campaignId}/cancel`)
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['campaigns'] })
      toast.success('Campaign cancelled')
    },
    onError: (error: any) => {
      const message = error.response?.data?.detail || 'Failed to cancel campaign'
      toast.error(message)
    },
  })
}
