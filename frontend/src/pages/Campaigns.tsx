import { useState, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import { PlusIcon } from '@heroicons/react/24/outline'
import api from '../services/api'
import Card from '../components/ui/Card'
import Button from '../components/ui/Button'
import Table, { Pagination } from '../components/ui/Table'
import { StatusBadge } from '../components/ui/Badge'
import Modal from '../components/ui/Modal'
import Input from '../components/ui/Input'
import { useCreateCampaign } from '../hooks/useCampaigns'
import type { Campaign, PaginatedResponse } from '../types'

interface CampaignFormData {
  name: string
  description: string
  campaign_type: string
  ai_enabled: boolean
}

export default function Campaigns() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [page, setPage] = useState(1)
  const [statusFilter, setStatusFilter] = useState('')
  const [modalOpen, setModalOpen] = useState(false)

  const createCampaign = useCreateCampaign()

  // Auto-open modal if new=true in URL
  useEffect(() => {
    if (searchParams.get('new') === 'true') {
      setModalOpen(true)
      setSearchParams({})
    }
  }, [searchParams, setSearchParams])

  const { register, handleSubmit, reset, formState: { errors } } = useForm<CampaignFormData>({
    defaultValues: {
      campaign_type: 'voice',
      ai_enabled: false,
    }
  })

  const { data, isLoading } = useQuery({
    queryKey: ['campaigns', page, statusFilter],
    queryFn: async () => {
      const params = new URLSearchParams()
      params.append('page', page.toString())
      params.append('page_size', '20')
      if (statusFilter) params.append('status', statusFilter)

      const response = await api.get<PaginatedResponse<Campaign>>(`/campaigns?${params}`)
      return response.data
    },
  })

  const columns = [
    {
      key: 'name',
      header: 'Campaign Name',
      render: (item: Campaign) => (
        <span className="font-medium text-gray-900">{item.name}</span>
      ),
    },
    {
      key: 'campaign_type',
      header: 'Type',
      render: (item: Campaign) => (
        <span className="capitalize">{item.campaign_type.replace('_', ' ')}</span>
      ),
    },
    {
      key: 'status',
      header: 'Status',
      render: (item: Campaign) => <StatusBadge status={item.status} />,
    },
    {
      key: 'progress',
      header: 'Progress',
      render: (item: Campaign) => {
        const progress = item.total_targets > 0
          ? Math.round((item.total_attempted / item.total_targets) * 100)
          : 0
        return (
          <div className="flex items-center gap-2">
            <div className="flex-1 h-2 bg-gray-200 rounded-full max-w-[100px]">
              <div
                className="h-2 bg-primary-600 rounded-full"
                style={{ width: `${progress}%` }}
              />
            </div>
            <span className="text-sm text-gray-500">{progress}%</span>
          </div>
        )
      },
    },
    {
      key: 'targets',
      header: 'Targets',
      render: (item: Campaign) => (
        <span>
          {item.total_attempted} / {item.total_targets}
        </span>
      ),
    },
    {
      key: 'successful',
      header: 'Successful',
      render: (item: Campaign) => (
        <span className="text-green-600 font-medium">
          {item.total_successful}
        </span>
      ),
    },
    {
      key: 'created_at',
      header: 'Created',
      render: (item: Campaign) =>
        new Date(item.created_at).toLocaleDateString(),
    },
  ]

  const statusOptions = [
    { value: '', label: 'All Statuses' },
    { value: 'draft', label: 'Draft' },
    { value: 'scheduled', label: 'Scheduled' },
    { value: 'running', label: 'Running' },
    { value: 'paused', label: 'Paused' },
    { value: 'completed', label: 'Completed' },
  ]

  const onSubmit = (data: CampaignFormData) => {
    createCampaign.mutate(data, {
      onSuccess: () => {
        setModalOpen(false)
        reset()
      },
    })
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900">Campaigns</h1>
          <p className="mt-1 text-sm text-gray-500">
            Manage voice and messaging campaigns
          </p>
        </div>
        <Button onClick={() => setModalOpen(true)}>
          <PlusIcon className="h-5 w-5 mr-2" />
          New Campaign
        </Button>
      </div>

      {/* Filters */}
      <Card>
        <div className="flex gap-4">
          <select
            className="block rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm"
            value={statusFilter}
            onChange={(e) => {
              setStatusFilter(e.target.value)
              setPage(1)
            }}
          >
            {statusOptions.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>
      </Card>

      {/* Table */}
      <Card padding="none">
        <Table
          columns={columns}
          data={data?.items || []}
          keyField="id"
          loading={isLoading}
          emptyMessage="No campaigns found"
        />
        {data && data.total > 0 && (
          <Pagination
            page={page}
            totalPages={data.total_pages}
            total={data.total}
            pageSize={20}
            onPageChange={setPage}
          />
        )}
      </Card>

      {/* New Campaign Modal */}
      <Modal
        isOpen={modalOpen}
        onClose={() => setModalOpen(false)}
        title="Create New Campaign"
        size="lg"
      >
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
          <Input
            label="Campaign Name"
            placeholder="Enter campaign name"
            error={errors.name?.message}
            {...register('name', { required: 'Campaign name is required' })}
          />

          <div>
            <label className="block text-sm font-medium text-light-700 mb-1.5">
              Description
            </label>
            <textarea
              {...register('description')}
              rows={3}
              className="block w-full rounded-lg bg-white border border-light-300 px-4 py-2.5 shadow-sm text-light-900 placeholder-light-400 sm:text-sm focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500"
              placeholder="Optional description"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-light-700 mb-1.5">
              Campaign Type
            </label>
            <select
              {...register('campaign_type')}
              className="block w-full rounded-lg bg-white border border-light-300 px-4 py-2.5 shadow-sm text-light-900 sm:text-sm focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500"
            >
              <option value="voice">Voice Call</option>
              <option value="sms">SMS</option>
              <option value="whatsapp">WhatsApp</option>
            </select>
          </div>

          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="ai_enabled"
              {...register('ai_enabled')}
              className="w-4 h-4 rounded border-light-300 bg-white text-primary-500 focus:ring-primary-500/20"
            />
            <label htmlFor="ai_enabled" className="text-sm text-light-700">
              Enable AI-powered calls
            </label>
          </div>

          <div className="flex justify-end gap-3 pt-4 border-t border-light-200">
            <Button
              type="button"
              variant="secondary"
              onClick={() => setModalOpen(false)}
            >
              Cancel
            </Button>
            <Button type="submit" loading={createCampaign.isPending}>
              Create Campaign
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  )
}
