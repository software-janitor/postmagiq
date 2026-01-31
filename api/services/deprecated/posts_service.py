"""Service to manage post metadata using database.

Primary source: Database (posts, chapters tables)
Legacy support: Can import from markdown content tracker
"""

import re
from pathlib import Path
from typing import Optional, Union
from uuid import UUID

from pydantic import BaseModel
from sqlmodel import select

from runner.content.ids import normalize_user_id
from runner.content.repository import ChapterRepository, PostRepository
from runner.db.engine import get_session
from runner.db.models import Chapter, ChapterCreate, Post, PostCreate


class PostMetadata(BaseModel):
    """Metadata for a single post (API response model)."""

    post_id: str  # e.g., "post_07"
    post_number: int
    chapter: int
    topic: str
    shape: Optional[str] = None  # FULL, OBSERVATION, SHORT, PARTIAL, REVERSAL
    cadence: Optional[str] = None  # Teaching, Field Note
    entry_point: Optional[str] = None
    status: str
    story_used: Optional[str] = None
    enemy: str  # Chapter enemy
    guidance: str  # Suggestions for raw story


# Shape guidance
SHAPE_GUIDANCE = {
    "FULL": """Tell a complete story with all 5 elements:
1. The Failure - What broke? What went wrong?
2. The Misunderstanding - What do people assume is the fix?
3. AI Amplification - How did AI make it worse?
4. The Fix - What resolved it?
5. The Scar - What did you learn?

Include specific details: error messages, hours lost, tools used.""",
    "PARTIAL": """Tell a story WITHOUT resolution:
1. The Failure - What broke?
2. The Misunderstanding - What's the wrong assumption?
3. AI Amplification - How did AI make it worse?

Do NOT include a fix or lesson. End messy. "I don't have a clean answer yet."
Include: specific errors, frustrations, what you tried that didn't work.""",
    "OBSERVATION": """Share something you noticed. No backstory needed, no lesson required.
- What did you observe?
- Why did it catch your attention?
- What questions does it raise?

End with a question or open thought. "I'm not sure what to make of this yet."
Keep it short and genuine.""",
    "SHORT": """One idea, under 200 words. No wrap-up needed.
- What's the single insight?
- One concrete example or moment
- Just end. No conclusion.""",
    "REVERSAL": """Update or contradict something you said before.
- What did you previously believe?
- What changed your thinking?
- What do you believe now?

Reference the original post. "I was wrong about X."
Be specific about what shifted.""",
}

# Default chapter enemies (used if not stored in database)
DEFAULT_CHAPTER_ENEMIES = {
    1: "Tool-first AI adoption (buying tools without an operating model)",
    2: "Unbounded autonomous agents (no blast radius, no checkpoints)",
    3: "AI adoption without domain expertise (AI can't validate what humans don't understand)",
    4: "Prompt engineering as strategy (optimizing prompts instead of building systems)",
    5: "Prompt engineering as strategy (optimizing prompts instead of building systems)",
    6: "AI adoption without enablement (shipping AI without training engineers)",
    7: "Scaling AI systems (guardrails + adoption at scale)",
    8: "Synthesis (all enemies)",
}


