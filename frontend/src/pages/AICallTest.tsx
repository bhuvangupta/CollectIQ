import { useState, useEffect, useCallback } from 'react'
import {
  PhoneIcon,
  PhoneXMarkIcon,
  ArrowPathIcon,
  CheckCircleIcon,
  XCircleIcon,
  ClockIcon,
  PlayIcon,
  DocumentTextIcon,
} from '@heroicons/react/24/outline'
import Card from '../components/ui/Card'
import Button from '../components/ui/Button'
import { api } from '../services/api'

interface CallState {
  callId: string | null
  status: string
  duration: number | null
  transcript: string | null
  recordingUrl: string | null
  disposition: string | null
}

interface BorrowerForm {
  phone_number: string
  borrower_name: string
  outstanding_amount: number
  emi_amount: number
  dpd: number
  loan_type: string
}

const DEFAULT_FORM: BorrowerForm = {
  phone_number: '+91',
  borrower_name: '',
  outstanding_amount: 10000,
  emi_amount: 2000,
  dpd: 15,
  loan_type: 'Personal Loan',
}

const STATUS_CONFIG: Record<string, { color: string; icon: typeof CheckCircleIcon }> = {
  initiated: { color: 'text-blue-500', icon: ClockIcon },
  queued: { color: 'text-blue-500', icon: ClockIcon },
  ringing: { color: 'text-amber-500', icon: PhoneIcon },
  in_progress: { color: 'text-green-500', icon: PhoneIcon },
  completed: { color: 'text-green-600', icon: CheckCircleIcon },
  failed: { color: 'text-red-500', icon: XCircleIcon },
  no_answer: { color: 'text-gray-500', icon: PhoneXMarkIcon },
  busy: { color: 'text-orange-500', icon: PhoneXMarkIcon },
  cancelled: { color: 'text-gray-500', icon: XCircleIcon },
}

