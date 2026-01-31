# Launch Readiness Plan

## Goals
- Make the app safe and simple for regular users while keeping full power for owner.
- Replace cost/token visibility with credits for regular users.
- Hide internal workflow mechanics and advanced tools from regular users.
- Fix signup and theme issues that block launch.

## Personas
- Owner: full access, including developer and internal views.
- Regular user: simplified UX, credit-based usage, no internal tooling.

## Feature Flags (per-user)
- `is_owner` (boolean)
- `show_internal_workflow` (boolean)
- `show_image_tools` (boolean)
- `show_ai_personas` (boolean)
- `show_live_workflow` (boolean)
- `show_state_editor` (boolean)
- `show_approvals` (boolean)
- `show_teams` (boolean)
- `show_strategy_admin` (boolean)

## Workstreams

### 1) Access + Flags Foundation
- [ ] Define user roles and per-user feature flags in backend.
- [ ] Add server-side checks and client-side gating for all flagged features.
- [ ] Add admin UI for toggling flags (owner-only).
- [ ] Default flag bundle for regular users.

### 2) Dashboard + Usage
- [ ] Dashboard: replace cost with credits consumed for regular users.
- [ ] Owner view: keep current cost-based developer view.
- [ ] Run history: for regular users show credits only; hide tokens, cost, and final state column.

### 3) Strategy + Content Plan
- [ ] Keep current Strategy/Content Plan/Analytics/Content Strategy upload as-is for regular users.
- [ ] Keep Create New Strategy as-is for regular users.

### 4) Story Workflow UX (Regular User)
- [ ] Replace workflow status bubbles with a simplified "Processing" state.
- [ ] Hide: progress bar, activity log, story review resolve, story templates, drafts, cross-audit, final audit details.
- [ ] Allow only one user response to LLM question per run.
- [ ] Final review: show "Postmagic auditor feedback" + score + suggestions; allow one revision only.
- [ ] After revision, finalize and show final post with no further review UI.

### 5) Finished Post Page
- [ ] Hide image prompt, generated prompt, and uploaded image for regular users.
- [ ] Disable image configuration entirely for regular users.
- [ ] Owner view retains all features.

### 6) Content Assets + Tools
- [ ] Disable Outfit Bank, Characters, and AI Personas for regular users.
- [ ] Gate Live Workflow page and State Editor to owner only.

### 7) Settings + Billing
- [ ] Regular users: show usage (credits), billing, payment methods, invoice history, notifications, agents, theme chooser.
- [ ] Hide personas and circuit breaker for regular users.
- [ ] Circuit breaker fixed to 1 for regular users; owner can use 3.
- [ ] Owner view shows actual costs; regular view shows credits only.

### 8) Approvals + Teams
- [ ] Disable approvals for now.
- [ ] Disable teams tab for now.

### 9) Evaluation Dashboard
- [ ] Audit what the evaluation dashboard does and document purpose.
- [ ] Decide: owner-only or remove from regular users.

### 10) Auth + Signup
- [ ] Fix user registration flow.
- [ ] Add smoke tests for signup/login and first-run onboarding.

### 11) Theme + Branding
- [ ] Ensure primary text never renders black on black.
- [ ] Audit theme defaults and fix contrast issues.

### 12) Agent Flow Updates (Secret Sauce)
- [ ] Plan rollout mechanism for agent flow updates without exposing internals.
- [ ] Decide how API-agent migration is delivered to all users.
- [ ] Ensure only owner can see agent flow details/logs.

### 13) QA + Launch Checklist
- [ ] Role-based UI audits (owner vs regular).
- [ ] Regression tests for strategy creation and story generation.
- [ ] Verify credit accounting across all user-visible pages.

## Open Questions
- How are credits calculated from cost/tokens today?
- Where are feature flags stored (user record, org, or config)?
- What is the current evaluation dashboard used for?
- Should regular users ever see any audit score breakdown details?
- Expected behavior when a regular user exceeds credits?

## Deliverables
- Feature-flagged UI and backend checks for owner vs regular users.
- Simplified story workflow for regular users.
- Fixed signup and theme contrast issues.
- Documented evaluation dashboard decision.
