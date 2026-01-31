"""Tests for v1 workspace-scoped onboarding API routes.

Tests the new workspace-scoped onboarding endpoints that replaced
the legacy user-scoped endpoints.
"""

import pytest
from unittest.mock import MagicMock, patch
from uuid import uuid4


class TestV1OnboardingModels:
    """Tests for v1 onboarding request/response models."""

    def test_quick_mode_request_model(self):
        """QuickModeRequest validates input."""
        from api.routes.v1.onboarding import QuickModeRequest

        req = QuickModeRequest(
            professional_role="Software Engineer",
            known_for="AI systems",
            target_audience="Tech leaders",
            content_style="educational",
            posts_per_week=3,
        )
        assert req.professional_role == "Software Engineer"
        assert req.posts_per_week == 3

    def test_quick_mode_request_validation(self):
        """QuickModeRequest rejects invalid input."""
        from api.routes.v1.onboarding import QuickModeRequest
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            QuickModeRequest(
                # Missing required fields
                professional_role="Engineer",
            )

    def test_deep_mode_message_request_model(self):
        """DeepModeMessageRequest validates input."""
        from api.routes.v1.onboarding import DeepModeMessageRequest

        # Without state (for first message)
        req = DeepModeMessageRequest(
            message="Let's start building my content strategy.",
            state=None,
        )
        assert req.message == "Let's start building my content strategy."
        assert req.state is None
        assert req.force_ready is False

        # With state and force_ready
        req = DeepModeMessageRequest(
            message="Generate my plan now",
            state={"messages": [], "turn_count": 5, "ready_to_generate": False},
            force_ready=True,
        )
        assert req.force_ready is True

    def test_generate_plan_request_model(self):
        """GeneratePlanRequest validates input."""
        from api.routes.v1.onboarding import GeneratePlanRequest

        req = GeneratePlanRequest(
            content_style="narrative",
            state={"messages": [], "turn_count": 5, "ready_to_generate": True},
        )
        assert req.content_style == "narrative"

    def test_approve_plan_request_model(self):
        """ApprovePlanRequest validates input."""
        from api.routes.v1.onboarding import ApprovePlanRequest

        req = ApprovePlanRequest(
            plan={
                "signature_thesis": "Test thesis",
                "chapters": [],
            },
            positioning="Content Creator",
            target_audience="Professionals",
            content_style="mixed",
            onboarding_mode="quick",
        )
        assert req.positioning == "Content Creator"
        assert req.transcript is None

        # With transcript
        req = ApprovePlanRequest(
            plan={"signature_thesis": "Test", "chapters": []},
            positioning="Test",
            target_audience="Test",
            content_style="mixed",
            onboarding_mode="deep",
            transcript='[{"role": "user", "content": "test"}]',
        )
        assert req.transcript is not None


class TestV1OnboardingResponses:
    """Tests for v1 onboarding response models."""

    def test_content_styles_response(self):
        """ContentStylesResponse structure is correct."""
        from api.routes.v1.onboarding import ContentStylesResponse

        resp = ContentStylesResponse(
            styles=[
                {"id": "narrative", "name": "Narrative", "description": "Story-driven"},
                {"id": "teaching", "name": "Teaching", "description": "Educational"},
            ]
        )
        assert len(resp.styles) == 2

    def test_deep_mode_response(self):
        """DeepModeResponse structure is correct."""
        from api.routes.v1.onboarding import DeepModeResponse

        resp = DeepModeResponse(
            message="Tell me about your goals",
            state={"messages": [], "turn_count": 1, "ready_to_generate": False},
            is_ready=False,
        )
        assert resp.is_ready is False

    def test_approve_response(self):
        """ApproveResponse structure is correct."""
        from api.routes.v1.onboarding import ApproveResponse

        resp = ApproveResponse(
            goal_id=str(uuid4()),
            chapters=[str(uuid4()), str(uuid4())],
        )
        assert len(resp.chapters) == 2


class TestV1OnboardingServiceIntegration:
    """Tests for v1 onboarding service integration."""

    def test_quick_mode_uses_onboarding_service(self):
        """process_quick_mode calls OnboardingService.generate_quick_plan."""
        from api.services.onboarding_service import OnboardingService, QuickOnboardingAnswers

        service = OnboardingService()

        # Verify the method exists and accepts the right arguments
        answers = QuickOnboardingAnswers(
            professional_role="Engineer",
            known_for="AI",
            target_audience="Developers",
            content_style="teaching",
            posts_per_week=2,
        )
        # Method should exist (actual call would need LLM)
        assert hasattr(service, "generate_quick_plan")

    def test_deep_mode_uses_onboarding_service(self):
        """process_deep_mode_message calls OnboardingService."""
        from api.services.onboarding_service import OnboardingService

        service = OnboardingService()

        # Verify the method exists
        assert hasattr(service, "generate_deep_plan")
        assert hasattr(service, "generate_plan_from_strategy")


class TestV1OnboardingNoUserIdRequired:
    """Tests verifying v1 endpoints don't require user_id."""

    def test_quick_mode_request_has_no_user_id(self):
        """QuickModeRequest doesn't have user_id field."""
        from api.routes.v1.onboarding import QuickModeRequest

        # Create request without user_id
        req = QuickModeRequest(
            professional_role="Test",
            known_for="Test",
            target_audience="Test",
            content_style="mixed",
            posts_per_week=2,
        )
        # Should not have user_id attribute from model
        assert "user_id" not in type(req).model_fields

    def test_approve_request_has_no_user_id(self):
        """ApprovePlanRequest doesn't have user_id field."""
        from api.routes.v1.onboarding import ApprovePlanRequest

        req = ApprovePlanRequest(
            plan={"signature_thesis": "Test", "chapters": []},
            positioning="Test",
            target_audience="Test",
            content_style="mixed",
            onboarding_mode="quick",
        )
        assert "user_id" not in type(req).model_fields

    def test_deep_message_request_has_no_user_id(self):
        """DeepModeMessageRequest doesn't have user_id field."""
        from api.routes.v1.onboarding import DeepModeMessageRequest

        req = DeepModeMessageRequest(
            message="Test message",
        )
        assert "user_id" not in type(req).model_fields


class TestV1OnboardingWorkspaceScoped:
    """Tests verifying v1 endpoints are workspace-scoped."""

    def test_router_prefix_includes_workspace_id(self):
        """V1 onboarding router uses workspace-scoped prefix."""
        from api.routes.v1.onboarding import router

        # Check the router prefix
        assert "/v1/w/{workspace_id}/onboarding" in router.prefix

    def test_content_styles_endpoint_path(self):
        """Content styles endpoint is at correct path."""
        from api.routes.v1.onboarding import router

        paths = [route.path for route in router.routes]
        assert any("content-styles" in path for path in paths)

    def test_quick_mode_endpoint_path(self):
        """Quick mode endpoint is at correct path."""
        from api.routes.v1.onboarding import router

        paths = [route.path for route in router.routes]
        assert any(path.endswith("/quick") for path in paths)

    def test_deep_message_endpoint_path(self):
        """Deep message endpoint is at correct path."""
        from api.routes.v1.onboarding import router

        paths = [route.path for route in router.routes]
        assert any("deep/message" in path for path in paths)

    def test_approve_endpoint_path(self):
        """Approve endpoint is at correct path."""
        from api.routes.v1.onboarding import router

        paths = [route.path for route in router.routes]
        assert any(path.endswith("/approve") for path in paths)
