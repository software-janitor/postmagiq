# Plan: Business Tier Upgrade Flow

> Show team onboarding when upgrading from individual tier to Business.

---

## Goal

When a user upgrades from Free/Starter/Pro to Business tier, guide them through setting up their team workspace. This is the moment when multi-tenancy becomes visible.

---

## Current State

- Users can see tier comparison in Settings
- "Upgrade" button exists but is non-functional
- No post-upgrade flow exists
- Workspace features hidden for individual tiers

---

## Target State

| Step | User Experience |
|------|-----------------|
| 1. Click Upgrade | Opens billing/payment modal |
| 2. Payment success | Redirects to team onboarding |
| 3. Team onboarding | Name workspace, invite members |
| 4. Complete | Workspace UI becomes visible |

---

## Implementation Plan

### Phase 1: Upgrade Button Flow

**File:** `gui/src/pages/Settings.tsx`

- [ ] Wire up "Upgrade" button to open payment modal
- [ ] Pass selected tier to payment flow
- [ ] Handle payment success callback

**File:** `gui/src/components/UpgradeModal.tsx` (new)

- [ ] Create modal for tier selection
- [ ] Show price comparison
- [ ] Integrate with Stripe checkout or billing API

---

### Phase 2: Payment Integration

**Files:**
- `api/routes/v1/billing.py`
- `api/services/billing_service.py`

- [ ] Create checkout session endpoint
- [ ] Handle Stripe webhook for successful payment
- [ ] Update workspace subscription tier
- [ ] Set `team_workspaces` feature flag to true

**Stripe flow:**
```
User clicks Upgrade
  → POST /v1/w/{id}/billing/checkout
  → Redirect to Stripe Checkout
  → Stripe webhook: payment_intent.succeeded
  → Update subscription tier
  → Redirect to /onboarding/team
```

---

### Phase 3: Team Onboarding Page

**File:** `gui/src/pages/onboarding/TeamSetup.tsx` (new)

**Step 1: Workspace Setup**
- [ ] Rename workspace (from "Personal" to team name)
- [ ] Optional: Upload workspace logo
- [ ] Optional: Set workspace description

**Step 2: Invite Members**
- [ ] Email input for inviting team members
- [ ] Role selector (Admin, Editor, Viewer)
- [ ] "Skip for now" option
- [ ] Send invite emails

**Step 3: Complete**
- [ ] Success message
- [ ] Redirect to dashboard
- [ ] Show workspace switcher in sidebar

---

### Phase 4: Post-Upgrade State Changes

**Backend changes:**

- [ ] Update user's feature flags after upgrade
- [ ] Enable `team_workspaces` feature
- [ ] Increase limits (credits, storage, etc.)

**Frontend changes:**

- [ ] Invalidate feature flags cache
- [ ] Show workspace switcher in sidebar
- [ ] Show Team nav item
- [ ] Update Settings to show new tier

---

## API Endpoints

### New Endpoints

```
POST /v1/w/{workspace_id}/billing/checkout
  Request: { tier_slug: "business", billing_period: "monthly" | "yearly" }
  Response: { checkout_url: "https://checkout.stripe.com/..." }

POST /v1/w/{workspace_id}/billing/webhook
  Stripe webhook handler

PUT /v1/w/{workspace_id}/setup
  Request: { name: "Acme Inc", description?: string }
  Response: { workspace: Workspace }

POST /v1/w/{workspace_id}/members/bulk-invite
  Request: { invites: [{ email: string, role: string }] }
  Response: { sent: number, failed: string[] }
```

---

## Frontend Routes

```tsx
// gui/src/router.tsx

{ path: '/onboarding/team', element: <TeamSetup /> }
{ path: '/onboarding/team/invite', element: <TeamInvite /> }
{ path: '/onboarding/team/complete', element: <TeamComplete /> }
```

---

## Components

### UpgradeModal

```tsx
interface UpgradeModalProps {
  isOpen: boolean
  onClose: () => void
  currentTier: string
  onUpgradeComplete: () => void
}
```

