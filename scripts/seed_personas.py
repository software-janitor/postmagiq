#!/usr/bin/env python3
"""Seed default system personas into the database.

Creates system personas that are available to all users.
System personas have is_system=True and use a dedicated system user.

Usage:
    python scripts/seed_personas.py

    Or via make:
    make seed-personas
"""

import os
import sys
from pathlib import Path

# Ensure we can import from the project
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set default DATABASE_URL for local development
os.environ.setdefault("DATABASE_URL", "postgresql://orchestrator:orchestrator_dev@localhost:6432/orchestrator")

from uuid import uuid4
from sqlmodel import Session, select
from runner.db.engine import engine, init_db
from runner.db.models import WorkflowPersona
from runner.content.ids import get_system_user_id


# =============================================================================
# Persona Definitions
# =============================================================================

PERSONA_DEFINITIONS = [
    {
        "name": "Writer",
        "slug": "writer",
        "description": "Drafting agent that writes LinkedIn posts from source material. No questions, just output.",
        "model_tier": "writer",
    },
    {
        "name": "Auditor",
        "slug": "auditor",
        "description": "Quality gate agent that audits drafts against voice guidelines and content strategy.",
        "model_tier": "auditor",
    },
    {
        "name": "Synthesizer",
        "slug": "synthesizer",
        "description": "Synthesis agent that combines multiple drafts into a final polished post.",
        "model_tier": "writer",
    },
    {
        "name": "Story Processor",
        "slug": "story-processor",
        "description": "Extracts 5 post elements from raw story material and structures them.",
        "model_tier": "writer",
    },
    {
        "name": "Story Reviewer",
        "slug": "story-reviewer",
        "description": "Reviews processed stories for completeness and quality before drafting.",
        "model_tier": "auditor",
    },
    {
        "name": "Input Validator",
        "slug": "input-validator",
        "description": "Validates input material to ensure it has sufficient content for a post.",
        "model_tier": "auditor",
    },
    {
        "name": "AI Detector",
        "slug": "ai-detector",
        "description": "Checks drafts for AI-sounding patterns and suggests improvements.",
        "model_tier": "auditor",
    },
]


def load_persona_content(slug: str) -> str:
    """Load persona content from markdown file in prompts directory."""
    prompts_dir = Path(__file__).parent.parent / "prompts"

    # Map slug to filename (handle hyphenated slugs)
    filename = f"{slug.replace('-', '_')}_persona.md"
    file_path = prompts_dir / filename

    if file_path.exists():
        return file_path.read_text()

    # Fallback: return empty content (persona exists but no detailed prompt)
    return ""


def seed_personas():
    """Seed system personas into the database."""
    init_db()

    system_user_id = get_system_user_id()

    with Session(engine) as session:
        created = 0
        updated = 0
        skipped = 0

        for persona_def in PERSONA_DEFINITIONS:
            slug = persona_def["slug"]

            # Check if system persona already exists
            existing = session.exec(
                select(WorkflowPersona).where(
                    WorkflowPersona.slug == slug,
                    WorkflowPersona.is_system == True,
                )
            ).first()

            # Load content from file
            content = load_persona_content(slug)

            if existing:
                # Update content if it changed
                if existing.content != content and content:
                    existing.content = content
                    existing.description = persona_def["description"]
                    existing.model_tier = persona_def["model_tier"]
                    session.add(existing)
                    updated += 1
                    print(f"  Updated: {persona_def['name']} ({slug})")
                else:
                    skipped += 1
                    print(f"  Skipped: {persona_def['name']} ({slug}) - already exists")
            else:
                # Create new system persona
                persona = WorkflowPersona(
                    id=uuid4(),
                    user_id=system_user_id,
                    name=persona_def["name"],
                    slug=slug,
                    description=persona_def["description"],
                    content=content,
                    is_system=True,
                    model_tier=persona_def["model_tier"],
                    workspace_id=None,  # System personas have no workspace
                )
                session.add(persona)
                created += 1
                print(f"  Created: {persona_def['name']} ({slug})")

        session.commit()

        print(f"\nSummary: {created} created, {updated} updated, {skipped} skipped")


if __name__ == "__main__":
    print("Seeding system personas...")
    seed_personas()
    print("Done!")
