import { useMutation, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import api from '../services/api'

interface BorrowerCreate {
  first_name: string
  last_name?: string
  primary_phone: string
  secondary_phone?: string
  email?: string
  city?: string
  state?: string
  pincode?: string
  tags?: string[]
}

export function useCreateBorrower() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (data: BorrowerCreate) => {
      const response = await api.post('/borrowers', data)
      return response.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['borrowers'] })
      toast.success('Borrower added successfully')
    },
    onError: (error: any) => {
      const message = error.response?.data?.detail || 'Failed to add borrower'
      toast.error(message)
    },
  })
}
