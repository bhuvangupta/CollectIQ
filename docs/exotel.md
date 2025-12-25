# Exotel Integration

CollectIQ supports direct Exotel telephony integration for production phone calls in India.

## Overview

Exotel is one of India's leading cloud telephony providers. CollectIQ can use Exotel for:

- **Outbound calls** - Initiate collection calls to borrowers
- **Call status tracking** - Real-time webhook callbacks for call events
- **SMS delivery** - Send SMS reminders and notifications
- **Campaign automation** - Bulk calling with retry scheduling

## Setup

### 1. Get Exotel Credentials

Sign up at [Exotel Dashboard](https://exotel.com/dashboard) and obtain:

- **API Key** - Your Exotel API key
- **API Token** - Your Exotel API token
- **SID** - Your account SID
- **Caller ID** - A verified phone number for outbound calls

### 2. Configure Environment

```bash
# .env

# Telephony Provider
TELEPHONY_PROVIDER=exotel

# Exotel Configuration
EXOTEL_API_KEY=your-api-key
EXOTEL_API_TOKEN=your-api-token
EXOTEL_SID=your-account-sid
EXOTEL_SUBDOMAIN=api          # or your custom subdomain
EXOTEL_CALLER_ID=+91XXXXXXXXXX
EXOTEL_WEBHOOK_URL=https://your-domain.com/webhooks/exotel
```

### 3. Configure Webhooks

Set up webhook URLs in your Exotel dashboard to receive call status updates:

| Event | Webhook URL |
|-------|-------------|
| Status Callback | `https://your-domain.com/webhooks/exotel/status` |
| Passthru (future) | `https://your-domain.com/webhooks/exotel/passthru` |

## Usage

### Per-Campaign Provider Selection

Each campaign can specify its own telephony provider:

```python
# Create campaign with Exotel
campaign = {
    "name": "December Collections",
    "campaign_type": "ai_voice",
    "telephony_provider": "exotel",  # or "bolna", "mock"
    "retry_delays_minutes": [30, 120, 480],  # Retry after 30min, 2hr, 8hr
    ...
}
```

### Retry Scheduling

Campaigns support automatic retry scheduling for failed calls:

| Outcome | Behavior |
|---------|----------|
| `no_answer` | Schedule retry |
| `busy` | Schedule retry |
| `voicemail` | Schedule retry |
| `failed` | Schedule retry |
| `network_error` | Schedule retry |
| `answered` | Mark complete |
| `promise_to_pay` | Mark successful |

Default retry delays: 30 minutes, 2 hours, 8 hours (configurable per campaign).

### Live Monitoring

Monitor campaign progress in real-time:

```bash
GET /api/v1/campaigns/{campaign_id}/live
```

Response:
```json
{
  "calls_in_progress": 5,
  "calls_queued": 12,
  "retries_pending": 8,
  "calls_completed_1h": 45,
  "success_rate_1h": 32.5,
  "calls_per_minute": 0.75,
  "estimated_completion_time": "2024-12-27T15:30:00Z",
  "recent_outcomes": [
    {"borrower_id": "...", "outcome": "promise_to_pay", "timestamp": "..."}
  ]
}
```

## API Reference

### Initiate Call

Called automatically by campaign tasks, but can be triggered manually:

```python
from telephony.services.factory import get_telephony_provider

provider = get_telephony_provider()  # Returns ExotelProvider if configured
result = await provider.initiate_call(
    from_number="+91XXXXXXXXXX",
    to_number="+91YYYYYYYYYY",
    caller_id="+91XXXXXXXXXX",
    callback_url="https://your-domain.com/webhooks/exotel/status",
    custom_field="campaign_id:borrower_id"
)
```

### Get Call Status

```python
status = await provider.get_call_status(call_id="exotel-call-sid")
```

### Send SMS

```python
message_id = await provider.send_sms(
    phone_number="+91YYYYYYYYYY",
    message="Your payment reminder...",
    sender_id="COLLIQ"
)
```

## Webhook Payload

Exotel sends status updates via POST to your webhook URL:

```json
{
  "CallSid": "call-sid",
  "From": "+91XXXXXXXXXX",
  "To": "+91YYYYYYYYYY",
  "Status": "completed",
  "Direction": "outbound-api",
  "Duration": 45,
  "RecordingUrl": "https://...",
  "CustomField": "campaign_id:campaign_borrower_id"
}
```

CollectIQ automatically parses this and updates campaign borrower status.

## Comparison with Bolna AI

| Feature | Exotel Direct | Bolna AI |
|---------|--------------|----------|
| Call Type | Basic IVR | Conversational AI |
| AI Agent | No | Yes (built-in) |
| Cost | Lower | Higher |
| Setup | Simple | Agent configuration |
| Best For | Basic reminders | Complex collections |

Use Exotel for simple payment reminders. Use Bolna AI for AI-powered collection conversations.

## Troubleshooting

### Call Not Initiating

1. Check credentials in `.env`
2. Verify caller ID is approved in Exotel dashboard
3. Check API rate limits

### Webhooks Not Received

1. Ensure `EXOTEL_WEBHOOK_URL` is publicly accessible
2. Check webhook configuration in Exotel dashboard
3. Verify SSL certificate is valid

### Call Quality Issues

1. Check network connectivity
2. Verify phone number format (+91 prefix)
3. Review Exotel dashboard for error logs

## Pricing

Exotel pricing varies by region and volume. Check [Exotel Pricing](https://exotel.com/pricing) for current rates.

Typical costs:
- Outbound calls: ~Rs 0.50-1.00/minute
- SMS: ~Rs 0.10-0.25/message
