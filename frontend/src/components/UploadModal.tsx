import { useState, useCallback } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import {
  ArrowUpTrayIcon,
  DocumentArrowDownIcon,
  CheckCircleIcon,
  XCircleIcon,
  ExclamationTriangleIcon,
} from '@heroicons/react/24/outline'
import Modal from './ui/Modal'
import Button from './ui/Button'
import api from '../services/api'
import toast from 'react-hot-toast'

interface UploadModalProps {
  isOpen: boolean
  onClose: () => void
  type: 'borrowers' | 'cases'
}

interface UploadResult {
  success: boolean
  total_rows: number
  created: number
  updated: number
  failed: number
  errors: Array<{
    row?: number
    index?: number
    error: string
    loan_account?: string
  }>
}

export default function UploadModal({ isOpen, onClose, type }: UploadModalProps) {
  const [file, setFile] = useState<File | null>(null)
  const [updateExisting, setUpdateExisting] = useState(false)
  const [result, setResult] = useState<UploadResult | null>(null)
  const [dragActive, setDragActive] = useState(false)
  const queryClient = useQueryClient()

  const uploadMutation = useMutation({
    mutationFn: async (formData: FormData) => {
      const response = await api.post(
        `/upload/${type}/upload?update_existing=${updateExisting}`,
        formData,
        {
          headers: { 'Content-Type': 'multipart/form-data' },
        }
      )
      return response.data as UploadResult
    },
    onSuccess: (data) => {
      setResult(data)
      if (data.success) {
        toast.success(`Successfully uploaded ${data.created} records`)
        queryClient.invalidateQueries({ queryKey: [type] })
      } else {
        toast.error(`Upload completed with ${data.failed} errors`)
      }
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Upload failed')
    },
  })

  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true)
    } else if (e.type === 'dragleave') {
      setDragActive(false)
    }
  }, [])

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setDragActive(false)

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const droppedFile = e.dataTransfer.files[0]
      if (droppedFile.name.endsWith('.csv')) {
        setFile(droppedFile)
        setResult(null)
      } else {
        toast.error('Please upload a CSV file')
      }
    }
  }, [])

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0])
      setResult(null)
    }
  }

  const handleUpload = () => {
    if (!file) return

    const formData = new FormData()
    formData.append('file', file)
    uploadMutation.mutate(formData)
  }

  const handleDownloadTemplate = async () => {
    try {
      const response = await api.get(`/upload/${type}/template`, {
        responseType: 'blob',
      })
      const url = window.URL.createObjectURL(new Blob([response.data]))
      const link = document.createElement('a')
      link.href = url
      link.setAttribute('download', `${type}_template.csv`)
      document.body.appendChild(link)
      link.click()
      link.remove()
    } catch {
      toast.error('Failed to download template')
    }
  }

  const handleClose = () => {
    setFile(null)
    setResult(null)
    onClose()
  }

  const title = type === 'borrowers' ? 'Upload Borrowers' : 'Upload Cases'
  const description = type === 'borrowers'
    ? 'Upload borrower data from a CSV file'
    : 'Upload cases with borrower and loan data from a CSV file'

  return (
    <Modal isOpen={isOpen} onClose={handleClose} title={title} size="lg">
      <div className="space-y-4">
        <p className="text-sm text-light-500">{description}</p>

        {/* Download Template */}
        <div className="flex items-center justify-between p-3 rounded-lg bg-light-50 border border-light-200">
          <div>
            <p className="text-sm font-medium text-light-700">Need a template?</p>
            <p className="text-xs text-light-500">Download the CSV template with all required columns</p>
          </div>
          <Button variant="secondary" size="sm" onClick={handleDownloadTemplate}>
            <DocumentArrowDownIcon className="h-4 w-4 mr-2" />
            Download Template
          </Button>
        </div>

        {/* File Drop Zone */}
        {!result && (
          <div
            className={`relative border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
              dragActive
                ? 'border-primary-500 bg-primary-50'
                : file
                ? 'border-accent-500 bg-accent-50'
                : 'border-light-300 hover:border-light-400'
            }`}
            onDragEnter={handleDrag}
            onDragLeave={handleDrag}
            onDragOver={handleDrag}
            onDrop={handleDrop}
          >
            <input
              type="file"
              accept=".csv"
              onChange={handleFileChange}
              className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
            />
            {file ? (
              <div className="space-y-2">
                <CheckCircleIcon className="h-10 w-10 text-accent-500 mx-auto" />
                <p className="text-sm font-medium text-light-900">{file.name}</p>
                <p className="text-xs text-light-500">
                  {(file.size / 1024).toFixed(1)} KB
                </p>
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation()
                    setFile(null)
                  }}
                  className="text-xs text-red-600 hover:text-red-700"
                >
                  Remove file
                </button>
              </div>
            ) : (
              <div className="space-y-2">
                <ArrowUpTrayIcon className="h-10 w-10 text-light-400 mx-auto" />
                <p className="text-sm text-light-600">
                  Drag and drop a CSV file, or <span className="text-primary-600">browse</span>
                </p>
                <p className="text-xs text-light-400">CSV files only</p>
              </div>
            )}
          </div>
        )}

        {/* Options */}
        {!result && (
          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="updateExisting"
              checked={updateExisting}
              onChange={(e) => setUpdateExisting(e.target.checked)}
              className="w-4 h-4 rounded border-light-300 bg-white text-primary-500 focus:ring-primary-500/20"
            />
            <label htmlFor="updateExisting" className="text-sm text-light-700">
              Update existing records if found (match by phone/loan number)
            </label>
          </div>
        )}

        {/* Upload Result */}
        {result && (
          <div className="space-y-4">
            {/* Summary */}
            <div className={`p-4 rounded-lg border ${
              result.success
                ? 'bg-green-50 border-green-200'
                : 'bg-amber-50 border-amber-200'
            }`}>
              <div className="flex items-start gap-3">
                {result.success ? (
                  <CheckCircleIcon className="h-6 w-6 text-green-500 flex-shrink-0" />
                ) : (
                  <ExclamationTriangleIcon className="h-6 w-6 text-amber-500 flex-shrink-0" />
                )}
                <div>
                  <p className={`font-medium ${result.success ? 'text-green-700' : 'text-amber-700'}`}>
                    {result.success ? 'Upload Successful' : 'Upload Completed with Errors'}
                  </p>
                  <div className="mt-2 grid grid-cols-4 gap-4 text-sm">
                    <div>
                      <p className="text-light-500">Total</p>
                      <p className="font-semibold text-light-900">{result.total_rows}</p>
                    </div>
                    <div>
                      <p className="text-light-500">Created</p>
                      <p className="font-semibold text-green-600">{result.created}</p>
                    </div>
                    <div>
                      <p className="text-light-500">Updated</p>
                      <p className="font-semibold text-blue-600">{result.updated}</p>
                    </div>
                    <div>
                      <p className="text-light-500">Failed</p>
                      <p className="font-semibold text-red-600">{result.failed}</p>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Errors */}
            {result.errors.length > 0 && (
              <div className="border border-red-200 rounded-lg overflow-hidden">
                <div className="bg-red-50 px-4 py-2 border-b border-red-200">
                  <p className="text-sm font-medium text-red-700">
                    Errors ({result.errors.length})
                  </p>
                </div>
                <div className="max-h-48 overflow-y-auto">
                  {result.errors.map((error, idx) => (
                    <div
                      key={idx}
                      className="flex items-start gap-2 px-4 py-2 border-b border-red-100 last:border-0"
                    >
                      <XCircleIcon className="h-4 w-4 text-red-500 flex-shrink-0 mt-0.5" />
                      <div className="text-sm">
                        <span className="font-medium text-light-700">
                          Row {error.row || error.index}
                          {error.loan_account && ` (${error.loan_account})`}:
                        </span>{' '}
                        <span className="text-red-600">{error.error}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Actions */}
        <div className="flex justify-end gap-3 pt-2">
          <Button variant="secondary" onClick={handleClose}>
            {result ? 'Close' : 'Cancel'}
          </Button>
          {!result && (
            <Button
              onClick={handleUpload}
              loading={uploadMutation.isPending}
              disabled={!file}
            >
              <ArrowUpTrayIcon className="h-4 w-4 mr-2" />
              Upload
            </Button>
          )}
          {result && (
            <Button
              onClick={() => {
                setFile(null)
                setResult(null)
              }}
            >
              Upload Another
            </Button>
          )}
        </div>
      </div>
    </Modal>
  )
}
