# Multi-Tenancy & RBAC Implementation Plan

## 1. Executive Summary
This plan outlines the architectural changes required to transform **Postmagiq** from a single-user application into a multi-tenant platform supporting agencies, workspaces, and granular Role-Based Access Control (RBAC).

**Core Goals:**
1.  **Multi-Tenancy:** Isolate data per workspace (e.g., separate strategy, content, and analytics).
2.  **Agency Model:** Allow a single user (Agent) to access multiple workspaces.
3.  **RBAC:** Define permissions for viewing, editing, and publishing content.

## 2. Data Model Architecture

We will introduce three key entities: `User`, `Workspace`, and `WorkspaceUser` (Membership).

### 2.1 Entity Relationship Diagram (Conceptual)
```mermaid
erDiagram
    User ||--o{ WorkspaceUser : "is member of"
    Workspace ||--o{ WorkspaceUser : "has member"
    Workspace ||--o{ Content : "owns"
    Workspace ||--o{ Strategy : "owns"
    WorkspaceUser }|..|{ Role : "has role"
```

### 2.2 Schema Definitions

**Note on Identifiers:** To ensure security (anti-id guessing) and scalability, **ALL** primary keys and foreign keys across the entire database (new and existing tables) will be migrated to **UUID v4**.

**1. Users Table**
*   Global identity provider.
*   `id`: UUID (Primary Key)
*   `email`: String (Unique)
*   `full_name`: String
*   `created_at`: Timestamp

**2. Workspaces Table**
*   The boundary of data isolation.
*   `id`: UUID (Primary Key)
*   `name`: String (e.g., "Acme Corp", "Client X")
*   `owner_id`: UUID (Foreign Key to Users)
*   `settings`: JSON (Global config, limits, enabled features)

**3. Workspace_Users Table (Junction)**
*   Links users to workspaces with a specific role.
*   `workspace_id`: UUID (Foreign Key to Workspaces)
*   `user_id`: UUID (Foreign Key to Users)
*   `role`: Enum (`owner`, `admin`, `editor`, `viewer`)
*   **Constraint:** Compound Primary Key (`workspace_id`, `user_id`)

**4. Index Requirements (MANDATORY)**

Every table with `workspace_id` MUST have an index. Without indexes, queries become full table scans as data grows.

```sql
-- Required indexes for all workspace-scoped tables
CREATE INDEX idx_goals_workspace ON goals(workspace_id);
CREATE INDEX idx_chapters_workspace ON chapters(workspace_id);
CREATE INDEX idx_posts_workspace ON posts(workspace_id);
CREATE INDEX idx_runs_workspace ON runs(workspace_id);
CREATE INDEX idx_telemetry_events_workspace ON telemetry_events(workspace_id);
CREATE INDEX idx_analytics_workspace ON analytics(workspace_id);

-- Compound indexes for common query patterns
CREATE INDEX idx_posts_workspace_status ON posts(workspace_id, status);
CREATE INDEX idx_posts_workspace_assignee ON posts(workspace_id, assignee_id);
CREATE INDEX idx_runs_workspace_created ON runs(workspace_id, created_at DESC);
CREATE INDEX idx_telemetry_workspace_category ON telemetry_events(workspace_id, event_category);
```

**5. Data Migration Strategy**
*   **Migration Step 1:** Convert all existing table primary keys from `INTEGER` to `UUID`.
*   **Migration Step 2:** Add `workspace_id` (UUID) column to all existing content tables (`goals`, `chapters`, `posts`, `runs`, `analytics`).
*   **Migration Step 3:** Create a "Default Workspace" with a new UUID.
*   **Migration Step 4:** Assign all existing data to this Default Workspace and update foreign key relationships.
*   **Migration Step 5:** Enforce `NOT NULL` and `FOREIGN KEY` constraints on `workspace_id`.
*   **Migration Step 6:** Create all required indexes on `workspace_id` columns.

## 3. RBAC & Permissions System

We will implement a granular permission system mapped to roles.

### 3.1 Roles Definition

| Role | Description | Key Permissions |
| :--- | :--- | :--- |
| **Owner** | Billing owner & agency head | All permissions + Billing + Delete Workspace |
| **Admin** | Workspace manager | Manage Users, Edit Strategy, Configure Integrations |
| **Editor** | Content creator | Create/Edit Posts, Run Workflows, View Strategy |
| **Viewer** | Client/Reviewer | View Posts, View Analytics, Approve/Reject (if enabled) |

### 3.2 Permission Scopes (examples)
*   `content:read`, `content:write`, `content:publish`
*   `strategy:read`, `strategy:write`
*   `workspace:settings`, `workspace:users`
*   `workflow:run`

## 4. API Layer Changes

### 4.1 Authentication & Context Middleware
*   **Authentication:** JWT-based auth (likely via external provider like Auth0 or Supabase, or internal simple JWT).
*   **Context Middleware:**
    1.  Extract `user_id` from JWT.
    2.  Extract `workspace_id` from Header (`X-Workspace-ID`).
    3.  **Verify:** Check if `user_id` is a member of `workspace_id`.
    4.  **Inject:** Inject `current_user` and `current_workspace` into the request context (`request.state`).

### 4.2 Endpoint Refactoring
*   **Before:** `GET /posts` (Returns all posts in DB)
*   **After:** `GET /posts` (Returns `SELECT * FROM posts WHERE workspace_id = :current_workspace_id`)

All service methods (e.g., `ContentService.get_posts`) must be updated to accept `workspace_id` as a mandatory argument.

### 4.3 API Versioning Strategy
To ensure stability for agency integrations and future mobile apps, we will adopt a strict versioning policy.

**1. URI Versioning (Primary)**
*   All endpoints will be prefixed with the version number: `/api/v1/...`
*   Current endpoints will be migrated to `v1`.
*   Breaking changes (e.g., schema restructuring, removing fields) will trigger a bump to `/api/v2/`.

**2. Implementation approach**
*   **FastAPI Router:** Use `APIRouter` with `prefix="/v1"`.
*   **Directory Structure:** Organize controllers by version:
    ```
    api/
      routers/
        v1/
          content.py
          auth.py
        v2/
          content.py
    ```

**3. Deprecation Policy**
*   **Sunset Header:** Responses from deprecated versions will include a `Sunset` header (HTTP date) indicating when the version will be disabled.
*   **Warning:** A `Warning` header will be sent 3 months prior to removal.
*   **Support Window:** We will support the previous major version for 6 months after a new major version is released.

## 5. Frontend (GUI) Changes

### 5.1 Global State Updates (`workflowStore` & `authStore`)
*   **New Store:** `useAuthStore` to manage `user`, `workspaces`, and `activeWorkspaceId`.
*   **Interceptor:** Axios/Fetch interceptor to attach `X-Workspace-ID` header to every request.

### 5.2 UI Components
*   **Workspace Switcher:** A dropdown in the Sidebar (top-left) to switch between available workspaces (Agency View).
*   **Role-Based Hiding:**
    *   Hide "Settings" and "Strategies" for `Viewer` role.
    *   Disable "Run Workflow" buttons for `Viewer` role.
*   **Team Management Page:** Interface for Admins to invite users by email and assign roles.
*   **Admin Pages:** Dedicated routes for Workspace configurations (`/settings/team`, `/settings/billing`).
*   **Auth Pages:** Clean, branded layouts for Login, Register, and Onboarding.

## 6. Implementation Phases

### Phase 1: Database Foundation
1.  Create `users`, `workspaces`, `workspace_users` tables.
2.  Run migration script to backfill existing data into a default workspace.
3.  Add `workspace_id` foreign keys to all content tables.

### Phase 2: Backend Logic
1.  Implement `AuthService` (Login/Register).
2.  Implement `WorkspaceService` (CRUD Workspaces, Invite Members).
3.  Update `ContentService` and `RunService` to scope queries by `workspace_id`.
4.  Add Authorization Middleware to FastApi.

### Phase 3: Frontend Integration
1.  Build Login/Registration pages.
2.  Implement Workspace Switcher in `Sidebar.tsx`.
3.  Update API client to send `X-Workspace-ID`.
4.  Implement UI permission gates.

## 7. Security Considerations
*   **Strict Scoping:** Ensure *every* SQL query includes `WHERE workspace_id = ?`. Use a repository pattern or ORM mixin to enforce this automatically and prevent data leaks.
*   **Invite Flow:** Secure token-based email invitations for adding users to workspaces.

## 8. Authentication & Administration UI

To fully support the agency model and secure access, we will implement the following dedicated interfaces.

### 8.1 Authentication Flows (Public Routes)
These pages will live outside the main app layout (`MainLayout`) and use a focused `AuthLayout`.

*   **Login (`/auth/login`):** Email/Password or OAuth (Google/Microsoft) entry point.
*   **Register (`/auth/register`):** New agency signup flow. Creates a `User` and a `Default Workspace`.
*   **Accept Invitation (`/auth/invite?token=...`):** Landing page for users invited to an existing workspace.
*   **Forgot Password (`/auth/reset-password`):** Standard recovery flow.

### 8.2 Workspace Administration (Inside App)
Accessible only to `Owner` and `Admin` roles.

*   **Team Settings (`/settings/team`):**
    *   List all members in the current workspace.
    *   "Invite Member" modal (Email + Role selection).
    *   Revoke access / Change role.
*   **Workspace Settings (`/settings/general`):**
    *   Rename workspace.
    *   Upload logo (for white-labeling).
    *   Delete workspace (Owner only).

### 8.3 Super Admin Dashboard (System Owner Only)
A hidden administrative view for the platform operator (you), accessible via a specific `is_superuser` flag on the `User` model.

*   **Route:** `/admin/overview`
*   **Capabilities:**
    *   View all registered Tenants/Workspaces.
    *   Impersonate User (Login as specific user for support).
    *   System-wide analytics (Total posts generated, Token usage across all clients).

## 9. User Activity & Telemetry Logging

To drive product improvement and provide audit trails, we will implement a comprehensive telemetry system.

### 9.1 Data Capture Strategy
We need to capture granular user interactions beyond just API calls.

**Key Metrics to Track:**
*   **Navigation:** Page views, feature usage frequency.
*   **Configuration:** Which settings/presets are most used (e.g., "Tone: Professional" vs "Casual").
*   **Refinement Behavior:**
    *   Number of iterations per post.
    *   Specific feedback text provided during "Human Approval" steps.
    *   Acceptance rate of AI suggestions.
*   **Performance:** Latency of generation vs User patience (cancellations).

### 9.2 Telemetry Schema (Events Table)
This table will likely grow fast, so it should be optimized for write-heavy loads (TimescaleDB or partitioned Postgres).

```sql
CREATE TABLE telemetry_events (
    id UUID PRIMARY KEY,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    user_id UUID NOT NULL,
    workspace_id UUID NOT NULL,
    event_category VARCHAR(50),  -- 'navigation', 'config', 'generation', 'feedback'
    event_action VARCHAR(50),    -- 'click_button', 'update_setting', 'refine_post'
    entity_id UUID,              -- Optional: ID of the Post/Story/Run being interacted with
    payload JSONB                -- Flexible data: { "old_value": "A", "new_value": "B", "feedback_text": "Too long" }
);
```

### 9.3 Implementation
1.  **Frontend Logger:** A lightweight utility in the GUI to batch and send events.
    *   `Logger.log('config_change', { setting: 'tone', value: 'witty' })`
    *   `Logger.log('refinement', { attempts: 3, final_sentiment: 'positive' })`
2.  **API Endpoint:** `POST /api/v1/telemetry/events` (Batched).
3.  **Analytics Dashboard:** A view for Admins to visualize "Top Used Configs" or "Common Refinement Requests".

## 10. Content Kanban Board

To improve content visibility and execution management, we will introduce a Jira-style Kanban board. This will be an **additive** view, co-existing with the current "Live Workflow" visualization.

### 10.1 Board Architecture
The board will visualize `Posts` as cards moving through lifecycle stages (Swimlanes).

**Default Swimlanes (Mapped to Post Status):**
1.  **Backlog / Ideas:** (`status='not_started'`) - Raw ideas or chapter outlines.
2.  **Drafting:** (`status='drafting'`) - Currently being processed by the AI Writer.
3.  **In Review:** (`status='review'`) - Awaiting human approval or feedback loops.
4.  **Polishing:** (`status='polishing'`) - Final AI touches or image generation.
5.  **Ready to Publish:** (`status='ready'`) - Completed, approved, and scheduled.
6.  **Published:** (`status='published'`) - Live on LinkedIn.

### 10.2 Core Features
*   **Drag-and-Drop Interface:** Users can drag a post card from "Backlog" to "Drafting" to trigger the `Start Workflow` action for that specific post.
*   **Quick Actions:** Cards will have buttons to:
    *   "Run" (Start/Resume workflow).
    *   "Edit" (Open the post in the Editor).
    *   "View" (See the generated content).
*   **Configurable View:**
    *   **Group By:** Chapter, Status, or Assignee (for multi-user workspaces).
    *   **Filters:** "My Posts", "Needs Attention", "Chapter 1 Only".
*   **Workspace Scoping:** The board naturally respects the multi-tenancy model, showing only posts for the `current_workspace`.

### 10.3 Integration Logic
*   **State Sync:** Moving a card is not just a UI change; it triggers a backend status update or workflow event.
    *   *Example:* Dragging from "In Review" -> "Drafting" might trigger a "Reject/Refine" workflow step with a prompt input.
*   **Real-time Updates:** The board will listen to the existing WebSocket events. When a background run completes, the card automatically jumps to the next column.

### 10.4 UI Implementation
*   **Route:** `/board` (New main navigation item).
*   **Library:** `@dnd-kit/core` or `react-beautiful-dnd` for smooth interactions.
*   **Design:** Professional "Postmagiq" aesthetic (Slate/Indigo), maximizing screen real estate for the columns.

## 11. Database Migration (SQLite to PostgreSQL)

To support concurrent users, UUIDs, and the robust locking required for multi-tenancy, we will migrate from SQLite to **PostgreSQL**.

**Mandate:** SQLite will be deprecated. The application will strictly require a Dockerized environment to run.

### 11.1 Infrastructure Changes
*   **Docker Compose:**
    *   Add a `postgres` service (v16+) to `docker-compose.yml`.
    *   Configure persistent volumes for data safety (`pgdata`).
    *   Set up environment variables for connection strings (`DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`).
*   **Application Config:**
    *   Update `runner/content/database.py` (and relevant config files) to switch from `sqlite://` to `postgresql+asyncpg://`.
    *   Ensure all database connection logic uses connection pooling (e.g., `SQLAlchemy` pool).

### 11.2 Migration Strategy

**Step 1: Schema Migration (The Structure)**
*   We will introduce **Alembic** for proper database migrations.
*   Generate an initial migration script that matches the *current* SQLite schema but adapted for Postgres (e.g., proper Enum types, Boolean fields).
*   Generate a second migration script for the *new* Multi-Tenancy schema (UUIDs, Workspaces table, etc.).

**Step 2: Data Transfer (The Content)**
*   Since UUIDs are being introduced simultaneously, direct replication is not possible.
*   **Script:** `scripts/migrate_sqlite_to_pg.py`
    1.  Connect to both the old SQLite DB file and the new Postgres instance.
    2.  Read all rows from SQLite.
    3.  **Transform:**
        *   Generate new UUIDs for every record.
        *   Map old integer IDs to new UUIDs in memory to preserve foreign key relationships (e.g., maintain `Chapter -> Post` links).
        *   Assign all migrated data to a newly created "Legacy/Default Workspace".
    4.  **Load:** Bulk insert the transformed data into Postgres.

### 11.3 Validation & Cutover
1.  **Dry Run:** Run the migration script against a copy of production data.
2.  **Verify:** Check record counts and integrity (e.g., "Do all posts still belong to the correct chapters?").
3.  **Cutover:**
    *   Stop the API.
    *   Run the final migration.
    *   Update config to point to Postgres.
    *   Restart API.

## 12. Subscription Tiers & Pricing Model

To support Individual, Team, and Agency customer segments with differentiated features and limits.

### 12.1 Tier Definitions

