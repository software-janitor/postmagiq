"""Service for tier-based feature flags and credit management.

Provides methods to check feature availability, get text limits,
and determine workflow config based on subscription tier.
"""

import math
from typing import Optional
from uuid import UUID

from sqlmodel import Session, select

from runner.db.engine import engine
from runner.db.models import (
    TierFeature,
    SubscriptionTier,
    AccountSubscription,
    SubscriptionStatus,
)


class FeatureNotAvailable(Exception):
    """Raised when a feature is not available for the current tier."""

    def __init__(self, feature_key: str, tier_name: str, required_tier: str):
        self.feature_key = feature_key
        self.tier_name = tier_name
        self.required_tier = required_tier
        super().__init__(
            f"Feature '{feature_key}' is not available on {tier_name}. "
            f"Upgrade to {required_tier} to access this feature."
        )


class TierService:
    """Service for tier-based feature management.

    Provides methods to:
    - Check if a feature is enabled for a workspace's tier
    - Get feature configuration (e.g., text limits)
    - Determine which workflow config to use
    - Calculate credit costs from USD amounts
    """

    # Feature to minimum tier mapping for upgrade CTAs
    FEATURE_MIN_TIER = {
        "basic_workflow": "free",
        "premium_workflow": "starter",
        "voice_transcription": "starter",
        "youtube_transcription": "pro",
        "priority_support": "pro",
        "api_access": "business",
        "team_workspaces": "business",
    }

    # Default text limits per tier
    DEFAULT_TEXT_LIMITS = {
        "free": 50000,
        "starter": 50000,
        "pro": 100000,
        "business": 100000,
    }

    def get_tier_for_workspace(self, workspace_id: UUID) -> Optional[SubscriptionTier]:
        """Get the subscription tier for a workspace.

        Args:
            workspace_id: Workspace UUID

        Returns:
            SubscriptionTier if found, None for free tier
        """
        with Session(engine) as session:
            sub_statement = select(AccountSubscription).where(
                AccountSubscription.workspace_id == workspace_id,
                AccountSubscription.status == SubscriptionStatus.active,
            )
            subscription = session.exec(sub_statement).first()

            if not subscription:
                # Return free tier
                tier_statement = select(SubscriptionTier).where(
                    SubscriptionTier.slug == "free"
                )
                tier = session.exec(tier_statement).first()
            else:
                tier = session.get(SubscriptionTier, subscription.tier_id)

            if tier:
                session.expunge(tier)
            return tier

    def get_tier_slug(self, workspace_id: UUID) -> str:
        """Get the tier slug for a workspace.

        Args:
            workspace_id: Workspace UUID

        Returns:
            Tier slug (e.g., 'free', 'starter', 'pro', 'business')
        """
        tier = self.get_tier_for_workspace(workspace_id)
        return tier.slug if tier else "free"

    def has_feature(self, workspace_id: UUID, feature_key: str) -> bool:
        """Check if a workspace has access to a feature.

        Args:
            workspace_id: Workspace UUID
            feature_key: Feature key (e.g., 'premium_workflow')

        Returns:
            True if feature is enabled, False otherwise
        """
        tier = self.get_tier_for_workspace(workspace_id)
        if not tier:
            return False

        with Session(engine) as session:
            statement = select(TierFeature).where(
                TierFeature.tier_id == tier.id,
                TierFeature.feature_key == feature_key,
            )
            feature = session.exec(statement).first()
            return feature.enabled if feature else False

    def require_feature(self, workspace_id: UUID, feature_key: str) -> None:
        """Require a feature, raising an error if not available.

        Args:
            workspace_id: Workspace UUID
            feature_key: Feature key (e.g., 'premium_workflow')

        Raises:
            FeatureNotAvailable: If feature is not enabled for this tier
        """
        if not self.has_feature(workspace_id, feature_key):
            tier = self.get_tier_for_workspace(workspace_id)
            tier_name = tier.name if tier else "Free"
            required_tier = self.FEATURE_MIN_TIER.get(feature_key, "Pro")
            raise FeatureNotAvailable(feature_key, tier_name, required_tier.title())

    def get_feature_config(
        self, workspace_id: UUID, feature_key: str
    ) -> Optional[dict]:
        """Get the configuration for a feature.

        Args:
            workspace_id: Workspace UUID
            feature_key: Feature key

        Returns:
            Feature config dict, or None if feature not found
        """
        tier = self.get_tier_for_workspace(workspace_id)
        if not tier:
            return None

        with Session(engine) as session:
            statement = select(TierFeature).where(
                TierFeature.tier_id == tier.id,
                TierFeature.feature_key == feature_key,
            )
            feature = session.exec(statement).first()
            return feature.config if feature else None

    def get_text_limit(self, workspace_id: UUID) -> int:
        """Get the text character limit for a workspace.

        Args:
            workspace_id: Workspace UUID

        Returns:
            Maximum text length in characters
        """
        tier_slug = self.get_tier_slug(workspace_id)

        # Try to get from premium_workflow config first
        config = self.get_feature_config(workspace_id, "premium_workflow")
        if config and "text_limit" in config:
            return config["text_limit"]

        # Fall back to basic_workflow config
        config = self.get_feature_config(workspace_id, "basic_workflow")
        if config and "text_limit" in config:
            return config["text_limit"]

        # Fall back to defaults
        return self.DEFAULT_TEXT_LIMITS.get(tier_slug, 50000)

    def get_workflow_config(self, workspace_id: UUID) -> str:
        """Get the workflow config file to use for a workspace.

        Free tier uses basic workflow (groq-free.yaml).
        Paid tiers use premium workflow (groq-premium.yaml).

        Args:
            workspace_id: Workspace UUID

        Returns:
            Workflow config filename (e.g., 'groq-free.yaml')
        """
        if self.has_feature(workspace_id, "premium_workflow"):
            return "groq-premium.yaml"
        return "groq-free.yaml"

    def get_all_features(self, workspace_id: UUID) -> dict:
        """Get all features and their status for a workspace.

        Args:
            workspace_id: Workspace UUID

        Returns:
            Dict of feature_key -> {enabled, config}
        """
        tier = self.get_tier_for_workspace(workspace_id)
        tier_slug = tier.slug if tier else "free"
        tier_id = tier.id if tier else None

        # Start with defaults for all features
        features = {}
        for feature_key in self.FEATURE_MIN_TIER:
            features[feature_key] = {
                "enabled": False,
                "config": {},
            }

        if not tier_id:
            # Free tier without DB record - set basic_workflow
            features["basic_workflow"] = {
                "enabled": True,
                "config": {
                    "text_limit": self.DEFAULT_TEXT_LIMITS.get(tier_slug, 50000)
                },
            }
            return features

        with Session(engine) as session:
            statement = select(TierFeature).where(TierFeature.tier_id == tier_id)
            tier_features = session.exec(statement).all()

            for tf in tier_features:
                features[tf.feature_key] = {
                    "enabled": tf.enabled,
                    "config": tf.config or {},
                }

        return features

    def get_features_summary(self, workspace_id: UUID) -> dict:
        """Get a simplified features summary for API response.

        Args:
            workspace_id: Workspace UUID

        Returns:
            Dict with feature keys -> bool and text_limit
        """
        features = self.get_all_features(workspace_id)
        text_limit = self.get_text_limit(workspace_id)

        return {
            "premium_workflow": features.get("premium_workflow", {}).get(
                "enabled", False
            ),
            "voice_transcription": features.get("voice_transcription", {}).get(
                "enabled", False
            ),
            "youtube_transcription": features.get("youtube_transcription", {}).get(
                "enabled", False
            ),
            "priority_support": features.get("priority_support", {}).get(
                "enabled", False
            ),
            "api_access": features.get("api_access", {}).get("enabled", False),
            "team_workspaces": features.get("team_workspaces", {}).get(
                "enabled", False
            ),
            "text_limit": text_limit,
        }

    @staticmethod
    def usd_to_credits(usd_amount: float) -> int:
        """Convert USD amount to credits (1 credit = $0.01).

        Always rounds up to ensure cost is covered.

        Args:
            usd_amount: Cost in USD

        Returns:
            Credits (rounded up)
        """
        return math.ceil(usd_amount * 100)

    @staticmethod
    def credits_to_usd(credits: int) -> float:
        """Convert credits to USD amount.

        Args:
            credits: Number of credits

        Returns:
            Cost in USD
        """
        return credits / 100

    def estimate_credits(self, text_length: int, is_premium: bool = False) -> int:
        """Estimate credits needed for a workflow run.

        Uses a simple estimation based on text length and tier.
        Phase 1: Fixed estimates based on text length
        Phase 2 (future): Use rolling average of actual costs

        Args:
            text_length: Character count of input text
            is_premium: Whether premium workflow will be used

        Returns:
            Estimated credits needed
        """
        # Rough estimation: ~4 chars per token, multiple agents
        estimated_tokens = text_length * 0.25

        # Cost per token varies by tier
        # Free tier: ~$0.0002/token (cheaper models)
        # Premium tier: ~$0.0004/token (better models)
        cost_per_token = 0.0004 if is_premium else 0.0002

        estimated_cost_usd = estimated_tokens * cost_per_token
        return self.usd_to_credits(estimated_cost_usd)


# Singleton instance
tier_service = TierService()
