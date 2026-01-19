"""Main content moderation orchestrator.

Coordinates multiple moderation checks and produces a final verdict.
"""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel


class ModerationStatus(str, Enum):
    """Result status for moderation check."""
    PASSED = "passed"
    FLAGGED = "flagged"  # Needs human review
    BLOCKED = "blocked"  # Automatically rejected


class ModerationType(str, Enum):
    """Types of moderation checks."""
    POLICY = "policy"  # Hate speech, harassment, etc.
    FACTUALITY = "factuality"  # Claim verification
    PLAGIARISM = "plagiarism"  # Too similar to sources
    BRAND_SAFETY = "brand_safety"  # Off-brand content
    PLATFORM_TOS = "platform_tos"  # Platform-specific rules


@dataclass
class ModerationConfig:
    """Configuration for moderation behavior."""
    # Confidence thresholds
    auto_pass_threshold: float = 0.95  # Above this, auto-pass
    review_threshold: float = 0.70  # Above this but below auto-pass, flag for review
    # Below review_threshold, auto-block

    # Which checks to run
    check_policy: bool = True
    check_factuality: bool = False  # Expensive, disabled by default
    check_plagiarism: bool = True
    check_brand_safety: bool = True
    check_platform_tos: bool = True

    # Plagiarism settings
    max_similarity_score: float = 0.80  # Flag if > 80% similar to sources

    # Platform-specific rules
    platform: Optional[str] = None


@dataclass
class ModerationFlag:
    """A single moderation flag."""
    type: ModerationType
    code: str
    message: str
    confidence: float
    details: Optional[dict] = None


@dataclass
class ModerationResult:
    """Result of moderation check."""
    id: UUID = field(default_factory=uuid4)
    status: ModerationStatus = ModerationStatus.PASSED
    confidence: float = 1.0
    flags: list[ModerationFlag] = field(default_factory=list)
    details: dict = field(default_factory=dict)
    checked_at: datetime = field(default_factory=datetime.utcnow)

    @property
    def passed(self) -> bool:
        """Whether content passed moderation."""
        return self.status == ModerationStatus.PASSED

    @property
    def needs_review(self) -> bool:
        """Whether content needs human review."""
        return self.status == ModerationStatus.FLAGGED

    @property
    def blocked(self) -> bool:
        """Whether content was blocked."""
        return self.status == ModerationStatus.BLOCKED

    def to_dict(self) -> dict:
        """Convert to dictionary for storage."""
        return {
            "id": str(self.id),
            "status": self.status.value,
            "confidence": self.confidence,
            "flags": [
                {
                    "type": f.type.value,
                    "code": f.code,
                    "message": f.message,
                    "confidence": f.confidence,
                    "details": f.details,
                }
                for f in self.flags
            ],
            "details": self.details,
            "checked_at": self.checked_at.isoformat(),
        }


