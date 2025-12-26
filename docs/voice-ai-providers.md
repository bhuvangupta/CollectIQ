# Voice AI Providers

CollectIQ supports multiple Voice AI providers for automated collection calls. These providers handle the entire conversation autonomously - making real phone calls to borrowers.

## Supported Providers

| Provider | Status | Best For | Pricing |
|----------|--------|----------|---------|
| **Mock** | Default | Development/Testing | Free |
| **Bolna AI** | Production | Indian languages, turnkey solution | ₹3-7/min |
| **Sarvam AI** | Production | Indian languages, self-hosted | Per API call |
| **LiveKit** | Production | Real-time WebRTC, low latency | Per minute |

---

## Quick Start

Set the provider in your `.env` file:

```bash
# Development (default)
VOICE_AI_PROVIDER=mock

# Production options
VOICE_AI_PROVIDER=bolna    # Bolna AI
VOICE_AI_PROVIDER=sarvam   # Sarvam AI + Exotel
VOICE_AI_PROVIDER=livekit  # LiveKit + Sarvam
```

---

## Mock Provider (Development)

The mock provider simulates AI calls without making real phone calls. Use this for development and testing.

```bash
VOICE_AI_PROVIDER=mock
```

No additional configuration required. Calls will be simulated and return mock transcripts.

---

## Bolna AI Setup

