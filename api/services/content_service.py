"""Service for content strategy database operations."""

from __future__ import annotations

import json
from typing import Optional, Union
from uuid import UUID

from sqlmodel import select

from runner.content.ids import coerce_uuid, normalize_user_id
from runner.content.models import (
    UserResponse,
    PlatformResponse,
    GoalResponse,
    ChapterResponse,
    PostResponse,
    VoiceProfileResponse,
    WritingSampleRecord,
    VOICE_PROMPTS,
    CONTENT_STYLES,
    POST_SHAPES,
)
from runner.content.repository import (
    UserRepository,
    PlatformRepository,
    GoalRepository,
    ChapterRepository,
    PostRepository,
    WritingSampleRepository,
    VoiceProfileRepository,
)
from runner.db.engine import get_session
from runner.db.models import (
    UserCreate,
    PlatformCreate,
    GoalCreate,
    ChapterCreate,
    PostCreate,
    WritingSampleCreate,
    VoiceProfileCreate,
    Goal,
    Chapter,
    Post,
    VoiceProfile,
)


LEGACY_VOICE_KEY = "legacy"


def _uuid_to_str(val: Union[UUID, str, None]) -> Optional[str]:
    """Convert UUID-like values to string for API responses."""
    if val is None:
        return None
    if isinstance(val, UUID):
        return str(val)
    return str(val)


def _datetime_to_str(val) -> Optional[str]:
    """Convert datetimes to ISO strings for API responses."""
    if not val:
        return None
    return val.isoformat()


def _generate_slug(name: str) -> str:
    """Generate a URL-safe slug from a name."""
    slug = name.lower().strip()
    slug = "".join(
        ch if ch.isalnum() or ch.isspace() or ch == "-" else "" for ch in slug
    )
    slug = "-".join(slug.split())
    slug = "-".join(part for part in slug.split("-") if part)
    return slug or "voice-profile"


def _encode_legacy_voice_profile(payload: dict) -> str:
    """Encode legacy voice profile fields into JSON for storage."""
    return json.dumps({LEGACY_VOICE_KEY: payload})


def _decode_legacy_voice_profile(description: Optional[str]) -> dict:
    """Decode legacy voice profile fields from JSON storage."""
    if not description:
        return {}
    try:
        data = json.loads(description)
    except json.JSONDecodeError:
        return {}
    if isinstance(data, dict) and LEGACY_VOICE_KEY in data:
        legacy = data.get(LEGACY_VOICE_KEY)
        return legacy if isinstance(legacy, dict) else {}
    return {}


def _format_sentence_patterns(value: Optional[str]) -> Optional[str]:
    """Format sentence_patterns JSON into human-readable text."""
    if not value:
        return None
    # If it's already a plain string (preset), return as-is
    if not value.startswith("{"):
        return value
    try:
        patterns = json.loads(value)
        if not isinstance(patterns, dict):
            return value
        parts = []
        if patterns.get("average_length"):
            parts.append(f"{patterns['average_length'].capitalize()} sentence length")
        if patterns.get("variation"):
            parts.append(f"{patterns['variation']} variation")
        if patterns.get("common_structures"):
            structures = patterns["common_structures"]
            if isinstance(structures, list):
                parts.append(f"Uses: {', '.join(structures)}")
        return ". ".join(parts) if parts else value
    except (json.JSONDecodeError, AttributeError):
        return value


def _format_signature_phrases(value: Optional[str]) -> Optional[str]:
    """Format signature_phrases JSON array into human-readable text."""
    if not value:
        return None
    # If it's already a plain string (preset), return as-is
    if not value.startswith("["):
        return value
    try:
        phrases = json.loads(value)
        if isinstance(phrases, list):
            return ", ".join(str(p) for p in phrases)
        return value
    except json.JSONDecodeError:
        return value


