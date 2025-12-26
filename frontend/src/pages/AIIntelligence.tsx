import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  SparklesIcon,
  CalculatorIcon,
  ArrowPathIcon,
  ExclamationTriangleIcon,
  CheckCircleIcon,
  ClockIcon,
  PhoneIcon,
  ChatBubbleLeftRightIcon,
  EnvelopeIcon,
  ScaleIcon,
  MegaphoneIcon,
} from '@heroicons/react/24/outline'
import { mlService, StrategyResult, RiskResult, PriorityResult } from '../services/mlService'
import { useAuthStore } from '../stores/authStore'

// Strategy to campaign mapping
const STRATEGY_CAMPAIGNS = [
  {
    strategy: 'gentle_reminder',
    label: 'Gentle Reminder',
    dpd_min: 1,
    dpd_max: 7,
    channels: ['whatsapp', 'sms'],
    description: 'Soft reminder for recently overdue accounts',
    color: 'bg-green-100 text-green-700 border-green-200',
  },
  {
    strategy: 'firm_reminder',
    label: 'Firm Reminder',
    dpd_min: 8,
    dpd_max: 30,
    channels: ['voice', 'whatsapp', 'sms'],
    description: 'Professional follow-up with payment options',
    color: 'bg-yellow-100 text-yellow-700 border-yellow-200',
  },
  {
    strategy: 'intensive_followup',
    label: 'Intensive Followup',
    dpd_min: 31,
    dpd_max: 60,
    channels: ['voice', 'whatsapp', 'sms'],
    description: 'Intensive collection with escalation warning',
    color: 'bg-orange-100 text-orange-700 border-orange-200',
  },
  {
    strategy: 'escalated_collection',
    label: 'Escalated Collection',
    dpd_min: 61,
    dpd_max: 90,
    channels: ['voice', 'whatsapp', 'sms'],
    description: 'Escalated collection with legal warning',
    color: 'bg-red-100 text-red-700 border-red-200',
  },
]

const STRATEGY_COLORS: Record<string, string> = {
  no_action: 'bg-gray-100 text-gray-700',
  gentle_reminder: 'bg-green-100 text-green-700',
  firm_reminder: 'bg-yellow-100 text-yellow-700',
  intensive_followup: 'bg-orange-100 text-orange-700',
  escalated_collection: 'bg-red-100 text-red-700',
  legal_recovery: 'bg-purple-100 text-purple-700',
}

const RISK_COLORS: Record<string, string> = {
  Low: 'bg-green-100 text-green-700 border-green-200',
  Medium: 'bg-yellow-100 text-yellow-700 border-yellow-200',
  High: 'bg-orange-100 text-orange-700 border-orange-200',
  'Very High': 'bg-red-100 text-red-700 border-red-200',
}

const CHANNEL_ICONS: Record<string, React.ElementType> = {
  call: PhoneIcon,
  whatsapp: ChatBubbleLeftRightIcon,
  sms: ChatBubbleLeftRightIcon,
  email: EnvelopeIcon,
  legal_notice: ScaleIcon,
}

