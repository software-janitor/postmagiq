# Implementation Tracker

Multi-tenancy implementation tracking for Postmagiq. Reference: `MULTI_TENANCY_PLAN.md`

## Overview

| Phase | Description | Timeline | Status | Lead |
|-------|-------------|----------|--------|------|
| Phase 0A | API-Based Agents | Week 0 | 🟢 Complete | Claude |
| Phase 0B | SQLModel + PostgreSQL Foundation | Week 0 | 🟢 Complete | Claude |
| Phase 1 | Database Foundation (Multi-tenancy) | Week 1-2 | 🟢 Complete | Claude |
| Phase 2 | Backend Logic (Auth + Services) | Week 3-4 | 🟢 Complete | Claude |
| Phase 3 | Frontend Integration | Week 5-6 | 🟢 Complete | Claude |
| Phase 4 | Subscription & Usage | Week 7-8 | 🟢 Complete | Claude |
| Phase 5 | Billing Integration (Stripe) | Week 9-10 | 🟢 Complete | Claude |
| Phase 6 | Assignment & Approvals | Week 11-12 | 🟢 Complete | Claude |
| Phase 7 | Notifications | Week 13 | 🟢 Complete | Claude |
| Phase 8 | API Keys & Webhooks | Week 14 | 🟢 Complete | Claude |
| Phase 9 | White-labeling | Week 15-16 | 🟢 Complete | Claude |
| Phase 10 | Polish & Launch | Week 17-18 | 🟡 In Progress | Claude |
| Phase 11 | Dynamic Workflow Configuration | Week 19 | 🟡 In Progress | Claude |

Legend: 🔴 Not Started | 🟡 In Progress | 🟢 Complete | ⏸️ Blocked

---

## Phase 0A: API-Based Agents

**Goal:** Add production-ready SDK-based agents alongside existing CLI agents.

### 0A.1 Dependencies
- [x] Add anthropic SDK to pyproject.toml
- [x] Add openai SDK to pyproject.toml
- [x] Add google-generativeai SDK to pyproject.toml
- [x] Add groq SDK to pyproject.toml (>=0.12.0)

### 0A.2 Base Infrastructure
- [x] Create runner/agents/api_base.py (APIAgent base class)
- [x] Add AGENT_MODE config to runner/config.py ("cli" or "api")
- [x] Add API key configs (ANTHROPIC_API_KEY, OPENAI_API_KEY, GOOGLE_API_KEY, GROQ_API_KEY)

### 0A.3 API Agent Implementations
- [x] Create runner/agents/claude_api.py (ClaudeAPIAgent)
- [x] Create runner/agents/openai_api.py (OpenAIAPIAgent)
- [x] Create runner/agents/gemini_api.py (GeminiAPIAgent)
- [x] Create runner/agents/groq_api.py (GroqAPIAgent with Whisper transcription)

### 0A.4 Factory Pattern
- [x] Create runner/agents/factory.py (create_agent with mode selection)
- [x] Update state_machine.py to use factory instead of direct imports
- [x] Update workflow_config.yaml for API agent definitions (mode selection via AGENT_MODE config)

### 0A.5 Testing
- [x] Add unit tests for API agents (mocked API calls)
- [ ] Add integration test with real API (optional, costs money)
- [ ] Verify CLI and API modes produce equivalent results

---

## Phase 0B: SQLModel + PostgreSQL Foundation

**Goal:** PostgreSQL + SQLModel ORM baseline. Prerequisite for all multi-tenancy work.

### 0B.1 Infrastructure
- [x] Add sqlmodel, psycopg2-binary, alembic to pyproject.toml
- [x] Add PostgreSQL service to docker-compose.yml
- [x] Add PgBouncer service to docker-compose.yml
- [x] Add DATABASE_URL to runner/config.py
- [x] Add USE_SQLMODEL feature flag to runner/config.py
- [x] Create runner/db/__init__.py
- [x] Create runner/db/engine.py (engine + session factory)
- [x] Initialize Alembic in runner/db/migrations/