class ContentModerator:
    """Main content moderation orchestrator.

    Runs multiple moderation checks and produces a final verdict.

    Usage:
        moderator = ContentModerator()
        result = await moderator.moderate(content, content_type="post")

        if result.blocked:
            raise ContentBlockedError(result.flags)
        elif result.needs_review:
            queue_for_review(content, result)
    """

    def __init__(self, config: Optional[ModerationConfig] = None):
        self.config = config or ModerationConfig()

    async def moderate(
        self,
        content: str,
        content_type: str = "post",
        context: Optional[dict] = None,
    ) -> ModerationResult:
        """Run all configured moderation checks on content.

        Args:
            content: The text content to moderate
            content_type: Type of content (post, comment, script)
            context: Additional context (brand guidelines, source material)

        Returns:
            ModerationResult with status and any flags
        """
        context = context or {}
        all_flags: list[ModerationFlag] = []

        # Run policy check (hate speech, harassment, etc.)
        if self.config.check_policy:
            policy_flags = await self._check_policy(content)
            all_flags.extend(policy_flags)

        # Run plagiarism check (similarity to sources)
        if self.config.check_plagiarism and context.get("sources"):
            plagiarism_flags = await self._check_plagiarism(
                content, context["sources"]
            )
            all_flags.extend(plagiarism_flags)

        # Run brand safety check
        if self.config.check_brand_safety and context.get("brand_guidelines"):
            brand_flags = await self._check_brand_safety(
                content, context["brand_guidelines"]
            )
            all_flags.extend(brand_flags)

        # Run platform ToS check
        if self.config.check_platform_tos and self.config.platform:
            tos_flags = await self._check_platform_tos(
                content, self.config.platform
            )
            all_flags.extend(tos_flags)

        # Determine final status based on flags
        return self._compute_verdict(all_flags)

    async def _check_policy(self, content: str) -> list[ModerationFlag]:
        """Check content against policy rules.

        This is a lightweight local check for obvious violations.
        For production, integrate with a dedicated moderation API.
        """
        flags = []

        # Check for common policy violations
        from runner.moderation.policies import PolicyChecker
        checker = PolicyChecker()
        violations = checker.check(content)

        for violation in violations:
            flags.append(ModerationFlag(
                type=ModerationType.POLICY,
                code=violation.code,
                message=violation.message,
                confidence=violation.confidence,
                details=violation.details,
            ))

        return flags

    async def _check_plagiarism(
        self, content: str, sources: list[str]
    ) -> list[ModerationFlag]:
        """Check if content is too similar to source material."""
        flags = []

        from runner.moderation.similarity import SimilarityChecker
        checker = SimilarityChecker()

        for i, source in enumerate(sources):
            result = checker.compute_similarity(content, source)
            if result.score > self.config.max_similarity_score:
                flags.append(ModerationFlag(
                    type=ModerationType.PLAGIARISM,
                    code="high_similarity",
                    message=f"Content is {result.score:.0%} similar to source {i+1}",
                    confidence=result.score,
                    details={
                        "source_index": i,
                        "similarity_score": result.score,
                        "matching_phrases": result.matching_phrases,
                    },
                ))

        return flags

    async def _check_brand_safety(
        self, content: str, guidelines: dict
    ) -> list[ModerationFlag]:
        """Check if content aligns with brand guidelines."""
        flags = []

        # Check for forbidden topics
        forbidden_topics = guidelines.get("forbidden_topics", [])
        content_lower = content.lower()

        for topic in forbidden_topics:
            if topic.lower() in content_lower:
                flags.append(ModerationFlag(
                    type=ModerationType.BRAND_SAFETY,
                    code="forbidden_topic",
                    message=f"Content mentions forbidden topic: {topic}",
                    confidence=0.9,
                    details={"topic": topic},
                ))

        # Check for required disclaimers
        required_disclaimers = guidelines.get("required_disclaimers", [])
        for disclaimer in required_disclaimers:
            if disclaimer.lower() not in content_lower:
                flags.append(ModerationFlag(
                    type=ModerationType.BRAND_SAFETY,
                    code="missing_disclaimer",
                    message=f"Missing required disclaimer: {disclaimer}",
                    confidence=0.95,
                    details={"disclaimer": disclaimer},
                ))

        return flags

    async def _check_platform_tos(
        self, content: str, platform: str
    ) -> list[ModerationFlag]:
        """Check content against platform-specific rules."""
        flags = []

        # Platform-specific checks
        platform_rules = PLATFORM_RULES.get(platform, {})

        # Check character limits
        max_chars = platform_rules.get("max_characters")
        if max_chars and len(content) > max_chars:
            flags.append(ModerationFlag(
                type=ModerationType.PLATFORM_TOS,
                code="exceeds_length",
                message=f"Content exceeds {platform} limit of {max_chars} characters",
                confidence=1.0,
                details={
                    "platform": platform,
                    "max_characters": max_chars,
                    "actual_characters": len(content),
                },
            ))

        # Check for forbidden content
        forbidden = platform_rules.get("forbidden_content", [])
        content_lower = content.lower()
        for item in forbidden:
            if item.lower() in content_lower:
                flags.append(ModerationFlag(
                    type=ModerationType.PLATFORM_TOS,
                    code="forbidden_content",
                    message=f"Content contains {platform} forbidden term: {item}",
                    confidence=0.85,
                    details={"platform": platform, "term": item},
                ))

        return flags

    def _compute_verdict(self, flags: list[ModerationFlag]) -> ModerationResult:
        """Compute final moderation verdict from all flags."""
        if not flags:
            return ModerationResult(
                status=ModerationStatus.PASSED,
                confidence=1.0,
                flags=[],
            )

        # Get the highest-confidence flag
        max_confidence = max(f.confidence for f in flags)

        # Determine status based on confidence thresholds
        if max_confidence < self.config.review_threshold:
            # Low confidence in any violation - pass
            status = ModerationStatus.PASSED
        elif max_confidence < self.config.auto_pass_threshold:
            # Medium confidence - flag for review
            status = ModerationStatus.FLAGGED
        else:
            # High confidence violation - block
            status = ModerationStatus.BLOCKED

        # Check for critical violations that always block
        critical_codes = {"hate_speech", "harassment", "violence", "illegal"}
        for flag in flags:
            if flag.code in critical_codes and flag.confidence > 0.7:
                status = ModerationStatus.BLOCKED
                break

        return ModerationResult(
            status=status,
            confidence=max_confidence,
            flags=flags,
            details={
                "total_flags": len(flags),
                "flag_types": list(set(f.type.value for f in flags)),
            },
        )


# Platform-specific rules
PLATFORM_RULES = {
    "linkedin": {
        "max_characters": 3000,
        "forbidden_content": [],  # LinkedIn is fairly permissive
    },
    "twitter": {
        "max_characters": 280,
        "forbidden_content": [],
    },
    "threads": {
        "max_characters": 500,
        "forbidden_content": [],
    },
    "instagram": {
        "max_characters": 2200,  # Caption limit
        "forbidden_content": [],
    },
}