export default function AICallTest() {
  const [form, setForm] = useState<BorrowerForm>(DEFAULT_FORM)
  const [callState, setCallState] = useState<CallState>({
    callId: null,
    status: '',
    duration: null,
    transcript: null,
    recordingUrl: null,
    disposition: null,
  })
  const [isLoading, setIsLoading] = useState(false)
  const [isSyncing, setIsSyncing] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [autoSync, setAutoSync] = useState(false)

  // Auto-sync call status
  useEffect(() => {
    if (!autoSync || !callState.callId) return
    if (['completed', 'failed', 'no_answer', 'busy', 'cancelled'].includes(callState.status)) {
      setAutoSync(false)
      return
    }

    const interval = setInterval(() => {
      syncCallStatus()
    }, 3000)

    return () => clearInterval(interval)
  }, [autoSync, callState.callId, callState.status])

  const makeCall = async () => {
    if (!form.phone_number || !form.borrower_name) {
      setError('Phone number and borrower name are required')
      return
    }

    setIsLoading(true)
    setError(null)

    try {
      const response = await api.post('/voice/call', form)

      if (response.data.success) {
        setCallState({
          callId: response.data.call_id,
          status: 'initiated',
          duration: null,
          transcript: null,
          recordingUrl: null,
          disposition: null,
        })
        setAutoSync(true)
      } else {
        setError(response.data.message || 'Failed to initiate call')
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Failed to make call')
    } finally {
      setIsLoading(false)
    }
  }

  const stopCall = async () => {
    if (!callState.callId) return

    try {
      await api.post(`/voice/call/${callState.callId}/stop`)
      setCallState(prev => ({ ...prev, status: 'cancelled' }))
      setAutoSync(false)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to stop call')
    }
  }

  const syncCallStatus = useCallback(async () => {
    if (!callState.callId) return

    setIsSyncing(true)
    try {
      const response = await api.post(`/voice/call/${callState.callId}/sync`)
      setCallState({
        callId: callState.callId,
        status: response.data.status,
        duration: response.data.duration,
        transcript: response.data.transcript,
        recordingUrl: response.data.recording_url,
        disposition: response.data.disposition,
      })
    } catch (err: any) {
      console.error('Sync error:', err)
    } finally {
      setIsSyncing(false)
    }
  }, [callState.callId])

  const resetCall = () => {
    setCallState({
      callId: null,
      status: '',
      duration: null,
      transcript: null,
      recordingUrl: null,
      disposition: null,
    })
    setAutoSync(false)
    setError(null)
  }

  const formatDuration = (seconds: number | null) => {
    if (!seconds) return '--:--'
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`
  }

  const StatusIcon = callState.status ? STATUS_CONFIG[callState.status]?.icon || ClockIcon : ClockIcon
  const statusColor = callState.status ? STATUS_CONFIG[callState.status]?.color || 'text-gray-500' : 'text-gray-500'

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl sm:text-2xl font-bold text-light-900">AI Call Test</h1>
        <p className="mt-1 text-xs sm:text-sm text-light-500">
          Test AI voice calls - makes real phone calls to borrowers
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Call Form */}
        <Card>
          <h3 className="text-sm font-medium text-light-700 mb-4">Call Details</h3>

          <div className="space-y-4">
            <div>
              <label className="block text-xs text-light-500 mb-1">Phone Number *</label>
              <input
                type="tel"
                value={form.phone_number}
                onChange={(e) => setForm(prev => ({ ...prev, phone_number: e.target.value }))}
                placeholder="+919876543210"
                disabled={!!callState.callId}
                className="w-full rounded-lg border border-light-300 px-3 py-2 text-sm disabled:bg-light-100"
              />
              <p className="text-xs text-light-400 mt-1">E.164 format (e.g., +919876543210)</p>
            </div>

            <div>
              <label className="block text-xs text-light-500 mb-1">Borrower Name *</label>
              <input
                type="text"
                value={form.borrower_name}
                onChange={(e) => setForm(prev => ({ ...prev, borrower_name: e.target.value }))}
                placeholder="Rahul Sharma"
                disabled={!!callState.callId}
                className="w-full rounded-lg border border-light-300 px-3 py-2 text-sm disabled:bg-light-100"
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-xs text-light-500 mb-1">Outstanding Amount</label>
                <input
                  type="number"
                  value={form.outstanding_amount}
                  onChange={(e) => setForm(prev => ({ ...prev, outstanding_amount: Number(e.target.value) }))}
                  disabled={!!callState.callId}
                  className="w-full rounded-lg border border-light-300 px-3 py-2 text-sm disabled:bg-light-100"
                />
              </div>
              <div>
                <label className="block text-xs text-light-500 mb-1">EMI Amount</label>
                <input
                  type="number"
                  value={form.emi_amount}
                  onChange={(e) => setForm(prev => ({ ...prev, emi_amount: Number(e.target.value) }))}
                  disabled={!!callState.callId}
                  className="w-full rounded-lg border border-light-300 px-3 py-2 text-sm disabled:bg-light-100"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-xs text-light-500 mb-1">Days Past Due</label>
                <input
                  type="number"
                  value={form.dpd}
                  onChange={(e) => setForm(prev => ({ ...prev, dpd: Number(e.target.value) }))}
                  disabled={!!callState.callId}
                  className="w-full rounded-lg border border-light-300 px-3 py-2 text-sm disabled:bg-light-100"
                />
              </div>
              <div>
                <label className="block text-xs text-light-500 mb-1">Loan Type</label>
                <select
                  value={form.loan_type}
                  onChange={(e) => setForm(prev => ({ ...prev, loan_type: e.target.value }))}
                  disabled={!!callState.callId}
                  className="w-full rounded-lg border border-light-300 px-3 py-2 text-sm disabled:bg-light-100"
                >
                  <option value="Personal Loan">Personal Loan</option>
                  <option value="Home Loan">Home Loan</option>
                  <option value="Vehicle Loan">Vehicle Loan</option>
                  <option value="Business Loan">Business Loan</option>
                  <option value="Credit Card">Credit Card</option>
                </select>
              </div>
            </div>
          </div>

          {error && (
            <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-600">
              {error}
            </div>
          )}

          <div className="mt-6 flex gap-3">
            {!callState.callId ? (
              <Button
                onClick={makeCall}
                loading={isLoading}
                className="flex-1"
              >
                <PhoneIcon className="h-4 w-4 mr-2" />
                Make Call
              </Button>
            ) : (
              <>
                {['initiated', 'queued', 'ringing', 'in_progress'].includes(callState.status) && (
                  <Button
                    variant="secondary"
                    onClick={stopCall}
                    className="flex-1"
                  >
                    <PhoneXMarkIcon className="h-4 w-4 mr-2" />
                    Stop Call
                  </Button>
                )}
                <Button
                  variant="secondary"
                  onClick={resetCall}
                  className="flex-1"
                >
                  New Call
                </Button>
              </>
            )}
          </div>
        </Card>

        {/* Call Status */}
        <Card>
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-medium text-light-700">Call Status</h3>
            {callState.callId && (
              <Button
                variant="secondary"
                size="sm"
                onClick={syncCallStatus}
                loading={isSyncing}
              >
                <ArrowPathIcon className={`h-4 w-4 mr-1 ${isSyncing ? 'animate-spin' : ''}`} />
                Sync
              </Button>
            )}
          </div>

          {callState.callId ? (
            <div className="space-y-4">
              {/* Status Badge */}
              <div className="flex items-center gap-3 p-4 bg-light-50 rounded-lg">
                <StatusIcon className={`h-8 w-8 ${statusColor}`} />
                <div>
                  <p className="text-sm font-medium text-light-800 capitalize">
                    {callState.status.replace('_', ' ')}
                  </p>
                  <p className="text-xs text-light-500">
                    Call ID: {callState.callId.slice(0, 8)}...
                  </p>
                </div>
                <div className="ml-auto text-right">
                  <p className="text-lg font-mono font-medium text-light-800">
                    {formatDuration(callState.duration)}
                  </p>
                  <p className="text-xs text-light-500">Duration</p>
                </div>
              </div>

              {/* Auto-sync indicator */}
              {autoSync && (
                <div className="flex items-center gap-2 text-xs text-light-500">
                  <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
                  Auto-syncing every 3 seconds...
                </div>
              )}

              {/* Disposition */}
              {callState.disposition && (
                <div className="p-3 bg-primary-50 border border-primary-200 rounded-lg">
                  <p className="text-xs text-primary-600 font-medium">Disposition</p>
                  <p className="text-sm text-primary-800 capitalize">
                    {callState.disposition.replace('_', ' ')}
                  </p>
                </div>
              )}

              {/* Recording */}
              {callState.recordingUrl && (
                <div className="p-3 bg-light-50 rounded-lg">
                  <p className="text-xs text-light-500 mb-2 flex items-center gap-1">
                    <PlayIcon className="h-3 w-3" />
                    Recording
                  </p>
                  <audio
                    controls
                    src={callState.recordingUrl}
                    className="w-full h-10"
                  />
                </div>
              )}

              {/* Transcript */}
              {callState.transcript && (
                <div className="p-3 bg-light-50 rounded-lg">
                  <p className="text-xs text-light-500 mb-2 flex items-center gap-1">
                    <DocumentTextIcon className="h-3 w-3" />
                    Transcript
                  </p>
                  <div className="max-h-48 overflow-y-auto text-sm text-light-700 whitespace-pre-wrap font-mono bg-white p-3 rounded border border-light-200">
                    {callState.transcript}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center py-12 text-light-400">
              <PhoneIcon className="h-12 w-12 mb-3 opacity-50" />
              <p className="text-sm">No active call</p>
              <p className="text-xs mt-1">Fill in the details and click "Make Call"</p>
            </div>
          )}
        </Card>
      </div>

      {/* Info Section */}
      <Card>
        <h3 className="text-sm font-medium text-light-700 mb-3">How it works</h3>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 text-xs text-light-600">
          <div className="flex gap-2">
            <span className="font-bold text-primary-600">1.</span>
            <span>Enter the borrower's phone number and details</span>
          </div>
          <div className="flex gap-2">
            <span className="font-bold text-primary-600">2.</span>
            <span>Bolna AI calls the number with Priya (AI agent)</span>
          </div>
          <div className="flex gap-2">
            <span className="font-bold text-primary-600">3.</span>
            <span>AI conducts collection conversation in Hinglish</span>
          </div>
          <div className="flex gap-2">
            <span className="font-bold text-primary-600">4.</span>
            <span>View transcript and recording after call ends</span>
          </div>
        </div>
      </Card>
    </div>
  )
}
