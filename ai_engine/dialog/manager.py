import re
from typing import Dict, Any, List, Optional

from .prompts import (
    COLLECTION_SYSTEM_PROMPT,
    COMPLIANCE_KEYWORDS,
    SENTIMENT_INDICATORS,
)
from .guardrails import ComplianceChecker
from ..llm import get_llm_provider, LLMProvider


class DialogManager:
    """Dialog manager for collection conversations using configurable LLM provider."""

    def __init__(self):
        self.llm: LLMProvider = get_llm_provider()
        self.compliance_checker = ComplianceChecker()

    async def generate_response(
        self,
        conversation_history: List[Dict[str, str]],
        context: Dict[str, Any],
        language: str = "hi"
    ) -> Dict[str, Any]:
        """Generate AI response for collection dialog."""
        # Build system prompt with context
        system_prompt = COLLECTION_SYSTEM_PROMPT.format(
            borrower_name=context.get("borrower_name", "Customer"),
            outstanding_amount=context.get("outstanding_amount", 0),
            dpd=context.get("dpd", 0),
            emi_amount=context.get("emi_amount", 0),
            loan_type=context.get("loan_type", "Personal Loan"),
            language="Hindi" if language == "hi" else "English"
        )

        # Format conversation for LLM
        messages = [{"role": "system", "content": system_prompt}]
        for msg in conversation_history:
            messages.append({
                "role": msg.get("role", "user"),
                "content": msg.get("content", "")
            })

        try:
            ai_response = await self.llm.chat(messages, temperature=0.7, top_p=0.9)

            # Check compliance
            compliance_check = self.compliance_checker.check(ai_response)
            if not compliance_check["is_compliant"]:
                # Regenerate with stricter prompt
                ai_response = await self._regenerate_compliant(
                    messages, compliance_check["issues"]
                )

            # Extract entities and actions
            entities = self._extract_entities(ai_response, language)
            action = self._determine_action(ai_response, conversation_history)
            should_end = self._should_end_conversation(ai_response, action)

            return {
                "response": ai_response,
                "action": action,
                "entities": entities,
                "should_end": should_end
            }

        except Exception as e:
            print(f"LLM error: {e}")
            # Return fallback response
            return self._fallback_response(context, language)

    async def _regenerate_compliant(
        self,
        messages: List[Dict],
        issues: List[str]
    ) -> str:
        """Regenerate response avoiding compliance issues."""
        # Add a reminder to avoid issues
        reminder = f"IMPORTANT: Avoid the following issues: {', '.join(issues)}. Be professional and respectful."
        messages.append({"role": "system", "content": reminder})

        try:
            return await self.llm.chat(messages, temperature=0.5)
        except Exception:
            return "I apologize, but I need to transfer you to a human agent. Please hold."

    def _extract_entities(self, text: str, language: str) -> Dict[str, Any]:
        """Extract entities like amounts, dates from text."""
        entities = {
            "amounts": [],
            "dates": [],
            "promises": []
        }

        # Extract amounts (₹ format)
        amount_pattern = r'₹\s*(\d+(?:,\d+)*(?:\.\d+)?)'
        amounts = re.findall(amount_pattern, text)
        entities["amounts"] = [a.replace(",", "") for a in amounts]

        # Extract dates (various formats)
        date_patterns = [
            r'\d{1,2}[-/]\d{1,2}[-/]\d{2,4}',
            r'\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*',
            r'(?:tomorrow|आज|कल|परसों)'
        ]
        for pattern in date_patterns:
            dates = re.findall(pattern, text, re.IGNORECASE)
            entities["dates"].extend(dates)

        return entities

    def _determine_action(
        self,
        response: str,
        history: List[Dict]
    ) -> Optional[str]:
        """Determine the action suggested by the response."""
        response_lower = response.lower()

        if any(word in response_lower for word in ["promise", "वादा", "कर दूंगा"]):
            return "promise_to_pay"
        elif any(word in response_lower for word in ["callback", "बाद में", "later"]):
            return "schedule_callback"
        elif any(word in response_lower for word in ["dispute", "विवाद", "complaint"]):
            return "escalate_dispute"
        elif any(word in response_lower for word in ["hardship", "मुश्किल", "problem"]):
            return "offer_settlement"

        return None

    def _should_end_conversation(self, response: str, action: Optional[str]) -> bool:
        """Determine if conversation should end."""
        end_indicators = [
            "thank you", "धन्यवाद", "goodbye", "अलविदा",
            "have a good day", "शुभ दिन"
        ]
        return any(ind in response.lower() for ind in end_indicators)

    def _fallback_response(self, context: Dict, language: str) -> Dict[str, Any]:
        """Return fallback response when AI fails."""
        if language == "hi":
            response = f"माफ़ कीजिए, क्या आप बता सकते हैं कि आप ₹{context.get('emi_amount', 0)} की EMI कब pay कर सकते हैं?"
        else:
            response = f"I apologize, could you let me know when you can pay the EMI of ₹{context.get('emi_amount', 0)}?"

        return {
            "response": response,
            "action": None,
            "entities": {},
            "should_end": False
        }

    async def analyze_sentiment(self, text: str) -> Dict[str, Any]:
        """Analyze sentiment of text."""
        text_lower = text.lower()

        scores = {"positive": 0, "negative": 0, "neutral": 0, "angry": 0}

        for sentiment, keywords in SENTIMENT_INDICATORS.items():
            for keyword in keywords:
                if keyword.lower() in text_lower:
                    scores[sentiment] += 1

        # Determine dominant sentiment
        max_sentiment = max(scores, key=scores.get)
        total = sum(scores.values()) or 1

        # Convert to -1 to 1 scale
        if max_sentiment == "positive":
            score = scores["positive"] / total
        elif max_sentiment == "negative" or max_sentiment == "angry":
            score = -scores[max_sentiment] / total
        else:
            score = 0

        return {
            "sentiment": max_sentiment,
            "score": round(score, 2)
        }

    async def summarize_transcript(
        self,
        transcript: str,
        language: str = "en"
    ) -> Dict[str, Any]:
        """Summarize a call transcript."""
        prompt = f"""Summarize the following collection call transcript.
Extract key points, action items, and any mentioned amounts or dates.

Transcript:
{transcript}

Provide:
1. A brief summary (2-3 sentences)
2. Key points discussed
3. Any action items or promises made
4. Mentioned amounts and dates
"""

        try:
            text = await self.llm.generate(prompt)

            return {
                "summary": text[:500],  # First 500 chars as summary
                "key_points": self._extract_bullet_points(text),
                "action_items": [],
                "entities": self._extract_entities(transcript, language)
            }

        except Exception as e:
            print(f"Summarization error: {e}")
            return {
                "summary": "Unable to generate summary.",
                "key_points": [],
                "action_items": [],
                "entities": {}
            }

    def _extract_bullet_points(self, text: str) -> List[str]:
        """Extract bullet points from text."""
        lines = text.split("\n")
        points = []
        for line in lines:
            line = line.strip()
            if line.startswith(("-", "•", "*", "1", "2", "3", "4", "5")):
                points.append(line.lstrip("-•*0123456789. "))
        return points[:5]  # Return max 5 points

    async def check_compliance(self, transcript: str) -> Dict[str, Any]:
        """Check transcript for compliance issues."""
        return self.compliance_checker.check(transcript)