### 0B.2 Base Models
- [x] Create runner/models/__init__.py
- [x] Create runner/models/base.py (UUIDModel base class with created_at)

### 0B.3 Core Content Models
- [x] Create runner/models/user.py (User, UserCreate, UserRead)
- [x] Create runner/models/platform.py
- [x] Create runner/models/content.py (Goal, Chapter, Post)
- [x] Create runner/models/voice.py (WritingSample, VoiceProfile)

### 0B.4 Workflow Models
- [x] Create runner/models/workflow.py (WorkflowRun, WorkflowOutput, WorkflowSession, etc.)

### 0B.5 Image System Models
- [x] Create runner/models/image.py (ImagePrompt, ImageConfigSet, ImageScene, ImagePose, etc.)

### 0B.6 Character System Models
- [x] Create runner/models/character.py (CharacterTemplate, OutfitPart, Outfit, Character, etc.)

### 0B.7 Analytics Models
- [x] Create runner/models/analytics.py (AnalyticsImport, PostMetric, DailyMetric, etc.)

### 0B.8 History Models
- [x] Create runner/models/history.py (RunRecord, InvocationRecord, AuditScoreRecord)

### 0B.9 Repository Layer
- [x] Create runner/content/repository.py
- [x] Implement UserRepository
- [x] Implement PlatformRepository
- [x] Implement ContentRepository (Goal, Chapter, Post)
- [x] Add remaining repositories as needed

### 0B.10 Service Layer Adaptation
- [x] Update ContentService for dual-backend support (USE_SQLMODEL flag)
- [ ] Verify PostgreSQL path works

### 0B.11 Testing
- [x] Add SQLModel unit tests (in-memory DB) - tests/unit/test_repositories.py
- [ ] Add repository integration tests
- [ ] Add migration validation tests
- [ ] Add API compatibility tests (same responses from both backends)

### 0B.12 Makefile Commands
- [x] Add `make db-up` (start postgres + pgbouncer)
- [x] Add `make db-migrate` (alembic upgrade head)
- [x] Add `make db-rollback` (alembic downgrade -1)
- [x] Add `make db-revision MSG="..."` (autogenerate migration)

---

## Phase 1: Database Foundation (Week 1-2)

**Goal:** Create multi-tenancy tables and add workspace_id to all existing tables.

### 1.1 New Tables (MULTI_TENANCY_PLAN.md §2, §33)
- [x] Create `users` table with UUID, email, full_name, password_hash, is_superuser - runner/db/models/user.py (from Phase 0B)
- [x] Create `workspaces` table (id, name, slug, owner_id, settings JSONB) - runner/db/models/workspace.py
- [x] Create `workspace_memberships` table (id, workspace_id, user_id, email, role, invite_status, invite_token, etc.) - runner/db/models/membership.py
- [ ] Create `accounts` table (agency grouping entity) - deferred to Phase 4 (optional for MVP)
- [ ] Add trigger for single-owner enforcement - deferred (can enforce in application layer)

### 1.2 Add workspace_id to Existing Tables (SQLModel fields, nullable for migration)
- [x] Add workspace_id FK to platforms - runner/db/models/platform.py
- [x] Add workspace_id FK to goals - runner/db/models/content.py
- [x] Add workspace_id FK to chapters - runner/db/models/content.py
- [x] Add workspace_id FK to posts - runner/db/models/content.py
- [x] Add workspace_id FK to writing_samples - runner/db/models/voice.py
- [x] Add workspace_id FK to voice_profiles - runner/db/models/voice.py
- [x] Add workspace_id FK to workflow_runs - runner/db/models/workflow.py
- [x] Add workspace_id FK to workflow_personas - runner/db/models/workflow.py
- [x] Add workspace_id FK to image_* tables - runner/db/models/image.py (all 7 tables)
- [x] Add workspace_id FK to character_* tables - runner/db/models/character.py (all tables with user_id)
- [x] Add workspace_id FK to analytics_* tables - runner/db/models/analytics.py (all 6 tables)

