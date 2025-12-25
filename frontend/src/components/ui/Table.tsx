import clsx from 'clsx'

interface Column<T> {
  key: string
  header: string
  render?: (item: T) => React.ReactNode
  className?: string
}

interface TableProps<T> {
  columns: Column<T>[]
  data: T[]
  keyField: keyof T
  onRowClick?: (item: T) => void
  loading?: boolean
  emptyMessage?: string
}

export default function Table<T extends Record<string, any>>({
  columns,
  data,
  keyField,
  onRowClick,
  loading,
  emptyMessage = 'No data available',
}: TableProps<T>) {
  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="relative">
          <div className="animate-spin rounded-full h-10 w-10 border-2 border-light-200 border-t-primary-500" />
          <div className="absolute inset-0 rounded-full animate-ping opacity-20 bg-primary-500" />
        </div>
      </div>
    )
  }

  if (data.length === 0) {
    return (
      <div className="text-center py-12">
        <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-light-100 mb-4">
          <svg className="w-6 h-6 text-light-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4" />
          </svg>
        </div>
        <p className="text-light-500">{emptyMessage}</p>
      </div>
    )
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-light-200 scrollbar-thin">
      <table className="min-w-full">
        <thead>
          <tr className="bg-light-50">
            {columns.map((column) => (
              <th
                key={column.key}
                className={clsx(
                  'px-3 sm:px-6 py-3 sm:py-4 text-left text-xs font-semibold text-light-500 uppercase tracking-wider',
                  column.className
                )}
              >
                {column.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-light-100 bg-white">
          {data.map((item) => (
            <tr
              key={String(item[keyField])}
              onClick={() => onRowClick?.(item)}
              className={clsx(
                'transition-colors duration-150',
                onRowClick && 'cursor-pointer hover:bg-light-50'
              )}
            >
              {columns.map((column) => (
                <td
                  key={column.key}
                  className={clsx(
                    'px-3 sm:px-6 py-3 sm:py-4 whitespace-nowrap text-sm text-light-700',
                    column.className
                  )}
                >
                  {column.render
                    ? column.render(item)
                    : item[column.key]}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

interface PaginationProps {
  page: number
  totalPages: number
  total: number
  pageSize: number
  onPageChange: (page: number) => void
}

export function Pagination({
  page,
  totalPages,
  total,
  pageSize,
  onPageChange,
}: PaginationProps) {
  const startItem = (page - 1) * pageSize + 1
  const endItem = Math.min(page * pageSize, total)

  return (
    <div className="flex items-center justify-between px-3 sm:px-4 py-3 sm:py-4 border-t border-light-200">
      {/* Mobile pagination */}
      <div className="flex flex-1 items-center justify-between sm:hidden">
        <button
          onClick={() => onPageChange(page - 1)}
          disabled={page <= 1}
          className={clsx(
            'relative inline-flex items-center rounded-lg px-3 py-2 text-sm font-medium',
            'bg-white border border-light-300 text-light-700 shadow-sm',
            'hover:bg-light-50 hover:text-light-900',
            'disabled:opacity-40 disabled:cursor-not-allowed',
            'transition-all duration-200'
          )}
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
        </button>
        <span className="text-sm text-light-500">
          Page <span className="font-medium text-light-900">{page}</span> of{' '}
          <span className="font-medium text-light-900">{totalPages}</span>
        </span>
        <button
          onClick={() => onPageChange(page + 1)}
          disabled={page >= totalPages}
          className={clsx(
            'relative inline-flex items-center rounded-lg px-3 py-2 text-sm font-medium',
            'bg-white border border-light-300 text-light-700 shadow-sm',
            'hover:bg-light-50 hover:text-light-900',
            'disabled:opacity-40 disabled:cursor-not-allowed',
            'transition-all duration-200'
          )}
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
          </svg>
        </button>
      </div>

      {/* Desktop pagination */}
      <div className="hidden sm:flex sm:flex-1 sm:items-center sm:justify-between">
        <div>
          <p className="text-sm text-light-500">
            Showing <span className="font-medium text-light-900">{startItem}</span> to{' '}
            <span className="font-medium text-light-900">{endItem}</span> of{' '}
            <span className="font-medium text-light-900">{total}</span> results
          </p>
        </div>
        <div>
          <nav className="isolate inline-flex gap-1">
            <button
              onClick={() => onPageChange(page - 1)}
              disabled={page <= 1}
              className={clsx(
                'relative inline-flex items-center rounded-lg px-3 py-2 text-sm font-medium',
                'bg-white border border-light-300 text-light-700 shadow-sm',
                'hover:bg-light-50 hover:text-light-900 hover:border-light-400',
                'disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:bg-white',
                'transition-all duration-200'
              )}
            >
              <svg className="w-4 h-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
              Prev
            </button>
            <div className="flex gap-1">
              {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                const pageNum = i + 1
                return (
                  <button
                    key={pageNum}
                    onClick={() => onPageChange(pageNum)}
                    className={clsx(
                      'relative inline-flex items-center justify-center w-10 h-10 rounded-lg text-sm font-medium',
                      'transition-all duration-200',
                      page === pageNum
                        ? 'bg-primary-50 text-primary-700 border border-primary-200'
                        : 'bg-white border border-light-300 text-light-700 shadow-sm hover:bg-light-50 hover:text-light-900'
                    )}
                  >
                    {pageNum}
                  </button>
                )
              })}
            </div>
            <button
              onClick={() => onPageChange(page + 1)}
              disabled={page >= totalPages}
              className={clsx(
                'relative inline-flex items-center rounded-lg px-3 py-2 text-sm font-medium',
                'bg-white border border-light-300 text-light-700 shadow-sm',
                'hover:bg-light-50 hover:text-light-900 hover:border-light-400',
                'disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:bg-white',
                'transition-all duration-200'
              )}
            >
              Next
              <svg className="w-4 h-4 ml-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
              </svg>
            </button>
          </nav>
        </div>
      </div>
    </div>
  )
}
