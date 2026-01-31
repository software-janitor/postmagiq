# MVP UI Cleanup Audit

> Remove complexity, focus on core value: Voice learning + AI content generation.

---

## Current State

### Already Hidden (via feature flags)
| Route | Flag | Status |
|-------|------|--------|
| /workflow | show_live_workflow | Hidden for regular users |
| /editor | show_state_editor | Hidden for regular users |
| /approvals | show_approvals | Hidden for regular users |
| /team | show_teams | Hidden for non-Max tiers |
| Workspace Switcher | team_workspaces | Hidden for non-Max tiers |
| Agents (Settings) | show_internal_workflow | Hidden |
| Circuit Breaker (Settings) | show_internal_workflow | Hidden |
| Personas (Settings) | show_ai_personas | Hidden |

### Needs Hiding for MVP
| Item | Reason | Action |
|------|--------|--------|
| Run History (/runs) | Internal, users don't care | Add flag |
| Whitelabel Settings | Business only, not MVP | Hide route |
| Workflow Configuration (Settings) | Internal | Add flag |

### Keep Visible
| Route | Purpose |
|-------|---------|
| / (Dashboard) | Main overview, quick actions |
| /strategies | List of content strategies |
| /strategy | Current active strategy |
| /onboarding | Create new strategy |
| /voice | Voice sample training |
| /voice-profiles | Manage trained voices |
| /story | Generate new content |
| /finished | View/edit/publish posts |
| /settings | Usage, billing, account |
| /settings/privacy | GDPR compliance |

---

## Changes to Make

### 1. Hide Run History
```tsx
// gui/src/components/layout/Sidebar.tsx
{ path: '/runs', icon: History, label: 'Run History', flag: 'show_internal_workflow' },
```

### 2. Hide Workflow Configuration Section
```tsx
// gui/src/pages/Settings.tsx
{flags.show_internal_workflow && (
  <div>Workflow Configuration...</div>
)}
```

### 3. Hide Whitelabel Settings Route
Already internal - just ensure no navigation links to it.

---

## Simplified Navigation (MVP)

```
Dashboard
├── Strategies
│   ├── Strategy List
│   └── New Strategy
├── Voice Learning
│   ├── Train Voice
│   └── Voice Profiles
├── Content
│   ├── New Story
│   └── Finished Posts
└── Settings
    ├── Usage & Billing
    ├── Notifications
    └── Privacy
```

---

## Feature Flags Summary

| Flag | Controls | Default for Users |
|------|----------|-------------------|
| show_internal_workflow | Run History, Workflow Config, Agents, Circuit Breaker | false |
| show_live_workflow | Live Workflow page | false |
| show_state_editor | State Editor page | false |
| show_approvals | Approvals page | false |
| show_teams | Team Settings page | false (only Max tier) |
| show_ai_personas | Personas section | false |
| show_costs | Cost display | false |
| show_image_tools | Image generation | false |

---

## Post-Launch (Add When Requested)

| Feature | Add When |
|---------|----------|
| Content Calendar | Users ask "when should I post?" |
| Analytics Dashboard | Users upload analytics >3 times |
| Browser Extension | >3 complaints about CSV import |
| Team Workspaces | Agencies show interest |
| API Access | Developers ask for it |

---

## Implementation

### Files to Modify

1. **gui/src/components/layout/Sidebar.tsx**
   - Add flag to Run History nav item

2. **gui/src/pages/Settings.tsx**
   - Wrap Workflow Configuration in flag check

### Estimated Effort
- 30 minutes