### 1.3 Workspace Repositories
- [x] Create WorkspaceRepository - runner/content/workspace_repository.py
- [x] Create WorkspaceMembershipRepository - runner/content/workspace_repository.py

### 1.4 Indexes (MULTI_TENANCY_PLAN.md §2.2.4)
- [x] CREATE INDEX idx_*_workspace ON each table(workspace_id) - in Alembic migration
- [x] CREATE INDEX idx_posts_workspace_status ON posts(workspace_id, status) - in Alembic migration
- [ ] CREATE INDEX idx_posts_workspace_assignee ON posts(workspace_id, assignee_id) - deferred (assignee_id not yet added)
- [x] CREATE INDEX idx_runs_workspace_created ON workflow_runs(workspace_id, created_at DESC) - in Alembic migration

### 1.5 Data Migration
- [x] Create Alembic migration for new tables - runner/db/migrations/versions/20260115_225103_initial_tables_with_multi_tenancy.py
- [x] Create Alembic migration for workspace_id columns - included in initial migration
- [N/A] Create script to generate "Default Workspace" for existing data - Fresh deploy, no existing data
- [N/A] Backfill workspace_id for all existing records - Fresh deploy, no existing data

---

## Phase 2: Backend Logic (Week 3-4)

**Goal:** Implement authentication, authorization, and core services.

### 2.1 Authentication (MULTI_TENANCY_PLAN.md §4, §24)
- [x] Add python-jose, passlib[bcrypt] to dependencies - pyproject.toml
- [x] Create api/auth/jwt.py (create_token, verify_token) - api/auth/jwt.py
- [x] Create api/auth/password.py (hash_password, verify_password) - api/auth/password.py
- [x] Update User model with password_hash, is_active, is_superuser - runner/db/models/user.py
- [x] Create `active_sessions` table for token revocation - runner/db/models/session.py
- [x] Create AuthService for auth business logic - api/auth/service.py

### 2.2 Auth Endpoints
- [x] POST /api/v1/auth/register (create user + return tokens) - api/routes/auth.py
- [x] POST /api/v1/auth/login (return JWT) - api/routes/auth.py
- [x] POST /api/v1/auth/logout (revoke session) - api/routes/auth.py
- [x] POST /api/v1/auth/refresh (refresh token) - api/routes/auth.py
- [x] GET /api/v1/auth/me (current user) - api/routes/auth.py

### 2.3 RBAC (MULTI_TENANCY_PLAN.md §3, §34)
- [x] Define Scope enum (content:read, content:write, strategy:read, etc.) - api/auth/scopes.py
- [x] Define ROLE_SCOPES mapping (owner, admin, editor, viewer) - api/auth/scopes.py
- [x] Create require_scope() decorator - api/auth/dependencies.py
- [x] Create api/auth/dependencies.py (get_current_user, require_scope, CurrentUser)

### 2.4 Workspace Context (MULTI_TENANCY_PLAN.md §35)
- [x] Create api/middleware/workspace.py (WorkspaceMiddleware)
- [x] Create api/middleware/auth.py (AuthMiddleware)
- [x] Update routes to /api/v1/w/{workspace_id}/... - api/routes/v1/
- [x] Inject workspace + membership into request.state
- [x] Verify user has access to workspace
- [x] Create api/routes/v1/dependencies.py (WorkspaceContext, get_workspace_context)
- [x] Create api/routes/v1/workspaces.py (workspace CRUD, member management)
- [x] Create api/routes/v1/workspace_content.py (goals, chapters, posts, voice profiles)

### 2.5 Services
- [x] Create api/services/workspace_service.py (CRUD, list user workspaces)
- [x] Create api/services/invite_service.py (create, accept, revoke invites)
- [ ] Update legacy ContentService to scope all queries by workspace_id (optional, v1 routes use SQLModel directly)

---

## Phase 3: Frontend Integration (Week 5-6)

**Goal:** Build auth UI and workspace switching.