### TeamSetup

```tsx
// Multi-step form
const steps = [
  { id: 'workspace', title: 'Name Your Workspace' },
  { id: 'invite', title: 'Invite Your Team' },
  { id: 'complete', title: 'You\'re All Set!' },
]
```

---

## Database Changes

None required - existing schema supports all needed operations.

---

## Feature Flag Updates

After successful upgrade:

```python
# api/services/tier_service.py

def apply_business_tier_features(workspace_id: UUID):
    """Enable Business tier features after upgrade."""
    # Update subscription
    subscription.tier_id = business_tier.id

    # Features now available:
    # - team_workspaces: true
    # - api_access: true
    # - priority_support: true
    # - Higher credit limits
```

---

## Testing Checklist

- [ ] Upgrade button opens payment modal
- [ ] Stripe checkout redirects correctly
- [ ] Webhook updates subscription tier
- [ ] Redirect to team onboarding after payment
- [ ] Workspace rename persists
- [ ] Invites are sent successfully
- [ ] Feature flags update after upgrade
- [ ] Sidebar shows workspace switcher post-upgrade
- [ ] Team nav item appears post-upgrade
- [ ] Settings shows new tier
- [ ] Downgrade path works (hides UI, keeps data)

---

## Error Handling

| Scenario | Handling |
|----------|----------|
| Payment fails | Show error, stay on Settings |
| Webhook timeout | Retry logic, manual reconciliation |
| Invite email fails | Show partial success, retry option |
| User closes onboarding early | Resume on next login |

---

## Analytics Events

```typescript
// Track upgrade funnel
analytics.track('upgrade_started', { from_tier, to_tier })
analytics.track('payment_completed', { tier, amount })
analytics.track('team_setup_started')
analytics.track('team_invites_sent', { count })
analytics.track('team_setup_completed')
analytics.track('team_setup_skipped')
```

---

## Files to Create

| File | Purpose |
|------|---------|
| `gui/src/components/UpgradeModal.tsx` | Tier selection & payment trigger |
| `gui/src/pages/onboarding/TeamSetup.tsx` | Team onboarding wizard |
| `api/routes/v1/checkout.py` | Stripe checkout endpoints |

## Files to Modify

| File | Changes |
|------|---------|
| `gui/src/pages/Settings.tsx` | Wire upgrade button |
| `gui/src/router.tsx` | Add team onboarding routes |
| `gui/src/stores/flagsStore.ts` | Invalidate on upgrade |
| `api/services/billing_service.py` | Add checkout logic |
| `api/routes/v1/billing.py` | Add checkout endpoint |

---

## Open Questions

1. **Stripe or in-app billing?**
   - Stripe Checkout is simpler
   - In-app requires more UI work but better UX

2. **What if user skips team setup?**
   - Option A: Nag on next login
   - Option B: Let them access features, remind later
   - Recommendation: Option B

3. **Downgrade handling?**
   - Keep workspace data, just hide UI
   - Don't delete team members
   - Show "reactivate" prompt

4. **Trial period?**
   - Consider 14-day Business trial
   - No payment required upfront
   - Converts to paid or downgrades

---

## Estimated Effort

| Phase | Effort |
|-------|--------|
| Phase 1: Upgrade button | 2-3 hours |
| Phase 2: Payment integration | 4-6 hours |
| Phase 3: Team onboarding | 4-5 hours |
| Phase 4: State changes | 2-3 hours |
| Testing | 2-3 hours |
| **Total** | **14-20 hours** |

---

## Dependencies

- Stripe account configured
- Webhook endpoint deployed
- Email service for invites (already exists)

---

## Success Criteria

- [ ] User can upgrade from Settings in under 2 minutes
- [ ] Payment is processed securely via Stripe
- [ ] Team onboarding is optional but encouraged
- [ ] Workspace features appear immediately after upgrade
- [ ] No data loss on downgrade
