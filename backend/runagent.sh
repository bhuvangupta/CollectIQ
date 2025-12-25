cd /Users/bhuvang/ofb/vasooli/collectiq && source venv/bin/activate && cd backend && \
  LIVEKIT_URL=wss://collectiq-42aqczxk.livekit.cloud \
  LIVEKIT_API_KEY=APIuykY3fgBVRdM \
  LIVEKIT_API_SECRET=erfSCklpy69xfQT7sIb3qahcRFbDVUPuRto01hpOrdHB \
  SARVAM_API_KEY=sk_b27ona9v_pCyaorEp900zGOvjw8SYag6Z \
  GROQ_API_KEY=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 \
  DEEPGRAM_API_KEY=f98fae26d38092e44999b6d70fb372ff01bb9ed7 \
  ELEVENLABS_VOICE_ID=kFCe7jyOkkYKzOgpe2u0 \
  ELEVEN_API_KEY=sk_416744c870f9aefc1dc99a77f6dfc5bccadb279111799f6b \
  python -m app.services.voice_ai.livekit_agent dev