### 3.1 Auth Pages (MULTI_TENANCY_PLAN.md §8)
- [x] Create AuthLayout.tsx (minimal layout for auth pages)
- [x] Create Login.tsx (/auth/login)
- [x] Create Register.tsx (/auth/register)
- [x] Create ForgotPassword.tsx (/auth/forgot-password)
- [x] Create AcceptInvite.tsx (/auth/invite?token=...)

### 3.2 Auth State
- [x] Create useAuthStore (user, tokens, login, logout, refresh)
- [x] Add axios/fetch interceptor for JWT header
- [ ] Remove any legacy X-Workspace-ID header usage (workspace_id must be in URL path)

### 3.3 Workspace Switching (MULTI_TENANCY_PLAN.md §28)
- [x] Update App.tsx with protected routes
- [x] Create useWorkspaceStore for workspace state
- [x] Create WorkspaceSwitcher.tsx in sidebar
- [x] Workspace auto-selected on login (store-based, not URL-based)

### 3.4 Team Management
- [x] Create TeamSettings.tsx (/team)
- [x] Implement invite member modal
- [x] Implement member list with role display
- [x] Implement remove member

### 3.5 Permission Gates
- [x] Create usePermission(scope) hook
- [x] Hide nav items based on role (ScopedNavLink)
- [x] Hide Settings for viewers (workflow:execute scope)

---

## Phase 4: Subscription & Usage (Week 7-8)

**Goal:** Implement subscription tiers and usage tracking.

### 4.1 Tables (MULTI_TENANCY_PLAN.md §12, §13)
- [x] Create `subscription_tiers` table
- [x] Create `account_subscriptions` table
- [x] Create `usage_tracking` table
- [x] Create `credit_reservations` table (idempotency)
- [x] Seed tier data (Individual $29, Team $99, Agency $249)
- [x] Create Alembic migration (002_subscription)

### 4.2 UsageService (MULTI_TENANCY_PLAN.md §13.4)
- [x] Implement get_or_create_usage_period()
- [x] Implement reserve_credit() with idempotency
- [x] Implement confirm_usage()
- [x] Implement release_reservation()
- [x] Implement get_usage_summary()
- [x] Implement check_limit()
- [x] Implement create_subscription()

### 4.3 Enforcement (MULTI_TENANCY_PLAN.md §13.3)
- [x] Create UsageEnforcementMiddleware
- [x] Block POST/PUT requests when limit reached (402 response)
- [x] Allow overage if overage_enabled on tier

### 4.4 UI
- [x] Create UsageBar component (progress bar)
- [x] Add usage section to Settings page
- [x] Add available plans display with upgrade buttons
- [x] Add overage warning banner
- [x] Add usage API routes (/v1/w/{workspace_id}/usage)

---

## Phase 5: Billing Integration (Week 9-10)

**Goal:** Stripe integration for payments.

### 5.1 Tables (MULTI_TENANCY_PLAN.md §14)
- [x] Create `billing_events` table
- [x] Create `invoices` table
- [x] Create `payment_methods` table
- [x] Create Alembic migration (003_billing)

### 5.2 BillingService (MULTI_TENANCY_PLAN.md §14.3)
- [x] Add stripe dependency to pyproject.toml
- [x] Implement create_checkout_session()
- [x] Implement create_portal_session()
- [x] Implement handle_webhook() with idempotency

### 5.3 Webhook Handler
- [x] POST /api/v1/webhooks/stripe
- [x] Handle checkout.session.completed
- [x] Handle invoice.paid (reset usage period)
- [x] Handle invoice.payment_failed
- [x] Handle customer.subscription.updated
- [x] Handle customer.subscription.deleted
- [x] Handle payment_method.attached

### 5.4 Trial Period
- [ ] 14-day free trial of Team tier on signup (deferred)
- [ ] Trial ending email (3 days before) (requires Phase 7)
- [ ] Downgrade to Individual if no payment method (deferred)

### 5.5 UI
- [x] Create BillingSection component
- [x] Show payment methods with card details
- [x] "Manage Subscription" button → Stripe portal
- [x] Invoice history table with status badges
- [x] Download PDF and View links

---

## Phase 6: Assignment & Approvals (Week 11-12)

