# Deprecated Routes

This directory contains routes that have been deprecated as part of the launch simplification.
These routes are preserved to enable future restoration if needed.

## Contents

| Module | Original Path | Reason | Restore Steps |
|--------|--------------|--------|---------------|
| voice.py | api/routes/voice.py | Replaced by v1/voice.py | 1. Move back to api/routes/ 2. Re-register in main.py |
| onboarding.py | api/routes/onboarding.py | Replaced by v1/onboarding.py | 1. Move back to api/routes/ 2. Re-register in main.py |
| finished_posts.py | api/routes/finished_posts.py | Replaced by v1/finished_posts.py | 1. Move back to api/routes/ 2. Re-register in main.py |
| ai_assistant.py | api/routes/ai_assistant.py | MVP scope reduction | 1. Move back to api/routes/ 2. Re-register in main.py |
| eval.py | api/routes/eval.py | MVP scope reduction | 1. Move back to api/routes/ 2. Re-register in main.py |
| watermark.py | api/routes/watermark.py | MVP scope reduction | 1. Move back to api/routes/ 2. Re-register in main.py |
| image_prompts.py | api/routes/image_prompts.py | Image features deferred | 1. Move back to api/routes/ 2. Re-register in main.py |
| image_config.py | api/routes/image_config.py | Image features deferred | 1. Move back to api/routes/ 2. Re-register in main.py |
| characters.py | api/routes/characters.py | Image features deferred | 1. Move back to api/routes/ 2. Re-register in main.py |
| platforms.py | api/routes/platforms.py | MVP scope reduction | 1. Move back to api/routes/ 2. Re-register in main.py |
| analytics.py | api/routes/analytics.py | MVP scope reduction | 1. Move back to api/routes/ 2. Re-register in main.py |
| content.py | api/routes/content.py | Legacy route | 1. Move back to api/routes/ 2. Re-register in main.py |
| posts.py | api/routes/posts.py | Legacy route | 1. Move back to api/routes/ 2. Re-register in main.py |

## Restore Instructions

To restore a deprecated module:

1. Move the module back to its original path:
   ```bash
   mv api/routes/deprecated/voice.py api/routes/voice.py
   ```

2. Re-register the router in `api/main.py`:
   ```python
   from api.routes import voice
   app.include_router(voice.router, prefix="/api", tags=["voice"])
   ```

3. If the route has associated services, restore them from `api/services/deprecated/`

4. Update any related GUI components and API clients

## Reference

See LAUNCH_SIMPLIFICATION_PLAN.md for the full deprecation plan and rationale.
