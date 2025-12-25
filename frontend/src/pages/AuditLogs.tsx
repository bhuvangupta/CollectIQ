import { useState } from 'react'
import { MagnifyingGlassIcon, ArrowDownTrayIcon, FunnelIcon } from '@heroicons/react/24/outline'
import toast from 'react-hot-toast'
import { useAuditLogs, useAuditLogActions, useAuditLogUsers, exportAuditLogsCSV } from '../hooks/useAuditLogs'
import Card from '../components/ui/Card'
import Button from '../components/ui/Button'
import Table, { Pagination } from '../components/ui/Table'
import type { AuditLog } from '../types'

const ACTION_COLORS: Record<string, string> = {
  case_created: 'bg-green-100 text-green-700',
  case_updated: 'bg-blue-100 text-blue-700',
  case_assigned: 'bg-purple-100 text-purple-700',
  case_status_changed: 'bg-amber-100 text-amber-700',
  case_note_added: 'bg-gray-100 text-gray-700',
  payment_recorded: 'bg-emerald-100 text-emerald-700',
  payment_updated: 'bg-cyan-100 text-cyan-700',
  promise_created: 'bg-indigo-100 text-indigo-700',
  promise_fulfilled: 'bg-green-100 text-green-700',
  promise_broken: 'bg-red-100 text-red-700',
}

const CATEGORY_LABELS: Record<string, string> = {
  case: 'Case',
  payment: 'Payment',
}

export default function AuditLogs() {
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [userId, setUserId] = useState('')
  const [action, setAction] = useState('')
  const [category, setCategory] = useState('')
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  const [filtersOpen, setFiltersOpen] = useState(false)
  const [exporting, setExporting] = useState(false)

  const { data, isLoading } = useAuditLogs({
    page,
    page_size: 20,
    user_id: userId || undefined,
    action: action || undefined,
    category: category || undefined,
    date_from: dateFrom || undefined,
    date_to: dateTo || undefined,
    search: search || undefined,
  })

  const { data: actions } = useAuditLogActions()
  const { data: users } = useAuditLogUsers()

  const handleExport = async () => {
    setExporting(true)
    try {
      await exportAuditLogsCSV({
        user_id: userId || undefined,
        action: action || undefined,
        category: category || undefined,
        date_from: dateFrom || undefined,
        date_to: dateTo || undefined,
        search: search || undefined,
      })
      toast.success('Audit logs exported successfully')
    } catch {
      toast.error('Failed to export audit logs')
    } finally {
      setExporting(false)
    }
  }

  const clearFilters = () => {
    setUserId('')
    setAction('')
    setCategory('')
    setDateFrom('')
    setDateTo('')
    setSearch('')
    setPage(1)
  }

  const hasActiveFilters = userId || action || category || dateFrom || dateTo || search

  const columns = [
    {
      key: 'performed_at',
      header: 'Date & Time',
      render: (item: AuditLog) => (
        <div className="text-sm">
          <div className="text-light-900">
            {new Date(item.performed_at).toLocaleDateString()}
          </div>
          <div className="text-light-500 text-xs">
            {new Date(item.performed_at).toLocaleTimeString()}
          </div>
        </div>
      ),
    },
    {
      key: 'user',
      header: 'User',
      render: (item: AuditLog) => (
        <div className="text-sm">
          <div className="text-light-900 font-medium">{item.user_name || 'System'}</div>
          <div className="text-light-500 text-xs">{item.user_email || '-'}</div>
        </div>
      ),
    },
    {
      key: 'action',
      header: 'Action',
      render: (item: AuditLog) => {
        const actionLabel = actions?.find(a => a.value === item.action)?.label || item.action
        const colorClass = ACTION_COLORS[item.action] || 'bg-gray-100 text-gray-700'
        return (
          <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${colorClass}`}>
            {actionLabel}
          </span>
        )
      },
    },
    {
      key: 'category',
      header: 'Category',
      render: (item: AuditLog) => (
        <span className="text-sm text-light-700">
          {CATEGORY_LABELS[item.category] || item.category}
        </span>
      ),
    },
    {
      key: 'entity',
      header: 'Entity',
      render: (item: AuditLog) => (
        <div className="text-sm">
          <div className="text-light-900">{item.entity_name || '-'}</div>
          {item.entity_type && (
            <div className="text-light-500 text-xs capitalize">{item.entity_type}</div>
          )}
        </div>
      ),
    },
    {
      key: 'description',
      header: 'Description',
      render: (item: AuditLog) => (
        <span className="text-sm text-light-600 max-w-xs truncate block">
          {item.description || '-'}
        </span>
      ),
    },
  ]

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold text-light-900">Audit Logs</h1>
          <p className="mt-1 text-xs sm:text-sm text-light-500">
            Track case and payment activities across your organization
          </p>
        </div>
        <Button
          className="self-start sm:self-auto"
          variant="secondary"
          onClick={handleExport}
          loading={exporting}
        >
          <ArrowDownTrayIcon className="h-4 w-4" />
          Export CSV
        </Button>
      </div>

      {/* Filters */}
      <Card>
        <div className="flex flex-col sm:flex-row gap-4">
          <div className="flex-1">
            <div className="relative">
              <MagnifyingGlassIcon className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-light-400" />
              <input
                type="text"
                placeholder="Search by entity or description..."
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
              value={userId}
              onChange={(e) => {
                setUserId(e.target.value)
                setPage(1)
              }}
            >
              <option value="">All Users</option>
              {users?.map((user) => (
                <option key={user.id} value={user.id}>
                  {user.name} ({user.role})
                </option>
              ))}
            </select>
            <select
              className="rounded-lg bg-white border border-light-300 py-2.5 px-4 text-sm text-light-700 focus:outline-none focus:border-primary-500 focus:ring-1 focus:ring-primary-500/20 transition-colors shadow-sm"
              value={action}
              onChange={(e) => {
                setAction(e.target.value)
                setPage(1)
              }}
            >
              <option value="">All Actions</option>
              {actions?.map((a) => (
                <option key={a.value} value={a.value}>
                  {a.label}
                </option>
              ))}
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
            <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
              <div>
                <label className="block text-sm font-medium text-light-700 mb-1">Category</label>
                <select
                  className="w-full rounded-lg bg-white border border-light-300 py-2 px-3 text-sm text-light-700 focus:outline-none focus:border-primary-500"
                  value={category}
                  onChange={(e) => {
                    setCategory(e.target.value)
                    setPage(1)
                  }}
                >
                  <option value="">All Categories</option>
                  <option value="case">Case</option>
                  <option value="payment">Payment</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-light-700 mb-1">Date From</label>
                <input
                  type="date"
                  className="w-full rounded-lg bg-white border border-light-300 py-2 px-3 text-sm text-light-700 focus:outline-none focus:border-primary-500"
                  value={dateFrom}
                  onChange={(e) => {
                    setDateFrom(e.target.value)
                    setPage(1)
                  }}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-light-700 mb-1">Date To</label>
                <input
                  type="date"
                  className="w-full rounded-lg bg-white border border-light-300 py-2 px-3 text-sm text-light-700 focus:outline-none focus:border-primary-500"
                  value={dateTo}
                  onChange={(e) => {
                    setDateTo(e.target.value)
                    setPage(1)
                  }}
                />
              </div>
              <div className="flex items-end">
                {hasActiveFilters && (
                  <button
                    onClick={clearFilters}
                    className="text-sm text-primary-600 hover:text-primary-800"
                  >
                    Clear all filters
                  </button>
                )}
              </div>
            </div>
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
          emptyMessage="No audit logs found"
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
    </div>
  )
}