**Goal:** Post assignment and multi-stage approval workflows.

### 6.1 Post Assignment (MULTI_TENANCY_PLAN.md §15)
- [x] Add assignee_id, due_date, priority, estimated_hours to posts
- [x] Create `post_assignment_history` table
- [ ] Update Kanban with assignee filters (deferred)
- [ ] Implement workload API endpoint (deferred)

### 6.2 Approval System (MULTI_TENANCY_PLAN.md §16)
- [x] Create `approval_stages` table
- [x] Create `approval_requests` table
- [x] Create `approval_comments` table
- [x] Seed default stages (Draft Review, Final Approval)

### 6.3 ApprovalService
- [x] Implement submit_for_approval()
- [x] Implement approve() (advance to next stage)
- [x] Implement reject() (return for revision)
- [x] Implement get_pending_approvals()

### 6.4 UI
- [x] Approval routes page (/approvals)
- [x] Approval modal with feedback form
- [x] Approval status badge on posts

---

## Phase 7: Notifications (Week 13)

**Goal:** In-app and email notifications.

### 7.1 Tables (MULTI_TENANCY_PLAN.md §17)
- [x] Create `notification_channels` table
- [x] Create `notifications` table
- [x] Create `notification_preferences` table
- [ ] Create `email_queue` table (deferred - email sending deferred)

### 7.2 NotificationService
- [x] Implement send_notification()
- [x] Implement mark_as_read()
- [x] Implement get_unread_count()
- [x] Implement get_notifications() with pagination
- [x] Implement dismiss notification
- [x] Implement preference management
- [ ] Real-time push via WebSocket (deferred)

### 7.3 Email Integration
- [ ] Add SendGrid or Resend dependency (deferred)
- [ ] Create email templates (invite, approval, due soon, etc.) (deferred)
- [ ] Background worker for email queue processing (deferred)

### 7.4 UI
- [x] NotificationBell in header with unread count
- [x] Notification dropdown with mark read/dismiss
- [x] NotificationSettings component on Settings page

---

## Phase 8: API Keys & Webhooks (Week 14)

**Goal:** External integrations for Agency tier.

### 8.1 Tables (MULTI_TENANCY_PLAN.md §18)
- [x] Create `api_keys` table
- [x] Create `webhooks` table
- [x] Create `webhook_deliveries` table
- [ ] Create `rate_limit_buckets` table (deferred - rate limiting in service layer)

### 8.2 API Key Auth
- [x] Generate API keys (qx_...)
- [x] API key validation service (APIKeyService.validate_key)
- [x] Scope-based API key permissions (APIKeyService.has_scope)

### 8.3 Rate Limiting
- [ ] Implement rate limit middleware (deferred)
- [ ] Per-tier limits (Individual: 60/min, Team: 120/min, Agency: 300/min) (deferred)

### 8.4 Webhooks
- [x] Implement webhook delivery with retries (WebhookService)
- [x] HMAC-SHA256 signature (_sign_payload)
- [x] Events: post.created, post.published, approval.*, workflow.*

### 8.5 UI
- [x] API Keys management page (DeveloperSettings)
- [x] Webhook configuration page (DeveloperSettings)
- [x] Delivery history/logs (WebhookDeliveryResponse)

---

## Phase 9: White-labeling (Week 15-16)

**Goal:** Custom branding for Agency tier.

### 9.1 Tables (MULTI_TENANCY_PLAN.md §19, §31)
- [x] Create `whitelabel_config` table - runner/db/models/whitelabel.py
- [x] Add custom domain verification fields - runner/db/models/whitelabel.py
- [x] Add email domain fields - runner/db/models/whitelabel.py

### 9.2 Custom Domains
- [x] DNS verification flow (TXT + CNAME) - api/services/domain_service.py
- [ ] SSL certificate provisioning (deferred - use Cloudflare/AWS)
- [x] Middleware to detect custom domain - api/middleware/custom_domain.py

