import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import DOMPurify from 'dompurify'
import {
  PhoneIcon,
  ChatBubbleLeftIcon,
  PlayIcon,
  FunnelIcon,
  ArrowPathIcon,
  EyeIcon,
  MagnifyingGlassIcon,
  DocumentTextIcon,
} from '@heroicons/react/24/outline'
import api from '../services/api'
import Card, { CardHeader, CardTitle } from '../components/ui/Card'
import Button from '../components/ui/Button'
import Badge from '../components/ui/Badge'
import Modal from '../components/ui/Modal'

interface TranscriptSearchResult {
  communication_id: string
  case_id: string
  case_number: string
  borrower_name: string
  channel: string
  initiated_at: string
  duration_seconds: number
  is_ai_handled: boolean
  transcript_snippet: string
  match_count: number
}

interface Communication {
  id: string
  channel: string
  direction: string
  status: string
  outcome?: string
  from_number?: string
  to_number: string
  duration_seconds?: number
  message_content?: string
  recording_url?: string
  ai_script?: string
  transcript?: string
  borrower_id?: string
  borrower_name?: string
  case_id?: string
  case_number?: string
  agent_name?: string
  is_ai_handled: boolean
  initiated_at: string
  connected_at?: string
  ended_at?: string
}

export default function Communications() {
  const [activeTab, setActiveTab] = useState<'list' | 'search'>('list')
  const [channel, setChannel] = useState<string>('')
  const [status, setStatus] = useState<string>('')
  const [page, setPage] = useState(1)
  const [selectedComm, setSelectedComm] = useState<Communication | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [searchTriggered, setSearchTriggered] = useState(false)

  const { data, isLoading, refetch } = useQuery({
    queryKey: ['communications', { channel, status, page }],
    queryFn: async () => {
      const params = new URLSearchParams()
      params.append('page', page.toString())
      params.append('page_size', '20')
      if (channel) params.append('channel', channel)
      if (status) params.append('status', status)
      const response = await api.get(`/communications?${params}`)
      return response.data
    },
  })

  // Transcript search query
  const { data: searchResults, isLoading: isSearching } = useQuery({
    queryKey: ['transcriptSearch', searchQuery],
    queryFn: async () => {
      const response = await api.get(`/analytics/transcripts/search?query=${encodeURIComponent(searchQuery)}&limit=50`)
      return response.data as { results: TranscriptSearchResult[], total: number, query: string }
    },
    enabled: searchTriggered && searchQuery.length >= 2,
  })

  const handleSearch = () => {
    if (searchQuery.length >= 2) {
      setSearchTriggered(true)
    }
  }

  const getStatusBadge = (status: string) => {
    const variants: Record<string, 'success' | 'warning' | 'danger' | 'default'> = {
      completed: 'success',
      in_progress: 'warning',
      ringing: 'warning',
      queued: 'default',
      failed: 'danger',
      no_answer: 'danger',
      busy: 'danger',
    }
    return <Badge variant={variants[status] || 'default'}>{status.replace('_', ' ')}</Badge>
  }

  const getChannelIcon = (channel: string) => {
    switch (channel) {
      case 'call':
        return <PhoneIcon className="h-5 w-5 text-primary-500" />
      case 'sms':
      case 'whatsapp':
        return <ChatBubbleLeftIcon className="h-5 w-5 text-accent-500" />
      default:
        return <PhoneIcon className="h-5 w-5 text-light-400" />
    }
  }

  const formatDuration = (seconds?: number) => {
    if (!seconds) return '-'
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  const formatTime = (dateString: string) => {
    const date = new Date(dateString)
    return date.toLocaleString('en-IN', {
      day: 'numeric',
      month: 'short',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-light-900">Communications</h1>
          <p className="mt-1 text-sm text-light-500">
            View all calls, SMS, and WhatsApp messages
          </p>
        </div>
        <Button variant="secondary" onClick={() => refetch()}>
          <ArrowPathIcon className="h-4 w-4 mr-2" />
          Refresh
        </Button>
      </div>

      {/* Tabs */}
      <div className="border-b border-light-200">
        <nav className="flex gap-4">
          <button
            onClick={() => setActiveTab('list')}
            className={`py-2 px-1 border-b-2 text-sm font-medium transition-colors ${
              activeTab === 'list'
                ? 'border-primary-500 text-primary-600'
                : 'border-transparent text-light-500 hover:text-light-700'
            }`}
          >
            <div className="flex items-center gap-2">
              <PhoneIcon className="h-4 w-4" />
              Communications
            </div>
          </button>
          <button
            onClick={() => setActiveTab('search')}
            className={`py-2 px-1 border-b-2 text-sm font-medium transition-colors ${
              activeTab === 'search'
                ? 'border-primary-500 text-primary-600'
                : 'border-transparent text-light-500 hover:text-light-700'
            }`}
          >
            <div className="flex items-center gap-2">
              <DocumentTextIcon className="h-4 w-4" />
              Transcript Search
            </div>
          </button>
        </nav>
      </div>

      {activeTab === 'search' ? (
        <>
          {/* Transcript Search */}
          <Card>
            <div className="flex gap-3">
              <div className="relative flex-1">
                <MagnifyingGlassIcon className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-light-400" />
                <input
                  type="text"
                  placeholder="Search transcripts... (e.g., payment, promise, EMI)"
                  value={searchQuery}
                  onChange={(e) => {
                    setSearchQuery(e.target.value)
                    setSearchTriggered(false)
                  }}
                  onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                  className="w-full rounded-lg border border-light-300 bg-white py-2.5 pl-10 pr-4 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                />
              </div>
              <Button onClick={handleSearch} disabled={searchQuery.length < 2}>
                <MagnifyingGlassIcon className="h-4 w-4 mr-2" />
                Search
              </Button>
            </div>
          </Card>

          {/* Search Results */}
          <Card>
            <CardHeader>
              <CardTitle>
                {searchResults?.total !== undefined
                  ? `Found ${searchResults.total} result${searchResults.total !== 1 ? 's' : ''}`
                  : 'Search Results'}
              </CardTitle>
            </CardHeader>

            {isSearching ? (
              <div className="flex items-center justify-center py-12">
                <div className="animate-spin rounded-full h-8 w-8 border-2 border-light-200 border-t-primary-500" />
              </div>
            ) : !searchTriggered ? (
              <div className="text-center py-12">
                <DocumentTextIcon className="h-12 w-12 text-light-300 mx-auto mb-3" />
                <p className="text-light-500">Enter a search term to search call transcripts</p>
                <p className="text-xs text-light-400 mt-1">Minimum 2 characters required</p>
              </div>
            ) : searchResults?.results?.length === 0 ? (
              <div className="text-center py-12">
                <p className="text-light-500">No transcripts found matching "{searchQuery}"</p>
              </div>
            ) : (
              <div className="space-y-3">
                {searchResults?.results?.map((result) => (
                  <div
                    key={result.communication_id}
                    className="p-4 rounded-lg border border-light-200 hover:border-light-300 transition-colors"
                  >
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="font-medium text-light-900">
                            {result.borrower_name}
                          </span>
                          <span className="text-xs text-light-400">•</span>
                          <Link
                            to={`/cases/${result.case_id}`}
                            className="text-xs text-primary-600 hover:text-primary-700"
                          >
                            {result.case_number}
                          </Link>
                          {result.is_ai_handled && (
                            <Badge variant="info" size="sm">AI</Badge>
                          )}
                        </div>
                        <p
                          className="text-sm text-light-600 line-clamp-2"
                          dangerouslySetInnerHTML={{
                            __html: DOMPurify.sanitize(
                              result.transcript_snippet.replace(
                                new RegExp(`(${searchQuery.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi'),
                                '<mark class="bg-yellow-200 px-0.5 rounded">$1</mark>'
                              ),
                              { ALLOWED_TAGS: ['mark'], ALLOWED_ATTR: ['class'] }
                            ),
                          }}
                        />
                        <div className="flex items-center gap-3 mt-2 text-xs text-light-400">
                          <span className="capitalize">{result.channel}</span>
                          <span>•</span>
                          <span>{formatDuration(result.duration_seconds)}</span>
                          <span>•</span>
                          <span>{formatTime(result.initiated_at)}</span>
                          <span>•</span>
                          <span>{result.match_count} match{result.match_count !== 1 ? 'es' : ''}</span>
                        </div>
                      </div>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => {
                          // Navigate to case with communication highlighted
                          window.location.href = `/cases/${result.case_id}`
                        }}
                      >
                        <EyeIcon className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Card>
        </>
      ) : (
        <>
      {/* Filters */}
      <Card>
        <div className="flex flex-wrap gap-4 items-center">
          <div className="flex items-center gap-2">
            <FunnelIcon className="h-4 w-4 text-light-400" />
            <span className="text-sm font-medium text-light-700">Filters:</span>
          </div>
          <select
            value={channel}
            onChange={(e) => setChannel(e.target.value)}
            className="rounded-lg border border-light-300 bg-white px-3 py-2 text-sm focus:border-primary-500 focus:outline-none"
          >
            <option value="">All Channels</option>
            <option value="call">Calls</option>
            <option value="sms">SMS</option>
            <option value="whatsapp">WhatsApp</option>
          </select>
          <select
            value={status}
            onChange={(e) => setStatus(e.target.value)}
            className="rounded-lg border border-light-300 bg-white px-3 py-2 text-sm focus:border-primary-500 focus:outline-none"
          >
            <option value="">All Status</option>
            <option value="completed">Completed</option>
            <option value="in_progress">In Progress</option>
            <option value="ringing">Ringing</option>
            <option value="failed">Failed</option>
            <option value="no_answer">No Answer</option>
          </select>
        </div>
      </Card>

      {/* Communications List */}
      <Card>
        <CardHeader>
          <CardTitle>Recent Communications</CardTitle>
        </CardHeader>

        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <div className="animate-spin rounded-full h-8 w-8 border-2 border-light-200 border-t-primary-500" />
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-light-200">
              <thead>
                <tr className="text-left text-xs font-medium text-light-500 uppercase tracking-wider">
                  <th className="px-4 py-3">Channel</th>
                  <th className="px-4 py-3">To</th>
                  <th className="px-4 py-3">Case</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3">Duration</th>
                  <th className="px-4 py-3">AI</th>
                  <th className="px-4 py-3">Time</th>
                  <th className="px-4 py-3">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-light-100">
                {data?.items?.map((comm: Communication) => (
                  <tr key={comm.id} className="hover:bg-light-50">
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        {getChannelIcon(comm.channel)}
                        <span className="text-sm capitalize">{comm.channel}</span>
                        <span className="text-xs text-light-400">
                          ({comm.direction})
                        </span>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <div>
                        <div className="text-sm font-medium text-light-900">
                          {comm.borrower_name || 'Unknown'}
                        </div>
                        <div className="text-xs text-light-500">{comm.to_number}</div>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      {comm.case_id ? (
                        <Link
                          to={`/cases/${comm.case_id}`}
                          className="text-sm text-primary-600 hover:text-primary-700"
                        >
                          {comm.case_number || 'View Case'}
                        </Link>
                      ) : (
                        <span className="text-sm text-light-400">-</span>
                      )}
                    </td>
                    <td className="px-4 py-3">{getStatusBadge(comm.status)}</td>
                    <td className="px-4 py-3">
                      <span className="text-sm text-light-700">
                        {formatDuration(comm.duration_seconds)}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      {comm.is_ai_handled ? (
                        <Badge variant="info">AI</Badge>
                      ) : (
                        <span className="text-sm text-light-400">Manual</span>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <span className="text-sm text-light-500">
                        {formatTime(comm.initiated_at)}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => setSelectedComm(comm)}
                          className="p-1.5 rounded-lg hover:bg-light-100 text-light-500 hover:text-primary-600"
                          title="View Details"
                        >
                          <EyeIcon className="h-4 w-4" />
                        </button>
                        {comm.recording_url && (
                          <button
                            className="p-1.5 rounded-lg hover:bg-light-100 text-light-500 hover:text-primary-600"
                            title="Play Recording"
                          >
                            <PlayIcon className="h-4 w-4" />
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
                {(!data?.items || data.items.length === 0) && (
                  <tr>
                    <td colSpan={8} className="px-4 py-12 text-center text-light-500">
                      No communications found
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination */}
        {data?.total_pages > 1 && (
          <div className="flex items-center justify-between border-t border-light-200 px-4 py-3">
            <span className="text-sm text-light-500">
              Page {page} of {data.total_pages}
            </span>
            <div className="flex gap-2">
              <Button
                variant="secondary"
                size="sm"
                disabled={page === 1}
                onClick={() => setPage((p) => p - 1)}
              >
                Previous
              </Button>
              <Button
                variant="secondary"
                size="sm"
                disabled={page === data.total_pages}
                onClick={() => setPage((p) => p + 1)}
              >
                Next
              </Button>
            </div>
          </div>
        )}
      </Card>
        </>
      )}

      {/* Communication Details Modal */}
      <Modal
        isOpen={!!selectedComm}
        onClose={() => setSelectedComm(null)}
        title="Communication Details"
        size="lg"
      >
        {selectedComm && (
          <div className="space-y-4">
            {/* Basic Info */}
            <div className="grid grid-cols-2 gap-4 p-4 rounded-lg bg-light-50 border border-light-200">
              <div>
                <p className="text-xs text-light-500">Channel</p>
                <p className="text-sm font-medium text-light-900 capitalize">
                  {selectedComm.channel} ({selectedComm.direction})
                </p>
              </div>
              <div>
                <p className="text-xs text-light-500">Status</p>
                <p className="text-sm font-medium text-light-900 capitalize">
                  {selectedComm.status.replace('_', ' ')}
                </p>
              </div>
              <div>
                <p className="text-xs text-light-500">To</p>
                <p className="text-sm font-medium text-light-900">
                  {selectedComm.borrower_name || 'Unknown'}
                </p>
                <p className="text-xs text-light-500">{selectedComm.to_number}</p>
              </div>
              <div>
                <p className="text-xs text-light-500">Duration</p>
                <p className="text-sm font-medium text-light-900">
                  {formatDuration(selectedComm.duration_seconds)}
                </p>
              </div>
              <div>
                <p className="text-xs text-light-500">Time</p>
                <p className="text-sm font-medium text-light-900">
                  {new Date(selectedComm.initiated_at).toLocaleString()}
                </p>
              </div>
              <div>
                <p className="text-xs text-light-500">Type</p>
                <p className="text-sm font-medium text-light-900">
                  {selectedComm.is_ai_handled ? 'AI Call' : 'Manual Call'}
                </p>
              </div>
            </div>

            {/* Outcome */}
            {selectedComm.outcome && (
              <div className="p-4 rounded-lg bg-light-50 border border-light-200">
                <p className="text-xs text-light-500 mb-1">Outcome</p>
                <p className="text-sm font-medium text-light-900 capitalize">
                  {selectedComm.outcome.replace(/_/g, ' ')}
                </p>
              </div>
            )}

            {/* AI Script (prepared by agent) */}
            {selectedComm.is_ai_handled && selectedComm.ai_script && (
              <div className="p-4 rounded-lg bg-primary-50 border border-primary-200">
                <p className="text-xs text-primary-600 mb-2">AI Script (Prepared)</p>
                <div className="text-sm text-light-700 whitespace-pre-wrap max-h-40 overflow-y-auto">
                  {selectedComm.ai_script}
                </div>
              </div>
            )}

            {/* Call Transcript (actual conversation) */}
            {selectedComm.transcript && (
              <div className="p-4 rounded-lg bg-light-50 border border-light-200">
                <p className="text-xs text-light-500 mb-2">Call Transcript</p>
                <div className="text-sm text-light-700 whitespace-pre-wrap max-h-60 overflow-y-auto">
                  {selectedComm.transcript}
                </div>
              </div>
            )}

            {/* Message content for SMS */}
            {selectedComm.channel === 'sms' && selectedComm.message_content && (
              <div className="p-4 rounded-lg bg-light-50 border border-light-200">
                <p className="text-xs text-light-500 mb-2">Message</p>
                <p className="text-sm text-light-700">{selectedComm.message_content}</p>
              </div>
            )}

            {/* Recording */}
            {selectedComm.recording_url && (
              <div className="p-4 rounded-lg bg-light-50 border border-light-200">
                <p className="text-xs text-light-500 mb-2">Recording</p>
                <div className="flex items-center gap-2">
                  <PlayIcon className="h-5 w-5 text-primary-500" />
                  <span className="text-sm text-light-700">
                    Recording available
                  </span>
                </div>
              </div>
            )}

            {/* Case Link */}
            {selectedComm.case_id && (
              <div className="flex justify-end">
                <Link
                  to={`/cases/${selectedComm.case_id}`}
                  className="text-sm text-primary-600 hover:text-primary-700"
                  onClick={() => setSelectedComm(null)}
                >
                  View Case →
                </Link>
              </div>
            )}
          </div>
        )}
      </Modal>
    </div>
  )
}