class ContentService:
    """Service for content strategy operations (SQLModel only)."""

    # =========================================================================
    # User Operations
    # =========================================================================

    def create_user(self, name: str, email: Optional[str] = None) -> str:
        """Create a new user and return the ID."""
        with get_session() as session:
            repo = UserRepository(session)
            user = repo.create(UserCreate(full_name=name, email=email))
            return str(user.id)

    def get_user(self, user_id: Union[str, UUID]) -> Optional[UserResponse]:
        """Get user with summary data."""
        uid = normalize_user_id(user_id)
        if not uid:
            return None
        with get_session() as session:
            user_repo = UserRepository(session)
            user = user_repo.get(uid)
            if not user:
                return None

            goal_repo = GoalRepository(session)
            VoiceProfileRepository(session)
            post_repo = PostRepository(session)

            goals = goal_repo.list_by_user(uid)
            posts = post_repo.list_by_user(uid)
            voice_profiles = session.exec(
                select(VoiceProfile).where(not VoiceProfile.is_preset)
            ).all()

            return UserResponse(
                id=str(user.id),
                name=user.name,
                email=user.email,
                has_goal=len(goals) > 0,
                has_voice_profile=len(voice_profiles) > 0,
                post_count=len(posts),
            )

    def get_user_by_email(self, email: str) -> Optional[UserResponse]:
        """Get user by email."""
        with get_session() as session:
            repo = UserRepository(session)
            user = repo.get_by_email(email)
            if not user:
                return None
            return self.get_user(user.id)

    def get_or_create_user(self, name: str, email: Optional[str] = None) -> str:
        """Get existing user by email or create new one."""
        with get_session() as session:
            repo = UserRepository(session)
            if email:
                user = repo.get_by_email(email)
                if user:
                    return str(user.id)
            user = repo.create(UserCreate(full_name=name, email=email))
            return str(user.id)

    def list_users(self) -> list[UserResponse]:
        """List all users with summary data."""
        with get_session() as session:
            user_repo = UserRepository(session)
            goal_repo = GoalRepository(session)
            post_repo = PostRepository(session)

            users = user_repo.list_all()
            voice_profiles = session.exec(
                select(VoiceProfile).where(not VoiceProfile.is_preset)
            ).all()
            has_voice = len(voice_profiles) > 0

            result = []
            for user in users:
                goals = goal_repo.list_by_user(user.id)
                posts = post_repo.list_by_user(user.id)
                result.append(
                    UserResponse(
                        id=str(user.id),
                        name=user.name,
                        email=user.email,
                        has_goal=len(goals) > 0,
                        has_voice_profile=has_voice,
                        post_count=len(posts),
                    )
                )
            return result

    # =========================================================================
    # Platform Operations
    # =========================================================================

    def create_platform(
        self,
        user_id: Union[str, UUID],
        name: str,
        description: Optional[str] = None,
        post_format: Optional[str] = None,
        default_word_count: Optional[int] = None,
        uses_enemies: bool = True,
    ) -> str:
        """Create a new platform for a user."""
        uid = normalize_user_id(user_id)
        if not uid:
            raise ValueError("Invalid user_id")
        record = PlatformCreate(
            user_id=uid,
            name=name,
            description=description,
            post_format=post_format,
            default_word_count=default_word_count,
            uses_enemies=uses_enemies,
        )
        with get_session() as session:
            repo = PlatformRepository(session)
            platform = repo.create(record)
            return str(platform.id)

    def get_platform(self, platform_id: Union[str, UUID]) -> Optional[PlatformResponse]:
        """Get platform by ID."""
        pid = coerce_uuid(platform_id)
        if not pid:
            return None
        with get_session() as session:
            repo = PlatformRepository(session)
            platform = repo.get(pid)
            if not platform:
                return None
            return PlatformResponse(
                id=str(platform.id),
                user_id=str(platform.user_id),
                name=platform.name,
                description=platform.description,
                post_format=platform.post_format,
                default_word_count=platform.default_word_count,
                uses_enemies=platform.uses_enemies,
                is_active=platform.is_active,
                created_at=_datetime_to_str(platform.created_at),
            )

    def get_platforms(self, user_id: Union[str, UUID]) -> list[PlatformResponse]:
        """Get all platforms for a user."""
        uid = normalize_user_id(user_id)
        if not uid:
            return []
        with get_session() as session:
            repo = PlatformRepository(session)
            platforms = repo.list_by_user(uid)
            return [
                PlatformResponse(
                    id=str(p.id),
                    user_id=str(p.user_id),
                    name=p.name,
                    description=p.description,
                    post_format=p.post_format,
                    default_word_count=p.default_word_count,
                    uses_enemies=p.uses_enemies,
                    is_active=p.is_active,
                    created_at=_datetime_to_str(p.created_at),
                )
                for p in platforms
            ]

    def update_platform(self, platform_id: Union[str, UUID], **kwargs) -> None:
        """Update platform fields."""
        pid = coerce_uuid(platform_id)
        if not pid:
            return
        with get_session() as session:
            repo = PlatformRepository(session)
            platform = repo.get(pid)
            if not platform:
                return
            for key, value in kwargs.items():
                if hasattr(platform, key):
                    setattr(platform, key, value)
            session.add(platform)
            session.commit()

    def delete_platform(self, platform_id: Union[str, UUID]) -> None:
        """Delete platform by ID."""
        pid = coerce_uuid(platform_id)
        if not pid:
            return
        with get_session() as session:
            repo = PlatformRepository(session)
            repo.delete(pid)

    # =========================================================================
    # Goal Operations
    # =========================================================================

    def save_goal(
        self,
        user_id: Union[str, UUID],
        strategy_type: str = "series",
        positioning: Optional[str] = None,
        signature_thesis: Optional[str] = None,
        target_audience: Optional[str] = None,
        content_style: Optional[str] = None,
        onboarding_mode: Optional[str] = None,
        onboarding_transcript: Optional[str] = None,
        workspace_id: Optional[Union[str, UUID]] = None,
    ) -> str:
        """Save a new goal for a user."""
        uid = normalize_user_id(user_id)
        if not uid:
            raise ValueError("Invalid user_id")
        wid = coerce_uuid(workspace_id) if workspace_id else None
        record = GoalCreate(
            user_id=uid,
            strategy_type=strategy_type,
            positioning=positioning,
            signature_thesis=signature_thesis,
            target_audience=target_audience,
            content_style=content_style,
            onboarding_mode=onboarding_mode,
            onboarding_transcript=onboarding_transcript,
            workspace_id=wid,
        )
        with get_session() as session:
            repo = GoalRepository(session)
            goal = repo.create(record)
            return str(goal.id)

    def get_goal(
        self,
        user_id: Union[str, UUID],
        platform_id: Optional[Union[str, UUID]] = None,
    ) -> Optional[GoalResponse]:
        """Get user's goal."""
        uid = normalize_user_id(user_id)
        if not uid:
            return None
        pid = coerce_uuid(platform_id) if platform_id else None
        with get_session() as session:
            repo = GoalRepository(session)
            goal = repo.get_by_platform(uid, pid) if pid else repo.get_by_user(uid)
            if not goal:
                return None
            return GoalResponse(
                id=str(goal.id),
                strategy_type=goal.strategy_type or "series",
                voice_profile_id=_uuid_to_str(goal.voice_profile_id),
                image_config_set_id=_uuid_to_str(goal.image_config_set_id),
                positioning=goal.positioning,
                signature_thesis=goal.signature_thesis,
                target_audience=goal.target_audience,
                content_style=goal.content_style,
                onboarding_mode=goal.onboarding_mode,
            )

    def update_goal(self, goal_id: Union[str, UUID], **kwargs) -> None:
        """Update goal fields."""
        gid = coerce_uuid(goal_id)
        if not gid:
            return
        if "voice_profile_id" in kwargs:
            kwargs["voice_profile_id"] = coerce_uuid(kwargs["voice_profile_id"])
        if "image_config_set_id" in kwargs:
            kwargs["image_config_set_id"] = coerce_uuid(kwargs["image_config_set_id"])
        with get_session() as session:
            goal = session.get(Goal, gid)
            if not goal:
                return
            for key, value in kwargs.items():
                if hasattr(goal, key):
                    setattr(goal, key, value)
            session.add(goal)
            session.commit()

    def delete_strategy(
        self, user_id: Union[str, UUID], goal_id: Union[str, UUID]
    ) -> dict:
        """Delete a strategy (goal) and all related chapters and posts."""
        uid = normalize_user_id(user_id)
        gid = coerce_uuid(goal_id)
        if not uid or not gid:
            return {
                "goal_id": _uuid_to_str(gid),
                "chapters_deleted": 0,
                "posts_deleted": 0,
            }
        with get_session() as session:
            chapters = list(
                session.exec(select(Chapter).where(Chapter.user_id == uid)).all()
            )
            chapter_ids = [c.id for c in chapters]
            posts = []
            if chapter_ids:
                posts = list(
                    session.exec(
                        select(Post).where(Post.chapter_id.in_(chapter_ids))
                    ).all()
                )
            for post in posts:
                session.delete(post)
            for chapter in chapters:
                session.delete(chapter)
            goal = session.get(Goal, gid)
            if goal:
                session.delete(goal)
            session.commit()
            return {
                "goal_id": str(gid),
                "chapters_deleted": len(chapter_ids),
                "posts_deleted": len(posts),
            }

    def get_goal_for_workspace(self, workspace_id: UUID) -> Optional[dict]:
        """Get the goal for a workspace."""
        with get_session() as session:
            repo = GoalRepository(session)
            goal = repo.get_by_workspace(workspace_id)
            if not goal:
                return None
            return {
                "id": str(goal.id),
                "strategy_type": goal.strategy_type or "series",
                "voice_profile_id": _uuid_to_str(goal.voice_profile_id),
                "image_config_set_id": _uuid_to_str(goal.image_config_set_id),
                "positioning": goal.positioning,
                "signature_thesis": goal.signature_thesis,
                "target_audience": goal.target_audience,
                "content_style": goal.content_style,
                "onboarding_mode": goal.onboarding_mode,
            }

    def get_chapters_for_workspace(self, workspace_id: UUID) -> list[dict]:
        """Get all chapters for a workspace with post counts."""
        with get_session() as session:
            chapter_repo = ChapterRepository(session)
            post_repo = PostRepository(session)
            chapters = chapter_repo.list_by_workspace(workspace_id)
            posts = post_repo.list_by_workspace(workspace_id)
            post_counts = {}
            completed_counts = {}
            for post in posts:
                post_counts[post.chapter_id] = post_counts.get(post.chapter_id, 0) + 1
                if post.status in ("ready", "published"):
                    completed_counts[post.chapter_id] = (
                        completed_counts.get(post.chapter_id, 0) + 1
                    )
            result = []
            for chapter in chapters:
                result.append(
                    {
                        "id": str(chapter.id),
                        "chapter_number": chapter.chapter_number,
                        "title": chapter.title,
                        "description": chapter.description,
                        "theme": chapter.theme,
                        "theme_description": chapter.theme_description,
                        "weeks_start": chapter.weeks_start,
                        "weeks_end": chapter.weeks_end,
                        "post_count": post_counts.get(chapter.id, 0),
                        "completed_count": completed_counts.get(chapter.id, 0),
                    }
                )
            return result

    def delete_strategy_for_workspace(self, workspace_id: UUID) -> dict:
        """Delete strategy (goal, chapters, posts) for a workspace."""
        with get_session() as session:
            goal_repo = GoalRepository(session)
            chapter_repo = ChapterRepository(session)
            post_repo = PostRepository(session)

            goal = goal_repo.get_by_workspace(workspace_id)
            chapters = chapter_repo.list_by_workspace(workspace_id)
            chapter_ids = [c.id for c in chapters]
            posts = post_repo.list_by_workspace(workspace_id)

            for post in posts:
                session.delete(post)
            for chapter in chapters:
                session.delete(chapter)
            if goal:
                session.delete(goal)
            session.commit()

            return {
                "goal_id": str(goal.id) if goal else None,
                "chapters_deleted": len(chapter_ids),
                "posts_deleted": len(posts),
            }

    # =========================================================================
    # Chapter Operations
    # =========================================================================

    def save_chapter(
        self,
        user_id: Union[str, UUID],
        chapter_number: int,
        title: str,
        description: Optional[str] = None,
        theme: Optional[str] = None,
        theme_description: Optional[str] = None,
        weeks_start: Optional[int] = None,
        weeks_end: Optional[int] = None,
        workspace_id: Optional[Union[str, UUID]] = None,
    ) -> str:
        """Save a new chapter."""
        uid = normalize_user_id(user_id)
        if not uid:
            raise ValueError("Invalid user_id")
        wid = coerce_uuid(workspace_id) if workspace_id else None
        record = ChapterCreate(
            user_id=uid,
            chapter_number=chapter_number,
            title=title,
            description=description,
            theme=theme,
            theme_description=theme_description,
            weeks_start=weeks_start,
            weeks_end=weeks_end,
            workspace_id=wid,
        )
        with get_session() as session:
            repo = ChapterRepository(session)
            chapter = repo.create(record)
            return str(chapter.id)

    def get_chapters(
        self,
        user_id: Union[str, UUID],
        platform_id: Optional[Union[str, UUID]] = None,
    ) -> list[ChapterResponse]:
        """Get all chapters with post counts, optionally filtered by platform."""
        uid = normalize_user_id(user_id)
        if not uid:
            return []
        pid = coerce_uuid(platform_id) if platform_id else None
        with get_session() as session:
            chapter_repo = ChapterRepository(session)
            post_repo = PostRepository(session)
            chapters = (
                chapter_repo.list_by_platform(uid, pid)
                if pid
                else chapter_repo.list_by_user(uid)
            )
            posts = post_repo.list_by_user(uid)
            post_counts = {}
            completed_counts = {}
            for post in posts:
                post_counts[post.chapter_id] = post_counts.get(post.chapter_id, 0) + 1
                if post.status in ("ready", "published"):
                    completed_counts[post.chapter_id] = (
                        completed_counts.get(post.chapter_id, 0) + 1
                    )
            result = []
            for chapter in chapters:
                result.append(
                    ChapterResponse(
                        id=str(chapter.id),
                        chapter_number=chapter.chapter_number,
                        title=chapter.title,
                        description=chapter.description,
                        theme=chapter.theme,
                        theme_description=chapter.theme_description,
                        weeks_start=chapter.weeks_start,
                        weeks_end=chapter.weeks_end,
                        post_count=post_counts.get(chapter.id, 0),
                        completed_count=completed_counts.get(chapter.id, 0),
                    )
                )
            return result

    def get_chapter(self, chapter_id: Union[str, UUID]) -> Optional[ChapterResponse]:
        """Get single chapter with post counts."""
        cid = coerce_uuid(chapter_id)
        if not cid:
            return None
        with get_session() as session:
            chapter_repo = ChapterRepository(session)
            post_repo = PostRepository(session)
            chapter = chapter_repo.get(cid)
            if not chapter:
                return None
            posts = post_repo.list_by_chapter(chapter.id)
            completed = [p for p in posts if p.status in ("ready", "published")]
            return ChapterResponse(
                id=str(chapter.id),
                chapter_number=chapter.chapter_number,
                title=chapter.title,
                description=chapter.description,
                theme=chapter.theme,
                theme_description=chapter.theme_description,
                weeks_start=chapter.weeks_start,
                weeks_end=chapter.weeks_end,
                post_count=len(posts),
                completed_count=len(completed),
            )

    # =========================================================================
    # Post Operations
    # =========================================================================

    def save_post(
        self,
        user_id: Union[str, UUID],
        chapter_id: Union[str, UUID],
        post_number: int,
        topic: Optional[str] = None,
        shape: Optional[str] = None,
        cadence: Optional[str] = None,
        entry_point: Optional[str] = None,
        status: str = "not_started",
        guidance: Optional[str] = None,
        workspace_id: Optional[Union[str, UUID]] = None,
    ) -> str:
        """Save a new post."""
        uid = normalize_user_id(user_id)
        cid = coerce_uuid(chapter_id)
        if not uid or not cid:
            raise ValueError("Invalid user_id or chapter_id")
        wid = coerce_uuid(workspace_id) if workspace_id else None
        record = PostCreate(
            user_id=uid,
            chapter_id=cid,
            post_number=post_number,
            topic=topic,
            shape=shape,
            cadence=cadence,
            entry_point=entry_point,
            status=status,
            guidance=guidance,
            workspace_id=wid,
        )
        with get_session() as session:
            repo = PostRepository(session)
            post = repo.create(record)
            return str(post.id)

    def get_posts(
        self,
        user_id: Union[str, UUID],
        chapter_id: Optional[Union[str, UUID]] = None,
        status: Optional[str] = None,
    ) -> list[PostResponse]:
        """Get posts, optionally filtered by chapter or status."""
        uid = normalize_user_id(user_id)
        if not uid:
            return []
        cid = coerce_uuid(chapter_id) if chapter_id else None
        with get_session() as session:
            chapter_repo = ChapterRepository(session)
            post_repo = PostRepository(session)
            chapters = {c.id: c for c in chapter_repo.list_by_user(uid)}

            if cid:
                posts = post_repo.list_by_chapter(cid)
            elif status:
                posts = post_repo.list_by_status(uid, status)
            else:
                posts = post_repo.list_by_user(uid)

            result = []
            for post in posts:
                chapter = chapters.get(post.chapter_id)
                result.append(
                    PostResponse(
                        id=str(post.id),
                        post_number=post.post_number,
                        chapter_id=str(post.chapter_id),
                        chapter_number=chapter.chapter_number if chapter else 0,
                        chapter_title=chapter.title if chapter else "",
                        topic=post.topic,
                        shape=post.shape,
                        cadence=post.cadence,
                        entry_point=post.entry_point,
                        status=post.status,
                        guidance=post.guidance,
                        published_url=post.published_url,
                    )
                )
            return result

    def get_available_posts(self, user_id: Union[str, UUID]) -> list[PostResponse]:
        """Get posts that need work (not_started, needs_story, draft)."""
        uid = normalize_user_id(user_id)
        if not uid:
            return []
        with get_session() as session:
            chapter_repo = ChapterRepository(session)
            chapters = {c.id: c for c in chapter_repo.list_by_user(uid)}
            posts = session.exec(
                select(Post)
                .where(
                    Post.user_id == uid,
                    Post.status.in_(["not_started", "needs_story", "draft"]),
                )
                .order_by(Post.post_number)
            ).all()
            result = []
            for post in posts:
                chapter = chapters.get(post.chapter_id)
                result.append(
                    PostResponse(
                        id=str(post.id),
                        post_number=post.post_number,
                        chapter_id=str(post.chapter_id),
                        chapter_number=chapter.chapter_number if chapter else 0,
                        chapter_title=chapter.title if chapter else "",
                        topic=post.topic,
                        shape=post.shape,
                        cadence=post.cadence,
                        entry_point=post.entry_point,
                        status=post.status,
                        guidance=post.guidance,
                        published_url=post.published_url,
                    )
                )
            return result

    def get_next_post(self, user_id: Union[str, UUID]) -> Optional[PostResponse]:
        """Get the next unfinished post (lowest number)."""
        posts = self.get_available_posts(user_id)
        return posts[0] if posts else None

    def get_post(self, post_id: Union[str, UUID]) -> Optional[PostResponse]:
        """Get post by ID."""
        pid = coerce_uuid(post_id)
        if not pid:
            return None
        with get_session() as session:
            post_repo = PostRepository(session)
            chapter_repo = ChapterRepository(session)
            post = post_repo.get(pid)
            if not post:
                return None
            chapter = chapter_repo.get(post.chapter_id)
            return PostResponse(
                id=str(post.id),
                post_number=post.post_number,
                chapter_id=str(post.chapter_id),
                chapter_number=chapter.chapter_number if chapter else 0,
                chapter_title=chapter.title if chapter else "",
                topic=post.topic,
                shape=post.shape,
                cadence=post.cadence,
                entry_point=post.entry_point,
                status=post.status,
                guidance=post.guidance,
                published_url=post.published_url,
            )

    def get_post_by_number(
        self, user_id: Union[str, UUID], post_number: int
    ) -> Optional[PostResponse]:
        """Get post by user and post number."""
        uid = normalize_user_id(user_id)
        if not uid:
            return None
        with get_session() as session:
            post_repo = PostRepository(session)
            chapter_repo = ChapterRepository(session)
            post = post_repo.get_by_number(uid, post_number)
            if not post:
                return None
            chapter = chapter_repo.get(post.chapter_id)
            return PostResponse(
                id=str(post.id),
                post_number=post.post_number,
                chapter_id=str(post.chapter_id),
                chapter_number=chapter.chapter_number if chapter else 0,
                chapter_title=chapter.title if chapter else "",
                topic=post.topic,
                shape=post.shape,
                cadence=post.cadence,
                entry_point=post.entry_point,
                status=post.status,
                guidance=post.guidance,
                published_url=post.published_url,
            )

    def update_post(self, post_id: Union[str, UUID], **kwargs) -> None:
        """Update post fields."""
        pid = coerce_uuid(post_id)
        if not pid:
            return
        with get_session() as session:
            post = session.get(Post, pid)
            if not post:
                return
            for key, value in kwargs.items():
                if hasattr(post, key):
                    setattr(post, key, value)
            session.add(post)
            session.commit()

    # =========================================================================
    # Writing Sample Operations
    # =========================================================================

    def save_writing_sample(
        self,
        user_id: Union[str, UUID],
        source_type: str,
        content: str,
        prompt_id: Optional[str] = None,
        prompt_text: Optional[str] = None,
        title: Optional[str] = None,
        workspace_id: Optional[UUID] = None,
    ) -> str:
        """Save a writing sample."""
        uid = normalize_user_id(user_id)
        if not uid:
            raise ValueError("Invalid user_id")
        word_count = len(content.split())
        record = WritingSampleCreate(
            user_id=uid,
            source_type=source_type,
            prompt_id=prompt_id,
            prompt_text=prompt_text,
            title=title,
            content=content,
            word_count=word_count,
            workspace_id=workspace_id,
        )
        with get_session() as session:
            repo = WritingSampleRepository(session)
            sample = repo.create(record)
            return str(sample.id)

    def get_writing_samples(
        self, user_id: Union[str, UUID]
    ) -> list[WritingSampleRecord]:
        """Get all writing samples for a user."""
        uid = normalize_user_id(user_id)
        if not uid:
            return []
        with get_session() as session:
            repo = WritingSampleRepository(session)
            samples = repo.list_by_user(uid)
            return [
                WritingSampleRecord(
                    id=str(s.id),
                    user_id=str(s.user_id),
                    source_type=s.source_type,
                    prompt_id=s.prompt_id,
                    prompt_text=s.prompt_text,
                    title=s.title,
                    content=s.content,
                    word_count=s.word_count,
                    created_at=_datetime_to_str(s.created_at),
                )
                for s in samples
            ]

    def get_writing_samples_for_workspace(
        self, workspace_id: UUID
    ) -> list[WritingSampleRecord]:
        """Get all writing samples for a workspace."""
        with get_session() as session:
            repo = WritingSampleRepository(session)
            samples = repo.list_by_workspace(workspace_id)
            return [
                WritingSampleRecord(
                    id=str(s.id),
                    user_id=str(s.user_id),
                    source_type=s.source_type,
                    prompt_id=s.prompt_id,
                    prompt_text=s.prompt_text,
                    title=s.title,
                    content=s.content,
                    word_count=s.word_count,
                    created_at=_datetime_to_str(s.created_at),
                )
                for s in samples
            ]

    # =========================================================================
    # Voice Profile Operations
    # =========================================================================

    def _default_voice_profile_id(self, user_id: UUID) -> Optional[UUID]:
        """Lookup default voice profile via goal association."""
        with get_session() as session:
            repo = GoalRepository(session)
            goal = repo.get_by_user(user_id)
            return goal.voice_profile_id if goal else None

    def _voice_profile_response(
        self, profile: VoiceProfile, default_id: Optional[UUID]
    ) -> VoiceProfileResponse:
        """Convert a VoiceProfile to VoiceProfileResponse."""
        legacy = _decode_legacy_voice_profile(profile.description)

        # Get raw values (prefer legacy, fallback to native fields)
        raw_sentence_patterns = legacy.get("sentence_patterns") or profile.example_excerpts
        raw_signature_phrases = legacy.get("signature_phrases") or profile.signature_phrases

        return VoiceProfileResponse(
            id=str(profile.id),
            name=profile.name,
            description=None if legacy else profile.description,
            is_default=default_id == profile.id,
            tone=legacy.get("tone") or profile.tone_description,
            sentence_patterns=_format_sentence_patterns(raw_sentence_patterns),
            vocabulary_level=legacy.get("vocabulary_level") or profile.word_choices,
            signature_phrases=_format_signature_phrases(raw_signature_phrases),
            storytelling_style=legacy.get("storytelling_style")
            or profile.avoid_patterns,
            emotional_register=legacy.get("emotional_register"),
            created_at=_datetime_to_str(profile.created_at),
        )

    def save_voice_profile(
        self,
        user_id: Union[str, UUID],
        tone: Optional[str] = None,
        sentence_patterns: Optional[str] = None,
        vocabulary_level: Optional[str] = None,
        signature_phrases: Optional[str] = None,
        storytelling_style: Optional[str] = None,
        emotional_register: Optional[str] = None,
        raw_analysis: Optional[str] = None,
    ) -> str:
        """Save a voice profile."""
        uid = normalize_user_id(user_id)
        if not uid:
            raise ValueError("Invalid user_id")
        with get_session() as session:
            repo = VoiceProfileRepository(session)
            existing = session.exec(
                select(VoiceProfile).where(not VoiceProfile.is_preset)
            ).all()
            name = "Default" if not existing else f"Voice Profile {len(existing) + 1}"
            slug = _generate_slug(name)
            counter = 1
            while repo.get_by_slug(slug):
                counter += 1
                slug = f"{_generate_slug(name)}-{counter}"

            legacy_payload = {
                "tone": tone,
                "sentence_patterns": sentence_patterns,
                "vocabulary_level": vocabulary_level,
                "signature_phrases": signature_phrases,
                "storytelling_style": storytelling_style,
                "emotional_register": emotional_register,
                "raw_analysis": raw_analysis,
            }
            record = VoiceProfileCreate(
                name=name,
                slug=slug,
                description=_encode_legacy_voice_profile(legacy_payload),
                is_preset=False,
                tone_description=tone,
                signature_phrases=signature_phrases,
                word_choices=vocabulary_level,
                example_excerpts=sentence_patterns,
                avoid_patterns=storytelling_style,
            )
            profile = repo.create(record)
            return str(profile.id)

    def save_voice_profile_for_workspace(
        self,
        workspace_id: UUID,
        user_id: UUID,
        tone: Optional[str] = None,
        sentence_patterns: Optional[str] = None,
        vocabulary_level: Optional[str] = None,
        signature_phrases: Optional[str] = None,
        storytelling_style: Optional[str] = None,
        emotional_register: Optional[str] = None,
        raw_analysis: Optional[str] = None,
    ) -> str:
        """Save a voice profile scoped to a workspace."""
        with get_session() as session:
            repo = VoiceProfileRepository(session)
            # Count existing workspace profiles for naming
            existing = repo.list_by_workspace(workspace_id)
            name = "Default" if not existing else f"Voice Profile {len(existing) + 1}"
            slug = _generate_slug(name)
            counter = 1
            while repo.get_by_slug(slug, workspace_id=workspace_id):
                counter += 1
                slug = f"{_generate_slug(name)}-{counter}"

            legacy_payload = {
                "tone": tone,
                "sentence_patterns": sentence_patterns,
                "vocabulary_level": vocabulary_level,
                "signature_phrases": signature_phrases,
                "storytelling_style": storytelling_style,
                "emotional_register": emotional_register,
                "raw_analysis": raw_analysis,
            }
            record = VoiceProfileCreate(
                name=name,
                slug=slug,
                description=_encode_legacy_voice_profile(legacy_payload),
                is_preset=False,
                tone_description=tone,
                signature_phrases=signature_phrases,
                word_choices=vocabulary_level,
                example_excerpts=sentence_patterns,
                avoid_patterns=storytelling_style,
                workspace_id=workspace_id,
                user_id=user_id,
            )
            profile = repo.create(record)
            return str(profile.id)

    def get_voice_profile(
        self, user_id: Union[str, UUID]
    ) -> Optional[VoiceProfileResponse]:
        """Get user's default voice profile record."""
        uid = normalize_user_id(user_id)
        if not uid:
            return None
        default_id = self._default_voice_profile_id(uid)
        with get_session() as session:
            repo = VoiceProfileRepository(session)
            profile = None
            if default_id:
                profile = repo.get(default_id)
            if not profile:
                profiles = session.exec(
                    select(VoiceProfile)
                    .where(not VoiceProfile.is_preset)
                    .order_by(VoiceProfile.created_at.desc())
                ).all()
                profile = profiles[0] if profiles else None
            if not profile:
                return None
            return self._voice_profile_response(profile, default_id)

    def get_voice_profile_by_id(self, profile_id: Union[str, UUID]):
        """Get a voice profile by ID."""
        pid = coerce_uuid(profile_id)
        if not pid:
            return None
        with get_session() as session:
            profile = session.get(VoiceProfile, pid)
            if not profile:
                return None
            return self._voice_profile_response(profile, None)

    def get_all_voice_profiles(self, user_id: Union[str, UUID]):
        """Get all voice profiles for a user."""
        uid = normalize_user_id(user_id)
        if not uid:
            return []
        default_id = self._default_voice_profile_id(uid)
        with get_session() as session:
            profiles = session.exec(
                select(VoiceProfile)
                .where(not VoiceProfile.is_preset)
                .order_by(VoiceProfile.created_at.desc())
            ).all()
            return [self._voice_profile_response(p, default_id) for p in profiles]

    def update_voice_profile(self, profile_id: Union[str, UUID], **kwargs) -> None:
        """Update voice profile fields."""
        pid = coerce_uuid(profile_id)
        if not pid:
            return
        with get_session() as session:
            profile = session.get(VoiceProfile, pid)
            if not profile:
                return
            legacy = _decode_legacy_voice_profile(profile.description)
            for key in (
                "tone",
                "sentence_patterns",
                "vocabulary_level",
                "signature_phrases",
                "storytelling_style",
                "emotional_register",
                "raw_analysis",
            ):
                if key in kwargs:
                    legacy[key] = kwargs[key]

            profile.description = _encode_legacy_voice_profile(legacy)
            if "tone" in kwargs:
                profile.tone_description = kwargs["tone"]
            if "signature_phrases" in kwargs:
                profile.signature_phrases = kwargs["signature_phrases"]
            if "vocabulary_level" in kwargs:
                profile.word_choices = kwargs["vocabulary_level"]
            if "sentence_patterns" in kwargs:
                profile.example_excerpts = kwargs["sentence_patterns"]
            if "storytelling_style" in kwargs:
                profile.avoid_patterns = kwargs["storytelling_style"]

            session.add(profile)
            session.commit()

    def set_default_voice_profile(
        self, user_id: Union[str, UUID], profile_id: Union[str, UUID]
    ) -> None:
        """Set a voice profile as the default by attaching to the user's goal."""
        uid = normalize_user_id(user_id)
        pid = coerce_uuid(profile_id)
        if not uid or not pid:
            return
        with get_session() as session:
            repo = GoalRepository(session)
            goal = repo.get_by_user(uid)
            if not goal:
                goal = repo.create(GoalCreate(user_id=uid))
            goal.voice_profile_id = pid
            session.add(goal)
            session.commit()

    def clone_voice_profile(self, profile_id: Union[str, UUID], new_name: str) -> str:
        """Clone a voice profile with a new name."""
        pid = coerce_uuid(profile_id)
        if not pid:
            raise ValueError("Invalid profile_id")
        with get_session() as session:
            repo = VoiceProfileRepository(session)
            profile = repo.get(pid)
            if not profile:
                raise ValueError("Voice profile not found")
            slug = _generate_slug(new_name)
            counter = 1
            while repo.get_by_slug(slug):
                counter += 1
                slug = f"{_generate_slug(new_name)}-{counter}"
            record = VoiceProfileCreate(
                name=new_name,
                slug=slug,
                description=profile.description,
                is_preset=False,
                tone_description=profile.tone_description,
                signature_phrases=profile.signature_phrases,
                word_choices=profile.word_choices,
                example_excerpts=profile.example_excerpts,
                avoid_patterns=profile.avoid_patterns,
            )
            cloned = repo.create(record)
            return str(cloned.id)

    def delete_voice_profile(self, profile_id: Union[str, UUID]) -> None:
        """Delete a voice profile."""
        pid = coerce_uuid(profile_id)
        if not pid:
            return
        with get_session() as session:
            repo = VoiceProfileRepository(session)
            repo.delete(pid)

    # =========================================================================
    # Constants
    # =========================================================================

    @staticmethod
    def get_voice_prompts() -> list[dict]:
        """Get available voice learning prompts."""
        return VOICE_PROMPTS

    @staticmethod
    def get_content_styles() -> list[dict]:
        """Get available content styles."""
        return CONTENT_STYLES

    @staticmethod
    def get_post_shapes() -> list[dict]:
        """Get available post shapes."""
        return POST_SHAPES