| Tier | Target | Price/mo | Users | Workspaces | AI Credits/mo | Features |
|------|--------|----------|-------|------------|---------------|----------|
| **Individual** | Solo creators | $29 | 1 | 1 | 100 | Voice profile, basic analytics, 1 platform |
| **Team** | Small teams | $99 | 5 | 3 | 500 | All Individual + assignment, approval workflow, 3 platforms |
| **Agency** | Agencies | $249 | Unlimited | 10 | 2000 | All Team + white-label, client portal, API access, custom domain |
| **Enterprise** | Large orgs | Custom | Custom | Custom | Custom | All Agency + SSO, dedicated support, SLA |

### 12.2 Schema: Subscription Tiers Table

```sql
CREATE TABLE subscription_tiers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(50) NOT NULL UNIQUE,  -- 'individual', 'team', 'agency', 'enterprise'
    display_name VARCHAR(100) NOT NULL,
    price_monthly_cents INTEGER NOT NULL,  -- 2900, 9900, 24900
    price_yearly_cents INTEGER,            -- Optional annual pricing (e.g., 10 months for 12)
    max_users INTEGER,                     -- NULL = unlimited
    max_workspaces INTEGER NOT NULL,
    max_credits_per_month INTEGER NOT NULL,
    max_platforms INTEGER NOT NULL DEFAULT 1,
    features JSONB NOT NULL DEFAULT '{}',  -- Feature flags
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Feature flags stored in JSONB:
-- {
--   "assignment": true,
--   "approval_workflow": true,
--   "white_label": true,
--   "client_portal": true,
--   "api_access": true,
--   "custom_domain": true,
--   "sso": true,
--   "priority_support": true
-- }
```

### 12.3 Schema: Account Subscriptions Table

```sql
CREATE TABLE account_subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    tier_id UUID NOT NULL REFERENCES subscription_tiers(id),
    stripe_subscription_id VARCHAR(255),
    stripe_customer_id VARCHAR(255),
    status VARCHAR(50) NOT NULL DEFAULT 'active',  -- 'active', 'past_due', 'canceled', 'trialing'
    billing_cycle VARCHAR(20) NOT NULL DEFAULT 'monthly',  -- 'monthly', 'yearly'
    current_period_start TIMESTAMPTZ,
    current_period_end TIMESTAMPTZ,
    trial_ends_at TIMESTAMPTZ,
    canceled_at TIMESTAMPTZ,
    -- Overage settings
    overage_enabled BOOLEAN DEFAULT false,
    overage_rate_cents INTEGER DEFAULT 500,  -- $5 per 100 credits
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_subscriptions_workspace ON account_subscriptions(workspace_id);
CREATE INDEX idx_subscriptions_stripe ON account_subscriptions(stripe_subscription_id);
```

### 12.4 Trial Period Flow

1. New workspace created → 14-day free trial of Team tier
2. Trial banner shown in UI with days remaining
3. At trial end: downgrade to Individual if no payment method
4. Stripe webhook `customer.subscription.trial_will_end` triggers email 3 days before

## 13. Usage Tracking & Enforcement

Backend tracks actual tokens; frontend displays as "AI Credits" for simplicity.

### 13.1 Schema: Usage Tracking Table

```sql
CREATE TABLE usage_tracking (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    period_start DATE NOT NULL,  -- First day of billing period
    period_end DATE NOT NULL,
    -- Display metrics (user-facing)
    credits_used INTEGER DEFAULT 0,
    credits_reserved INTEGER DEFAULT 0,  -- Reserved during execution
    overage_credits INTEGER DEFAULT 0,   -- Credits used beyond limit
    -- Actual token tracking (backend)
    tokens_input BIGINT DEFAULT 0,
    tokens_output BIGINT DEFAULT 0,
    cost_usd DECIMAL(10,4) DEFAULT 0,
    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(workspace_id, period_start)
);

CREATE INDEX idx_usage_workspace_period ON usage_tracking(workspace_id, period_start);
```

### 13.2 Credit Deduction Points

| Action | Credits | Tokens (approx) |
|--------|---------|-----------------|
| Story review | 1 | ~2K |
| Story process | 1 | ~3K |
| Draft (per model) | 1 | ~4K |
| Audit (per model) | 1 | ~3K |
| Synthesis | 2 | ~5K |
| Full workflow (5 writers, 2 auditors) | ~12 | ~30K |

### 13.3 Enforcement Middleware

```python
# api/middleware/usage.py

class UsageEnforcementMiddleware:
    """Check and enforce AI credit limits before workflow execution."""

    async def __call__(self, request: Request, call_next):
        if not request.url.path.startswith("/api/workflow/execute"):
            return await call_next(request)

        workspace = request.state.current_workspace
        subscription = await self.get_subscription(workspace.id)
        usage = await self.get_current_usage(workspace.id)
        limit = subscription.tier.max_credits_per_month

        if usage.credits_used >= limit:
            if subscription.overage_enabled:
                # Allow but will track as overage
                request.state.is_overage = True
            else:
                raise HTTPException(
                    status_code=403,
                    detail={
                        "error": "usage_limit_exceeded",
                        "credits_used": usage.credits_used,
                        "credits_limit": limit,
                        "message": "Monthly AI credit limit reached. Enable overage billing or upgrade your plan."
                    }
                )

        return await call_next(request)
```

### 13.4 Usage Service

```python
# api/services/usage_service.py

class UsageService:
    """Track and manage AI credit usage."""

    def get_current_period(self, workspace_id: UUID) -> UsageTracking:
        """Get or create usage record for current billing period."""
        pass

    def check_and_reserve(self, workspace_id: UUID, credits: int) -> bool:
        """Reserve credits before execution. Returns False if would exceed limit."""
        usage = self.get_current_period(workspace_id)
        limit = self.get_limit(workspace_id)

        if usage.credits_used + usage.credits_reserved + credits > limit:
            subscription = self.get_subscription(workspace_id)
            if not subscription.overage_enabled:
                return False

        usage.credits_reserved += credits
        self.db.save(usage)
        return True

    def confirm_usage(
        self,
        workspace_id: UUID,
        credits: int,
        tokens_input: int,
        tokens_output: int,
        cost_usd: float
    ) -> None:
        """Confirm usage after workflow completion."""
        usage = self.get_current_period(workspace_id)
        limit = self.get_limit(workspace_id)

        usage.credits_reserved -= credits
        usage.credits_used += credits
        usage.tokens_input += tokens_input
        usage.tokens_output += tokens_output
        usage.cost_usd += cost_usd

        # Track overage separately
        if usage.credits_used > limit:
            usage.overage_credits = usage.credits_used - limit

        self.db.save(usage)

    def release_reservation(self, workspace_id: UUID, credits: int) -> None:
        """Release reserved credits if workflow fails/cancels."""
        usage = self.get_current_period(workspace_id)
        usage.credits_reserved = max(0, usage.credits_reserved - credits)
        self.db.save(usage)

    def get_usage_summary(self, workspace_id: UUID) -> UsageSummary:
        """Get usage summary for display in UI."""
        usage = self.get_current_period(workspace_id)
        subscription = self.get_subscription(workspace_id)
        limit = subscription.tier.max_credits_per_month

        return UsageSummary(
            credits_used=usage.credits_used,
            credits_limit=limit,
            credits_remaining=max(0, limit - usage.credits_used),
            overage_credits=usage.overage_credits,
            period_end=usage.period_end,
            percentage_used=round((usage.credits_used / limit) * 100, 1),
            is_warning=(usage.credits_used / limit) >= 0.8,
            is_exceeded=usage.credits_used >= limit
        )
```

### 13.5 UI Components

**Sidebar Usage Widget:**
```
┌─────────────────────────┐
│ AI Credits              │
│ ████████░░░░░ 47/100    │
│ Resets Jan 15           │
└─────────────────────────┘
```

**Warning States:**
- 0-79%: Normal (amber progress bar)
- 80-99%: Warning banner "Running low on AI credits"
- 100%: Block modal with upgrade/overage options

**API Endpoint:**
```
GET /api/usage/summary
Response: {
    "credits_used": 47,
    "credits_limit": 100,
    "credits_remaining": 53,
    "overage_credits": 0,
    "period_end": "2026-02-01",
    "percentage_used": 47.0,
    "is_warning": false,
    "is_exceeded": false
}
```

## 14. Billing Integration (Stripe)

### 14.1 Schema: Billing Events Table

```sql
CREATE TABLE billing_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id),
    stripe_event_id VARCHAR(255) UNIQUE,
    event_type VARCHAR(100) NOT NULL,  -- 'invoice.paid', 'subscription.updated', etc.
    payload JSONB NOT NULL,
    processed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_billing_events_workspace ON billing_events(workspace_id);
CREATE INDEX idx_billing_events_type ON billing_events(event_type);
```

### 14.2 Schema: Invoices Table

```sql
CREATE TABLE invoices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id),
    stripe_invoice_id VARCHAR(255) UNIQUE,
    amount_cents INTEGER NOT NULL,
    currency VARCHAR(10) DEFAULT 'usd',
    status VARCHAR(50) NOT NULL,  -- 'draft', 'open', 'paid', 'void', 'uncollectible'
    invoice_pdf_url TEXT,
    period_start TIMESTAMPTZ,
    period_end TIMESTAMPTZ,
    -- Overage line items
    overage_credits INTEGER DEFAULT 0,
    overage_amount_cents INTEGER DEFAULT 0,
    paid_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### 14.3 Billing Service

```python
# api/services/billing_service.py

class BillingService:
    """Stripe integration for subscription management."""

    def create_checkout_session(
        self, workspace_id: UUID, tier_id: UUID, billing_cycle: str
    ) -> str:
        """Create Stripe checkout session for new/upgrade subscription."""
        pass

    def create_customer_portal_session(self, workspace_id: UUID) -> str:
        """Create Stripe customer portal session for managing subscription."""
        pass

    def handle_webhook(self, payload: bytes, signature: str) -> None:
        """Process Stripe webhook events."""
        # invoice.paid -> record payment, reset usage period
        # subscription.updated -> update tier
        # subscription.deleted -> downgrade to free/block
        pass

    def calculate_overage_invoice(self, workspace_id: UUID) -> int:
        """Calculate overage charges for current period."""
        usage = self.usage_service.get_current_period(workspace_id)
        subscription = self.get_subscription(workspace_id)

        if usage.overage_credits > 0:
            return (usage.overage_credits // 100 + 1) * subscription.overage_rate_cents
        return 0
```

### 14.4 Webhook Events to Handle

| Stripe Event | Action |
|--------------|--------|
| `checkout.session.completed` | Create subscription record |
| `invoice.paid` | Record payment, reset usage if new period |
| `invoice.payment_failed` | Mark subscription past_due, send notification |
| `customer.subscription.updated` | Update tier/status |
| `customer.subscription.deleted` | Cancel subscription |
| `customer.subscription.trial_will_end` | Send trial ending notification |

## 15. Post Assignment & Due Dates

### 15.1 Schema Updates to Posts Table

```sql
ALTER TABLE posts ADD COLUMN IF NOT EXISTS assignee_id UUID REFERENCES users(id);
ALTER TABLE posts ADD COLUMN IF NOT EXISTS due_date DATE;
ALTER TABLE posts ADD COLUMN IF NOT EXISTS priority VARCHAR(20) DEFAULT 'medium';
ALTER TABLE posts ADD COLUMN IF NOT EXISTS estimated_hours DECIMAL(4,1);
ALTER TABLE posts ADD COLUMN IF NOT EXISTS actual_hours DECIMAL(4,1);

CREATE INDEX idx_posts_assignee ON posts(assignee_id);
CREATE INDEX idx_posts_due_date ON posts(due_date);
CREATE INDEX idx_posts_priority ON posts(priority);
```

### 15.2 Schema: Post Assignment History

```sql
CREATE TABLE post_assignment_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    post_id UUID NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
    from_user_id UUID REFERENCES users(id),  -- NULL if first assignment
    to_user_id UUID REFERENCES users(id),    -- NULL if unassigned
    assigned_by_id UUID NOT NULL REFERENCES users(id),
    reason TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_assignment_history_post ON post_assignment_history(post_id);
```

### 15.3 Priority Levels

| Priority | Color | SLA (suggested) |
|----------|-------|-----------------|
| `low` | Gray | No deadline |
| `medium` | Amber | This week |
| `high` | Orange | 48 hours |
| `urgent` | Red | Same day |

### 15.4 Kanban Enhancements

**Filter by assignee:**
```
GET /api/board?workspace_id={uuid}&assignee_id={uuid}
```

**Group by assignee (swimlanes):**
```
GET /api/board?workspace_id={uuid}&group_by=assignee
```

**Workload view:**
```
GET /api/board/workload?workspace_id={uuid}

Response: {
    "members": [
        {
            "user_id": "...",
            "user_name": "Alice",
            "total_posts": 8,
            "posts_due_this_week": 3,
            "posts_overdue": 1,
            "estimated_hours_remaining": 12.5
        }
    ],
    "unassigned_count": 5,
    "overdue_count": 2
}
```

## 16. Approval Workflows

For Team and Agency tiers: configurable multi-stage approval before publishing.

### 16.1 Schema: Approval Stages

```sql
CREATE TABLE approval_stages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,  -- 'Editor Review', 'Client Approval'
    stage_order INTEGER NOT NULL,
    required_role VARCHAR(50),  -- 'editor', 'admin', 'viewer' (client)
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(workspace_id, stage_order)
);
```

### 16.2 Schema: Approval Requests

```sql
CREATE TABLE approval_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    post_id UUID NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
    stage_id UUID NOT NULL REFERENCES approval_stages(id),
    requested_by_id UUID NOT NULL REFERENCES users(id),
    assignee_id UUID REFERENCES users(id),  -- Specific approver, NULL = any with role
    status VARCHAR(50) NOT NULL DEFAULT 'pending',  -- 'pending', 'approved', 'rejected', 'skipped'
    decision_by_id UUID REFERENCES users(id),
    decision_at TIMESTAMPTZ,
    feedback TEXT,
    version INTEGER NOT NULL DEFAULT 1,  -- Post version being reviewed
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(post_id, stage_id, version)
);

CREATE INDEX idx_approval_requests_post ON approval_requests(post_id);
CREATE INDEX idx_approval_requests_assignee ON approval_requests(assignee_id, status);
CREATE INDEX idx_approval_requests_pending ON approval_requests(status) WHERE status = 'pending';
```

### 16.3 Schema: Approval Comments

```sql
CREATE TABLE approval_comments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    approval_request_id UUID NOT NULL REFERENCES approval_requests(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id),
    content TEXT NOT NULL,
    is_internal BOOLEAN DEFAULT false,  -- Internal comments not visible to clients
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_approval_comments_request ON approval_comments(approval_request_id);
```

### 16.4 Default Workflow Stages

| Stage | Order | Role | Description |
|-------|-------|------|-------------|
| Editor Review | 1 | editor | Internal quality check |
| Client Approval | 2 | viewer | External client sign-off (Agency tier) |

### 16.5 Approval Service

```python
# api/services/approval_service.py

class ApprovalService:
    """Multi-stage approval workflow management."""

    def submit_for_approval(self, post_id: UUID, submitted_by_id: UUID) -> ApprovalRequest:
        """Submit post to first approval stage."""
        pass

    def approve(self, request_id: UUID, user_id: UUID, feedback: Optional[str]) -> ApprovalRequest:
        """Approve and advance to next stage or complete."""
        pass

    def reject(self, request_id: UUID, user_id: UUID, feedback: str) -> ApprovalRequest:
        """Reject and return to assignee for revision."""
        pass

    def get_pending_approvals(self, user_id: UUID, workspace_id: UUID) -> list[ApprovalRequest]:
        """Get approvals pending for user (by role or direct assignment)."""
        pass
```

## 17. Notifications System

### 17.1 Schema: Notifications Table

```sql
CREATE TABLE notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    type VARCHAR(50) NOT NULL,
    title VARCHAR(255) NOT NULL,
    body TEXT,
    entity_type VARCHAR(50),  -- 'post', 'approval', 'workspace'
    entity_id UUID,
    action_url TEXT,  -- Deep link to relevant page
    is_read BOOLEAN DEFAULT false,
    read_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_notifications_user ON notifications(user_id, is_read);
