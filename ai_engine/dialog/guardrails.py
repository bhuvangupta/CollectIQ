"""Compliance and safety guardrails for collection dialogs."""

import re
from typing import Dict, List, Any

from .prompts import COMPLIANCE_KEYWORDS


class ComplianceChecker:
    """Check for compliance violations in collection conversations."""

    def __init__(self):
        self.violation_patterns = self._build_patterns()

    def _build_patterns(self) -> Dict[str, List[str]]:
        """Build regex patterns for violation detection."""
        return {
            "threatening": [
                r"(threat|धमकी|मारूंगा|पीटूंगा)",
                r"(jail|जेल|arrest|गिरफ्तार)",
                r"(legal\s+action|कानूनी\s+कार्रवाई)",
                r"(consequences|परिणाम\s+भुगतना)",
            ],
            "abusive": [
                r"(stupid|बेवकूफ|idiot|पागल)",
                r"(fool|मूर्ख|useless|निकम्मा)",
            ],
            "privacy_violation": [
                r"(tell\s+your\s+(boss|employer|neighbor))",
                r"(आपके\s+(बॉस|पड़ोसी|ऑफिस)\s+को\s+बताऊंगा)",
                r"(inform\s+your\s+family)",
                r"(social\s+media|सोशल\s+मीडिया)",
            ],
            "harassment": [
                r"(call\s+again\s+and\s+again|बार\s+बार\s+फोन)",
                r"(won't\s+let\s+you|नहीं\s+छोड़ूंगा)",
                r"(harass|परेशान\s+करूंगा)",
            ],
            "misrepresentation": [
                r"(police\s+will\s+come|पुलिस\s+आएगी)",
                r"(government\s+action|सरकारी\s+कार्रवाई)",
                r"(court\s+order|कोर्ट\s+का\s+आदेश)",
            ],
            "timing_violation": [
                # Calls outside 8 AM - 7 PM should be flagged
                # This would be checked at call level, not in text
            ],
        }

    def check(self, text: str) -> Dict[str, Any]:
        """Check text for compliance violations."""
        text_lower = text.lower()
        issues = []
        flags = []

        for category, patterns in self.violation_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text_lower, re.IGNORECASE):
                    issues.append(category)
                    flags.append({
                        "category": category,
                        "severity": self._get_severity(category),
                        "pattern": pattern,
                    })
                    break  # One match per category is enough

        # Also check for keyword matches
        for keyword in COMPLIANCE_KEYWORDS:
            if keyword.lower() in text_lower:
                if "keyword_match" not in issues:
                    issues.append("keyword_match")
                    flags.append({
                        "category": "keyword_match",
                        "severity": "medium",
                        "matched_keyword": keyword,
                    })

        return {
            "is_compliant": len(issues) == 0,
            "issues": list(set(issues)),
            "flags": flags,
        }

    def _get_severity(self, category: str) -> str:
        """Get severity level for a violation category."""
        severity_map = {
            "threatening": "high",
            "abusive": "high",
            "privacy_violation": "high",
            "harassment": "high",
            "misrepresentation": "medium",
            "keyword_match": "medium",
        }
        return severity_map.get(category, "low")

    def sanitize_response(self, response: str) -> str:
        """Sanitize response by removing/replacing problematic content."""
        result = response

        # Replace threatening phrases
        replacements = [
            (r"legal\s+action", "proper process"),
            (r"कानूनी\s+कार्रवाई", "उचित प्रक्रिया"),
            (r"consequences", "impact"),
            (r"परिणाम\s+भुगतना", "प्रभाव"),
        ]

        for pattern, replacement in replacements:
            result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)

        return result


class ResponseFilter:
    """Filter AI responses for safety and quality."""

    def __init__(self):
        self.compliance_checker = ComplianceChecker()
        self.max_length = 500  # Max response length in characters

    def filter(self, response: str) -> Dict[str, Any]:
        """Filter and validate AI response."""
        # Check compliance
        compliance = self.compliance_checker.check(response)

        if not compliance["is_compliant"]:
            # Attempt to sanitize
            sanitized = self.compliance_checker.sanitize_response(response)
            recheck = self.compliance_checker.check(sanitized)

            if not recheck["is_compliant"]:
                return {
                    "approved": False,
                    "response": None,
                    "reason": "Compliance violation",
                    "issues": compliance["issues"],
                }

            response = sanitized

        # Truncate if too long
        if len(response) > self.max_length:
            response = response[:self.max_length].rsplit(" ", 1)[0] + "..."

        return {
            "approved": True,
            "response": response,
            "reason": None,
            "issues": [],
        }
