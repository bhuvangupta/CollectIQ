import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import {
  ArrowDownTrayIcon,
} from '@heroicons/react/24/outline'
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts'
import api from '../services/api'
import Card, { CardHeader, CardTitle } from '../components/ui/Card'
import Button from '../components/ui/Button'

export default function Reports() {
  const [dateRange, setDateRange] = useState('30')
  const [exporting, setExporting] = useState(false)

  const handleExport = async () => {
    setExporting(true)
    try {
      const response = await api.get(`/analytics/export?days=${dateRange}`, {
        responseType: 'blob',
      })
      const url = window.URL.createObjectURL(new Blob([response.data]))
      const link = document.createElement('a')
      link.href = url
      link.setAttribute('download', `report-${dateRange}days-${new Date().toISOString().split('T')[0]}.csv`)
      document.body.appendChild(link)
      link.click()
      link.remove()
      toast.success('Report exported successfully')
    } catch {
      toast.error('Export not available yet')
    } finally {
      setExporting(false)
    }
  }

  const { data: agentPerformance } = useQuery({
    queryKey: ['agentPerformance', dateRange],
    queryFn: async () => {
      const response = await api.get(`/analytics/agents/performance?days=${dateRange}`)
      return response.data.agents
    },
  })

  const { data: collectionTrend } = useQuery({
    queryKey: ['collectionTrend', dateRange],
    queryFn: async () => {
      const response = await api.get(`/analytics/collections/trend?days=${dateRange}`)
      return response.data.trend
    },
  })

  const { data: dispositionBreakdown } = useQuery({
    queryKey: ['dispositionBreakdown', dateRange],
    queryFn: async () => {
      const response = await api.get(`/analytics/disposition/breakdown?days=${dateRange}`)
      return response.data.dispositions
    },
  })

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900">Reports</h1>
          <p className="mt-1 text-sm text-gray-500">
            Analytics and performance reports
          </p>
        </div>
        <div className="flex gap-2">
          <select
            className="block rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm"
            value={dateRange}
            onChange={(e) => setDateRange(e.target.value)}
          >
            <option value="7">Last 7 days</option>
            <option value="30">Last 30 days</option>
            <option value="60">Last 60 days</option>
            <option value="90">Last 90 days</option>
          </select>
          <Button variant="secondary" onClick={handleExport} loading={exporting}>
            <ArrowDownTrayIcon className="h-5 w-5 mr-2" />
            Export
          </Button>
        </div>
      </div>

      {/* Collection Trend */}
      <Card>
        <CardHeader>
          <CardTitle>Collection Trend</CardTitle>
        </CardHeader>
        <div className="h-80">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={collectionTrend || []}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis
                dataKey="date"
                tickFormatter={(value) => new Date(value).toLocaleDateString('en-IN', { day: 'numeric', month: 'short' })}
              />
              <YAxis
                tickFormatter={(value) => `₹${(value / 1000).toFixed(0)}K`}
              />
              <Tooltip
                formatter={(value: number) => [`₹${value.toLocaleString()}`, 'Amount']}
                labelFormatter={(label) => new Date(label).toLocaleDateString()}
              />
              <Legend />
              <Line
                type="monotone"
                dataKey="amount"
                stroke="#3B82F6"
                strokeWidth={2}
                dot={false}
                name="Collection Amount"
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </Card>

      {/* Agent Performance */}
      <Card>
        <CardHeader>
          <CardTitle>Agent Performance</CardTitle>
        </CardHeader>
        <div className="h-80">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={agentPerformance || []}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="agent_name" />
              <YAxis />
              <Tooltip />
              <Legend />
              <Bar dataKey="total_calls" fill="#3B82F6" name="Total Calls" />
              <Bar dataKey="connected_calls" fill="#10B981" name="Connected" />
              <Bar dataKey="promises_secured" fill="#F59E0B" name="Promises" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </Card>

      {/* Disposition Breakdown */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle>Call Disposition Summary</CardTitle>
          </CardHeader>
          <div className="space-y-4">
            {dispositionBreakdown &&
              Object.entries(dispositionBreakdown).map(([disp, data]: [string, any]) => (
                <div key={disp} className="flex items-center justify-between">
                  <span className="text-sm font-medium text-gray-700 capitalize">
                    {disp.replace('_', ' ')}
                  </span>
                  <div className="flex items-center gap-2">
                    <div className="w-24 h-2 bg-gray-200 rounded-full">
                      <div
                        className="h-2 bg-primary-600 rounded-full"
                        style={{ width: `${Math.min(100, data.total / 10)}%` }}
                      />
                    </div>
                    <span className="text-sm text-gray-500 w-12 text-right">
                      {data.total}
                    </span>
                  </div>
                </div>
              ))}
          </div>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Quick Stats</CardTitle>
          </CardHeader>
          <div className="grid grid-cols-2 gap-4">
            <div className="p-4 bg-blue-50 rounded-lg">
              <div className="text-2xl font-semibold text-blue-600">
                {agentPerformance?.reduce((sum: number, a: any) => sum + a.total_calls, 0) || 0}
              </div>
              <div className="text-sm text-blue-600">Total Calls</div>
            </div>
            <div className="p-4 bg-green-50 rounded-lg">
              <div className="text-2xl font-semibold text-green-600">
                {agentPerformance?.reduce((sum: number, a: any) => sum + a.connected_calls, 0) || 0}
              </div>
              <div className="text-sm text-green-600">Connected</div>
            </div>
            <div className="p-4 bg-yellow-50 rounded-lg">
              <div className="text-2xl font-semibold text-yellow-600">
                {agentPerformance?.reduce((sum: number, a: any) => sum + a.promises_secured, 0) || 0}
              </div>
              <div className="text-sm text-yellow-600">Promises</div>
            </div>
            <div className="p-4 bg-purple-50 rounded-lg">
              <div className="text-2xl font-semibold text-purple-600">
                {agentPerformance?.reduce((sum: number, a: any) => sum + a.talk_time_minutes, 0) || 0}
              </div>
              <div className="text-sm text-purple-600">Talk Time (min)</div>
            </div>
          </div>
        </Card>
      </div>
    </div>
  )
}