[Bolna](https://www.bolna.ai) is an Indian voice AI platform optimized for Hindi, Hinglish, and regional languages. It's a turnkey solution - Bolna handles STT, LLM, TTS, and telephony.

### Features
- Hindi, Hinglish, and regional language support
- Low latency (<300ms)
- Built-in telephony (Exotel, Twilio, Plivo)
- Natural conversation with interruption handling

### 1. Create Bolna Account & Agent

1. Sign up at [app.bolna.ai](https://app.bolna.ai)
2. Create a new Agent with collection-focused prompt
3. Configure voice (recommended: Indian female)
4. Get your **API Key** and **Agent ID**

### 2. Configure Agent Prompt

In the Bolna dashboard, set up your agent with a prompt like:

```
You are Priya, a friendly female collection agent from CollectIQ Finance.

BORROWER CONTEXT:
- Name: {{borrower_name}}
- Outstanding: ₹{{outstanding_amount}}
- EMI: ₹{{emi_amount}}
- Overdue: {{dpd}} days

SPEAKING STYLE:
- Speak natural Hinglish (Hindi-English mix)
- Keep responses SHORT (1-2 sentences)
- Be polite but direct
- Use "aap" and "ji" for respect

GOAL:
Get a payment commitment or callback date.

RULES:
- NEVER threaten or be rude
- If they can't pay now, ask when they can
- Confirm any payment promises with date
```

### 3. Configure Environment

```bash
# .env
VOICE_AI_PROVIDER=bolna
BOLNA_API_KEY=bn-your-api-key
BOLNA_AGENT_ID=your-agent-id

# Optional: For webhook callbacks (production)
VOICE_AI_WEBHOOK_URL=https://your-domain.com/api/v1/voice/webhook
```

### 4. Test the Integration

1. Start the backend: `./scripts/start_backend.sh`
2. Navigate to **AI Calls** page in the frontend
3. Enter a phone number and borrower details
4. Click "Make AI Call"

> **Note**: Bolna trial accounts can only call verified phone numbers. Add your test number in Bolna dashboard.

---

## Sarvam AI Setup

[Sarvam AI](https://www.sarvam.ai) provides Indian language STT and TTS APIs. Combined with Exotel for telephony, this gives you more control over the voice AI pipeline.

### Architecture
```
Exotel (Telephony) → Sarvam STT → LLM (Groq) → Sarvam TTS → Exotel
```

### 1. Get API Keys

1. **Sarvam AI**: Sign up at [sarvam.ai](https://www.sarvam.ai) and get API key
2. **Exotel**: Sign up at [exotel.com](https://exotel.com) for telephony
3. **Groq** (optional): For fast LLM inference

### 2. Configure Environment

```bash
# .env
VOICE_AI_PROVIDER=sarvam

# Sarvam AI
SARVAM_API_KEY=your-sarvam-api-key

# Exotel (for telephony)
EXOTEL_API_KEY=your-exotel-api-key
EXOTEL_API_TOKEN=your-exotel-api-token
EXOTEL_SID=your-exotel-sid
EXOTEL_CALLER_ID=your-exotel-phone-number

# LLM (Groq recommended for speed)
GROQ_API_KEY=your-groq-api-key
```

### 3. How It Works

1. Exotel initiates outbound call
2. Audio streams to your server via WebSocket
3. Sarvam STT converts speech to text
4. Groq LLM generates response
5. Sarvam TTS converts response to speech
6. Audio sent back to caller

---

## LiveKit Setup

[LiveKit](https://livekit.io) provides real-time WebRTC infrastructure. Combined with Sarvam AI, it enables low-latency voice conversations.

### Features
- WebRTC-based (lowest latency)
- Real-time audio streaming
- Browser-based testing without phone
- Scalable infrastructure

### 1. Get API Keys

1. **LiveKit Cloud**: Sign up at [cloud.livekit.io](https://cloud.livekit.io)
2. **Sarvam AI**: For STT and TTS
3. **Groq**: For LLM inference

### 2. Configure Environment

```bash
# .env
VOICE_AI_PROVIDER=livekit

# LiveKit
LIVEKIT_URL=wss://your-project.livekit.cloud
LIVEKIT_API_KEY=your-livekit-api-key
LIVEKIT_API_SECRET=your-livekit-api-secret

# Sarvam AI (for STT/TTS)
SARVAM_API_KEY=your-sarvam-api-key

# Groq (for LLM)
GROQ_API_KEY=your-groq-api-key
```

### 3. LiveKit-Specific Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /api/v1/voice/livekit/status` | Check LiveKit availability |
| `POST /api/v1/voice/livekit/call` | Start LiveKit voice call |
| `POST /api/v1/voice/livekit/room/{room}/token` | Get room access token |
| `POST /api/v1/voice/livekit/room/{room}/end` | End LiveKit call |

---

## Switching Providers

Simply change the `VOICE_AI_PROVIDER` environment variable and restart:

```bash
# Development
VOICE_AI_PROVIDER=mock

# Production - Turnkey solution
VOICE_AI_PROVIDER=bolna

# Production - More control
VOICE_AI_PROVIDER=sarvam

# Production - WebRTC/Low latency
VOICE_AI_PROVIDER=livekit
```

All providers (except LiveKit) use the same `/api/v1/voice/*` endpoints.

---

## API Endpoints

### Common Endpoints (All Providers)

| Endpoint | Description |
|----------|-------------|
| `POST /api/v1/voice/call` | Make AI-powered call |
| `GET /api/v1/voice/call/{id}` | Get call status/transcript |
| `POST /api/v1/voice/call/{id}/stop` | Stop active call |
| `POST /api/v1/voice/call/{id}/sync` | Poll call status (for local dev) |
| `POST /api/v1/voice/agent` | Create voice agent |
| `GET /api/v1/voice/agent` | List agents |
| `GET /api/v1/voice/agent/{id}` | Get agent details |
| `POST /api/v1/voice/webhook` | Webhook for call updates |
| `GET /api/v1/voice/health` | Check provider health |

### Make Call Request

```json
POST /api/v1/voice/call
{
  "phone_number": "+919876543210",
  "borrower_name": "Rahul Sharma",
  "outstanding_amount": 25000,
  "emi_amount": 5000,
  "dpd": 45,
  "loan_type": "Personal Loan",
  "case_id": "optional-case-uuid"
}
```

---

## Dynamic Variables

All providers support these variables in prompts:

| Variable | Description |
|----------|-------------|
| `{{borrower_name}}` | Customer's name |
| `{{outstanding_amount}}` | Total amount due |
| `{{emi_amount}}` | Monthly EMI amount |
| `{{dpd}}` | Days past due |
| `{{loan_type}}` | Type of loan |
| `{{case_id}}` | Internal case reference |

---

## Provider Comparison

| Feature | Mock | Bolna | Sarvam | LiveKit |
|---------|------|-------|--------|---------|
| Real calls | No | Yes | Yes | Yes |
| Setup complexity | None | Low | Medium | Medium |
| Latency | N/A | ~300ms | ~500ms | ~200ms |
| Indian languages | N/A | Excellent | Excellent | Excellent |
| Telephony included | N/A | Yes | No (Exotel) | No (WebRTC) |
| Cost control | N/A | Per minute | Per API call | Per minute |
| Browser testing | Yes | No | No | Yes |
