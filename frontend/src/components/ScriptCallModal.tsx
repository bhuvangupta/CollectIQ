import { useState, useEffect } from 'react'
import { useMutation } from '@tanstack/react-query'
import {
  DocumentTextIcon,
  PhoneIcon,
  ArrowPathIcon,
  CheckCircleIcon,
  ClipboardDocumentIcon,
} from '@heroicons/react/24/outline'
import Modal from './ui/Modal'
import Button from './ui/Button'
import api from '../services/api'
import toast from 'react-hot-toast'

interface ScriptCallModalProps {
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

export default function ScriptCallModal({
  isOpen,
  onClose,
  caseId,
  borrowerId,
  loanId,
  borrowerName,
  borrowerPhone,
  preferredLanguage = 'en',
}: ScriptCallModalProps) {
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

  // Reset state when modal closes
  useEffect(() => {
    if (!isOpen) {
      setCallInitiated(false)
      setScriptData(null)
      setScript('')
    } else {
      setLanguage(preferredLanguage)
    }
  }, [isOpen, preferredLanguage])

  const handleRegenerate = () => {
    generateScript.mutate(language)
  }

  const handleCopyScript = () => {
    navigator.clipboard.writeText(script)
    toast.success('Script copied to clipboard')
  }

  const scriptLoading = generateScript.isPending

  // Initiate manual call with script (NOT using Bolna AI)
  const initiateCall = useMutation({
    mutationFn: async () => {
      const response = await api.post('/communications/call', {
        borrower_id: borrowerId,
        case_id: caseId,
        loan_id: loanId,
        use_ai: false,  // Manual call, not AI
        script,  // Script is saved for reference
        language,
      })
      return response.data
    },
    onSuccess: () => {
      setCallInitiated(true)
      toast.success('Call initiated - use the script as your guide')
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to initiate call')
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
    <Modal isOpen={isOpen} onClose={handleClose} title="Script Call" size="lg">
      <div className="space-y-4">
        {/* Info Banner */}
        <div className="p-3 rounded-lg bg-amber-50 border border-amber-200">
          <p className="text-sm text-amber-700">
            <strong>Script Call:</strong> AI generates a script for you to follow.
            You'll make the call manually using this script as a guide.
          </p>
        </div>

        {/* Recipient Info */}
        <div className="flex items-center justify-between p-3 rounded-lg bg-light-50 border border-light-200">
          <div>
            <p className="text-sm font-medium text-light-900">{borrowerName}</p>
            <p className="text-sm text-light-500">{borrowerPhone}</p>
          </div>
          <div className="flex items-center gap-2">
            <DocumentTextIcon className="h-5 w-5 text-amber-500" />
            <span className="text-sm font-medium text-amber-600">Script Call</span>
          </div>
        </div>

        {/* Language Selector */}
        <div className="flex items-center gap-3">
          <label className="text-sm font-medium text-light-700">Language:</label>
          <div className="flex gap-2">
            {[
              { value: 'en', label: 'English' },
              { value: 'hinglish', label: 'Hinglish' },
              { value: 'hi', label: 'Hindi' },
            ].map((lang) => (
              <button
                key={lang.value}
                type="button"
                className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                  language === lang.value
                    ? 'bg-amber-100 text-amber-700 border border-amber-300'
                    : 'bg-light-100 text-light-600 border border-light-200 hover:bg-light-200'
                }`}
                onClick={() => setLanguage(lang.value)}
              >
                {lang.label} {preferredLanguage === lang.value && '★'}
              </button>
            ))}
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
              Your Call Script
            </label>
            <div className="flex gap-2">
              <Button
                variant="ghost"
                size="sm"
                onClick={handleCopyScript}
                disabled={!script.trim()}
              >
                <ClipboardDocumentIcon className="h-4 w-4 mr-1" />
                Copy
              </Button>
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
          </div>
          {scriptLoading ? (
            <div className="flex items-center justify-center h-48 rounded-lg border border-light-200 bg-light-50">
              <div className="text-center">
                <ArrowPathIcon className="h-8 w-8 text-amber-500 animate-spin mx-auto" />
                <p className="mt-2 text-sm text-light-500">Generating script...</p>
              </div>
            </div>
          ) : (
            <textarea
              value={script}
              onChange={(e) => setScript(e.target.value)}
              rows={10}
              className="block w-full rounded-lg bg-white border border-light-300 px-4 py-3 shadow-sm text-light-900 placeholder-light-400 sm:text-sm focus:outline-none focus:ring-2 focus:ring-amber-500/20 focus:border-amber-500 resize-none font-mono"
              placeholder="AI-generated script will appear here..."
            />
          )}
          <p className="mt-1 text-xs text-light-500">
            Edit the script as needed. This will be saved with the call record for reference.
          </p>
        </div>

        {/* Call Status */}
        {callInitiated && (
          <div className="flex items-center gap-3 p-3 rounded-lg bg-green-50 border border-green-200">
            <CheckCircleIcon className="h-5 w-5 text-green-500" />
            <div>
              <p className="text-sm font-medium text-green-700">
                Call Initiated
              </p>
              <p className="text-xs text-green-600">
                Use the script above as your guide. The script is saved in the call record.
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
              className="bg-amber-600 hover:bg-amber-700"
            >
              <PhoneIcon className="h-5 w-5 mr-2" />
              Start Call with Script
            </Button>
          )}
        </div>
      </div>
    </Modal>
  )
}
