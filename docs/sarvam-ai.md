# Sarvam AI Integration

Sarvam AI provides sovereign Indian AI models optimized for 11 Indian languages. CollectIQ integrates Sarvam's APIs for STT, TTS, and LLM.

## Why Sarvam?

| Feature | Sarvam | Others |
|---------|--------|--------|
| **Indian Languages** | 11 native languages | Limited support |
| **Code-mixing** | Native Hinglish support | Translation-based |
| **Pricing** | ₹1/min for agents | ₹3-10/min |
| **Data Sovereignty** | India-hosted | Global |

## Available Services

### 1. Speech-to-Text (Saarika)

Sarvam's STT model with:
- 11 Indian languages + English
- Auto language detection
- Code-mixing support
- Word-level timestamps

**Cost**: ₹30/hour (~₹0.50/min)

### 2. Text-to-Speech (Bulbul)

Natural Indian voices:
- 10 languages
- 7 voice options (4 female, 3 male)
- Pitch, pace, loudness control
- Code-mixed text support

**Cost**: ₹15/10,000 characters

### 3. LLM (Sarvam-M)

24B parameter model:
- Native Indian language understanding
- Hybrid thinking mode
- Wikipedia grounding
- Streaming support

**Cost**: Free tier available

## Setup

### 1. Get API Key

1. Sign up at [dashboard.sarvam.ai](https://dashboard.sarvam.ai)
2. Get your API key from the dashboard
3. New users get ₹1000 free credits

### 2. Configure Environment

```bash
# .env

# Use Sarvam for all AI services
LLM_PROVIDER=sarvam
STT_PROVIDER=sarvam

# Sarvam API Key
SARVAM_API_KEY=your-api-key

# Model Configuration (optional, these are defaults)
SARVAM_LLM_MODEL=sarvam-m
SARVAM_STT_MODEL=saarika:v2
SARVAM_TTS_MODEL=bulbul:v2
SARVAM_TTS_VOICE=Anushka
```

### 3. Available Voices

| Voice | Gender | Best For |
|-------|--------|----------|
| **Anushka** | Female | Hindi, General |
| **Manisha** | Female | Telugu |
| **Vidya** | Female | Tamil |
| **Arya** | Female | Bengali |
| **Abhilash** | Male | Hindi, General |
| **Karun** | Male | Tamil |
| **Hitesh** | Male | Telugu |

### 4. Supported Languages

| Code | Language |
|------|----------|
| `hi-IN` | Hindi |
| `en-IN` | English (Indian) |
| `ta-IN` | Tamil |
| `te-IN` | Telugu |
| `bn-IN` | Bengali |
| `mr-IN` | Marathi |
| `gu-IN` | Gujarati |
| `kn-IN` | Kannada |
| `ml-IN` | Malayalam |
| `pa-IN` | Punjabi |
| `od-IN` | Odia |

## Usage Examples

### STT (Speech-to-Text)

```python
from stt import get_stt_provider

# Set STT_PROVIDER=sarvam in .env
stt = get_stt_provider()

# Transcribe audio
result = await stt.transcribe(
    audio_data=audio_bytes,
    language="hi",  # or "auto" for detection
    audio_format="wav"
)

print(result.text)  # Transcribed text
print(result.language)  # Detected language
```

### TTS (Text-to-Speech)

```python
from voice.sarvam_tts import SarvamTTSService

tts = SarvamTTSService()

# Synthesize speech
audio = await tts.synthesize(
    text="Namaste, kaise hain aap?",
    voice="Anushka",
    language="hi",
    pace=1.0,
    pitch=0.0
)

# Stream for lower latency
async for chunk in tts.synthesize_chunked(text, voice="Anushka"):
    play_audio(chunk)
```

### LLM (Chat)

```python
from llm import get_llm_provider

# Set LLM_PROVIDER=sarvam in .env
llm = get_llm_provider()

# Chat
response = await llm.chat([
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "Mujhe loan ke baare mein batao"}
])

# Stream for real-time
async for token in llm.chat_stream(messages):
    print(token, end="")
```

## Comparison with Other Providers

### For Voice Pipeline (Internal Demo)

| Provider | STT | TTS | LLM | Best For |
|----------|-----|-----|-----|----------|
| **Sarvam** | ₹0.50/min | ₹15/10K chars | Free | Indian languages |
| **Groq** | ₹0.06/min | - | ₹0.05/1M tokens | Speed |
| **Whisper+Edge** | Free (local) | Free | - | Offline |

### For Phone Calls

| Provider | Cost | API | Notes |
|----------|------|-----|-------|
| **Sarvam Samvaad** | ₹1/min | Dashboard only | No programmatic API |
| **Bolna** | ₹3-7/min | Full API | Easy integration |
| **ElevenLabs** | ₹7-8.5/min | Full API | Best voice quality |

## Recommended Configuration

### For Indian Languages (Hinglish)

```bash
# Best for Hindi/Hinglish conversations
LLM_PROVIDER=sarvam
STT_PROVIDER=sarvam
SARVAM_API_KEY=your-key
```

### For Speed + Quality Balance

```bash
# Groq for speed, Sarvam TTS for Indian voices
LLM_PROVIDER=groq
STT_PROVIDER=groq
# Use Sarvam TTS directly in code for Indian voices
```

### For Offline/Cost Savings

```bash
# Local models
LLM_PROVIDER=ollama
STT_PROVIDER=whisper
# Edge TTS is free for TTS
```

## API Reference

### STT Endpoint

```
POST https://api.sarvam.ai/speech-to-text
Header: api-subscription-key: <your-key>
Content-Type: multipart/form-data

file: <audio file>
model: saarika:v2
language_code: hi-IN (or "unknown" for auto-detect)
```

### TTS Endpoint

```
POST https://api.sarvam.ai/text-to-speech
Header: api-subscription-key: <your-key>
Content-Type: application/json

{
  "inputs": ["Text to speak"],
  "target_language_code": "hi-IN",
  "speaker": "Anushka",
  "model": "bulbul:v2"
}
```

### LLM Endpoint

```
POST https://api.sarvam.ai/v1/chat/completions
Header: api-subscription-key: <your-key>
Content-Type: application/json

{
  "model": "sarvam-m",
  "messages": [{"role": "user", "content": "Hello"}],
  "stream": false
}
```

## Resources

- [Sarvam Dashboard](https://dashboard.sarvam.ai)
- [API Documentation](https://docs.sarvam.ai)
- [Sarvam-M Model](https://huggingface.co/sarvamai/sarvam-m)
