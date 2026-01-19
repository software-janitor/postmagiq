#!/usr/bin/env python3
"""Migrate data from SQLite to PostgreSQL."""

import sqlite3
from datetime import datetime
from uuid import uuid4
import psycopg2

SQLITE_PATH = "/home/mg/code/linkedin_articles/deprecated/data/content_strategy.db"
POSTGRES_URL = "postgresql://orchestrator:orchestrator_dev@localhost:5433/orchestrator"

maps = {
    'goal': {}, 'chapter': {}, 'post': {}, 'scene': {}, 'pose': {},
    'prop': {}, 'sentiment': {}, 'prop_category': {}, 'character_template': {},
    'character': {}, 'outfit': {}, 'outfit_part': {}, 'image_character': {},
    'image_outfit': {},
}

def migrate():
    sqlite_conn = sqlite3.connect(SQLITE_PATH)
    sqlite_conn.row_factory = sqlite3.Row
    sq = sqlite_conn.cursor()
    
    pg = psycopg2.connect(POSTGRES_URL)
    pg.autocommit = False
    pc = pg.cursor()
    
    # Get workspace (owner's workspace)
    pc.execute("SELECT id FROM workspaces WHERE slug = 'test-workspace'")
    ws = pc.fetchone()[0]

    # Get default user
    pc.execute("SELECT id FROM users WHERE email = 'owner@example.com'")
    default_user = pc.fetchone()[0]
    
    print(f"Workspace: {ws}")
    print(f"Default user: {default_user}")
    
    try:
        # Goals
        print("\nMigrating goals...")
        sq.execute("SELECT * FROM goals")
        for row in sq.fetchall():
            new_id = uuid4()
            maps['goal'][row['id']] = new_id
            pc.execute("""
                INSERT INTO goals (id, workspace_id, user_id, positioning, signature_thesis,
                    target_audience, content_style, onboarding_mode, onboarding_transcript,
                    strategy_type, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT DO NOTHING
            """, (str(new_id), str(ws), str(default_user), 
                  row['positioning'], row['signature_thesis'],
                  row['target_audience'], row['content_style'],
                  row['onboarding_mode'], row['onboarding_transcript'],
                  row['strategy_type'], row['created_at'] or datetime.utcnow()))
        print(f"  Migrated {len(maps['goal'])} goals")
        
        # Chapters (no goal_id - they have platform_id)
        print("Migrating chapters...")
        sq.execute("SELECT * FROM chapters")
        for row in sq.fetchall():
            new_id = uuid4()
            maps['chapter'][row['id']] = new_id
            pc.execute("""
                INSERT INTO chapters (id, workspace_id, user_id, chapter_number, title, 
                    description, theme, theme_description, weeks_start, weeks_end)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT DO NOTHING
            """, (str(new_id), str(ws), str(default_user), row['chapter_number'], row['title'],
                  row['description'], row['theme'], row['theme_description'],
                  row['weeks_start'], row['weeks_end']))
        print(f"  Migrated {len(maps['chapter'])} chapters")
        
        # Posts
        print("Migrating posts...")
        sq.execute("SELECT * FROM posts")
        for row in sq.fetchall():
            chapter_id = maps['chapter'].get(row['chapter_id'])
            if not chapter_id:
                continue
            new_id = uuid4()
            maps['post'][row['id']] = new_id
            pc.execute("""
                INSERT INTO posts (id, workspace_id, user_id, chapter_id, post_number, topic,
                    shape, cadence, entry_point, status, story_used, published_at, published_url, guidance)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT DO NOTHING
            """, (str(new_id), str(ws), str(default_user), str(chapter_id), 
                  row['post_number'], row['topic'], row['shape'], row['cadence'],
                  row['entry_point'], row['status'], row['story_used'],
                  row['published_at'], row['published_url'], row['guidance']))
        print(f"  Migrated {len(maps['post'])} posts")
        
        # Workflow personas
        print("Migrating workflow_personas...")
        sq.execute("SELECT * FROM workflow_personas")
        count = 0
        for row in sq.fetchall():
            pc.execute("""
                INSERT INTO workflow_personas (id, workspace_id, user_id, name, slug,
                    content, is_system, model_tier, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT DO NOTHING
            """, (str(uuid4()), str(ws), str(default_user), row['name'], row['slug'],
                  row['content'], bool(row['is_system']), row['model_tier'],
                  row['created_at'] or datetime.utcnow()))
            count += 1
        print(f"  Migrated {count} workflow_personas")

        # Commit core data before proceeding with optional image data
        pg.commit()
        print("\n✅ Core data committed (goals, chapters, posts, personas)")

        # Sentiments - skip, schema mismatch
        print("\nSkipping sentiments (schema mismatch)...")
        
        # Image scenes
        print("Migrating image_scenes...")
        sq.execute("SELECT * FROM image_scenes")
        for row in sq.fetchall():
            new_id = uuid4()
            maps['scene'][row['id']] = new_id
            pc.execute("""
                INSERT INTO image_scenes (id, workspace_id, code, name, description,
                    camera_angle, lighting, background, atmosphere, is_active)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT DO NOTHING
            """, (str(new_id), str(ws), row['code'], row['name'], row['description'],
                  row['camera_angle'], row['lighting'], row['background'],
                  row['atmosphere'], row['is_active']))
        print(f"  Migrated {len(maps['scene'])} image_scenes")
        
        # Image poses
        print("Migrating image_poses...")
        sq.execute("SELECT * FROM image_poses")
        for row in sq.fetchall():
            new_id = uuid4()
            maps['pose'][row['id']] = new_id
            pc.execute("""
                INSERT INTO image_poses (id, workspace_id, code, name, description,
                    body_position, hand_position, facial_expression, is_active)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT DO NOTHING
            """, (str(new_id), str(ws), row['code'], row['name'], row['description'],
                  row['body_position'], row['hand_position'], row['facial_expression'], row['is_active']))
        print(f"  Migrated {len(maps['pose'])} image_poses")
        
        # Prop categories
        print("Migrating prop_categories...")
        sq.execute("SELECT * FROM prop_categories")
        for row in sq.fetchall():
            new_id = uuid4()
            maps['prop_category'][row['id']] = new_id
            pc.execute("""
                INSERT INTO prop_categories (id, workspace_id, name, description)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT DO NOTHING
            """, (str(new_id), str(ws), row['name'], row['description']))
        print(f"  Migrated {len(maps['prop_category'])} prop_categories")
        
        # Image props
        print("Migrating image_props...")
        sq.execute("SELECT * FROM image_props")
        for row in sq.fetchall():
            new_id = uuid4()
            maps['prop'][row['id']] = new_id
            pc.execute("""
                INSERT INTO image_props (id, workspace_id, code, name, description,
                    category, placement, is_active)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT DO NOTHING
            """, (str(new_id), str(ws), row['code'], row['name'], row['description'],
                  row['category'], row['placement'], row['is_active']))
        print(f"  Migrated {len(maps['prop'])} image_props")
        
        # Character templates
        print("Migrating character_templates...")
        sq.execute("SELECT * FROM character_templates")
        for row in sq.fetchall():
            new_id = uuid4()
            maps['character_template'][row['id']] = new_id
            pc.execute("""
                INSERT INTO character_templates (id, workspace_id, name, base_description,
                    physical_traits, style_notes, is_active)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT DO NOTHING
            """, (str(new_id), str(ws), row['name'], row['base_description'],
                  row['physical_traits'], row['style_notes'], row['is_active']))
        print(f"  Migrated {len(maps['character_template'])} character_templates")
        
        # Characters
        print("Migrating characters...")
        sq.execute("SELECT * FROM characters")
        for row in sq.fetchall():
            new_id = uuid4()
            maps['character'][row['id']] = new_id
            template_id = maps['character_template'].get(row['template_id']) if row['template_id'] else None
            pc.execute("""
                INSERT INTO characters (id, workspace_id, template_id, name, role, description,
                    physical_description, personality_traits, is_active)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT DO NOTHING
            """, (str(new_id), str(ws), str(template_id) if template_id else None,
                  row['name'], row['role'], row['description'],
                  row['physical_description'], row['personality_traits'], row['is_active']))
        print(f"  Migrated {len(maps['character'])} characters")
        
        # Outfit parts
        print("Migrating outfit_parts...")
        sq.execute("SELECT * FROM outfit_parts")
        for row in sq.fetchall():
            new_id = uuid4()
            maps['outfit_part'][row['id']] = new_id
            pc.execute("""
                INSERT INTO outfit_parts (id, workspace_id, category, name, description,
                    style_tags, is_active)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT DO NOTHING
            """, (str(new_id), str(ws), row['category'], row['name'], row['description'],
                  row['style_tags'], row['is_active']))
        print(f"  Migrated {len(maps['outfit_part'])} outfit_parts")
        
        # Outfits
        print("Migrating outfits...")
        sq.execute("SELECT * FROM outfits")
        for row in sq.fetchall():
            new_id = uuid4()
            maps['outfit'][row['id']] = new_id
            pc.execute("""
                INSERT INTO outfits (id, workspace_id, name, description, style, occasion, is_active)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT DO NOTHING
            """, (str(new_id), str(ws), row['name'], row['description'],
                  row['style'], row['occasion'], row['is_active']))
        print(f"  Migrated {len(maps['outfit'])} outfits")
        
        # Outfit items
        print("Migrating outfit_items...")
        sq.execute("SELECT * FROM outfit_items")
        count = 0
        for row in sq.fetchall():
            outfit_id = maps['outfit'].get(row['outfit_id'])
            part_id = maps['outfit_part'].get(row['part_id'])
            if not outfit_id or not part_id:
                continue
            pc.execute("""
                INSERT INTO outfit_items (id, workspace_id, outfit_id, part_id, layer_order)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT DO NOTHING
            """, (str(uuid4()), str(ws), str(outfit_id), str(part_id), row['layer_order']))
            count += 1
        print(f"  Migrated {count} outfit_items")
        
        # Character outfits
        print("Migrating character_outfits...")
        sq.execute("SELECT * FROM character_outfits")
        count = 0
        for row in sq.fetchall():
            character_id = maps['character'].get(row['character_id'])
            outfit_id = maps['outfit'].get(row['outfit_id'])
            if not character_id or not outfit_id:
                continue
            pc.execute("""
                INSERT INTO character_outfits (id, workspace_id, character_id, outfit_id, is_default)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT DO NOTHING
            """, (str(uuid4()), str(ws), str(character_id), str(outfit_id), row['is_default']))
            count += 1
        print(f"  Migrated {count} character_outfits")
        
        # Scene characters
        print("Migrating scene_characters...")
        sq.execute("SELECT * FROM scene_characters")
        count = 0
        for row in sq.fetchall():
            scene_id = maps['scene'].get(row['scene_id'])
            character_id = maps['character'].get(row['character_id'])
            sentiment_id = maps['sentiment'].get(row['sentiment_id']) if row['sentiment_id'] else None
            if not scene_id or not character_id:
                continue
            pc.execute("""
                INSERT INTO scene_characters (id, workspace_id, scene_id, character_id, sentiment_id, position_hint)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT DO NOTHING
            """, (str(uuid4()), str(ws), str(scene_id), str(character_id),
                  str(sentiment_id) if sentiment_id else None, row['position_hint']))
            count += 1
        print(f"  Migrated {count} scene_characters")
        
        # Image characters
        print("Migrating image_characters...")
        sq.execute("SELECT * FROM image_characters")
        for row in sq.fetchall():
            new_id = uuid4()
            maps['image_character'][row['id']] = new_id
            pc.execute("""
                INSERT INTO image_characters (id, workspace_id, code, name, description,
                    physical_description, default_expression, is_active)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT DO NOTHING
            """, (str(new_id), str(ws), row['code'], row['name'], row['description'],
                  row['physical_description'], row['default_expression'], row['is_active']))
        print(f"  Migrated {len(maps['image_character'])} image_characters")
        
        # Image outfits
        print("Migrating image_outfits...")
        sq.execute("SELECT * FROM image_outfits")
        for row in sq.fetchall():
            new_id = uuid4()
            maps['image_outfit'][row['id']] = new_id
            pc.execute("""
                INSERT INTO image_outfits (id, workspace_id, code, name, description,
                    clothing_items, accessories, is_active)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT DO NOTHING
            """, (str(new_id), str(ws), row['code'], row['name'], row['description'],
                  row['clothing_items'], row['accessories'], row['is_active']))
        print(f"  Migrated {len(maps['image_outfit'])} image_outfits")
        
        # Image prompts
        print("Migrating image_prompts...")
        sq.execute("SELECT * FROM image_prompts")
        count = 0
        for row in sq.fetchall():
            post_id = maps['post'].get(row['post_id']) if row['post_id'] else None
            scene_id = maps['scene'].get(row['scene_id']) if row['scene_id'] else None
            pose_id = maps['pose'].get(row['pose_id']) if row['pose_id'] else None
            sentiment_id = maps['sentiment'].get(row['sentiment_id']) if row['sentiment_id'] else None
            character_id = maps['image_character'].get(row['character_id']) if row['character_id'] else None
            outfit_id = maps['image_outfit'].get(row['outfit_id']) if row['outfit_id'] else None
            
            pc.execute("""
                INSERT INTO image_prompts (id, workspace_id, post_id, scene_id, pose_id,
                    sentiment_id, character_id, outfit_id, custom_props, generated_prompt, image_url, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT DO NOTHING
            """, (str(uuid4()), str(ws),
                  str(post_id) if post_id else None,
                  str(scene_id) if scene_id else None,
                  str(pose_id) if pose_id else None,
                  str(sentiment_id) if sentiment_id else None,
                  str(character_id) if character_id else None,
                  str(outfit_id) if outfit_id else None,
                  row['custom_props'], row['generated_prompt'], row['image_url'],
                  row['created_at'] or datetime.utcnow()))
            count += 1
        print(f"  Migrated {count} image_prompts")
        
        # Scene prop rules
        print("Migrating scene_prop_rules...")
        sq.execute("SELECT * FROM scene_prop_rules")
        count = 0
        for row in sq.fetchall():
            scene_id = maps['scene'].get(row['scene_id'])
            prop_id = maps['prop_category'].get(row['prop_category_id'])
            if not scene_id or not prop_id:
                continue
            pc.execute("""
                INSERT INTO scene_prop_rules (id, workspace_id, scene_id, prop_id, is_required, probability)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT DO NOTHING
            """, (str(uuid4()), str(ws), str(scene_id), str(prop_id),
                  row['is_required'], row['probability']))
            count += 1
        print(f"  Migrated {count} scene_prop_rules")
        
        # Context prop rules
        print("Migrating context_prop_rules...")
        sq.execute("SELECT * FROM context_prop_rules")
        count = 0
        for row in sq.fetchall():
            prop_id = maps['prop_category'].get(row['prop_category_id'])
            if not prop_id:
                continue
            pc.execute("""
                INSERT INTO context_prop_rules (id, workspace_id, context_type, prop_id, is_required, probability)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT DO NOTHING
            """, (str(uuid4()), str(ws), row['context_type'], str(prop_id),
                  row['is_required'], row['probability']))
            count += 1
        print(f"  Migrated {count} context_prop_rules")

        # Workflow runs
        print("Migrating workflow_runs...")
        pc.execute("SELECT run_id FROM workflow_runs")
        existing_runs = {row[0] for row in pc.fetchall()}

        sq.execute("SELECT * FROM workflow_runs")
        runs_count = 0
        for row in sq.fetchall():
            if row['run_id'] in existing_runs:
                continue
            pc.execute("""
                INSERT INTO workflow_runs (id, workspace_id, user_id, run_id, story, status,
                    current_state, final_state, total_tokens, total_cost_usd, started_at, completed_at, error)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (run_id) DO NOTHING
            """, (str(uuid4()), str(ws), str(default_user), row['run_id'], row['story'],
                  row['status'] or 'completed', row['current_state'], row['final_state'],
                  row['total_tokens'] or 0, row['total_cost_usd'] or 0.0,
                  row['started_at'] or datetime.utcnow(), row['completed_at'], row['error']))
            runs_count += 1
        print(f"  Migrated {runs_count} workflow_runs")

        # Workflow outputs
        print("Migrating workflow_outputs...")
        sq.execute("SELECT * FROM workflow_outputs")
        outputs_count = 0
        for row in sq.fetchall():
            if row['run_id'] in existing_runs:
                continue
            pc.execute("""
                INSERT INTO workflow_outputs (id, workspace_id, run_id, state_name, agent,
                    output_type, content, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (str(uuid4()), str(ws), row['run_id'], row['state_name'], row['agent'],
                  row['output_type'], row['content'], row['created_at'] or datetime.utcnow()))
            outputs_count += 1
        print(f"  Migrated {outputs_count} workflow_outputs")

        pg.commit()
        print("\n" + "=" * 50)
        print("Migration completed successfully!")
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
