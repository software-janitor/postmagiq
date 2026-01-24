Launch Simplification Plan (v10)

Goals
- Reduce feature surface for launch while preserving secured code for later restoration.
- Keep core workflow + workspace collaboration + strategy + voice + finished posts tracking.
- Disable non-MVP endpoints without deleting models/migrations.
- Fresh deploy assumption: no existing users/data; no backfill or migration required.

Security Baseline Constraint
- Security remediation added auth/ownership checks to many legacy routes; ws and finished_posts publish/unpublish still require fixes.
- Deprecated code must be the secured version (canonical), never older unsecured copies.

Scope Decisions (Closed)
- Disable: ai_assistant, eval, watermark.
- Keep: voice synthesizer, strategy builder, finished posts tracking, workspace + invites.
- Image features: deprecate but preserve for later (scenes/clothing/prompts/etc.).
- Analytics/platforms/content/posts/characters: deprecate (not needed for MVP).
- Launch LLM provider: Groq only (see GROQ_IMPLEMENTATION_PLAN.md for details).

Route Disposition Matrix (Closed)
| Route/Module | Decision | Notes |
| --- | --- | --- |
| api/routes/auth.py | KEEP | Core auth. |
| api/routes/health.py | KEEP | Monitoring. |
| api/routes/portal.py | KEEP | Client portal. |
| api/routes/workflow.py | KEEP | Core orchestrator. |
| api/routes/runs.py | KEEP | Run history. |
| api/routes/ws.py | KEEP | Real-time updates, auth must be added. |
| api/routes/workflow_personas.py | KEEP | Secured; keep canonical. |
| api/routes/config.py | KEEP + SECURE | Required for tier management. **Add owner-only auth in Phase 2.** |
| api/routes/v1/* | KEEP | See explicit list below. |
| api/routes/v1/voice.py | ADD | Workspace-scoped voice API. |
| api/routes/v1/onboarding.py | ADD | Workspace-scoped strategy builder. |
| api/routes/v1/finished_posts.py | ADD | Workspace-scoped finished posts (read-only). |
| api/routes/voice.py | DEPRECATE | Legacy; replaced by v1/voice. |
| api/routes/onboarding.py | DEPRECATE | Legacy; replaced by v1/onboarding. |
| api/routes/finished_posts.py | DEPRECATE | Legacy; replaced by v1/finished_posts. |
| api/routes/ai_assistant.py | DEPRECATE | Move secured code to deprecated. |
| api/routes/eval.py | DEPRECATE | Move secured code to deprecated. |
| api/routes/watermark.py | DEPRECATE | Move secured code to deprecated. |
| api/routes/image_prompts.py | DEPRECATE | Preserve image features. |
| api/routes/image_config.py | DEPRECATE | Preserve image features. |
| api/routes/characters.py | DEPRECATE | Image feature dependency. |
| api/routes/platforms.py | DEPRECATE | Not needed for MVP. |
| api/routes/analytics.py | DEPRECATE | Not needed for MVP. |
| api/routes/content.py | DEPRECATE | Not needed for MVP (legacy). |
| api/routes/posts.py | DEPRECATE | Legacy tracker only. |

v1 Route Inventory (Explicit)
- api/routes/v1/__init__.py (support module)
- api/routes/v1/audit.py
- api/routes/v1/usage.py
- api/routes/v1/billing.py
- api/routes/v1/domains.py
- api/routes/v1/privacy.py
- api/routes/v1/api_keys.py
- api/routes/v1/webhooks.py
- api/routes/v1/approvals.py
- api/routes/v1/workspaces.py
- api/routes/v1/notifications.py
- api/routes/v1/voice.py (new)
- api/routes/v1/onboarding.py (new)
- api/routes/v1/finished_posts.py (new)
- api/routes/v1/voice_profiles.py
- api/routes/v1/workspace_content.py
- api/routes/v1/dependencies.py (support module)

Blocking Decisions (Closed)
1) Strategy builder migrates to /api/v1/w/{workspace_id}/onboarding/*.
2) Voice migrates to /api/v1/w/{workspace_id}/voice/*.
3) Finished posts migrates to /api/v1/w/{workspace_id}/finished-posts (read-only).
4) analytics/platforms/content/posts/characters are deprecated.
5) Legacy /api/voice, /api/onboarding, /api/finished-posts are deprecated and removed after migration.
6) Billing is charged to workspace.owner_id for all workspace-scoped actions.
7) Groq is the only enabled LLM provider for launch (GROQ_IMPLEMENTATION_PLAN.md).
8) Dynamic workflow configuration system enables GUI-selectable configs (GROQ_IMPLEMENTATION_PLAN.md §Dynamic Workflow Configuration).

Phase Order
Phase 0: Groq Agent + Dynamic Workflow Config (LAUNCH BLOCKER)
- See GROQ_IMPLEMENTATION_PLAN.md for full details.
- Must complete before Phase 2 (workflow depends on working agents).

Phase 1: Inventory + Decision Closure
- Completed by this plan (route decisions closed).
- Confirm orchestrator stays (workflow.py, runs.py, ws.py, workflow_config.yaml).
- Confirm fresh deploy; skip any data backfill tasks.

Phase 2: Implement Security for What Stays
- WebSocket auth (currently none): add JWT verification and run ownership checks.
- Voice: move to /api/v1/w/{workspace_id}/voice, verify membership, bill workspace.owner_id.
- Onboarding/strategy: move to /api/v1/w/{workspace_id}/onboarding, verify membership, bill workspace.owner_id.
- Finished posts: move to /api/v1/w/{workspace_id}/finished-posts (read-only).
- Config routes: add owner-only auth to api/routes/config.py (tier management is sensitive).
- Update GUI/API clients to pass workspace_id and use v1 routes.
- Security note: finished_posts publish/unpublish endpoints are currently unauthenticated; removal is required.

Workspace Migration for Legacy Routes (Required)
- Create v1 workspace-scoped routes and update clients to call them.
- Legacy routes are deprecated immediately after v1 is in place and removed in Phase 4.
- Enforce membership via workspace middleware/dependencies on all v1 routes.

WebSocket Auth Implementation (Explicit)
- Accept token from `Authorization: Bearer` or `?token=`.
- Verify JWT with verify_token(); reject if invalid or inactive user.
- If run_id provided, check run ownership before subscribing.
- Disable global broadcast subscription for non-owner users.

Phase 3: Deprecate (Secured Code Only)
- Create deprecated namespaces:
  - api/routes/deprecated/
  - api/services/deprecated/
  - gui/src/deprecated/
- Move secured code for disabled features into deprecated.
- Move legacy /api/voice, /api/onboarding, /api/finished-posts after v1 migration.
- Do not delete models/migrations.
- Add README.md with restore steps.

Phase 4: Unwire Runtime
- Remove deprecated router registrations from api/main.py.
- Ensure legacy /api/voice, /api/onboarding, /api/finished-posts are unregistered.
- Remove GUI navigation/routes calling deprecated endpoints.
- Update Makefile help targets.

Deprecated Endpoint Removal Standard
- After deprecation, remove router registrations so endpoints return 404.
- Document removals in release notes instead of serving stub routes.

Finished Posts Disable Approach (Explicit)
- Keep list/get endpoints intact (v1 workspace routes).
- Remove publish/unpublish endpoints entirely (no stubs) in legacy and v1.
- Tech debt note: finished_posts.py reads from POSTS_DIR/IMAGES_DIR filesystem paths as fallback; fresh installs won't have these directories. Low priority since database is primary source.

Phase 5: Tests
- Remove or update tests that hit deprecated endpoints.
- Add tests for auth + membership + billing owner on voice/onboarding/finished_posts/ws.

Phase 6: Validation
- OpenAPI exposes only MVP endpoints.
- Smoke test: auth/login, workspace create/invite, voice analysis, strategy builder, finished posts list/get, workflow run.
- Verify legacy /api/voice, /api/onboarding, /api/finished-posts return 404.

Service Disposition Matrix (Complete)
| Service | Decision | Notes |
| --- | --- | --- |
| api/services/analytics_service.py | DEPRECATE | Analytics disabled. |
| api/services/api_key_service.py | KEEP | v1 API keys. |
| api/services/approval_service.py | KEEP | Approvals/portal. |
| api/services/audit_service.py | KEEP | Audit logs. |
| api/services/billing_service.py | KEEP | v1 billing. |
| api/services/config_service.py | KEEP | Required for tier management. |
| api/services/content_service.py | KEEP (scope down) | See function list below. |
| api/services/domain_service.py | KEEP | Custom domains. |
| api/services/email_service.py | KEEP | Invites/notifications. |
| api/services/eval_service.py | DEPRECATE | Eval endpoints disabled. |
| api/services/health_service.py | KEEP | Health checks. |
| api/services/image_config_service.py | DEPRECATE | Image features. |
| api/services/image_prompt_service.py | DEPRECATE | Image features. |
| api/services/image_vision_service.py | DEPRECATE | Image features. |
| api/services/invite_service.py | KEEP | Workspace invites. |
| api/services/notification_service.py | KEEP | Notifications. |
| api/services/onboarding_service.py | KEEP | Strategy builder. |
| api/services/portal_service.py | KEEP | Client portal. |
| api/services/posts_service.py | DEPRECATE | Legacy tracker. |
| api/services/run_service.py | KEEP | Runs/Artifacts. |
| api/services/scene_generator_service.py | DEPRECATE | Image features. |
| api/services/strategy_chat_service.py | DEPRECATE | Used only by ai_assistant. |
| api/services/usage_service.py | KEEP | Usage limits. |
| api/services/voice_service.py | KEEP | Voice synthesizer. |
| api/services/watermark_service.py | DEPRECATE | Watermark feature. |
| api/services/webhook_service.py | KEEP | Webhooks. |
| api/services/workflow_service.py | KEEP | Orchestrator. |
| api/services/workspace_service.py | KEEP | Workspaces. |

content_service.py Function Disposition (Explicit)
KEEP (used by onboarding/finished_posts/voice):
- User: get_user, get_or_create_user
- Goal: save_goal, get_goal, update_goal, delete_strategy
- Chapter: save_chapter, get_chapters, get_chapter
- Post: save_post, get_posts, get_post, get_post_by_number, get_available_posts, get_next_post, update_post
- Writing samples: save_writing_sample, get_writing_samples
- Voice profiles: save_voice_profile, get_voice_profile, get_voice_profile_by_id, get_all_voice_profiles, update_voice_profile, set_default_voice_profile, clone_voice_profile, delete_voice_profile
- Constants: get_voice_prompts, get_content_styles, get_post_shapes
- Require workspace_id for KEEP functions; remove user_id-only paths.

DEPRECATE (move to deprecated/content_service.py):
- Platform: create_platform, get_platform, get_platforms, update_platform, delete_platform
- User admin: create_user, list_users, get_user_by_email

Database Model Retention Policy
- Keep all SQLModel models and Alembic migrations.
- Deprecated features are only unwired; tables remain to enable future restoration.

Docker/Infra Decisions
- Remove watermark service container from docker-compose (feature deprecated).
- Remove WATERMARK_SERVICE_URL from api service env in compose.
- Keep Ollama service (voice uses OLLAMA_HOST).
- Pass GROQ_API_KEY into api container via docker-compose and document in .env.example.
- Set AGENT_MODE=api in api container environment.

Makefile Changes (Explicit)

Targets to REMOVE:
- eval-agents
- eval-costs
- eval-trend
- eval-post
- eval-summary

Targets to KEEP:
- workflow, workflow-interactive, workflow-step
- test, test-unit, test-int, test-e2e, coverage, test-file
- logs, log-states, log-tokens, log-summary
- db-up, db-down, db-migrate, db-rollback, db-revision, db-history, db-current, db-shell
- up, up-gpu, up-cpu, down, api, gui, gui-build, dev, dev-stop, restart
- ollama-pull, ollama-list
- setup, install-hooks, install-deps, install-gui-deps, install-gh, check-env
- seed-personas
- clean
- pr

Makefile Validation Update
- check-env should require GROQ_API_KEY.

Frontend Inventory (Complete)
Pages to KEEP:
- Dashboard.tsx
- LiveWorkflow.tsx
- RunHistory.tsx
- RunDetail.tsx
- StoryWorkflow.tsx
- FinishedPosts.tsx
- Onboarding.tsx
- Strategies.tsx
- Strategy.tsx
- VoiceLearning.tsx
- VoiceProfiles.tsx
- TeamSettings.tsx
- Approvals.tsx
- Editor.tsx
- Settings.tsx

Pages to DEPRECATE:
- AIPersonas.tsx
- Evaluation.tsx
- ImageConfig.tsx
- OutfitBank.tsx
- Characters.tsx
- DeveloperSettings.tsx

GUI Navigation Items to Remove (gui/src/components/layout/Sidebar.tsx)
Remove from navItems array:
- { path: '/image-config', label: 'Image Config', flag: 'show_image_tools' }
- { path: '/characters', label: 'Characters', flag: 'show_image_tools' }
- { path: '/outfit-bank', label: 'Outfit Bank', flag: 'show_image_tools' }
- { path: '/ai-personas', label: 'AI Personas', flag: 'show_ai_personas' }
- { path: '/evaluation', label: 'Evaluation', flag: 'show_internal_workflow' }

Note: These items are currently gated by feature flags. Either:
1. Remove the navItems entries entirely, OR
2. Ensure flags default to false in production

GUI Router Config (gui/src/App.tsx)
Remove route definitions for deprecated pages:
- /image-config -> ImageConfig
- /characters -> Characters
- /outfit-bank -> OutfitBank
- /ai-personas -> AIPersonas
- /evaluation -> Evaluation
- /developer-settings -> DeveloperSettings (if present)

API Clients (Complete)
- KEEP: client.ts, workflow.ts, runs.ts, onboarding.ts (migrate to v1), voice.ts (migrate to v1), privacy.ts, whitelabel.ts
- ADD: finished_posts.ts (v1 workspace-scoped client) or update FinishedPosts page to call v1 directly.
- DEPRECATE: eval.ts, content.ts, platforms.ts, posts.ts

Tests Inventory (Complete, by file)
KEEP:
- tests/conftest.py
- tests/__init__.py
- tests/unit/__init__.py
- tests/unit/test_audit.py
- tests/unit/test_agents.py
- tests/unit/test_api_agents.py
- tests/unit/test_circuit_breaker.py
- tests/unit/test_compose_persona_prompt.py
- tests/unit/test_database_session_manager.py
- tests/unit/test_domain_service.py
- tests/unit/test_error_handlers.py
- tests/unit/test_health.py
- tests/unit/test_history.py
- tests/unit/test_logging.py
- tests/unit/test_models.py
- tests/unit/test_multitenancy.py
- tests/unit/test_notifications.py
- tests/unit/test_ollama.py
- tests/unit/test_repositories.py
- tests/unit/test_resilience.py
- tests/unit/test_session_manager.py
- tests/unit/test_state_machine.py
- tests/unit/test_token_tracking.py
- tests/unit/test_v1_routes.py
- tests/unit/test_whitelabel.py
- tests/integration/__init__.py
- tests/integration/conftest.py
- tests/integration/test_portal.py
- tests/integration/test_model_selection.py
- tests/integration/test_voice_api.py (migrate to v1)
- tests/integration/test_onboarding_api.py (migrate to v1)
- tests/e2e/__init__.py

DEPRECATE:
- tests/integration/test_ai_assistant.py
- tests/integration/test_content_api.py
- tests/integration/test_platforms.py
- tests/unit/test_image_vision_service.py

DECIDE (untracked file):
- tests/db_utils.py - If needed, add to KEEP and commit. Otherwise add to .gitignore.

Test Disposition Strategy
- Deprecated tests move to `tests/deprecated/` and are excluded from CI runs.
- If a deprecated test covers a kept service, split it before moving.
- Update pytest config to ignore `tests/deprecated/`.

Environment Variable Changes
- Add: GROQ_API_KEY (required for launch).
- Add: AGENT_MODE=api (force SDK agents).
- Remove: WATERMARK_SERVICE_URL.
- Remove if deprecated-only: EVAL_*, IMAGE_*.
- Review: image-specific env vars; remove if only used by deprecated services.
- Audit .env.example, docker-compose, and deployment configs for changes.

Deferred Work (Post-Launch Backlog)
- Premium tier providers re-enablement (claude/gpt/gemini)
- finished_posts.py filesystem fallback removal (use database only)
- YouTube audio extraction (G2 in GROQ_IMPLEMENTATION_PLAN.md)
- Content input flexibility (G3 in GROQ_IMPLEMENTATION_PLAN.md)
- Tier-gated model presets (G4 in GROQ_IMPLEMENTATION_PLAN.md)

Dynamic Workflow Configuration (Launch Required)
- Phases 2-15 in IMPLEMENTATION_TRACKER.md implement the dynamic workflow system
- Required for local testing and Groq config selection
- Production deployment filtering via DEPLOYMENT_ENV
- See GROQ_IMPLEMENTATION_PLAN.md §Dynamic Workflow Configuration for architecture

Rollback Strategy (Explicit)
- Tag at each phase boundary (launch-simplify-p0, p1, p2, p3, p4, p5, p6).
- Phase 3 rollback: re-register routers and move modules back from deprecated paths.
- Phase 4 rollback: restore GUI routes and Makefile targets from tags.

Implementation Artifacts
- Deprecated README template with original paths + restore commands:
```
# Deprecated Module
Original path: <original>
Moved from commit/tag: <tag>
Reason: <deprecation reason>

Restore:
1) Move module back to original path.
2) Re-register router/service in api/main.py or gui routes.
3) Re-enable env vars and docker-compose entries if needed.
```

Related Documents
- GROQ_IMPLEMENTATION_PLAN.md - Groq agent implementation (Phase 0 blocker)
