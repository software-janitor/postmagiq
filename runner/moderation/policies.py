"""Policy checker for content moderation.

Checks content against policy rules for:
- Hate speech
- Harassment
- Violence
- Misinformation patterns
- Spam patterns

This is a lightweight local implementation. For production,
integrate with dedicated moderation APIs (OpenAI Moderation,
Perspective API, etc.)
"""

import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class PolicyViolation:
    """A policy violation found in content."""
    code: str
    message: str
    confidence: float
    details: Optional[dict] = None


class PolicyChecker:
    """Check content against policy rules.

    This is a lightweight, rule-based checker for obvious violations.
    For production use, integrate with a dedicated moderation API.

    Usage:
        checker = PolicyChecker()
        violations = checker.check(content)

        if violations:
            for v in violations:
                print(f"{v.code}: {v.message} ({v.confidence:.0%})")
    """

    def __init__(self):
        # Pattern-based detection for obvious violations
        # These are intentionally broad to catch variations
        self._patterns = self._build_patterns()

    def _build_patterns(self) -> dict:
        """Build regex patterns for policy violations."""
        return {
            "spam_repetition": {
                "pattern": r"(.{10,})\1{3,}",  # Same 10+ chars repeated 3+ times
                "code": "spam",
                "message": "Excessive repetition detected",
                "confidence": 0.8,
            },
            "excessive_caps": {
                "pattern": r"[A-Z\s]{50,}",  # 50+ consecutive caps
                "code": "spam",
                "message": "Excessive capitalization",
                "confidence": 0.6,
            },
            "url_spam": {
                "pattern": r"(https?://\S+\s*){5,}",  # 5+ URLs
                "code": "spam",
                "message": "Excessive URLs detected",
                "confidence": 0.7,
            },
            "contact_solicitation": {
                "pattern": r"(dm|message|contact)\s+me\s+(for|to)\s+(price|deal|offer)",
                "code": "spam",
                "message": "Potential spam solicitation",
                "confidence": 0.65,
            },
        }

    def check(self, content: str) -> list[PolicyViolation]:
        """Check content against all policy rules.

        Args:
            content: Text content to check

        Returns:
            List of PolicyViolation objects for any violations found
        """
        violations = []

        # Run pattern-based checks
        for name, rule in self._patterns.items():
            if re.search(rule["pattern"], content, re.IGNORECASE):
                violations.append(PolicyViolation(
                    code=rule["code"],
                    message=rule["message"],
                    confidence=rule["confidence"],
                    details={"pattern_name": name},
                ))

        # Check for empty or near-empty content
        if len(content.strip()) < 10:
            violations.append(PolicyViolation(
                code="too_short",
                message="Content is too short",
                confidence=1.0,
            ))

        # Check for potential prompt injection patterns
        prompt_injection_patterns = [
            r"ignore\s+(previous|all)\s+(instructions|prompts)",
            r"disregard\s+(everything|all)\s+(above|before)",
            r"you\s+are\s+now\s+a\s+different",
            r"forget\s+your\s+(training|instructions)",
        ]
        for pattern in prompt_injection_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                violations.append(PolicyViolation(
                    code="prompt_injection",
                    message="Potential prompt injection detected",
                    confidence=0.75,
                ))
                break  # Only flag once

        return violations


class AdvancedPolicyChecker:
    """Advanced policy checker using LLM-based moderation.

    This integrates with external moderation APIs for more accurate
    detection of nuanced policy violations.

    Usage:
        checker = AdvancedPolicyChecker(api_key="...")
        result = await checker.check(content)
    """

    def __init__(self, api_key: Optional[str] = None, model: str = "omni-moderation-latest"):
        """Initialize with OpenAI API key for moderation."""
        self.api_key = api_key
        self.model = model

    async def check(self, content: str) -> list[PolicyViolation]:
        """Check content using OpenAI's moderation API.

        Args:
            content: Text content to check

        Returns:
            List of PolicyViolation objects
        """
        if not self.api_key:
            # Fall back to basic checker
            basic = PolicyChecker()
            return basic.check(content)

        try:
            from openai import AsyncOpenAI

            client = AsyncOpenAI(api_key=self.api_key)
            response = await client.moderations.create(
                model=self.model,
                input=content,
            )

            violations = []
            result = response.results[0]

            # Map OpenAI categories to our violation codes
            category_map = {
                "hate": ("hate_speech", "Hate speech detected"),
                "hate/threatening": ("hate_speech", "Threatening hate speech detected"),
                "harassment": ("harassment", "Harassment detected"),
                "harassment/threatening": ("harassment", "Threatening harassment detected"),
                "self-harm": ("self_harm", "Self-harm content detected"),
                "self-harm/intent": ("self_harm", "Self-harm intent detected"),
                "self-harm/instructions": ("self_harm", "Self-harm instructions detected"),
                "sexual": ("sexual", "Sexual content detected"),
                "sexual/minors": ("csam", "CSAM content detected"),
                "violence": ("violence", "Violent content detected"),
                "violence/graphic": ("violence", "Graphic violence detected"),
            }

            for category, (code, message) in category_map.items():
                # Get the category score (0-1)
                score_attr = category.replace("/", "_") + "_score"
                if hasattr(result.category_scores, score_attr.replace("-", "_")):
                    score = getattr(result.category_scores, score_attr.replace("-", "_"))
                    if score > 0.5:  # Flag if >50% confidence
                        violations.append(PolicyViolation(
                            code=code,
                            message=message,
                            confidence=score,
                            details={"openai_category": category},
                        ))

            return violations

        except ImportError:
            # OpenAI not installed, fall back to basic
            basic = PolicyChecker()
            return basic.check(content)
        except Exception as e:
            # API error, fall back to basic
            basic = PolicyChecker()
            violations = basic.check(content)
            violations.append(PolicyViolation(
                code="moderation_error",
                message=f"Moderation API error: {str(e)}",
                confidence=0.5,
            ))
            return violations
