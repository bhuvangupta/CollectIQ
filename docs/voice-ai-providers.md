# Voice AI Providers

CollectIQ supports multiple Voice AI providers for automated collection calls. These providers handle the entire conversation autonomously - making real phone calls to borrowers.

## Supported Providers

| Provider | Pricing | Best For |
|----------|---------|----------|
| **Bolna AI** | ₹3-7/min | Indian languages, cost-effective |
| **ElevenLabs** | $0.08-0.10/min (~₹7-8.5) | Best voice quality, global |

---

## Bolna AI Setup

[Bolna](https://www.bolna.ai) is an Indian voice AI platform optimized for Hindi, Hinglish, and regional languages.

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

## ElevenLabs Setup

[ElevenLabs](https://elevenlabs.io) offers industry-leading voice quality with 160+ Indian accent variations.

### 1. Create ElevenLabs Account

1. Sign up at [elevenlabs.io](https://elevenlabs.io)
2. Get API key from **Settings → API Keys**

### 2. Create Conversational AI Agent

1. Go to **Conversational AI** in ElevenLabs dashboard
2. Create a new Agent
3. Configure the agent prompt with dynamic variables:

```
You are Priya, a professional collection agent from CollectIQ Finance.

CONTEXT:
- Calling: {{borrower_name}}
- Outstanding Amount: ₹{{outstanding_amount}}
- EMI Amount: ₹{{emi_amount}}
- Days Overdue: {{dpd}}

STYLE:
- Speak in natural Hinglish
- Be warm but professional
- Keep responses concise (1-2 sentences)

OBJECTIVE:
Remind about pending payment and get commitment date.

GUIDELINES:
- Always be respectful
- Never threaten or harass
- Offer flexible payment options
- Confirm any promises made
```

4. Select a Hindi/Indian voice (e.g., "Riya")
5. Save and note the **Agent ID**

### 3. Connect Phone Number (Twilio)

ElevenLabs requires Twilio for phone calls:

1. Go to **Phone Numbers** in ElevenLabs dashboard
2. Connect your Twilio account
3. Add a phone number
4. Note the **Phone Number ID**

### 4. Configure Environment

```bash
# .env
VOICE_AI_PROVIDER=elevenlabs
ELEVENLABS_API_KEY=your-api-key
ELEVENLABS_AGENT_ID=your-agent-id
ELEVENLABS_PHONE_NUMBER_ID=your-phone-number-id
```

### 5. Test the Integration

Same as Bolna - use the **AI Calls** page to test.

---

## Switching Providers

Simply change the `VOICE_AI_PROVIDER` environment variable:

```bash
# Use Bolna (default, recommended for India)
VOICE_AI_PROVIDER=bolna

# Use ElevenLabs (best voice quality)
VOICE_AI_PROVIDER=elevenlabs
```

Both providers use the same API endpoints - no code changes required.

---

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `POST /api/v1/voice/call` | Make AI-powered call |
| `GET /api/v1/voice/call/{id}` | Get call status/transcript |
| `POST /api/v1/voice/call/{id}/sync` | Poll call status (for local dev) |
| `POST /api/v1/voice/agent` | Create voice agent |
| `GET /api/v1/voice/agent` | List agents |
| `POST /api/v1/voice/webhook` | Webhook for call updates |

---

## Dynamic Variables

Both providers support these variables in prompts:

| Variable | Description |
|----------|-------------|
| `{{borrower_name}}` | Customer's name |
| `{{outstanding_amount}}` | Total amount due |
| `{{emi_amount}}` | Monthly EMI amount |
| `{{dpd}}` | Days past due |
| `{{loan_type}}` | Type of loan |
| `{{case_id}}` | Internal case reference |
