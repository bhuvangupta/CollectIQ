import clsx from 'clsx'

interface BadgeProps {
  children: React.ReactNode
  variant?: 'default' | 'success' | 'warning' | 'danger' | 'info' | 'ai'
  size?: 'sm' | 'md'
  className?: string
  dot?: boolean
  pulse?: boolean
}

export default function Badge({
  children,
  variant = 'default',
  size = 'md',
  className,
  dot = false,
  pulse = false,
}: BadgeProps) {
  const variants = {
    default: 'bg-light-100 text-light-600 border-light-200/60',
    success: 'bg-accent-50 text-accent-700 border-accent-200/60',
    warning: 'bg-amber-50 text-amber-700 border-amber-200/60',
    danger: 'bg-red-50 text-red-700 border-red-200/60',
    info: 'bg-primary-50 text-primary-700 border-primary-200/60',
    ai: 'bg-ai-50 text-ai-700 border-ai-200/60',
  }

  const dotColors = {
    default: 'bg-light-500',
    success: 'bg-accent-500',
    warning: 'bg-amber-500',
    danger: 'bg-red-500',
    info: 'bg-primary-500',
    ai: 'bg-ai-500',
  }

  const sizes = {
    sm: 'px-2 py-0.5 text-xs',
    md: 'px-2.5 py-1 text-xs',
  }

  return (
    <span
      className={clsx(
        'inline-flex items-center gap-1.5 font-medium rounded-full border',
        'transition-all duration-200 ease-snappy',
        'hover:scale-105',
        variants[variant],
        sizes[size],
        className
      )}
    >
      {dot && (
        <span className="relative flex h-1.5 w-1.5">
          {pulse && (
            <span className={clsx('absolute inline-flex h-full w-full rounded-full opacity-75 animate-ping', dotColors[variant])} />
          )}
          <span className={clsx('relative inline-flex rounded-full h-1.5 w-1.5', dotColors[variant])} />
        </span>
      )}
      {children}
    </span>
  )
}

export function StatusBadge({ status }: { status: string }) {
  const statusConfig: Record<string, { variant: BadgeProps['variant']; label: string; dot?: boolean; pulse?: boolean }> = {
    open: { variant: 'info', label: 'Open', dot: true, pulse: true },
    in_progress: { variant: 'warning', label: 'In Progress', dot: true, pulse: true },
    promise_to_pay: { variant: 'success', label: 'PTP', dot: true },
    resolved: { variant: 'success', label: 'Resolved', dot: true },
    escalated: { variant: 'danger', label: 'Escalated', dot: true, pulse: true },
    closed: { variant: 'default', label: 'Closed' },
    active: { variant: 'success', label: 'Active', dot: true, pulse: true },
    closed_loan: { variant: 'default', label: 'Closed' },
    draft: { variant: 'default', label: 'Draft' },
    scheduled: { variant: 'info', label: 'Scheduled', dot: true },
    running: { variant: 'warning', label: 'Running', dot: true, pulse: true },
    paused: { variant: 'warning', label: 'Paused' },
    completed: { variant: 'success', label: 'Completed' },
    cancelled: { variant: 'danger', label: 'Cancelled' },
  }

  const config = statusConfig[status] || { variant: 'default', label: status }

  return <Badge variant={config.variant} dot={config.dot} pulse={config.pulse}>{config.label}</Badge>
}

export function PriorityBadge({ priority }: { priority: number }) {
  const priorityConfig: Record<number, { variant: BadgeProps['variant']; label: string }> = {
    1: { variant: 'default', label: 'Low' },
    2: { variant: 'default', label: 'Low' },
    3: { variant: 'info', label: 'Medium' },
    4: { variant: 'warning', label: 'High' },
    5: { variant: 'danger', label: 'Critical' },
  }

  const config = priorityConfig[priority] || { variant: 'default', label: `P${priority}` }

  return <Badge variant={config.variant}>{config.label}</Badge>
}

export function BucketBadge({ bucket }: { bucket: string | null }) {
  const bucketConfig: Record<string, { variant: BadgeProps['variant']; label: string }> = {
    current: { variant: 'success', label: 'Current' },
    '1-30': { variant: 'info', label: '1-30 DPD' },
    '31-60': { variant: 'warning', label: '31-60 DPD' },
    '61-90': { variant: 'warning', label: '61-90 DPD' },
    '90+': { variant: 'danger', label: '90+ DPD' },
  }

  const config = bucketConfig[bucket || ''] || { variant: 'default', label: bucket || 'Unknown' }

  return <Badge variant={config.variant}>{config.label}</Badge>
}
