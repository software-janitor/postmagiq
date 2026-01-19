#!/usr/bin/env python3
"""Seed default sentiments into the database.

Creates system sentiments that are available to all users.
Sentiments define emotional states for image prompt generation.

Usage:
    python scripts/seed_sentiments.py

    Or via make:
    make seed-sentiments
"""

import os
import sys
from pathlib import Path

# Ensure we can import from the project
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set default DATABASE_URL for local development
os.environ.setdefault("DATABASE_URL", "postgresql://orchestrator:orchestrator_dev@localhost:6432/orchestrator")

import json
from uuid import uuid4
from sqlmodel import Session, select
from runner.db.engine import engine, init_db
from runner.db.models import Sentiment
from runner.content.ids import get_system_user_id


# =============================================================================
# Default Sentiment Definitions
# =============================================================================

DEFAULT_SENTIMENTS = [
    {
        "name": "SUCCESS",
        "description": "Post ends with resolution, lesson learned, or achievement",
        "color_hint": "#10b981",  # Green
        "robot_color": "CYAN/BLUE trim - represents assistance, completion",
        "robot_eyes": "happy face (simple upturned curved line for smile)",
        "robot_posture": "hovering confidently, screen showing thumbs up or checkmark",
    },
    {
        "name": "FAILURE",
        "description": "Post ends mid-crisis, frustration, or unresolved failure",
        "color_hint": "#ef4444",  # Red
        "robot_color": "RED trim - represents danger, failure state",
        "robot_eyes": "distressed face (downturned curved line, X eyes)",
        "robot_posture": "recoiling, sparking, or crashed on desk",
    },
    {
        "name": "UNRESOLVED",
        "description": "Post ends with tradeoff, ongoing challenge, or contemplation",
        "color_hint": "#f59e0b",  # Amber
        "robot_color": "AMBER/YELLOW trim - represents caution, thinking",
        "robot_eyes": "thinking face (three animated dots, loading indicator)",
        "robot_posture": "tilted slightly, hovering with amber glow, waiting",
    },
]


def seed_sentiments():
    """Seed default sentiments into the database."""
    init_db()

    system_user_id = get_system_user_id()

    with Session(engine) as session:
        created = 0
        skipped = 0

        for sentiment_def in DEFAULT_SENTIMENTS:
            name = sentiment_def["name"]

            # Check if sentiment already exists for system user
            existing = session.exec(
                select(Sentiment).where(
                    Sentiment.user_id == system_user_id,
                    Sentiment.name == name,
                )
            ).first()

            if existing:
                skipped += 1
                print(f"  Skipped: {name} - already exists")
                continue

            # Create new sentiment with legacy encoding
            legacy_data = {
                "description": sentiment_def["description"],
                "color_hint": sentiment_def["color_hint"],
                "robot_color": sentiment_def["robot_color"],
                "robot_eyes": sentiment_def["robot_eyes"],
                "robot_posture": sentiment_def["robot_posture"],
                "is_system": True,
            }

            record = Sentiment(
                id=uuid4(),
                user_id=system_user_id,
                name=name,
                description=json.dumps(legacy_data),
                color_code=sentiment_def["color_hint"],
            )
            session.add(record)
            created += 1
            print(f"  Created: {name}")

        session.commit()
        print(f"\nSummary: {created} created, {skipped} skipped")


if __name__ == "__main__":
    print("Seeding default sentiments...")
    seed_sentiments()
    print("Done!")
