import { useState, useRef, useCallback, useEffect } from 'react'
import {
  MicrophoneIcon,
  StopIcon,
  SpeakerWaveIcon,
  PhoneXMarkIcon,
  PhoneIcon,
  SignalIcon,
  ClockIcon,
} from '@heroicons/react/24/outline'
import Card from '../components/ui/Card'
import Button from '../components/ui/Button'

interface TranscriptItem {
  role: 'user' | 'assistant'
  text: string
  timestamp: Date
}

interface BorrowerContext {
  borrower_name: string
  outstanding_amount: number
  emi_amount: number
  dpd: number
  loan_type: string
}

const DEFAULT_CONTEXT: BorrowerContext = {
  borrower_name: 'Vivek',
  outstanding_amount: 50000,
  emi_amount: 5000,
  dpd: 30,
  loan_type: 'Personal Loan',
}

// Audio waveform component
function AudioWaveform({ audioLevel, isActive }: { audioLevel: number; isActive: boolean }) {
  const bars = 5
  return (
    <div className="flex items-center justify-center gap-1 h-8">
      {Array.from({ length: bars }).map((_, i) => {
        const barLevel = isActive ? Math.min(1, audioLevel * (1 + Math.random() * 0.5)) : 0
        const height = Math.max(4, barLevel * 32)
        return (
          <div
            key={i}
            className={`w-1 rounded-full transition-all duration-75 ${
              isActive ? 'bg-primary-500' : 'bg-light-300'
            }`}
            style={{ height: `${height}px` }}
          />
        )
      })}
    </div>
  )
}

// Call timer component
function CallTimer({ startTime }: { startTime: Date | null }) {
  const [elapsed, setElapsed] = useState(0)

  useEffect(() => {
    if (!startTime) {
      setElapsed(0)
      return
    }

    const interval = setInterval(() => {
      setElapsed(Math.floor((Date.now() - startTime.getTime()) / 1000))
    }, 1000)

    return () => clearInterval(interval)
  }, [startTime])

  const minutes = Math.floor(elapsed / 60)
  const seconds = elapsed % 60

  return (
    <div className="flex items-center gap-1 text-light-600">
      <ClockIcon className="h-4 w-4" />
      <span className="text-sm font-mono">
        {String(minutes).padStart(2, '0')}:{String(seconds).padStart(2, '0')}
      </span>
    </div>
  )
}

// Connection quality indicator
function ConnectionQuality({ latency }: { latency: number }) {
  const getQuality = () => {
    if (latency < 100) return { level: 3, label: 'Excellent', color: 'text-green-500' }
    if (latency < 300) return { level: 2, label: 'Good', color: 'text-yellow-500' }
    return { level: 1, label: 'Poor', color: 'text-red-500' }
  }

  const quality = getQuality()

  return (
    <div className={`flex items-center gap-1 ${quality.color}`}>
      <SignalIcon className="h-4 w-4" />
      <div className="flex gap-0.5">
        {[1, 2, 3].map((level) => (
          <div
            key={level}
            className={`w-1 rounded-sm ${
              level <= quality.level ? 'bg-current' : 'bg-light-300'
            }`}
            style={{ height: `${level * 4}px` }}
          />
        ))}
      </div>
      <span className="text-xs">{latency}ms</span>
    </div>
  )
}

