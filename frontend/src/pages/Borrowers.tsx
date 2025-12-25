import { useState, useRef } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import toast from 'react-hot-toast'
import { MagnifyingGlassIcon, ArrowUpTrayIcon, PlusIcon, UsersIcon } from '@heroicons/react/24/outline'
import api from '../services/api'
import Card from '../components/ui/Card'
import Button from '../components/ui/Button'
import Table, { Pagination } from '../components/ui/Table'
import Badge from '../components/ui/Badge'
import Modal from '../components/ui/Modal'
import Input from '../components/ui/Input'
import { useCreateBorrower } from '../hooks/useBorrowers'
import type { Borrower, PaginatedResponse } from '../types'

interface BorrowerFormData {
  first_name: string
  last_name: string
  primary_phone: string
  email: string
  city: string
  state: string
}

export default function Borrowers() {
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [modalOpen, setModalOpen] = useState(false)
  const [importModalOpen, setImportModalOpen] = useState(false)
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const queryClient = useQueryClient()

  const createBorrower = useCreateBorrower()

  const importBorrowers = useMutation({
    mutationFn: async (file: File) => {
      const formData = new FormData()
      formData.append('file', file)
      const response = await api.post('/borrowers/import', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      return response.data
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['borrowers'] })
      toast.success(`Imported ${data.imported} borrowers, Updated ${data.updated}`)
      setImportModalOpen(false)
      setSelectedFile(null)
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to import borrowers')
    },
  })

  const { register, handleSubmit, reset, formState: { errors } } = useForm<BorrowerFormData>()

  const onSubmit = (data: BorrowerFormData) => {
    createBorrower.mutate(data, {
      onSuccess: () => {
        setModalOpen(false)
        reset()
      },
    })
  }

  const { data, isLoading } = useQuery({
    queryKey: ['borrowers', page, search],
    queryFn: async () => {
      const params = new URLSearchParams()
      params.append('page', page.toString())
      params.append('page_size', '20')
      if (search) params.append('search', search)

      const response = await api.get<PaginatedResponse<Borrower>>(`/borrowers?${params}`)
      return response.data
    },
  })

  const columns = [
    {
      key: 'external_id',
      header: 'ID',
      render: (item: Borrower) => (
        <span className="text-light-500 font-mono text-xs">{item.external_id || '-'}</span>
      ),
    },
    {
      key: 'name',
      header: 'Name',
      render: (item: Borrower) => (
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-primary-100 to-primary-200 flex items-center justify-center">
            <span className="text-xs font-medium text-primary-700">
              {item.first_name?.[0]}{item.last_name?.[0]}
            </span>
          </div>
          <span className="font-medium text-light-900">
            {item.first_name} {item.last_name}
          </span>
        </div>
      ),
    },
    {
      key: 'primary_phone',
      header: 'Phone',
      render: (item: Borrower) => (
        <span className="text-light-700">{item.primary_phone}</span>
      ),
    },
    {
      key: 'city',
      header: 'City',
      render: (item: Borrower) => (
        <span className="text-light-500">{item.city || '-'}</span>
      ),
    },
    {
      key: 'state',
      header: 'State',
      render: (item: Borrower) => (
        <span className="text-light-500">{item.state || '-'}</span>
      ),
    },
    {
      key: 'tags',
      header: 'Tags',
      render: (item: Borrower) =>
        item.tags && item.tags.length > 0 ? (
          <div className="flex gap-1">
            {item.tags.slice(0, 2).map((tag) => (
              <Badge key={tag} size="sm" variant="info">
                {tag}
              </Badge>
            ))}
            {item.tags.length > 2 && (
              <Badge size="sm">+{item.tags.length - 2}</Badge>
            )}
          </div>
        ) : (
          <span className="text-light-400">-</span>
        ),
    },
    {
      key: 'is_active',
      header: 'Status',
      render: (item: Borrower) => (
        <Badge variant={item.is_active ? 'success' : 'default'} dot={item.is_active}>
          {item.is_active ? 'Active' : 'Inactive'}
        </Badge>
      ),
    },
  ]

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold text-light-900">Borrowers</h1>
          <p className="mt-1 text-xs sm:text-sm text-light-500">
            Manage your borrower database
          </p>
        </div>
        <div className="flex gap-2 self-start sm:self-auto">
          <Button variant="secondary" className="text-xs sm:text-sm" onClick={() => setImportModalOpen(true)}>
            <ArrowUpTrayIcon className="h-4 w-4" />
            <span className="hidden sm:inline">Import</span>
          </Button>
          <Button className="text-xs sm:text-sm" onClick={() => setModalOpen(true)}>
            <PlusIcon className="h-4 w-4" />
            <span className="hidden sm:inline">Add Borrower</span>
            <span className="sm:hidden">Add</span>
          </Button>
        </div>
      </div>

      {/* Stats Summary */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 sm:gap-4">
        <Card className="flex items-center gap-3 sm:gap-4" hover>
          <div className="p-2 sm:p-3 rounded-xl bg-primary-50">
            <UsersIcon className="h-5 w-5 sm:h-6 sm:w-6 text-primary-600" />
          </div>
          <div>
            <p className="text-xl sm:text-2xl font-bold text-light-900">{data?.total || 0}</p>
            <p className="text-xs sm:text-sm text-light-500">Total Borrowers</p>
          </div>
        </Card>
        <Card className="flex items-center gap-3 sm:gap-4" hover>
          <div className="p-2 sm:p-3 rounded-xl bg-accent-50">
            <UsersIcon className="h-5 w-5 sm:h-6 sm:w-6 text-accent-600" />
          </div>
          <div>
            <p className="text-xl sm:text-2xl font-bold text-light-900">{data?.items?.filter(b => b.is_active).length || 0}</p>
            <p className="text-xs sm:text-sm text-light-500">Active</p>
          </div>
        </Card>
        <Card className="flex items-center gap-3 sm:gap-4" hover>
          <div className="p-2 sm:p-3 rounded-xl bg-amber-50">
            <UsersIcon className="h-5 w-5 sm:h-6 sm:w-6 text-amber-600" />
          </div>
          <div>
            <p className="text-xl sm:text-2xl font-bold text-light-900">-</p>
            <p className="text-xs sm:text-sm text-light-500">With Active Loans</p>
          </div>
        </Card>
      </div>

      {/* Filters */}
      <Card>
        <div className="flex flex-col sm:flex-row gap-4">
          <div className="flex-1">
            <div className="relative">
              <MagnifyingGlassIcon className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-light-400" />
              <input
                type="text"
                placeholder="Search by name, phone, or ID..."
                className="w-full rounded-lg bg-white border border-light-300 py-2.5 pl-10 pr-4 text-sm text-light-900 placeholder-light-400 focus:outline-none focus:border-primary-500 focus:ring-1 focus:ring-primary-500/20 transition-colors shadow-sm"
                value={search}
                onChange={(e) => {
                  setSearch(e.target.value)
                  setPage(1)
                }}
              />
            </div>
          </div>
        </div>
      </Card>

      {/* Table */}
      <Card padding="none">
        <Table
          columns={columns}
          data={data?.items || []}
          keyField="id"
          loading={isLoading}
          emptyMessage="No borrowers found"
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

      {/* Add Borrower Modal */}
      <Modal
        isOpen={modalOpen}
        onClose={() => setModalOpen(false)}
        title="Add New Borrower"
        size="lg"
      >
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Input
              label="First Name"
              placeholder="Enter first name"
              error={errors.first_name?.message}
              {...register('first_name', { required: 'First name is required' })}
            />
            <Input
              label="Last Name"
              placeholder="Enter last name"
              {...register('last_name')}
            />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Input
              label="Phone Number"
              placeholder="+91 9876543210"
              error={errors.primary_phone?.message}
              {...register('primary_phone', {
                required: 'Phone number is required',
                pattern: {
                  value: /^[+]?[0-9]{10,14}$/,
                  message: 'Invalid phone number'
                }
              })}
            />
            <Input
              label="Email"
              type="email"
              placeholder="borrower@email.com"
              {...register('email')}
            />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Input
              label="City"
              placeholder="Enter city"
              {...register('city')}
            />
            <Input
              label="State"
              placeholder="Enter state"
              {...register('state')}
            />
          </div>

          <div className="flex justify-end gap-3 pt-4 border-t border-light-200">
            <Button
              type="button"
              variant="secondary"
              onClick={() => setModalOpen(false)}
            >
              Cancel
            </Button>
            <Button type="submit" loading={createBorrower.isPending}>
              Add Borrower
            </Button>
          </div>
        </form>
      </Modal>

      {/* Import Modal */}
      <Modal
        isOpen={importModalOpen}
        onClose={() => {
          setImportModalOpen(false)
          setSelectedFile(null)
        }}
        title="Import Borrowers"
      >
        <div className="space-y-4">
          <div>
            <p className="text-sm text-light-600 mb-4">
              Upload a CSV or Excel file with borrower data. Required columns: first_name, primary_phone.
              Optional: last_name, email, city, state, pincode.
            </p>
            <input
              type="file"
              ref={fileInputRef}
              accept=".csv,.xlsx,.xls"
              className="hidden"
              onChange={(e) => setSelectedFile(e.target.files?.[0] || null)}
            />
            <div
              onClick={() => fileInputRef.current?.click()}
              className="border-2 border-dashed border-light-300 rounded-lg p-8 text-center cursor-pointer hover:border-primary-400 transition-colors"
            >
              <ArrowUpTrayIcon className="h-10 w-10 mx-auto text-light-400 mb-3" />
              {selectedFile ? (
                <p className="text-sm text-light-700">{selectedFile.name}</p>
              ) : (
                <>
                  <p className="text-sm text-light-600">Click to upload or drag and drop</p>
                  <p className="text-xs text-light-400 mt-1">CSV, XLS, XLSX (max 10MB)</p>
                </>
              )}
            </div>
          </div>
          <div className="flex justify-end gap-3 pt-4 border-t border-light-200">
            <Button
              type="button"
              variant="secondary"
              onClick={() => {
                setImportModalOpen(false)
                setSelectedFile(null)
              }}
            >
              Cancel
            </Button>
            <Button
              onClick={() => selectedFile && importBorrowers.mutate(selectedFile)}
              loading={importBorrowers.isPending}
              disabled={!selectedFile}
            >
              Import
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  )
}