CREATE INDEX idx_notifications_created ON notifications(created_at DESC);
```

### 17.2 Notification Types

| Type | Trigger | Title Template |
|------|---------|---------------|
| `post_assigned` | Post assigned to user | "New post assigned: {topic}" |
| `post_due_soon` | 24h before due date | "Post due tomorrow: {topic}" |
| `post_overdue` | Due date passed | "Post overdue: {topic}" |
| `approval_requested` | Post submitted for your approval | "Approval needed: {topic}" |
| `approval_approved` | Your post was approved | "Post approved: {topic}" |
| `approval_rejected` | Your post was rejected | "Post needs revision: {topic}" |
| `comment_added` | Comment on your post | "{user} commented on {topic}" |
| `workspace_invite` | Invited to workspace | "You've been invited to {workspace}" |
| `usage_warning` | 80% of limit reached | "Running low on AI credits" |
| `usage_exceeded` | Limit reached | "AI credit limit reached" |

### 17.3 Schema: Notification Preferences

```sql
CREATE TABLE notification_preferences (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    notification_type VARCHAR(50) NOT NULL,
    in_app BOOLEAN DEFAULT true,
    email BOOLEAN DEFAULT true,
    email_frequency VARCHAR(20) DEFAULT 'immediate',  -- 'immediate', 'daily_digest', 'never'
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, notification_type)
);
```

### 17.4 Schema: Email Queue

```sql
CREATE TABLE email_queue (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    to_email VARCHAR(255) NOT NULL,
    to_name VARCHAR(255),
    subject VARCHAR(500) NOT NULL,
    template VARCHAR(100) NOT NULL,
    template_data JSONB NOT NULL,
    status VARCHAR(50) DEFAULT 'pending',  -- 'pending', 'sent', 'failed'
    sent_at TIMESTAMPTZ,
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_email_queue_status ON email_queue(status) WHERE status = 'pending';
```

### 17.5 Real-time Notifications

Extend existing WebSocket connection to push notifications:

```python
# Broadcast notification to connected user
await ws_manager.send_personal_message(
    user_id=user_id,
    message={
        "type": "notification",
        "data": notification.dict()
    }
)
```

## 18. API Keys, Webhooks & Rate Limiting

For Agency tier: external integrations via API.

### 18.1 Schema: API Keys

```sql
CREATE TABLE api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,  -- 'Zapier Integration', 'CI/CD Pipeline'
    key_prefix VARCHAR(10) NOT NULL,  -- First 10 chars: 'qx_live_ab'
    key_hash VARCHAR(255) NOT NULL,   -- bcrypt hash of full key
    scopes JSONB NOT NULL DEFAULT '[]',  -- ['posts:read', 'posts:write', 'workflow:run']
    rate_limit_per_minute INTEGER DEFAULT 60,
    last_used_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ,
    is_active BOOLEAN DEFAULT true,
    created_by_id UUID NOT NULL REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_api_keys_workspace ON api_keys(workspace_id);
CREATE INDEX idx_api_keys_prefix ON api_keys(key_prefix);
```

### 18.2 Schema: Webhooks

```sql
CREATE TABLE webhooks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    url TEXT NOT NULL,
    events JSONB NOT NULL DEFAULT '[]',  -- ['post.created', 'post.published', 'approval.completed']
    secret VARCHAR(255) NOT NULL,  -- For HMAC signature
    is_active BOOLEAN DEFAULT true,
    failure_count INTEGER DEFAULT 0,
    last_triggered_at TIMESTAMPTZ,
    last_success_at TIMESTAMPTZ,
    last_failure_reason TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_webhooks_workspace ON webhooks(workspace_id);
```

### 18.3 Schema: Webhook Deliveries

```sql
CREATE TABLE webhook_deliveries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    webhook_id UUID NOT NULL REFERENCES webhooks(id) ON DELETE CASCADE,
    event_type VARCHAR(100) NOT NULL,
    payload JSONB NOT NULL,
    response_status INTEGER,
    response_body TEXT,
    response_time_ms INTEGER,
    attempt_count INTEGER DEFAULT 1,
    status VARCHAR(50) DEFAULT 'pending',  -- 'pending', 'success', 'failed'
    next_retry_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_webhook_deliveries_status ON webhook_deliveries(status) WHERE status = 'pending';
```

### 18.4 Webhook Events

| Event | Payload | Trigger |
|-------|---------|---------|
| `post.created` | Post object | New post created |
| `post.status_changed` | Post + old/new status | Status transition |
| `post.published` | Post + publish URL | Post marked published |
| `approval.requested` | Approval request | Submitted for approval |
| `approval.completed` | Approval + decision | Approved or rejected |
| `workflow.started` | Run info | Workflow execution started |
| `workflow.completed` | Run + outputs | Workflow finished |

### 18.5 Rate Limiting by Tier

| Tier | Requests/min | Requests/day |
|------|--------------|--------------|
| Individual | 60 | 1,000 |
| Team | 120 | 5,000 |
| Agency | 300 | 20,000 |
| Enterprise | Custom | Custom |

```sql
CREATE TABLE rate_limit_buckets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    bucket_key VARCHAR(100) NOT NULL,  -- 'minute:2026-01-14T10:30', 'day:2026-01-14'
    request_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(workspace_id, bucket_key)
);
```

### 18.6 Webhook Security

Sign all webhook payloads with HMAC-SHA256:

```
X-Postmagiq-Signature: t=1673449200,v1=5257a869e7ecebeda32affa62cdca3fa51cad7e77a0e56ff536d0ce8e108d8bd
```

Receiving servers should:
1. Extract timestamp and signature from header
2. Verify timestamp is within 5 minutes
3. Compute HMAC-SHA256 of `{timestamp}.{payload}` using webhook secret
4. Compare computed signature with header signature

## 19. White-labeling for Agencies

### 19.1 Schema: White-label Configuration

```sql
CREATE TABLE whitelabel_config (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL UNIQUE REFERENCES workspaces(id) ON DELETE CASCADE,
    -- Branding
    company_name VARCHAR(255),
    logo_url TEXT,
    logo_dark_url TEXT,  -- For dark mode
    favicon_url TEXT,
    -- Colors (hex)
    primary_color VARCHAR(7) DEFAULT '#F59E0B',  -- Amber
    secondary_color VARCHAR(7) DEFAULT '#FBBF24',
    accent_color VARCHAR(7) DEFAULT '#10B981',   -- Emerald
    -- Custom domain
    custom_domain VARCHAR(255) UNIQUE,
    domain_verified BOOLEAN DEFAULT false,
    domain_verification_token VARCHAR(255),
    -- Portal settings
    portal_welcome_text TEXT,
    portal_footer_text TEXT,
    support_email VARCHAR(255),
    -- Status
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_whitelabel_domain ON whitelabel_config(custom_domain) WHERE domain_verified = true;
```

### 19.2 Custom Domain Verification

1. Agency enters desired domain (e.g., `content.agency.com`)
2. System generates verification token
3. Agency adds DNS records:
   - TXT: `_postmatiq-verify.content.agency.com` → `{token}`
   - CNAME: `content.agency.com` → `app.postmatiq.com`
4. Background job verifies DNS records
5. On success: provision SSL certificate via Let's Encrypt/Cloudflare

### 19.3 Client Portal Routes

```
# White-labeled client portal
{custom_domain}/portal/login
{custom_domain}/portal/posts
{custom_domain}/portal/posts/{id}/review
{custom_domain}/portal/posts/{id}/approve
```

### 19.4 Client Portal Access

```sql
-- Add client-specific columns to workspace_users
ALTER TABLE workspace_users ADD COLUMN IF NOT EXISTS is_client BOOLEAN DEFAULT false;
ALTER TABLE workspace_users ADD COLUMN IF NOT EXISTS client_company_name VARCHAR(255);
ALTER TABLE workspace_users ADD COLUMN IF NOT EXISTS portal_access_token VARCHAR(255);
ALTER TABLE workspace_users ADD COLUMN IF NOT EXISTS portal_token_expires_at TIMESTAMPTZ;
```

Clients have limited access:
- View posts assigned to them for approval
- Approve/reject posts
- Add comments
- View their approval history

## 20. Updated Implementation Phases

### Phase 0A: API-Based Agents (Prerequisite)

**Goal:** Add production-ready SDK-based agents alongside existing CLI agents. Required for scalable multi-tenant deployment.

**Current:** Agents use CLI tools (claude, gemini, codex) via subprocess
**Target:** SDK-based agents using official APIs (anthropic, openai, google-generativeai)

**Tasks:**
- [ ] Add anthropic, openai, google-generativeai SDKs to pyproject.toml
- [ ] Create `runner/agents/api_base.py` (APIAgent base class with retry/rate-limit handling)
- [ ] Add AGENT_MODE config to runner/config.py ("cli" or "api")
- [ ] Create `runner/agents/claude_api.py` (ClaudeAPIAgent using anthropic SDK)
- [ ] Create `runner/agents/openai_api.py` (OpenAIAPIAgent using openai SDK)
- [ ] Create `runner/agents/gemini_api.py` (GeminiAPIAgent using google-generativeai SDK)
- [ ] Create `runner/agents/factory.py` (create_agent with mode selection)
- [ ] Update state_machine.py to use factory instead of direct imports
- [ ] Add unit tests for API agents (mocked API calls)

**Architecture:**
```
runner/agents/
├── base.py          # BaseAgent (existing abstract interface)
├── cli_base.py      # CLIAgent (existing subprocess invocation)
├── api_base.py      # NEW: APIAgent (SDK invocation base)
├── claude.py        # ClaudeAgent (CLI - keep for dev)
├── claude_api.py    # NEW: ClaudeAPIAgent (anthropic SDK)
├── openai_api.py    # NEW: OpenAIAPIAgent (openai SDK)
├── gemini_api.py    # NEW: GeminiAPIAgent (google-generativeai SDK)
└── factory.py       # NEW: Agent factory with mode selection
```

### Phase 0B: SQLModel + PostgreSQL Foundation (Prerequisite)

**Goal:** Replace SQLite + raw SQL with PostgreSQL + SQLModel ORM. Required for UUID PKs, proper locking, and multi-tenancy.

**Current:** SQLite + raw SQL + INTEGER PKs + 42 tables
**Target:** PostgreSQL + SQLModel ORM + UUID PKs + Alembic migrations

**Tasks:**
- [ ] Add sqlmodel, psycopg2-binary, alembic to pyproject.toml
- [ ] Add PostgreSQL + PgBouncer services to docker-compose.yml
- [ ] Add DATABASE_URL, USE_SQLMODEL to runner/config.py
- [ ] Create `runner/db/engine.py` (engine + session factory)
- [ ] Initialize Alembic in `runner/db/migrations/`
- [ ] Create `runner/models/base.py` (UUIDModel base class)
- [ ] Create SQLModel definitions for all existing tables:
  - `runner/models/user.py` (User, UserCreate, UserRead)
  - `runner/models/platform.py`
  - `runner/models/content.py` (Goal, Chapter, Post)
  - `runner/models/voice.py` (WritingSample, VoiceProfile)
  - `runner/models/workflow.py` (WorkflowRun, WorkflowOutput, etc.)
  - `runner/models/image.py` (ImagePrompt, ImageScene, etc.)
  - `runner/models/character.py` (Character, Outfit, etc.)
  - `runner/models/analytics.py` (AnalyticsImport, PostMetric, etc.)
- [ ] Create `runner/content/repository.py` (SQLModel query layer)
- [ ] Create `scripts/migrate_sqlite_to_postgres.py` (data migration with UUID mapping)
- [ ] Update ContentService for dual-backend support (USE_SQLMODEL flag)
- [ ] Add Makefile commands (db-up, db-migrate, db-rollback, db-revision)
- [ ] Add SQLModel unit tests

**File Structure:**
```
runner/
├── db/
│   ├── __init__.py
│   ├── engine.py              # Engine creation, session factory
│   ├── session.py             # Session dependency for FastAPI
│   └── migrations/            # Alembic
│       ├── alembic.ini
│       ├── env.py
│       └── versions/
├── models/
│   ├── __init__.py            # Export all models
│   ├── base.py                # UUIDModel base class
│   ├── user.py
│   ├── platform.py
│   ├── content.py
│   ├── voice.py
│   ├── image.py
│   ├── character.py
│   ├── workflow.py
│   ├── analytics.py
│   └── history.py
└── content/
    ├── database.py            # KEEP during migration (existing SQLite)
    └── repository.py          # NEW: SQLModel-based queries
```

**Docker Compose Addition:**
```yaml
postgres:
  image: postgres:16-alpine
  environment:
    POSTGRES_USER: orchestrator
    POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-orchestrator_dev}
    POSTGRES_DB: orchestrator
  ports:
    - "5432:5432"
  volumes:
    - postgres_data:/var/lib/postgresql/data
  healthcheck:
    test: ["CMD-SHELL", "pg_isready -U orchestrator"]
    interval: 5s
    timeout: 5s
    retries: 5

pgbouncer:
  image: edoburu/pgbouncer:1.21.0
  environment:
    DATABASE_URL: postgres://orchestrator:${POSTGRES_PASSWORD}@postgres:5432/orchestrator
    POOL_MODE: transaction
    MAX_CLIENT_CONN: 100
    DEFAULT_POOL_SIZE: 20
  ports:
    - "6432:5432"
  depends_on:
    postgres:
      condition: service_healthy
```

### Phase 1: Database Foundation (Week 1-2)
*From original plan, unchanged*

### Phase 2: Backend Logic (Week 3-4)
*From original plan, unchanged*

### Phase 3: Frontend Integration (Week 5-6)
*From original plan, unchanged*

### Phase 4: Subscription & Usage (Week 7-8)
- [ ] Create subscription_tiers, account_subscriptions tables
- [ ] Create usage_tracking table
- [ ] Implement UsageService with credit tracking
- [ ] Add enforcement middleware for workflow execution
- [ ] Create usage display component in sidebar
- [ ] Add upgrade prompts when limit reached

### Phase 5: Billing Integration (Week 9-10)
- [ ] Stripe SDK integration
- [ ] Checkout session creation
- [ ] Customer portal for subscription management
- [ ] Webhook handler for Stripe events
- [ ] Trial period logic
- [ ] Invoice history page

### Phase 6: Assignment & Approvals (Week 11-12)
- [ ] Add assignment columns to posts
- [ ] Create assignment history table
- [ ] Create approval_stages, approval_requests tables
- [ ] Implement ApprovalService
- [ ] Update Kanban with assignee filters
- [ ] Workload visualization

### Phase 7: Notifications (Week 13)
- [ ] Create notifications tables
- [ ] Implement NotificationService
- [ ] Email queue with SendGrid/Resend
- [ ] Real-time notifications via WebSocket
- [ ] Notification preferences UI

### Phase 8: API & Webhooks (Week 14)
- [ ] API key generation and auth
- [ ] Rate limiting middleware
- [ ] Webhook configuration UI
- [ ] Webhook delivery system with retries
- [ ] API documentation

### Phase 9: White-labeling (Week 15-16)
- [ ] Custom domain verification
- [ ] Theme customization UI
- [ ] Client portal routes
- [ ] SSL certificate provisioning

### Phase 10: Polish & Launch (Week 17-18)
- [ ] Load testing
- [ ] Security audit
- [ ] Documentation
- [ ] Monitoring and alerting
- [ ] Gradual rollout

## 21. New Tables Summary

| # | Table | Purpose |
|---|-------|---------|
| 1 | `subscription_tiers` | Tier definitions |
| 2 | `account_subscriptions` | Workspace subscriptions |
| 3 | `usage_tracking` | Per-period usage metrics |
| 4 | `billing_events` | Stripe webhook events |
| 5 | `invoices` | Invoice records |
| 6 | `post_assignment_history` | Assignment audit trail |
| 7 | `approval_stages` | Workflow stage config |
| 8 | `approval_requests` | Pending approvals |
| 9 | `approval_comments` | Review feedback |
| 10 | `notifications` | In-app notifications |
| 11 | `notification_preferences` | User preferences |
| 12 | `email_queue` | Outbound email queue |
| 13 | `api_keys` | API authentication |
| 14 | `webhooks` | Webhook configs |
| 15 | `webhook_deliveries` | Delivery attempts |
| 16 | `rate_limit_buckets` | Rate limiting |
| 17 | `whitelabel_config` | Branding settings |
| 18 | `system_templates` | Global/workspace templates |
| 19 | `active_sessions` | Session tracking for revocation |
| 20 | `assets` | Uploaded file registry (S3) |
| 21 | `audit_logs` | Security and admin actions |
| 22 | `accounts` | Agency/team billing entity |
| 23 | `credit_reservations` | Idempotent credit tracking |

## 22. Modified Tables Summary

| Table | New Columns |
|-------|-------------|
| `posts` | `assignee_id`, `due_date`, `priority`, `estimated_hours`, `actual_hours` |
| `workspaces` | `account_id`, `telemetry_enabled` |
| `users` | `telemetry_consent` |
| `account_subscriptions` | `account_id` (moved from workspace_id) |
| `whitelabel_config` | `email_domain`, `email_from_name`, `email_reply_to`, `email_domain_verified`, `dkim_selector`, `dkim_public_key` |
| `telemetry_events` | `is_anonymized` |

**Note:** `workspace_users` renamed to `workspace_memberships` with surrogate UUID primary key. See Section 33.

## 23. Global & Shared Resources

### 23.1 Resource Isolation Model

| Resource Type | Isolation | Example |
|--------------|-----------|---------|
| **Tenant Data** | workspace_id required | Posts, strategies, runs |
| **System Templates** | workspace_id = NULL | Default prompts, persona templates |
| **Platform Config** | No workspace_id column | Subscription tiers, feature flags |

### 23.2 Schema: System Templates

```sql
CREATE TABLE system_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID REFERENCES workspaces(id),  -- NULL = system-wide
    template_type VARCHAR(50) NOT NULL,  -- 'persona', 'prompt', 'workflow'
    name VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    is_default BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- System templates have NULL workspace_id