class PostsService:
    """Service for managing posts using SQLModel."""

    def get_all_posts(
        self, user_id: Optional[Union[str, UUID]] = None
    ) -> list[PostMetadata]:
        """Get all posts for a user."""
        uid = normalize_user_id(user_id)
        if not uid:
            return []
        with get_session() as session:
            post_repo = PostRepository(session)
            chapter_repo = ChapterRepository(session)
            posts = post_repo.list_by_user(uid)
            chapters = {c.id: c for c in chapter_repo.list_by_user(uid)}
            return [self._to_metadata(p, chapters) for p in posts]

    def get_available_posts(
        self, user_id: Optional[Union[str, UUID]] = None
    ) -> list[PostMetadata]:
        """Get posts that need stories or are not started."""
        uid = normalize_user_id(user_id)
        if not uid:
            return []
        with get_session() as session:
            chapters = {c.id: c for c in ChapterRepository(session).list_by_user(uid)}
            posts = session.exec(
                select(Post)
                .where(
                    Post.user_id == uid,
                    Post.status.in_(["not_started", "needs_story", "draft"]),
                )
                .order_by(Post.post_number)
            ).all()
            return [self._to_metadata(p, chapters) for p in posts]

    def get_post(
        self, user_id: Union[str, UUID], post_number: int
    ) -> Optional[PostMetadata]:
        """Get a specific post by number."""
        uid = normalize_user_id(user_id)
        if not uid:
            return None
        with get_session() as session:
            post_repo = PostRepository(session)
            chapter_repo = ChapterRepository(session)
            post = post_repo.get_by_number(uid, post_number)
            if not post:
                return None
            chapters = {c.id: c for c in chapter_repo.list_by_user(uid)}
            return self._to_metadata(post, chapters)

    def update_post_status(
        self, user_id: Union[str, UUID], post_number: int, status: str
    ) -> bool:
        """Update a post's status."""
        uid = normalize_user_id(user_id)
        if not uid:
            return False
        with get_session() as session:
            post_repo = PostRepository(session)
            post = post_repo.get_by_number(uid, post_number)
            if not post:
                return False
            post_repo.update_status(post.id, status)
            return True

    def update_post(
        self, user_id: Union[str, UUID], post_number: int, **kwargs
    ) -> bool:
        """Update post fields."""
        uid = normalize_user_id(user_id)
        if not uid:
            return False
        with get_session() as session:
            post_repo = PostRepository(session)
            post = post_repo.get_by_number(uid, post_number)
            if not post:
                return False
            for key, value in kwargs.items():
                if hasattr(post, key):
                    setattr(post, key, value)
            session.add(post)
            session.commit()
            return True

    def _to_metadata(
        self,
        post: Post,
        chapters: dict[UUID, Chapter],
    ) -> PostMetadata:
        """Convert PostRecord to PostMetadata."""
        chapter = chapters.get(post.chapter_id)
        chapter_num = chapter.chapter_number if chapter else 0

        # Get enemy from chapter theme or default
        if chapter and chapter.theme:
            enemy = chapter.theme
        else:
            enemy = DEFAULT_CHAPTER_ENEMIES.get(chapter_num, "")

        # Generate guidance if not stored
        guidance = post.guidance
        if not guidance:
            shape_guidance = SHAPE_GUIDANCE.get(post.shape, SHAPE_GUIDANCE["FULL"])
            guidance = f"**Chapter Enemy:** {enemy}\n\n{shape_guidance}"

        return PostMetadata(
            post_id=f"post_{post.post_number:02d}",
            post_number=post.post_number,
            chapter=chapter_num,
            topic=post.topic or f"Chapter {chapter_num} Post {post.post_number}",
            shape=post.shape,
            cadence=post.cadence,
            entry_point=post.entry_point,
            status=post.status,
            story_used=post.story_used,
            enemy=enemy,
            guidance=guidance,
        )


# =============================================================================
# Legacy Support Functions
# =============================================================================


def _parse_table_header(header_line: str) -> dict[str, int]:
    """Parse table header to get column indices."""
    columns = [col.strip().lower() for col in header_line.split("|")]
    indices = {}
    for i, col in enumerate(columns):
        if col in ("post", "#"):
            indices["post"] = i
        elif col == "topic":
            indices["topic"] = i
        elif col == "shape":
            indices["shape"] = i
        elif col == "cadence":
            indices["cadence"] = i
        elif col in ("entry point", "entry"):
            indices["entry_point"] = i
        elif col == "status":
            indices["status"] = i
        elif col in ("story used", "story"):
            indices["story_used"] = i
        elif col == "resolved?":
            indices["resolved"] = i
    return indices


