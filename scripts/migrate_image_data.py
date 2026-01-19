#!/usr/bin/env python3
"""Migrate image configuration data from SQLite to PostgreSQL."""

import sqlite3
from datetime import datetime
from uuid import uuid4
import psycopg2

SQLITE_PATH = "/home/mg/code/linkedin_articles/deprecated/data/content_strategy.db"
POSTGRES_URL = "postgresql://orchestrator:orchestrator_dev@localhost:5433/orchestrator"


def migrate():
    sqlite_conn = sqlite3.connect(SQLITE_PATH)
    sqlite_conn.row_factory = sqlite3.Row
    sq = sqlite_conn.cursor()

    pg = psycopg2.connect(POSTGRES_URL)
    pg.autocommit = False
    pc = pg.cursor()

    # Get workspace
    pc.execute("SELECT id FROM workspaces WHERE slug = 'test-owner'")
    ws = pc.fetchone()[0]

    # Get default user
    pc.execute("SELECT id FROM users WHERE email = 'owner@example.com'")
    default_user = pc.fetchone()[0]

    print(f"Workspace: {ws}")
    print(f"Default user: {default_user}")

    try:
        # Image scenes
        print("\nMigrating image_scenes...")
        sq.execute("SELECT * FROM image_scenes")
        count = 0
        for row in sq.fetchall():
            pc.execute("""
                INSERT INTO image_scenes (id, user_id, workspace_id, code, name, sentiment,
                    viewpoint, description, is_hardware_only, no_desk_props, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT DO NOTHING
            """, (
                str(uuid4()),
                str(default_user),
                str(ws),
                row['code'],
                row['name'] if row['name'] else row['code'],  # Use code as name if name is missing
                row['sentiment'] or 'neutral',
                row['viewpoint'] or 'medium',
                row['description'] or '',
                bool(row['is_hardware_only']) if row['is_hardware_only'] is not None else False,
                bool(row['no_desk_props']) if row['no_desk_props'] is not None else False,
                row['created_at'] or datetime.utcnow(),
            ))
            count += 1
        print(f"  Migrated {count} image_scenes")

        # Image poses
        print("Migrating image_poses...")
        sq.execute("SELECT * FROM image_poses")
        count = 0
        for row in sq.fetchall():
            pc.execute("""
                INSERT INTO image_poses (id, user_id, workspace_id, code, sentiment,
                    description, emotional_note, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT DO NOTHING
            """, (
                str(uuid4()),
                str(default_user),
                str(ws),
                row['code'],
                row['sentiment'] or 'neutral',
                row['description'] or '',
                row['emotional_note'],
                row['created_at'] or datetime.utcnow(),
            ))
            count += 1
        print(f"  Migrated {count} image_poses")

        # Image outfits
        print("Migrating image_outfits...")
        sq.execute("SELECT * FROM image_outfits")
        count = 0
        for row in sq.fetchall():
            pc.execute("""
                INSERT INTO image_outfits (id, user_id, workspace_id, vest, shirt, pants, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT DO NOTHING
            """, (
                str(uuid4()),
                str(default_user),
                str(ws),
                row['vest'] or '',
                row['shirt'] or '',
                row['pants'] or '',
                row['created_at'] or datetime.utcnow(),
            ))
            count += 1
        print(f"  Migrated {count} image_outfits")

        # Image props
        print("Migrating image_props...")
        sq.execute("SELECT * FROM image_props")
        count = 0
        for row in sq.fetchall():
            pc.execute("""
                INSERT INTO image_props (id, user_id, workspace_id, category, description, context, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT DO NOTHING
            """, (
                str(uuid4()),
                str(default_user),
                str(ws),
                row['category'] or 'general',
                row['description'] or '',
                row['context'] or 'any',
                row['created_at'] or datetime.utcnow(),
            ))
            count += 1
        print(f"  Migrated {count} image_props")

        # Image characters
        print("Migrating image_characters...")
        sq.execute("SELECT * FROM image_characters")
        count = 0
        for row in sq.fetchall():
            pc.execute("""
                INSERT INTO image_characters (id, user_id, workspace_id, character_type,
                    appearance, face_details, clothing_rules, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT DO NOTHING
            """, (
                str(uuid4()),
                str(default_user),
                str(ws),
                row['character_type'] or 'protagonist',
                row['appearance'] or '',
                row['face_details'],
                row['clothing_rules'],
                row['created_at'] or datetime.utcnow(),
            ))
            count += 1
        print(f"  Migrated {count} image_characters")

        pg.commit()
        print("\n" + "=" * 50)
        print("✅ Image data migration completed successfully!")
        print("=" * 50)

    except Exception as e:
        pg.rollback()
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        sqlite_conn.close()
        pg.close()


if __name__ == "__main__":
    migrate()
