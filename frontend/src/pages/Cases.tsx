import { useState, useEffect } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import { MagnifyingGlassIcon, FunnelIcon, PlusIcon } from '@heroicons/react/24/outline'
import { useCases, useCaseStats, useCreateCase } from '../hooks/useCases'
import api from '../services/api'
import Card from '../components/ui/Card'
import Button from '../components/ui/Button'
import Table, { Pagination } from '../components/ui/Table'
import { StatusBadge, PriorityBadge } from '../components/ui/Badge'
import Modal from '../components/ui/Modal'
import type { Case, Loan, PaginatedResponse } from '../types'

interface CaseFormData {
  loan_id: string
  priority: number
  case_type: string
}

export default function Cases() {
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [modalOpen, setModalOpen] = useState(false)
  const [loanSearch, setLoanSearch] = useState('')
  const [filtersOpen, setFiltersOpen] = useState(false)
  const [followUpFrom, setFollowUpFrom] = useState('')
  const [followUpTo, setFollowUpTo] = useState('')
  const [hasFollowUp, setHasFollowUp] = useState<string>('')
  const [sortBy, setSortBy] = useState<string>('created_at')
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc')

  const createCase = useCreateCase()

  // Auto-open modal if new=true in URL
  useEffect(() => {
    if (searchParams.get('new') === 'true') {
      setModalOpen(true)
      setSearchParams({})
    }
  }, [searchParams, setSearchParams])

  const { register, handleSubmit, reset, formState: { errors } } = useForm<CaseFormData>({
    defaultValues: {
      priority: 3,
      case_type: 'collection',
    }
  })

  // Fetch loans for selection
  const { data: loansData } = useQuery({
    queryKey: ['loans', loanSearch],
    queryFn: async () => {
      const params = new URLSearchParams()
      params.append('page_size', '50')
      if (loanSearch) params.append('search', loanSearch)
      const response = await api.get<PaginatedResponse<Loan>>(`/loans?${params}`)
      return response.data
    },
    enabled: modalOpen,
  })

  const { data, isLoading } = useCases({
    page,
    page_size: 20,
    search: search || undefined,
    status: statusFilter || undefined,
    follow_up_from: followUpFrom || undefined,
    follow_up_to: followUpTo || undefined,
    has_follow_up: hasFollowUp === 'true' ? true : hasFollowUp === 'false' ? false : undefined,
    sort_by: sortBy,
    sort_order: sortOrder,
  })

  const { data: stats } = useCaseStats()

  const columns = [
    {
      key: 'case_number',
      header: 'Case #',
      render: (item: Case) => (
        <span className="font-medium text-primary-600">{item.case_number}</span>
      ),
    },
    {
      key: 'status',
      header: 'Status',
      render: (item: Case) => <StatusBadge status={item.status} />,
    },
    {
      key: 'priority',
      header: 'Priority',
      render: (item: Case) => <PriorityBadge priority={item.priority} />,
    },
    {
      key: 'total_attempts',
      header: 'Attempts',
      render: (item: Case) => (
        <span className="text-light-700">{item.total_attempts}</span>
      ),
    },
    {
      key: 'last_contact_date',
      header: 'Last Contact',
      render: (item: Case) => (
        <span className="text-light-500">
          {item.last_contact_date
            ? new Date(item.last_contact_date).toLocaleDateString()
            : 'Never'}
        </span>
      ),
    },
    {
      key: 'next_follow_up',
      header: 'Follow Up',
      render: (item: Case) => (
        <span className="text-light-500">
          {item.next_follow_up
            ? new Date(item.next_follow_up).toLocaleDateString()
            : '-'}
        </span>
      ),
    },
    {
      key: 'created_at',
      header: 'Created',
      render: (item: Case) => (
        <span className="text-light-500">
          {new Date(item.created_at).toLocaleDateString()}
        </span>
      ),
    },
  ]

  const statusOptions = [
    { value: '', label: 'All Statuses' },
    { value: 'open', label: 'Open' },
    { value: 'in_progress', label: 'In Progress' },
    { value: 'promise_to_pay', label: 'Promise to Pay' },
    { value: 'resolved', label: 'Resolved' },
    { value: 'escalated', label: 'Escalated' },
  ]

  const statItems = [
    { label: 'Total', value: stats?.total || 0, color: 'text-light-900' },
    { label: 'Open', value: stats?.open || 0, color: 'text-primary-600' },
    { label: 'In Progress', value: stats?.in_progress || 0, color: 'text-amber-600' },
    { label: 'PTP', value: stats?.promise_to_pay || 0, color: 'text-accent-600' },
    { label: 'Escalated', value: stats?.escalated || 0, color: 'text-red-600' },
  ]

  const onSubmit = (data: CaseFormData) => {
    createCase.mutate(data, {
      onSuccess: () => {
        setModalOpen(false)
        reset()
      },
    })
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold text-light-900">Cases</h1>
          <p className="mt-1 text-xs sm:text-sm text-light-500">
            Manage and track collection cases
          </p>
        </div>
        <Button className="self-start sm:self-auto" onClick={() => setModalOpen(true)}>
          <PlusIcon className="h-4 w-4" />
          <span className="hidden sm:inline">Create Case</span>
          <span className="sm:hidden">New</span>
        </Button>
      </div>

      {/* Stats */}
      {stats && (
        <div className="grid grid-cols-2 gap-3 sm:gap-4 sm:grid-cols-3 lg:grid-cols-5">
          {statItems.map((stat) => (
            <Card key={stat.label} className="text-center" hover>
              <div className={`text-xl sm:text-2xl font-bold ${stat.color}`}>{stat.value}</div>
              <div className="text-xs sm:text-sm text-light-500 mt-1">{stat.label}</div>
            </Card>
          ))}
        </div>
      )}

      {/* Filters */}
      <Card>
        <div className="flex flex-col sm:flex-row gap-4">
          <div className="flex-1">
            <div className="relative">
              <MagnifyingGlassIcon className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-light-400" />
              <input
                type="text"
                placeholder="Search cases..."
                className="w-full rounded-lg bg-white border border-light-300 py-2.5 pl-10 pr-4 text-sm text-light-900 placeholder-light-400 focus:outline-none focus:border-primary-500 focus:ring-1 focus:ring-primary-500/20 transition-colors shadow-sm"
                value={search}
                onChange={(e) => {
                  setSearch(e.target.value)
                  setPage(1)
                }}
              />
            </div>
          </div>
          <div className="flex gap-2 flex-wrap">
            <select
              className="rounded-lg bg-white border border-light-300 py-2.5 px-4 text-sm text-light-700 focus:outline-none focus:border-primary-500 focus:ring-1 focus:ring-primary-500/20 transition-colors shadow-sm"
              value={statusFilter}
              onChange={(e) => {
                setStatusFilter(e.target.value)
                setPage(1)
              }}
            >
              {statusOptions.map((option) => (
                <option key={option.value} value={option.value} className="bg-white">
                  {option.label}
                </option>
              ))}
            </select>
            <select
              className="rounded-lg bg-white border border-light-300 py-2.5 px-4 text-sm text-light-700 focus:outline-none focus:border-primary-500 focus:ring-1 focus:ring-primary-500/20 transition-colors shadow-sm"
              value={`${sortBy}-${sortOrder}`}
              onChange={(e) => {
                const [field, order] = e.target.value.split('-')
                setSortBy(field)
                setSortOrder(order as 'asc' | 'desc')
                setPage(1)
              }}
            >
              <option value="created_at-desc">Newest First</option>
              <option value="created_at-asc">Oldest First</option>
              <option value="last_contact_date-desc">Last Contact (Recent)</option>
              <option value="last_contact_date-asc">Last Contact (Oldest)</option>
              <option value="next_follow_up-asc">Follow Up (Soonest)</option>
              <option value="next_follow_up-desc">Follow Up (Latest)</option>
              <option value="priority-desc">Priority (High to Low)</option>
              <option value="priority-asc">Priority (Low to High)</option>
            </select>
            <Button variant="secondary" onClick={() => setFiltersOpen(!filtersOpen)}>
              <FunnelIcon className="h-4 w-4" />
              Filters
            </Button>
          </div>
        </div>

        {/* Advanced Filters Panel */}
        {filtersOpen && (
          <div className="mt-4 pt-4 border-t border-light-200 space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div>
                <label className="block text-sm font-medium text-light-700 mb-1">Priority</label>
                <select className="w-full rounded-lg bg-white border border-light-300 py-2 px-3 text-sm text-light-700 focus:outline-none focus:border-primary-500">
                  <option value="">All Priorities</option>
                  <option value="5">Critical</option>
                  <option value="4">High</option>
                  <option value="3">Medium</option>
                  <option value="2">Low</option>
                  <option value="1">Lowest</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-light-700 mb-1">Case Type</label>
                <select className="w-full rounded-lg bg-white border border-light-300 py-2 px-3 text-sm text-light-700 focus:outline-none focus:border-primary-500">
                  <option value="">All Types</option>
                  <option value="collection">Collection</option>
                  <option value="recovery">Recovery</option>
                  <option value="legal">Legal</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-light-700 mb-1">Assignment</label>
                <select className="w-full rounded-lg bg-white border border-light-300 py-2 px-3 text-sm text-light-700 focus:outline-none focus:border-primary-500">
                  <option value="">All</option>
                  <option value="unassigned">Unassigned</option>
                  <option value="assigned">Assigned to me</option>
                </select>
              </div>
            </div>

            {/* Follow-up Date Filters */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div>
                <label className="block text-sm font-medium text-light-700 mb-1">Follow-up Status</label>
                <select
                  className="w-full rounded-lg bg-white border border-light-300 py-2 px-3 text-sm text-light-700 focus:outline-none focus:border-primary-500"
                  value={hasFollowUp}
                  onChange={(e) => {
                    setHasFollowUp(e.target.value)
                    setPage(1)
                  }}
                >
                  <option value="">All Cases</option>
                  <option value="true">Has Follow-up Scheduled</option>
                  <option value="false">No Follow-up Scheduled</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-light-700 mb-1">Follow-up From</label>
                <input
                  type="date"
                  className="w-full rounded-lg bg-white border border-light-300 py-2 px-3 text-sm text-light-700 focus:outline-none focus:border-primary-500"
                  value={followUpFrom}
                  onChange={(e) => {
                    setFollowUpFrom(e.target.value)
                    setPage(1)
                  }}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-light-700 mb-1">Follow-up To</label>
                <input
                  type="date"
                  className="w-full rounded-lg bg-white border border-light-300 py-2 px-3 text-sm text-light-700 focus:outline-none focus:border-primary-500"
                  value={followUpTo}
                  onChange={(e) => {
                    setFollowUpTo(e.target.value)
                    setPage(1)
                  }}
                />
              </div>
            </div>

            {/* Clear Filters */}
            {(followUpFrom || followUpTo || hasFollowUp) && (
              <div className="flex justify-end">
                <button
                  onClick={() => {
                    setFollowUpFrom('')
                    setFollowUpTo('')
                    setHasFollowUp('')
                    setPage(1)
                  }}
                  className="text-sm text-primary-600 hover:text-primary-800"
                >
                  Clear follow-up filters
                </button>
              </div>
            )}
          </div>
        )}
      </Card>

      {/* Table */}
      <Card padding="none">
        <Table
          columns={columns}
          data={data?.items || []}
          keyField="id"
          loading={isLoading}
          onRowClick={(item) => navigate(`/cases/${item.id}`)}
          emptyMessage="No cases found"
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

      {/* Create Case Modal */}
      <Modal
        isOpen={modalOpen}
        onClose={() => setModalOpen(false)}
        title="Create New Case"
        size="lg"
      >
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
          <div>
            <label className="block text-sm font-medium text-light-700 mb-1.5">
              Select Loan
            </label>
            <input
              type="text"
              placeholder="Search loans by account number..."
              className="block w-full rounded-lg bg-white border border-light-300 px-4 py-2.5 shadow-sm text-light-900 placeholder-light-400 sm:text-sm focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500 mb-2"
              value={loanSearch}
              onChange={(e) => setLoanSearch(e.target.value)}
            />
            <select
              {...register('loan_id', { required: 'Please select a loan' })}
              className="block w-full rounded-lg bg-white border border-light-300 px-4 py-2.5 shadow-sm text-light-900 sm:text-sm focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500"
            >
              <option value="">Select a loan...</option>
              {loansData?.items?.map((loan) => (
                <option key={loan.id} value={loan.id}>
                  {loan.loan_account_number || loan.external_loan_id} - ₹{loan.total_outstanding?.toLocaleString()} ({loan.dpd} DPD)
                </option>
              ))}
            </select>
            {errors.loan_id && (
              <p className="mt-1.5 text-sm text-red-600">{errors.loan_id.message}</p>
            )}
          </div>

          <div>
            <label className="block text-sm font-medium text-light-700 mb-1.5">
              Priority
            </label>
            <select
              {...register('priority', { valueAsNumber: true })}
              className="block w-full rounded-lg bg-white border border-light-300 px-4 py-2.5 shadow-sm text-light-900 sm:text-sm focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500"
            >
              <option value={1}>Low (1)</option>
              <option value={2}>Low (2)</option>
              <option value={3}>Medium (3)</option>
              <option value={4}>High (4)</option>
              <option value={5}>Critical (5)</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-light-700 mb-1.5">
              Case Type
            </label>
            <select
              {...register('case_type')}
              className="block w-full rounded-lg bg-white border border-light-300 px-4 py-2.5 shadow-sm text-light-900 sm:text-sm focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500"
            >
              <option value="collection">Collection</option>
              <option value="recovery">Recovery</option>
              <option value="legal">Legal</option>
            </select>
          </div>

          <div className="flex justify-end gap-3 pt-4 border-t border-light-200">
            <Button
              type="button"
              variant="secondary"
              onClick={() => setModalOpen(false)}
            >
              Cancel
            </Button>
            <Button type="submit" loading={createCase.isPending}>
              Create Case
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  )
}
