"""Integration tests for voice profile data isolation.

Ensures users can only access:
1. System presets (is_preset=True, workspace_id=NULL)
2. Profiles in their own workspace

Run with: make test-int
"""

import pytest
from uuid import uuid4
from sqlmodel import Session, select

from runner.db.models import VoiceProfile, User, Workspace
from tests.db_utils import is_database_available

pytestmark = pytest.mark.skipif(
    not is_database_available(),
    reason="Database not available"
)


class TestVoiceProfileIsolation:
    """Test that voice profiles are properly isolated between workspaces."""

    def test_workspace_can_see_presets(self, test_engine, seeded_user):
        """Workspace A can see system preset profiles."""
        with Session(test_engine) as session:
            # Create workspace
            workspace = Workspace(
                id=uuid4(),
                name="Test Workspace",
                slug=f"test-{uuid4().hex[:8]}",
                owner_id=seeded_user.id,
            )
            session.add(workspace)

            # Create preset profile
            preset = VoiceProfile(
                id=uuid4(),
                name="System Preset",
                slug=f"preset-{uuid4().hex[:8]}",
                is_preset=True,
                user_id=None,
                workspace_id=None,
            )
            session.add(preset)
            session.commit()

            # Query as workspace would
            profiles = session.exec(
                select(VoiceProfile).where(
                    (VoiceProfile.workspace_id == workspace.id) |
                    (VoiceProfile.is_preset == True)
                )
            ).all()

            assert any(p.id == preset.id for p in profiles), \
                "Workspace should see system preset"

    def test_workspace_can_see_own_profiles(self, test_engine, seeded_user):
        """Workspace can see its own profiles."""
        with Session(test_engine) as session:
            # Create workspace
            workspace = Workspace(
                id=uuid4(),
                name="Test Workspace",
                slug=f"test-{uuid4().hex[:8]}",
                owner_id=seeded_user.id,
            )
            session.add(workspace)

            # Create workspace profile
            profile = VoiceProfile(
                id=uuid4(),
                name="My Profile",
                slug=f"my-{uuid4().hex[:8]}",
                is_preset=False,
                user_id=seeded_user.id,
                workspace_id=workspace.id,
            )
            session.add(profile)
            session.commit()

            # Query as workspace would
            profiles = session.exec(
                select(VoiceProfile).where(
                    (VoiceProfile.workspace_id == workspace.id) |
                    (VoiceProfile.is_preset == True)
                )
            ).all()

            assert any(p.id == profile.id for p in profiles), \
                "Workspace should see its own profile"

    def test_workspace_cannot_see_other_workspace_profiles(self, test_engine, seeded_user):
        """Workspace A cannot see workspace B's profiles."""
        with Session(test_engine) as session:
            # Create workspace A
            workspace_a = Workspace(
                id=uuid4(),
                name="Workspace A",
                slug=f"ws-a-{uuid4().hex[:8]}",
                owner_id=seeded_user.id,
            )
            session.add(workspace_a)

            # Create other user and workspace B
            other_user = User(
                id=uuid4(),
                email=f"other-{uuid4().hex[:8]}@test.com",
                is_active=True,
                is_superuser=False,
            )
            session.add(other_user)
            session.commit()

            workspace_b = Workspace(
                id=uuid4(),
                name="Workspace B",
                slug=f"ws-b-{uuid4().hex[:8]}",
                owner_id=other_user.id,
            )
            session.add(workspace_b)

            # Create secret profile in workspace B
            secret_profile = VoiceProfile(
                id=uuid4(),
                name="Secret Profile",
                slug=f"secret-{uuid4().hex[:8]}",
                is_preset=False,
                user_id=other_user.id,
                workspace_id=workspace_b.id,
            )
            session.add(secret_profile)
            session.commit()

            # Query as workspace A would
            profiles_visible_to_a = session.exec(
                select(VoiceProfile).where(
                    (VoiceProfile.workspace_id == workspace_a.id) |
                    (VoiceProfile.is_preset == True)
                )
            ).all()

            assert not any(p.id == secret_profile.id for p in profiles_visible_to_a), \
                "Workspace A should NOT see Workspace B's profile"

    def test_full_isolation_scenario(self, test_engine, seeded_user):
        """Full test: workspace A sees only presets + own profiles."""
        with Session(test_engine) as session:
            # Create workspace A
            workspace_a = Workspace(
                id=uuid4(),
                name="Workspace A",
                slug=f"ws-a-{uuid4().hex[:8]}",
                owner_id=seeded_user.id,
            )
            session.add(workspace_a)

            # Create other user and workspace B
            other_user = User(
                id=uuid4(),
                email=f"other-{uuid4().hex[:8]}@test.com",
                is_active=True,
                is_superuser=False,
            )
            session.add(other_user)
            session.commit()

            workspace_b = Workspace(
                id=uuid4(),
                name="Workspace B",
                slug=f"ws-b-{uuid4().hex[:8]}",
                owner_id=other_user.id,
            )
            session.add(workspace_b)

            # Create preset (visible to all)
            preset = VoiceProfile(
                id=uuid4(),
                name="System Preset",
                slug=f"preset-{uuid4().hex[:8]}",
                is_preset=True,
                user_id=None,
                workspace_id=None,
            )
            session.add(preset)

            # Create profile in workspace A
            profile_a = VoiceProfile(
                id=uuid4(),
                name="Profile A",
                slug=f"profile-a-{uuid4().hex[:8]}",
                is_preset=False,
                user_id=seeded_user.id,
                workspace_id=workspace_a.id,
            )
            session.add(profile_a)

            # Create profile in workspace B
            profile_b = VoiceProfile(
                id=uuid4(),
                name="Profile B",
                slug=f"profile-b-{uuid4().hex[:8]}",
                is_preset=False,
                user_id=other_user.id,
                workspace_id=workspace_b.id,
            )
            session.add(profile_b)
            session.commit()

            # Query as workspace A
            profiles_a = session.exec(
                select(VoiceProfile).where(
                    (VoiceProfile.workspace_id == workspace_a.id) |
                    (VoiceProfile.is_preset == True)
                )
            ).all()
            ids_visible_to_a = {p.id for p in profiles_a}

            assert preset.id in ids_visible_to_a, "A should see preset"
            assert profile_a.id in ids_visible_to_a, "A should see own profile"
            assert profile_b.id not in ids_visible_to_a, "A should NOT see B's profile"

            # Query as workspace B
            profiles_b = session.exec(
                select(VoiceProfile).where(
                    (VoiceProfile.workspace_id == workspace_b.id) |
                    (VoiceProfile.is_preset == True)
                )
            ).all()
            ids_visible_to_b = {p.id for p in profiles_b}

            assert preset.id in ids_visible_to_b, "B should see preset"
            assert profile_b.id in ids_visible_to_b, "B should see own profile"
            assert profile_a.id not in ids_visible_to_b, "B should NOT see A's profile"


