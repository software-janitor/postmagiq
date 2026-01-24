Security Audit Report (Revised)

Scope
- Backend API (legacy + v1 routes), workflow runner, and frontend clients.

Auth Coverage Matrix (Legacy + Core)
Legend: Required = auth dependency on all endpoints; Partial = mix; None = no auth dependency.
| File | Coverage | Evidence |
| --- | --- | --- |
| `api/routes/workflow.py` | Partial | Unauthed control endpoints at `api/routes/workflow.py:42`, `api/routes/workflow.py:52`, `api/routes/workflow.py:58`, `api/routes/workflow.py:67`, `api/routes/workflow.py:73`; auth on execute/runs at `api/routes/workflow.py:28`, `api/routes/workflow.py:79` |
| `api/routes/ws.py` | None | WebSocket accepts connections without auth at `api/routes/ws.py:13`; global subscribers at `api/websocket/manager.py:15` |
| `api/routes/config.py` | None | Unauthed read/write at `api/routes/config.py:12` and `api/routes/config.py:18` |
| `api/routes/ai_assistant.py` | None | Unauthed chat at `api/routes/ai_assistant.py:140`; strategy chat at `api/routes/ai_assistant.py:235` |
| `api/routes/eval.py` | None | Unauthed analytics endpoints at `api/routes/eval.py:11`, `api/routes/eval.py:24`, `api/routes/eval.py:34`, `api/routes/eval.py:47`, `api/routes/eval.py:60`, `api/routes/eval.py:79`, `api/routes/eval.py:93` |
| `api/routes/content.py` | Partial | Most CRUD unauth (e.g., `api/routes/content.py:129`, `api/routes/content.py:165`, `api/routes/content.py:200`); only reset uses auth at `api/routes/content.py:333` |
| `api/routes/voice.py` | None | Unauthed samples at `api/routes/voice.py:124`; delete profile at `api/routes/voice.py:297` |
| `api/routes/analytics.py` | None | Unauthed import at `api/routes/analytics.py:55`; destructive clear at `api/routes/analytics.py:117` |
| `api/routes/onboarding.py` | None | Unauthed user creation at `api/routes/onboarding.py:151` |
| `api/routes/image_config.py` | None | Unauthed seed/reset at `api/routes/image_config.py:123`, `api/routes/image_config.py:130` |
| `api/routes/image_prompts.py` | Partial | Auth required for generate_prompt at `api/routes/image_prompts.py:32`; unauth list/delete at `api/routes/image_prompts.py:62`, `api/routes/image_prompts.py:89`, `api/routes/image_prompts.py:289` |
| `api/routes/platforms.py` | None | Unauthed CRUD at `api/routes/platforms.py:45`, `api/routes/platforms.py:90` |
| `api/routes/characters.py` | Partial | Templates list uses auth at `api/routes/characters.py:272`; user_id CRUD unauth at `api/routes/characters.py:302`, `api/routes/characters.py:326` |
| `api/routes/posts.py` | None | Unauthed tracker reads at `api/routes/posts.py:23` |
| `api/routes/watermark.py` | None | Unauthed path-based remove at `api/routes/watermark.py:41` and batch at `api/routes/watermark.py:106` |
| `api/routes/finished_posts.py` | Partial | Auth on list at `api/routes/finished_posts.py:114`; publish/unpublish unauth at `api/routes/finished_posts.py:314`, `api/routes/finished_posts.py:346` |
| `api/routes/runs.py` | Required | get_current_user on all endpoints (e.g., `api/routes/runs.py:23`) |
| `api/routes/workflow_personas.py` | Required | get_current_user on all endpoints (e.g., `api/routes/workflow_personas.py:86`); ownership not enforced on user_id/persona_id paths |
| `api/routes/v1/workspace_content.py` | Required | Workspace scope required (e.g., `api/routes/v1/workspace_content.py:189`) |

Critical Findings
- Unauthenticated workflow control endpoints allow any caller to step/abort/approve/pause/resume workflows. `api/routes/workflow.py:42`, `api/routes/workflow.py:52`, `api/routes/workflow.py:58`, `api/routes/workflow.py:67`, `api/routes/workflow.py:73`
- WebSocket endpoint lacks auth; any client can subscribe to any run_id and global subscribers receive all events. `api/routes/ws.py:13`, `api/websocket/manager.py:15`, `api/websocket/manager.py:51`
- Legacy API mass IDOR + destructive writes: user_id is caller-supplied with no ownership checks. Examples include delete strategy `api/routes/content.py:200`, delete profile `api/routes/voice.py:297`, clear analytics `api/routes/analytics.py:117`, image config seed/reset `api/routes/image_config.py:123`, platforms CRUD `api/routes/platforms.py:45`, characters CRUD `api/routes/characters.py:302`, image prompt list/delete `api/routes/image_prompts.py:62`, onboarding user creation `api/routes/onboarding.py:151`
- Workflow config endpoints are fully unauthenticated, enabling config read/overwrite. `api/routes/config.py:12`, `api/routes/config.py:18`
- AI assistant endpoints are unauthenticated, allowing unlimited LLM invocations. `api/routes/ai_assistant.py:140`, `api/routes/ai_assistant.py:235`
- JWT token type is not enforced; any valid JWT (refresh/portal/access) is accepted by get_current_user. `api/auth/dependencies.py:89`, `api/middleware/auth.py:55`, `api/auth/jwt.py:61`
- Arbitrary file read via input_path in workflow runner; input_path is copied without sandboxing. `runner/runner.py:53`, `runner/runner.py:71`
- Path-based watermark removal reads and writes arbitrary files without auth. `api/routes/watermark.py:41`, `api/services/watermark_service.py:74`, `api/services/watermark_service.py:102`
- Default JWT secret fallback when env var missing enables token forgery and full auth bypass. `api/auth/jwt.py:11`

