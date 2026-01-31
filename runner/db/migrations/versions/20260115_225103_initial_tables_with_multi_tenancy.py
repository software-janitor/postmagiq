"""Initial tables with multi-tenancy.

Revision ID: 001_initial
Revises:
Create Date: 2026-01-15

Creates all tables for the workflow orchestrator with multi-tenancy support.
All user-scoped tables include workspace_id (nullable for migration compatibility).
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ==========================================================================
    # Core Tables
    # ==========================================================================

    # Users table
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("full_name", sa.String(), nullable=True),
        sa.Column("password_hash", sa.String(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
        sa.Column("is_superuser", sa.Boolean(), nullable=False, default=False),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    # Workspaces table
    op.create_table(
        "workspaces",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("slug", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("settings", postgresql.JSON(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_workspaces_name", "workspaces", ["name"])
    op.create_index("ix_workspaces_slug", "workspaces", ["slug"], unique=True)
    op.create_index("ix_workspaces_owner_id", "workspaces", ["owner_id"])

    # Workspace memberships table
    op.create_table(
        "workspace_memberships",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("role", sa.String(), nullable=False, default="viewer"),
        sa.Column("invite_status", sa.String(), nullable=False, default="pending"),
        sa.Column("invite_token", sa.String(), nullable=True),
        sa.Column("invited_at", sa.DateTime(), nullable=True),
        sa.Column("accepted_at", sa.DateTime(), nullable=True),
        sa.Column("invited_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["invited_by_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_workspace_memberships_workspace_id",
        "workspace_memberships",
        ["workspace_id"],
    )
    op.create_index(
        "ix_workspace_memberships_user_id", "workspace_memberships", ["user_id"]
    )
    op.create_index(
        "ix_workspace_memberships_email", "workspace_memberships", ["email"]
    )
    op.create_index(
        "ix_workspace_memberships_invite_token",
        "workspace_memberships",
        ["invite_token"],
    )

    # Active sessions table
    op.create_table(
        "active_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("token_jti", sa.String(), nullable=False),
        sa.Column("user_agent", sa.String(), nullable=True),
        sa.Column("ip_address", sa.String(), nullable=True),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(), nullable=True, server_default=sa.func.now()
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_active_sessions_user_id", "active_sessions", ["user_id"])
    op.create_index(
        "ix_active_sessions_token_jti", "active_sessions", ["token_jti"], unique=True
    )

    # Platforms table
    op.create_table(
        "platforms",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("icon", sa.String(), nullable=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_platforms_name", "platforms", ["name"])
    op.create_index("ix_platforms_user_id", "platforms", ["user_id"])
    op.create_index("ix_platforms_workspace_id", "platforms", ["workspace_id"])

    # ==========================================================================
    # Content Tables
    # ==========================================================================

    # Voice profiles table
    op.create_table(
        "voice_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("tone", sa.String(), nullable=True),
        sa.Column("style_notes", sa.String(), nullable=True),
        sa.Column("vocabulary", sa.String(), nullable=True),
        sa.Column("avoid_patterns", sa.String(), nullable=True),
        sa.Column("signature_phrases", sa.String(), nullable=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_voice_profiles_user_id", "voice_profiles", ["user_id"])
    op.create_index(
        "ix_voice_profiles_workspace_id", "voice_profiles", ["workspace_id"]
    )

    # Writing samples table
    op.create_table(
        "writing_samples",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(), nullable=True),
        sa.Column("content", sa.String(), nullable=False),
        sa.Column("source", sa.String(), nullable=True),
        sa.Column("sample_type", sa.String(), nullable=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("voice_profile_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["voice_profile_id"], ["voice_profiles.id"]),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_writing_samples_user_id", "writing_samples", ["user_id"])
    op.create_index(
        "ix_writing_samples_workspace_id", "writing_samples", ["workspace_id"]
    )

    # Image config sets table
    op.create_table(
        "image_config_sets",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("is_default", sa.Boolean(), nullable=False, default=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_image_config_sets_user_id", "image_config_sets", ["user_id"])
    op.create_index(
        "ix_image_config_sets_workspace_id", "image_config_sets", ["workspace_id"]
    )

    # Goals table
    op.create_table(
        "goals",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("positioning", sa.String(), nullable=True),
        sa.Column("signature_thesis", sa.String(), nullable=True),
        sa.Column("target_audience", sa.String(), nullable=True),
        sa.Column("content_style", sa.String(), nullable=True),
        sa.Column("onboarding_mode", sa.String(), nullable=True),
        sa.Column("onboarding_transcript", sa.String(), nullable=True),
        sa.Column("strategy_type", sa.String(), nullable=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("platform_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("voice_profile_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("image_config_set_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["platform_id"], ["platforms.id"]),
        sa.ForeignKeyConstraint(["voice_profile_id"], ["voice_profiles.id"]),
        sa.ForeignKeyConstraint(["image_config_set_id"], ["image_config_sets.id"]),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_goals_user_id", "goals", ["user_id"])
    op.create_index("ix_goals_platform_id", "goals", ["platform_id"])
    op.create_index("ix_goals_workspace_id", "goals", ["workspace_id"])

    # Chapters table
    op.create_table(
        "chapters",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("chapter_number", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("theme", sa.String(), nullable=True),
        sa.Column("theme_description", sa.String(), nullable=True),
        sa.Column("weeks_start", sa.Integer(), nullable=True),
        sa.Column("weeks_end", sa.Integer(), nullable=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("platform_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["platform_id"], ["platforms.id"]),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_chapters_chapter_number", "chapters", ["chapter_number"])
    op.create_index("ix_chapters_user_id", "chapters", ["user_id"])
    op.create_index("ix_chapters_platform_id", "chapters", ["platform_id"])
    op.create_index("ix_chapters_workspace_id", "chapters", ["workspace_id"])

    # Posts table
    op.create_table(
        "posts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("post_number", sa.Integer(), nullable=False),
        sa.Column("topic", sa.String(), nullable=True),
        sa.Column("shape", sa.String(), nullable=True),
        sa.Column("cadence", sa.String(), nullable=True),
        sa.Column("entry_point", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=False, default="not_started"),
        sa.Column("story_used", sa.String(), nullable=True),
        sa.Column("published_at", sa.DateTime(), nullable=True),
        sa.Column("published_url", sa.String(), nullable=True),
        sa.Column("guidance", sa.String(), nullable=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("chapter_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["chapter_id"], ["chapters.id"]),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_posts_post_number", "posts", ["post_number"])
    op.create_index("ix_posts_status", "posts", ["status"])
    op.create_index("ix_posts_user_id", "posts", ["user_id"])
    op.create_index("ix_posts_chapter_id", "posts", ["chapter_id"])
    op.create_index("ix_posts_workspace_id", "posts", ["workspace_id"])
    # Compound indexes for common queries
    op.create_index("ix_posts_workspace_status", "posts", ["workspace_id", "status"])

    # ==========================================================================
    # Workflow Tables
    # ==========================================================================

    # Workflow personas table
    op.create_table(
        "workflow_personas",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("role", sa.String(), nullable=True),
        sa.Column("prompt_template", sa.String(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_workflow_personas_name", "workflow_personas", ["name"])
    op.create_index("ix_workflow_personas_user_id", "workflow_personas", ["user_id"])
    op.create_index(
        "ix_workflow_personas_workspace_id", "workflow_personas", ["workspace_id"]
    )

    # Workflow runs table
    op.create_table(
        "workflow_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("run_id", sa.String(), nullable=False),
        sa.Column("story_name", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=False, default="running"),
        sa.Column("current_state", sa.String(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("error_message", sa.String(), nullable=True),
        sa.Column("total_transitions", sa.Integer(), nullable=True),
        sa.Column("total_tokens", sa.Integer(), nullable=True),
        sa.Column("total_cost", sa.Float(), nullable=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("post_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["post_id"], ["posts.id"]),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_workflow_runs_run_id", "workflow_runs", ["run_id"], unique=True)
    op.create_index("ix_workflow_runs_status", "workflow_runs", ["status"])
    op.create_index("ix_workflow_runs_user_id", "workflow_runs", ["user_id"])
    op.create_index("ix_workflow_runs_workspace_id", "workflow_runs", ["workspace_id"])
    op.create_index(
        "ix_workflow_runs_workspace_created",
        "workflow_runs",
        ["workspace_id", "created_at"],
    )

    # Workflow outputs table
    op.create_table(
        "workflow_outputs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("output_type", sa.String(), nullable=False),
        sa.Column("content", sa.String(), nullable=True),
        sa.Column("file_path", sa.String(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, default=1),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.ForeignKeyConstraint(["run_id"], ["workflow_runs.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_workflow_outputs_run_id", "workflow_outputs", ["run_id"])
    op.create_index(
        "ix_workflow_outputs_output_type", "workflow_outputs", ["output_type"]
    )

    # Workflow sessions table
    op.create_table(
        "workflow_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("agent_name", sa.String(), nullable=False),
        sa.Column("session_id", sa.String(), nullable=True),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.ForeignKeyConstraint(["run_id"], ["workflow_runs.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_workflow_sessions_run_id", "workflow_sessions", ["run_id"])

    # Workflow state metrics table
    op.create_table(
        "workflow_state_metrics",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("state_name", sa.String(), nullable=False),
        sa.Column("agent_name", sa.String(), nullable=True),
        sa.Column("input_tokens", sa.Integer(), nullable=True),
        sa.Column("output_tokens", sa.Integer(), nullable=True),
        sa.Column("cost", sa.Float(), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.ForeignKeyConstraint(["run_id"], ["workflow_runs.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_workflow_state_metrics_run_id", "workflow_state_metrics", ["run_id"]
    )

    # ==========================================================================
    # Image Tables
    # ==========================================================================

    # Image prompts table
    op.create_table(
        "image_prompts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("post_id", sa.String(), nullable=False),
        sa.Column("sentiment", sa.String(), nullable=True),
        sa.Column("context", sa.String(), nullable=False, default="software"),
        sa.Column("scene_code", sa.String(), nullable=True),
        sa.Column("scene_name", sa.String(), nullable=True),
        sa.Column("pose_code", sa.String(), nullable=True),
        sa.Column("outfit_vest", sa.String(), nullable=True),
        sa.Column("outfit_shirt", sa.String(), nullable=True),
        sa.Column("prompt_content", sa.String(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, default=1),
        sa.Column("image_data", sa.String(), nullable=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_image_prompts_post_id", "image_prompts", ["post_id"])
    op.create_index("ix_image_prompts_user_id", "image_prompts", ["user_id"])
    op.create_index("ix_image_prompts_workspace_id", "image_prompts", ["workspace_id"])

    # Image scenes table
    op.create_table(
        "image_scenes",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("sentiment", sa.String(), nullable=False),
        sa.Column("viewpoint", sa.String(), nullable=False, default="standard"),
        sa.Column("description", sa.String(), nullable=False),
        sa.Column("is_hardware_only", sa.Boolean(), nullable=False, default=False),
        sa.Column("no_desk_props", sa.Boolean(), nullable=False, default=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_image_scenes_code", "image_scenes", ["code"])
    op.create_index("ix_image_scenes_user_id", "image_scenes", ["user_id"])
    op.create_index("ix_image_scenes_workspace_id", "image_scenes", ["workspace_id"])

    # Image poses table
    op.create_table(
        "image_poses",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(), nullable=False),
        sa.Column("sentiment", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=False),
        sa.Column("emotional_note", sa.String(), nullable=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_image_poses_code", "image_poses", ["code"])
    op.create_index("ix_image_poses_user_id", "image_poses", ["user_id"])
    op.create_index("ix_image_poses_workspace_id", "image_poses", ["workspace_id"])

    # Image outfits table
    op.create_table(
        "image_outfits",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("vest", sa.String(), nullable=False),
        sa.Column("shirt", sa.String(), nullable=False),
        sa.Column("pants", sa.String(), nullable=False, default="Dark pants"),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_image_outfits_user_id", "image_outfits", ["user_id"])
    op.create_index("ix_image_outfits_workspace_id", "image_outfits", ["workspace_id"])

    # Image props table
    op.create_table(
        "image_props",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("category", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=False),
        sa.Column("context", sa.String(), nullable=False, default="all"),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_image_props_user_id", "image_props", ["user_id"])
    op.create_index("ix_image_props_workspace_id", "image_props", ["workspace_id"])

    # Image characters table
    op.create_table(
        "image_characters",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("character_type", sa.String(), nullable=False),
        sa.Column("appearance", sa.String(), nullable=False),
        sa.Column("face_details", sa.String(), nullable=True),
        sa.Column("clothing_rules", sa.String(), nullable=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_image_characters_user_id", "image_characters", ["user_id"])
    op.create_index(
        "ix_image_characters_workspace_id", "image_characters", ["workspace_id"]
    )

    # ==========================================================================
    # Character Tables
    # ==========================================================================

    # Character templates table
    op.create_table(
        "character_templates",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("base_appearance", sa.String(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_character_templates_user_id", "character_templates", ["user_id"]
    )
    op.create_index(
        "ix_character_templates_workspace_id", "character_templates", ["workspace_id"]
    )

    # Outfit parts table
    op.create_table(
        "outfit_parts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("category", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=False),
        sa.Column("color", sa.String(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_outfit_parts_user_id", "outfit_parts", ["user_id"])
    op.create_index("ix_outfit_parts_workspace_id", "outfit_parts", ["workspace_id"])

    # Outfits table
    op.create_table(
        "outfits",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("is_default", sa.Boolean(), nullable=False, default=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_outfits_user_id", "outfits", ["user_id"])
    op.create_index("ix_outfits_workspace_id", "outfits", ["workspace_id"])

    # Outfit items (junction table)
    op.create_table(
        "outfit_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("outfit_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("outfit_part_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["outfit_id"], ["outfits.id"]),
        sa.ForeignKeyConstraint(["outfit_part_id"], ["outfit_parts.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_outfit_items_outfit_id", "outfit_items", ["outfit_id"])
    op.create_index(
        "ix_outfit_items_outfit_part_id", "outfit_items", ["outfit_part_id"]
    )

    # Characters table
    op.create_table(
        "characters",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("template_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("default_outfit_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["template_id"], ["character_templates.id"]),
        sa.ForeignKeyConstraint(["default_outfit_id"], ["outfits.id"]),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_characters_user_id", "characters", ["user_id"])
    op.create_index("ix_characters_workspace_id", "characters", ["workspace_id"])

    # Character outfits (junction table)
    op.create_table(
        "character_outfits",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("character_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("outfit_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["character_id"], ["characters.id"]),
        sa.ForeignKeyConstraint(["outfit_id"], ["outfits.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_character_outfits_character_id", "character_outfits", ["character_id"]
    )
    op.create_index(
        "ix_character_outfits_outfit_id", "character_outfits", ["outfit_id"]
    )

    # Sentiments table
    op.create_table(
        "sentiments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("color_code", sa.String(), nullable=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sentiments_user_id", "sentiments", ["user_id"])
    op.create_index("ix_sentiments_workspace_id", "sentiments", ["workspace_id"])

    # Scene characters (junction table)
    op.create_table(
        "scene_characters",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("position", sa.String(), nullable=True),
        sa.Column("scene_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("character_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["scene_id"], ["image_scenes.id"]),
        sa.ForeignKeyConstraint(["character_id"], ["characters.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_scene_characters_scene_id", "scene_characters", ["scene_id"])
    op.create_index(
        "ix_scene_characters_character_id", "scene_characters", ["character_id"]
    )

    # Prop categories table
    op.create_table(
        "prop_categories",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_prop_categories_user_id", "prop_categories", ["user_id"])
    op.create_index(
        "ix_prop_categories_workspace_id", "prop_categories", ["workspace_id"]
    )

    # Scene prop rules (junction table)
    op.create_table(
        "scene_prop_rules",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("is_required", sa.Boolean(), nullable=False, default=False),
        sa.Column("max_count", sa.Integer(), nullable=True),
        sa.Column("scene_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("prop_category_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["scene_id"], ["image_scenes.id"]),
        sa.ForeignKeyConstraint(["prop_category_id"], ["prop_categories.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_scene_prop_rules_scene_id", "scene_prop_rules", ["scene_id"])
    op.create_index(
        "ix_scene_prop_rules_prop_category_id", "scene_prop_rules", ["prop_category_id"]
    )

    # Context prop rules table
    op.create_table(
        "context_prop_rules",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("context", sa.String(), nullable=False),
        sa.Column("is_required", sa.Boolean(), nullable=False, default=False),
        sa.Column("prop_category_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["prop_category_id"], ["prop_categories.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_context_prop_rules_prop_category_id",
        "context_prop_rules",
        ["prop_category_id"],
    )

    # ==========================================================================
    # Analytics Tables
    # ==========================================================================

    # Analytics imports table
    op.create_table(
        "analytics_imports",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("platform_name", sa.String(), nullable=False),
        sa.Column("filename", sa.String(), nullable=False),
        sa.Column(
            "import_date", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("row_count", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(), nullable=False, default="pending"),
        sa.Column("error_message", sa.String(), nullable=True),
        sa.Column("import_type", sa.String(), nullable=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_analytics_imports_platform_name", "analytics_imports", ["platform_name"]
    )
    op.create_index("ix_analytics_imports_user_id", "analytics_imports", ["user_id"])
    op.create_index(
        "ix_analytics_imports_workspace_id", "analytics_imports", ["workspace_id"]
    )

    # Post metrics table
    op.create_table(
        "post_metrics",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("platform_name", sa.String(), nullable=False),
        sa.Column("external_url", sa.String(), nullable=True),
        sa.Column("post_date", sa.Date(), nullable=True),
        sa.Column("impressions", sa.Integer(), nullable=True),
        sa.Column("engagement_count", sa.Integer(), nullable=True),
        sa.Column("engagement_rate", sa.Float(), nullable=True),
        sa.Column("likes", sa.Integer(), nullable=True),
        sa.Column("comments", sa.Integer(), nullable=True),
        sa.Column("shares", sa.Integer(), nullable=True),
        sa.Column("clicks", sa.Integer(), nullable=True),
        sa.Column("metric_date", sa.Date(), nullable=False),
        sa.Column("impressions_delta", sa.Integer(), nullable=True),
        sa.Column("engagement_delta", sa.Integer(), nullable=True),
        sa.Column("likes_delta", sa.Integer(), nullable=True),
        sa.Column("comments_delta", sa.Integer(), nullable=True),
        sa.Column("shares_delta", sa.Integer(), nullable=True),
        sa.Column("clicks_delta", sa.Integer(), nullable=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("post_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("import_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["post_id"], ["posts.id"]),
        sa.ForeignKeyConstraint(["import_id"], ["analytics_imports.id"]),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_post_metrics_platform_name", "post_metrics", ["platform_name"])
    op.create_index("ix_post_metrics_metric_date", "post_metrics", ["metric_date"])
    op.create_index("ix_post_metrics_user_id", "post_metrics", ["user_id"])
    op.create_index("ix_post_metrics_post_id", "post_metrics", ["post_id"])
    op.create_index("ix_post_metrics_workspace_id", "post_metrics", ["workspace_id"])

    # Daily metrics table
    op.create_table(
        "daily_metrics",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("platform_name", sa.String(), nullable=False),
        sa.Column("metric_date", sa.Date(), nullable=False),
        sa.Column("impressions", sa.Integer(), nullable=True),
        sa.Column("engagements", sa.Integer(), nullable=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("import_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["import_id"], ["analytics_imports.id"]),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_daily_metrics_metric_date", "daily_metrics", ["metric_date"])
    op.create_index("ix_daily_metrics_user_id", "daily_metrics", ["user_id"])
    op.create_index("ix_daily_metrics_workspace_id", "daily_metrics", ["workspace_id"])

    # Follower metrics table
    op.create_table(
        "follower_metrics",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("platform_name", sa.String(), nullable=False),
        sa.Column("metric_date", sa.Date(), nullable=False),
        sa.Column("new_followers", sa.Integer(), nullable=True),
        sa.Column("total_followers", sa.Integer(), nullable=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("import_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["import_id"], ["analytics_imports.id"]),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_follower_metrics_metric_date", "follower_metrics", ["metric_date"]
    )
    op.create_index("ix_follower_metrics_user_id", "follower_metrics", ["user_id"])
    op.create_index(
        "ix_follower_metrics_workspace_id", "follower_metrics", ["workspace_id"]
    )

    # Audience demographics table
    op.create_table(
        "audience_demographics",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("platform_name", sa.String(), nullable=False),
        sa.Column("category", sa.String(), nullable=False),
        sa.Column("value", sa.String(), nullable=False),
        sa.Column("percentage", sa.Float(), nullable=True),
        sa.Column("metric_date", sa.Date(), nullable=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("import_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["import_id"], ["analytics_imports.id"]),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_audience_demographics_user_id", "audience_demographics", ["user_id"]
    )
    op.create_index(
        "ix_audience_demographics_workspace_id",
        "audience_demographics",
        ["workspace_id"],
    )

    # Post demographics table
    op.create_table(
        "post_demographics",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("platform_name", sa.String(), nullable=False),
        sa.Column("external_url", sa.String(), nullable=False),
        sa.Column("category", sa.String(), nullable=False),
        sa.Column("value", sa.String(), nullable=False),
        sa.Column("percentage", sa.Float(), nullable=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("import_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["import_id"], ["analytics_imports.id"]),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_post_demographics_external_url", "post_demographics", ["external_url"]
    )
    op.create_index("ix_post_demographics_user_id", "post_demographics", ["user_id"])
    op.create_index(
        "ix_post_demographics_workspace_id", "post_demographics", ["workspace_id"]
    )

    # ==========================================================================
    # History Tables
    # ==========================================================================

    # Run records table
    op.create_table(
        "run_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("run_id", sa.String(), nullable=False),
        sa.Column("story", sa.String(), nullable=True),
        sa.Column("outcome", sa.String(), nullable=True),
        sa.Column("final_score", sa.Integer(), nullable=True),
        sa.Column("total_tokens", sa.Integer(), nullable=True),
        sa.Column("total_cost", sa.Float(), nullable=True),
        sa.Column("duration_seconds", sa.Float(), nullable=True),
        sa.Column("transitions", sa.Integer(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_run_records_run_id", "run_records", ["run_id"], unique=True)

    # Invocation records table
    op.create_table(
        "invocation_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("state", sa.String(), nullable=False),
        sa.Column("agent", sa.String(), nullable=False),
        sa.Column("input_tokens", sa.Integer(), nullable=True),
        sa.Column("output_tokens", sa.Integer(), nullable=True),
        sa.Column("cost", sa.Float(), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.ForeignKeyConstraint(["run_id"], ["run_records.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_invocation_records_run_id", "invocation_records", ["run_id"])

    # Audit score records table
    op.create_table(
        "audit_score_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("auditor", sa.String(), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("iteration", sa.Integer(), nullable=False),
        sa.Column("feedback", sa.String(), nullable=True),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.ForeignKeyConstraint(["run_id"], ["run_records.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_score_records_run_id", "audit_score_records", ["run_id"])

    # Post iteration records table
    op.create_table(
        "post_iteration_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("story", sa.String(), nullable=False),
        sa.Column("iteration", sa.Integer(), nullable=False),
        sa.Column("draft_text", sa.String(), nullable=True),
        sa.Column("audit_score", sa.Integer(), nullable=True),
        sa.Column("audit_feedback", sa.String(), nullable=True),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.ForeignKeyConstraint(["run_id"], ["run_records.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_post_iteration_records_story", "post_iteration_records", ["story"]
    )
    op.create_index(
        "ix_post_iteration_records_run_id", "post_iteration_records", ["run_id"]
    )


def downgrade() -> None:
    # Drop tables in reverse dependency order

    # History tables
    op.drop_table("post_iteration_records")
    op.drop_table("audit_score_records")
    op.drop_table("invocation_records")
    op.drop_table("run_records")

    # Analytics tables
    op.drop_table("post_demographics")
    op.drop_table("audience_demographics")
    op.drop_table("follower_metrics")
    op.drop_table("daily_metrics")
    op.drop_table("post_metrics")
    op.drop_table("analytics_imports")

    # Character tables (junction tables first)
    op.drop_table("context_prop_rules")
    op.drop_table("scene_prop_rules")
    op.drop_table("prop_categories")
    op.drop_table("scene_characters")
    op.drop_table("sentiments")
    op.drop_table("character_outfits")
    op.drop_table("characters")
    op.drop_table("outfit_items")
    op.drop_table("outfits")
    op.drop_table("outfit_parts")
    op.drop_table("character_templates")

    # Image tables
    op.drop_table("image_characters")
    op.drop_table("image_props")
    op.drop_table("image_outfits")
    op.drop_table("image_poses")
    op.drop_table("image_scenes")
    op.drop_table("image_prompts")

    # Workflow tables
    op.drop_table("workflow_state_metrics")
    op.drop_table("workflow_sessions")
    op.drop_table("workflow_outputs")
    op.drop_table("workflow_runs")
    op.drop_table("workflow_personas")

    # Content tables
    op.drop_table("posts")
    op.drop_table("chapters")
    op.drop_table("goals")
    op.drop_table("image_config_sets")
    op.drop_table("writing_samples")
    op.drop_table("voice_profiles")
    op.drop_table("platforms")

    # Core tables
    op.drop_table("active_sessions")
    op.drop_table("workspace_memberships")
    op.drop_table("workspaces")
    op.drop_table("users")
