# Plan: Hide Multi-Tenancy for Individual Users

> Keep the workspace architecture but make it invisible for individual plans.

---

## Goal

Users on Free/Starter/Pro tiers should never see workspace concepts. They sign up, they use the app. Multi-tenancy only surfaces for Business/Agency tiers.

---

## Current State

- Every user belongs to a workspace
- Workspace ID is in URLs: `/w/{workspace_id}/...`
- Sidebar shows workspace name
- Team settings visible to all users
- Workspace switcher exists (even for single workspace)

---

## Target State

| Tier | Workspace Experience |
|------|---------------------|
| Free | Invisible — auto-created, never shown |
| Starter | Invisible — auto-created, never shown |
| Pro | Invisible — auto-created, never shown |
| Business | Full multi-tenancy — teams, workspaces, switcher |

---

## Implementation Plan

### Phase 1: Auto-Create Personal Workspace on Signup

**File:** `api/routers/auth.py` (or wherever registration happens)

- [ ] On user registration, auto-create workspace named "{user.name}'s Space" or just "Personal"
- [ ] Set user as owner
- [ ] Create default WorkspaceMembership
- [ ] Store `default_workspace_id` on User model (for quick lookup)

**Schema change (if needed):**
```python
# api/models/user.py
class User(SQLModel):
    ...
    default_workspace_id: UUID | None = None  # Auto-set on signup
```

**Migration:**
- [ ] Add `default_workspace_id` column to users table
- [ ] Backfill existing users with their first workspace

---

### Phase 2: Remove Workspace ID from URLs (Individual Tiers)

