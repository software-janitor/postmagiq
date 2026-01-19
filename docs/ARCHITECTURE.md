# Postmagiq Orchestrator - Architecture Documentation

> Comprehensive codebase audit generated 2026-01-18

## Executive Summary

Postmagiq Orchestrator is a **multi-tenant SaaS platform** for AI-powered LinkedIn content creation. It orchestrates multiple AI agents (Claude, Gemini, Codex, Ollama) through a finite state machine workflow to generate, audit, and refine professional content.

**Target Audience:** Content creators, marketers, and professionals who want to maintain consistent, high-quality LinkedIn presence using AI assistance while preserving their authentic voice.

**Core Value Proposition:** Rather than treating AI as a "magic content generator," Postmagiq treats it as a collaborative system with multiple specialized agents, each with defined roles, quality gates, and human checkpoints.

---

## Table of Contents

1. [System Architecture](#system-architecture)
2. [AI Agent Infrastructure](#ai-agent-infrastructure)
3. [Workflow State Machine](#workflow-state-machine)
4. [Database Models](#database-models)
5. [API Structure](#api-structure)
6. [Frontend Architecture](#frontend-architecture)
7. [Prompt Engineering System](#prompt-engineering-system)
8. [Security & Multi-Tenancy](#security--multi-tenancy)
9. [Development & Deployment](#development--deployment)

---

## System Architecture

### High-Level Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              FRONTEND (React)                                │
│                         gui/ - Vite + TypeScript + Zustand                   │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              API LAYER (FastAPI)                             │
│                         api/ - REST + WebSocket + JWT Auth                   │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
              ┌───────────────────────┼───────────────────────┐
              ▼                       ▼                       ▼
┌─────────────────────┐  ┌─────────────────────┐  ┌─────────────────────┐
│   WORKFLOW ENGINE   │  │    DATA LAYER       │  │   EXTERNAL SERVICES │
│   runner/           │  │    PostgreSQL       │  │   - Stripe Billing  │
│                     │  │    + pgvector       │  │   - SMTP Email      │
│   - State Machine   │  │    Redis Cache      │  │   - Image Services  │
│   - Agent Invokers  │  │                     │  │                     │
│   - Circuit Breaker │  │                     │  │                     │
└─────────────────────┘  └─────────────────────┘  └─────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           AI AGENT BACKENDS                                  │
│   ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐                        │
│   │ Claude  │  │ Gemini  │  │  Codex  │  │ Ollama  │                        │
│   │  CLI    │  │   API   │  │   CLI   │  │  Local  │                        │
│   └─────────┘  └─────────┘  └─────────┘  └─────────┘                        │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Technology Stack

| Layer | Technology | Purpose |
|-------|------------|---------|
| Frontend | React 18 + TypeScript + Vite | SPA with hot reload |
| State Management | Zustand | Lightweight reactive state |
| Styling | TailwindCSS + shadcn/ui | Component library |
| API | FastAPI + Pydantic | Type-safe REST API |
| Auth | JWT + bcrypt | Stateless authentication |
| Database | PostgreSQL 16 + pgvector | Relational + vector embeddings |
| Cache | Redis 7 | Session cache, rate limiting |
| Connection Pool | PgBouncer | Database connection pooling |
| Container | Docker Compose | Service orchestration |

### Directory Structure

```
orchestrator/
├── api/                      # FastAPI backend
│   ├── main.py               # Application entry point
│   ├── routes/               # API endpoints (50+ endpoints)
│   ├── services/             # Business logic layer
│   ├── middleware/           # Auth, CORS, error handling
│   └── dependencies.py       # Dependency injection
├── runner/                   # Workflow orchestration engine
│   ├── runner.py             # CLI entry point
│   ├── state_machine.py      # FSM implementation
│   ├── circuit_breaker.py    # Safety mechanisms
│   ├── agents/               # AI agent implementations
│   ├── sessions/             # Session persistence
│   ├── metrics/              # Cost/token tracking
│   ├── logging/              # Structured logging
│   ├── content/              # Content management
│   ├── history/              # Run history queries
│   └── db/                   # Database models & migrations
├── gui/                      # React frontend
│   ├── src/
│   │   ├── pages/            # Route components
│   │   ├── components/       # Reusable UI components
│   │   ├── stores/           # Zustand state stores
│   │   ├── hooks/            # Custom React hooks
│   │   └── lib/              # Utilities & API client
│   └── e2e/                  # Playwright tests
├── prompts/                  # Persona templates
├── workflow/                 # Runtime artifacts
├── tests/                    # Test suites
└── docker-compose.yml        # Service definitions
```

---

## AI Agent Infrastructure

### Agent Types

The system supports four distinct AI backends, each with specialized use cases:

#### 1. Claude (Anthropic)

**Implementation:** `runner/agents/claude.py`

```python
class ClaudeAgent(BaseAgent):
    """Claude CLI agent with session persistence."""

    # Invocation modes:
    # - CLI: claude -p "prompt" --output-format json
    # - Resume: claude --resume {session_id} -p "prompt"
    # - Streaming: Real-time token output via PTY
```

**Characteristics:**
- Primary orchestrator for complex reasoning tasks
- Session persistence for multi-turn conversations
- Supports `--resume` for context continuity
- JSON output format for structured responses
- Cost: ~$15/1M input tokens, ~$75/1M output tokens (Opus)

#### 2. Gemini (Google)

**Implementation:** `runner/agents/gemini.py`

```python
class GeminiAgent(BaseAgent):
    """Gemini API agent with direct SDK integration."""

    # Uses google.generativeai SDK
    # Supports vision for image analysis
    # Lower cost alternative for simpler tasks
```

**Characteristics:**
- API-based (no CLI)
- Excellent for vision tasks (image analysis)
- Character creation from photos
- Cost: ~$1.25/1M input tokens (Pro)

#### 3. Codex (OpenAI)

**Implementation:** `runner/agents/codex.py`

```python
class CodexAgent(BaseAgent):
    """OpenAI Codex agent for code generation."""

    # Specialized for code-related tasks
    # Session persistence via CLI
```

**Characteristics:**
- Code generation specialist
- CLI-based with session support
- Used for technical content

#### 4. Ollama (Local)

**Implementation:** `runner/agents/ollama.py`

```python
class OllamaAgent(BaseAgent):
    """Local LLM via Ollama for privacy-sensitive tasks."""

    # Runs entirely on local hardware
    # No data leaves the machine
    # Supports llama3.2, mistral, etc.
```

**Characteristics:**
- Fully local execution
- Zero API costs
- GPU acceleration supported
- Models: llama3.2, mistral, codellama

### Agent Abstraction Layer

All agents implement a common interface:

```python
# runner/agents/base.py

class BaseAgent(ABC):
    """Abstract base class for all AI agents."""

    @abstractmethod
    def invoke(self, prompt: str, **kwargs) -> AgentResult:
        """Execute a prompt and return structured result."""
        pass

    @abstractmethod
    def get_command(self, prompt: str) -> str:
        """Build the execution command."""
        pass

@dataclass
class AgentResult:
    success: bool
    content: str
    tokens_in: int
    tokens_out: int
    cost_usd: float
    duration_seconds: float
    session_id: Optional[str]
    error: Optional[str]
```

### Agent Factory Pattern

```python
# runner/agents/factory.py

class AgentFactory:
    """Factory for creating agent instances from config."""

    _registry = {
        "claude": ClaudeAgent,
        "gemini": GeminiAgent,
        "codex": CodexAgent,
        "ollama": OllamaAgent,
    }

    @classmethod
    def create(cls, agent_type: str, config: dict) -> BaseAgent:
        agent_class = cls._registry.get(agent_type)
        return agent_class(**config)
```

### Agent Roles in Workflow

| Role | Agent | Purpose |
|------|-------|---------|
| Writer | Claude/Ollama | Initial draft generation |
| Auditor | Claude/Gemini | Quality gate evaluation |
| Synthesizer | Claude | Combine multi-agent outputs |
| Orchestrator | Claude | Complex reasoning, planning |
| Vision | Gemini | Image analysis, character extraction |

---

## Workflow State Machine

### Core Concepts

The workflow engine is a **Finite State Machine (FSM)** that orchestrates AI agents through defined states with controlled transitions.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        WORKFLOW STATE MACHINE                                │
│                                                                              │
│   ┌─────────┐     ┌─────────┐     ┌─────────┐     ┌─────────┐              │
│   │ INITIAL │────▶│  DRAFT  │────▶│  AUDIT  │────▶│  FINAL  │              │
│   └─────────┘     └─────────┘     └─────────┘     └─────────┘              │
│                         │               │                                    │
│                         │               │ (fail)                             │
│                         │               ▼                                    │
│                         │         ┌─────────┐                               │
│                         └─────────│ REVISE  │                               │
│                           (loop)  └─────────┘                               │
│                                                                              │
│   Circuit Breaker: Max 3 visits per state, 20 total transitions             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### State Types

| Type | Behavior | Example |
|------|----------|---------|
| `initial` | Entry point, no agent execution | `start` |
| `fan-out` | Parallel multi-agent execution | `draft` (3 writers) |
| `single` | Single agent with quality gate | `audit` |
| `orchestrator-task` | Persistent session agent | `synthesize` |
| `human-approval` | Pause for user input | `review` |
| `terminal` | Exit point | `complete` |

### Configuration Schema

```yaml
# workflow_config.yaml

workflow:
  name: "linkedin_post"
  initial_state: "start"

  states:
    start:
      type: initial
      transitions:
        - target: draft
          condition: always

    draft:
      type: fan-out
      agents:
        - name: writer_claude
          type: claude
          persona: writer
        - name: writer_ollama
          type: ollama
          model: llama3.2
      transitions:
        - target: audit
          condition: all_complete

    audit:
      type: single
      agent:
        name: auditor
        type: claude
        persona: auditor
      output_schema: AuditResult
      transitions:
        - target: revise
          condition: "result.decision == 'retry'"
        - target: synthesize
          condition: "result.decision == 'proceed'"
        - target: halt
          condition: "result.decision == 'halt'"

    synthesize:
      type: orchestrator-task
      agent:
        name: orchestrator
        type: claude
        session_persist: true
      transitions:
        - target: complete
          condition: always

    complete:
      type: terminal
```

### Circuit Breaker Safety

The circuit breaker prevents runaway costs and infinite loops:

```python
# runner/circuit_breaker.py

class CircuitBreaker:
    """Safety mechanism to prevent runaway workflows."""

    # Soft limits (orchestrator can request override)
    state_visit_limit: int = 3        # Max visits per state
    transition_limit: int = 20        # Max total transitions
    timeout_minutes: int = 30         # Max runtime
    cost_limit_usd: float = 5.00      # Max spend

    # Hard limits (cannot be overridden)
    max_transitions_hard: int = 50
    max_runtime_hard_minutes: int = 60
    max_cost_hard_usd: float = 10.00

    def check(self, context: WorkflowContext) -> CircuitStatus:
        """Check all limits and return status."""
        pass
```

### Execution Flow

```python
# runner/state_machine.py

class StateMachine:
    def run(self, story_id: str) -> WorkflowResult:
        context = self.initialize_context(story_id)

        while not context.is_terminal:
            # 1. Check circuit breaker
            status = self.circuit_breaker.check(context)
            if status.tripped:
                return self.handle_circuit_break(status)

            # 2. Execute current state
            state = self.states[context.current_state]
            result = self.execute_state(state, context)

            # 3. Log state transition
            self.logger.log_transition(context, result)

            # 4. Evaluate transitions
            next_state = self.evaluate_transitions(state, result)
            context.transition_to(next_state)

        return WorkflowResult(success=True, outputs=context.outputs)
```

---

## Database Models

### Entity Relationship Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              CORE ENTITIES                                   │
└─────────────────────────────────────────────────────────────────────────────┘

┌──────────────┐       ┌──────────────┐       ┌──────────────┐
│    USER      │       │  WORKSPACE   │       │   BILLING    │
├──────────────┤       ├──────────────┤       ├──────────────┤
│ id (UUID)    │──┐    │ id (UUID)    │    ┌──│ subscription │
│ email        │  │    │ owner_id     │◀───┘  │ tier         │
│ password_hash│  │    │ name         │       │ credit_bal   │
│ role         │  └───▶│ settings     │       │ stripe_id    │
│ workspace_id │       │ created_at   │       └──────────────┘
└──────────────┘       └──────────────┘
       │                      │
       │                      │
       ▼                      ▼
┌──────────────┐       ┌──────────────┐       ┌──────────────┐
│   SESSION    │       │    POST      │       │ VOICE_PROFILE│
├──────────────┤       ├──────────────┤       ├──────────────┤
│ id (UUID)    │       │ id (UUID)    │       │ id (UUID)    │
│ user_id      │       │ workspace_id │       │ workspace_id │
│ token        │       │ title        │       │ name         │
│ expires_at   │       │ content      │       │ tone         │
│ ip_address   │       │ status       │       │ style_rules  │
└──────────────┘       │ platform     │       │ examples     │
                       │ voice_id     │       └──────────────┘
                       └──────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                           CONTENT PIPELINE                                    │
└──────────────────────────────────────────────────────────────────────────────┘

┌──────────────┐       ┌──────────────┐       ┌──────────────┐
│   STRATEGY   │       │   CHAPTER    │       │  STORY_ENTRY │
├──────────────┤       ├──────────────┤       ├──────────────┤
│ id (UUID)    │──────▶│ id (UUID)    │──────▶│ id (UUID)    │
│ workspace_id │       │ strategy_id  │       │ chapter_id   │
│ name         │       │ number       │       │ week_number  │
│ thesis       │       │ theme        │       │ topic        │
│ enemy        │       │ enemy        │       │ story_source │
└──────────────┘       │ weeks        │       │ shape        │
                       └──────────────┘       │ cadence      │
                                              └──────────────┘

┌──────────────────────────────────────────────────────────────────────────────┐
│                           VISUAL ASSETS                                       │
└──────────────────────────────────────────────────────────────────────────────┘

┌──────────────┐       ┌──────────────┐       ┌──────────────┐
│  CHARACTER   │       │    SCENE     │       │    POSE      │
├──────────────┤       ├──────────────┤       ├──────────────┤
│ id (UUID)    │       │ id (UUID)    │       │ id (UUID)    │
│ workspace_id │       │ workspace_id │       │ workspace_id │
│ name         │       │ name         │       │ name         │
│ description  │       │ description  │       │ description  │
│ appearance   │       │ sentiment_id │       │ sentiment_id │
│ personality  │       │ props        │       │ camera_angle │
└──────────────┘       └──────────────┘       └──────────────┘

┌──────────────┐       ┌──────────────┐       ┌──────────────┐
│   OUTFIT     │       │  SENTIMENT   │       │     PROP     │
├──────────────┤       ├──────────────┤       ├──────────────┤
│ id (UUID)    │       │ id (UUID)    │       │ id (UUID)    │
│ workspace_id │       │ workspace_id │       │ workspace_id │
│ name         │       │ strategy_id  │       │ category     │
│ parts[]      │       │ name         │       │ name         │
│ sentiment_id │       │ color_scheme │       │ description  │
└──────────────┘       │ mood         │       └──────────────┘
                       └──────────────┘

┌──────────────────────────────────────────────────────────────────────────────┐
│                        MARKET INTELLIGENCE (pgvector)                         │
└──────────────────────────────────────────────────────────────────────────────┘

┌──────────────┐       ┌──────────────┐       ┌──────────────┐
│  EMBEDDING   │       │AUDIENCE_SEG  │       │CALIBRATED_   │
├──────────────┤       ├──────────────┤       │   VOICE      │
│ id (UUID)    │       │ id (UUID)    │       ├──────────────┤
│ workspace_id │       │ workspace_id │       │ id (UUID)    │
│ source_type  │       │ name         │       │ workspace_id │
│ source_id    │       │ profile JSON │       │ voice_id     │
│ embedding[]  │◀──────│ demographics │       │ segment_id   │
│ chunk_text   │ vec   │ psychographic│       │ platform     │
│ metadata     │ 1536  │ is_primary   │       │ voice_spec   │
└──────────────┘       └──────────────┘       └──────────────┘
```

### Key Models by Module

| Module | Models | Purpose |
|--------|--------|---------|
| `user.py` | User, UserRole | Authentication, system roles |
| `workspace.py` | Workspace, WorkspaceMembership, WorkspaceInvite | Multi-tenant isolation |
| `subscription.py` | SubscriptionTier, AccountSubscription | Billing tiers |
| `post.py` | Post | Generated content |
| `voice_profile.py` | VoiceProfile | User's writing voice |
| `content.py` | Strategy, Chapter, StoryEntry, Goal | Content planning |
| `character.py` | Character, Scene, Pose, Outfit, Sentiment, Prop | Visual assets |
| `market_intelligence.py` | Embedding, AudienceSegment, CalibratedVoice | Semantic search |

### Model Inheritance

```python
# runner/db/models/base.py

class UUIDModel(SQLModel):
    """Base model with UUID primary key."""
    id: UUID = Field(default_factory=uuid4, primary_key=True)

class TimestampMixin(SQLModel):
    """Mixin for created_at/updated_at timestamps."""
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default=None)
```

---

## API Structure

### Route Organization

```
api/routes/
├── auth.py                 # Authentication & registration
├── users.py                # User management
├── workspaces.py           # Workspace CRUD
├── billing.py              # Stripe integration
├── content.py              # Content strategy management
├── posts.py                # Post CRUD
├── finished_posts.py       # Published post viewer
├── voice_profiles.py       # Voice profile management
├── workflow_personas.py    # AI persona configuration
├── characters.py           # Visual character management
├── scenes.py               # Scene definitions
├── poses.py                # Pose library
├── outfits.py              # Outfit combinations
├── sentiments.py           # Sentiment definitions
├── props.py                # Prop categories
├── image_prompts.py        # Image generation prompts
├── workflow.py             # Workflow execution API
├── run_history.py          # Execution history
└── health.py               # Health checks
```

### Authentication Flow

```
┌─────────┐     ┌─────────┐     ┌─────────┐     ┌─────────┐
│ Client  │────▶│  Login  │────▶│  JWT    │────▶│Protected│
│         │     │ /login  │     │ Token   │     │ Routes  │
└─────────┘     └─────────┘     └─────────┘     └─────────┘
                     │                               │
                     ▼                               ▼
              ┌─────────────┐               ┌─────────────┐
              │ Verify      │               │ Decode JWT  │
              │ Password    │               │ Get User    │
              │ bcrypt      │               │ Check Scope │
              └─────────────┘               └─────────────┘
```

### Authorization Scopes

```python
# api/auth/scopes.py

class Scope(str, Enum):
    # Content operations
    CONTENT_READ = "content:read"
    CONTENT_WRITE = "content:write"
    CONTENT_DELETE = "content:delete"

    # Team management
    TEAM_READ = "team:read"
    TEAM_MANAGE = "team:manage"

    # Billing
    BILLING_READ = "billing:read"
    BILLING_MANAGE = "billing:manage"

    # Admin
    ADMIN_SYSTEM = "admin:system"
```

### Endpoint Examples

```python
# api/routes/posts.py

@router.get("/posts", response_model=list[PostRead])
async def list_posts(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List posts for current user's workspace."""
    return await post_service.list_by_workspace(
        db, workspace_id=user.workspace_id
    )

@router.post("/posts", response_model=PostRead)
async def create_post(
    post: PostCreate,
    user: User = Depends(require_scope(Scope.CONTENT_WRITE)),
    db: Session = Depends(get_db),
):
    """Create a new post in workspace."""
    return await post_service.create(db, post, workspace_id=user.workspace_id)
```

### WebSocket Streaming

```python
# api/routes/workflow.py

@router.websocket("/workflow/{story_id}/stream")
async def workflow_stream(
    websocket: WebSocket,
    story_id: str,
    token: str = Query(...),
):
    """Stream workflow execution progress in real-time."""
    await websocket.accept()

    async for event in workflow_service.execute_streaming(story_id):
        await websocket.send_json({
            "type": event.type,
            "state": event.state,
            "agent": event.agent,
            "content": event.content,
            "tokens": event.tokens,
            "cost": event.cost,
        })
```

---

## Frontend Architecture

### State Management (Zustand)

The frontend uses Zustand for lightweight, reactive state management:

```typescript
// gui/src/stores/authStore.ts

interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  viewAsUser: boolean;  // Owner can preview user experience

  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  toggleViewMode: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      token: null,
      isAuthenticated: false,
      viewAsUser: false,

      login: async (email, password) => {
        const response = await api.post('/auth/login', { email, password });
        set({
          user: response.user,
          token: response.token,
          isAuthenticated: true,
        });
      },

      logout: () => {
        set({ user: null, token: null, isAuthenticated: false });
      },

      toggleViewMode: () => {
        set(state => ({ viewAsUser: !state.viewAsUser }));
      },
    }),
    { name: 'auth-storage' }
  )
);
```

### Store Structure

| Store | Purpose | Key State |
|-------|---------|-----------|
| `authStore` | Authentication | user, token, viewAsUser |
| `workspaceStore` | Workspace data | workspace, members |
| `contentStore` | Content pipeline | strategies, posts, drafts |
| `visualStore` | Visual assets | characters, scenes, outfits |
| `flagsStore` | Feature flags | enabled features by role |

### Page Components

```
gui/src/pages/
├── Landing.tsx             # Public landing page
├── Login.tsx               # Authentication
├── Register.tsx            # User registration
├── Dashboard.tsx           # Main dashboard
├── StoryWorkflow.tsx       # Workflow execution UI
├── RunHistory.tsx          # Execution history
├── FinishedPosts.tsx       # Published posts viewer
├── Settings.tsx            # User/workspace settings
├── Billing.tsx             # Subscription management
├── Team.tsx                # Workspace members
├── ContentStrategy.tsx     # Strategy management
├── Characters.tsx          # Character management
├── ImageConfig.tsx         # Visual asset config
├── AIPersonas.tsx          # AI persona configuration
└── VoiceProfiles.tsx       # Voice profile management
```

### Data Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              REACT COMPONENT                                 │
│                                                                              │
│   useEffect(() => {                                                          │
│     contentStore.fetchPosts();  // Triggers store action                     │
│   }, []);                                                                    │
│                                                                              │
│   const posts = useContentStore(s => s.posts);  // Subscribe to state        │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              ZUSTAND STORE                                   │
│                                                                              │
│   fetchPosts: async () => {                                                  │
│     set({ loading: true });                                                  │
│     const posts = await api.get('/posts');  // API call                      │
│     set({ posts, loading: false });                                          │
│   }                                                                          │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              API CLIENT                                      │
│                                                                              │
│   const api = axios.create({ baseURL: '/api' });                            │
│   api.interceptors.request.use(config => {                                   │
│     config.headers.Authorization = `Bearer ${token}`;                        │
│     return config;                                                           │
│   });                                                                        │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Prompt Engineering System

### Three-Layer Composition

The prompt system uses a hierarchical composition model:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        LAYER 1: UNIVERSAL RULES                              │
│                                                                              │
│   - Word count constraints (250-400 words)                                   │
│   - Format rules (no bullets, no headers)                                    │
│   - Quality standards                                                        │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        LAYER 2: VOICE PROFILE                                │
│                                                                              │
│   User-specific voice characteristics:                                       │
│   - Tone (reflective, vulnerable, generous)                                  │
│   - Signature phrases                                                        │
│   - Things to avoid                                                          │
│   - Example content                                                          │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        LAYER 3: PERSONA TEMPLATE                             │
│                                                                              │
│   Role-specific instructions:                                                │
│   - Writer: Generate initial draft                                           │
│   - Auditor: Evaluate against criteria                                       │
│   - Synthesizer: Combine multiple drafts                                     │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Persona Templates

Located in `prompts/` directory:

```
prompts/
├── writer.md           # Draft generation persona
├── auditor.md          # Quality evaluation persona
├── synthesizer.md      # Draft combination persona
├── voice_samples/      # Example content per voice
└── guidelines/         # Platform-specific guidelines
```

### Prompt Assembly

```python
# runner/prompts/composer.py

class PromptComposer:
    """Assembles prompts from layers."""

    def compose(
        self,
        persona: str,
        voice_profile: VoiceProfile,
        context: dict,
    ) -> str:
        # Layer 1: Universal rules
        rules = self.load_template("universal_rules.md")

        # Layer 2: Voice profile
        voice = self.format_voice_profile(voice_profile)

        # Layer 3: Persona template
        persona_template = self.load_template(f"{persona}.md")

        # Compose final prompt
        return persona_template.format(
            universal_rules=rules,
            voice_profile=voice,
            **context,
        )
```

---

## Security & Multi-Tenancy

### Data Isolation

Every data access is scoped by workspace:

```python
# api/services/post_service.py

async def list_by_workspace(
    db: Session,
    workspace_id: UUID,
) -> list[Post]:
    """List posts for a specific workspace only."""
    return db.exec(
        select(Post)
        .where(Post.workspace_id == workspace_id)
        .order_by(Post.created_at.desc())
    ).all()
```

### Authentication Security

- Passwords hashed with bcrypt (cost factor 12)
- JWT tokens with 24-hour expiry
- Refresh token rotation
- Session invalidation on password change

### Rate Limiting

```python
# api/middleware/rate_limit.py

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    client_ip = request.client.host
    key = f"rate_limit:{client_ip}"

    current = await redis.incr(key)
    if current == 1:
        await redis.expire(key, 60)  # 60 second window

    if current > 100:  # 100 requests per minute
        raise HTTPException(429, "Rate limit exceeded")

    return await call_next(request)
```

### Role-Based Access Control

**System Roles (UserRole):**
| Role | Access Level |
|------|-------------|
| `owner` | SaaS owner, full system access |
| `admin` | Administrative functions |
| `user` | Standard user access |

**Workspace Roles:**
| Role | Capabilities |
|------|-------------|
| `owner` | Full workspace control, billing |
| `admin` | Manage members, settings |
| `editor` | Create and edit content |
| `viewer` | Read-only access |

---

## Development & Deployment

### Quick Start

```bash
# 1. Clone and setup
git clone <repo>
cd orchestrator
make setup

# 2. Configure environment
cp .env.example .env
# Edit .env with your secrets

# 3. Start services
make dev

# Services available at:
# - Frontend: http://localhost:5173
# - API: http://localhost:8000
# - API Docs: http://localhost:8000/docs
```

### Docker Services

| Service | Port | Purpose |
|---------|------|---------|
| postgres | 5433 | Database (direct) |
| pgbouncer | 6433 | Connection pooling |
| redis | 6380 | Cache |
| ollama | 11434 | Local LLM |
| api | 8000 | FastAPI backend |
| gui | 5173 | React frontend |
| watermark | 8001 | Image processing |

### Environment Variables

```bash
# Required
JWT_SECRET=<random-256-bit-key>
POSTGRES_PASSWORD=<strong-password>

# Billing (optional)
STRIPE_SECRET_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...

# Email (optional)
SMTP_HOST=smtp.gmail.com
SMTP_USER=...
SMTP_PASSWORD=...

# App
APP_BASE_URL=http://localhost:5173
```

### Testing

```bash
make test           # Unit tests
make test-int       # Integration tests
make test-e2e       # End-to-end tests (costs money)
make coverage       # Coverage report
make test-file FILE=tests/unit/test_circuit_breaker.py  # Single file
```

### Makefile Commands

| Category | Command | Description |
|----------|---------|-------------|
| Setup | `make setup` | First-time setup |
| Dev | `make dev` | Start all services (Docker) |
| Dev | `make dev-local` | Start API + GUI locally |
| Database | `make db-up` | Start PostgreSQL |
| Database | `make db-migrate` | Run migrations |
| Database | `make db-shell` | PostgreSQL CLI |
| Test | `make test` | Run unit tests |
| Test | `make coverage` | Generate coverage |
| Workflow | `make workflow STORY=post_03` | Run workflow |
| Git | `make pr TITLE="..."` | Create PR |

### Production Checklist

- [ ] Set strong `JWT_SECRET` (256-bit random)
- [ ] Configure SMTP for emails
- [ ] Set up Stripe webhooks
- [ ] Enable HTTPS (TLS termination)
- [ ] Set up monitoring/logging
- [ ] Configure PostgreSQL backups
- [ ] Set rate limits
- [ ] Review CORS settings
- [ ] Enable WAF if exposed

---

## Appendix: Key Files Reference

| File | Purpose |
|------|---------|
| `workflow_config.yaml` | State machine definition |
| `docker-compose.yml` | Service orchestration |
| `alembic.ini` | Migration configuration |
| `runner/db/migrations/` | Database schema versions |
| `prompts/*.md` | AI persona templates |
| `.env.example` | Environment template |
| `Makefile` | Development commands |

---

*Generated: 2026-01-18 | Postmagiq Orchestrator v1.0*