class TestPresetProfiles:
    """Test system preset behavior."""

    def test_preset_has_no_owner(self, test_engine):
        """System presets have no user_id or workspace_id."""
        with Session(test_engine) as session:
            preset = VoiceProfile(
                id=uuid4(),
                name="System Preset",
                slug=f"preset-{uuid4().hex[:8]}",
                is_preset=True,
                user_id=None,
                workspace_id=None,
            )
            session.add(preset)
            session.commit()
            session.refresh(preset)

            assert preset.user_id is None
            assert preset.workspace_id is None
            assert preset.is_preset is True

    def test_workspace_profile_has_owner(self, test_engine, seeded_user):
        """Workspace profiles have user_id and workspace_id."""
        with Session(test_engine) as session:
            workspace = Workspace(
                id=uuid4(),
                name="Test Workspace",
                slug=f"test-{uuid4().hex[:8]}",
                owner_id=seeded_user.id,
            )
            session.add(workspace)

            profile = VoiceProfile(
                id=uuid4(),
                name="My Profile",
                slug=f"my-{uuid4().hex[:8]}",
                is_preset=False,
                user_id=seeded_user.id,
                workspace_id=workspace.id,
            )
            session.add(profile)
            session.commit()
            session.refresh(profile)

            assert profile.user_id == seeded_user.id
            assert profile.workspace_id == workspace.id
            assert profile.is_preset is False