def import_from_markdown(
    tracker_path: str,
    user_id: Optional[Union[str, UUID]] = None,
) -> int:
    """Import posts from markdown content tracker into database.

    This is a one-time migration helper. Returns count of posts imported.
    """
    uid = normalize_user_id(user_id)
    if not uid:
        return 0
    path = Path(tracker_path)
    if not path.exists():
        return 0

    content = path.read_text()
    imported = 0

    # Parse chapter by chapter
    chapter_pattern = (
        r"## Chapter (\d+)[^\n]*\n+\*\*Weeks[^|]*\|\s*(?:Enemy:\s*)?([^*]+)\*\*"
    )

    with get_session() as session:
        chapter_repo = ChapterRepository(session)
        post_repo = PostRepository(session)

        for chapter_match in re.finditer(chapter_pattern, content):
            chapter_num = int(chapter_match.group(1))
            chapter_enemy = chapter_match.group(2).strip()

            # Get or create chapter
            chapters = chapter_repo.list_by_user(uid)
            chapter = next(
                (c for c in chapters if c.chapter_number == chapter_num), None
            )

            if not chapter:
                chapter_record = ChapterCreate(
                    user_id=uid,
                    chapter_number=chapter_num,
                    title=f"Chapter {chapter_num}",
                    theme=chapter_enemy,
                    theme_description=DEFAULT_CHAPTER_ENEMIES.get(chapter_num, ""),
                )
                chapter = chapter_repo.create(chapter_record)
            else:
                if not chapter.theme:
                    chapter.theme = chapter_enemy
                    session.add(chapter)
                    session.commit()

            # Find the table after this chapter header
            chapter_start = chapter_match.end()
            next_chapter = content.find("## Chapter", chapter_start)
            if next_chapter == -1:
                next_chapter = len(content)

            chapter_content = content[chapter_start:next_chapter]

            # Find table header
            lines = chapter_content.split("\n")
            col_indices = {}
            for line in lines:
                if line.startswith("|") and "Post" in line and "Topic" in line:
                    col_indices = _parse_table_header(line)
                    break

            # Parse table rows
            table_row_pattern = r"^\|[^|]*\d+[^|]*\|"
            for line in lines:
                if not re.match(table_row_pattern, line.strip()):
                    continue
                if "---" in line:
                    continue

                columns = [c.strip() for c in line.split("|")]

                def get_col(name: str) -> Optional[str]:
                    idx = col_indices.get(name)
                    if idx is not None and idx < len(columns):
                        val = columns[idx].strip()
                        return val if val and val not in ("—", "TBD", "") else None
                    return None

                post_col = get_col("post")
                if not post_col or not post_col.isdigit():
                    continue
                post_num = int(post_col)

                # Check if post already exists
                existing = post_repo.get_by_number(uid, post_num)
                if existing:
                    continue  # Skip existing posts

                topic = get_col("topic") or f"Chapter {chapter_num} Post {post_num}"
                shape = get_col("shape")
                cadence = get_col("cadence")
                entry_point = get_col("entry_point")
                status = get_col("status") or "not_started"
                story_used = get_col("story_used")

                # Normalize status
                status_lower = status.lower()
                if "not started" in status_lower:
                    status = "not_started"
                elif "needs story" in status_lower:
                    status = "needs_story"
                elif "draft" in status_lower or "in progress" in status_lower:
                    status = "draft"
                elif "ready" in status_lower:
                    status = "ready"
                elif "published" in status_lower:
                    status = "published"

                post_record = PostCreate(
                    user_id=uid,
                    chapter_id=chapter.id,
                    post_number=post_num,
                    topic=topic,
                    shape=shape,
                    cadence=cadence,
                    entry_point=entry_point,
                    status=status,
                    story_used=story_used,
                )
                post_repo.create(post_record)
                imported += 1

        session.commit()

    return imported


# =============================================================================
# Legacy API (backward compatibility)
# =============================================================================

# Default service instance
_default_service: Optional[PostsService] = None


def _get_service() -> PostsService:
    """Get or create default service instance."""
    global _default_service
    if _default_service is None:
        _default_service = PostsService()
    return _default_service


def parse_content_tracker(tracker_path: str) -> list[PostMetadata]:
    """Legacy function: Get all posts from database.

    Note: tracker_path is kept for backward compatibility but no longer used.
    Use import_posts_from_markdown() to explicitly import from markdown.
    """
    service = _get_service()
    return service.get_all_posts()


def get_available_posts(tracker_path: str) -> list[PostMetadata]:
    """Legacy function: Get posts that need work from database.

    Note: tracker_path is kept for backward compatibility but no longer used.
    Use import_posts_from_markdown() to explicitly import from markdown.
    """
    service = _get_service()
    return service.get_available_posts()


def import_posts_from_markdown(
    tracker_path: str, user_id: Optional[Union[str, UUID]] = None
) -> int:
    """Explicitly import posts from markdown content tracker.

    Call this function directly when you want to import from markdown.
    Returns the count of posts imported.
    """
    return import_from_markdown(tracker_path, user_id)


def get_all_posts(tracker_path: str) -> list[PostMetadata]:
    """Legacy function: Get all posts from database.

    Note: tracker_path is kept for backward compatibility but no longer used.
    """
    return parse_content_tracker(tracker_path)
