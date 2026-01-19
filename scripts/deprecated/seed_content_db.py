#!/usr/bin/env python3
"""Seed the content database from the LinkedIn content tracker markdown."""

import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlmodel import select

from runner.content.ids import normalize_user_id
from runner.db.engine import get_session
from runner.db.models import User, Goal, Chapter, Post
from api.services.content_service import ContentService


# Chapter data extracted from the tracker
CHAPTERS = [
    {
        "chapter_number": 1,
        "title": "Why AI Adoption Fails Without Systems",
        "theme": "Tool-first AI adoption",
        "theme_description": "Buying tools without an operating model. No enablement, no training, no systems thinking.",
        "weeks_start": 1,
        "weeks_end": 6,
    },
    {
        "chapter_number": 2,
        "title": "Domain Boundaries as AI Blast-Radius Limits",
        "theme": "Unbounded autonomous agents",
        "theme_description": "No blast radius, no checkpoints, no human oversight. Fails in production.",
        "weeks_start": 7,
        "weeks_end": 13,
    },
    {
        "chapter_number": 3,
        "title": "Human Expertise as the Control Plane",
        "theme": "AI adoption without domain expertise",
        "theme_description": "AI can't validate what humans don't understand.",
        "weeks_start": 14,
        "weeks_end": 19,
    },
    {
        "chapter_number": 4,
        "title": "Planning: Where Leverage Is Created",
        "theme": "Prompt engineering as strategy",
        "theme_description": "Optimizing prompts instead of building systems.",
        "weeks_start": 20,
        "weeks_end": 26,
    },
    {
        "chapter_number": 5,
        "title": "Templates, Tooling, and Execution",
        "theme": "Prompt engineering as strategy",
        "theme_description": "Optimizing prompts instead of building systems.",
        "weeks_start": 27,
        "weeks_end": 33,
    },
    {
        "chapter_number": 6,
        "title": "AI Enablement at Scale",
        "theme": "AI adoption without enablement",
        "theme_description": "Shipping AI infrastructure without training engineers to use it. Adoption stalls.",
        "weeks_start": 34,
        "weeks_end": 40,
    },
    {
        "chapter_number": 7,
        "title": "Scaling AI Systems",
        "theme": "Scaling AI systems",
        "theme_description": "Guardrails and adoption at scale.",
        "weeks_start": 41,
        "weeks_end": 46,
    },
    {
        "chapter_number": 8,
        "title": "The Operating Model",
        "theme": "Synthesis",
        "theme_description": "All enemies combined - the complete operating model.",
        "weeks_start": 47,
        "weeks_end": 52,
    },
]

# Post data - extracted from tracker
# Format: (post_number, chapter, topic, shape, cadence, status, story_used)
POSTS = [
    # Chapter 1
    (1, 1, "AI doesn't fail — systems fail", "FULL", "Teaching", "published", "post_01"),
    (2, 1, "Tools don't solve systems problems", "FULL", "Teaching", "published", "post_02"),
    (3, 1, "Voice memo pipeline observation", "OBSERVATION", "Field Note", "ready", "voice_memo_pipeline"),
    (4, 1, "TBD", "FULL", "Teaching", "needs_story", None),
    (5, 1, "Why leverage comes from constraints", "FULL", "Teaching", "needs_story", None),
    (6, 1, "TBD", "SHORT", "Field Note", "needs_story", None),
    # Chapter 2
    (7, 2, "Why clear domain boundaries matter more with AI", None, None, "not_started", None),
    (8, 2, "Blast-radius limits for AI systems", None, None, "not_started", None),
    (9, 2, "Shared language for humans and AI", None, None, "not_started", None),
    (10, 2, "Invariants as executable constraints", None, None, "not_started", None),
    (11, 2, "Domain events as safe AI integration points", None, None, "not_started", None),
    (12, 2, "When AI can't debug what it built", None, None, "ready", "post_03"),
    (13, 2, "When strict boundaries aren't worth it", None, None, "not_started", None),
    # Chapter 3
    (14, 3, "Why domain expertise didn't become obsolete", None, None, "not_started", None),
    (15, 3, "Humans define correctness; AI accelerates execution", None, None, "not_started", None),
    (16, 3, "Training engineers to specify instead of prompt", None, None, "not_started", None),
    (17, 3, "Reviewing AI output as a domain expert", None, None, "not_started", None),
    (18, 3, "When humans must override AI decisions", None, None, "not_started", None),
    (19, 3, "Designing feedback loops between humans and AI", None, None, "not_started", None),
    # Chapter 4
    (20, 4, "Planning is the highest-leverage activity", "FULL", "Teaching", "needs_story", None),
    (21, 4, "The smaller the task, the smarter the AI", "FULL", "Teaching", "ready", "story_agent_fsm"),
    (22, 4, "AI-assisted backlog refinement", "OBSERVATION", "Field Note", "needs_story", None),
    (23, 4, "Turning epics into execution graphs", "FULL", "Teaching", "needs_story", None),
    (24, 4, "AI-assisted acceptance criteria writing", "SHORT", "Field Note", "needs_story", None),
    (25, 4, "Planning as a multi-agent coordination problem", "FULL", "Teaching", "needs_story", None),
    (26, 4, "Why fast execution without planning increases risk", "PARTIAL", "Field Note", "needs_story", None),
    # Chapter 5
    (27, 5, "Humans and AI as a distributed system", None, None, "ready", "post_04"),
    (28, 5, "Feature templates that guide humans and AI", None, None, "not_started", None),
    (29, 5, "Architecture decision records as long-term memory", None, None, "not_started", None),
    (30, 5, "Workflow and task runners AI can execute reliably", None, None, "not_started", None),
    (31, 5, "Designing workflows AI cannot misinterpret", None, None, "not_started", None),
    (32, 5, "Deterministic pipelines beat clever prompts", None, None, "not_started", None),
    (33, 5, "When automation should replace autonomy", None, None, "not_started", None),
    # Chapter 6
    (34, 6, "One set of rules for humans and AI", None, None, "not_started", None),
    (35, 6, "Linters, analyzers, and hooks as AI constraints", None, None, "not_started", None),
    (36, 6, "Security and data boundaries for AI systems", None, None, "not_started", None),
    (37, 6, "PR size limits and why they matter more with AI", None, None, "not_started", None),
    (38, 6, "Auditing AI-generated changes without slowing teams", None, None, "not_started", None),
    (39, 6, "Guardrails as velocity multipliers", None, None, "not_started", None),
    (40, 6, "The guardrail that backfired", None, None, "not_started", None),
    # Chapter 7
    (41, 7, "Governing human and AI developers together", None, None, "not_started", None),
    (42, 7, "Full-system audits versus component audits", None, None, "not_started", None),
    (43, 7, "Documentation as a first-class system", None, None, "not_started", None),
    (44, 7, "Keeping documentation accurate over time", None, None, "not_started", None),
    (45, 7, "Traceability across human and AI actions", None, None, "not_started", None),
    (46, 7, "Designing systems that are audit-ready by default", None, None, "not_started", None),
    # Chapter 8
    (47, 8, "Platform teams as AI enablement engines", None, None, "not_started", None),
    (48, 8, "Centralized standards, decentralized execution", None, None, "not_started", None),
    (49, 8, "Measuring leverage instead of output", None, None, "not_started", None),
    (50, 8, "Detecting AI adoption failure modes early", None, None, "not_started", None),
    (51, 8, "What a mature human + AI delivery organization looks like", None, None, "not_started", None),
    (52, 8, "The complete systems-of-systems playbook", None, None, "not_started", None),
]


