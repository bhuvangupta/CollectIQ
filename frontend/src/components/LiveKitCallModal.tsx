import { useState, useEffect, useCallback } from 'react'
import { useMutation } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import {
  LiveKitRoom,
  RoomAudioRenderer,
  useRoomContext,
  useTracks,
  useConnectionState,
  useParticipants,
} from '@livekit/components-react'
import { ConnectionState, Track } from 'livekit-client'
import {
  PhoneIcon,
  PhoneXMarkIcon,
  MicrophoneIcon,
  SpeakerWaveIcon,
  SparklesIcon,
} from '@heroicons/react/24/outline'
import Modal from './ui/Modal'
import Button from './ui/Button'
import api from '../services/api'

interface LiveKitCallModalProps {
  isOpen: boolean
  onClose: () => void
  caseId: string
  borrowerName?: string
  borrowerPhone?: string
  outstandingAmount?: number
  emiAmount?: number
  dpd?: number
  loanType?: string
}

interface CallSession {
  room_name: string
  livekit_url: string
  user_token: string
}

function CallInterface({ onEnd }: { onEnd: () => void }) {
  const room = useRoomContext()
  const connectionState = useConnectionState()
  const participants = useParticipants()
  // Track microphone for audio visualization (not currently used but available)
  useTracks([Track.Source.Microphone, Track.Source.Unknown])
  const [isMuted, setIsMuted] = useState(false)
  const [callDuration, setCallDuration] = useState(0)

  // Track call duration
  useEffect(() => {
    if (connectionState === ConnectionState.Connected) {
      const interval = setInterval(() => {
        setCallDuration((prev) => prev + 1)
      }, 1000)
      return () => clearInterval(interval)
    }
  }, [connectionState])

  const formatDuration = (seconds: number) => {
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  const toggleMute = useCallback(() => {
    const localParticipant = room.localParticipant
    if (localParticipant) {
      localParticipant.setMicrophoneEnabled(isMuted)
      setIsMuted(!isMuted)
    }
  }, [room, isMuted])

  const handleEndCall = useCallback(() => {
    room.disconnect()
    onEnd()
  }, [room, onEnd])

  // Check if AI agent is in the room
  const aiAgent = participants.find((p) => p.name?.includes('AI') || p.name?.includes('Priya'))

  return (
    <div className="space-y-6">
      {/* Connection Status */}
      <div className="text-center">
        <div className={`inline-flex items-center gap-2 px-4 py-2 rounded-full ${
          connectionState === ConnectionState.Connected
            ? 'bg-green-100 text-green-700'
            : connectionState === ConnectionState.Connecting
            ? 'bg-yellow-100 text-yellow-700'
            : 'bg-red-100 text-red-700'
        }`}>
          <span className={`h-2 w-2 rounded-full ${
            connectionState === ConnectionState.Connected
              ? 'bg-green-500 animate-pulse'
              : connectionState === ConnectionState.Connecting
              ? 'bg-yellow-500 animate-pulse'
              : 'bg-red-500'
          }`} />
          <span className="text-sm font-medium">
            {connectionState === ConnectionState.Connected
              ? 'Connected'
              : connectionState === ConnectionState.Connecting
              ? 'Connecting...'
              : 'Disconnected'}
          </span>
        </div>
      </div>

      {/* Call Duration */}
      {connectionState === ConnectionState.Connected && (
        <div className="text-center">
          <p className="text-3xl font-mono font-semibold text-gray-900">
            {formatDuration(callDuration)}
          </p>
        </div>
      )}

      {/* AI Agent Status */}
      <div className="flex justify-center">
        <div className="flex items-center gap-3 p-4 rounded-xl bg-primary-50 border border-primary-200">
          <div className="relative">
            <div className="w-16 h-16 rounded-full bg-primary-100 flex items-center justify-center">
              <SparklesIcon className="h-8 w-8 text-primary-600" />
            </div>
            {aiAgent && (
              <span className="absolute bottom-0 right-0 h-4 w-4 rounded-full bg-green-500 border-2 border-white" />
            )}
          </div>
          <div>
            <p className="font-semibold text-primary-900">Priya (AI Agent)</p>
            <p className="text-sm text-primary-600">
              {aiAgent ? 'Speaking...' : 'Waiting to join...'}
            </p>
          </div>
        </div>
      </div>

      {/* Audio Visualizer Placeholder */}
      <div className="flex justify-center items-center gap-1 h-12">
        {[...Array(12)].map((_, i) => (
          <div
            key={i}
            className={`w-1 rounded-full bg-primary-400 transition-all duration-150 ${
              connectionState === ConnectionState.Connected
                ? 'animate-pulse'
                : ''
            }`}
            style={{
              height: connectionState === ConnectionState.Connected
                ? `${Math.random() * 100}%`
                : '20%',
              animationDelay: `${i * 50}ms`,
            }}
          />
        ))}
      </div>

      {/* Controls */}
      <div className="flex justify-center gap-4">
        <button
          onClick={toggleMute}
          className={`p-4 rounded-full transition-colors ${
            isMuted
              ? 'bg-red-100 text-red-600 hover:bg-red-200'
              : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
          }`}
          title={isMuted ? 'Unmute' : 'Mute'}
        >
          <MicrophoneIcon className="h-6 w-6" />
          {isMuted && (
            <span className="absolute -top-1 -right-1 h-3 w-3 rounded-full bg-red-500" />
          )}
        </button>

        <button
          onClick={handleEndCall}
          className="p-4 rounded-full bg-red-500 text-white hover:bg-red-600 transition-colors"
          title="End Call"
        >
          <PhoneXMarkIcon className="h-6 w-6" />
        </button>

        <button
          className="p-4 rounded-full bg-gray-100 text-gray-600"
          title="Speaker"
        >
          <SpeakerWaveIcon className="h-6 w-6" />
        </button>
      </div>

      {/* Audio Renderer - Hidden but necessary for audio playback */}
      <RoomAudioRenderer />
    </div>
  )
}

export default function LiveKitCallModal({
  isOpen,
  onClose,
  caseId,
  borrowerName,
  borrowerPhone,
  outstandingAmount = 0,
  emiAmount = 0,
  dpd = 0,
  loanType = 'Personal Loan',
}: LiveKitCallModalProps) {
  const [callSession, setCallSession] = useState<CallSession | null>(null)
  const [callEnded, setCallEnded] = useState(false)

  // Start LiveKit call
  const startCall = useMutation({
    mutationFn: async () => {
      const response = await api.post('/voice/livekit/call', {
        borrower_name: borrowerName,
        phone_number: borrowerPhone,
        outstanding_amount: outstandingAmount,
        emi_amount: emiAmount,
        dpd: dpd,
        loan_type: loanType,
        case_id: caseId,
      })
      return response.data as CallSession
    },
    onSuccess: (data) => {
      setCallSession(data)
      toast.success('Connected! AI agent is joining...')
    },
    onError: (error: any) => {
      const message = error.response?.data?.detail || 'Failed to start call'
      toast.error(message)
    },
  })

  // End call
  const endCall = useMutation({
    mutationFn: async (roomName: string) => {
      const response = await api.post(`/voice/livekit/room/${roomName}/end`)
      return response.data
    },
  })

  const handleStartCall = () => {
    startCall.mutate()
  }

  const handleEndCall = async () => {
    if (callSession?.room_name) {
      await endCall.mutateAsync(callSession.room_name)
    }
    setCallEnded(true)
    setCallSession(null)
  }

  const handleClose = () => {
    if (callSession?.room_name) {
      endCall.mutate(callSession.room_name)
    }
    setCallSession(null)
    setCallEnded(false)
    onClose()
  }

  // Reset state when modal closes
  useEffect(() => {
    if (!isOpen) {
      setCallSession(null)
      setCallEnded(false)
    }
  }, [isOpen])

  return (
    <Modal
      isOpen={isOpen}
      onClose={handleClose}
      title="AI Voice Call"
      size="lg"
    >
      <div className="space-y-6">
        {/* Pre-call state */}
        {!callSession && !callEnded && (
          <>
            {/* Info Banner */}
            <div className="p-4 rounded-lg bg-primary-50 border border-primary-200">
              <div className="flex items-start gap-3">
                <SparklesIcon className="h-6 w-6 text-primary-600 flex-shrink-0" />
                <div>
                  <p className="font-medium text-primary-900">
                    Browser-Based AI Voice Call
                  </p>
                  <p className="text-sm text-primary-700 mt-1">
                    Have a real-time voice conversation with our AI collection agent (Priya).
                    She speaks natural Hinglish and will handle the collection call professionally.
                  </p>
                </div>
              </div>
            </div>

            {/* Borrower Info */}
            <div className="p-4 rounded-lg bg-light-50 border border-light-200">
              <h4 className="font-medium text-light-900 mb-3">Borrower Details</h4>
              <dl className="grid grid-cols-2 gap-3 text-sm">
                <div>
                  <dt className="text-light-500">Name</dt>
                  <dd className="font-medium text-light-900">{borrowerName}</dd>
                </div>
                <div>
                  <dt className="text-light-500">Phone</dt>
                  <dd className="font-medium text-light-900">{borrowerPhone}</dd>
                </div>
                <div>
                  <dt className="text-light-500">Outstanding</dt>
                  <dd className="font-medium text-light-900">
                    {outstandingAmount.toLocaleString('en-IN', {
                      style: 'currency',
                      currency: 'INR',
                      maximumFractionDigits: 0,
                    })}
                  </dd>
                </div>
                <div>
                  <dt className="text-light-500">DPD</dt>
                  <dd className="font-medium text-light-900">{dpd} days</dd>
                </div>
              </dl>
            </div>

            {/* Microphone Permission Note */}
            <div className="p-3 rounded-lg bg-yellow-50 border border-yellow-200">
              <p className="text-sm text-yellow-800">
                <strong>Note:</strong> Your browser will request microphone access.
                Please allow it to have the voice conversation.
              </p>
            </div>

            {/* Actions */}
            <div className="flex justify-end gap-3">
              <Button variant="secondary" onClick={handleClose}>
                Cancel
              </Button>
              <Button
                onClick={handleStartCall}
                loading={startCall.isPending}
                disabled={startCall.isPending}
              >
                <PhoneIcon className="h-5 w-5 mr-2" />
                Start Voice Call
              </Button>
            </div>
          </>
        )}

        {/* Active call state */}
        {callSession && !callEnded && (
          <LiveKitRoom
            serverUrl={callSession.livekit_url}
            token={callSession.user_token}
            connect={true}
            audio={true}
            video={false}
          >
            <CallInterface onEnd={handleEndCall} />
          </LiveKitRoom>
        )}

        {/* Call ended state */}
        {callEnded && (
          <div className="text-center py-8">
            <div className="w-16 h-16 rounded-full bg-green-100 flex items-center justify-center mx-auto mb-4">
              <PhoneXMarkIcon className="h-8 w-8 text-green-600" />
            </div>
            <h3 className="text-lg font-semibold text-gray-900 mb-2">
              Call Ended
            </h3>
            <p className="text-gray-600 mb-6">
              The call transcript and summary will be available in the communications tab.
            </p>
            <Button onClick={handleClose}>
              Close
            </Button>
          </div>
        )}
      </div>
    </Modal>
  )
}
