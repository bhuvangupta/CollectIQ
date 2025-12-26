import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'
import {
  CurrencyRupeeIcon,
  FolderIcon,
  PhoneIcon,
  ChartBarIcon,
  ArrowTrendingUpIcon,
  ArrowTrendingDownIcon,
  SparklesIcon,
  MagnifyingGlassIcon,
  BanknotesIcon,
  ClockIcon,
  ExclamationCircleIcon,
} from '@heroicons/react/24/outline'
import { useInitiateCall } from '../hooks/useCommunications'
import Modal from '../components/ui/Modal'
import Button from '../components/ui/Button'
import {
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  AreaChart,
  Area,
} from 'recharts'
import api from '../services/api'
import Card, { CardHeader, CardTitle } from '../components/ui/Card'
import { AnimatedCounter } from '../components/ui/AnimatedCounter'
import type { DashboardStats } from '../types'

const COLORS = ['#10B981', '#06B6D4', '#F59E0B', '#EF4444', '#64748B']

export default function Dashboard() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [callModalOpen, setCallModalOpen] = useState(false)
  const [paymentModalOpen, setPaymentModalOpen] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [paymentSearchQuery, setPaymentSearchQuery] = useState('')
  const [selectedCase, setSelectedCase] = useState<any>(null)
  const [selectedPaymentCase, setSelectedPaymentCase] = useState<any>(null)
  const [paymentAmount, setPaymentAmount] = useState('')
  const [paymentDate, setPaymentDate] = useState(new Date().toISOString().split('T')[0])
  const [paymentMode, setPaymentMode] = useState('cash')
  const [transactionRef, setTransactionRef] = useState('')
  const [paymentNotes, setPaymentNotes] = useState('')
  const initiateCall = useInitiateCall()

  const { data: stats, isLoading } = useQuery({
    queryKey: ['dashboardStats'],
    queryFn: async () => {
      const response = await api.get<DashboardStats>('/analytics/dashboard')
      return response.data
    },
  })

  const { data: bucketData } = useQuery({
    queryKey: ['bucketDistribution'],
    queryFn: async () => {
      const response = await api.get('/analytics/portfolio/bucket-distribution')
      return response.data.buckets
    },
  })

  // Search cases for call modal
  const { data: searchResults } = useQuery({
    queryKey: ['searchCases', searchQuery],
    queryFn: async () => {
      const response = await api.get(`/cases?search=${searchQuery}&page_size=10`)
      return response.data.items
    },
    enabled: callModalOpen && searchQuery.length > 0,
  })

  // Get recent cases for quick selection
  const { data: recentCases } = useQuery({
    queryKey: ['recentCases'],
    queryFn: async () => {
      const response = await api.get('/cases?page_size=5')
      return response.data.items
    },
    enabled: callModalOpen,
  })

  // Search cases for payment modal
  const { data: paymentSearchResults } = useQuery({
    queryKey: ['searchPaymentCases', paymentSearchQuery],
    queryFn: async () => {
      const response = await api.get(`/cases?search=${paymentSearchQuery}&page_size=10`)
      return response.data.items
    },
    enabled: paymentModalOpen && paymentSearchQuery.length > 0,
  })

  // Get recent cases for payment modal
  const { data: recentPaymentCases } = useQuery({
    queryKey: ['recentPaymentCases'],
    queryFn: async () => {
      const response = await api.get('/cases?page_size=5')
      return response.data.items
    },
    enabled: paymentModalOpen,
  })

  // Get scheduled follow-ups (cases with next_follow_up set)
  const { data: scheduledFollowUps } = useQuery({
    queryKey: ['scheduledFollowUps'],
    queryFn: async () => {
      const response = await api.get('/cases?page_size=50')
      // Filter cases with next_follow_up and sort by date
      const casesWithFollowUp = (response.data.items || [])
        .filter((c: any) => c.next_follow_up)
        .sort((a: any, b: any) => new Date(a.next_follow_up).getTime() - new Date(b.next_follow_up).getTime())
      return casesWithFollowUp.slice(0, 10) // Show top 10
    },
  })

  // Record payment mutation
  const recordPayment = useMutation({
    mutationFn: async (data: {
      loan_id: string
      borrower_id: string
      amount: number
      payment_date: string
      payment_mode: string
      transaction_reference?: string
      notes?: string
    }) => {
      const response = await api.post('/payments', data)
      return response.data
    },
    onSuccess: () => {
      toast.success('Payment recorded successfully')
      queryClient.invalidateQueries({ queryKey: ['dashboardStats'] })
      queryClient.invalidateQueries({ queryKey: ['casePayments'] })
      setPaymentModalOpen(false)
      resetPaymentForm()
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to record payment')
    },
  })

  const resetPaymentForm = () => {
    setSelectedPaymentCase(null)
    setPaymentSearchQuery('')
    setPaymentAmount('')
    setPaymentDate(new Date().toISOString().split('T')[0])
    setPaymentMode('cash')
    setTransactionRef('')
    setPaymentNotes('')
  }

  const handleRecordPayment = () => {
    if (!selectedPaymentCase || !paymentAmount) {
      toast.error('Please select a case and enter amount')
      return
    }
    recordPayment.mutate({
      loan_id: selectedPaymentCase.loan_id,
      borrower_id: selectedPaymentCase.borrower_id,
      amount: parseFloat(paymentAmount),
      payment_date: paymentDate,
      payment_mode: paymentMode,
      transaction_reference: transactionRef || undefined,
      notes: paymentNotes || undefined,
    })
  }

  const handleMakeCall = () => {
    if (!selectedCase) {
      toast.error('Please select a case first')
      return
    }
    initiateCall.mutate(
      {
        case_id: selectedCase.id,
      },
      {
        onSuccess: () => {
          setCallModalOpen(false)
          setSelectedCase(null)
          setSearchQuery('')
        },
      }
    )
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="relative">
          <div className="animate-spin rounded-full h-10 w-10 border-2 border-light-200 border-t-primary-500" />
          <div className="absolute inset-0 rounded-full animate-pulse-ring bg-primary-500/20" />
        </div>
      </div>
    )
  }

  const statCards = [
    {
      name: 'Total Outstanding',
      value: (stats?.portfolio.total_outstanding || 0) / 100000,
      suffix: 'L',
      prefix: '₹',
      decimals: 1,
      subtext: `${stats?.portfolio.overdue_percentage || 0}% overdue`,
      icon: CurrencyRupeeIcon,
      trend: 'up',
      trendValue: '+12.5%',
      gradient: 'from-primary-500 to-primary-600',
      bgGlow: 'bg-primary-500/10',
    },
    {
      name: 'Open Cases',
      value: stats?.cases.open_cases || 0,
      subtext: `${stats?.cases.resolved_today || 0} resolved today`,
      icon: FolderIcon,
      trend: 'down',
      trendValue: '-8.2%',
      gradient: 'from-amber-500 to-amber-600',
      bgGlow: 'bg-amber-500/10',
    },
    {
      name: 'Calls Today',
      value: stats?.communications.calls_today || 0,
      subtext: `${stats?.communications.contact_rate || 0}% contact rate`,
      icon: PhoneIcon,
      trend: 'up',
      trendValue: '+24.3%',
      gradient: 'from-accent-500 to-accent-600',
      bgGlow: 'bg-accent-500/10',
    },
    {
      name: 'AI Conversations',
      value: stats?.campaigns.active || 0,
      subtext: 'Active sessions',
      icon: SparklesIcon,
      trend: 'up',
      trendValue: '+45.1%',
      gradient: 'from-ai-500 to-ai-600',
      bgGlow: 'bg-ai-500/10',
    },
  ]

  const pieData = bucketData?.map((b: any) => ({
    name: b.bucket,
    value: b.count,
  })) || []

  const collectionData = [
    { day: 'Mon', amount: 125000, ai: 45000 },
    { day: 'Tue', amount: 180000, ai: 72000 },
    { day: 'Wed', amount: 145000, ai: 58000 },
    { day: 'Thu', amount: 210000, ai: 95000 },
    { day: 'Fri', amount: 175000, ai: 78000 },
    { day: 'Sat', amount: 95000, ai: 42000 },
    { day: 'Sun', amount: 45000, ai: 18000 },
  ]

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold text-light-900">Dashboard</h1>
          <p className="mt-1 text-xs sm:text-sm text-light-500">
            Real-time overview of your collection performance
          </p>
        </div>
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-accent-50 border border-accent-200 self-start sm:self-auto">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-accent-400 opacity-75" />
            <span className="relative inline-flex rounded-full h-2 w-2 bg-accent-500" />
          </span>
          <span className="text-sm text-accent-700">Live</span>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4 stagger-grid">
        {statCards.map((stat, index) => (
          <Card
            key={stat.name}
            className="relative overflow-hidden group"
            glow
            hover
            style={{ animationDelay: `${index * 0.05}s` }}
          >
            <div className={`absolute top-0 right-0 w-32 h-32 rounded-full ${stat.bgGlow} blur-2xl -translate-y-1/2 translate-x-1/2 transition-transform duration-500 group-hover:scale-150`} />
            <div className="relative">
              <div className="flex items-start justify-between">
                <div className={`rounded-xl bg-gradient-to-br ${stat.gradient} p-3 shadow-lg transition-transform duration-300 group-hover:scale-110`}>
                  <stat.icon className="h-6 w-6 text-white" />
                </div>
                <div className={`flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded-full ${stat.trend === 'up' ? 'text-accent-600 bg-accent-50' : 'text-red-600 bg-red-50'}`}>
                  {stat.trend === 'up' ? (
                    <ArrowTrendingUpIcon className="h-3 w-3" />
                  ) : (
                    <ArrowTrendingDownIcon className="h-3 w-3" />
                  )}
                  {stat.trendValue}
                </div>
              </div>
              <div className="mt-4">
                <p className="text-sm font-medium text-light-500">{stat.name}</p>
                <p className="mt-1 text-3xl font-bold text-light-900 font-mono tabular-nums">
                  <AnimatedCounter
                    value={stat.value}
                    prefix={stat.prefix || ''}
                    suffix={stat.suffix || ''}
                    decimals={stat.decimals || 0}
                    duration={800}
                  />
                </p>
                <p className="mt-1 text-sm text-light-400">{stat.subtext}</p>
              </div>
            </div>
          </Card>
        ))}
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Collection Trend */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>Collection Trend</CardTitle>
              <div className="flex items-center gap-4 text-xs">
                <div className="flex items-center gap-1.5">
                  <span className="w-2.5 h-2.5 rounded-full bg-primary-500" />
                  <span className="text-light-500">Total</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="w-2.5 h-2.5 rounded-full bg-accent-500" />
                  <span className="text-light-500">AI Collected</span>
                </div>
              </div>
            </div>
          </CardHeader>
          <div className="h-64 sm:h-80">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={collectionData}>
                <defs>
                  <linearGradient id="colorAmount" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#06B6D4" stopOpacity={0.2}/>
                    <stop offset="95%" stopColor="#06B6D4" stopOpacity={0}/>
                  </linearGradient>
                  <linearGradient id="colorAI" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#10B981" stopOpacity={0.2}/>
                    <stop offset="95%" stopColor="#10B981" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
                <XAxis dataKey="day" stroke="#94a3b8" fontSize={12} tickLine={false} axisLine={false} />
                <YAxis stroke="#94a3b8" fontSize={12} tickLine={false} axisLine={false} tickFormatter={(value) => `₹${value/1000}K`} />
                <Tooltip
                  contentStyle={{ backgroundColor: '#ffffff', border: '1px solid #e2e8f0', borderRadius: '8px', boxShadow: '0 4px 6px -1px rgba(0,0,0,0.1)' }}
                  labelStyle={{ color: '#475569' }}
                  formatter={(value: number) => [`₹${(value / 1000).toFixed(0)}K`, '']}
                />
                <Area type="monotone" dataKey="amount" stroke="#06B6D4" strokeWidth={2} fillOpacity={1} fill="url(#colorAmount)" />
                <Area type="monotone" dataKey="ai" stroke="#10B981" strokeWidth={2} fillOpacity={1} fill="url(#colorAI)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </Card>

        {/* Bucket Distribution */}
        <Card>
          <CardHeader>
            <CardTitle>Portfolio by DPD Bucket</CardTitle>
          </CardHeader>
          <div className="h-64 sm:h-80">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={pieData}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={100}
                  paddingAngle={4}
                  dataKey="value"
                >
                  {pieData.map((_: any, index: number) => (
                    <Cell
                      key={`cell-${index}`}
                      fill={COLORS[index % COLORS.length]}
                      stroke="transparent"
                    />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{ backgroundColor: '#ffffff', border: '1px solid #e2e8f0', borderRadius: '8px', boxShadow: '0 4px 6px -1px rgba(0,0,0,0.1)' }}
                  labelStyle={{ color: '#475569' }}
                />
              </PieChart>
            </ResponsiveContainer>
            <div className="flex flex-wrap justify-center gap-4 -mt-4">
              {pieData.map((entry: any, index: number) => (
                <div key={entry.name} className="flex items-center gap-2">
                  <span className="w-3 h-3 rounded-full" style={{ backgroundColor: COLORS[index % COLORS.length] }} />
                  <span className="text-xs text-light-500">{entry.name}</span>
                </div>
              ))}
            </div>
          </div>
        </Card>
      </div>

      {/* Quick Actions & Scheduled Follow-ups */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Quick Actions */}
        <Card className="lg:col-span-1">
          <CardHeader>
            <CardTitle>Quick Actions</CardTitle>
          </CardHeader>
          <div className="grid grid-cols-2 gap-3">
            {[
              { icon: PhoneIcon, label: 'Make Call', color: 'primary', bgColor: 'bg-primary-50', hoverBg: 'group-hover:bg-primary-100', iconColor: 'text-primary-600', action: () => setCallModalOpen(true) },
              { icon: FolderIcon, label: 'New Case', color: 'amber', bgColor: 'bg-amber-50', hoverBg: 'group-hover:bg-amber-100', iconColor: 'text-amber-600', action: () => navigate('/cases?new=true') },
              { icon: ChartBarIcon, label: 'Campaign', color: 'accent', bgColor: 'bg-accent-50', hoverBg: 'group-hover:bg-accent-100', iconColor: 'text-accent-600', action: () => navigate('/campaigns?new=true') },
              { icon: CurrencyRupeeIcon, label: 'Payment', color: 'ai', bgColor: 'bg-ai-50', hoverBg: 'group-hover:bg-ai-100', iconColor: 'text-ai-600', action: () => setPaymentModalOpen(true) },
            ].map((action) => (
              <button
                key={action.label}
                onClick={action.action}
                className="quick-action"
              >
                <div className={`quick-action-icon ${action.bgColor} ${action.hoverBg}`}>
                  <action.icon className={`h-5 w-5 ${action.iconColor}`} />
                </div>
                <span className="mt-2 text-xs font-medium text-light-700 group-hover:text-light-900 transition-colors">
                  {action.label}
                </span>
              </button>
            ))}
          </div>
        </Card>

        {/* Scheduled Follow-ups */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>Scheduled Follow-ups</CardTitle>
              <button
                onClick={() => navigate('/cases')}
                className="text-xs text-primary-600 hover:text-primary-800"
              >
                View All
              </button>
            </div>
          </CardHeader>
          <div className="space-y-2 max-h-64 overflow-y-auto scrollbar-thin">
            {(!scheduledFollowUps || scheduledFollowUps.length === 0) ? (
              <div className="text-center py-8">
                <ClockIcon className="h-10 w-10 text-light-300 mx-auto mb-2" />
                <p className="text-sm text-light-500">No scheduled follow-ups</p>
              </div>
            ) : (
              scheduledFollowUps.map((caseItem: any, index: number) => {
                const followUpDate = new Date(caseItem.next_follow_up)
                const now = new Date()
                const isOverdue = followUpDate < now
                const isToday = followUpDate.toDateString() === now.toDateString()
                const isTomorrow = followUpDate.toDateString() === new Date(now.getTime() + 86400000).toDateString()

                let dateLabel = followUpDate.toLocaleDateString('en-IN', { day: 'numeric', month: 'short' })
                let timeLabel = followUpDate.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' })

                if (isToday) dateLabel = 'Today'
                else if (isTomorrow) dateLabel = 'Tomorrow'

                return (
                  <div
                    key={caseItem.id}
                    onClick={() => navigate(`/cases/${caseItem.id}`)}
                    className={`follow-up-item ${
                      isOverdue
                        ? 'follow-up-overdue'
                        : isToday
                        ? 'follow-up-today'
                        : 'follow-up-upcoming'
                    }`}
                    style={{ animationDelay: `${index * 0.03}s` }}
                  >
                    <div className={`p-2 rounded-lg transition-colors ${
                      isOverdue ? 'bg-red-100' : isToday ? 'bg-amber-100' : 'bg-light-100'
                    }`}>
                      {isOverdue ? (
                        <ExclamationCircleIcon className="h-4 w-4 text-red-600" />
                      ) : (
                        <ClockIcon className={`h-4 w-4 ${isToday ? 'text-amber-600' : 'text-light-500'}`} />
                      )}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium text-light-900 truncate">
                          {caseItem.borrower_name || caseItem.case_number}
                        </span>
                        {isOverdue && (
                          <span className="text-xs px-1.5 py-0.5 rounded-full bg-red-100 text-red-700 font-medium">
                            Overdue
                          </span>
                        )}
                      </div>
                      <p className="text-xs text-light-500 truncate">
                        {caseItem.case_number} • ₹{(caseItem.total_outstanding || 0).toLocaleString()}
                      </p>
                    </div>
                    <div className="text-right">
                      <p className={`text-xs font-medium ${
                        isOverdue ? 'text-red-600' : isToday ? 'text-amber-600' : 'text-light-700'
                      }`}>
                        {dateLabel}
                      </p>
                      <p className="text-xs text-light-500">{timeLabel}</p>
                    </div>
                  </div>
                )
              })
            )}
          </div>
        </Card>
      </div>

      {/* Make Call Modal */}
      <Modal
        isOpen={callModalOpen}
        onClose={() => {
          setCallModalOpen(false)
          setSelectedCase(null)
          setSearchQuery('')
        }}
        title="Make a Call"
      >
        <div className="space-y-4">
          {/* Search */}
          <div className="relative">
            <MagnifyingGlassIcon className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-light-400" />
            <input
              type="text"
              placeholder="Search by case number or borrower..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full rounded-lg border border-light-300 bg-white py-2 pl-10 pr-4 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
            />
          </div>

          {/* Results */}
          <div className="max-h-64 overflow-y-auto space-y-2">
            {searchQuery.length > 0 && searchResults?.length === 0 && (
              <p className="text-sm text-light-500 text-center py-4">No cases found</p>
            )}

            {(searchQuery.length > 0 ? searchResults : recentCases)?.map((caseItem: any) => (
              <button
                key={caseItem.id}
                onClick={() => setSelectedCase(caseItem)}
                className={`w-full text-left p-3 rounded-lg border transition-colors ${
                  selectedCase?.id === caseItem.id
                    ? 'border-primary-500 bg-primary-50'
                    : 'border-light-200 hover:border-light-300 hover:bg-light-50'
                }`}
              >
                <div className="flex justify-between items-start">
                  <div>
                    <p className="font-medium text-light-900">{caseItem.case_number}</p>
                    <p className="text-sm text-light-500">
                      {caseItem.borrower_name || 'Borrower'}
                    </p>
                  </div>
                  <span className={`text-xs px-2 py-1 rounded-full ${
                    caseItem.priority === 1 ? 'bg-red-100 text-red-700' :
                    caseItem.priority === 2 ? 'bg-amber-100 text-amber-700' :
                    'bg-light-100 text-light-600'
                  }`}>
                    P{caseItem.priority}
                  </span>
                </div>
              </button>
            ))}

            {!searchQuery && recentCases?.length === 0 && (
              <p className="text-sm text-light-500 text-center py-4">No recent cases</p>
            )}
          </div>

          {selectedCase && (
            <div className="p-3 rounded-lg bg-accent-50 border border-accent-200">
              <p className="text-sm text-accent-700">
                Ready to call case <span className="font-medium">{selectedCase.case_number}</span>
              </p>
            </div>
          )}

          <div className="flex justify-end gap-3 pt-2">
            <Button
              variant="secondary"
              onClick={() => {
                setCallModalOpen(false)
                setSelectedCase(null)
                setSearchQuery('')
              }}
            >
              Cancel
            </Button>
            <Button
              onClick={handleMakeCall}
              loading={initiateCall.isPending}
              disabled={!selectedCase}
            >
              <PhoneIcon className="h-4 w-4 mr-2" />
              Call Now
            </Button>
          </div>
        </div>
      </Modal>

      {/* Record Payment Modal */}
      <Modal
        isOpen={paymentModalOpen}
        onClose={() => {
          setPaymentModalOpen(false)
          resetPaymentForm()
        }}
        title="Record Payment"
        size="lg"
      >
        <div className="space-y-4">
          {/* Step 1: Select Case */}
          {!selectedPaymentCase ? (
            <>
              <div className="relative">
                <MagnifyingGlassIcon className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-light-400" />
                <input
                  type="text"
                  placeholder="Search by case number or borrower..."
                  value={paymentSearchQuery}
                  onChange={(e) => setPaymentSearchQuery(e.target.value)}
                  className="w-full rounded-lg border border-light-300 bg-white py-2 pl-10 pr-4 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                />
              </div>

              <div className="max-h-64 overflow-y-auto space-y-2">
                {paymentSearchQuery.length > 0 && paymentSearchResults?.length === 0 && (
                  <p className="text-sm text-light-500 text-center py-4">No cases found</p>
                )}

                {(paymentSearchQuery.length > 0 ? paymentSearchResults : recentPaymentCases)?.map((caseItem: any) => (
                  <button
                    key={caseItem.id}
                    onClick={() => setSelectedPaymentCase(caseItem)}
                    className="w-full text-left p-3 rounded-lg border border-light-200 hover:border-primary-300 hover:bg-light-50 transition-colors"
                  >
                    <div className="flex justify-between items-start">
                      <div>
                        <p className="font-medium text-light-900">{caseItem.case_number}</p>
                        <p className="text-sm text-light-500">{caseItem.borrower_name}</p>
                      </div>
                      <div className="text-right">
                        <p className="text-sm font-medium text-light-900">
                          ₹{(caseItem.total_outstanding || 0).toLocaleString()}
                        </p>
                        <p className="text-xs text-light-500">Outstanding</p>
                      </div>
                    </div>
                  </button>
                ))}

                {!paymentSearchQuery && recentPaymentCases?.length === 0 && (
                  <p className="text-sm text-light-500 text-center py-4">No recent cases</p>
                )}
              </div>
            </>
          ) : (
            <>
              {/* Borrower info - matches CaseDetail */}
              <div className="p-3 rounded-lg bg-light-50 border border-light-200">
                <div className="flex justify-between items-center">
                  <div>
                    <p className="text-sm text-light-700">
                      <span className="font-medium">Borrower:</span> {selectedPaymentCase.borrower_name}
                    </p>
                    <p className="text-sm text-light-700">
                      <span className="font-medium">Outstanding:</span> ₹{(selectedPaymentCase.total_outstanding || 0).toLocaleString()}
                    </p>
                  </div>
                  <button
                    onClick={() => setSelectedPaymentCase(null)}
                    className="text-xs text-primary-600 hover:text-primary-800 underline"
                  >
                    Change Case
                  </button>
                </div>
              </div>

              {/* Amount */}
              <div>
                <label className="block text-sm font-medium text-light-700 mb-1">
                  Amount (₹) <span className="text-red-500">*</span>
                </label>
                <div className="relative">
                  <span className="absolute left-3 top-2.5 text-light-500">₹</span>
                  <input
                    type="number"
                    step="0.01"
                    min="1"
                    className="block w-full rounded-lg bg-white border border-light-300 pl-8 pr-4 py-2.5 shadow-sm text-light-900 placeholder-light-400 sm:text-sm focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500"
                    placeholder="Enter amount"
                    value={paymentAmount}
                    onChange={(e) => setPaymentAmount(e.target.value)}
                  />
                </div>
              </div>

              {/* Payment Date */}
              <div>
                <label className="block text-sm font-medium text-light-700 mb-1">
                  Payment Date <span className="text-red-500">*</span>
                </label>
                <input
                  type="date"
                  className="block w-full rounded-lg bg-white border border-light-300 px-4 py-2.5 shadow-sm text-light-900 sm:text-sm focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500"
                  value={paymentDate}
                  onChange={(e) => setPaymentDate(e.target.value)}
                />
              </div>

              {/* Payment Mode */}
              <div>
                <label className="block text-sm font-medium text-light-700 mb-1">
                  Payment Mode <span className="text-red-500">*</span>
                </label>
                <select
                  className="block w-full rounded-lg bg-white border border-light-300 px-4 py-2.5 shadow-sm text-light-900 sm:text-sm focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500"
                  value={paymentMode}
                  onChange={(e) => setPaymentMode(e.target.value)}
                >
                  <option value="cash">Cash</option>
                  <option value="cheque">Cheque</option>
                  <option value="neft">NEFT</option>
                  <option value="imps">IMPS</option>
                  <option value="upi">UPI</option>
                  <option value="auto_debit">Auto Debit</option>
                  <option value="card">Card</option>
                  <option value="other">Other</option>
                </select>
              </div>

              {/* Transaction Reference */}
              <div>
                <label className="block text-sm font-medium text-light-700 mb-1">
                  Transaction Reference / Cheque No.
                </label>
                <input
                  type="text"
                  className="block w-full rounded-lg bg-white border border-light-300 px-4 py-2.5 shadow-sm text-light-900 placeholder-light-400 sm:text-sm focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500"
                  placeholder="Enter reference number"
                  value={transactionRef}
                  onChange={(e) => setTransactionRef(e.target.value)}
                />
              </div>

              {/* Notes */}
              <div>
                <label className="block text-sm font-medium text-light-700 mb-1">
                  Notes
                </label>
                <textarea
                  rows={2}
                  className="block w-full rounded-lg bg-white border border-light-300 px-4 py-2.5 shadow-sm text-light-900 placeholder-light-400 sm:text-sm focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500"
                  placeholder="Any additional notes..."
                  value={paymentNotes}
                  onChange={(e) => setPaymentNotes(e.target.value)}
                />
              </div>
            </>
          )}

          {/* Actions */}
          <div className="flex justify-end gap-3 pt-2">
            <Button
              variant="secondary"
              onClick={() => {
                setPaymentModalOpen(false)
                resetPaymentForm()
              }}
            >
              Cancel
            </Button>
            {selectedPaymentCase && (
              <Button
                onClick={handleRecordPayment}
                loading={recordPayment.isPending}
                disabled={!paymentAmount || parseFloat(paymentAmount) <= 0}
              >
                <BanknotesIcon className="h-4 w-4 mr-2" />
                Record Payment
              </Button>
            )}
          </div>
        </div>
      </Modal>
    </div>
  )
}
