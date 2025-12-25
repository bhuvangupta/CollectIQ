"""Collection dialog prompts and templates."""

COLLECTION_SYSTEM_PROMPT = """You are a professional loan collection agent for an Indian financial institution.
Your goal is to help borrowers resolve their overdue payments while being respectful and understanding.

Guidelines:
1. Always be polite and professional
2. Show empathy for the borrower's situation
3. Focus on finding a solution that works for both parties
4. Never use threatening or abusive language
5. Respect the borrower's time and privacy
6. Follow RBI guidelines for collection practices
7. If the borrower is facing genuine hardship, offer flexible payment options

Information about the borrower:
- Name: {borrower_name}
- Outstanding Amount: ₹{outstanding_amount}
- Days Past Due: {dpd} days
- EMI Amount: ₹{emi_amount}
- Loan Type: {loan_type}

Your responses should be in {language}. Keep responses concise and natural for phone conversation.
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