-- Workspace-specific overrides have workspace_id set
CREATE INDEX idx_templates_workspace ON system_templates(workspace_id);
CREATE INDEX idx_templates_type ON system_templates(template_type, is_default);
```

### 23.3 Query Pattern for Shared Resources

```python
def get_template(workspace_id: UUID, template_type: str) -> Template:
    """Get workspace-specific template, falling back to system default."""
    # First try workspace-specific
    template = db.query(SystemTemplate).filter(
        SystemTemplate.workspace_id == workspace_id,
        SystemTemplate.template_type == template_type
    ).first()

    # Fall back to system default
    if not template:
        template = db.query(SystemTemplate).filter(
            SystemTemplate.workspace_id.is_(None),
            SystemTemplate.template_type == template_type,
            SystemTemplate.is_default == True
        ).first()

    return template
```

### 23.4 Telemetry Query Scoping

**CRITICAL:** All telemetry queries MUST be scoped to workspace_id to prevent cross-tenant data leakage.

```python
# WRONG - Leaks aggregate data across tenants
def get_popular_configs():
    return db.query(func.count()).group_by(TelemetryEvent.payload['setting'])

# CORRECT - Scoped to workspace
def get_popular_configs(workspace_id: UUID):
    return db.query(func.count()).filter(
        TelemetryEvent.workspace_id == workspace_id
    ).group_by(TelemetryEvent.payload['setting'])
```

## 24. Session Management & Token Revocation

### 24.1 Problem: JWT Expiry Gap

JWTs are stateless. If a user is removed from a workspace, their token remains valid until expiry (potentially 1 hour). This creates a security gap.

### 24.2 Solution: Session Validation Layer

```sql
CREATE TABLE active_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    session_token VARCHAR(255) NOT NULL UNIQUE,  -- JWT jti claim
    device_info JSONB,  -- User-agent, IP, etc.
    last_activity_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL,
    revoked_at TIMESTAMPTZ,
    revoked_reason VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_sessions_user ON active_sessions(user_id);
CREATE INDEX idx_sessions_token ON active_sessions(session_token);
CREATE INDEX idx_sessions_expires ON active_sessions(expires_at) WHERE revoked_at IS NULL;
```

### 24.3 Session Check Middleware

```python
# api/middleware/session.py

class SessionValidationMiddleware:
    """Validate JWT session has not been revoked."""

    async def __call__(self, request: Request, call_next):
        if not request.state.user:
            return await call_next(request)

        token_jti = request.state.jwt_claims.get('jti')
        if not token_jti:
            return await call_next(request)

        # Check if session is revoked (cache this for performance)
        session = await self.get_session(token_jti)
        if not session or session.revoked_at:
            raise HTTPException(
                status_code=401,
                detail="Session revoked. Please log in again."
            )

        # Update last activity
        await self.touch_session(token_jti)
        return await call_next(request)

    @lru_cache(maxsize=10000, ttl=60)  # Cache for 60 seconds
    async def get_session(self, token_jti: str) -> ActiveSession:
        return await db.query(ActiveSession).filter(
            ActiveSession.session_token == token_jti
        ).first()
```

### 24.4 Revocation Triggers

| Trigger | Action |
|---------|--------|
| User removed from workspace | Revoke sessions where user has no remaining workspaces |
| Password changed | Revoke all sessions except current |
| Admin force logout | Revoke specific session |
| Suspicious activity | Revoke all sessions for user |

```python
async def revoke_user_sessions(user_id: UUID, reason: str, exclude_jti: str = None):
    """Revoke all sessions for a user, optionally excluding current."""
    query = update(ActiveSession).where(
        ActiveSession.user_id == user_id,
        ActiveSession.revoked_at.is_(None)
    ).values(
        revoked_at=func.now(),
        revoked_reason=reason
    )

    if exclude_jti:
        query = query.where(ActiveSession.session_token != exclude_jti)

    await db.execute(query)
    # Invalidate cache
    session_cache.invalidate_user(user_id)
```

## 25. Enhanced Invite Flow

### 25.1 Schema Updates to workspace_users

```sql
ALTER TABLE workspace_users ADD COLUMN IF NOT EXISTS invite_status VARCHAR(20) DEFAULT 'active';
ALTER TABLE workspace_users ADD COLUMN IF NOT EXISTS invite_token VARCHAR(255) UNIQUE;
ALTER TABLE workspace_users ADD COLUMN IF NOT EXISTS invite_expires_at TIMESTAMPTZ;
ALTER TABLE workspace_users ADD COLUMN IF NOT EXISTS invited_by_id UUID REFERENCES users(id);
ALTER TABLE workspace_users ADD COLUMN IF NOT EXISTS invited_at TIMESTAMPTZ;
ALTER TABLE workspace_users ADD COLUMN IF NOT EXISTS accepted_at TIMESTAMPTZ;

CREATE INDEX idx_workspace_users_invite ON workspace_users(invite_token) WHERE invite_status = 'pending';
```

### 25.2 Invite Status Flow

```
┌─────────┐   Accept   ┌─────────┐
│ pending │ ─────────▶ │ active  │
└─────────┘            └─────────┘
     │                      │
     │ Expire/Revoke        │ Remove
     ▼                      ▼
┌─────────┐            ┌─────────┐
│ expired │            │ removed │
└─────────┘            └─────────┘
```

| Status | Description |
|--------|-------------|
| `pending` | Invite sent, awaiting acceptance |
| `active` | User accepted invite, fully active |
| `expired` | Invite link expired (7 days default) |
| `removed` | User removed from workspace |

### 25.3 Invite Service

```python
# api/services/invite_service.py

class InviteService:
    INVITE_EXPIRY_DAYS = 7

    async def create_invite(
        self,
        workspace_id: UUID,
        email: str,
        role: str,
        invited_by_id: UUID
    ) -> WorkspaceUser:
        """Create or resend invite to email."""
        # Check if user exists
        user = await self.user_service.get_by_email(email)

        # Check if already member
        existing = await self.get_membership(workspace_id, user.id if user else None, email)
        if existing and existing.invite_status == 'active':
            raise HTTPException(400, "User is already a member")

        invite_token = secrets.token_urlsafe(32)
        expires_at = datetime.utcnow() + timedelta(days=self.INVITE_EXPIRY_DAYS)

        membership = WorkspaceUser(
            workspace_id=workspace_id,
            user_id=user.id if user else None,
            email=email,  # Store email for users not yet registered
            role=role,
            invite_status='pending',
            invite_token=invite_token,
            invite_expires_at=expires_at,
            invited_by_id=invited_by_id,
            invited_at=datetime.utcnow()
        )

        await db.save(membership)
        await self.send_invite_email(email, workspace_id, invite_token)
        return membership

    async def accept_invite(self, token: str, user_id: UUID) -> WorkspaceUser:
        """Accept invite and activate membership."""
        membership = await db.query(WorkspaceUser).filter(
            WorkspaceUser.invite_token == token
        ).first()

        if not membership:
            raise HTTPException(404, "Invite not found")
        if membership.invite_status != 'pending':
            raise HTTPException(400, f"Invite is {membership.invite_status}")
        if membership.invite_expires_at < datetime.utcnow():
            membership.invite_status = 'expired'
            await db.save(membership)
            raise HTTPException(400, "Invite has expired")

        membership.user_id = user_id
        membership.invite_status = 'active'
        membership.accepted_at = datetime.utcnow()
        membership.invite_token = None  # Clear token after use
        await db.save(membership)
        return membership
```

## 26. Workspace Seed Data

### 26.1 Strategy: Template-Based Seeding

When a new workspace is created, optionally seed with example content to help users understand the platform.

### 26.2 Seed Configuration

```python
# api/services/workspace_service.py

SEED_TEMPLATES = {
    'empty': {
        'description': 'Start with a blank workspace',
        'goals': [],
        'chapters': [],
        'posts': []
    },
    'tutorial': {
        'description': 'Includes example strategy and tutorial posts',
        'goals': [{
            'signature_thesis': 'Example: Share your expertise to build authority',
            'positioning': 'Thought Leader',
            'target_audience': 'Your target audience'
        }],
        'chapters': [{
            'title': 'Getting Started',
            'description': 'Your first chapter of content'
        }],
        'posts': [{
            'topic': 'Welcome to Postmagiq - Your First Post',
            'status': 'not_started',
            'is_tutorial': True
        }]
    },
    'agency_demo': {
        'description': 'Demo content for agency presentations',
        'goals': [/* ... */],
        'chapters': [/* ... */],
        'posts': [/* ... */]
    }
}

async def create_workspace(
    name: str,
    owner_id: UUID,
    seed_template: str = 'empty'
) -> Workspace:
    """Create workspace with optional seed data."""
    workspace = Workspace(name=name, owner_id=owner_id)
    await db.save(workspace)

    # Add owner as admin
    membership = WorkspaceUser(
        workspace_id=workspace.id,
        user_id=owner_id,
        role='owner',
        invite_status='active'
    )
    await db.save(membership)

    # Apply seed template
    if seed_template != 'empty':
        await self.apply_seed_template(workspace.id, seed_template)

    return workspace
```

### 26.3 Onboarding Flow

```
Register → Create Workspace → Select Template → [Tutorial / Empty / Skip]
                                   │
                                   ▼
                           Seed Data Applied
                                   │
                                   ▼
                           Dashboard with Guide
```

## 27. Operations: Connection Pooling & Backups

### 27.1 Connection Pooling with PgBouncer

**Problem:** Each API request opening a new DB connection causes "too many clients" errors under load.

**Solution:** Use PgBouncer as a connection pooler in front of PostgreSQL.

```yaml
# docker-compose.yml

services:
  pgbouncer:
    image: edoburu/pgbouncer:1.21.0
    environment:
      DATABASE_URL: postgres://postgres:password@postgres:5432/postmatiq
      POOL_MODE: transaction
      MAX_CLIENT_CONN: 1000
      DEFAULT_POOL_SIZE: 20
      MIN_POOL_SIZE: 5
      RESERVE_POOL_SIZE: 5
    ports:
      - "6432:6432"
    depends_on:
      - postgres

  api:
    environment:
      # Connect to PgBouncer, not directly to Postgres
      DATABASE_URL: postgres://postgres:password@pgbouncer:6432/postmatiq
```

**SQLAlchemy Configuration:**

```python
# runner/content/database.py

engine = create_async_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,      # Verify connections before use
    pool_size=5,             # Matches PgBouncer DEFAULT_POOL_SIZE
    max_overflow=10,         # Allow burst capacity
    pool_recycle=300,        # Recycle connections every 5 min
)
```

### 27.2 Backup Strategy

#### Automated Daily Backups

```yaml
# docker-compose.yml

services:
  backup:
    image: prodrigestivill/postgres-backup-local
    environment:
      POSTGRES_HOST: postgres
      POSTGRES_DB: postmatiq
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: ${DB_PASSWORD}
      SCHEDULE: "@daily"
      BACKUP_KEEP_DAYS: 7
      BACKUP_KEEP_WEEKS: 4
      BACKUP_KEEP_MONTHS: 6
    volumes:
      - ./backups:/backups
    depends_on:
      - postgres