High Findings
- Middleware module collision: `api/middleware.py` (file) collides with `api/middleware/` (package); import resolution can load wrong middleware or break wiring. `api/middleware.py:1`, `api/middleware/__init__.py:1`, `api/middleware/usage.py:1`
- Workflow run ownership IDOR: run details and outputs are fetched by run_id with no ownership validation. `api/routes/workflow.py:90`, `api/routes/workflow.py:104`, `runner/content/workflow_store.py:57`, `runner/content/workflow_store.py:104`
- workflow_personas IDOR: authenticated users can access other users' personas via user_id path or persona_id without ownership checks. `api/routes/workflow_personas.py:252`, `api/routes/workflow_personas.py:298`, `api/routes/workflow_personas.py:337`
- Deactivated users retain access; get_current_user never checks user.is_active. `api/auth/dependencies.py:121`, `api/auth/dependencies.py:130`
- Eval endpoints are unauthenticated, exposing internal performance/cost metrics. `api/routes/eval.py:11`, `api/routes/eval.py:24`, `api/routes/eval.py:60`
- Webhook signing uses secret_hash (not plaintext secret) and failure retries never increment attempt_number, causing unverifiable signatures and endless retries. `api/services/webhook_service.py:276`, `api/services/webhook_service.py:341`, `api/services/webhook_service.py:419`
- No rate limiting middleware on any endpoints; usage middleware only gates billing resources. `api/main.py:39`, `api/middleware/usage.py:55`

Medium Findings
- Finished posts publish/unpublish endpoints are unauthenticated, allowing anyone to alter publish status. `api/routes/finished_posts.py:314`, `api/routes/finished_posts.py:346`
- Portal router registered twice; can cause duplicate routes/OpenAPI collisions. `api/main.py:102`, `api/main.py:108`
- Usage enforcement swallows exceptions without logging; limits can fail open silently. `api/middleware/usage.py:56`, `api/middleware/usage.py:85`
- Notifications mark delivered_at when email channel is enabled, but email delivery is TODO (not implemented); delivery state is inaccurate. `api/services/notification_service.py:296`, `api/services/notification_service.py:313`
- Frontend voice learning hardcodes userId=1, mixing tenants in multi-user scenarios. `gui/src/pages/VoiceLearning.tsx:32`
- Frontend voice client uses legacy /voice endpoints with raw user_id; will break once auth/tenant scoping is enforced. `gui/src/api/voice.ts:75`, `gui/src/api/voice.ts:101`
- No request size limits or body size middleware; large payloads can cause memory/CPU pressure. `api/main.py:39`

Low Findings
- CORS dev origins hardcoded; should be environment-configured in production. `api/main.py:55`
- API key and webhook prefix exposure could aid enumeration (acceptable if documented). `runner/db/models/api_key.py:92`, `runner/db/models/api_key.py:172`

Test Gaps
- No tests for unauthenticated workflow control or WebSocket access control. `api/routes/workflow.py:42`, `api/routes/ws.py:13`
- Integration tests currently validate legacy unauthenticated APIs and will mask required auth changes. `tests/integration/test_content_api.py:20`, `tests/integration/test_voice_api.py:13`
- No tests for token type enforcement or webhook signing/retry behavior. `api/auth/dependencies.py:89`, `api/services/webhook_service.py:276`
- No tests for path-based file access protections (input_path/watermark). `runner/runner.py:53`, `api/routes/watermark.py:41`
- No tests for user.is_active enforcement in auth dependency. `api/auth/dependencies.py:121`
- No tests for workflow_personas ownership validation. `api/routes/workflow_personas.py:252`

Clarifications / Not Confirmed
- Path traversal in finalize_story is not confirmed; story parsing is regex-limited and filenames are fixed. `api/routes/workflow.py:160`, `api/routes/workflow.py:188`
- Subprocess command injection via session IDs not confirmed; CLI uses args lists and session IDs are regex-extracted. `runner/agents/cli_base.py:123`, `runner/sessions/native.py:15`
- runs endpoints are authenticated via get_current_user; no unauthenticated access observed. `api/routes/runs.py:23`

Questions / Decisions Needed
- Should all legacy /api/* routes be deprecated in favor of /api/v1/w/* workspace-scoped routes?
- Should path-based inputs (input_path, watermark input_dir/output_dir) be removed from API mode or restricted to a sandbox directory?
- Should refresh and portal tokens be fully isolated from standard user APIs (token type enforcement)?

Change Summary
- Added eval routes and runs routes to auth coverage matrix, with corrected auth posture.
- Added workflow_personas IDOR and user.is_active enforcement gap; removed misleading "protected" note.
- Promoted default JWT secret fallback to Critical.

Next Steps
1. Enforce authentication and ownership checks on legacy routes and workflow_personas.
2. Enforce token types and user.is_active checks; add WebSocket auth + run ownership checks.
3. Eliminate or sandbox path-based inputs and add request size/rate limits.
4. Fix webhook signing/retry logic and add tests for auth boundaries and file-access protections.
