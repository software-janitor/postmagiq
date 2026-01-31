# Postmagiq — Product Audit

> AI-powered content generation platform with multi-agent workflow orchestration, voice learning, cross-platform analytics, and team collaboration.

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Problem Statement](#problem-statement)
3. [Solution Overview](#solution-overview)
4. [Core Features](#core-features)
5. [Platform Architecture](#platform-architecture)
6. [Workflow Orchestration](#workflow-orchestration)
7. [Data Model](#data-model)
8. [Subscription Tiers](#subscription-tiers)
9. [API Reference](#api-reference)
10. [Competitive Landscape](#competitive-landscape)
11. [Roadmap](#roadmap)
12. [Risks & Mitigations](#risks--mitigations)
13. [Key Metrics](#key-metrics)

---

## Executive Summary

Postmagiq is a multi-tenant SaaS platform for AI-powered LinkedIn content creation and distribution. It uses a sophisticated workflow orchestration engine with multiple AI agents powered by Groq's fast LPU inference, working through a finite state machine to generate, audit, and refine professional content.

**Core Philosophy:** AI as a collaborative system with specialized agents, not a "magic generator" — preserving authentic user voice while leveraging AI capabilities.

**Key Differentiators:**
- Multi-agent orchestration with quality gates
- Voice profile learning from writing samples
- Voice/YouTube transcription input
- Cross-platform analytics (LinkedIn, X, Threads, Medium)
- Team approval workflows
- Circuit breaker safety limits on AI spending

---

## Problem Statement

| Pain Point | Impact |
|------------|--------|
| **Generic AI content** | AI-generated posts lack authentic voice, feel robotic |
| **No quality control** | Single-shot generation produces inconsistent results |
| **Voice inconsistency** | Content doesn't match creator's established tone |
| **Manual revision loops** | Hours spent editing AI output to sound human |
| **No team workflow** | Solo creators can't scale with collaborators |
| **Cost unpredictability** | AI API costs can spiral without limits |

### Target Users (MVP Focus: B2B Thought Leaders)

| Segment | Characteristics | Why Ideal |
|---------|-----------------|-----------|
| **B2B Thought Leaders** | LinkedIn-heavy, building authority | High willingness to pay, clear ROI |
| Consultants/Coaches | Personal brand = business | Need consistent, professional voice |
| Founders/Executives | Time-constrained, high standards | Value quality over quantity |

---

## Solution Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    POSTMAGIQ PLATFORM                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  CONTENT CREATION                      ANALYTICS                │
│  ─────────────────                     ─────────                │
│                                                                 │
│   ┌───────────┐  ┌───────────┐        ┌───────────────────┐    │
│   │  Voice    │  │ YouTube/  │        │  LinkedIn  │ X    │    │
│   │  Profile  │  │  Audio    │        │  Threads   │Medium│    │
│   └─────┬─────┘  └─────┬─────┘        └─────────┬─────────┘    │
│         │              │                        │               │
│         └──────┬───────┘                        │               │
│                ▼                                ▼               │
│   ┌─────────────────────────┐     ┌─────────────────────────┐  │
│   │  Workflow Orchestrator  │     │   Analytics Dashboard   │  │
│   │  (Finite State Machine) │     │   (Cross-Platform)      │  │
│   └───────────┬─────────────┘     └─────────────────────────┘  │
│               │                                                 │
│               ▼                                                 │
│   ┌─────────────────────────────────────────────┐              │
│   │              GROQ API (Fast LPU)            │              │
│   │  ┌─────────┐ ┌─────────┐ ┌─────────┐       │              │
│   │  │GPT-OSS  │ │Llama 70B│ │GPT-OSS  │       │              │
│   │  │  120B   │ │         │ │  20B    │       │              │
│   │  │(Review, │ │(Draft)  │ │(Draft)  │       │              │
│   │  │Synth)   │ │         │ │         │       │              │
│   │  └─────────┘ └─────────┘ └─────────┘       │              │
│   └─────────────────────────────────────────────┘              │
│               │                                                 │
│               ▼                                                 │
│   ┌─────────────────────────┐                                  │
│   │   Split Audit Gates     │                                  │
│   │   • Fabrication Check   │                                  │
│   │   • Style Check         │                                  │
│   │   Pass → Next Stage     │                                  │
│   │   Fail → Revise Loop    │                                  │
│   └─────────────────────────┘                                  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Core Features

### 1. Voice Profile Learning

| Feature | Description |
|---------|-------------|
| **Writing sample analysis** | Upload existing posts/articles to extract voice patterns |
| **Tone detection** | Identifies formal/casual, authoritative/conversational style |
| **Signature phrases** | Captures recurring expressions and vocabulary |
| **Avoid patterns** | Learns what NOT to say based on examples |
| **Multiple profiles** | Different voices for different content types |

**How It Works:**
```
Upload Samples → AI Analysis → Voice Profile Generated
     ↓                              ↓
"Your writing is direct, uses short paragraphs,
 avoids jargon, frequently uses 'Here's the thing:'"
```

### 2. Content Strategy Management

| Feature | Description |
|---------|-------------|
| **Goals** | Define positioning, signature thesis, target audience |
| **Chapters** | Organize content into themed series (e.g., 4-week sprints) |
| **Posts** | Individual content pieces linked to strategy |
| **Series types** | Daily tips, weekly deep-dives, campaign bursts |

### 3. Voice & YouTube Transcription

| Feature | Description | Tier |
|---------|-------------|------|
| **Audio upload** | Transcribe voice memos, recordings | All tiers |
| **YouTube URL** | Extract and transcribe video audio | Pro+ |
| **Transcription → Draft** | Feed transcript into content workflow | All tiers |

**Use Case:** Record a voice memo with rough ideas → transcribe → generate polished LinkedIn post in your voice.

### 4. Multi-Agent Workflow Orchestration

All agents powered by **Groq API** (fast LPU inference).

#### Workflow Stages

| Stage | Purpose |
|-------|---------|
| **Story Review** | Check story completeness, ask clarifying questions |
| **Story Process** | Extract 5 elements, determine narrative shape |
| **Draft** | Generate multiple drafts in parallel (fan-out) |
| **Cross-Audit** | Split audit: fabrication check + style check |
| **Synthesize** | Combine best elements from drafts |
| **Final Audit** | Final quality check on synthesized post |
| **Human Approval** | User reviews and approves or requests changes |

#### Tier-Based Agent Configuration

| Component | Free Tier | Premium Tier (Starter/Pro/Business) |
|-----------|-----------|-------------------------------------|
| **Draft Agents** | GPT-OSS 20B, Llama 8B (2 agents) | GPT-OSS 120B, Llama 70B, GPT-OSS 20B (3 agents) |
| **Auditors** | GPT-OSS 20B, Llama 8B | GPT-OSS 120B (both) |
| **Orchestrator** | GPT-OSS 20B | GPT-OSS 120B |
| **Cost/Run** | ~$0.10 max (10 credits) | ~$0.50 max (50 credits) |
| **Timeout** | 15 min | 30 min |
| **Retries** | 1 | 2 |

### 5. Team Collaboration

| Feature | Description |
|---------|-------------|
| **Workspaces** | Isolated tenant environments |
| **Roles** | Owner, Admin, Editor, Viewer |
| **Approval workflows** | Route content for review before publishing |
| **Comments** | Inline feedback on draft content |
| **Notifications** | Alert team members on actions |

### 6. Cross-Platform Analytics

Import and analyze post performance across all your social platforms in one place.

#### Data Collection Methods

| Platform | Import Method | Refresh |
|----------|---------------|---------|
| **LinkedIn** | CSV upload (Creator Analytics export) | Manual |
| **X** | OAuth connection | Automated |
| **Threads** | OAuth connection | Automated |
| **Medium** | Copy-paste stats table | Manual |

#### Metrics Tracked

| Metric | LinkedIn | X | Threads | Medium |
|--------|----------|---|---------|--------|
| Impressions/Views | ✅ | ✅ | ❌ | ✅ |
| Likes/Reactions | ✅ | ✅ | ✅ | ✅ (claps) |
| Comments/Replies | ✅ | ✅ | ✅ | ✅ |
| Shares/Reposts | ✅ | ✅ | ✅ | ❌ |
| Clicks | ✅ | ✅ | ❌ | ❌ |
| Read time/ratio | ❌ | ❌ | ❌ | ✅ |
| Engagement rate | ✅ | ✅ | ✅ | ✅ |

#### Analytics Features

| Feature | Description |
|---------|-------------|
| **Top performing posts** | Ranked by engagement, impressions, or custom metric |
| **Daily metrics** | Time series of impressions, engagements, followers |
| **Follower growth** | Track new followers and total count over time |
| **Audience demographics** | Job title, location, industry, seniority breakdown |
| **Post demographics** | Per-post audience composition |
| **Aggregate summary** | Overall performance across all platforms |

#### Self-Benchmarking

Every metric shows context vs. your own performance:
- Value vs. your 30-day average
- Trend indicator (↑ up / ↓ down / → flat)
- Percentile rank within your own content

**Example:** "1,200 impressions (↑ 40% vs. your average)"

### 7. Run History & Cost Tracking

| Feature | Description |
|---------|-------------|
| **Run history** | View all workflow executions |
| **State log** | See each transition in the state machine |
| **Token usage** | Track tokens consumed per agent |
| **Cost breakdown** | Dollar cost per run and cumulative |

---

## Platform Architecture

### Technology Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | React 18 + TypeScript + Vite |
| **State Management** | Zustand + React Query |
| **Styling** | TailwindCSS + shadcn/ui |
| **API** | FastAPI + Pydantic |
| **ORM** | SQLModel (SQLAlchemy) |
| **Database** | PostgreSQL 16 + pgvector |
| **Cache** | Redis 7 |
| **Connection Pool** | PgBouncer |
| **Auth** | JWT + bcrypt |
| **LLM APIs** | Groq (GPT-OSS, Llama), Whisper |
| **Audio** | Groq Whisper API, yt-dlp |
| **Containerization** | Docker Compose |
| **Testing** | pytest, Playwright |

### System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         FRONTEND                                │
│                    React / Vite / Tailwind                      │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                          API LAYER                              │
│                   FastAPI / Python / REST + WebSocket           │
├─────────────────────────────────────────────────────────────────┤
│  • Auth (JWT + OAuth flows)                                     │
│  • Workflow execution                                           │
│  • Voice profile management                                     │
│  • Transcription services                                       │
└─────────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│   PostgreSQL    │  │     Redis       │  │    Groq API     │
│   + pgvector    │  │   (cache/jobs)  │  │  GPT-OSS/Llama  │
│                 │  │                 │  │    Whisper      │
└─────────────────┘  └─────────────────┘  └─────────────────┘
```

---

## Workflow Orchestration

### State Machine Model

```
┌───────┐   ┌────────────┐   ┌─────────────┐   ┌───────┐   ┌─────────────┐
│ start │──▶│story-review│──▶│story-process│──▶│ draft │──▶│ cross-audit │
└───────┘   └─────┬──────┘   └─────────────┘   └───────┘   └──────┬──────┘
                  │                                 ▲              │
                  ▼ (questions)                    │              ▼
            ┌─────────────┐                        │        ┌────────────┐
            │story-feedback│────────────────────────┘        │ synthesize │
            └─────────────┘                                  └─────┬──────┘
                                                                   │
    ┌──────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────┐   ┌────────────────────┐   ┌────────────────┐   ┌──────────┐
│ final-audit │──▶│ human-approval     │──▶│    complete    │   │   halt   │
└──────┬──────┘   │ (approve/feedback) │   └────────────────┘   └──────────┘
       │          └────────────────────┘
       ▼ (issues)
┌────────────────────┐
│final-audit-feedback│
└────────────────────┘
```

### State Types

| Type | Behavior |
|------|----------|
| `initial` | Entry point, no agent execution |
| `fan-out` | Run multiple agents in parallel |
| `single` | Run one agent (quality gates) |
| `orchestrator-task` | Agent with session persistence |
| `human-approval` | Pause for user input |
| `terminal` | Exit point |

### Circuit Breaker Safety Limits

| Limit | Free Tier | Premium Tier |
|-------|-----------|--------------|
| State visits | 2 per state | 3 per state |
| Total transitions | 15 (soft) / 20 (hard) | 20 (soft) / 50 (hard) |
| Runtime | 15 min (soft) / 30 min (hard) | 30 min (soft) / 60 min (hard) |
| Cost | $0.10 (soft) / $0.20 (hard) | $0.50 (soft) / $1.00 (hard) |

These limits prevent runaway loops and unexpected API costs.

### Agent Configuration

All production agents use Groq API for fast inference.

| Model | Size | Use Case | Tiers |
|-------|------|----------|-------|
| **GPT-OSS 120B** | 120B params | Story review, synthesis, premium drafts | Premium |
| **Llama 70B** | 70B params | Premium drafts | Premium |
| **GPT-OSS 20B** | 20B params | Free tier orchestrator, drafts | All |
| **Llama 8B** | 8B params | Free tier drafts, audits | Free |
| **Whisper** | — | Audio/YouTube transcription | All |

**Alternative Configurations (Development):**
- **Ollama** — Local inference, zero API cost, for testing
- **Claude** — Premium quality, higher cost (reserved for future premium tier)

---

## Data Model

### Core Entities

| Entity | Purpose |
|--------|---------|
| **User** | Authenticated user account |
| **Workspace** | Multi-tenant isolation unit |
| **WorkspaceMembership** | User-workspace relationship with role |
| **Goal** | Content strategy definition |
| **Chapter** | Themed content grouping |
| **Post** | Individual content piece |
| **VoiceProfile** | Learned writing voice |
| **WritingSample** | Input text for voice learning |
| **WorkflowRun** | Execution record |
| **WorkflowOutput** | Agent outputs per state |
| **ApprovalRequest** | Content review workflow |

### Entity Relationships

```
User ──────┬──────▶ Workspace
           │            │
           │            ├──▶ Goal ──▶ Chapter ──▶ Post
           │            │
           │            ├──▶ VoiceProfile
           │            │
           │            ├──▶ WorkflowRun ──▶ WorkflowOutput
           │            │
           │            └──▶ ApprovalRequest
           │
           └──▶ WorkspaceMembership
```

---

## Subscription Tiers

| Feature | Free | Starter | Pro | Business |
|---------|------|---------|-----|----------|
| Workflow runs/month | 10 | 50 | Unlimited | Unlimited |
| Voice profiles | 1 | 3 | Unlimited | Unlimited |
| Voice transcription | Yes | Yes | Yes | Yes |
| YouTube transcription | No | No | Yes | Yes |
| Team members | 1 | 3 | 10 | Unlimited |
| Approval workflows | No | Yes | Yes | Yes |
| API access | No | Yes | Yes | Yes |
| Webhooks | No | No | Yes | Yes |
| White-label | No | No | No | Yes |
| Priority support | No | No | Yes | Yes |

---

## API Reference

### Authentication

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/v1/auth/register` | POST | Register new user |
| `/v1/auth/login` | POST | Login, get JWT |
| `/v1/auth/me` | GET | Current user profile |
| `/v1/auth/me/flags` | GET | Feature flags for user |

### Workspace-Scoped Endpoints (`/v1/w/{workspace_id}/`)

#### Content Management

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/goals` | GET, POST | List/create content strategies |
| `/goals/{id}` | PUT, DELETE | Update/delete strategy |
| `/chapters` | GET, POST | List/create chapters |
| `/posts` | GET, POST | List/create posts |
| `/posts/{id}` | PUT, DELETE | Update/delete post |
| `/finished-posts` | GET | List completed posts |
| `/finished-posts/{id}/publish` | POST, DELETE | Mark published/unpublished |

#### Voice & Transcription

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/voice-profiles` | GET, POST | List/create voice profiles |
| `/voice-profiles/{id}` | PUT, DELETE | Update/delete profile |
| `/voice/samples` | GET, POST | List/save writing samples |
| `/voice/analyze` | POST | Auto-generate voice profile from samples |
| `/transcribe/upload` | POST | Transcribe uploaded audio |
| `/transcribe/youtube` | POST | Transcribe YouTube video (Pro+) |

#### Analytics

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/analytics/import` | POST | Import CSV/XLS analytics file |
| `/analytics/imports` | GET | List analytics imports |
| `/analytics/metrics` | GET | Get post metrics |
| `/analytics/top-posts` | GET | Get top performing posts |
| `/analytics/summary` | GET | Aggregate analytics summary |
| `/analytics/daily` | GET | Daily metrics time series |
| `/analytics/followers` | GET | Follower growth data |
| `/analytics/demographics` | GET | Audience demographics |

#### Team & Approvals

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/members` | GET, POST | List/add workspace members |
| `/members/{id}/role` | PUT | Update member role |
| `/approval-requests` | GET, POST | List/create approval requests |
| `/approval-requests/{id}/approve` | POST | Approve content |
| `/approval-requests/{id}/reject` | POST | Reject content |
| `/approval-requests/{id}/comments` | POST | Add comment |

#### Billing

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/billing/subscription` | GET | Current subscription |
| `/billing/checkout` | POST | Create checkout session |
| `/billing/invoices` | GET | List invoices |
| `/usage` | GET | Current usage/credits |

### Workflow Execution

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/runs` | GET | List all workflow runs |
| `/api/runs/{id}` | GET | Run details |
| `/api/runs/{id}/states` | GET | State transition log |
| `/api/runs/{id}/tokens` | GET | Token usage breakdown |
| `/api/runs/{id}/artifacts` | GET | Output artifacts |
| `/api/runs/{id}/stream` | WebSocket | Real-time execution stream |

---

## Competitive Landscape

| Competitor | Approach | Weakness |
|------------|----------|----------|
| **ChatGPT/Claude direct** | Single-shot generation | No quality control, no voice learning |
| **Jasper** | Template-based AI content | Generic output, expensive |
| **Copy.ai** | Marketing copy focus | Not optimized for thought leadership |
| **Typefully** | Scheduling + light AI | AI is secondary feature |
| **Taplio** | LinkedIn-specific | Template-heavy, less voice customization |

### Our Differentiation

1. **Multi-agent orchestration** — not single-shot generation
2. **Voice profile learning** — content sounds like you, not AI
3. **Quality gates** — audit stage catches bad outputs before you see them
4. **Cross-platform analytics** — see what's working across LinkedIn, X, Threads, Medium
5. **Circuit breakers** — cost predictability with hard limits
6. **Team workflows** — scale content with collaborators

---

## Roadmap

### Current (Shipped)

- [x] Multi-agent workflow orchestration
- [x] Voice profile learning from samples
- [x] Voice transcription (audio upload)
- [x] YouTube transcription (Pro+)
- [x] Cross-platform analytics (LinkedIn, X, Threads, Medium)
- [x] Analytics import (CSV, OAuth, copy-paste)
- [x] Audience demographics tracking
- [x] Team workspaces with roles
- [x] Approval workflows
- [x] Run history with cost tracking
- [x] Subscription tiers with Stripe

### Near-Term

- [ ] Content calendar view
- [ ] Posting frequency analytics
- [ ] Goal progress tracking
- [ ] Batch content generation
- [ ] Webhook integrations

### Future

- [ ] Direct LinkedIn publishing (OAuth)
- [ ] A/B testing for post variants
- [ ] Audience engagement analytics
- [ ] Browser extension for research capture
- [ ] Mobile app

---

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| **LLM API price changes** | Medium | High | Multi-provider support, Ollama fallback |
| **LLM quality degradation** | Medium | High | Audit stage catches bad outputs |
| **Cost overruns** | Low | Medium | Circuit breaker hard limits |
| **Voice profile inaccuracy** | Medium | Medium | Allow manual tuning, more samples |
| **LinkedIn API access** | High | Medium | Manual copy-paste MVP, pursue partnership |
| **Competitor catches up** | High | Medium | Focus on voice differentiation |

---

## Key Metrics

### Product Metrics (Hypotheses to Validate)

| Metric | Target | Rationale |
|--------|--------|-----------|
| **Activation** | 50%+ create voice profile in first session | Voice is core differentiator |
| **Weekly active** | 60%+ of paid users | Content creation is recurring need |
| **Runs per user/week** | 3+ | Healthy engagement |
| **Audit pass rate** | 70%+ | Quality gate is working |
| **Time to first post** | <10 min | Fast time to value |

### Business Metrics (Hypotheses to Validate)

| Metric | Target | Rationale |
|--------|--------|-----------|
| **Trial → Paid** | 10%+ | Standard SaaS benchmark |
| **Monthly churn** | <8% | Early-stage acceptable |
| **NPS** | >30 | Early product, room to grow |
| **Avg revenue/user** | $30+ | Sustainable unit economics |

---

## Summary

Postmagiq solves the core problem with AI content: **it sounds like AI, not like you** — and shows you what's actually working.

**What We Do:**
1. Learn your voice from existing writing
2. Generate drafts with multiple AI agents in parallel
3. Audit quality before you ever see the output
4. Synthesize the best elements into final content
5. Track performance across LinkedIn, X, Threads, and Medium
6. Support team review and approval workflows

**What We Don't Do:**
- Single-shot "generate and hope" content
- Generic templates that sound like everyone else
- Unbounded AI costs with no safety limits
- Force you to check 4 different dashboards

**Bottom Line:** Multi-agent orchestration + voice learning + quality gates + cross-platform analytics = content that sounds like you wrote it, at scale, with data to prove what works.
