#!/usr/bin/env python3
"""Seed voice profile presets into the database.

Parses voice profiles from prompts/voice_profiles/ and creates
system preset records (is_preset=True, workspace_id=None).

Usage:
    python scripts/seed_voice_profiles.py

    Or via make:
    make seed-voices
"""

import os
import re
import sys
from pathlib import Path

# Ensure we can import from the project
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set default DATABASE_URL for local development
os.environ.setdefault("DATABASE_URL", "postgresql://orchestrator:orchestrator_dev@localhost:6432/orchestrator")

from uuid import uuid4
from sqlmodel import Session, select
from runner.db.engine import engine, init_db
from runner.db.models import VoiceProfile


def parse_voice_profile(file_path: Path) -> dict:
    """Parse a voice profile from its markdown file.

    Extracts structured fields from ## sections:
    - Your Voice -> tone_description
    - Signature Phrases -> signature_phrases
    - Word Choices -> word_choices
    - Example Excerpts -> example_excerpts
    - Avoid -> avoid_patterns
    """
    content = file_path.read_text()

    # Extract title from first line
    title_match = re.match(r"#\s*Voice Profile:\s*(.+)", content)
    name = title_match.group(1).strip() if title_match else file_path.stem.replace("-", " ").title()

    # Extract description from first paragraph after title
    desc_match = re.search(r"^#.+\n+(.+?)(?:\n\n|\n---)", content, re.MULTILINE)
    description = desc_match.group(1).strip() if desc_match else ""

    # Extract sections by ## headers
    sections = {}
    current_section = None
    current_content = []

    for line in content.split("\n"):
        if line.startswith("## "):
            if current_section:
                sections[current_section] = "\n".join(current_content).strip()
            current_section = line[3:].strip()
            current_content = []
        elif current_section:
            current_content.append(line)

    if current_section:
        sections[current_section] = "\n".join(current_content).strip()

    slug = file_path.stem  # e.g., "servant-leader"

    return {
        "name": name,
        "slug": slug,
        "description": description,
        "tone_description": sections.get("Your Voice", ""),
        "signature_phrases": sections.get("Signature Phrases (use sparingly)", ""),
        "word_choices": sections.get("Word Choices", ""),
        "example_excerpts": sections.get("Example Excerpts", ""),
        "avoid_patterns": sections.get("Avoid", ""),
    }


def seed_voice_profiles():
    """Seed voice profile presets into the database."""
    print("Initializing database...")
    init_db()

    profiles_dir = Path(__file__).parent.parent / "prompts" / "voice_profiles"
    if not profiles_dir.exists():
        print(f"ERROR: Voice profiles directory not found: {profiles_dir}")
        sys.exit(1)

    # Parse all .md files in voice_profiles/
    profiles_to_seed = []
    for md_file in sorted(profiles_dir.glob("*.md")):
        print(f"  Parsing: {md_file.name}")
        profile_data = parse_voice_profile(md_file)
        profiles_to_seed.append(profile_data)

    if not profiles_to_seed:
        print("No voice profile files found.")
        return

    with Session(engine) as session:
        created_count = 0
        updated_count = 0

        for profile_data in profiles_to_seed:
            # Check if profile exists by slug (system presets have workspace_id=None)
            existing = session.exec(
                select(VoiceProfile).where(
                    VoiceProfile.slug == profile_data["slug"],
                    VoiceProfile.workspace_id == None,  # noqa: E711
                )
            ).first()

            if existing:
                print(f"  Updating preset: {profile_data['name']} (slug: {profile_data['slug']})")
                for key, value in profile_data.items():
                    setattr(existing, key, value)
                existing.is_preset = True
                session.add(existing)
                updated_count += 1
            else:
                print(f"  Creating preset: {profile_data['name']} (slug: {profile_data['slug']})")
                profile = VoiceProfile(
                    id=uuid4(),
                    user_id=None,  # System presets have no owner
                    workspace_id=None,
                    is_preset=True,
                    **profile_data,
                )
                session.add(profile)
                created_count += 1

        session.commit()

        print(f"\nCreated: {created_count}")
        print(f"Updated: {updated_count}")
        print(f"Total presets: {len(profiles_to_seed)}")


if __name__ == "__main__":
    seed_voice_profiles()
