import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import toast from 'react-hot-toast'
import {
  ArrowLeftIcon,
  PhoneIcon,
  ChatBubbleLeftIcon,
  PlayIcon,
  SparklesIcon,
  ChevronDownIcon,
  ChevronUpIcon,
  DocumentTextIcon,
  BanknotesIcon,
  CurrencyRupeeIcon,
} from '@heroicons/react/24/outline'
import { useCase, useCaseNotes, useAddCaseNote, useUpdateCase, useAssignCase } from '../hooks/useCases'
import { useInitiateCall, useSendSMS, useSendWhatsApp } from '../hooks/useCommunications'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import api from '../services/api'
import Card, { CardHeader, CardTitle } from '../components/ui/Card'
import Button from '../components/ui/Button'
import { StatusBadge, PriorityBadge, BucketBadge } from '../components/ui/Badge'
import Modal from '../components/ui/Modal'
import AICallModal from '../components/AICallModal'
import ScriptCallModal from '../components/ScriptCallModal'

export default function CaseDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [noteModalOpen, setNoteModalOpen] = useState(false)
  const [smsModalOpen, setSmsModalOpen] = useState(false)
  const [whatsappModalOpen, setWhatsappModalOpen] = useState(false)
  const [assignModalOpen, setAssignModalOpen] = useState(false)
  const [followUpModalOpen, setFollowUpModalOpen] = useState(false)
  const [aiCallModalOpen, setAiCallModalOpen] = useState(false)
  const [scriptCallModalOpen, setScriptCallModalOpen] = useState(false)
  const [paymentModalOpen, setPaymentModalOpen] = useState(false)
  const [expandedCommId, setExpandedCommId] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState<'notes' | 'payments' | 'communications'>('communications')
  const [confirmModal, setConfirmModal] = useState<{
    open: boolean
    type: 'status' | 'priority'
    value: string | number
    label: string
  }>({ open: false, type: 'status', value: '', label: '' })
  const [smsMessage, setSmsMessage] = useState('')
  const [whatsappMessage, setWhatsappMessage] = useState('')
  const [selectedSmsTemplate, setSelectedSmsTemplate] = useState('')
  const [selectedWhatsappTemplate, setSelectedWhatsappTemplate] = useState('')
  const [selectedAgent, setSelectedAgent] = useState('')
  const [followUpDate, setFollowUpDate] = useState('')
  const [paymentAmount, setPaymentAmount] = useState('')
  const [paymentDate, setPaymentDate] = useState(new Date().toISOString().split('T')[0])
  const [paymentMode, setPaymentMode] = useState('cash')
  const [transactionRef, setTransactionRef] = useState('')
  const [paymentNotes, setPaymentNotes] = useState('')

  const queryClient = useQueryClient()

  const { data: caseData, isLoading } = useCase(id!)
  const { data: notes } = useCaseNotes(id!)
  const { data: communications } = useQuery({
    queryKey: ['caseCommunications', id],
    queryFn: async () => {
      const response = await api.get(`/communications?case_id=${id}&page_size=10`)
      return response.data.items || []
    },
    enabled: !!id,
  })
  const addNote = useAddCaseNote()
  const updateCase = useUpdateCase()
  const initiateCall = useInitiateCall()
  const sendSMS = useSendSMS()
  const sendWhatsApp = useSendWhatsApp()
  const assignCase = useAssignCase()

  // Fetch payments for this case/loan
  const { data: payments } = useQuery({
    queryKey: ['casePayments', caseData?.loan_id],
    queryFn: async () => {
      const response = await api.get(`/payments?loan_id=${caseData?.loan_id}&page_size=20`)
      return response.data.items || []
    },
    enabled: !!caseData?.loan_id,
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
      queryClient.invalidateQueries({ queryKey: ['casePayments'] })
      queryClient.invalidateQueries({ queryKey: ['case', id] })
      setPaymentModalOpen(false)
      setPaymentAmount('')
      setPaymentDate(new Date().toISOString().split('T')[0])
      setPaymentMode('cash')
      setTransactionRef('')
      setPaymentNotes('')
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to record payment')
    },
  })

  // Fetch agents for assignment
  const { data: agents } = useQuery({
    queryKey: ['agents'],
    queryFn: async () => {
      const response = await api.get('/users?role=agent')
      return response.data.items || []
    },
    enabled: assignModalOpen,
  })

  // Fetch SMS templates
  const { data: smsTemplates } = useQuery({
    queryKey: ['templates', 'sms'],
    queryFn: async () => {
      const response = await api.get('/templates?channel=sms')
      return response.data
    },
    enabled: smsModalOpen,
  })

  // Fetch WhatsApp templates
  const { data: whatsappTemplates } = useQuery({
    queryKey: ['templates', 'whatsapp'],
    queryFn: async () => {
      const response = await api.get('/templates?channel=whatsapp')
      return response.data
    },
    enabled: whatsappModalOpen,
  })

  // Fill placeholders in template content
  const fillPlaceholders = (content: string) => {
    if (!caseData) return content
    const caseAny = caseData as any
    return content
      .replace(/\{name\}/g, caseData.borrower_name || '')
      .replace(/\{amount\}/g, caseData.total_outstanding ? Math.round(caseData.total_outstanding).toLocaleString() : '')
      .replace(/\{dpd\}/g, String(caseData.dpd || 0))
      .replace(/\{emi\}/g, caseAny.emi_amount ? Math.round(caseAny.emi_amount).toLocaleString() : '')
      .replace(/\{due_date\}/g, caseAny.due_date ? new Date(caseAny.due_date).toLocaleDateString() : '')
  }

  // Handle SMS template selection
  const handleSmsTemplateSelect = (templateId: string) => {
    setSelectedSmsTemplate(templateId)
    const template = smsTemplates?.find((t: any) => t.id === templateId)
    if (template) {
      setSmsMessage(fillPlaceholders(template.content))
    }
  }

  // Handle WhatsApp template selection
  const handleWhatsappTemplateSelect = (templateId: string) => {
    setSelectedWhatsappTemplate(templateId)
    const template = whatsappTemplates?.find((t: any) => t.id === templateId)
    if (template) {
      setWhatsappMessage(fillPlaceholders(template.content))
    }
  }

  const { register, handleSubmit, reset } = useForm<{ content: string }>()

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600" />
      </div>
    )
  }

  if (!caseData) {
    return <div>Case not found</div>
  }

  const onAddNote = (data: { content: string }) => {
    addNote.mutate(
      { caseId: id!, content: data.content },
      {
        onSuccess: () => {
          setNoteModalOpen(false)
          reset()
        },
      }
    )
  }

  const handleCall = () => {
    if (!caseData) return
    initiateCall.mutate({
      borrower_id: caseData.borrower_id,
      case_id: id,
      loan_id: caseData.loan_id,
    })
  }

  const handleSendSMS = () => {
    if (!caseData || !smsMessage.trim()) return
    sendSMS.mutate(
      {
        borrower_id: caseData.borrower_id,
        case_id: id,
        message: smsMessage,
      },
      {
        onSuccess: () => {
          setSmsModalOpen(false)
          setSmsMessage('')
        },
      }
    )
  }

  const handleSendWhatsApp = () => {
    if (!caseData || !whatsappMessage.trim()) return
    sendWhatsApp.mutate(
      {
        borrower_id: caseData.borrower_id,
        case_id: id,
        message: whatsappMessage,
      },
      {
        onSuccess: () => {
          setWhatsappModalOpen(false)
          setWhatsappMessage('')
        },
      }
    )
  }

  const handleAssignAgent = () => {
    if (!selectedAgent) return
    assignCase.mutate(
      { caseId: id!, agentId: selectedAgent },
      {
        onSuccess: () => {
          setAssignModalOpen(false)
          setSelectedAgent('')
        },
      }
    )
  }

  const handleScheduleFollowUp = () => {
    if (!followUpDate) return
    updateCase.mutate(
      { id: id!, data: { next_follow_up: followUpDate } },
      {
        onSuccess: () => {
          setFollowUpModalOpen(false)
          setFollowUpDate('')
          toast.success('Follow up scheduled')
        },
      }
    )
  }

  const handleRecordPayment = () => {
    if (!paymentAmount || !caseData) return
    recordPayment.mutate({
      loan_id: caseData.loan_id,
      borrower_id: caseData.borrower_id,
      amount: parseFloat(paymentAmount),
      payment_date: paymentDate,
      payment_mode: paymentMode,
      transaction_reference: transactionRef || undefined,
      notes: paymentNotes || undefined,
    })
  }

  const handleConfirmChange = () => {
    if (confirmModal.type === 'status') {
      updateCase.mutate({ id: id!, data: { status: confirmModal.value as string } })
    } else {
      updateCase.mutate({ id: id!, data: { priority: confirmModal.value as number } })
    }
    setConfirmModal({ open: false, type: 'status', value: '', label: '' })
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <button
            onClick={() => navigate('/cases')}
            className="rounded-md p-2 text-gray-400 hover:text-gray-500 hover:bg-gray-100"
          >
            <ArrowLeftIcon className="h-5 w-5" />
          </button>
          <div>
            <h1 className="text-2xl font-semibold text-gray-900">
              {caseData.case_number}
            </h1>
            <div className="flex items-center gap-2 mt-1">
              <StatusBadge status={caseData.status} />
              <PriorityBadge priority={caseData.priority} />
              {caseData.bucket && <BucketBadge bucket={caseData.bucket} />}
            </div>
          </div>
        </div>
        <div className="flex gap-2">
          <Button variant="secondary" onClick={() => setSmsModalOpen(true)}>
            <ChatBubbleLeftIcon className="h-5 w-5 mr-2" />
            SMS
          </Button>
          <Button variant="secondary" onClick={() => setWhatsappModalOpen(true)}>
            <ChatBubbleLeftIcon className="h-5 w-5 mr-2" />
            WhatsApp
          </Button>
          <Button variant="secondary" onClick={handleCall} loading={initiateCall.isPending}>
            <PhoneIcon className="h-5 w-5 mr-2" />
            Manual Call
          </Button>
          <Button variant="secondary" onClick={() => setPaymentModalOpen(true)}>
            <CurrencyRupeeIcon className="h-5 w-5 mr-2" />
            Record Payment
          </Button>
          <Button variant="secondary" onClick={() => setScriptCallModalOpen(true)}>
            <DocumentTextIcon className="h-5 w-5 mr-2" />
            Script Call
          </Button>
          <Button onClick={() => setAiCallModalOpen(true)}>
            <SparklesIcon className="h-5 w-5 mr-2" />
            AI Call
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main Info */}
        <div className="lg:col-span-2 space-y-6">
          {/* Borrower & Loan Info */}
          <Card>
            <CardHeader>
              <CardTitle>Borrower Information</CardTitle>
            </CardHeader>
            <dl className="grid grid-cols-2 gap-4">
              <div>
                <dt className="text-sm font-medium text-gray-500">Name</dt>
                <dd className="mt-1 text-sm text-gray-900">{caseData.borrower_name}</dd>
              </div>
              <div>
                <dt className="text-sm font-medium text-gray-500">Phone</dt>
                <dd className="mt-1 text-sm text-gray-900">{caseData.borrower_phone}</dd>
              </div>
              <div>
                <dt className="text-sm font-medium text-gray-500">Loan Account</dt>
                <dd className="mt-1 text-sm text-gray-900">{caseData.loan_account_number || '-'}</dd>
              </div>
              <div>
                <dt className="text-sm font-medium text-gray-500">Outstanding</dt>
                <dd className="mt-1 text-sm text-gray-900">
                  {caseData.total_outstanding
                    ? `₹${caseData.total_outstanding.toLocaleString()}`
                    : '-'}
                </dd>
              </div>
              <div>
                <dt className="text-sm font-medium text-gray-500">DPD</dt>
                <dd className="mt-1 text-sm text-gray-900">{caseData.dpd} days</dd>
              </div>
              <div>
                <dt className="text-sm font-medium text-gray-500">Assigned To</dt>
                <dd className="mt-1 text-sm text-gray-900">{caseData.assigned_agent_name || 'Unassigned'}</dd>
              </div>
            </dl>
          </Card>

          {/* Tabs for Notes, Payments, Communications */}
          <Card>
            {/* Tab Navigation */}
            <div className="border-b border-light-200">
              <nav className="flex -mb-px">
                <button
                  onClick={() => setActiveTab('communications')}
                  className={`px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
                    activeTab === 'communications'
                      ? 'border-primary-500 text-primary-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  }`}
                >
                  <div className="flex items-center gap-2">
                    <PhoneIcon className="h-4 w-4" />
                    Communications
                    {communications?.length > 0 && (
                      <span className="bg-light-100 text-light-600 text-xs px-2 py-0.5 rounded-full">
                        {communications.length}
                      </span>
                    )}
                  </div>
                </button>
                <button
                  onClick={() => setActiveTab('payments')}
                  className={`px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
                    activeTab === 'payments'
                      ? 'border-primary-500 text-primary-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  }`}
                >
                  <div className="flex items-center gap-2">
                    <BanknotesIcon className="h-4 w-4" />
                    Payments
                    {payments?.length > 0 && (
                      <span className="bg-green-100 text-green-600 text-xs px-2 py-0.5 rounded-full">
                        {payments.length}
                      </span>
                    )}
                  </div>
                </button>
                <button
                  onClick={() => setActiveTab('notes')}
                  className={`px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
                    activeTab === 'notes'
                      ? 'border-primary-500 text-primary-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  }`}
                >
                  <div className="flex items-center gap-2">
                    <DocumentTextIcon className="h-4 w-4" />
                    Notes
                    {(notes?.length ?? 0) > 0 && (
                      <span className="bg-light-100 text-light-600 text-xs px-2 py-0.5 rounded-full">
                        {notes?.length}
                      </span>
                    )}
                  </div>
                </button>
              </nav>
            </div>

            {/* Tab Content */}
            <div className="p-4">
              {/* Notes Tab */}
              {activeTab === 'notes' && (
                <div className="space-y-4">
                  <div className="flex justify-end">
                    <Button size="sm" onClick={() => setNoteModalOpen(true)}>
                      Add Note
                    </Button>
                  </div>
                  {notes?.length === 0 && (
                    <p className="text-sm text-gray-500 text-center py-8">No notes yet</p>
                  )}
                  {notes?.map((note) => (
                    <div
                      key={note.id}
                      className="border-l-4 border-gray-200 pl-4 py-2"
                    >
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-medium text-gray-900">
                          {note.author_name || 'System'}
                        </span>
                        <span className="text-xs text-gray-500">
                          {new Date(note.created_at).toLocaleString()}
                        </span>
                      </div>
                      <p className="mt-1 text-sm text-gray-600">{note.content}</p>
                    </div>
                  ))}
                </div>
              )}

              {/* Payments Tab */}
              {activeTab === 'payments' && (
                <div className="space-y-3">
                  <div className="flex justify-end">
                    <Button size="sm" onClick={() => setPaymentModalOpen(true)}>
                      <CurrencyRupeeIcon className="h-4 w-4 mr-1" />
                      Record Payment
                    </Button>
                  </div>
                  {(!payments || payments.length === 0) && (
                    <p className="text-sm text-gray-500 text-center py-8">No payments recorded yet</p>
                  )}
                  {payments?.map((payment: any) => (
                    <div
                      key={payment.id}
                      className="flex items-center justify-between p-3 rounded-lg bg-light-50 border border-light-200"
                    >
                      <div className="flex items-center gap-3">
                        <div className={`p-2 rounded-lg ${
                          payment.status === 'confirmed' ? 'bg-green-100' :
                          payment.status === 'pending' ? 'bg-yellow-100' : 'bg-red-100'
                        }`}>
                          <BanknotesIcon className={`h-4 w-4 ${
                            payment.status === 'confirmed' ? 'text-green-600' :
                            payment.status === 'pending' ? 'text-yellow-600' : 'text-red-600'
                          }`} />
                        </div>
                        <div>
                          <div className="flex items-center gap-2">
                            <span className="text-sm font-semibold text-gray-900">
                              ₹{parseFloat(payment.amount).toLocaleString()}
                            </span>
                            <span className={`text-xs px-2 py-0.5 rounded-full ${
                              payment.status === 'confirmed' ? 'bg-green-100 text-green-700' :
                              payment.status === 'pending' ? 'bg-yellow-100 text-yellow-700' :
                              'bg-red-100 text-red-700'
                            }`}>
                              {payment.status}
                            </span>
                          </div>
                          <div className="flex items-center gap-2 mt-0.5">
                            <span className="text-xs text-gray-500 capitalize">
                              {payment.payment_mode?.replace('_', ' ')}
                            </span>
                            {payment.transaction_reference && (
                              <span className="text-xs text-gray-400">
                                Ref: {payment.transaction_reference}
                              </span>
                            )}
                          </div>
                        </div>
                      </div>
                      <div className="text-right">
                        <span className="text-xs text-gray-500">
                          {new Date(payment.payment_date).toLocaleDateString()}
                        </span>
                        {payment.receipt_number && (
                          <p className="text-xs text-gray-400">{payment.receipt_number}</p>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {/* Communications Tab */}
              {activeTab === 'communications' && (
                <div className="space-y-3">
                  {(!communications || communications.length === 0) && (
                    <p className="text-sm text-gray-500 text-center py-8">No communications yet</p>
                  )}
                  {communications?.map((comm: any) => (
                    <div
                      key={comm.id}
                      className="rounded-lg bg-light-50 border border-light-200 overflow-hidden"
                    >
                      <div
                        className="flex items-start gap-3 p-3 cursor-pointer hover:bg-light-100"
                        onClick={() => setExpandedCommId(expandedCommId === comm.id ? null : comm.id)}
                      >
                        <div className={`p-2 rounded-lg ${
                          comm.channel === 'call' ? 'bg-primary-100' : 'bg-accent-100'
                        }`}>
                          {comm.channel === 'call' ? (
                            <PhoneIcon className="h-4 w-4 text-primary-600" />
                          ) : (
                            <ChatBubbleLeftIcon className="h-4 w-4 text-accent-600" />
                          )}
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center justify-between">
                            <span className="text-sm font-medium text-light-900 capitalize">
                              {comm.channel} ({comm.direction})
                            </span>
                            <span className="text-xs text-light-500">
                              {new Date(comm.initiated_at).toLocaleString()}
                            </span>
                          </div>
                          <div className="flex items-center gap-2 mt-1">
                            <span className={`text-xs px-2 py-0.5 rounded-full ${
                              comm.status === 'completed' ? 'bg-accent-100 text-accent-700' :
                              comm.status === 'failed' || comm.status === 'no_answer' ? 'bg-red-100 text-red-700' :
                              'bg-light-100 text-light-600'
                            }`}>
                              {comm.status.replace('_', ' ')}
                            </span>
                            {comm.duration_seconds > 0 && (
                              <span className="text-xs text-light-500">
                                {Math.floor(comm.duration_seconds / 60)}:{(comm.duration_seconds % 60).toString().padStart(2, '0')}
                              </span>
                            )}
                            {comm.is_ai_handled && (
                              <span className="text-xs px-2 py-0.5 rounded-full bg-primary-100 text-primary-700">
                                AI
                              </span>
                            )}
                          </div>
                          {comm.outcome && (
                            <p className="text-xs text-light-500 mt-1">
                              Outcome: {comm.outcome.replace('_', ' ')}
                            </p>
                          )}
                        </div>
                        <div className="flex items-center gap-1">
                          {comm.recording_url && (
                            <button
                              className="p-1.5 rounded-lg hover:bg-light-200 text-light-500 hover:text-primary-600"
                              title="Play Recording"
                              onClick={(e) => e.stopPropagation()}
                            >
                              <PlayIcon className="h-4 w-4" />
                            </button>
                          )}
                          {expandedCommId === comm.id ? (
                            <ChevronUpIcon className="h-4 w-4 text-light-400" />
                          ) : (
                            <ChevronDownIcon className="h-4 w-4 text-light-400" />
                          )}
                        </div>
                      </div>
                      {/* Expanded Details */}
                      {expandedCommId === comm.id && (
                        <div className="border-t border-light-200 p-3 space-y-3 bg-white">
                          {/* AI Script */}
                          {comm.is_ai_handled && comm.ai_script && (
                            <div className="p-3 rounded-lg bg-primary-50 border border-primary-100">
                              <p className="text-xs font-medium text-primary-600 mb-1">AI Script (Prepared)</p>
                              <p className="text-sm text-light-700 whitespace-pre-wrap">{comm.ai_script}</p>
                            </div>
                          )}
                          {/* Transcript */}
                          {comm.transcript && (
                            <div className="p-3 rounded-lg bg-light-100 border border-light-200">
                              <p className="text-xs font-medium text-light-600 mb-1">Call Transcript</p>
                              <p className="text-sm text-light-700 whitespace-pre-wrap">{comm.transcript}</p>
                            </div>
                          )}
                          {/* No details message */}
                          {!comm.ai_script && !comm.transcript && (
                            <p className="text-sm text-light-400 italic">No script or transcript available</p>
                          )}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </Card>
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Quick Stats */}
          <Card>
            <CardHeader>
              <CardTitle>Activity</CardTitle>
            </CardHeader>
            <dl className="space-y-3">
              <div className="flex justify-between">
                <dt className="text-sm text-gray-500">Total Attempts</dt>
                <dd className="text-sm font-medium text-gray-900">{caseData.total_attempts}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-sm text-gray-500">Successful Contacts</dt>
                <dd className="text-sm font-medium text-gray-900">{caseData.successful_contacts}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-sm text-gray-500">Last Contact</dt>
                <dd className="text-sm font-medium text-gray-900">
                  {caseData.last_contact_date
                    ? new Date(caseData.last_contact_date).toLocaleDateString()
                    : 'Never'}
                </dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-sm text-gray-500">Next Follow Up</dt>
                <dd className="text-sm font-medium text-gray-900">
                  {caseData.next_follow_up
                    ? new Date(caseData.next_follow_up).toLocaleDateString()
                    : 'Not set'}
                </dd>
              </div>
            </dl>
          </Card>

          {/* Actions */}
          <Card>
            <CardHeader>
              <CardTitle>Actions</CardTitle>
            </CardHeader>
            <div className="space-y-4">
              {/* Case Status */}
              <div>
                <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
                  Status
                </label>
                <div className="flex flex-wrap gap-1.5">
                  {[
                    { value: 'open', label: 'Open', color: 'bg-blue-100 text-blue-700 border-blue-200 hover:bg-blue-200' },
                    { value: 'in_progress', label: 'In Progress', color: 'bg-amber-100 text-amber-700 border-amber-200 hover:bg-amber-200' },
                    { value: 'promise_to_pay', label: 'PTP', color: 'bg-purple-100 text-purple-700 border-purple-200 hover:bg-purple-200' },
                    { value: 'resolved', label: 'Resolved', color: 'bg-green-100 text-green-700 border-green-200 hover:bg-green-200' },
                    { value: 'escalated', label: 'Escalated', color: 'bg-red-100 text-red-700 border-red-200 hover:bg-red-200' },
                    { value: 'closed', label: 'Closed', color: 'bg-gray-100 text-gray-700 border-gray-200 hover:bg-gray-200' },
                  ].map((status) => (
                    <button
                      key={status.value}
                      onClick={() => {
                        if (caseData.status !== status.value) {
                          setConfirmModal({ open: true, type: 'status', value: status.value, label: status.label })
                        }
                      }}
                      className={`px-2.5 py-1 text-xs font-medium rounded-full border transition-all ${
                        caseData.status === status.value
                          ? `${status.color} ring-2 ring-offset-1 ring-primary-500`
                          : 'bg-gray-50 text-gray-500 border-gray-200 hover:bg-gray-100'
                      }`}
                    >
                      {status.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* Priority */}
              <div>
                <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
                  Priority
                </label>
                <div className="flex flex-wrap gap-1.5">
                  {[
                    { value: 5, label: 'Critical', color: 'bg-red-100 text-red-700 border-red-200 hover:bg-red-200' },
                    { value: 4, label: 'High', color: 'bg-orange-100 text-orange-700 border-orange-200 hover:bg-orange-200' },
                    { value: 3, label: 'Medium', color: 'bg-yellow-100 text-yellow-700 border-yellow-200 hover:bg-yellow-200' },
                    { value: 2, label: 'Low', color: 'bg-green-100 text-green-700 border-green-200 hover:bg-green-200' },
                    { value: 1, label: 'Lowest', color: 'bg-gray-100 text-gray-600 border-gray-200 hover:bg-gray-200' },
                  ].map((priority) => (
                    <button
                      key={priority.value}
                      onClick={() => {
                        if (caseData.priority !== priority.value) {
                          setConfirmModal({ open: true, type: 'priority', value: priority.value, label: priority.label })
                        }
                      }}
                      className={`px-2.5 py-1 text-xs font-medium rounded-full border transition-all ${
                        caseData.priority === priority.value
                          ? `${priority.color} ring-2 ring-offset-1 ring-primary-500`
                          : 'bg-gray-50 text-gray-500 border-gray-200 hover:bg-gray-100'
                      }`}
                    >
                      {priority.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* Action Buttons */}
              <div className="pt-2 border-t border-gray-100 space-y-2">
                <Button variant="secondary" className="w-full" onClick={() => setAssignModalOpen(true)}>
                  Assign Agent
                </Button>
                <Button variant="secondary" className="w-full" onClick={() => setFollowUpModalOpen(true)}>
                  Schedule Follow Up
                </Button>
              </div>
            </div>
          </Card>

          {/* AI Summary */}
          {caseData.ai_summary && (
            <Card>
              <CardHeader>
                <CardTitle>AI Summary</CardTitle>
              </CardHeader>
              <p className="text-sm text-gray-600">{caseData.ai_summary}</p>
            </Card>
          )}
        </div>
      </div>

      {/* Add Note Modal */}
      <Modal
        isOpen={noteModalOpen}
        onClose={() => setNoteModalOpen(false)}
        title="Add Note"
      >
        <form onSubmit={handleSubmit(onAddNote)} className="space-y-4">
          <textarea
            {...register('content', { required: true })}
            rows={4}
            className="block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm"
            placeholder="Enter your note..."
          />
          <div className="flex justify-end gap-2">
            <Button
              type="button"
              variant="secondary"
              onClick={() => setNoteModalOpen(false)}
            >
              Cancel
            </Button>
            <Button type="submit" loading={addNote.isPending}>
              Add Note
            </Button>
          </div>
        </form>
      </Modal>

      {/* Send SMS Modal */}
      <Modal
        isOpen={smsModalOpen}
        onClose={() => setSmsModalOpen(false)}
        title="Send SMS"
        size="lg"
      >
        <div className="space-y-4">
          <div className="p-3 rounded-lg bg-light-50 border border-light-200">
            <p className="text-sm text-light-700">
              <span className="font-medium">To:</span> {caseData?.borrower_name} ({caseData?.borrower_phone})
            </p>
          </div>

          {/* Template Selection */}
          <div className="p-3 rounded-lg bg-primary-50 border border-primary-200">
            <div className="flex items-center gap-2 mb-3">
              <DocumentTextIcon className="h-4 w-4 text-primary-600" />
              <span className="text-sm font-medium text-primary-700">Select Template</span>
            </div>
            {smsTemplates?.length === 0 ? (
              <p className="text-sm text-primary-600">No templates available. Add templates in Settings.</p>
            ) : (
              <select
                value={selectedSmsTemplate}
                onChange={(e) => handleSmsTemplateSelect(e.target.value)}
                className="block w-full rounded-lg border border-primary-200 bg-white px-3 py-2 text-sm focus:border-primary-500 focus:outline-none"
              >
                <option value="">Select a template...</option>
                {smsTemplates?.map((t: any) => (
                  <option key={t.id} value={t.id}>
                    {t.name} ({t.language === 'en' ? 'English' : t.language === 'hinglish' ? 'Hinglish' : 'Hindi'})
                  </option>
                ))}
              </select>
            )}
          </div>

          {/* Message */}
          <div>
            <label className="block text-sm font-medium text-light-700 mb-1">
              Message
            </label>
            <textarea
              rows={4}
              className="block w-full rounded-lg bg-white border border-light-300 px-4 py-2.5 shadow-sm text-light-900 placeholder-light-400 sm:text-sm focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500"
              placeholder="Select a template or enter your message..."
              value={smsMessage}
              onChange={(e) => setSmsMessage(e.target.value)}
            />
            <p className="mt-1 text-xs text-light-500">
              {smsMessage.length} characters
            </p>
          </div>

          <div className="flex justify-end gap-2">
            <Button
              type="button"
              variant="secondary"
              onClick={() => {
                setSmsModalOpen(false)
                setSmsMessage('')
                setSelectedSmsTemplate('')
              }}
            >
              Cancel
            </Button>
            <Button
              onClick={handleSendSMS}
              loading={sendSMS.isPending}
              disabled={!smsMessage.trim()}
            >
              Send SMS
            </Button>
          </div>
        </div>
      </Modal>

      {/* Send WhatsApp Modal */}
      <Modal
        isOpen={whatsappModalOpen}
        onClose={() => setWhatsappModalOpen(false)}
        title="Send WhatsApp"
        size="lg"
      >
        <div className="space-y-4">
          <div className="p-3 rounded-lg bg-light-50 border border-light-200">
            <p className="text-sm text-light-700">
              <span className="font-medium">To:</span> {caseData?.borrower_name} ({caseData?.borrower_phone})
            </p>
          </div>

          {/* Template Selection */}
          <div className="p-3 rounded-lg bg-green-50 border border-green-200">
            <div className="flex items-center gap-2 mb-3">
              <DocumentTextIcon className="h-4 w-4 text-green-600" />
              <span className="text-sm font-medium text-green-700">Select Template</span>
            </div>
            {whatsappTemplates?.length === 0 ? (
              <p className="text-sm text-green-600">No templates available. Add templates in Settings.</p>
            ) : (
              <select
                value={selectedWhatsappTemplate}
                onChange={(e) => handleWhatsappTemplateSelect(e.target.value)}
                className="block w-full rounded-lg border border-green-200 bg-white px-3 py-2 text-sm focus:border-green-500 focus:outline-none"
              >
                <option value="">Select a template...</option>
                {whatsappTemplates?.map((t: any) => (
                  <option key={t.id} value={t.id}>
                    {t.name} ({t.language === 'en' ? 'English' : t.language === 'hinglish' ? 'Hinglish' : 'Hindi'})
                  </option>
                ))}
              </select>
            )}
          </div>

          {/* Message */}
          <div>
            <label className="block text-sm font-medium text-light-700 mb-1">
              Message
            </label>
            <textarea
              rows={6}
              className="block w-full rounded-lg bg-white border border-light-300 px-4 py-2.5 shadow-sm text-light-900 placeholder-light-400 sm:text-sm focus:outline-none focus:ring-2 focus:ring-green-500/20 focus:border-green-500"
              placeholder="Select a template or enter your message..."
              value={whatsappMessage}
              onChange={(e) => setWhatsappMessage(e.target.value)}
            />
            <p className="mt-1 text-xs text-light-500">
              {whatsappMessage.length} characters
            </p>
          </div>

          <div className="flex justify-end gap-2">
            <Button
              type="button"
              variant="secondary"
              onClick={() => {
                setWhatsappModalOpen(false)
                setWhatsappMessage('')
                setSelectedWhatsappTemplate('')
              }}
            >
              Cancel
            </Button>
            <Button
              onClick={handleSendWhatsApp}
              loading={sendWhatsApp.isPending}
              disabled={!whatsappMessage.trim()}
              className="bg-green-600 hover:bg-green-700"
            >
              Send WhatsApp
            </Button>
          </div>
        </div>
      </Modal>

      {/* Assign Agent Modal */}
      <Modal
        isOpen={assignModalOpen}
        onClose={() => setAssignModalOpen(false)}
        title="Assign Agent"
      >
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-light-700 mb-1">
              Select Agent
            </label>
            <select
              className="block w-full rounded-lg bg-white border border-light-300 px-4 py-2.5 shadow-sm text-light-900 sm:text-sm focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500"
              value={selectedAgent}
              onChange={(e) => setSelectedAgent(e.target.value)}
            >
              <option value="">Select an agent...</option>
              {agents?.map((agent: any) => (
                <option key={agent.id} value={agent.id}>
                  {agent.first_name} {agent.last_name}
                </option>
              ))}
            </select>
          </div>
          <div className="flex justify-end gap-2">
            <Button
              type="button"
              variant="secondary"
              onClick={() => setAssignModalOpen(false)}
            >
              Cancel
            </Button>
            <Button onClick={handleAssignAgent} loading={assignCase.isPending}>
              Assign
            </Button>
          </div>
        </div>
      </Modal>

      {/* Schedule Follow Up Modal */}
      <Modal
        isOpen={followUpModalOpen}
        onClose={() => setFollowUpModalOpen(false)}
        title="Schedule Follow Up"
      >
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-light-700 mb-1">
              Follow Up Date & Time
            </label>
            <input
              type="datetime-local"
              className="block w-full rounded-lg bg-white border border-light-300 px-4 py-2.5 shadow-sm text-light-900 sm:text-sm focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500"
              value={followUpDate}
              onChange={(e) => setFollowUpDate(e.target.value)}
            />
          </div>
          <div className="flex justify-end gap-2">
            <Button
              type="button"
              variant="secondary"
              onClick={() => setFollowUpModalOpen(false)}
            >
              Cancel
            </Button>
            <Button onClick={handleScheduleFollowUp} loading={updateCase.isPending}>
              Schedule
            </Button>
          </div>
        </div>
      </Modal>

      {/* AI Call Modal (Bolna - Fully Automated) */}
      <AICallModal
        isOpen={aiCallModalOpen}
        onClose={() => setAiCallModalOpen(false)}
        caseId={id!}
        borrowerId={caseData?.borrower_id}
        loanId={caseData?.loan_id}
        borrowerName={caseData?.borrower_name}
        borrowerPhone={caseData?.borrower_phone}
        preferredLanguage={(caseData as any)?.borrower_preferred_language || 'en'}
      />

      {/* Script Call Modal (Agent-guided with AI script) */}
      <ScriptCallModal
        isOpen={scriptCallModalOpen}
        onClose={() => setScriptCallModalOpen(false)}
        caseId={id!}
        borrowerId={caseData?.borrower_id}
        loanId={caseData?.loan_id}
        borrowerName={caseData?.borrower_name}
        borrowerPhone={caseData?.borrower_phone}
        preferredLanguage={(caseData as any)?.borrower_preferred_language || 'en'}
      />

      {/* Confirmation Modal */}
      <Modal
        isOpen={confirmModal.open}
        onClose={() => setConfirmModal({ open: false, type: 'status', value: '', label: '' })}
        title={`Change ${confirmModal.type === 'status' ? 'Status' : 'Priority'}`}
      >
        <div className="space-y-4">
          <p className="text-sm text-gray-600">
            Are you sure you want to change the {confirmModal.type} to{' '}
            <span className="font-semibold text-gray-900">{confirmModal.label}</span>?
          </p>
          <div className="flex justify-end gap-3">
            <Button
              variant="secondary"
              onClick={() => setConfirmModal({ open: false, type: 'status', value: '', label: '' })}
            >
              Cancel
            </Button>
            <Button onClick={handleConfirmChange} loading={updateCase.isPending}>
              Confirm
            </Button>
          </div>
        </div>
      </Modal>

      {/* Record Payment Modal */}
      <Modal
        isOpen={paymentModalOpen}
        onClose={() => setPaymentModalOpen(false)}
        title="Record Payment"
        size="lg"
      >
        <div className="space-y-4">
          {/* Borrower info */}
          <div className="p-3 rounded-lg bg-light-50 border border-light-200">
            <p className="text-sm text-light-700">
              <span className="font-medium">Borrower:</span> {caseData?.borrower_name}
            </p>
            <p className="text-sm text-light-700">
              <span className="font-medium">Outstanding:</span> ₹{caseData?.total_outstanding?.toLocaleString() || '0'}
            </p>
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

          {/* Actions */}
          <div className="flex justify-end gap-2 pt-2">
            <Button
              type="button"
              variant="secondary"
              onClick={() => {
                setPaymentModalOpen(false)
                setPaymentAmount('')
                setPaymentDate(new Date().toISOString().split('T')[0])
                setPaymentMode('cash')
                setTransactionRef('')
                setPaymentNotes('')
              }}
            >
              Cancel
            </Button>
            <Button
              onClick={handleRecordPayment}
              loading={recordPayment.isPending}
              disabled={!paymentAmount || parseFloat(paymentAmount) <= 0}
            >
              <BanknotesIcon className="h-4 w-4 mr-2" />
              Record Payment
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  )
}
