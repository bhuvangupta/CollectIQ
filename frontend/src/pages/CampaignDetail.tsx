import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import {
  ArrowLeftIcon,
  PhoneIcon,
  CheckCircleIcon,
  XCircleIcon,
  ClockIcon,
  UserGroupIcon,
  ChartBarIcon,
  ArrowTrendingUpIcon,
  BeakerIcon,
  ChatBubbleLeftRightIcon,
  SparklesIcon,
} from '@heroicons/react/24/outline'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  AreaChart,
  Area,
} from 'recharts'
import api from '../services/api'
import Card, { CardHeader, CardTitle } from '../components/ui/Card'
import Button from '../components/ui/Button'
import { StatusBadge } from '../components/ui/Badge'
import { AnimatedCounter } from '../components/ui/AnimatedCounter'

interface SimulationBorrower {
  borrower_name: string
  phone: string
  amount: number
  dpd: number
  strategy: string
  message: string
  ai_script?: {
    opening: string
    objection_handling: string[]
    closing: string
    tone: string
    language: string
    suggested_responses: Record<string, string>
  }
}

interface SimulationResult {
  campaign_id: string
  campaign_name: string
  campaign_type: string
  sample_borrowers: SimulationBorrower[]
  total_targets: number
  message_template: string
}

interface CampaignAnalytics {
  campaign: {
    id: string
    name: string
    campaign_type: string
    status: string
    created_at: string
    started_at: string | null
    completed_at: string | null
  }
  stats: {
    total_targets: number
    total_attempted: number
    total_successful: number
    total_failed: number
    success_rate: number
    avg_duration_seconds: number
    total_cost: number
  }
  funnel: {
    stage: string
    count: number
    percentage: number
  }[]
  hourly_trend: {
    hour: number
    attempts: number
    successes: number
    success_rate: number
  }[]
  daily_trend: {
    date: string
    attempts: number
    successes: number
    success_rate: number
  }[]
}