**Current:** `/w/{workspace_id}/goals`
**Target:** `/goals` (workspace inferred from user's default)

**Approach A: Dual routing (recommended)**
- Keep `/w/{workspace_id}/...` routes for Business tier
- Add `/...` routes that infer workspace from `current_user.default_workspace_id`
- Frontend chooses which to use based on tier

**Approach B: Always infer, keep URL for API consistency**
- URLs still have workspace_id internally
- Frontend auto-inserts it, user never sees it

**Files to modify:**
- [ ] `gui/src/lib/api.ts` — API client to auto-inject workspace_id
- [ ] `gui/src/router.tsx` — Remove workspace_id from route paths for individual tiers
- [ ] `api/routers/*.py` — Add alternate routes without workspace_id prefix

---

### Phase 3: Hide Team/Workspace UI Elements

**Sidebar changes:**
- [ ] Hide workspace name/switcher for individual tiers
- [ ] Hide "Team Settings" nav item
- [ ] Hide "Invite Members" buttons

**Files:**
- [ ] `gui/src/components/sidebar.tsx`
- [ ] `gui/src/components/workspace-switcher.tsx`

**Implementation:**
```tsx
// Use feature flag or tier check
const showTeamFeatures = subscription.tier === 'business';

{showTeamFeatures && (
  <SidebarItem href="/team-settings">Team Settings</SidebarItem>
)}
```

---

### Phase 4: Hide Workspace References in Copy

Search and replace or conditionally render:

| Current | Target (Individual) |
|---------|---------------------|
| "Workspace Settings" | "Settings" |
| "Workspace Members" | Hidden |
| "Your workspace" | "Your account" |
| "Workspace name" | Hidden |

**Files to audit:**
- [ ] `gui/src/pages/settings.tsx`
- [ ] `gui/src/pages/team-settings.tsx`
- [ ] `gui/src/components/*.tsx` — Search for "workspace"
- [ ] API error messages

---

### Phase 5: Upgrade Flow to Business Tier

When user upgrades to Business:
- [ ] Show "Create Team" onboarding flow
- [ ] Allow renaming workspace
- [ ] Show invite members UI
- [ ] Enable workspace switcher
- [ ] Allow creating additional workspaces

**Files:**
- [ ] `gui/src/pages/billing.tsx` — Post-upgrade flow
- [ ] `gui/src/pages/onboarding/team-setup.tsx` — New page

---

## API Changes Summary

### New Endpoints (Optional)

If using Approach A (dual routing):

```
# Individual tier routes (workspace inferred)
GET  /v1/goals           → uses current_user.default_workspace_id
POST /v1/posts           → uses current_user.default_workspace_id

# Business tier routes (explicit workspace)
GET  /v1/w/{workspace_id}/goals
POST /v1/w/{workspace_id}/posts
```

### Dependency Injection Change

```python
# api/dependencies.py

async def get_workspace_id(
    workspace_id: UUID | None = None,
    current_user: User = Depends(get_current_user)
) -> UUID:
    """Get workspace ID from path or user's default."""
    if workspace_id:
        # Verify user has access to this workspace
        return workspace_id
    if current_user.default_workspace_id:
        return current_user.default_workspace_id
    raise HTTPException(404, "No workspace found")
```

---

## Frontend Changes Summary

### Router Config

```tsx
// gui/src/router.tsx

const routes = [
  // Individual tier routes (no workspace in path)
  { path: '/dashboard', element: <Dashboard /> },
  { path: '/goals', element: <Goals /> },
  { path: '/posts', element: <Posts /> },

  // Business tier routes (workspace in path)
  { path: '/w/:workspaceId/dashboard', element: <Dashboard /> },
  { path: '/w/:workspaceId/goals', element: <Goals /> },
];
```

### API Client

```typescript
// gui/src/lib/api.ts

function getApiBase(): string {
  const tier = useSubscription().tier;
  const workspaceId = useWorkspace().id;

  if (tier === 'business') {
    return `/v1/w/${workspaceId}`;
  }
  return '/v1';  // Workspace inferred server-side
}
```

---

## Database Changes

### Migration: Add default_workspace_id

```python
# alembic/versions/xxx_add_default_workspace_id.py

def upgrade():
    op.add_column('users', sa.Column('default_workspace_id', sa.UUID(), nullable=True))
    op.create_foreign_key('fk_users_default_workspace', 'users', 'workspaces',
                          ['default_workspace_id'], ['id'])

    # Backfill: Set first workspace as default for existing users
    op.execute("""
        UPDATE users u
        SET default_workspace_id = (
            SELECT workspace_id FROM workspace_memberships wm
            WHERE wm.user_id = u.id
            ORDER BY wm.created_at
            LIMIT 1
        )
    """)

def downgrade():
    op.drop_constraint('fk_users_default_workspace', 'users')
    op.drop_column('users', 'default_workspace_id')
```

---

## Testing Checklist

- [ ] New user signup creates personal workspace automatically
- [ ] Free/Starter/Pro users never see "workspace" in UI
- [ ] URLs work without workspace_id for individual tiers
- [ ] Business tier users see full workspace UI
- [ ] Upgrade from Pro → Business shows team onboarding
- [ ] API works with both URL patterns
- [ ] Existing users backfilled correctly

---

## Rollout Plan

1. **Backend first:** Add default_workspace_id, dual routing
2. **Frontend feature flag:** `HIDE_WORKSPACE_UI=true`
3. **Gradual UI cleanup:** Remove workspace references
4. **Test with new signups:** Verify invisible workspace flow
5. **Backfill existing users:** Set default_workspace_id
6. **Remove feature flag:** Ship to all users

---

## Files to Modify

### Backend
- `api/models/user.py`
- `api/dependencies.py`
- `api/routers/auth.py`
- `api/routers/goals.py` (add non-workspace routes)
- `api/routers/posts.py` (add non-workspace routes)
- `alembic/versions/xxx_add_default_workspace_id.py`

### Frontend
- `gui/src/lib/api.ts`
- `gui/src/router.tsx`
- `gui/src/components/sidebar.tsx`
- `gui/src/components/workspace-switcher.tsx`
- `gui/src/pages/settings.tsx`
- `gui/src/pages/team-settings.tsx`
- `gui/src/hooks/useWorkspace.ts`

---

## Open Questions

1. **What happens when Business user downgrades?**
   - Option A: Keep workspaces, just hide UI
   - Option B: Merge all content into personal workspace
   - Recommendation: Option A (less destructive)

2. **Can individual users share content for review?**
   - Could add "share link" without full team features
   - Defer to post-MVP

3. **Naming: "Personal" workspace or user's name?**
   - "{Name}'s Space" feels friendlier
   - But user never sees it anyway for individual tiers

---

## Estimated Effort

| Phase | Effort |
|-------|--------|
| Phase 1: Auto-create workspace | 2-3 hours |
| Phase 2: URL routing | 4-6 hours |
| Phase 3: Hide UI elements | 2-3 hours |
| Phase 4: Copy cleanup | 1-2 hours |
| Phase 5: Upgrade flow | 3-4 hours |
| Testing | 2-3 hours |
| **Total** | **14-21 hours** |

---

## Success Criteria

- [ ] New user can sign up and use app without ever seeing "workspace"
- [ ] Zero references to workspaces/teams in Free/Starter/Pro UI
- [ ] Business tier users have full multi-tenancy experience
- [ ] No breaking changes to existing users
- [ ] API backwards compatible