```

#### WAL Archiving for Point-in-Time Recovery

```sql
-- postgresql.conf
wal_level = replica
archive_mode = on
archive_command = 'cp %p /backups/wal/%f'
```

#### Backup Verification

```bash
# Weekly backup verification cron job
#!/bin/bash
BACKUP_FILE=$(ls -t /backups/*.sql.gz | head -1)
pg_restore --list "$BACKUP_FILE" > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "Backup verification passed: $BACKUP_FILE"
else
    echo "BACKUP VERIFICATION FAILED" | mail -s "Postmagiq Backup Alert" ops@postmatiq.com
fi
```

### 27.3 Monitoring

```yaml
# docker-compose.yml

services:
  postgres-exporter:
    image: prometheuscommunity/postgres-exporter
    environment:
      DATA_SOURCE_NAME: postgres://postgres:password@postgres:5432/postmatiq?sslmode=disable
    ports:
      - "9187:9187"
```

Key metrics to monitor:
- `pg_stat_activity_count` - Active connections
- `pg_stat_database_tup_fetched` - Rows read
- `pg_stat_database_deadlocks` - Deadlock count
- `pgbouncer_pools_cl_active` - Active client connections

## 28. Frontend URL Structure

### 28.1 Workspace-Scoped Routes

**Problem:** Without workspace_id in URL, refreshing loses context and deep-linking fails.

**Solution:** Mandate `/w/{workspace_id}/...` URL structure.

```typescript
// gui/src/App.tsx

const routes = [
  // Public routes (no workspace)
  { path: '/auth/login', element: <Login /> },
  { path: '/auth/register', element: <Register /> },
  { path: '/auth/invite', element: <AcceptInvite /> },

  // Workspace-scoped routes
  { path: '/w/:workspaceId', element: <WorkspaceLayout />, children: [
    { path: 'dashboard', element: <Dashboard /> },
    { path: 'board', element: <Board /> },
    { path: 'strategy', element: <Strategy /> },
    { path: 'posts/:postId', element: <PostDetail /> },
    { path: 'posts/:postId/edit', element: <Editor /> },
    { path: 'workflow/:runId', element: <LiveWorkflow /> },
    { path: 'settings', element: <Settings /> },
    { path: 'settings/team', element: <TeamSettings /> },
    { path: 'settings/billing', element: <BillingSettings /> },
  ]},

  // Redirect root to default workspace
  { path: '/', element: <WorkspaceRedirect /> },
]
```

### 28.2 Workspace Context Provider

```typescript
// gui/src/contexts/WorkspaceContext.tsx

export function WorkspaceLayout() {
  const { workspaceId } = useParams<{ workspaceId: string }>()
  const { data: workspace, isLoading, error } = useQuery({
    queryKey: ['workspace', workspaceId],
    queryFn: () => fetchWorkspace(workspaceId!),
  })

  if (isLoading) return <WorkspaceSkeleton />
  if (error || !workspace) return <Navigate to="/auth/login" />

  return (
    <WorkspaceContext.Provider value={workspace}>
      <MainLayout>
        <Outlet />
      </MainLayout>
    </WorkspaceContext.Provider>
  )
}
```

### 28.3 URL Generation Helpers

```typescript
// gui/src/utils/routes.ts

export function workspaceUrl(workspaceId: string, path: string): string {
  return `/w/${workspaceId}${path.startsWith('/') ? path : '/' + path}`
}

// Usage in components
const { workspaceId } = useWorkspace()
<Link to={workspaceUrl(workspaceId, '/board')}>Board</Link>
<Link to={workspaceUrl(workspaceId, `/posts/${post.id}`)}>View Post</Link>
```

### 28.4 Workspace Switcher Updates

```typescript
// gui/src/components/layout/WorkspaceSwitcher.tsx

function WorkspaceSwitcher() {
  const navigate = useNavigate()
  const { workspaceId } = useParams()
  const location = useLocation()

  const handleSwitch = (newWorkspaceId: string) => {
    // Preserve current page path when switching
    const currentPath = location.pathname.replace(`/w/${workspaceId}`, '')
    navigate(`/w/${newWorkspaceId}${currentPath}`)
  }

  // ...
}
```

### 28.5 Deep Link Examples

| Action | URL |
|--------|-----|
| Dashboard | `/w/abc123/dashboard` |
| Specific post | `/w/abc123/posts/def456` |
| Edit post | `/w/abc123/posts/def456/edit` |
| Live workflow | `/w/abc123/workflow/run789` |
| Team settings | `/w/abc123/settings/team` |
| Kanban board | `/w/abc123/board` |

## 29. Object Storage (Asset Hosting)

### 29.1 Storage Architecture

All user-uploaded assets (logos, images, attachments) are stored in S3-compatible object storage.

```
s3://postmatiq-assets/
├── system/                          # Platform assets (NULL workspace)
│   ├── templates/
│   └── defaults/
├── workspaces/
│   └── {workspace_uuid}/
│       ├── branding/
│       │   ├── logo.png
│       │   ├── logo-dark.png
│       │   └── favicon.ico
│       ├── posts/
│       │   └── {post_uuid}/
│       │       └── images/
│       └── attachments/
└── users/
    └── {user_uuid}/
        └── avatar.png
```

### 29.2 Schema: Asset Registry

```sql
CREATE TABLE assets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE,  -- NULL = system
    user_id UUID REFERENCES users(id),  -- Uploader
    asset_type VARCHAR(50) NOT NULL,  -- 'logo', 'post_image', 'avatar', 'attachment'
    filename VARCHAR(255) NOT NULL,
    mime_type VARCHAR(100) NOT NULL,
    size_bytes BIGINT NOT NULL,
    s3_bucket VARCHAR(100) NOT NULL,
    s3_key VARCHAR(500) NOT NULL UNIQUE,
    cdn_url TEXT,  -- CloudFront/CDN URL if enabled
    checksum_sha256 VARCHAR(64),
    is_public BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_assets_workspace ON assets(workspace_id);
CREATE INDEX idx_assets_type ON assets(asset_type);
```

### 29.3 Upload Service

```python
# api/services/asset_service.py

class AssetService:
    ALLOWED_TYPES = {
        'logo': ['image/png', 'image/jpeg', 'image/svg+xml'],
        'post_image': ['image/png', 'image/jpeg', 'image/gif', 'image/webp'],
        'avatar': ['image/png', 'image/jpeg'],
    }
    MAX_SIZES = {
        'logo': 5 * 1024 * 1024,      # 5MB
        'post_image': 10 * 1024 * 1024,  # 10MB
        'avatar': 2 * 1024 * 1024,     # 2MB
    }

    async def upload(
        self,
        workspace_id: UUID,
        user_id: UUID,
        asset_type: str,
        file: UploadFile
    ) -> Asset:
        # Validate type and size
        if file.content_type not in self.ALLOWED_TYPES.get(asset_type, []):
            raise HTTPException(400, f"Invalid file type for {asset_type}")
        if file.size > self.MAX_SIZES.get(asset_type, 0):
            raise HTTPException(400, "File too large")

        # Generate S3 key
        s3_key = f"workspaces/{workspace_id}/{asset_type}s/{uuid4()}/{file.filename}"

        # Upload to S3
        await self.s3.upload_fileobj(
            file.file,
            self.bucket,
            s3_key,
            ExtraArgs={'ContentType': file.content_type}
        )

        # Register in database
        asset = Asset(
            workspace_id=workspace_id,
            user_id=user_id,
            asset_type=asset_type,
            filename=file.filename,
            mime_type=file.content_type,
            size_bytes=file.size,
            s3_bucket=self.bucket,
            s3_key=s3_key,
            cdn_url=f"{self.cdn_base}/{s3_key}"
        )
        await db.save(asset)
        return asset

    def generate_presigned_url(self, asset: Asset, expires_in: int = 3600) -> str:
        """Generate presigned URL for private assets."""
        return self.s3.generate_presigned_url(
            'get_object',
            Params={'Bucket': asset.s3_bucket, 'Key': asset.s3_key},
            ExpiresIn=expires_in
        )
```

### 29.4 Infrastructure Config

```yaml
# docker-compose.yml (dev)
services:
  minio:
    image: minio/minio
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: postmatiq
      MINIO_ROOT_PASSWORD: ${MINIO_PASSWORD}
    volumes:
      - minio_data:/data
    ports:
      - "9000:9000"
      - "9001:9001"

# Production: AWS S3 + CloudFront
# S3_BUCKET=postmatiq-assets-prod
# CDN_BASE=https://assets.postmatiq.com
```

## 30. System Logging & Observability

### 30.1 Log Categories

| Category | Purpose | Destination |
|----------|---------|-------------|
| **User Telemetry** | Product analytics, feature usage | `telemetry_events` table |
| **Application Logs** | Errors, warnings, debug info | stdout → aggregator |
| **Audit Logs** | Security events, admin actions | `audit_logs` table |
| **Request Logs** | API access patterns | stdout → aggregator |

### 30.2 Structured Logging Format

```python
# api/logging.py

import structlog

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ]
)

logger = structlog.get_logger()

# Usage
logger.info(
    "workflow_started",
    workspace_id=str(workspace_id),
    run_id=str(run_id),
    agent_count=5
)

# Output (JSON to stdout)
{
    "event": "workflow_started",
    "level": "info",
    "timestamp": "2026-01-14T10:30:00Z",
    "workspace_id": "abc-123",
    "run_id": "def-456",
    "agent_count": 5
}
```

### 30.3 Schema: Audit Logs

```sql
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    -- Actor
    actor_type VARCHAR(20) NOT NULL,  -- 'user', 'system', 'admin', 'api_key'
    actor_id UUID,
    actor_email VARCHAR(255),
    -- Target
    workspace_id UUID REFERENCES workspaces(id),
    resource_type VARCHAR(50),  -- 'user', 'workspace', 'post', 'subscription'
    resource_id UUID,
    -- Action
    action VARCHAR(50) NOT NULL,  -- 'create', 'update', 'delete', 'impersonate', 'export'
    action_detail JSONB,  -- {old_value: x, new_value: y}
    -- Context
    ip_address INET,
    user_agent TEXT,
    request_id UUID
);

CREATE INDEX idx_audit_workspace ON audit_logs(workspace_id, timestamp DESC);
CREATE INDEX idx_audit_actor ON audit_logs(actor_id, timestamp DESC);
CREATE INDEX idx_audit_action ON audit_logs(action, timestamp DESC);
```

### 30.4 Audit Events

| Action | When | Detail |
|--------|------|--------|
| `user.invited` | Member invited | `{email, role}` |
| `user.removed` | Member removed | `{user_id, role}` |
| `user.role_changed` | Role updated | `{old_role, new_role}` |
| `admin.impersonate_start` | Super-admin impersonates | `{target_user_id}` |
| `admin.impersonate_end` | Impersonation ended | `{duration_seconds}` |
| `subscription.upgraded` | Tier changed | `{old_tier, new_tier}` |
| `subscription.canceled` | Subscription canceled | `{reason}` |
| `workspace.settings_changed` | Config updated | `{changed_fields}` |
| `data.exported` | Bulk data export | `{export_type, record_count}` |
| `api_key.created` | API key generated | `{key_prefix, scopes}` |
| `api_key.revoked` | API key disabled | `{key_prefix, reason}` |

### 30.5 Super-Admin Impersonation (with Audit)

```python
# api/services/admin_service.py

class AdminService:
    async def start_impersonation(
        self,
        admin_user_id: UUID,
        target_user_id: UUID,
        reason: str
    ) -> ImpersonationSession:
        # Verify admin is super-admin
        admin = await self.user_service.get(admin_user_id)
        if not admin.is_superuser:
            raise HTTPException(403, "Not authorized")

        # Create impersonation session
        session = ImpersonationSession(
            admin_id=admin_user_id,
            target_user_id=target_user_id,
            reason=reason,
            started_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(hours=1)
        )
        await db.save(session)

        # MANDATORY: Audit log
        await self.audit_service.log(
            actor_type='admin',
            actor_id=admin_user_id,
            action='admin.impersonate_start',
            resource_type='user',
            resource_id=target_user_id,
            action_detail={'reason': reason}
        )

        # OPTIONAL: Notify target user
        await self.notification_service.create(
            user_id=target_user_id,
            type='admin_access',
            title='Admin accessed your account',
            body=f'A Postmagiq admin accessed your account for: {reason}'
        )

        return session
```

### 30.6 Log Aggregation (Production)

```yaml
# docker-compose.prod.yml

services:
  api:
    logging:
      driver: "awslogs"
      options:
        awslogs-region: "us-east-1"
        awslogs-group: "postmatiq-api"
        awslogs-stream-prefix: "api"

# Alternative: Datadog
  datadog-agent:
    image: datadog/agent:latest
    environment:
      DD_API_KEY: ${DD_API_KEY}
      DD_LOGS_ENABLED: true
      DD_LOGS_CONFIG_CONTAINER_COLLECT_ALL: true
```

## 31. Email White-labeling

### 31.1 Default Behavior

All transactional emails sent from `noreply@postmatiq.com` with Postmagiq branding.

### 31.2 Agency Tier: Custom Email Domain

Agencies can configure custom sending domain for client-facing emails.

```sql
ALTER TABLE whitelabel_config ADD COLUMN IF NOT EXISTS email_domain VARCHAR(255);
ALTER TABLE whitelabel_config ADD COLUMN IF NOT EXISTS email_from_name VARCHAR(255);
ALTER TABLE whitelabel_config ADD COLUMN IF NOT EXISTS email_reply_to VARCHAR(255);
ALTER TABLE whitelabel_config ADD COLUMN IF NOT EXISTS email_domain_verified BOOLEAN DEFAULT false;
ALTER TABLE whitelabel_config ADD COLUMN IF NOT EXISTS dkim_selector VARCHAR(50);
ALTER TABLE whitelabel_config ADD COLUMN IF NOT EXISTS dkim_public_key TEXT;
```

### 31.3 Email Domain Verification

1. Agency enters domain (e.g., `mail.agency.com`)
2. System generates DKIM key pair
3. Agency adds DNS records:
   ```
   TXT: postmatiq._domainkey.mail.agency.com → "v=DKIM1; k=rsa; p={public_key}"
   TXT: mail.agency.com → "v=spf1 include:spf.postmatiq.com ~all"
   ```
4. Background job verifies DNS
5. On success: emails sent via agency domain

### 31.4 Email Sending Logic

```python
# api/services/email_service.py

class EmailService:
    async def send(
        self,
        workspace_id: UUID,
        to_email: str,
        template: str,
        data: dict
    ):
        whitelabel = await self.get_whitelabel(workspace_id)

        if whitelabel and whitelabel.email_domain_verified:
            # Agency custom domain
            from_email = f"{whitelabel.email_from_name} <noreply@{whitelabel.email_domain}>"
            reply_to = whitelabel.email_reply_to
            branding = whitelabel  # Custom logo, colors
        else:
            # Default Postmagiq
            from_email = "Postmagiq <noreply@postmatiq.com>"
            reply_to = "support@postmatiq.com"
            branding = None  # Default branding

        await self.provider.send(
            from_email=from_email,
            reply_to=reply_to,
            to_email=to_email,
            template=template,
            data={**data, 'branding': branding}
        )
```

### 31.5 Scope Clarification

| Feature | Individual | Team | Agency |
|---------|-----------|------|--------|
| Emails from Postmagiq domain | Yes | Yes | Yes (default) |
| Custom email domain | No | No | Yes (verified) |
| Custom email branding | No | No | Yes |
| Remove "Powered by Postmagiq" | No | No | Yes |

## 32. Unified Migration Strategy

### 32.1 Problem: Conflicting Migration Paths

The original plan described two migrations:
1. Section 2.2.5: In-place UUID conversion
2. Section 11: SQLite → Postgres copy with UUID regeneration

These conflict and could corrupt data. This section replaces both with a unified strategy.

### 32.2 Single Migration Path

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   SQLite    │ ──▶ │  Transform  │ ──▶ │  Postgres   │
│  (INTEGER)  │     │   Script    │     │   (UUID)    │
└─────────────┘     └─────────────┘     └─────────────┘
```

**There is ONE migration, not two.**

### 32.3 Migration Script

```python
# scripts/migrate_to_postgres.py

"""
Unified migration: SQLite (INTEGER PKs) → Postgres (UUID PKs)

This script:
1. Reads all data from SQLite
2. Generates UUIDs for all records
3. Maintains relationship mappings (old INT → new UUID)
4. Creates default workspace for existing data
5. Writes to Postgres with new UUIDs
6. Verifies data integrity
"""

import sqlite3
import asyncpg
from uuid import uuid4

class Migration:
    def __init__(self, sqlite_path: str, postgres_url: str):
        self.id_map: dict[str, dict[int, UUID]] = {}  # table -> old_id -> new_uuid

    async def run(self):
        # Phase 1: Read SQLite, generate UUID mappings
        await self.read_and_map_ids()

        # Phase 2: Create Postgres schema (Alembic)
        await self.create_schema()

        # Phase 3: Create default workspace
        default_workspace_id = await self.create_default_workspace()

        # Phase 4: Migrate data with UUID substitution
        await self.migrate_data(default_workspace_id)

        # Phase 5: Verify integrity
        await self.verify()

    async def read_and_map_ids(self):
        """Generate UUIDs for every existing record."""
        tables = ['goals', 'chapters', 'posts', 'runs', 'post_analytics']

        for table in tables:
            self.id_map[table] = {}
            rows = self.sqlite.execute(f"SELECT id FROM {table}").fetchall()
            for (old_id,) in rows:
                self.id_map[table][old_id] = uuid4()

    async def migrate_data(self, workspace_id: UUID):
        """Copy data with UUID substitution."""
        # Example: posts table
        posts = self.sqlite.execute("SELECT * FROM posts").fetchall()

        for post in posts:
            new_id = self.id_map['posts'][post['id']]
            new_chapter_id = self.id_map['chapters'][post['chapter_id']]

            await self.postgres.execute("""
                INSERT INTO posts (id, workspace_id, chapter_id, topic, status, ...)
                VALUES ($1, $2, $3, $4, $5, ...)
            """, new_id, workspace_id, new_chapter_id, post['topic'], post['status'])

    async def verify(self):
        """Verify record counts and relationships."""
        for table in self.id_map:
            sqlite_count = self.sqlite.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            pg_count = await self.postgres.fetchval(f"SELECT COUNT(*) FROM {table}")
            assert sqlite_count == pg_count, f"Count mismatch in {table}"

        # Verify FK relationships
        orphan_posts = await self.postgres.fetchval("""
            SELECT COUNT(*) FROM posts p
            WHERE NOT EXISTS (SELECT 1 FROM chapters c WHERE c.id = p.chapter_id)
        """)
        assert orphan_posts == 0, "Orphaned posts found"
```

### 32.4 Downtime & Rollback Strategy

| Phase | Duration | Rollback |
|-------|----------|----------|
| Pre-migration (schema) | 0 | N/A |
| Stop API | < 1 min | Restart API |
| Run migration script | 5-30 min | Restore SQLite, restart |
| Verify integrity | 2-5 min | Restore SQLite, restart |
| Update config → Postgres | < 1 min | Revert config, restart |
| Start API | < 1 min | N/A |

**Total downtime:** 10-40 minutes depending on data size.

### 32.5 Rollback Procedure

```bash
#!/bin/bash
# scripts/rollback_migration.sh

# 1. Stop API
docker-compose stop api

# 2. Revert database config
cp .env.sqlite.backup .env

# 3. Verify SQLite still intact
sqlite3 data/postmatiq.db "SELECT COUNT(*) FROM posts;"

# 4. Restart API with SQLite
docker-compose up -d api

echo "Rolled back to SQLite"
```

## 33. Workspace Membership (Complete Schema)

### 33.1 Problem: Underspecified Membership

The original schema used a composite key `(workspace_id, user_id)` which:
- Cannot be referenced by other tables (approvals, assignments)
- Cannot track invite state properly
- Cannot enforce "exactly one owner"

### 33.2 Revised Schema

```sql
CREATE TABLE workspace_memberships (
    -- Surrogate primary key for FK references
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Core relationship
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,  -- NULL until invite accepted
    email VARCHAR(255) NOT NULL,  -- Always stored for pending invites

    -- Role
    role VARCHAR(20) NOT NULL CHECK (role IN ('owner', 'admin', 'editor', 'viewer')),

    -- Invite state
    invite_status VARCHAR(20) NOT NULL DEFAULT 'pending'
        CHECK (invite_status IN ('pending', 'active', 'expired', 'removed')),
    invite_token VARCHAR(255) UNIQUE,
    invite_expires_at TIMESTAMPTZ,
    invited_by_id UUID REFERENCES users(id),
    invited_at TIMESTAMPTZ,
    accepted_at TIMESTAMPTZ,

    -- Client portal (Agency tier)
    is_client BOOLEAN DEFAULT false,
    client_company_name VARCHAR(255),
    portal_access_token VARCHAR(255),
    portal_token_expires_at TIMESTAMPTZ,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- Constraints
    UNIQUE(workspace_id, email),  -- One invite per email per workspace
    UNIQUE(workspace_id, user_id) -- One membership per user per workspace (when user_id set)
);

CREATE INDEX idx_memberships_workspace ON workspace_memberships(workspace_id);
CREATE INDEX idx_memberships_user ON workspace_memberships(user_id);
CREATE INDEX idx_memberships_invite ON workspace_memberships(invite_token) WHERE invite_status = 'pending';
```

### 33.3 Owner Enforcement

```sql
-- Trigger to ensure exactly one owner per workspace
CREATE OR REPLACE FUNCTION enforce_single_owner()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.role = 'owner' AND NEW.invite_status = 'active' THEN
        -- Check if another active owner exists
        IF EXISTS (
            SELECT 1 FROM workspace_memberships
            WHERE workspace_id = NEW.workspace_id
              AND role = 'owner'
              AND invite_status = 'active'
              AND id != NEW.id
        ) THEN
            RAISE EXCEPTION 'Workspace already has an owner';
        END IF;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_single_owner
    BEFORE INSERT OR UPDATE ON workspace_memberships
    FOR EACH ROW EXECUTE FUNCTION enforce_single_owner();
```

### 33.4 FK References from Other Tables

```sql
-- Approvals reference membership
ALTER TABLE approval_requests
    ADD COLUMN membership_id UUID REFERENCES workspace_memberships(id);

-- Assignments reference membership
ALTER TABLE posts
    ALTER COLUMN assignee_id TYPE UUID,
    ADD CONSTRAINT fk_posts_assignee
        FOREIGN KEY (assignee_id) REFERENCES workspace_memberships(id);
```

## 34. Complete RBAC Matrix

### 34.1 Scope Definitions

```python
# api/auth/scopes.py

class Scope(str, Enum):
    # Content
    CONTENT_READ = "content:read"
    CONTENT_WRITE = "content:write"
    CONTENT_DELETE = "content:delete"
    CONTENT_PUBLISH = "content:publish"

    # Strategy
    STRATEGY_READ = "strategy:read"
    STRATEGY_WRITE = "strategy:write"

    # Workflow
    WORKFLOW_RUN = "workflow:run"
    WORKFLOW_CANCEL = "workflow:cancel"

    # Approvals
    APPROVAL_VIEW = "approval:view"
    APPROVAL_SUBMIT = "approval:submit"
    APPROVAL_DECIDE = "approval:decide"

    # Workspace
    WORKSPACE_SETTINGS = "workspace:settings"
    WORKSPACE_USERS = "workspace:users"
    WORKSPACE_BILLING = "workspace:billing"
    WORKSPACE_DELETE = "workspace:delete"

    # Board/Kanban
    BOARD_VIEW = "board:view"
    BOARD_MOVE = "board:move"
    BOARD_ASSIGN = "board:assign"

    # Usage
    USAGE_VIEW = "usage:view"
    USAGE_ADMIN = "usage:admin"

    # API
    API_KEYS_MANAGE = "api:keys:manage"
    WEBHOOKS_MANAGE = "api:webhooks:manage"
```

### 34.2 Role → Scope Matrix

| Scope | Owner | Admin | Editor | Viewer |
|-------|:-----:|:-----:|:------:|:------:|
| `content:read` | ✓ | ✓ | ✓ | ✓ |
| `content:write` | ✓ | ✓ | ✓ | - |
| `content:delete` | ✓ | ✓ | - | - |
| `content:publish` | ✓ | ✓ | - | - |
| `strategy:read` | ✓ | ✓ | ✓ | - |
| `strategy:write` | ✓ | ✓ | - | - |
| `workflow:run` | ✓ | ✓ | ✓ | - |
| `workflow:cancel` | ✓ | ✓ | ✓ | - |
| `approval:view` | ✓ | ✓ | ✓ | ✓ |
| `approval:submit` | ✓ | ✓ | ✓ | - |
| `approval:decide` | ✓ | ✓ | - | ✓* |
| `workspace:settings` | ✓ | ✓ | - | - |
| `workspace:users` | ✓ | ✓ | - | - |
| `workspace:billing` | ✓ | - | - | - |
| `workspace:delete` | ✓ | - | - | - |
| `board:view` | ✓ | ✓ | ✓ | ✓ |
| `board:move` | ✓ | ✓ | ✓ | - |
| `board:assign` | ✓ | ✓ | - | - |
| `usage:view` | ✓ | ✓ | ✓ | - |
| `usage:admin` | ✓ | - | - | - |
| `api:keys:manage` | ✓ | ✓ | - | - |
| `api:webhooks:manage` | ✓ | ✓ | - | - |

*Viewer can only approve posts assigned to them (client approval flow)

### 34.3 Permission Check Middleware

```python
# api/middleware/permissions.py

from functools import wraps

ROLE_SCOPES = {
    'owner': {Scope.CONTENT_READ, Scope.CONTENT_WRITE, ...},  # All scopes
    'admin': {Scope.CONTENT_READ, Scope.CONTENT_WRITE, Scope.CONTENT_DELETE, ...},
    'editor': {Scope.CONTENT_READ, Scope.CONTENT_WRITE, Scope.WORKFLOW_RUN, ...},
    'viewer': {Scope.CONTENT_READ, Scope.APPROVAL_VIEW, Scope.APPROVAL_DECIDE, Scope.BOARD_VIEW},
}

def require_scope(*required_scopes: Scope):
    """Decorator to enforce scope requirements on endpoints."""
    def decorator(func):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            membership = request.state.membership
            if not membership:
                raise HTTPException(401, "Not authenticated")

            user_scopes = ROLE_SCOPES.get(membership.role, set())

            # Check all required scopes
            missing = set(required_scopes) - user_scopes
            if missing:
                raise HTTPException(
                    403,
                    f"Missing permissions: {', '.join(s.value for s in missing)}"
                )

            return await func(request, *args, **kwargs)
        return wrapper
    return decorator

# Usage in routes
@router.delete("/posts/{post_id}")
@require_scope(Scope.CONTENT_DELETE)
async def delete_post(request: Request, post_id: UUID):
    ...

@router.post("/workflow/run")
@require_scope(Scope.WORKFLOW_RUN)
async def start_workflow(request: Request, ...):
    ...

@router.put("/settings/billing")
@require_scope(Scope.WORKSPACE_BILLING)
async def update_billing(request: Request, ...):
    ...
```

### 34.4 Frontend Permission Gates

```typescript
// gui/src/hooks/usePermission.ts

const ROLE_SCOPES: Record<Role, Set<Scope>> = {
  owner: new Set([...ALL_SCOPES]),
  admin: new Set([Scope.CONTENT_READ, Scope.CONTENT_WRITE, ...]),
  editor: new Set([Scope.CONTENT_READ, Scope.CONTENT_WRITE, Scope.WORKFLOW_RUN, ...]),
  viewer: new Set([Scope.CONTENT_READ, Scope.APPROVAL_VIEW, Scope.BOARD_VIEW]),
}

export function usePermission(scope: Scope): boolean {
  const { membership } = useWorkspace()
  if (!membership) return false
  return ROLE_SCOPES[membership.role]?.has(scope) ?? false
}

// Usage in components
function DeleteButton({ postId }: { postId: string }) {
  const canDelete = usePermission(Scope.CONTENT_DELETE)
  if (!canDelete) return null
  return <button onClick={() => deletePost(postId)}>Delete</button>
}
```

## 35. Workspace Context Resolution

### 35.1 Problem: Header vs URL Conflict

Two sources of workspace_id:
- Header: `X-Workspace-ID` (original design)
- URL: `/w/{workspaceId}/...` (added for deep-linking)

### 35.2 Resolution: URL is Canonical

**URL parameter is the single source of truth.** The header is deprecated.

```python
# api/middleware/workspace.py

class WorkspaceContextMiddleware:
    """Extract workspace from URL path, NOT from header."""

    async def __call__(self, request: Request, call_next):
        # Extract workspace_id from URL path
        workspace_id = self.extract_from_path(request.url.path)

        if workspace_id:
            # Verify user has access to this workspace
            membership = await self.get_membership(
                request.state.user.id,
                workspace_id
            )

            if not membership or membership.invite_status != 'active':
                raise HTTPException(403, "Access denied to this workspace")

            request.state.workspace_id = workspace_id
            request.state.membership = membership

        # DEPRECATION: Warn if header is present
        if 'X-Workspace-ID' in request.headers:
            logger.warning(
                "deprecated_header",
                header="X-Workspace-ID",
                message="Use URL path /w/{workspace_id}/... instead"
            )

        return await call_next(request)

    def extract_from_path(self, path: str) -> Optional[UUID]:
        """Extract workspace_id from /w/{uuid}/... pattern."""
        match = re.match(r'^/api/v\d+/w/([a-f0-9-]{36})/', path)
        if match:
            return UUID(match.group(1))
        return None
```

### 35.3 API Route Structure

```python
# api/routers/v1/__init__.py

# All workspace-scoped routes under /w/{workspace_id}
router = APIRouter(prefix="/api/v1")

# Public routes (no workspace)
router.include_router(auth_router, prefix="/auth", tags=["auth"])

# Workspace-scoped routes
ws_router = APIRouter(prefix="/w/{workspace_id}")
ws_router.include_router(content_router, prefix="/content", tags=["content"])
ws_router.include_router(workflow_router, prefix="/workflow", tags=["workflow"])
ws_router.include_router(board_router, prefix="/board", tags=["board"])
ws_router.include_router(settings_router, prefix="/settings", tags=["settings"])

router.include_router(ws_router)

# Final routes:
# POST /api/v1/auth/login
# GET  /api/v1/w/{workspace_id}/content/posts
# POST /api/v1/w/{workspace_id}/workflow/run
# GET  /api/v1/w/{workspace_id}/board
```

### 35.4 Cross-Tenant Protection

```python
# api/dependencies.py

async def get_workspace(
    workspace_id: UUID = Path(...),
    user: User = Depends(get_current_user)
) -> Workspace:
    """Dependency that validates workspace access."""
    membership = await db.query(WorkspaceMembership).filter(
        WorkspaceMembership.workspace_id == workspace_id,
        WorkspaceMembership.user_id == user.id,
        WorkspaceMembership.invite_status == 'active'
    ).first()

    if not membership:
        # CRITICAL: Don't reveal if workspace exists
        raise HTTPException(404, "Workspace not found")

    workspace = await db.query(Workspace).get(workspace_id)
    return workspace

# Usage
@router.get("/w/{workspace_id}/posts")
async def list_posts(workspace: Workspace = Depends(get_workspace)):
    # workspace is guaranteed to be accessible by current user
    return await post_service.list(workspace.id)
```

## 36. Atomic Usage & Billing

### 36.1 Problem: Race Conditions

Concurrent workflows can oversubscribe credits. Webhook retries can double-charge.

### 36.2 Solution: Transactional Credit Management

```python
# api/services/usage_service.py

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert

class UsageService:
    async def reserve_credits(
        self,
        workspace_id: UUID,
        credits: int,
        idempotency_key: str  # e.g., run_id
    ) -> bool:
        """
        Atomically reserve credits with optimistic locking.
        Returns False if limit exceeded.
        """
        async with db.begin():  # Transaction
            # Lock the usage row for update
            usage = await db.execute(
                select(UsageTracking)
                .where(
                    UsageTracking.workspace_id == workspace_id,
                    UsageTracking.period_start == self.current_period_start()
                )
                .with_for_update()  # Row-level lock
            ).scalar_one_or_none()

            if not usage:
                # Create usage record if doesn't exist
                usage = UsageTracking(
                    workspace_id=workspace_id,
                    period_start=self.current_period_start(),
                    period_end=self.current_period_end()
                )
                db.add(usage)

            # Check limit
            subscription = await self.get_subscription(workspace_id)
            limit = subscription.tier.max_credits_per_month
            available = limit - usage.credits_used - usage.credits_reserved

            if credits > available and not subscription.overage_enabled:
                return False

            # Reserve
            usage.credits_reserved += credits

            # Record reservation for idempotency
            reservation = CreditReservation(
                idempotency_key=idempotency_key,
                workspace_id=workspace_id,
                credits=credits,
                status='reserved'
            )
            db.add(reservation)

            # Commit happens automatically at end of context

        return True

    async def confirm_credits(
        self,
        workspace_id: UUID,
        idempotency_key: str,
        actual_tokens: TokenUsage
    ) -> None:
        """
        Confirm reserved credits after workflow completion.
        Idempotent - safe to retry.
        """
        async with db.begin():
            # Check if already confirmed (idempotency)
            reservation = await db.execute(
                select(CreditReservation)
                .where(CreditReservation.idempotency_key == idempotency_key)
                .with_for_update()
            ).scalar_one_or_none()

            if not reservation:
                raise ValueError(f"No reservation found: {idempotency_key}")

            if reservation.status == 'confirmed':
                # Already processed, skip
                return

            # Lock and update usage
            usage = await db.execute(
                select(UsageTracking)
                .where(
                    UsageTracking.workspace_id == workspace_id,
                    UsageTracking.period_start == self.current_period_start()
                )
                .with_for_update()
            ).scalar_one()

            # Move from reserved to used
            usage.credits_reserved -= reservation.credits
            usage.credits_used += reservation.credits
            usage.tokens_input += actual_tokens.input
            usage.tokens_output += actual_tokens.output

            # Track overage
            limit = await self.get_limit(workspace_id)
            if usage.credits_used > limit:
                usage.overage_credits = usage.credits_used - limit

            # Mark reservation confirmed
            reservation.status = 'confirmed'
            reservation.confirmed_at = datetime.utcnow()
```

### 36.3 Schema: Credit Reservations (Idempotency)

```sql
CREATE TABLE credit_reservations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    idempotency_key VARCHAR(255) NOT NULL UNIQUE,  -- Usually run_id
    workspace_id UUID NOT NULL REFERENCES workspaces(id),
    credits INTEGER NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'reserved',  -- 'reserved', 'confirmed', 'released'
    reserved_at TIMESTAMPTZ DEFAULT NOW(),
    confirmed_at TIMESTAMPTZ,
    released_at TIMESTAMPTZ
);

CREATE INDEX idx_reservations_workspace ON credit_reservations(workspace_id);
CREATE INDEX idx_reservations_status ON credit_reservations(status) WHERE status = 'reserved';
```

### 36.4 Stripe Webhook Idempotency

```python
# api/routers/webhooks/stripe.py

@router.post("/stripe")
async def handle_stripe_webhook(request: Request):
    payload = await request.body()
    sig = request.headers.get('stripe-signature')

    try:
        event = stripe.Webhook.construct_event(payload, sig, WEBHOOK_SECRET)
    except ValueError:
        raise HTTPException(400, "Invalid payload")

    # Idempotency check
    existing = await db.query(BillingEvent).filter(
        BillingEvent.stripe_event_id == event.id
    ).first()

    if existing:
        if existing.processed_at:
            # Already processed, return success
            return {"status": "already_processed"}
        else:
            # Processing failed before, retry
            pass

    # Record event before processing
    billing_event = BillingEvent(
        stripe_event_id=event.id,
        event_type=event.type,
        payload=event.data
    )
    await db.save(billing_event)

    try:
        # Process event
        await process_stripe_event(event)

        # Mark processed
        billing_event.processed_at = datetime.utcnow()
        await db.save(billing_event)

    except Exception as e:
        logger.error("stripe_webhook_failed", event_id=event.id, error=str(e))
        raise

    return {"status": "processed"}
```

## 37. Agency Entity (Account Grouping)

### 37.1 Problem: No Parent Tenant

Without an Agency entity, we cannot:
- Group workspaces under one billing account
- Enforce tier limits (max 10 workspaces for Agency)
- Generate per-agency audit logs

### 37.2 Schema: Accounts Table

```sql
CREATE TABLE accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    owner_id UUID NOT NULL REFERENCES users(id),
    account_type VARCHAR(20) NOT NULL DEFAULT 'individual',  -- 'individual', 'team', 'agency'
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Move subscription from workspace to account level
ALTER TABLE account_subscriptions
    DROP COLUMN workspace_id,
    ADD COLUMN account_id UUID NOT NULL REFERENCES accounts(id) ON DELETE CASCADE;

-- Link workspaces to accounts
ALTER TABLE workspaces
    ADD COLUMN account_id UUID NOT NULL REFERENCES accounts(id) ON DELETE CASCADE;

CREATE INDEX idx_workspaces_account ON workspaces(account_id);
```

### 37.3 Updated Entity Relationship

```mermaid
erDiagram
    User ||--o{ Account : "owns"
    Account ||--o{ Workspace : "contains"
    Account ||--|| AccountSubscription : "has"
    Workspace ||--o{ WorkspaceMembership : "has"
    User ||--o{ WorkspaceMembership : "member of"
```

### 37.4 Tier Limit Enforcement

```python
# api/services/workspace_service.py

class WorkspaceService:
    async def create_workspace(
        self,
        account_id: UUID,
        name: str,
        owner_id: UUID
    ) -> Workspace:
        # Check workspace limit
        account = await self.get_account(account_id)
        subscription = await self.billing_service.get_subscription(account_id)
        current_count = await self.count_workspaces(account_id)

        if current_count >= subscription.tier.max_workspaces:
            raise HTTPException(
                403,
                f"Workspace limit reached ({subscription.tier.max_workspaces}). "
                "Upgrade your plan to create more workspaces."
            )

        workspace = Workspace(
            account_id=account_id,
            name=name,
            owner_id=owner_id
        )
        await db.save(workspace)
        return workspace

    async def add_member(
        self,
        workspace_id: UUID,
        email: str,
        role: str
    ) -> WorkspaceMembership:
        workspace = await self.get_workspace(workspace_id)
        subscription = await self.billing_service.get_subscription(workspace.account_id)

        # Check user limit (across all workspaces in account)
        current_users = await self.count_unique_users(workspace.account_id)

        if subscription.tier.max_users and current_users >= subscription.tier.max_users:
            raise HTTPException(
                403,
                f"User limit reached ({subscription.tier.max_users}). "
                "Upgrade your plan to invite more team members."
            )

        # ... create membership
```

## 38. Telemetry Privacy & Consent

### 38.1 Data Categories

| Category | Contains | Retention | Consent Required |
|----------|----------|-----------|------------------|
| **Operational** | Errors, latency | 30 days | No (legitimate interest) |
| **Analytics** | Page views, feature usage | 1 year | Yes (opt-out) |
| **Feedback** | User-provided text | Forever | Yes (explicit) |

### 38.2 Schema Updates

```sql
-- User consent preferences
ALTER TABLE users ADD COLUMN IF NOT EXISTS telemetry_consent JSONB DEFAULT '{
    "analytics": true,
    "feedback_collection": true,
    "marketing": false
}';

-- Workspace-level override (for agency clients)
ALTER TABLE workspaces ADD COLUMN IF NOT EXISTS telemetry_enabled BOOLEAN DEFAULT true;

-- Add anonymization flag to telemetry
ALTER TABLE telemetry_events ADD COLUMN IF NOT EXISTS is_anonymized BOOLEAN DEFAULT false;
```

### 38.3 Consent Flow

```python
# api/services/telemetry_service.py

class TelemetryService:
    async def log_event(
        self,
        user_id: UUID,
        workspace_id: UUID,
        event_category: str,
        event_action: str,
        payload: dict
    ) -> Optional[TelemetryEvent]:
        # Check workspace-level opt-out
        workspace = await db.query(Workspace).get(workspace_id)
        if not workspace.telemetry_enabled:
            return None

        # Check user consent for category
        user = await db.query(User).get(user_id)
        consent = user.telemetry_consent or {}

        if event_category == 'analytics' and not consent.get('analytics', True):
            return None

        if event_category == 'feedback' and not consent.get('feedback_collection', True):
            return None

        # Log event
        event = TelemetryEvent(
            user_id=user_id,
            workspace_id=workspace_id,
            event_category=event_category,
            event_action=event_action,
            payload=payload
        )
        await db.save(event)
        return event
```

### 38.4 Data Retention & Anonymization

```python
# scripts/telemetry_retention.py (cron job)

async def apply_retention_policy():
    """Run daily to enforce data retention."""

    # Delete old operational logs (30 days)
    await db.execute("""
        DELETE FROM telemetry_events
        WHERE event_category = 'operational'
          AND timestamp < NOW() - INTERVAL '30 days'
    """)

    # Anonymize analytics older than 1 year
    await db.execute("""
        UPDATE telemetry_events
        SET user_id = NULL,
            payload = payload - 'user_email' - 'ip_address',
            is_anonymized = true
        WHERE event_category = 'analytics'
          AND timestamp < NOW() - INTERVAL '1 year'
          AND NOT is_anonymized
    """)

    # Keep feedback forever but remove PII after 2 years
    await db.execute("""
        UPDATE telemetry_events
        SET payload = jsonb_set(
            payload - 'user_name' - 'user_email',
            '{anonymized}',
            'true'
        ),
        is_anonymized = true
        WHERE event_category = 'feedback'
          AND timestamp < NOW() - INTERVAL '2 years'
          AND NOT is_anonymized
    """)
```

### 38.5 Privacy UI

```typescript
// gui/src/pages/Settings/Privacy.tsx

function PrivacySettings() {
  const { user, updateConsent } = useAuth()

  return (
    <div>
      <h2>Privacy Settings</h2>

      <Toggle
        label="Analytics"
        description="Help us improve by sharing anonymous usage data"
        checked={user.telemetryConsent.analytics}
        onChange={(v) => updateConsent({ analytics: v })}
      />

      <Toggle
        label="Feedback Collection"
        description="Allow us to collect your feedback and refinement text"
        checked={user.telemetryConsent.feedback_collection}
        onChange={(v) => updateConsent({ feedback_collection: v })}
      />

      <Button onClick={() => exportMyData()}>
        Export My Data
      </Button>

      <Button variant="danger" onClick={() => deleteMyData()}>
        Delete All My Data
      </Button>
    </div>
  )
}
```

## 39. Asset Cleanup Strategy

### 39.1 Problem: Orphaned S3 Objects

When assets are deleted from the database, the corresponding S3 objects remain, accumulating storage costs.

### 39.2 Solution: Multi-Layer Cleanup

#### Layer 1: Database Trigger (Immediate)

```sql
-- Track deletions for async cleanup
CREATE TABLE asset_deletions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    s3_bucket VARCHAR(100) NOT NULL,
    s3_key VARCHAR(500) NOT NULL,
    deleted_at TIMESTAMPTZ DEFAULT NOW(),
    cleaned_up_at TIMESTAMPTZ
);

CREATE INDEX idx_asset_deletions_pending ON asset_deletions(deleted_at) WHERE cleaned_up_at IS NULL;

-- Trigger to capture deletions
CREATE OR REPLACE FUNCTION track_asset_deletion()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO asset_deletions (s3_bucket, s3_key)
    VALUES (OLD.s3_bucket, OLD.s3_key);
    RETURN OLD;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_asset_deletion
    BEFORE DELETE ON assets
    FOR EACH ROW EXECUTE FUNCTION track_asset_deletion();
```

#### Layer 2: Background Worker (Async)

```python
# scripts/cleanup_assets.py (cron: every 5 minutes)

async def cleanup_deleted_assets():
    """Delete S3 objects for removed assets."""
    pending = await db.execute("""
        SELECT id, s3_bucket, s3_key FROM asset_deletions
        WHERE cleaned_up_at IS NULL
        ORDER BY deleted_at
        LIMIT 100
    """).fetchall()

    for row in pending:
        try:
            await s3.delete_object(Bucket=row.s3_bucket, Key=row.s3_key)
            await db.execute("""
                UPDATE asset_deletions SET cleaned_up_at = NOW()
                WHERE id = $1
            """, row.id)
        except s3.exceptions.NoSuchKey:
            # Already deleted, mark as cleaned
            await db.execute("""
                UPDATE asset_deletions SET cleaned_up_at = NOW()
                WHERE id = $1
            """, row.id)
        except Exception as e:
            logger.error("asset_cleanup_failed", s3_key=row.s3_key, error=str(e))
```

#### Layer 3: S3 Lifecycle Rules (Safety Net)

```json
{
    "Rules": [
        {
            "ID": "cleanup-orphaned-workspace-assets",
            "Filter": {
                "Prefix": "workspaces/"
            },
            "Status": "Enabled",
            "Expiration": {
                "Days": 90
            },
            "NoncurrentVersionExpiration": {
                "NoncurrentDays": 30
            }
        },
        {
            "ID": "cleanup-incomplete-uploads",
            "Filter": {},
            "Status": "Enabled",
            "AbortIncompleteMultipartUpload": {
                "DaysAfterInitiation": 7
            }
        }
    ]
}
```

### 39.3 Cascade Deletes

When a workspace is deleted, all its assets should be cleaned up.

```python
# api/services/workspace_service.py

async def delete_workspace(workspace_id: UUID):
    """Delete workspace and all associated data."""
    async with db.begin():
        # Get all assets for this workspace
        assets = await db.execute("""
            SELECT s3_bucket, s3_key FROM assets WHERE workspace_id = $1
        """, workspace_id).fetchall()

        # Queue S3 deletions
        for asset in assets:
            await db.execute("""
                INSERT INTO asset_deletions (s3_bucket, s3_key)
                VALUES ($1, $2)
            """, asset.s3_bucket, asset.s3_key)

        # Delete workspace (cascades to assets table via FK)
        await db.execute("DELETE FROM workspaces WHERE id = $1", workspace_id)

    # Trigger immediate cleanup
    await cleanup_deleted_assets()
```

### 39.4 Monitoring

```sql
-- Alert if cleanup backlog grows
SELECT COUNT(*) as pending_cleanups,
       MIN(deleted_at) as oldest_pending
FROM asset_deletions
WHERE cleaned_up_at IS NULL;

-- Alert threshold: > 1000 pending or oldest > 1 hour
```

## 40. Push Notifications (Web Push)

### 40.1 Overview

Web Push enables notifications even when the browser is closed, improving engagement for time-sensitive events.

### 40.2 Schema: Push Subscriptions

```sql
CREATE TABLE push_subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    endpoint TEXT NOT NULL UNIQUE,
    p256dh_key TEXT NOT NULL,
    auth_key TEXT NOT NULL,
    user_agent TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_used_at TIMESTAMPTZ
);

CREATE INDEX idx_push_subscriptions_user ON push_subscriptions(user_id);
```

### 40.3 VAPID Key Generation

```bash
# Generate VAPID keys (one-time setup)
npx web-push generate-vapid-keys

# Store in environment
VAPID_PUBLIC_KEY=BEl62iUYgUiv...
VAPID_PRIVATE_KEY=UGTXy4kDmN...
VAPID_SUBJECT=mailto:notifications@postmatiq.com
```

### 40.4 Frontend: Service Worker Registration

```typescript
// gui/src/services/push.ts

export async function subscribeToPush(): Promise<PushSubscription | null> {
  if (!('serviceWorker' in navigator) || !('PushManager' in window)) {
    return null
  }

  const registration = await navigator.serviceWorker.register('/sw.js')

  const subscription = await registration.pushManager.subscribe({
    userVisibleOnly: true,
    applicationServerKey: urlBase64ToUint8Array(VAPID_PUBLIC_KEY)
  })

  // Send subscription to backend
  await api.post('/notifications/push/subscribe', {
    endpoint: subscription.endpoint,
    keys: {
      p256dh: btoa(String.fromCharCode(...new Uint8Array(subscription.getKey('p256dh')!))),
      auth: btoa(String.fromCharCode(...new Uint8Array(subscription.getKey('auth')!)))
    }
  })

  return subscription
}
```

### 40.5 Service Worker

```javascript
// gui/public/sw.js

self.addEventListener('push', (event) => {
  const data = event.data?.json() ?? {}

  const options = {
    body: data.body,
    icon: '/icon-192.png',
    badge: '/badge-72.png',
    tag: data.tag || 'default',
    data: { url: data.url },
    actions: data.actions || []
  }

  event.waitUntil(
    self.registration.showNotification(data.title || 'Postmagiq', options)
  )
})

self.addEventListener('notificationclick', (event) => {
  event.notification.close()

  if (event.notification.data?.url) {
    event.waitUntil(
      clients.openWindow(event.notification.data.url)
    )
  }
})
```

### 40.6 Backend: Send Push

```python
# api/services/push_service.py

from pywebpush import webpush, WebPushException

class PushService:
    async def send_push(
        self,
        user_id: UUID,
        title: str,
        body: str,
        url: str = None,
        tag: str = None
    ):
        subscriptions = await db.query(PushSubscription).filter(
            PushSubscription.user_id == user_id
        ).all()

        for sub in subscriptions:
            try:
                webpush(
                    subscription_info={
                        "endpoint": sub.endpoint,
                        "keys": {
                            "p256dh": sub.p256dh_key,
                            "auth": sub.auth_key
                        }
                    },
                    data=json.dumps({
                        "title": title,
                        "body": body,
                        "url": url,
                        "tag": tag
                    }),
                    vapid_private_key=settings.VAPID_PRIVATE_KEY,
                    vapid_claims={"sub": settings.VAPID_SUBJECT}
                )

                sub.last_used_at = datetime.utcnow()
                await db.save(sub)

            except WebPushException as e:
                if e.response.status_code in (404, 410):
                    # Subscription expired, remove it
                    await db.delete(sub)
                else:
                    logger.error("push_failed", user_id=str(user_id), error=str(e))
```

### 40.7 Notification Preferences Update

```sql
-- Add push preference to notification_preferences
ALTER TABLE notification_preferences
    ADD COLUMN IF NOT EXISTS push BOOLEAN DEFAULT true;
```

### 40.8 Push Events

| Event | Push Title | Body |
|-------|------------|------|
| `post_assigned` | "New Assignment" | "{post_topic} assigned to you" |
| `approval_requested` | "Approval Needed" | "{post_topic} needs your review" |
| `post_due_soon` | "Due Tomorrow" | "{post_topic} is due in 24 hours" |
| `approval_completed` | "Post Approved" | "{post_topic} was approved" |

## 41. Community Template Marketplace (Future)

### 41.1 Overview

Allow users to share successful templates (prompts, personas, workflows) with the community. **Out of scope for MVP** but schema designed for future expansion.

### 41.2 Schema: Marketplace Templates

```sql
CREATE TABLE marketplace_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    -- Origin
    author_id UUID NOT NULL REFERENCES users(id),
    source_template_id UUID REFERENCES system_templates(id),
    -- Metadata
    name VARCHAR(255) NOT NULL,
    description TEXT,
    template_type VARCHAR(50) NOT NULL,  -- 'persona', 'prompt', 'workflow'
    content TEXT NOT NULL,
    -- Discovery
    tags JSONB DEFAULT '[]',
    category VARCHAR(100),
    -- Stats
    downloads INTEGER DEFAULT 0,
    rating_sum INTEGER DEFAULT 0,
    rating_count INTEGER DEFAULT 0,
    -- Moderation
    status VARCHAR(20) DEFAULT 'pending',  -- 'pending', 'approved', 'rejected', 'removed'
    reviewed_by_id UUID REFERENCES users(id),
    reviewed_at TIMESTAMPTZ,
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_marketplace_status ON marketplace_templates(status, template_type);
CREATE INDEX idx_marketplace_downloads ON marketplace_templates(downloads DESC) WHERE status = 'approved';
CREATE INDEX idx_marketplace_rating ON marketplace_templates((rating_sum::float / NULLIF(rating_count, 0)) DESC) WHERE status = 'approved';
```

### 41.3 Schema: Template Installs

```sql
CREATE TABLE template_installs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    marketplace_template_id UUID NOT NULL REFERENCES marketplace_templates(id),
    workspace_id UUID NOT NULL REFERENCES workspaces(id),
    installed_by_id UUID NOT NULL REFERENCES users(id),
    installed_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(marketplace_template_id, workspace_id)
);
```

### 41.4 Schema: Template Ratings

```sql
CREATE TABLE template_ratings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    marketplace_template_id UUID NOT NULL REFERENCES marketplace_templates(id),
    user_id UUID NOT NULL REFERENCES users(id),
    rating INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
    review TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(marketplace_template_id, user_id)
);

-- Update aggregate on rating change
CREATE OR REPLACE FUNCTION update_template_rating()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE marketplace_templates
    SET rating_sum = (SELECT COALESCE(SUM(rating), 0) FROM template_ratings WHERE marketplace_template_id = NEW.marketplace_template_id),
        rating_count = (SELECT COUNT(*) FROM template_ratings WHERE marketplace_template_id = NEW.marketplace_template_id)
    WHERE id = NEW.marketplace_template_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_update_rating
    AFTER INSERT OR UPDATE OR DELETE ON template_ratings
    FOR EACH ROW EXECUTE FUNCTION update_template_rating();
```

### 41.5 Future API Endpoints

```
GET  /api/v1/marketplace/templates?type=persona&sort=popular
GET  /api/v1/marketplace/templates/{id}
POST /api/v1/marketplace/templates              # Submit template
POST /api/v1/marketplace/templates/{id}/install # Install to workspace
POST /api/v1/marketplace/templates/{id}/rate    # Rate template
```

### 41.6 Revenue Model (Future)

| Template Type | Free | Premium ($) | Revenue Split |
|---------------|------|-------------|---------------|
| Community | ✓ | - | - |
| Verified | ✓ | - | - |
| Premium | - | $5-25 | 70% author / 30% platform |

## 42. Error Handling & Retry Policies

### 42.1 API Error Responses

```python
# api/errors.py

class APIError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 400, details: dict = None):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}

# Standard error codes
class ErrorCodes:
    # Auth
    INVALID_CREDENTIALS = "auth/invalid-credentials"
    SESSION_EXPIRED = "auth/session-expired"
    SESSION_REVOKED = "auth/session-revoked"

    # Workspace
    WORKSPACE_NOT_FOUND = "workspace/not-found"
    WORKSPACE_ACCESS_DENIED = "workspace/access-denied"
    WORKSPACE_LIMIT_REACHED = "workspace/limit-reached"

    # Usage
    CREDITS_EXCEEDED = "usage/credits-exceeded"
    RATE_LIMIT_EXCEEDED = "usage/rate-limit-exceeded"

    # Content
    POST_NOT_FOUND = "content/post-not-found"
    INVALID_STATUS_TRANSITION = "content/invalid-status-transition"

    # Billing
    PAYMENT_REQUIRED = "billing/payment-required"
    SUBSCRIPTION_INACTIVE = "billing/subscription-inactive"

# Error response format
{
    "error": {
        "code": "usage/credits-exceeded",
        "message": "Monthly AI credit limit reached",
        "details": {
            "credits_used": 100,
            "credits_limit": 100,
            "reset_date": "2026-02-01"
        }
    }
}
```

### 42.2 Retry Policies

| Operation | Retries | Backoff | Timeout |
|-----------|---------|---------|---------|
| AI workflow step | 2 | Exponential (1s, 4s) | 5 min |
| S3 upload | 3 | Linear (1s) | 30s |
| Stripe API | 3 | Exponential (1s, 2s, 4s) | 10s |
| Email send | 3 | Exponential (5s, 30s, 5min) | 30s |
| Webhook delivery | 5 | Exponential (1min, 5min, 30min, 2hr, 24hr) | 30s |
| Push notification | 1 | None | 10s |

### 42.3 Circuit Breaker for External Services

```python
# api/utils/circuit_breaker.py

from datetime import datetime, timedelta

class CircuitBreaker:
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        half_open_requests: int = 3
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_requests = half_open_requests
        self.failures = 0
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half-open

    def can_execute(self) -> bool:
        if self.state == "closed":
            return True

        if self.state == "open":
            if datetime.utcnow() - self.last_failure_time > timedelta(seconds=self.recovery_timeout):
                self.state = "half-open"
                self.half_open_count = 0
                return True
            return False

        if self.state == "half-open":
            self.half_open_count += 1
            return self.half_open_count <= self.half_open_requests

    def record_success(self):
        if self.state == "half-open":
            self.state = "closed"
        self.failures = 0

    def record_failure(self):
        self.failures += 1
        self.last_failure_time = datetime.utcnow()

        if self.failures >= self.failure_threshold:
            self.state = "open"

# Usage
stripe_breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=60)

async def charge_customer(customer_id: str, amount: int):
    if not stripe_breaker.can_execute():
        raise APIError(
            ErrorCodes.SERVICE_UNAVAILABLE,
            "Payment service temporarily unavailable",
            status_code=503
        )

    try:
        result = await stripe.charges.create(...)
        stripe_breaker.record_success()
        return result
    except stripe.error.APIError:
        stripe_breaker.record_failure()
        raise
```

## 43. Health Checks & Readiness Probes

### 43.1 Health Endpoints

```python
# api/routers/health.py

@router.get("/health/live")
async def liveness():
    """Kubernetes liveness probe - is the process running?"""
    return {"status": "ok"}

@router.get("/health/ready")
async def readiness():
    """Kubernetes readiness probe - can we serve traffic?"""
    checks = {}

    # Database
    try:
        await db.execute("SELECT 1")
        checks["database"] = "ok"
    except Exception as e:
        checks["database"] = f"error: {str(e)}"

    # Redis (if used)
    try:
        await redis.ping()
        checks["redis"] = "ok"
    except Exception as e:
        checks["redis"] = f"error: {str(e)}"

    # S3
    try:
        await s3.head_bucket(Bucket=settings.S3_BUCKET)
        checks["s3"] = "ok"
    except Exception as e:
        checks["s3"] = f"error: {str(e)}"

    all_ok = all(v == "ok" for v in checks.values())

    return JSONResponse(
        status_code=200 if all_ok else 503,
        content={"status": "ok" if all_ok else "degraded", "checks": checks}
    )

@router.get("/health/startup")
async def startup():
    """Kubernetes startup probe - has initialization completed?"""
    # Check migrations are up to date
    try:
        current = await get_current_migration_version()
        latest = get_latest_migration_version()
        if current != latest:
            return JSONResponse(
                status_code=503,
                content={"status": "pending_migrations", "current": current, "latest": latest}
            )
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={"status": "error", "message": str(e)}
        )

    return {"status": "ok"}
```

### 43.2 Kubernetes Configuration

```yaml
# k8s/deployment.yaml

apiVersion: apps/v1
kind: Deployment
spec:
  template:
    spec:
      containers:
        - name: api
          livenessProbe:
            httpGet:
              path: /health/live
              port: 8000
            initialDelaySeconds: 10
            periodSeconds: 10
            failureThreshold: 3

          readinessProbe:
            httpGet:
              path: /health/ready
              port: 8000
            initialDelaySeconds: 5
            periodSeconds: 5
            failureThreshold: 3

          startupProbe:
            httpGet:
              path: /health/startup
              port: 8000
            initialDelaySeconds: 0
            periodSeconds: 5
            failureThreshold: 30  # 150 seconds max startup time
```

### 43.3 Docker Compose Health Checks

```yaml
# docker-compose.yml

services:
  api:
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health/ready"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  postgres:
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5

  pgbouncer:
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -h localhost -p 6432"]
      interval: 10s
      timeout: 5s
      retries: 5
    depends_on:
      postgres:
        condition: service_healthy
```

## 44. Audit Response Summary (Final)

| Audit Gap | Section | Status |
|-----------|---------|--------|
| Object storage | 29 | S3 bucket structure, asset registry, upload service |
| Asset cleanup | 39 | Deletion triggers, background worker, S3 lifecycle |
| System logging | 30 | Structured logs, audit logs, observability |
| Email white-labeling | 31 | Custom domain, DKIM verification |
| Migration conflict | 32 | Unified single migration path with rollback |
| Membership schema | 33 | Surrogate ID, constraints, owner enforcement |
| RBAC enforcement | 34 | Complete scope→role matrix, middleware |
| Workspace context | 35 | URL is canonical, header deprecated |
| Usage atomicity | 36 | Transactions, row locks, idempotency keys |
| Agency entity | 37 | Account table, tier limit enforcement |
| Telemetry privacy | 38 | Consent, retention, anonymization |
| Super-admin audit | 30.5 | Audit logging, user notification |
| Push notifications | 40 | Web Push, service worker, VAPID |
| Template marketplace | 41 | Schema for future community sharing |
| Error handling | 42 | Standard codes, retry policies, circuit breaker |
| Health checks | 43 | Liveness, readiness, startup probes |

## 45. Complete Table Summary

### 45.1 New Tables (27 total)

| # | Table | Purpose | Section |
|---|-------|---------|---------|
| 1 | `accounts` | Agency/billing entity | 37 |
| 2 | `subscription_tiers` | Tier definitions | 12 |
| 3 | `account_subscriptions` | Account subscriptions | 12 |
| 4 | `usage_tracking` | Per-period usage metrics | 13 |
| 5 | `credit_reservations` | Idempotent credit tracking | 36 |
| 6 | `billing_events` | Stripe webhook events | 14 |
| 7 | `invoices` | Invoice records | 14 |
| 8 | `workspace_memberships` | User↔Workspace with surrogate PK | 33 |
| 9 | `post_assignment_history` | Assignment audit trail | 15 |
| 10 | `approval_stages` | Workflow stage config | 16 |
| 11 | `approval_requests` | Pending approvals | 16 |
| 12 | `approval_comments` | Review feedback | 16 |
| 13 | `notifications` | In-app notifications | 17 |
| 14 | `notification_preferences` | User preferences | 17 |
| 15 | `email_queue` | Outbound email queue | 17 |
| 16 | `push_subscriptions` | Web Push subscriptions | 40 |
| 17 | `api_keys` | API authentication | 18 |
| 18 | `webhooks` | Webhook configs | 18 |
| 19 | `webhook_deliveries` | Delivery attempts | 18 |
| 20 | `rate_limit_buckets` | Rate limiting | 18 |
| 21 | `whitelabel_config` | Branding settings | 19 |
| 22 | `system_templates` | Global/workspace templates | 23 |
| 23 | `active_sessions` | Session tracking for revocation | 24 |
| 24 | `assets` | Uploaded file registry (S3) | 29 |
| 25 | `asset_deletions` | Pending S3 cleanup queue | 39 |
| 26 | `audit_logs` | Security and admin actions | 30 |
| 27 | `marketplace_templates` | Community templates (future) | 41 |

### 45.2 Modified Tables

| Table | New Columns | Section |
|-------|-------------|---------|
| `users` | `is_superuser`, `telemetry_consent` | 8, 38 |
| `workspaces` | `account_id`, `telemetry_enabled` | 37, 38 |
| `posts` | `assignee_id`, `due_date`, `priority`, `estimated_hours`, `actual_hours` | 15 |
| `whitelabel_config` | `email_domain`, `email_from_name`, `email_reply_to`, `email_domain_verified`, `dkim_selector`, `dkim_public_key` | 31 |
| `telemetry_events` | `is_anonymized` | 38 |

### 45.3 Removed/Renamed Tables

| Original | New Name | Reason |
|----------|----------|--------|
| `workspace_users` | `workspace_memberships` | Surrogate PK needed for FK references |

## 46. Implementation Phases (Final)

### Phase 1: Database Foundation (Week 1-2)
- [ ] Set up PostgreSQL + PgBouncer in Docker
- [ ] Create Alembic migration framework
- [ ] Create `accounts`, `workspaces`, `workspace_memberships` tables
- [ ] Create `users` table with auth fields
- [ ] Run unified SQLite → Postgres migration
- [ ] Verify data integrity post-migration

### Phase 2: Authentication & RBAC (Week 3-4)
- [ ] Implement JWT auth with `active_sessions`
- [ ] Create session validation middleware
- [ ] Implement RBAC scope system
- [ ] Create `require_scope()` decorator
- [ ] Build Login/Register/Invite flows
- [ ] Add workspace context middleware (URL-based)

### Phase 3: Frontend Integration (Week 5-6)
- [ ] Implement `/w/{workspaceId}/...` route structure
- [ ] Build WorkspaceContext provider
- [ ] Create WorkspaceSwitcher component
- [ ] Implement `usePermission()` hook
- [ ] Build Team Settings page
- [ ] Build Auth pages (Login, Register, Invite)

### Phase 4: Subscription & Usage (Week 7-8)
- [ ] Create `subscription_tiers`, `account_subscriptions` tables
- [ ] Create `usage_tracking`, `credit_reservations` tables
- [ ] Implement UsageService with transactional locking
- [ ] Add enforcement middleware
- [ ] Create usage display component in sidebar
- [ ] Add upgrade prompts when limit reached

### Phase 5: Billing Integration (Week 9-10)
- [ ] Stripe SDK integration
- [ ] Checkout session creation
- [ ] Customer portal for subscription management
- [ ] Idempotent webhook handler
- [ ] Trial period logic (14-day Team trial)
- [ ] Invoice history page
- [ ] Overage billing calculation

### Phase 6: Assignment & Approvals (Week 11-12)
- [ ] Add assignment columns to posts
- [ ] Create assignment history table
- [ ] Create `approval_stages`, `approval_requests`, `approval_comments` tables
- [ ] Implement ApprovalService
- [ ] Update Kanban with assignee filters
- [ ] Workload visualization

### Phase 7: Notifications (Week 13)
- [ ] Create `notifications`, `notification_preferences`, `email_queue` tables
- [ ] Implement NotificationService
- [ ] Email queue with SendGrid/Resend
- [ ] Real-time notifications via WebSocket
- [ ] Web Push with Service Worker
- [ ] Notification preferences UI

### Phase 8: Object Storage & Assets (Week 14)
- [ ] Set up S3/MinIO
- [ ] Create `assets`, `asset_deletions` tables
- [ ] Implement AssetService with upload validation
- [ ] Background cleanup worker
- [ ] S3 lifecycle rules

### Phase 9: API & Webhooks (Week 15)
- [ ] API key generation and auth
- [ ] Rate limiting middleware with circuit breaker
- [ ] Webhook configuration UI
- [ ] Webhook delivery system with retries
- [ ] API documentation (OpenAPI)

### Phase 10: White-labeling (Week 16-17)
- [ ] Create `whitelabel_config` table with email fields
- [ ] Custom domain verification
- [ ] DKIM key generation
- [ ] Theme customization UI
- [ ] Client portal routes
- [ ] Email sending with custom domain

### Phase 11: Observability & Ops (Week 18)
- [ ] Structured logging with structlog
- [ ] `audit_logs` table and service
- [ ] Health check endpoints
- [ ] Prometheus/Datadog metrics
- [ ] Backup verification scripts
- [ ] Runbook documentation

### Phase 12: Polish & Launch (Week 19-20)
- [ ] Load testing (k6/Locust)
- [ ] Security audit
- [ ] Error handling standardization
- [ ] Privacy settings UI
- [ ] Monitoring dashboards
- [ ] Gradual rollout