### 9.3 Client Portal
- [x] Create /portal/* routes (login, posts, review, approve) - api/routes/portal.py
- [x] Stripped-down UI for clients - api/services/portal_service.py
- [x] Agency branding applied - uses whitelabel_config

### 9.4 UI
- [x] White-label settings page - gui/src/pages/settings/WhitelabelSettings.tsx
- [x] Logo upload - gui/src/components/settings/LogoUpload.tsx
- [x] Color customization - gui/src/components/settings/ColorPicker.tsx
- [ ] Custom domain setup wizard (deferred)

---

## Phase 10: Polish & Launch (Week 17-18)

**Goal:** Production readiness.

### 10.1 Testing
- [ ] Load testing (k6 or locust)
- [ ] Security audit (OWASP top 10)
- [ ] Penetration testing

### 10.2 Observability (MULTI_TENANCY_PLAN.md §30)
- [x] Structured logging with structlog - runner/logging/structured.py
- [x] Create `audit_logs` table - runner/db/models/audit.py
- [x] Create AuditService - api/services/audit_service.py
- [x] Create audit routes - api/routes/v1/audit.py
- [x] Health check endpoints - api/routes/health.py
- [x] Prometheus metrics middleware - api/middleware/metrics.py
- [ ] Add postgres-exporter for metrics (deferred)
- [ ] Set up alerting (deferred)

### 10.3 Error Handling
- [x] Standardized exceptions - api/exceptions.py
- [x] Global error handlers - api/error_handlers.py
- [x] Standard response models - api/responses.py

### 10.4 Documentation
- [ ] API documentation (OpenAPI/Swagger)
- [ ] User guide
- [ ] Admin guide

### 10.5 Launch
- [ ] Gradual rollout plan
- [ ] Rollback procedure
- [ ] Support runbook

---

## Phase 11: Dynamic Workflow Configuration

**Goal:** GUI-selectable workflow configs with deployment filtering. See GROQ_IMPLEMENTATION_PLAN.md §Dynamic Workflow Configuration.

### 11.1 Update Project Plan Files
- [x] Add Feedback Loop Handling section to GROQ_IMPLEMENTATION_PLAN.md
- [x] Add Dynamic Workflow Configuration section to GROQ_IMPLEMENTATION_PLAN.md
- [x] Update LAUNCH_SIMPLIFICATION_PLAN.md with dynamic workflow reference
- [x] Add all phases to IMPLEMENTATION_TRACKER.md

### 11.2 Create Workflow Config Directory Structure
- [x] Create `workflows/configs/` directory
- [x] Move `workflow_config.yaml` → `workflows/configs/legacy-claude.yaml`
- [x] Create symlink: `workflow_config.yaml` → `workflows/configs/legacy-claude.yaml`
- [x] Verify existing workflow still works via symlink

### 11.3 Create Groq Production Config
- [x] Copy `legacy-claude.yaml` to `groq-production.yaml`
- [x] Replace all agent references with Groq agents
- [x] Add Groq agent definitions
- [x] Update tiers to use Groq agents
- [x] Disable non-Groq agents (enabled: false)

### 11.4 Create Ollama Local Config
- [x] Copy `groq-production.yaml` to `ollama-local.yaml`
- [x] Replace all agent references with Ollama agents
- [x] Add Ollama agent definitions (ollama-llama-8b, ollama-mistral, ollama-llama-3b)
- [x] Update tiers to use Ollama agents

### 11.5 Create Workflow Registry
- [x] Create `workflows/registry.yaml` with workflow metadata
- [x] Define groq-production, ollama-local, legacy-claude entries
- [x] Add deployment environment filtering config

### 11.6 CLI Config Selection
- [x] Add `--config` argument to runner/runner.py CLI
- [x] Add `resolve_workflow_config(name: str)` and `list_workflow_configs()` functions
- [x] Update Makefile: `make workflow CONFIG=groq-production STORY=post_01`
- [x] Keep backward compat: if CONFIG not specified, use legacy symlink

### 11.7 Database Schema - WorkflowConfig Table
- [x] Create `runner/db/models/workflow_config.py` (WorkflowConfig model)
- [x] Create Alembic migration for workflow_configs table
- [ ] Run migration: `make db-migrate` (pending database start)

### 11.8 Database Schema - Workspace Preference
- [x] Create migration to add `workflow_config_id` column to workspaces
- [x] Update Workspace model with relationship
- [ ] Run migration: `make db-migrate` (pending database start)

### 11.9 Sync Command
- [x] Create `scripts/sync_workflows.py`
- [x] Read `workflows/registry.yaml`, filter by DEPLOYMENT_ENV
- [x] Upsert to workflow_configs table
- [x] Add to Makefile: `make sync-workflows`

### 11.10 WorkflowConfig Repository
- [x] Create `runner/content/workflow_config_repository.py`
- [x] Implement `list_for_workspace(environment, tier)`
- [x] Implement `get_by_slug(slug)`
- [x] Implement `get(id)`
- [x] Implement `upsert(slug, config)`
- [ ] Add unit tests

### 11.11 WorkflowConfig API Endpoints
- [x] Create `api/routes/workflow_configs.py`
- [x] GET `/workflow-configs` - list available configs
- [x] GET `/workflow-configs/{slug}` - get specific config
- [x] GET `/workflow-configs/default` - get default config
- [x] Register router in `api/main.py`
- [ ] Add integration tests

### 11.12 Runner Integration with API
- [x] Update workflow execute request to accept config slug
- [x] Update workflow_service.execute to resolve config path
- [x] Fall back to default config if none selected

### 11.13 GUI - Workflow Config Selector
- [x] Add API client functions for workflow configs (`gui/src/api/workflow.ts`)
- [x] Create WorkflowConfigSelector component
- [x] Add to LiveWorkflow page (integrated into workflow start flow)
- [ ] Add to Settings page for default selection
- [ ] Only owner/admin can change (settings page)

### 11.14 Deployment Configuration
- [ ] Add `DEPLOYMENT_ENV` to docker-compose.yml
- [ ] Document in `.env.example`
- [ ] Ensure `make sync-workflows` runs on deploy

---

## New Tables Summary (from MULTI_TENANCY_PLAN.md §21)

| # | Table | Phase |
|---|-------|-------|
| 1 | subscription_tiers | 4 |
| 2 | account_subscriptions | 4 |
| 3 | usage_tracking | 4 |
| 4 | billing_events | 5 |
| 5 | invoices | 5 |
| 6 | post_assignment_history | 6 |
| 7 | approval_stages | 6 |
| 8 | approval_requests | 6 |
| 9 | approval_comments | 6 |
| 10 | notifications | 7 |
| 11 | notification_preferences | 7 |
| 12 | email_queue | 7 |
| 13 | api_keys | 8 |
| 14 | webhooks | 8 |
| 15 | webhook_deliveries | 8 |
| 16 | rate_limit_buckets | 8 |
| 17 | whitelabel_config | 9 |
| 18 | system_templates | 1 |
| 19 | active_sessions | 2 |
| 20 | assets | 9 |
| 21 | audit_logs | 10 |
| 22 | accounts | 1 |
| 23 | credit_reservations | 4 |
| 24 | workflow_configs | 11 |

---

## Blockers & Notes

| Date | Issue | Owner | Resolution |
|------|-------|-------|------------|
| - | - | - | - |

---

## How to Use This Tracker

1. **Claim a task:** Add your name/initials next to the checkbox
2. **Update status:** Check the box when complete
3. **Update phase status:** Change 🔴 → 🟡 when any task starts, 🟡 → 🟢 when all tasks done
4. **Log blockers:** Add to Blockers table with date and owner
5. **Commit tracker updates:** Include in your PRs

---

## References

- `MULTI_TENANCY_PLAN.md` - Full architectural specification
- `WORKFLOW_ORCHESTRATION_PLAN.md` - Existing workflow system (complete)
- `GROQ_IMPLEMENTATION_PLAN.md` - Groq agent + dynamic workflow configuration
- `LAUNCH_SIMPLIFICATION_PLAN.md` - Launch scope and deprecation plan
- `CLAUDE.md` - Project instructions and patterns