export default function CampaignDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [showSimulation, setShowSimulation] = useState(false)
  const [simulationResult, setSimulationResult] = useState<SimulationResult | null>(null)

  const simulateMutation = useMutation({
    mutationFn: async () => {
      const response = await api.post<SimulationResult>(`/campaigns/${id}/simulate`)
      return response.data
    },
    onSuccess: (data) => {
      setSimulationResult(data)
      setShowSimulation(true)
      toast.success('Simulation generated successfully')
    },
    onError: (error: any) => {
      const message = error.response?.data?.detail || 'Failed to generate simulation'
      toast.error(message)
    },
  })

  const { data: analytics, isLoading } = useQuery({
    queryKey: ['campaignAnalytics', id],
    queryFn: async () => {
      const response = await api.get<CampaignAnalytics>(`/analytics/campaigns/${id}/analytics`)
      return response.data
    },
    enabled: !!id,
  })

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

  if (!analytics) {
    return (
      <div className="text-center py-12">
        <p className="text-light-500">Campaign not found</p>
        <Button variant="secondary" onClick={() => navigate('/campaigns')} className="mt-4">
          Back to Campaigns
        </Button>
      </div>
    )
  }

  const { campaign, stats, funnel, hourly_trend, daily_trend } = analytics

  const statCards = [
    {
      name: 'Total Targets',
      value: stats.total_targets,
      icon: UserGroupIcon,
      gradient: 'from-primary-500 to-primary-600',
      bgGlow: 'bg-primary-500/10',
    },
    {
      name: 'Attempted',
      value: stats.total_attempted,
      icon: PhoneIcon,
      gradient: 'from-amber-500 to-amber-600',
      bgGlow: 'bg-amber-500/10',
    },
    {
      name: 'Successful',
      value: stats.total_successful,
      icon: CheckCircleIcon,
      gradient: 'from-accent-500 to-accent-600',
      bgGlow: 'bg-accent-500/10',
    },
    {
      name: 'Success Rate',
      value: stats.success_rate,
      suffix: '%',
      decimals: 1,
      icon: ArrowTrendingUpIcon,
      gradient: 'from-ai-500 to-ai-600',
      bgGlow: 'bg-ai-500/10',
    },
  ]

  const funnelColors = ['#06B6D4', '#10B981', '#F59E0B', '#EF4444', '#64748B']

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" onClick={() => navigate('/campaigns')}>
            <ArrowLeftIcon className="h-5 w-5" />
          </Button>
          <div>
            <h1 className="text-xl sm:text-2xl font-bold text-light-900">{campaign.name}</h1>
            <div className="flex items-center gap-3 mt-1">
              <span className="text-sm text-light-500 capitalize">
                {campaign.campaign_type.replace('_', ' ')}
              </span>
              <StatusBadge status={campaign.status} />
            </div>
          </div>
        </div>
        <Button
          variant="secondary"
          onClick={() => simulateMutation.mutate()}
          loading={simulateMutation.isPending}
        >
          <BeakerIcon className="h-5 w-5 mr-2" />
          Simulate Campaign
        </Button>
      </div>

      {/* Simulation Results */}
      {showSimulation && simulationResult && (
        <Card className="border-2 border-ai-500/30 bg-gradient-to-br from-ai-500/5 to-transparent">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-ai-500/10">
                <SparklesIcon className="h-5 w-5 text-ai-500" />
              </div>
              <div>
                <h3 className="text-lg font-semibold text-light-900">Campaign Simulation Preview</h3>
                <p className="text-sm text-light-500">
                  Showing {simulationResult.sample_borrowers.length} sample messages from {simulationResult.total_targets} total targets
                </p>
              </div>
            </div>
            <Button variant="ghost" size="sm" onClick={() => setShowSimulation(false)}>
              Close
            </Button>
          </div>

          {/* Message Template */}
          <div className="mb-6 p-4 bg-light-100 rounded-lg">
            <p className="text-xs font-medium text-light-500 uppercase tracking-wide mb-2">Message Template</p>
            <p className="text-sm text-light-700 font-mono">{simulationResult.message_template}</p>
          </div>

          {/* Sample Messages */}
          <div className="space-y-4">
            {simulationResult.sample_borrowers.map((borrower, index) => (
              <div key={index} className="border border-light-200 rounded-lg overflow-hidden">
                {/* Borrower Header */}
                <div className="bg-light-50 px-4 py-3 flex items-center justify-between border-b border-light-200">
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-full bg-primary-500/10 flex items-center justify-center">
                      <span className="text-sm font-medium text-primary-600">
                        {borrower.borrower_name.charAt(0)}
                      </span>
                    </div>
                    <div>
                      <p className="font-medium text-light-900">{borrower.borrower_name}</p>
                      <p className="text-xs text-light-500">{borrower.phone}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-4 text-sm">
                    <span className="text-light-600">₹{borrower.amount.toLocaleString()}</span>
                    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                      borrower.dpd <= 30 ? 'bg-green-100 text-green-700' :
                      borrower.dpd <= 60 ? 'bg-yellow-100 text-yellow-700' :
                      borrower.dpd <= 90 ? 'bg-orange-100 text-orange-700' :
                      'bg-red-100 text-red-700'
                    }`}>
                      {borrower.dpd} DPD
                    </span>
                    <span className="px-2 py-0.5 rounded-full bg-ai-100 text-ai-700 text-xs font-medium">
                      {borrower.strategy}
                    </span>
                  </div>
                </div>

                {/* Message Preview */}
                <div className="p-4">
                  <div className="flex items-start gap-3 mb-4">
                    <ChatBubbleLeftRightIcon className="h-5 w-5 text-primary-500 flex-shrink-0 mt-0.5" />
                    <div className="flex-1">
                      <p className="text-xs font-medium text-light-500 uppercase tracking-wide mb-1">
                        {campaign.campaign_type === 'voice' ? 'Voice Message Script' : 'SMS/WhatsApp Message'}
                      </p>
                      <p className="text-sm text-light-700 bg-primary-50 rounded-lg p-3 border border-primary-100">
                        {borrower.message}
                      </p>
                    </div>
                  </div>

                  {/* AI Call Script (only for voice campaigns) */}
                  {borrower.ai_script && campaign.campaign_type === 'voice' && (
                    <div className="mt-4 pt-4 border-t border-light-200">
                      <div className="flex items-center gap-2 mb-3">
                        <SparklesIcon className="h-4 w-4 text-ai-500" />
                        <span className="text-xs font-medium text-ai-600 uppercase tracking-wide">
                          AI Call Script ({borrower.ai_script.tone} tone - {borrower.ai_script.language === 'hi' ? 'Hinglish' : 'English'})
                        </span>
                      </div>

                      <div className="space-y-3 text-sm">
                        {/* Opening */}
                        <div className="bg-green-50 rounded-lg p-3 border border-green-100">
                          <p className="text-xs font-medium text-green-600 mb-1">Opening</p>
                          <p className="text-green-800">{borrower.ai_script.opening}</p>
                        </div>

                        {/* Objection Handling */}
                        <div className="bg-amber-50 rounded-lg p-3 border border-amber-100">
                          <p className="text-xs font-medium text-amber-600 mb-2">Objection Handling</p>
                          <ul className="space-y-1">
                            {borrower.ai_script.objection_handling.map((obj, i) => (
                              <li key={i} className="text-amber-800 text-sm flex items-start gap-2">
                                <span className="text-amber-500">•</span>
                                {obj}
                              </li>
                            ))}
                          </ul>
                        </div>

                        {/* Suggested Responses */}
                        {Object.keys(borrower.ai_script.suggested_responses).length > 0 && (
                          <div className="bg-blue-50 rounded-lg p-3 border border-blue-100">
                            <p className="text-xs font-medium text-blue-600 mb-2">Suggested Responses</p>
                            <div className="space-y-2">
                              {Object.entries(borrower.ai_script.suggested_responses).map(([scenario, response]) => (
                                <div key={scenario} className="text-sm">
                                  <span className="font-medium text-blue-700 capitalize">{scenario.replace('_', ' ')}:</span>
                                  <span className="text-blue-800 ml-2">{response}</span>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}

                        {/* Closing */}
                        <div className="bg-purple-50 rounded-lg p-3 border border-purple-100">
                          <p className="text-xs font-medium text-purple-600 mb-1">Closing</p>
                          <p className="text-purple-800">{borrower.ai_script.closing}</p>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Stats Grid */}
      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
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
              </div>
              <div className="mt-4">
                <p className="text-sm font-medium text-light-500">{stat.name}</p>
                <p className="mt-1 text-3xl font-bold text-light-900 font-mono tabular-nums">
                  <AnimatedCounter
                    value={stat.value}
                    suffix={stat.suffix || ''}
                    decimals={stat.decimals || 0}
                    duration={800}
                  />
                </p>
              </div>
            </div>
          </Card>
        ))}
      </div>

      {/* Conversion Funnel & Daily Trend */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Conversion Funnel */}
        <Card>
          <CardHeader>
            <CardTitle>Conversion Funnel</CardTitle>
          </CardHeader>
          <div className="space-y-3">
            {funnel.map((stage, index) => (
              <div key={stage.stage} className="relative">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-sm font-medium text-light-700 capitalize">
                    {stage.stage.replace('_', ' ')}
                  </span>
                  <span className="text-sm text-light-500">
                    {stage.count} ({stage.percentage.toFixed(1)}%)
                  </span>
                </div>
                <div className="h-8 bg-light-100 rounded-lg overflow-hidden">
                  <div
                    className="h-full rounded-lg transition-all duration-500"
                    style={{
                      width: `${stage.percentage}%`,
                      backgroundColor: funnelColors[index % funnelColors.length],
                    }}
                  />
                </div>
              </div>
            ))}
          </div>
        </Card>

        {/* Daily Trend */}
        <Card>
          <CardHeader>
            <CardTitle>Daily Performance</CardTitle>
          </CardHeader>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={daily_trend}>
                <defs>
                  <linearGradient id="colorAttempts" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#06B6D4" stopOpacity={0.2}/>
                    <stop offset="95%" stopColor="#06B6D4" stopOpacity={0}/>
                  </linearGradient>
                  <linearGradient id="colorSuccesses" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#10B981" stopOpacity={0.2}/>
                    <stop offset="95%" stopColor="#10B981" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
                <XAxis
                  dataKey="date"
                  stroke="#94a3b8"
                  fontSize={12}
                  tickLine={false}
                  axisLine={false}
                  tickFormatter={(value) => new Date(value).toLocaleDateString('en-IN', { day: 'numeric', month: 'short' })}
                />
                <YAxis stroke="#94a3b8" fontSize={12} tickLine={false} axisLine={false} />
                <Tooltip
                  contentStyle={{ backgroundColor: '#ffffff', border: '1px solid #e2e8f0', borderRadius: '8px', boxShadow: '0 4px 6px -1px rgba(0,0,0,0.1)' }}
                  labelFormatter={(label) => new Date(label).toLocaleDateString()}
                />
                <Area type="monotone" dataKey="attempts" stroke="#06B6D4" strokeWidth={2} fillOpacity={1} fill="url(#colorAttempts)" name="Attempts" />
                <Area type="monotone" dataKey="successes" stroke="#10B981" strokeWidth={2} fillOpacity={1} fill="url(#colorSuccesses)" name="Successes" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </Card>
      </div>

      {/* Hourly Distribution */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>Hourly Distribution</CardTitle>
            <div className="flex items-center gap-4 text-xs">
              <div className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full bg-primary-500" />
                <span className="text-light-500">Attempts</span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full bg-accent-500" />
                <span className="text-light-500">Successes</span>
              </div>
            </div>
          </div>
        </CardHeader>
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={hourly_trend}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
              <XAxis
                dataKey="hour"
                stroke="#94a3b8"
                fontSize={12}
                tickLine={false}
                axisLine={false}
                tickFormatter={(value) => `${value}:00`}
              />
              <YAxis stroke="#94a3b8" fontSize={12} tickLine={false} axisLine={false} />
              <Tooltip
                contentStyle={{ backgroundColor: '#ffffff', border: '1px solid #e2e8f0', borderRadius: '8px', boxShadow: '0 4px 6px -1px rgba(0,0,0,0.1)' }}
                labelFormatter={(label) => `${label}:00 - ${label}:59`}
              />
              <Bar dataKey="attempts" fill="#06B6D4" name="Attempts" radius={[4, 4, 0, 0]} />
              <Bar dataKey="successes" fill="#10B981" name="Successes" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </Card>

      {/* Additional Stats */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <Card>
          <div className="flex items-center gap-4">
            <div className="p-3 rounded-xl bg-amber-50">
              <ClockIcon className="h-6 w-6 text-amber-600" />
            </div>
            <div>
              <p className="text-sm text-light-500">Avg Duration</p>
              <p className="text-xl font-bold text-light-900">
                {Math.floor(stats.avg_duration_seconds / 60)}m {Math.round(stats.avg_duration_seconds % 60)}s
              </p>
            </div>
          </div>
        </Card>

        <Card>
          <div className="flex items-center gap-4">
            <div className="p-3 rounded-xl bg-red-50">
              <XCircleIcon className="h-6 w-6 text-red-600" />
            </div>
            <div>
              <p className="text-sm text-light-500">Failed</p>
              <p className="text-xl font-bold text-light-900">{stats.total_failed}</p>
            </div>
          </div>
        </Card>

        <Card>
          <div className="flex items-center gap-4">
            <div className="p-3 rounded-xl bg-green-50">
              <ChartBarIcon className="h-6 w-6 text-green-600" />
            </div>
            <div>
              <p className="text-sm text-light-500">Completion</p>
              <p className="text-xl font-bold text-light-900">
                {stats.total_targets > 0 ? Math.round((stats.total_attempted / stats.total_targets) * 100) : 0}%
              </p>
            </div>
          </div>
        </Card>
      </div>
    </div>
  )
}
