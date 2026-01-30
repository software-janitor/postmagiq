"""Tests for the tier service and feature flags.

Tests feature flag checks, credit calculations, and workflow config selection.
"""

import pytest
from unittest.mock import MagicMock, patch
from uuid import uuid4


class TestTierServiceCreation:
    """Tests for TierService instantiation."""

    def test_tier_service_can_be_imported(self):
        """TierService can be imported."""
        from api.services.tier_service import TierService, tier_service

        assert TierService is not None
        assert tier_service is not None

    def test_feature_not_available_exception(self):
        """FeatureNotAvailable exception has correct attributes."""
        from api.services.tier_service import FeatureNotAvailable

        exc = FeatureNotAvailable(
            feature_key="youtube_transcription",
            tier_name="Free",
            required_tier="Pro",
        )

        assert exc.feature_key == "youtube_transcription"
        assert exc.tier_name == "Free"
        assert exc.required_tier == "Pro"
        assert "youtube_transcription" in str(exc)
        assert "Pro" in str(exc)


class TestCreditConversion:
    """Tests for credit/USD conversion."""

    def test_usd_to_credits_rounds_up(self):
        """USD to credits always rounds up."""
        from api.services.tier_service import TierService

        # 1 cent = 1 credit
        assert TierService.usd_to_credits(0.01) == 1

        # Less than 1 cent rounds up to 1
        assert TierService.usd_to_credits(0.001) == 1
        assert TierService.usd_to_credits(0.009) == 1

        # 10 cents = 10 credits
        assert TierService.usd_to_credits(0.10) == 10

        # Partial cents round up
        assert TierService.usd_to_credits(0.105) == 11
        assert TierService.usd_to_credits(0.11) == 11

        # $1 = 100 credits
        assert TierService.usd_to_credits(1.00) == 100

    def test_credits_to_usd(self):
        """Credits to USD conversion."""
        from api.services.tier_service import TierService

        assert TierService.credits_to_usd(1) == 0.01
        assert TierService.credits_to_usd(10) == 0.10
        assert TierService.credits_to_usd(100) == 1.00
        assert TierService.credits_to_usd(420) == 4.20


class TestCreditEstimation:
    """Tests for credit estimation."""

    def test_estimate_credits_basic_tier(self):
        """Credit estimation for basic (free) tier."""
        from api.services.tier_service import TierService

        service = TierService()

        # Short text
        credits = service.estimate_credits(1000, is_premium=False)
        assert credits >= 1

        # Medium text
        credits = service.estimate_credits(10000, is_premium=False)
        assert credits >= 1

        # Long text
        credits = service.estimate_credits(50000, is_premium=False)
        assert credits >= 1

    def test_estimate_credits_premium_tier(self):
        """Credit estimation for premium tier."""
        from api.services.tier_service import TierService

        service = TierService()

        # Premium tier costs more per token
        basic_credits = service.estimate_credits(10000, is_premium=False)
        premium_credits = service.estimate_credits(10000, is_premium=True)

        # Premium should cost more
        assert premium_credits > basic_credits

    def test_estimate_credits_minimum_is_one(self):
        """Minimum credit estimate is 1."""
        from api.services.tier_service import TierService

        service = TierService()

        # Even very short text should cost at least 1 credit
        credits = service.estimate_credits(10, is_premium=False)
        assert credits >= 1


class TestFeatureMinTierMapping:
    """Tests for feature to minimum tier mapping."""

    def test_feature_min_tier_defined(self):
        """All features have minimum tier defined."""
        from api.services.tier_service import TierService

        expected_features = [
            "premium_workflow",
            "direct_publishing",
            "voice_transcription",
            "youtube_transcription",
            "priority_support",
        ]

        for feature in expected_features:
            assert feature in TierService.FEATURE_MIN_TIER

    def test_premium_workflow_is_free(self):
        """Premium workflow is available on free tier."""
        from api.services.tier_service import TierService

        assert TierService.FEATURE_MIN_TIER["premium_workflow"] == "free"

    def test_premium_features_require_pro_tier(self):
        """Premium features require pro tier."""
        from api.services.tier_service import TierService

        assert TierService.FEATURE_MIN_TIER["voice_transcription"] == "pro"
        assert TierService.FEATURE_MIN_TIER["youtube_transcription"] == "pro"
        assert TierService.FEATURE_MIN_TIER["priority_support"] == "pro"