def seed_database(force: bool = False):
    """Seed the content database with tracker data."""
    print("Seeding database (PostgreSQL)")

    service = ContentService()
    email = "matthew@example.com"
    existing_user = service.get_user_by_email(email)

    if existing_user and not force:
        print("Database already seeded. Use --force to reseed.")
        return

    if existing_user and force:
        uid = normalize_user_id(existing_user.id)
        if uid:
            with get_session() as session:
                for model in (Post, Chapter, Goal, User):
                    rows = session.exec(
                        select(model).where(model.user_id == uid) if hasattr(model, "user_id") else select(model).where(model.id == uid)
                    ).all()
                    for row in rows:
                        session.delete(row)
                session.commit()

    # Create user
    user_id = service.get_or_create_user("Matthew Garcia", email=email)
    print(f"Created user: Matthew Garcia (ID: {user_id})")

    # Create goal
    goal_id = service.create_goal(
        user_id=user_id,
        positioning="Distinguished/Partner-level AI systems leader",
        signature_thesis="AI fails without systems. I design the platforms that make it work at enterprise scale—and train engineers to use them.",
        target_audience="Engineering leaders, Senior developers, Tech founders",
        content_style="teaching",
        onboarding_mode="imported",
    )
    print(f"Created goal (ID: {goal_id})")

    # Create chapters
    chapter_ids = {}
    for chapter_data in CHAPTERS:
        chapter_id = service.create_chapter(
            user_id=user_id,
            chapter_number=chapter_data["chapter_number"],
            title=chapter_data["title"],
            description=f"Weeks {chapter_data['weeks_start']}-{chapter_data['weeks_end']}",
            theme=chapter_data["theme"],
            theme_description=chapter_data["theme_description"],
            weeks_start=chapter_data["weeks_start"],
            weeks_end=chapter_data["weeks_end"],
        )
        chapter_ids[chapter_data["chapter_number"]] = chapter_id
        print(f"Created Chapter {chapter_data['chapter_number']}: {chapter_data['title']}")

    # Create posts
    for post_data in POSTS:
        post_num, chapter_num, topic, shape, cadence, status, story_used = post_data
        service.create_post(
            user_id=user_id,
            chapter_id=chapter_ids[chapter_num],
            post_number=post_num,
            topic=topic,
            shape=shape,
            cadence=cadence,
            status=status,
            story_used=story_used,
        )
        print(f"  Post {post_num}: {topic[:40]}... ({status})")

    print("\nDatabase seeded successfully!")
    print("  - 1 user")
    print("  - 1 goal")
    print(f"  - {len(CHAPTERS)} chapters")
    print(f"  - {len(POSTS)} posts")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Seed content database from tracker")
    parser.add_argument(
        "--db-path",
        default="workflow/content/content.db",
        help="Legacy SQLite path (ignored)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force reseed (deletes existing data)",
    )

    args = parser.parse_args()

    if args.force:
        print("Force mode enabled: existing Postgres data will be cleared for the seed user.")

    seed_database(force=args.force)


if __name__ == "__main__":
    main()
