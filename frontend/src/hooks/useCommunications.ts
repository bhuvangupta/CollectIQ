import { useMutation, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import api from '../services/api'

interface InitiateCallRequest {
  borrower_id?: string
  loan_id?: string
  case_id?: string
  phone_number?: string
  use_ai?: boolean
}

interface InitiateCallResponse {
  communication_id: string
  call_sid: string
  status: string
}

interface SendSMSRequest {
  borrower_id: string
  loan_id?: string
  case_id?: string
  message: string
  phone_number?: string
}

export function useInitiateCall() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (request: InitiateCallRequest) => {
      const response = await api.post<InitiateCallResponse>('/communications/call', request)
      return response.data
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['communications'] })
      if (data.status === 'ringing') {
        toast.success('Call ringing...', { icon: '📞', duration: 5000 })
      } else if (data.status === 'failed') {
        toast.error('Call failed to connect')
      } else {
        toast.success(`Call ${data.status}`)
      }
    },
    onError: (error: any) => {
      const message = error.response?.data?.detail || 'Failed to initiate call'
      toast.error(message)
    },
  })
}

export function useSendSMS() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (request: SendSMSRequest) => {
      const response = await api.post('/communications/sms', request)
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['communications'] })
      toast.success('SMS sent successfully')
    },
    onError: (error: any) => {
      const message = error.response?.data?.detail || 'Failed to send SMS'
      toast.error(message)
    },
  })
}

interface SendWhatsAppRequest {
  borrower_id: string
  loan_id?: string
  case_id?: string
  message: string
  phone_number?: string
}

export function useSendWhatsApp() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (request: SendWhatsAppRequest) => {
      const response = await api.post('/communications/whatsapp', request)
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['communications'] })
      toast.success('WhatsApp message sent successfully')
    },
    onError: (error: any) => {
      const message = error.response?.data?.detail || 'Failed to send WhatsApp message'
      toast.error(message)
    },
  })
}