class TestDefaultTextLimits:
    """Tests for default text limits per tier."""

    def test_text_limits_defined(self):
        """Text limits are defined for each tier."""
        from api.services.tier_service import TierService

        assert "free" in TierService.DEFAULT_TEXT_LIMITS
        assert "base" in TierService.DEFAULT_TEXT_LIMITS
        assert "pro" in TierService.DEFAULT_TEXT_LIMITS
        assert "max" in TierService.DEFAULT_TEXT_LIMITS

    def test_free_tier_has_lower_limit(self):
        """Free tier has lower text limit than pro/max."""
        from api.services.tier_service import TierService

        assert TierService.DEFAULT_TEXT_LIMITS["free"] == 50000
        assert TierService.DEFAULT_TEXT_LIMITS["pro"] == 100000

    def test_base_matches_free_limit(self):
        """Base tier has same limit as free."""
        from api.services.tier_service import TierService

        assert TierService.DEFAULT_TEXT_LIMITS["base"] == TierService.DEFAULT_TEXT_LIMITS["free"]


class TestWorkflowConfigSelection:
    """Tests for workflow config selection based on tier."""

    def test_workflow_config_returns_string(self):
        """get_workflow_config returns a config filename."""
        from api.services.tier_service import TierService

        service = TierService()

        # All tiers use premium workflow for best quality
        config = service.get_workflow_config(uuid4())
        assert config == "groq-premium.yaml"


class TestTierFeatureModel:
    """Tests for TierFeature database model."""

    def test_tier_feature_model_exists(self):
        """TierFeature model can be imported."""
        from runner.db.models import TierFeature, TierFeatureRead

        assert TierFeature is not None
        assert TierFeatureRead is not None

    def test_tier_feature_has_required_fields(self):
        """TierFeature has all required fields."""
        from runner.db.models import TierFeature

        # Check table name
        assert TierFeature.__tablename__ == "tier_features"

        # Check fields exist (will raise AttributeError if not)
        tier_feature_fields = TierFeature.model_fields

        assert "feature_key" in tier_feature_fields
        assert "enabled" in tier_feature_fields
        assert "config" in tier_feature_fields
        assert "tier_id" in tier_feature_fields


class TestTranscriptionFeatureGates:
    """Tests for feature gates on transcription routes."""

    def test_upload_route_imports_feature_gate(self):
        """Upload route imports FeatureNotAvailable."""
        from api.routes.v1.transcription import tier_service, FeatureNotAvailable

        assert tier_service is not None
        assert FeatureNotAvailable is not None

    def test_feature_locked_response_model(self):
        """FeatureLockedResponse model is defined."""
        from api.routes.v1.transcription import FeatureLockedResponse

        resp = FeatureLockedResponse(
            feature="youtube_transcription",
            current_tier="Free",
            required_tier="Pro",
            message="Upgrade required",
        )

        assert resp.error == "feature_locked"
        assert resp.feature == "youtube_transcription"
        assert resp.current_tier == "Free"
        assert resp.required_tier == "Pro"


class TestUsageRouteEstimate:
    """Tests for the credit estimate endpoint."""

    def test_estimate_request_model(self):
        """EstimateRequest model is defined."""
        from api.routes.v1.usage import EstimateRequest

        req = EstimateRequest(text_length=10000)
        assert req.text_length == 10000

    def test_estimate_response_model(self):
        """EstimateResponse model is defined."""
        from api.routes.v1.usage import EstimateResponse

        resp = EstimateResponse(
            text_length=10000,
            estimated_credits=5,
            credits_remaining=25,
            can_proceed=True,
        )

        assert resp.text_length == 10000
        assert resp.estimated_credits == 5
        assert resp.credits_remaining == 25
        assert resp.can_proceed is True


class TestUsageSummaryCredits:
    """Tests for credits in usage summary response."""

    def test_usage_summary_has_credits(self):
        """UsageSummaryResponse includes credits info."""
        from api.routes.v1.usage import CreditsInfo, FeaturesInfo, TierInfo

        credits = CreditsInfo(used=5, limit=30, remaining=25)
        assert credits.used == 5
        assert credits.limit == 30
        assert credits.remaining == 25

    def test_features_info_model(self):
        """FeaturesInfo model has all feature flags."""
        from api.routes.v1.usage import FeaturesInfo

        features = FeaturesInfo(
            premium_workflow=True,
            voice_transcription=True,
            youtube_transcription=False,
            priority_support=False,
            api_access=False,
            team_workspaces=False,
            text_limit=50000,
        )

        assert features.premium_workflow is True
        assert features.voice_transcription is True
        assert features.youtube_transcription is False
        assert features.text_limit == 50000

    def test_tier_info_model(self):
        """TierInfo model has name and slug."""
        from api.routes.v1.usage import TierInfo

        tier = TierInfo(name="Starter", slug="starter")
        assert tier.name == "Starter"
        assert tier.slug == "starter"