export default function VoiceDemo() {
  const [isConnected, setIsConnected] = useState(false)
  const [isConnecting, setIsConnecting] = useState(false)
  const [isRecording, setIsRecording] = useState(false)
  const [isAiSpeaking, setIsAiSpeaking] = useState(false)
  const [isProcessing, setIsProcessing] = useState(false)
  const [status, setStatus] = useState<string>('Disconnected')
  const [transcript, setTranscript] = useState<TranscriptItem[]>([])
  const [context, setContext] = useState<BorrowerContext>(DEFAULT_CONTEXT)

  // New state for UI enhancements
  const [callStartTime, setCallStartTime] = useState<Date | null>(null)
  const [audioLevel, setAudioLevel] = useState(0)
  const [latency, setLatency] = useState(0)

  const wsRef = useRef<WebSocket | null>(null)
  const audioContextRef = useRef<AudioContext | null>(null)
  const mediaStreamRef = useRef<MediaStream | null>(null)
  const processorRef = useRef<ScriptProcessorNode | null>(null)
  const audioChunksRef = useRef<ArrayBuffer[]>([])  // Accumulate chunks for one message
  const isPlayingRef = useRef(false)
  const audioElementRef = useRef<HTMLAudioElement | null>(null)
  const analyserRef = useRef<AnalyserNode | null>(null)
  const animationFrameRef = useRef<number | null>(null)
  const lastPingRef = useRef<number>(0)

  // Stop all audio playback
  const stopAudioPlayback = useCallback(() => {
    // Stop audio element
    if (audioElementRef.current) {
      audioElementRef.current.pause()
      audioElementRef.current.src = ''
      audioElementRef.current = null
    }
    // Clear accumulated chunks
    audioChunksRef.current = []
    isPlayingRef.current = false
    setIsAiSpeaking(false)
  }, [])

  // Play accumulated audio chunks as MP3
  const playAccumulatedAudio = useCallback(() => {
    if (audioChunksRef.current.length === 0) return

    // Combine all chunks into a single blob
    const blob = new Blob(audioChunksRef.current, { type: 'audio/mpeg' })
    audioChunksRef.current = []

    const url = URL.createObjectURL(blob)
    const audio = new Audio(url)
    audioElementRef.current = audio

    audio.onended = () => {
      URL.revokeObjectURL(url)
      audioElementRef.current = null
      isPlayingRef.current = false
      setIsAiSpeaking(false)
    }

    audio.onerror = (err) => {
      console.error('Audio playback error:', err)
      URL.revokeObjectURL(url)
      audioElementRef.current = null
      isPlayingRef.current = false
      setIsAiSpeaking(false)
    }

    isPlayingRef.current = true
    audio.play().catch(err => {
      console.error('Error starting audio:', err)
      isPlayingRef.current = false
      setIsAiSpeaking(false)
    })
  }, [])

  // Handle incoming WebSocket messages
  const handleMessage = useCallback(async (event: MessageEvent) => {
    if (event.data instanceof Blob) {
      // Audio data from AI - accumulate chunks
      const arrayBuffer = await event.data.arrayBuffer()
      audioChunksRef.current.push(arrayBuffer)
      setIsAiSpeaking(true)
    } else {
      // JSON message
      try {
        const msg = JSON.parse(event.data)

        switch (msg.type) {
          case 'greeting_complete':
            // Play accumulated greeting audio
            playAccumulatedAudio()
            setStatus('Ready - Hold mic button to speak')
            break

          case 'processing':
            setIsProcessing(true)
            setStatus('AI is thinking...')
            break

          case 'transcript':
            setTranscript(prev => [...prev, {
              role: msg.role,
              text: msg.text,
              timestamp: new Date()
            }])
            break

          case 'response_complete':
            // Play accumulated response audio
            playAccumulatedAudio()
            setIsProcessing(false)
            setStatus('Ready - Hold mic button to speak')
            break

          case 'session_ended':
            setStatus('Call ended')
            disconnect()
            break

          case 'error':
            console.error('Server error:', msg.message)
            setStatus(`Error: ${msg.message}`)
            break

          case 'context_updated':
            setStatus('Context updated')
            break

          case 'interrupted':
            // AI speech was interrupted by user
            stopAudioPlayback()
            setStatus('Listening...')
            break

          case 'pong':
            // Calculate latency
            if (lastPingRef.current > 0) {
              setLatency(Date.now() - lastPingRef.current)
            }
            break
        }
      } catch (err) {
        console.error('Error parsing message:', err)
      }
    }
  }, [playAccumulatedAudio, stopAudioPlayback])

  // Connect to WebSocket
  const connect = useCallback(async () => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return

    setIsConnecting(true)
    setStatus('Connecting...')

    try {
      const sessionId = crypto.randomUUID()
      const aiEngineUrl = import.meta.env.VITE_AI_ENGINE_WS_URL || 'ws://localhost:8001'
      const ws = new WebSocket(`${aiEngineUrl}/ws/voice/${sessionId}`)

      ws.onopen = () => {
        setIsConnected(true)
        setIsConnecting(false)
        setCallStartTime(new Date())
        setStatus('Connected - AI is greeting...')
        setIsAiSpeaking(true)

        // Send initial context
        ws.send(JSON.stringify({
          type: 'update_context',
          context: {
            borrower_name: context.borrower_name,
            outstanding_amount: context.outstanding_amount,
            emi_amount: context.emi_amount,
            dpd: context.dpd,
            loan_type: context.loan_type,
            language: 'hi'
          }
        }))

        // Start latency ping
        const pingInterval = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            lastPingRef.current = Date.now()
            ws.send(JSON.stringify({ type: 'ping' }))
          }
        }, 5000)

        // Store interval for cleanup
        ;(ws as any)._pingInterval = pingInterval
      }

      ws.onmessage = handleMessage

      ws.onclose = () => {
        // Clear ping interval
        if ((ws as any)._pingInterval) {
          clearInterval((ws as any)._pingInterval)
        }
        setIsConnected(false)
        setIsRecording(false)
        setIsAiSpeaking(false)
        setCallStartTime(null)
        setStatus('Disconnected')
        stopRecording()
      }

      ws.onerror = (error) => {
        console.error('WebSocket error:', error)
        setStatus('Connection error')
        setIsConnecting(false)
      }

      wsRef.current = ws
    } catch (err) {
      console.error('Error connecting:', err)
      setStatus('Failed to connect')
      setIsConnecting(false)
    }
  }, [context, handleMessage])

  // Disconnect from WebSocket
  const disconnect = useCallback(() => {
    stopRecording()

    if (wsRef.current) {
      if (wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({ type: 'end_session' }))
      }
      wsRef.current.close()
      wsRef.current = null
    }

    setIsConnected(false)
    setIsAiSpeaking(false)
    setStatus('Disconnected')
  }, [])

  // Start recording audio
  const startRecording = useCallback(async () => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return
    if (isProcessing) return

    // If AI is speaking, interrupt it
    if (isAiSpeaking) {
      wsRef.current.send(JSON.stringify({ type: 'interrupt' }))
      stopAudioPlayback()
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          sampleRate: 16000,
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        }
      })

      mediaStreamRef.current = stream

      // Create audio context at 16kHz
      const audioContext = new AudioContext({ sampleRate: 16000 })
      audioContextRef.current = audioContext

      const source = audioContext.createMediaStreamSource(stream)
      const processor = audioContext.createScriptProcessor(4096, 1, 1)

      // Create analyser for audio level visualization
      const analyser = audioContext.createAnalyser()
      analyser.fftSize = 256
      source.connect(analyser)
      analyserRef.current = analyser

      // Start audio level monitoring
      const updateAudioLevel = () => {
        if (!analyserRef.current) return

        const dataArray = new Uint8Array(analyser.frequencyBinCount)
        analyser.getByteFrequencyData(dataArray)

        // Calculate average level
        const average = dataArray.reduce((sum, val) => sum + val, 0) / dataArray.length
        setAudioLevel(average / 255)

        animationFrameRef.current = requestAnimationFrame(updateAudioLevel)
      }
      updateAudioLevel()

      processor.onaudioprocess = (e) => {
        if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return

        const inputData = e.inputBuffer.getChannelData(0)

        // Convert Float32Array to Int16Array
        const int16 = new Int16Array(inputData.length)
        for (let i = 0; i < inputData.length; i++) {
          const s = Math.max(-1, Math.min(1, inputData[i]))
          int16[i] = s < 0 ? s * 0x8000 : s * 0x7FFF
        }

        wsRef.current.send(int16.buffer)
      }

      source.connect(processor)
      processor.connect(audioContext.destination)
      processorRef.current = processor

      setIsRecording(true)
      setStatus('Listening...')
    } catch (err) {
      console.error('Error accessing microphone:', err)
      setStatus('Microphone access denied')
    }
  }, [isAiSpeaking, isProcessing, stopAudioPlayback])

  // Stop recording audio
  const stopRecording = useCallback(() => {
    // Stop audio level animation
    if (animationFrameRef.current) {
      cancelAnimationFrame(animationFrameRef.current)
      animationFrameRef.current = null
    }

    // Disconnect analyser
    if (analyserRef.current) {
      analyserRef.current = null
    }

    if (processorRef.current) {
      processorRef.current.disconnect()
      processorRef.current = null
    }

    if (mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach(track => track.stop())
      mediaStreamRef.current = null
    }

    setIsRecording(false)
    setAudioLevel(0)
    if (isConnected) {
      setStatus('Processing...')
    }
  }, [isConnected])

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      disconnect()
      if (audioContextRef.current) {
        audioContextRef.current.close()
      }
    }
  }, [disconnect])

  // Handle AI speaking state based on audio playback
  useEffect(() => {
    if (audioChunksRef.current.length === 0 && !isPlayingRef.current) {
      setIsAiSpeaking(false)
    }
  }, [transcript])

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl sm:text-2xl font-bold text-light-900">AI Voice Demo</h1>
        <p className="mt-1 text-xs sm:text-sm text-light-500">
          Test real-time AI voice conversations with Priya
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main Call Interface */}
        <div className="lg:col-span-2">
          <Card>
            {/* Status Bar */}
            <div className="flex items-center justify-between mb-6">
              <div className="flex items-center gap-3">
                <div className={`w-3 h-3 rounded-full ${
                  isConnected ? 'bg-green-500 animate-pulse' : 'bg-red-500'
                }`} />
                <span className="text-sm text-light-600">{status}</span>
                {isConnected && <CallTimer startTime={callStartTime} />}
              </div>
              <div className="flex items-center gap-4">
                {isConnected && <ConnectionQuality latency={latency || 50} />}
                {isConnected && (
                  <span className="text-xs text-light-400">
                    {context.borrower_name}
                  </span>
                )}
              </div>
            </div>

            {/* Call Controls */}
            <div className="flex flex-col items-center justify-center py-8">
              {!isConnected ? (
                <Button
                  onClick={connect}
                  loading={isConnecting}
                  size="lg"
                  className="px-8"
                >
                  <PhoneIcon className="h-5 w-5 mr-2" />
                  Start Demo Call
                </Button>
              ) : (
                <div className="flex flex-col items-center gap-6">
                  {/* AI Speaking Indicator */}
                  {isAiSpeaking && (
                    <div className="flex items-center gap-2 text-primary-600">
                      <SpeakerWaveIcon className="h-5 w-5 animate-pulse" />
                      <span className="text-sm font-medium">Priya is speaking...</span>
                    </div>
                  )}

                  {/* Processing Indicator */}
                  {isProcessing && !isAiSpeaking && (
                    <div className="flex items-center gap-2 text-amber-600">
                      <div className="animate-spin rounded-full h-4 w-4 border-2 border-amber-200 border-t-amber-600" />
                      <span className="text-sm">Processing...</span>
                    </div>
                  )}

                  {/* Audio Waveform */}
                  <div className="h-8 w-32 mb-2">
                    <AudioWaveform audioLevel={audioLevel} isActive={isRecording} />
                  </div>

                  {/* Mic Button */}
                  <button
                    onMouseDown={startRecording}
                    onMouseUp={stopRecording}
                    onMouseLeave={stopRecording}
                    onTouchStart={startRecording}
                    onTouchEnd={stopRecording}
                    disabled={isProcessing}
                    className={`p-6 rounded-full transition-all duration-200 ${
                      isRecording
                        ? 'bg-red-500 text-white scale-110 shadow-lg shadow-red-500/30'
                        : isProcessing
                        ? 'bg-light-200 text-light-400 cursor-not-allowed'
                        : isAiSpeaking
                        ? 'bg-amber-100 text-amber-600 hover:bg-amber-200 hover:scale-105 ring-2 ring-amber-300'
                        : 'bg-primary-100 text-primary-600 hover:bg-primary-200 hover:scale-105'
                    }`}
                  >
                    {isRecording ? (
                      <StopIcon className="h-10 w-10" />
                    ) : (
                      <MicrophoneIcon className="h-10 w-10" />
                    )}
                  </button>

                  <p className="text-sm text-light-500">
                    {isRecording
                      ? 'Release to send'
                      : isAiSpeaking
                      ? 'Hold to interrupt'
                      : 'Hold to speak'}
                  </p>

                  {/* End Call Button */}
                  <Button
                    variant="secondary"
                    onClick={disconnect}
                    className="mt-4"
                  >
                    <PhoneXMarkIcon className="h-4 w-4 mr-2" />
                    End Call
                  </Button>
                </div>
              )}
            </div>

            {/* Transcript */}
            <div className="mt-6 border-t border-light-200 pt-4">
              <h3 className="text-sm font-medium text-light-700 mb-3">Conversation</h3>
              <div className="bg-light-50 rounded-lg p-4 max-h-64 overflow-y-auto space-y-3">
                {transcript.length === 0 ? (
                  <p className="text-light-400 text-sm italic text-center">
                    Conversation will appear here...
                  </p>
                ) : (
                  transcript.map((item, idx) => (
                    <div
                      key={idx}
                      className={`flex ${item.role === 'user' ? 'justify-end' : 'justify-start'}`}
                    >
                      <div
                        className={`max-w-[80%] rounded-lg px-4 py-2 ${
                          item.role === 'user'
                            ? 'bg-primary-100 text-primary-800'
                            : 'bg-white border border-light-200 text-light-800'
                        }`}
                      >
                        <p className="text-xs font-medium mb-1 opacity-70">
                          {item.role === 'user' ? 'You' : 'Priya'}
                        </p>
                        <p className="text-sm">{item.text}</p>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          </Card>
        </div>

        {/* Context Settings */}
        <div>
          <Card>
            <h3 className="text-sm font-medium text-light-700 mb-4">Demo Context</h3>
            <div className="space-y-4">
              <div>
                <label className="block text-xs text-light-500 mb-1">Borrower Name</label>
                <input
                  type="text"
                  value={context.borrower_name}
                  onChange={(e) => setContext(prev => ({ ...prev, borrower_name: e.target.value }))}
                  disabled={isConnected}
                  className="w-full rounded-lg border border-light-300 px-3 py-2 text-sm disabled:bg-light-100"
                />
              </div>
              <div>
                <label className="block text-xs text-light-500 mb-1">Outstanding Amount</label>
                <input
                  type="number"
                  value={context.outstanding_amount}
                  onChange={(e) => setContext(prev => ({ ...prev, outstanding_amount: Number(e.target.value) }))}
                  disabled={isConnected}
                  className="w-full rounded-lg border border-light-300 px-3 py-2 text-sm disabled:bg-light-100"
                />
              </div>
              <div>
                <label className="block text-xs text-light-500 mb-1">EMI Amount</label>
                <input
                  type="number"
                  value={context.emi_amount}
                  onChange={(e) => setContext(prev => ({ ...prev, emi_amount: Number(e.target.value) }))}
                  disabled={isConnected}
                  className="w-full rounded-lg border border-light-300 px-3 py-2 text-sm disabled:bg-light-100"
                />
              </div>
              <div>
                <label className="block text-xs text-light-500 mb-1">Days Past Due</label>
                <input
                  type="number"
                  value={context.dpd}
                  onChange={(e) => setContext(prev => ({ ...prev, dpd: Number(e.target.value) }))}
                  disabled={isConnected}
                  className="w-full rounded-lg border border-light-300 px-3 py-2 text-sm disabled:bg-light-100"
                />
              </div>
              <div>
                <label className="block text-xs text-light-500 mb-1">Loan Type</label>
                <select
                  value={context.loan_type}
                  onChange={(e) => setContext(prev => ({ ...prev, loan_type: e.target.value }))}
                  disabled={isConnected}
                  className="w-full rounded-lg border border-light-300 px-3 py-2 text-sm disabled:bg-light-100"
                >
                  <option value="Personal Loan">Personal Loan</option>
                  <option value="Home Loan">Home Loan</option>
                  <option value="Vehicle Loan">Vehicle Loan</option>
                  <option value="Business Loan">Business Loan</option>
                </select>
              </div>
            </div>

            <div className="mt-6 p-3 bg-light-50 rounded-lg">
              <h4 className="text-xs font-medium text-light-600 mb-2">Instructions</h4>
              <ul className="text-xs text-light-500 space-y-1">
                <li>1. Configure the borrower context</li>
                <li>2. Click "Start Demo Call"</li>
                <li>3. Wait for Priya's greeting</li>
                <li>4. Hold the mic button to speak</li>
                <li>5. Release to send your message</li>
              </ul>
            </div>
          </Card>
        </div>
      </div>
    </div>
  )
}
