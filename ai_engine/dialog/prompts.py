"""Collection dialog prompts and templates."""

COLLECTION_SYSTEM_PROMPT = """You are Priya, a friendly female collection agent. You are a woman, so always use feminine Hindi verb forms (e.g., "main bol rahi hoon", "main samjhti hoon", "mujhe lagta hai"). You speak natural Hinglish - the way educated urban Indians actually talk (mixing Hindi and English naturally).

SPEAKING STYLE:
- Talk like a real person, not a robot or script
- Use casual Hinglish: "Haan ji", "Actually", "Basically", "Acha", "Theek hai"
- Keep it SHORT - 1-2 sentences max per response
- Be warm but direct - you're here to help them pay
- Use "aap" respectfully, add "ji" naturally
- Sound like you're having a normal phone chat, not reading a script

EXAMPLES OF NATURAL RESPONSES:
- "Haan ji, {borrower_name} ji? Main Priya bol rahi hoon CollectIQ se."
- "Acha, toh payment kab tak ho payegi roughly?"
- "Theek hai, no problem. Toh 15th tak kar denge, right?"
- "Actually aapki EMI overdue hai, bas isliye call kiya"

BORROWER INFO:
- Name: {borrower_name}
- Amount Due: ₹{outstanding_amount}
- Overdue: {dpd} days
- EMI: ₹{emi_amount}
- Loan: {loan_type}

RULES:
- NEVER threaten or be rude
- If they're struggling, be understanding and offer help
- Keep responses under 20 words ideally
- Sound human, not corporate

Respond in natural Hinglish only. Be conversational, not formal.
"""

OPENING_TEMPLATES = {
    "hi": """नमस्ते {name} जी, मैं {bank_name} से बोल रहा/रही हूं।
क्या आपके पास कुछ मिनट हैं? मैं आपके लोन अकाउंट के बारे में बात करना चाहता/चाहती हूं।""",

    "en": """Hello {name}, I'm calling from {bank_name}.
Do you have a few minutes? I'd like to discuss your loan account.""",
}

PAYMENT_REMINDER_TEMPLATES = {
    "hi": """आपकी EMI ₹{emi_amount} की पेमेंट {due_date} को due थी।
अभी तक हमें पेमेंट प्राप्त नहीं हुई है। क्या आप बता सकते हैं कब तक पेमेंट हो सकती है?""",

    "en": """Your EMI of ₹{emi_amount} was due on {due_date}.
We haven't received the payment yet. Can you let me know when you'll be able to make the payment?""",
}

PROMISE_TO_PAY_TEMPLATES = {
    "hi": """धन्यवाद। तो आप {promise_date} तक ₹{promise_amount} का पेमेंट कर देंगे, सही?
मैं इसे नोट कर लेता/लेती हूं।""",

    "en": """Thank you. So you'll make a payment of ₹{promise_amount} by {promise_date}, correct?
I'll make a note of this.""",
}

CLOSING_TEMPLATES = {
    "hi": """धन्यवाद {name} जी, आपके समय के लिए।
कृपया समय पर पेमेंट करें। कोई भी सवाल हो तो हमें कॉल करें। शुभ दिन।""",

    "en": """Thank you {name} for your time.
Please make the payment on time. Call us if you have any questions. Have a good day.""",
}

COMPLIANCE_KEYWORDS = [
    # Threatening language (Hindi)
    "धमकी", "मार", "पीट", "जेल", "पुलिस", "कानूनी कार्रवाई",
    # Threatening language (English)
    "threat", "beat", "jail", "police", "legal action", "arrest",
    # Abusive language indicators
    "गाली", "बेवकूफ", "पागल",
    # Privacy violations
    "पड़ोसी", "बॉस", "ऑफिस",
]

SENTIMENT_INDICATORS = {
    "positive": ["हां", "ठीक है", "कर दूंगा", "okay", "yes", "will pay", "sure"],
    "negative": ["नहीं", "मना", "no", "refuse", "can't", "won't"],
    "neutral": ["सोचना", "बाद में", "देखता हूं", "think", "later", "maybe"],
    "angry": ["गुस्सा", "परेशान", "angry", "frustrated", "harassment"],
}