export default function AIIntelligence() {
  const navigate = useNavigate()
  const { user } = useAuthStore()
  const isAdmin = user?.role === 'admin'
  const isManager = user?.role === 'manager'

  const createCampaignFromStrategy = (strategy: typeof STRATEGY_CAMPAIGNS[0]) => {
    const params = new URLSearchParams({
      new: 'true',
      strategy: strategy.strategy,
      dpd_min: strategy.dpd_min.toString(),
      dpd_max: strategy.dpd_max.toString(),
      channel: strategy.channels[0],
      name: `${strategy.label} Campaign`,
    })
    navigate(`/campaigns?${params.toString()}`)
  }

  // Simulator state
  const [dpd, setDpd] = useState(30)
  const [overdueAmount, setOverdueAmount] = useState(10000)
  const [principalAmount, setPrincipalAmount] = useState(100000)
  const [totalAttempts, setTotalAttempts] = useState(0)

  // Results state
  const [strategy, setStrategy] = useState<StrategyResult | null>(null)
  const [risk, setRisk] = useState<RiskResult | null>(null)
  const [priority, setPriority] = useState<PriorityResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Batch state
  const [batchLoading, setBatchLoading] = useState(false)
  const [batchResult, setBatchResult] = useState<{ cases_updated: number } | null>(null)

  const runAnalysis = async () => {
    setLoading(true)
    setError(null)

    try {
      const [strategyRes, riskRes, priorityRes] = await Promise.all([
        mlService.recommendStrategy({ dpd }),
        mlService.assessRisk({
          dpd,
          overdue_amount: overdueAmount,
          principal_amount: principalAmount,
          total_attempts: totalAttempts,
        }),
        mlService.calculatePriority({
          dpd,
          overdue_amount: overdueAmount,
          principal_amount: principalAmount,
        }),
      ])

      setStrategy(strategyRes)
      setRisk(riskRes)
      setPriority(priorityRes)
    } catch (err) {
      setError('Failed to run analysis')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const runBatchRecalculate = async () => {
    setBatchLoading(true)
    setBatchResult(null)

    try {
      const result = await mlService.batchRecalculatePriorities()
      setBatchResult(result)
    } catch (err) {
      setError('Failed to run batch recalculation')
      console.error(err)
    } finally {
      setBatchLoading(false)
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-light-900 flex items-center gap-2">
            <SparklesIcon className="h-7 w-7 text-primary-500" />
            AI Intelligence
          </h1>
          <p className="text-light-500 mt-1">
            Collection strategy recommendations and risk analysis
          </p>
        </div>

        {(isAdmin || isManager) && (
          <button
            onClick={runBatchRecalculate}
            disabled={batchLoading}
            className="flex items-center gap-2 px-4 py-2 bg-primary-500 text-white rounded-lg hover:bg-primary-600 disabled:opacity-50 transition-colors"
          >
            <ArrowPathIcon className={`h-5 w-5 ${batchLoading ? 'animate-spin' : ''}`} />
            {batchLoading ? 'Recalculating...' : 'Recalculate All Cases'}
          </button>
        )}
      </div>

      {batchResult && (
        <div className="bg-green-50 border border-green-200 rounded-lg p-4 flex items-center gap-3">
          <CheckCircleIcon className="h-5 w-5 text-green-500" />
          <span className="text-green-700">
            Successfully updated {batchResult.cases_updated} cases with new priorities
          </span>
        </div>
      )}

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 flex items-center gap-3">
          <ExclamationTriangleIcon className="h-5 w-5 text-red-500" />
          <span className="text-red-700">{error}</span>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Simulator Input */}
        <div className="bg-white rounded-xl shadow-sm border border-light-200 p-6">
          <h2 className="text-lg font-semibold text-light-900 mb-4 flex items-center gap-2">
            <CalculatorIcon className="h-5 w-5 text-primary-500" />
            Simulator
          </h2>

          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-light-700 mb-1">
                Days Past Due (DPD)
              </label>
              <input
                type="number"
                value={dpd}
                onChange={(e) => setDpd(parseInt(e.target.value) || 0)}
                className="w-full px-3 py-2 border border-light-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
              />
              <input
                type="range"
                min="0"
                max="180"
                value={dpd}
                onChange={(e) => setDpd(parseInt(e.target.value))}
                className="w-full mt-2"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-light-700 mb-1">
                Overdue Amount
              </label>
              <input
                type="number"
                value={overdueAmount}
                onChange={(e) => setOverdueAmount(parseInt(e.target.value) || 0)}
                className="w-full px-3 py-2 border border-light-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-light-700 mb-1">
                Principal Amount
              </label>
              <input
                type="number"
                value={principalAmount}
                onChange={(e) => setPrincipalAmount(parseInt(e.target.value) || 0)}
                className="w-full px-3 py-2 border border-light-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-light-700 mb-1">
                Contact Attempts
              </label>
              <input
                type="number"
                value={totalAttempts}
                onChange={(e) => setTotalAttempts(parseInt(e.target.value) || 0)}
                className="w-full px-3 py-2 border border-light-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
              />
            </div>

            <button
              onClick={runAnalysis}
              disabled={loading}
              className="w-full py-2 bg-primary-500 text-white rounded-lg hover:bg-primary-600 disabled:opacity-50 transition-colors flex items-center justify-center gap-2"
            >
              {loading ? (
                <>
                  <ArrowPathIcon className="h-5 w-5 animate-spin" />
                  Analyzing...
                </>
              ) : (
                <>
                  <SparklesIcon className="h-5 w-5" />
                  Run Analysis
                </>
              )}
            </button>
          </div>
        </div>

        {/* Strategy Result */}
        <div className="bg-white rounded-xl shadow-sm border border-light-200 p-6">
          <h2 className="text-lg font-semibold text-light-900 mb-4">
            Collection Strategy
          </h2>

          {strategy ? (
            <div className="space-y-4">
              <div
                className={`inline-block px-3 py-1 rounded-full text-sm font-medium ${
                  STRATEGY_COLORS[strategy.strategy] || 'bg-gray-100'
                }`}
              >
                {strategy.strategy.replace(/_/g, ' ').toUpperCase()}
              </div>

              <p className="text-light-600">{strategy.description}</p>

              <div>
                <h4 className="text-sm font-medium text-light-700 mb-2">Channels</h4>
                <div className="flex flex-wrap gap-2">
                  {strategy.channels.map((channel) => {
                    const Icon = CHANNEL_ICONS[channel] || ChatBubbleLeftRightIcon
                    return (
                      <span
                        key={channel}
                        className="inline-flex items-center gap-1 px-2 py-1 bg-light-100 rounded text-sm text-light-700"
                      >
                        <Icon className="h-4 w-4" />
                        {channel}
                      </span>
                    )
                  })}
                </div>
              </div>

              <div className="flex gap-4">
                <div>
                  <span className="text-xs text-light-500">Frequency</span>
                  <p className="text-sm font-medium text-light-700">{strategy.frequency}</p>
                </div>
                <div>
                  <span className="text-xs text-light-500">Tone</span>
                  <p className="text-sm font-medium text-light-700">{strategy.tone}</p>
                </div>
              </div>

              {strategy.suggested_actions && (
                <div>
                  <h4 className="text-sm font-medium text-light-700 mb-2">Suggested Actions</h4>
                  <ul className="space-y-1">
                    {strategy.suggested_actions.map((action, i) => (
                      <li key={i} className="text-sm text-light-600 flex items-start gap-2">
                        <CheckCircleIcon className="h-4 w-4 text-primary-500 mt-0.5 flex-shrink-0" />
                        {action}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {strategy.legal_action_recommended && (
                <div className="bg-red-50 border border-red-200 rounded-lg p-3 flex items-center gap-2">
                  <ScaleIcon className="h-5 w-5 text-red-500" />
                  <span className="text-sm text-red-700">Legal action recommended</span>
                </div>
              )}
            </div>
          ) : (
            <div className="text-center py-8 text-light-400">
              <ClockIcon className="h-12 w-12 mx-auto mb-2" />
              <p>Run analysis to see strategy</p>
            </div>
          )}
        </div>

        {/* Risk & Priority Result */}
        <div className="bg-white rounded-xl shadow-sm border border-light-200 p-6">
          <h2 className="text-lg font-semibold text-light-900 mb-4">
            Risk & Priority
          </h2>

          {risk && priority ? (
            <div className="space-y-6">
              {/* Risk Score */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium text-light-700">Risk Score</span>
                  <span
                    className={`px-2 py-0.5 rounded text-sm font-medium border ${
                      RISK_COLORS[risk.risk_level] || 'bg-gray-100'
                    }`}
                  >
                    {risk.risk_level}
                  </span>
                </div>
                <div className="relative h-4 bg-light-100 rounded-full overflow-hidden">
                  <div
                    className="absolute inset-y-0 left-0 bg-gradient-to-r from-green-500 via-yellow-500 to-red-500 rounded-full"
                    style={{ width: `${risk.score * 100}%` }}
                  />
                </div>
                <div className="flex justify-between mt-1 text-xs text-light-500">
                  <span>0%</span>
                  <span className="font-medium text-light-700">
                    {(risk.score * 100).toFixed(1)}%
                  </span>
                  <span>100%</span>
                </div>
              </div>

              {/* Priority Score */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium text-light-700">Priority Score</span>
                  <span className="text-2xl font-bold text-primary-600">
                    {priority.score.toFixed(1)}/10
                  </span>
                </div>
                <div className="flex gap-1">
                  {[1, 2, 3, 4, 5].map((level) => (
                    <div
                      key={level}
                      className={`flex-1 h-2 rounded ${
                        level <= priority.priority_level
                          ? level <= 2
                            ? 'bg-green-500'
                            : level <= 3
                            ? 'bg-yellow-500'
                            : level <= 4
                            ? 'bg-orange-500'
                            : 'bg-red-500'
                          : 'bg-light-200'
                      }`}
                    />
                  ))}
                </div>
                <p className="text-center mt-1 text-sm text-light-600">
                  Priority Level: {priority.priority_level}
                </p>
              </div>

              {/* Factors */}
              <div>
                <h4 className="text-sm font-medium text-light-700 mb-2">Risk Factors</h4>
                <div className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span className="text-light-500">DPD Factor</span>
                    <span className="text-light-700">
                      {(risk.factors.dpd_factor * 100).toFixed(1)}%
                    </span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-light-500">Overdue Factor</span>
                    <span className="text-light-700">
                      {(risk.factors.overdue_factor * 100).toFixed(1)}%
                    </span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-light-500">Contact Resistance</span>
                    <span className="text-light-700">
                      {(risk.factors.contact_factor * 100).toFixed(1)}%
                    </span>
                  </div>
                </div>
              </div>

              <div className="text-xs text-light-400 text-center">
                Model: {risk.model}
              </div>
            </div>
          ) : (
            <div className="text-center py-8 text-light-400">
              <ClockIcon className="h-12 w-12 mx-auto mb-2" />
              <p>Run analysis to see risk & priority</p>
            </div>
          )}
        </div>
      </div>

      {/* Strategy Guide */}
      <div className="bg-white rounded-xl shadow-sm border border-light-200 p-6">
        <h2 className="text-lg font-semibold text-light-900 mb-4">Strategy Guide</h2>
        <div className="overflow-x-auto">
          <table className="min-w-full">
            <thead>
              <tr className="border-b border-light-200">
                <th className="text-left py-2 px-3 text-sm font-medium text-light-500">DPD</th>
                <th className="text-left py-2 px-3 text-sm font-medium text-light-500">Strategy</th>
                <th className="text-left py-2 px-3 text-sm font-medium text-light-500">Channels</th>
                <th className="text-left py-2 px-3 text-sm font-medium text-light-500">Tone</th>
              </tr>
            </thead>
            <tbody>
              <tr className="border-b border-light-100">
                <td className="py-2 px-3 text-sm">0-7</td>
                <td className="py-2 px-3">
                  <span className="px-2 py-0.5 bg-green-100 text-green-700 rounded text-sm">
                    Gentle Reminder
                  </span>
                </td>
                <td className="py-2 px-3 text-sm text-light-600">WhatsApp, SMS</td>
                <td className="py-2 px-3 text-sm text-light-600">Polite</td>
              </tr>
              <tr className="border-b border-light-100">
                <td className="py-2 px-3 text-sm">8-30</td>
                <td className="py-2 px-3">
                  <span className="px-2 py-0.5 bg-yellow-100 text-yellow-700 rounded text-sm">
                    Firm Reminder
                  </span>
                </td>
                <td className="py-2 px-3 text-sm text-light-600">Call, WhatsApp, SMS</td>
                <td className="py-2 px-3 text-sm text-light-600">Professional</td>
              </tr>
              <tr className="border-b border-light-100">
                <td className="py-2 px-3 text-sm">31-60</td>
                <td className="py-2 px-3">
                  <span className="px-2 py-0.5 bg-orange-100 text-orange-700 rounded text-sm">
                    Intensive Followup
                  </span>
                </td>
                <td className="py-2 px-3 text-sm text-light-600">All channels</td>
                <td className="py-2 px-3 text-sm text-light-600">Firm</td>
              </tr>
              <tr className="border-b border-light-100">
                <td className="py-2 px-3 text-sm">61-90</td>
                <td className="py-2 px-3">
                  <span className="px-2 py-0.5 bg-red-100 text-red-700 rounded text-sm">
                    Escalated Collection
                  </span>
                </td>
                <td className="py-2 px-3 text-sm text-light-600">All channels</td>
                <td className="py-2 px-3 text-sm text-light-600">Urgent</td>
              </tr>
              <tr>
                <td className="py-2 px-3 text-sm">90+</td>
                <td className="py-2 px-3">
                  <span className="px-2 py-0.5 bg-purple-100 text-purple-700 rounded text-sm">
                    Legal Recovery
                  </span>
                </td>
                <td className="py-2 px-3 text-sm text-light-600">Legal notice, Email</td>
                <td className="py-2 px-3 text-sm text-light-600">Formal</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      {/* Quick Campaign Creation */}
      {(isAdmin || isManager) && (
        <div className="bg-white rounded-xl shadow-sm border border-light-200 p-6">
          <h2 className="text-lg font-semibold text-light-900 mb-4 flex items-center gap-2">
            <MegaphoneIcon className="h-5 w-5 text-primary-500" />
            Quick Campaign Creation
          </h2>
          <p className="text-light-500 text-sm mb-4">
            Create campaigns targeting cases by their collection strategy. Cases are automatically filtered by DPD range.
          </p>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {STRATEGY_CAMPAIGNS.map((strat) => (
              <div
                key={strat.strategy}
                className={`border rounded-lg p-4 ${strat.color}`}
              >
                <h3 className="font-medium mb-1">{strat.label}</h3>
                <p className="text-sm opacity-80 mb-2">DPD {strat.dpd_min}-{strat.dpd_max}</p>
                <p className="text-xs opacity-70 mb-3">{strat.description}</p>
                <div className="flex flex-wrap gap-1 mb-3">
                  {strat.channels.map((ch) => (
                    <span key={ch} className="text-xs bg-white/50 px-1.5 py-0.5 rounded">
                      {ch}
                    </span>
                  ))}
                </div>
                <button
                  onClick={() => createCampaignFromStrategy(strat)}
                  className="w-full py-1.5 bg-white/80 hover:bg-white rounded text-sm font-medium transition-colors"
                >
                  Create Campaign
                </button>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
