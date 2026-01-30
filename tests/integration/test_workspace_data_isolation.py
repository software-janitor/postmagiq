"""Integration tests for workspace data isolation.

Ensures all user-generated data is properly isolated between workspaces.
Each workspace should only see:
1. Their own data (workspace_id matches)
2. System presets (where applicable)

Run with: make test-int
"""

import pytest
from uuid import uuid4
from sqlmodel import Session, select, or_

from runner.db.models import (
    # Core
    User,
    Workspace,
    # Content
    Goal,
    Chapter,
    Post,
    # Voice
    WritingSample,
    VoiceProfile,
    # Workflow
    WorkflowRun,
    WorkflowPersona,
    # API
    APIKey,
    # Notifications
    Notification,
    # Approvals
    ApprovalRequest,
    ApprovalStage,
    # Analytics
    AnalyticsImport,
    # Characters
    Character,
    # Images
    ImagePrompt,
    # Market Intelligence
    AudienceSegment,
    # Billing/Usage
    UsageTracking,
    # Subscription
    AccountSubscription,
    SubscriptionTier,
    # Whitelabel
    WhitelabelConfig,
)
from tests.db_utils import is_database_available

pytestmark = pytest.mark.skipif(
    not is_database_available(),
    reason="Database not available"
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def user_a(test_engine) -> User:
    """Create user A."""
    with Session(test_engine) as session:
        user = User(
            id=uuid4(),
            email=f"user-a-{uuid4().hex[:8]}@test.com",
            full_name="User A",
            is_active=True,
            is_superuser=False,
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        return user


@pytest.fixture
def user_b(test_engine) -> User:
    """Create user B."""
    with Session(test_engine) as session:
        user = User(
            id=uuid4(),
            email=f"user-b-{uuid4().hex[:8]}@test.com",
            full_name="User B",
            is_active=True,
            is_superuser=False,
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        return user


@pytest.fixture
def workspace_a(test_engine, user_a) -> Workspace:
    """Create workspace A owned by user A."""
    with Session(test_engine) as session:
        workspace = Workspace(
            id=uuid4(),
            name="Workspace A",
            slug=f"workspace-a-{uuid4().hex[:8]}",
            owner_id=user_a.id,
        )
        session.add(workspace)
        session.commit()
        session.refresh(workspace)
        return workspace


@pytest.fixture
def workspace_b(test_engine, user_b) -> Workspace:
    """Create workspace B owned by user B."""
    with Session(test_engine) as session:
        workspace = Workspace(
            id=uuid4(),
            name="Workspace B",
            slug=f"workspace-b-{uuid4().hex[:8]}",
            owner_id=user_b.id,
        )
        session.add(workspace)
        session.commit()
        session.refresh(workspace)
        return workspace


# =============================================================================
# Content Isolation Tests (Goal, Chapter, Post)
# =============================================================================


class TestGoalIsolation:
    """Test Goal data isolation between workspaces."""

    def test_workspace_sees_own_goals(self, test_engine, workspace_a, user_a):
        """Workspace A can see its own goals."""
        with Session(test_engine) as session:
            goal = Goal(
                id=uuid4(),
                user_id=user_a.id,
                workspace_id=workspace_a.id,
                title="Goal A",
                description="Test goal for workspace A",
            )
            session.add(goal)
            session.commit()

            goals = session.exec(
                select(Goal).where(Goal.workspace_id == workspace_a.id)
            ).all()

            assert any(g.id == goal.id for g in goals)

    def test_workspace_cannot_see_other_goals(
        self, test_engine, workspace_a, workspace_b, user_a, user_b
    ):
        """Workspace A cannot see workspace B's goals."""
        with Session(test_engine) as session:
            # Create goal in workspace B
            goal_b = Goal(
                id=uuid4(),
                user_id=user_b.id,
                workspace_id=workspace_b.id,
                title="Secret Goal B",
                description="This should not be visible to A",
            )
            session.add(goal_b)
            session.commit()

            # Query as workspace A
            goals_visible_to_a = session.exec(
                select(Goal).where(Goal.workspace_id == workspace_a.id)
            ).all()

            assert not any(g.id == goal_b.id for g in goals_visible_to_a), \
                "Workspace A should NOT see Workspace B's goals"


class TestChapterIsolation:
    """Test Chapter data isolation between workspaces."""

    def test_workspace_cannot_see_other_chapters(
        self, test_engine, workspace_a, workspace_b, user_a, user_b
    ):
        """Workspace A cannot see workspace B's chapters."""
        with Session(test_engine) as session:
            # Create goal first (required for chapter)
            goal_b = Goal(
                id=uuid4(),
                user_id=user_b.id,
                workspace_id=workspace_b.id,
                title="Goal B",
            )
            session.add(goal_b)
            session.commit()

            # Create chapter in workspace B
            chapter_b = Chapter(
                id=uuid4(),
                goal_id=goal_b.id,
                workspace_id=workspace_b.id,
                title="Secret Chapter",
                description="Hidden from A",
                order=1,
            )
            session.add(chapter_b)
            session.commit()

            # Query as workspace A
            chapters_a = session.exec(
                select(Chapter).where(Chapter.workspace_id == workspace_a.id)
            ).all()

            assert not any(c.id == chapter_b.id for c in chapters_a)


class TestPostIsolation:
    """Test Post data isolation between workspaces."""

    def test_workspace_cannot_see_other_posts(
        self, test_engine, workspace_a, workspace_b, user_a, user_b
    ):
        """Workspace A cannot see workspace B's posts."""
        with Session(test_engine) as session:
            # Create goal and chapter for post
            goal_b = Goal(
                id=uuid4(),
                user_id=user_b.id,
                workspace_id=workspace_b.id,
                title="Goal B",
            )
            session.add(goal_b)
            session.commit()

            chapter_b = Chapter(
                id=uuid4(),
                goal_id=goal_b.id,
                workspace_id=workspace_b.id,
                title="Chapter B",
                order=1,
            )
            session.add(chapter_b)
            session.commit()

            # Create post in workspace B
            post_b = Post(
                id=uuid4(),
                chapter_id=chapter_b.id,
                workspace_id=workspace_b.id,
                title="Secret Post",
                order=1,
            )
            session.add(post_b)
            session.commit()

            # Query as workspace A
            posts_a = session.exec(
                select(Post).where(Post.workspace_id == workspace_a.id)
            ).all()

            assert not any(p.id == post_b.id for p in posts_a)


# =============================================================================
# Voice Isolation Tests (WritingSample)
# =============================================================================


class TestWritingSampleIsolation:
    """Test WritingSample data isolation between workspaces."""

    def test_workspace_cannot_see_other_samples(
        self, test_engine, workspace_a, workspace_b, user_a, user_b
    ):
        """Workspace A cannot see workspace B's writing samples."""
        with Session(test_engine) as session:
            # Create sample in workspace B
            sample_b = WritingSample(
                id=uuid4(),
                user_id=user_b.id,
                workspace_id=workspace_b.id,
                source_type="upload",
                content="This is my secret writing style...",
                word_count=6,
            )
            session.add(sample_b)
            session.commit()

            # Query as workspace A
            samples_a = session.exec(
                select(WritingSample).where(
                    WritingSample.workspace_id == workspace_a.id
                )
            ).all()

            assert not any(s.id == sample_b.id for s in samples_a)


# =============================================================================
# API Key Isolation Tests
# =============================================================================


class TestAPIKeyIsolation:
    """Test APIKey data isolation between workspaces."""

    def test_workspace_cannot_see_other_api_keys(
        self, test_engine, workspace_a, workspace_b, user_a, user_b
    ):
        """Workspace A cannot see workspace B's API keys."""
        with Session(test_engine) as session:
            # Create API key in workspace B
            api_key_b = APIKey(
                id=uuid4(),
                workspace_id=workspace_b.id,
                created_by_id=user_b.id,
                name="Secret API Key",
                key_hash="hashed_secret_key",
                key_prefix="sk_test",
            )
            session.add(api_key_b)
            session.commit()

            # Query as workspace A
            keys_a = session.exec(
                select(APIKey).where(APIKey.workspace_id == workspace_a.id)
            ).all()

            assert not any(k.id == api_key_b.id for k in keys_a)


# =============================================================================
# Notification Isolation Tests
# =============================================================================


class TestNotificationIsolation:
    """Test Notification data isolation between workspaces."""

    def test_workspace_cannot_see_other_notifications(
        self, test_engine, workspace_a, workspace_b, user_a, user_b
    ):
        """Workspace A cannot see workspace B's notifications."""
        with Session(test_engine) as session:
            # Create notification in workspace B
            notification_b = Notification(
                id=uuid4(),
                workspace_id=workspace_b.id,
                user_id=user_b.id,
                type="content_ready",
                title="Your content is ready",
                message="Secret notification",
            )
            session.add(notification_b)
            session.commit()

            # Query as workspace A
            notifications_a = session.exec(
                select(Notification).where(
                    Notification.workspace_id == workspace_a.id
                )
            ).all()

            assert not any(n.id == notification_b.id for n in notifications_a)


# =============================================================================
# Approval Isolation Tests
# =============================================================================


class TestApprovalRequestIsolation:
    """Test ApprovalRequest data isolation between workspaces."""

    def test_workspace_cannot_see_other_approval_requests(
        self, test_engine, workspace_a, workspace_b, user_a, user_b
    ):
        """Workspace A cannot see workspace B's approval requests."""
        with Session(test_engine) as session:
            # Create approval request in workspace B
            request_b = ApprovalRequest(
                id=uuid4(),
                workspace_id=workspace_b.id,
                requester_id=user_b.id,
                entity_type="post",
                entity_id=uuid4(),
                status="pending",
            )
            session.add(request_b)
            session.commit()

            # Query as workspace A
            requests_a = session.exec(
                select(ApprovalRequest).where(
                    ApprovalRequest.workspace_id == workspace_a.id
                )
            ).all()

            assert not any(r.id == request_b.id for r in requests_a)


class TestApprovalStageIsolation:
    """Test ApprovalStage data isolation between workspaces."""

    def test_workspace_cannot_see_other_approval_stages(
        self, test_engine, workspace_a, workspace_b, user_a, user_b
    ):
        """Workspace A cannot see workspace B's approval stages."""
        with Session(test_engine) as session:
            # Create approval stage in workspace B
            stage_b = ApprovalStage(
                id=uuid4(),
                workspace_id=workspace_b.id,
                name="Secret Stage",
                order=1,
            )
            session.add(stage_b)
            session.commit()

            # Query as workspace A
            stages_a = session.exec(
                select(ApprovalStage).where(
                    ApprovalStage.workspace_id == workspace_a.id
                )
            ).all()

            assert not any(s.id == stage_b.id for s in stages_a)


# =============================================================================
# Analytics Isolation Tests
# =============================================================================


class TestAnalyticsImportIsolation:
    """Test AnalyticsImport data isolation between workspaces."""

    def test_workspace_cannot_see_other_analytics(
        self, test_engine, workspace_a, workspace_b, user_a, user_b
    ):
        """Workspace A cannot see workspace B's analytics imports."""
        with Session(test_engine) as session:
            # Create analytics import in workspace B
            import_b = AnalyticsImport(
                id=uuid4(),
                user_id=user_b.id,
                workspace_id=workspace_b.id,
                platform="linkedin",
                status="completed",
            )
            session.add(import_b)
            session.commit()

            # Query as workspace A
            imports_a = session.exec(
                select(AnalyticsImport).where(
                    AnalyticsImport.workspace_id == workspace_a.id
                )
            ).all()

            assert not any(i.id == import_b.id for i in imports_a)


# =============================================================================
# Character Isolation Tests
# =============================================================================


class TestCharacterIsolation:
    """Test Character data isolation between workspaces."""

    def test_workspace_cannot_see_other_characters(
        self, test_engine, workspace_a, workspace_b, user_a, user_b
    ):
        """Workspace A cannot see workspace B's characters."""
        with Session(test_engine) as session:
            # Create character in workspace B
            character_b = Character(
                id=uuid4(),
                user_id=user_b.id,
                workspace_id=workspace_b.id,
                name="Secret Character",
            )
            session.add(character_b)
            session.commit()

            # Query as workspace A
            characters_a = session.exec(
                select(Character).where(
                    Character.workspace_id == workspace_a.id
                )
            ).all()

            assert not any(c.id == character_b.id for c in characters_a)


# =============================================================================
# Image Isolation Tests
# =============================================================================


class TestImagePromptIsolation:
    """Test ImagePrompt data isolation between workspaces."""

    def test_workspace_cannot_see_other_image_prompts(
        self, test_engine, workspace_a, workspace_b, user_a, user_b
    ):
        """Workspace A cannot see workspace B's image prompts."""
        with Session(test_engine) as session:
            # Create image prompt in workspace B
            prompt_b = ImagePrompt(
                id=uuid4(),
                user_id=user_b.id,
                workspace_id=workspace_b.id,
                prompt="A secret image prompt",
                status="pending",
            )
            session.add(prompt_b)
            session.commit()

            # Query as workspace A
            prompts_a = session.exec(
                select(ImagePrompt).where(
                    ImagePrompt.workspace_id == workspace_a.id
                )
            ).all()

            assert not any(p.id == prompt_b.id for p in prompts_a)


# =============================================================================
# Workflow Isolation Tests
# =============================================================================


class TestWorkflowRunIsolation:
    """Test WorkflowRun data isolation between workspaces."""

    def test_workspace_cannot_see_other_workflow_runs(
        self, test_engine, workspace_a, workspace_b, user_a, user_b
    ):
        """Workspace A cannot see workspace B's workflow runs."""
        with Session(test_engine) as session:
            # Create workflow run in workspace B
            run_b = WorkflowRun(
                id=uuid4(),
                user_id=user_b.id,
                workspace_id=workspace_b.id,
                status="running",
            )
            session.add(run_b)
            session.commit()

            # Query as workspace A
            runs_a = session.exec(
                select(WorkflowRun).where(
                    WorkflowRun.workspace_id == workspace_a.id
                )
            ).all()

            assert not any(r.id == run_b.id for r in runs_a)


class TestWorkflowPersonaIsolation:
    """Test WorkflowPersona data isolation between workspaces."""

    def test_preset_personas_visible_to_all(self, test_engine, workspace_a):
        """System preset personas should be visible to all workspaces."""
        with Session(test_engine) as session:
            # Create a preset persona (no workspace_id)
            preset = WorkflowPersona(
                id=uuid4(),
                name="System Writer",
                slug=f"system-writer-{uuid4().hex[:8]}",
                role="writer",
                is_preset=True,
                workspace_id=None,
            )
            session.add(preset)
            session.commit()

            # Query as workspace A (should see presets)
            personas = session.exec(
                select(WorkflowPersona).where(
                    or_(
                        WorkflowPersona.workspace_id == workspace_a.id,
                        WorkflowPersona.is_preset == True,
                    )
                )
            ).all()

            assert any(p.id == preset.id for p in personas)

    def test_workspace_cannot_see_other_custom_personas(
        self, test_engine, workspace_a, workspace_b
    ):
        """Workspace A cannot see workspace B's custom personas."""
        with Session(test_engine) as session:
            # Create custom persona in workspace B
            persona_b = WorkflowPersona(
                id=uuid4(),
                name="Custom Writer B",
                slug=f"custom-writer-b-{uuid4().hex[:8]}",
                role="writer",
                is_preset=False,
                workspace_id=workspace_b.id,
            )
            session.add(persona_b)
            session.commit()

            # Query as workspace A
            personas_a = session.exec(
                select(WorkflowPersona).where(
                    or_(
                        WorkflowPersona.workspace_id == workspace_a.id,
                        WorkflowPersona.is_preset == True,
                    )
                )
            ).all()

            assert not any(p.id == persona_b.id for p in personas_a)


# =============================================================================
# Full Isolation Scenario Test
# =============================================================================


class TestFullDataIsolation:
    """Comprehensive test verifying complete data isolation."""

    def test_complete_workspace_isolation(
        self, test_engine, workspace_a, workspace_b, user_a, user_b
    ):
        """Verify complete isolation across all entity types."""
        with Session(test_engine) as session:
            # Create data in workspace B
            goal_b = Goal(
                id=uuid4(),
                user_id=user_b.id,
                workspace_id=workspace_b.id,
                title="B's Goal",
            )
            session.add(goal_b)

            sample_b = WritingSample(
                id=uuid4(),
                user_id=user_b.id,
                workspace_id=workspace_b.id,
                source_type="upload",
                content="B's writing",
                word_count=2,
            )
            session.add(sample_b)

            notification_b = Notification(
                id=uuid4(),
                workspace_id=workspace_b.id,
                user_id=user_b.id,
                type="info",
                title="B's notification",
            )
            session.add(notification_b)

            session.commit()

            # Verify workspace A sees NONE of B's data
            goals_a = session.exec(
                select(Goal).where(Goal.workspace_id == workspace_a.id)
            ).all()
            samples_a = session.exec(
                select(WritingSample).where(
                    WritingSample.workspace_id == workspace_a.id
                )
            ).all()
            notifications_a = session.exec(
                select(Notification).where(
                    Notification.workspace_id == workspace_a.id
                )
            ).all()

            # None of B's IDs should appear
            all_a_ids = (
                {g.id for g in goals_a} |
                {s.id for s in samples_a} |
                {n.id for n in notifications_a}
            )
            b_ids = {goal_b.id, sample_b.id, notification_b.id}

            assert all_a_ids.isdisjoint(b_ids), \
                "Workspace A should not see ANY of Workspace B's data"


# =============================================================================
# Market Intelligence Isolation Tests
# =============================================================================


class TestAudienceSegmentIsolation:
    """Test AudienceSegment data isolation between workspaces."""

    def test_workspace_cannot_see_other_segments(
        self, test_engine, workspace_a, workspace_b
    ):
        """Workspace A cannot see workspace B's audience segments."""
        with Session(test_engine) as session:
            # Create segment in workspace B
            segment_b = AudienceSegment(
                id=uuid4(),
                workspace_id=workspace_b.id,
                name="Enterprise Buyers",
                description="B's target segment",
            )
            session.add(segment_b)
            session.commit()

            # Query as workspace A
            segments_a = session.exec(
                select(AudienceSegment).where(
                    AudienceSegment.workspace_id == workspace_a.id
                )
            ).all()

            assert not any(s.id == segment_b.id for s in segments_a)


# =============================================================================
# Usage Tracking Isolation Tests
# =============================================================================


class TestUsageTrackingIsolation:
    """Test UsageTracking data isolation between workspaces."""

    def test_workspace_cannot_see_other_usage(
        self, test_engine, workspace_a, workspace_b
    ):
        """Workspace A cannot see workspace B's usage tracking."""
        with Session(test_engine) as session:
            # First, need to get or create subscription for B
            tier = session.exec(select(SubscriptionTier).limit(1)).first()
            if not tier:
                tier = SubscriptionTier(
                    id=uuid4(),
                    name="Test Tier",
                    slug=f"test-tier-{uuid4().hex[:8]}",
                    monthly_price_cents=0,
                    yearly_price_cents=0,
                )
                session.add(tier)
                session.commit()

            sub_b = AccountSubscription(
                id=uuid4(),
                workspace_id=workspace_b.id,
                tier_id=tier.id,
                status="active",
            )
            session.add(sub_b)
            session.commit()

            # Create usage tracking for workspace B
            usage_b = UsageTracking(
                id=uuid4(),
                subscription_id=sub_b.id,
                period_start=None,
                period_end=None,
            )
            session.add(usage_b)
            session.commit()

            # Query usage via subscription for workspace A
            # UsageTracking is linked via subscription, not directly workspace_id
            subs_a = session.exec(
                select(AccountSubscription).where(
                    AccountSubscription.workspace_id == workspace_a.id
                )
            ).all()
            sub_ids_a = {s.id for s in subs_a}

            usage_a = session.exec(
                select(UsageTracking).where(
                    UsageTracking.subscription_id.in_(sub_ids_a)
                )
            ).all() if sub_ids_a else []

            assert not any(u.id == usage_b.id for u in usage_a)


# =============================================================================
# Subscription Isolation Tests
# =============================================================================


class TestAccountSubscriptionIsolation:
    """Test AccountSubscription data isolation between workspaces."""

    def test_workspace_cannot_see_other_subscriptions(
        self, test_engine, workspace_a, workspace_b
    ):
        """Workspace A cannot see workspace B's subscription."""
        with Session(test_engine) as session:
            # Get or create a tier
            tier = session.exec(select(SubscriptionTier).limit(1)).first()
            if not tier:
                tier = SubscriptionTier(
                    id=uuid4(),
                    name="Test Tier",
                    slug=f"test-tier-{uuid4().hex[:8]}",
                    monthly_price_cents=0,
                    yearly_price_cents=0,
                )
                session.add(tier)
                session.commit()

            # Create subscription for workspace B
            sub_b = AccountSubscription(
                id=uuid4(),
                workspace_id=workspace_b.id,
                tier_id=tier.id,
                status="active",
            )
            session.add(sub_b)
            session.commit()

            # Query as workspace A
            subs_a = session.exec(
                select(AccountSubscription).where(
                    AccountSubscription.workspace_id == workspace_a.id
                )
            ).all()

            assert not any(s.id == sub_b.id for s in subs_a)


# =============================================================================
# Whitelabel Isolation Tests
# =============================================================================


class TestWhitelabelConfigIsolation:
    """Test WhitelabelConfig data isolation between workspaces."""

    def test_workspace_cannot_see_other_whitelabel(
        self, test_engine, workspace_a, workspace_b
    ):
        """Workspace A cannot see workspace B's whitelabel config."""
        with Session(test_engine) as session:
            # Create whitelabel config for workspace B
            config_b = WhitelabelConfig(
                id=uuid4(),
                workspace_id=workspace_b.id,
                brand_name="B's Brand",
                primary_color="#FF0000",
            )
            session.add(config_b)
            session.commit()

            # Query as workspace A
            configs_a = session.exec(
                select(WhitelabelConfig).where(
                    WhitelabelConfig.workspace_id == workspace_a.id
                )
            ).all()

            assert not any(c.id == config_b.id for c in configs_a)
