import { useState, useEffect } from 'react'
import { useMutation } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import {
  SparklesIcon,
  PhoneIcon,
  ArrowPathIcon,
  CheckCircleIcon,
} from '@heroicons/react/24/outline'
import Modal from './ui/Modal'
import Button from './ui/Button'
import api from '../services/api'

interface AICallModalProps {
  isOpen: boolean
  onClose: () => void
  caseId: string
  borrowerId?: string
  loanId?: string
  borrowerName?: string
  borrowerPhone?: string
  preferredLanguage?: string
}

interface ScriptData {
  script: string
  context: {
    agent_name?: string
    organization_name?: string
    borrower_name?: string
    outstanding_amount?: number
    emi_amount?: number
    dpd?: number
    bucket?: string
    total_attempts?: number
  }
}

export default function AICallModal({
  isOpen,
  onClose,
  caseId,
  borrowerId: _borrowerId,
  loanId: _loanId,
  borrowerName,
  borrowerPhone,
  preferredLanguage = 'en',
}: AICallModalProps) {
  // borrowerId and loanId are passed but not directly used (available in scriptData.context)
  void _borrowerId
  void _loanId
  const [script, setScript] = useState('')
  const [language, setLanguage] = useState(preferredLanguage)
  const [callInitiated, setCallInitiated] = useState(false)
  const [scriptData, setScriptData] = useState<ScriptData | null>(null)

  // Generate script mutation
  const generateScript = useMutation({
    mutationFn: async (lang: string) => {
      const response = await api.post('/communications/generate-script', {
        case_id: caseId,
        language: lang,
      })
      return response.data as ScriptData
    },
    onSuccess: (data) => {
      setScriptData(data)
      setScript(data.script)
    },
  })

  // Generate script when modal opens or language changes
  useEffect(() => {
    if (isOpen && caseId) {
      generateScript.mutate(language)
    }
  }, [isOpen, caseId, language])

  // Reset state when modal closes or opens with new preferred language
  useEffect(() => {
    if (!isOpen) {
      setCallInitiated(false)
      setScriptData(null)
      setScript('')
    } else {
      // Set language to borrower's preferred language when modal opens
      setLanguage(preferredLanguage)
    }
  }, [isOpen, preferredLanguage])

  const handleRegenerate = () => {
    generateScript.mutate(language)
  }

  const scriptLoading = generateScript.isPending

  // Initiate AI call via Voice AI provider (Bolna)
  const initiateCall = useMutation({
    mutationFn: async () => {
      // Use the voice API endpoint for AI calls
      const response = await api.post('/voice/call', {
        phone_number: borrowerPhone,
        borrower_name: scriptData?.context?.borrower_name || borrowerName,
        outstanding_amount: scriptData?.context?.outstanding_amount || 0,
        emi_amount: scriptData?.context?.emi_amount || 0,
        dpd: scriptData?.context?.dpd || 0,
        loan_type: 'Personal Loan',
        case_id: caseId || undefined,
      })
      return response.data
    },
    onSuccess: (data) => {
      setCallInitiated(true)
      if (data.call_id) {
        console.log('AI Call initiated with ID:', data.call_id)
      }
    },
    onError: (error: any) => {
      const message = error.response?.data?.message || error.response?.data?.detail || 'Failed to initiate call'
      toast.error(message)
    },
  })

  const handleInitiateCall = () => {
    if (script.trim()) {
      initiateCall.mutate()
    }
  }

  const handleClose = () => {
    setCallInitiated(false)
    onClose()
  }

  return (
    <Modal isOpen={isOpen} onClose={handleClose} title="AI Call (Automated)" size="lg">
      <div className="space-y-4">
        {/* Info Banner */}
        <div className="p-3 rounded-lg bg-primary-50 border border-primary-200">
          <p className="text-sm text-primary-700">
            <strong>Automated AI Call:</strong> Our AI agent (Priya) will have a natural
            conversation with the borrower. The call is fully automated.
          </p>
        </div>

        {/* Recipient Info */}
        <div className="flex items-center justify-between p-3 rounded-lg bg-light-50 border border-light-200">
          <div>
            <p className="text-sm font-medium text-light-900">{borrowerName}</p>
            <p className="text-sm text-light-500">{borrowerPhone}</p>
          </div>
          <div className="flex items-center gap-2">
            <SparklesIcon className="h-5 w-5 text-primary-500" />
            <span className="text-sm font-medium text-primary-600">AI Agent: Priya</span>
          </div>
        </div>

        {/* Language Selector */}
        <div className="flex items-center gap-3">
          <label className="text-sm font-medium text-light-700">Language:</label>
          <div className="flex gap-2">
            <button
              type="button"
              className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                language === 'en'
                  ? 'bg-primary-100 text-primary-700 border border-primary-300'
                  : 'bg-light-100 text-light-600 border border-light-200 hover:bg-light-200'
              }`}
              onClick={() => setLanguage('en')}
            >
              English {preferredLanguage === 'en' && '★'}
            </button>
            <button
              type="button"
              className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                language === 'hinglish'
                  ? 'bg-primary-100 text-primary-700 border border-primary-300'
                  : 'bg-light-100 text-light-600 border border-light-200 hover:bg-light-200'
              }`}
              onClick={() => setLanguage('hinglish')}
            >
              Hinglish {preferredLanguage === 'hinglish' && '★'}
            </button>
            <button
              type="button"
              className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                language === 'hi'
                  ? 'bg-primary-100 text-primary-700 border border-primary-300'
                  : 'bg-light-100 text-light-600 border border-light-200 hover:bg-light-200'
              }`}
              onClick={() => setLanguage('hi')}
            >
              Hindi {preferredLanguage === 'hi' && '★'}
            </button>
          </div>
        </div>

        {/* Context Info */}
        {scriptData?.context && (
          <div className="grid grid-cols-4 gap-3 p-3 rounded-lg bg-light-50 border border-light-200">
            <div>
              <p className="text-xs text-light-500">Calling As</p>
              <p className="text-sm font-medium text-light-900">
                {scriptData.context.agent_name || '-'}
              </p>
            </div>
            <div>
              <p className="text-xs text-light-500">Outstanding</p>
              <p className="text-sm font-medium text-light-900">
                {scriptData.context.outstanding_amount?.toLocaleString('en-IN', {
                  style: 'currency',
                  currency: 'INR',
                  maximumFractionDigits: 0,
                }) || '-'}
              </p>
            </div>
            <div>
              <p className="text-xs text-light-500">DPD</p>
              <p className="text-sm font-medium text-light-900">
                {scriptData.context.dpd || 0} days
              </p>
            </div>
            <div>
              <p className="text-xs text-light-500">Previous Attempts</p>
              <p className="text-sm font-medium text-light-900">
                {scriptData.context.total_attempts || 0}
              </p>
            </div>
          </div>
        )}

        {/* Script Editor */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <label className="text-sm font-medium text-light-700">
              Call Script
            </label>
            <Button
              variant="ghost"
              size="sm"
              onClick={handleRegenerate}
              disabled={scriptLoading}
            >
              <ArrowPathIcon
                className={`h-4 w-4 mr-1 ${scriptLoading ? 'animate-spin' : ''}`}
              />
              Regenerate
            </Button>
          </div>
          {scriptLoading ? (
            <div className="flex items-center justify-center h-48 rounded-lg border border-light-200 bg-light-50">
              <div className="text-center">
                <ArrowPathIcon className="h-8 w-8 text-primary-500 animate-spin mx-auto" />
                <p className="mt-2 text-sm text-light-500">Generating script...</p>
              </div>
            </div>
          ) : (
            <textarea
              value={script}
              onChange={(e) => setScript(e.target.value)}
              rows={8}
              className="block w-full rounded-lg bg-white border border-light-300 px-4 py-3 shadow-sm text-light-900 placeholder-light-400 sm:text-sm focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500 resize-none"
              placeholder="AI-generated script will appear here..."
            />
          )}
          <p className="mt-1 text-xs text-light-500">
            This is a preview of what the AI might say. The actual conversation will be dynamic based on borrower responses.
          </p>
        </div>

        {/* Call Status */}
        {callInitiated && (
          <div className="flex items-center gap-3 p-3 rounded-lg bg-accent-50 border border-accent-200">
            <CheckCircleIcon className="h-5 w-5 text-accent-500" />
            <div>
              <p className="text-sm font-medium text-accent-700">
                AI Call Initiated
              </p>
              <p className="text-xs text-accent-600">
                The AI is now calling {borrowerName}. You can track progress in the communications section.
              </p>
            </div>
          </div>
        )}

        {/* Actions */}
        <div className="flex justify-end gap-3 pt-2">
          <Button variant="secondary" onClick={handleClose}>
            {callInitiated ? 'Close' : 'Cancel'}
          </Button>
          {!callInitiated && (
            <Button
              onClick={handleInitiateCall}
              loading={initiateCall.isPending}
              disabled={!script.trim() || scriptLoading}
            >
              <PhoneIcon className="h-5 w-5 mr-2" />
              Initiate AI Call
            </Button>
          )}
        </div>
      </div>
    </Modal>
  )
}
