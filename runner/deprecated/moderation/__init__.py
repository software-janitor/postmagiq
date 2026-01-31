"""Content moderation module for safety and policy filtering.

This module provides moderation capabilities for generated content:
- Policy filters (hate speech, misinformation, etc.)
- Factuality/claim verification
- Plagiarism detection (similarity to sources)
- Brand safety checks
- Platform ToS compliance

Usage:
    from runner.moderation import ContentModerator

    moderator = ContentModerator()
    result = await moderator.moderate(content, content_type="post")

    if result.status == "blocked":
        # Content failed moderation
        print(f"Blocked: {result.flags}")
    elif result.status == "flagged":
        # Content needs human review
        queue_for_review(content, result)
    else:
        # Content passed
        publish(content)
"""

from runner.moderation.moderator import (
    ContentModerator,
    ModerationResult,
    ModerationConfig,
)
from runner.moderation.policies import (
    PolicyChecker,
    PolicyViolation,
)
from runner.moderation.similarity import (
    SimilarityChecker,
    SimilarityResult,
)

__all__ = [
    "ContentModerator",
    "ModerationResult",
    "ModerationConfig",
    "PolicyChecker",
    "PolicyViolation",
    "SimilarityChecker",
    "SimilarityResult",
]
