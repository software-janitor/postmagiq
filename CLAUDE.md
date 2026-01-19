# Claude Code Instructions - Workflow Orchestrator

## Goal

Make the smallest possible changes that achieve the specific requirement, using exactly the same patterns that already exist in the code. Always create a plan that breaks down everything into smaller tasks and implement step by step.

---

## Behavior Rules (How Claude Acts)

### Planning

1. **READ FIRST** - Always examine existing code patterns before planning or suggesting changes
2. **BREAK INTO PHASES** - Always break work into small, independently testable phases
3. **KEEP PLANS CONCISE** - Sacrifice grammar for brevity
4. **LIST UNRESOLVED QUESTIONS** - End every plan with unresolved questions
5. **VERIFY THEN PROCEED** - Run tests to verify current phase works before next phase

### Communication

1. **NO SELF-ATTRIBUTION** - NEVER add Claude, Anthropic, AI, or "Generated with" to commits/code
2. **BE DIRECT AND HONEST** - Don't say something is production ready when it's not
3. **SMALL REVIEWABLE TASKS** - Keep individual tasks small enough for easy review
4. **VERIFY BEFORE MOVING ON** - Run tests to confirm changes compile/run before proceeding
5. **NEVER ASK USER TO DEBUG** - Do it yourself using available tools
6. **USE HYPERLINKS** - Always format URLs as markdown links: `[text](url)`

### Git Workflow

- Create branch automatically at start of work (don't ask)
- Commit at checkpoints automatically (don't ask)
- After tests pass: push and create PR using `make pr` (don't ask)
- **ALWAYS use `make pr`** - it filters self-attribution patterns automatically

### Task Completion Checklist (MANDATORY)

Before moving on, verify ALL:

- [ ] Tests written WITH the feature (not after)
- [ ] Targeted tests pass: `make test` or `pytest tests/unit -q --tb=short`
- [ ] Committed and pushed (no asking)
- [ ] PR created with link shown

---

## Code Rules (How Claude Writes Code)

### Core Principles

1. **MINIMAL CHANGES** - Only modify what's absolutely necessary
2. **USE EXISTING PATTERNS** - Follow the exact same patterns already in the codebase
3. **AVOID REBUILDING** - Don't redesign existing functionality unless broken
4. **WRITE TESTS WITH FEATURES** - Tests are part of the implementation, not an afterthought

### Key Patterns

**Pydantic for LLM outputs:**
```python
from pydantic import BaseModel, Field
from typing import Literal

class AuditResult(BaseModel):
    score: int = Field(ge=1, le=10)
    decision: Literal["proceed", "retry", "halt"]
    feedback: str
```

**deepcopy before state mutation:**
```python
from copy import deepcopy

# CRITICAL: Copy state to avoid mutating the canonical config
state = deepcopy(self.states[state_name])
state["context"] = feedback  # Safe mutation
```

**shlex.quote for shell commands:**
```python
import shlex
safe_prompt = shlex.quote(prompt)  # Prevent shell injection
command = f"claude -p {safe_prompt}"
```

**Subprocess with args list (preferred):**
```python
# Preferred: No shell=True
args = ["claude", "--output-format", "json", "-p", prompt]
result = subprocess.run(args, capture_output=True, text=True)
```

### Testing

**Use MockAgent for unit tests:**
```python
class MockAgent:
    def __init__(self, responses: list[str]):
        self.responses = responses
        self.call_count = 0

    def invoke(self, prompt: str) -> AgentResult:
        response = self.responses[self.call_count % len(self.responses)]
        self.call_count += 1
        return AgentResult(success=True, content=response, ...)
```

---

## Architecture Overview

### System Layers
```
┌─────────────────────────────────────────────────────────────────┐
│                         MAKE COMMAND                             │
│                    make workflow STORY=post_03                   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                       PYTHON RUNNER                              │
│  runner/runner.py → runner/state_machine.py → runner/agents/    │
└─────────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│  ORCHESTRATOR   │  │    WORKERS      │  │    LOGGING      │
│  (persistent)   │  │  (stateless)    │  │                 │
│                 │  │                 │  │  • State log    │
│  claude --resume│  │  claude -p      │  │  • Agent logs   │
│  gemini --resume│  │  gemini         │  │  • Token usage  │
└─────────────────┘  └─────────────────┘  └─────────────────┘
```

### Key Directories

| Directory | Purpose |
|-----------|---------|
| `runner/` | Core orchestration code |
| `runner/agents/` | Agent implementations (Claude, Gemini, Codex) |
| `runner/sessions/` | Session persistence managers |
| `runner/metrics/` | Token tracking and cost calculation |
| `runner/logging/` | State and agent logging |
| `runner/models.py` | Pydantic models for LLM outputs |
| `prompts/` | Persona templates (writer, auditor, synthesizer) |
| `workflow/` | Runtime artifacts (drafts, audits, logs, sessions) |
| `tests/` | Unit, integration, e2e tests |

### Key Files

| File | Purpose |
|------|---------|
| `workflow_config.yaml` | State machine config, agent definitions |
| `runner/runner.py` | Main entry point |
| `runner/state_machine.py` | State transitions, fan-out execution |
| `runner/circuit_breaker.py` | Loop prevention, cost limits |
| `runner/agents/base.py` | Abstract agent interface |
| `runner/sessions/native.py` | CLI session management |
| `runner/models.py` | Pydantic models (AgentResult, AuditResult, etc.) |

---

## Common Pitfalls (AVOID THESE)

### 1. Mutating Config State
```python
# WRONG - mutates shared state
state = self.states[state_name]
state["context"] = feedback

# CORRECT - deepcopy first
state = deepcopy(self.states[state_name])
state["context"] = feedback
```

### 2. Shell Injection
```python
# WRONG - breaks on apostrophes
command = f"claude -p '{prompt}'"

# CORRECT - shlex.quote or args list
safe_prompt = shlex.quote(prompt)
command = f"claude -p {safe_prompt}"
```

### 3. Missing Timeout in proc.wait()
```python
# WRONG - blocks forever
returncode = proc.wait()

# CORRECT - use timeout
try:
    returncode = proc.wait(timeout=300)
except subprocess.TimeoutExpired:
    proc.kill()
    proc.wait()
```

### 4. Hardcoding Resume Commands
```python
# WRONG - drops JSON flags
if self.session_id:
    return f"claude --resume {self.session_id} -p '{prompt}'"

# CORRECT - use resume_command from config
return agent_config["resume_command"].format(
    session_id=self.session_id,
    prompt=safe_prompt
)
```

### 5. Double-Quoting Prompts
```yaml
# WRONG - command template has quotes AND get_command() uses shlex.quote()
# shlex.quote("hello world") returns 'hello world'
# Result: claude -p ''hello world'' (broken!)
command: "claude -p '{prompt}'"

# CORRECT - no quotes in template, shlex.quote() handles it
command: "claude -p {prompt}"
```

---

## Quick Start

### Fresh Install
```bash
make setup           # Install dependencies (Python + npm)
make db-up           # Start PostgreSQL + PgBouncer
make db-migrate      # Create tables + seed initial data
make dev             # Start API + GUI (Ctrl+C to stop)
```

The database migration seeds all required initial data:
- Subscription tiers (Free, Individual, Team, Agency)
- System personas (Writer, Auditor, Synthesizer, etc.)
- System user for system-owned data

No separate seed commands needed for fresh installs.

### Updating Personas
If you modify persona prompts in `prompts/`, run:
```bash
make seed-personas   # Updates persona content from prompts/
```

---

## Available Tools

### Setup & Development
| Command | Description |
|---------|-------------|
| `make setup` | First-time setup (hooks + deps) |
| `make db-up` | Start PostgreSQL + PgBouncer |
| `make db-migrate` | Run database migrations (creates tables + seeds data) |
| `make dev` | Start API + GUI together |
| `make dev-stop` | Stop running dev servers |
| `make restart` | Restart dev servers |

### Workflow
| Command | Description |
|---------|-------------|
| `make workflow STORY=post_03` | Run full workflow for a story |
| `make workflow-step STEP=draft` | Run single workflow step |
| `make check-config` | Validate workflow_config.yaml |

### Testing
| Command | Description |
|---------|-------------|
| `make test` | Run unit tests |
| `make test-int` | Run integration tests with fixtures |
| `make test-e2e` | Run real API tests (costs money) |
| `make coverage` | Generate coverage report |
| `make test-file FILE=tests/unit/test_circuit_breaker.py` | Run specific test |

### Database
| Command | Description |
|---------|-------------|
| `make db-up` | Start PostgreSQL + PgBouncer |
| `make db-down` | Stop PostgreSQL + PgBouncer |
| `make db-migrate` | Run Alembic migrations |
| `make db-rollback` | Rollback last migration |
| `make db-shell` | Connect to PostgreSQL CLI |

### Personas
| Command | Description |
|---------|-------------|
| `make seed-personas` | Update system personas from prompts/ |

### Logging
| Command | Description |
|---------|-------------|
| `make logs` | List all runs |
| `make log-states RUN=xxx` | Show state log for a run |
| `make log-tokens RUN=xxx` | Show token usage for a run |
| `make log-summary RUN=xxx` | Show run summary |

### Evaluation
| Command | Description |
|---------|-------------|
| `make eval-agents` | Agent performance comparison |
| `make eval-costs` | Cost breakdown by agent |
| `make eval-trend` | Quality trend over time |
| `make eval-post STORY=post_03` | Post iteration history |

### Git
| Command | Description |
|---------|-------------|
| `make pr TITLE="..." BODY_FILE=body.md` | Create PR from file (auto-filters self-attribution) |
| `make pr TITLE="..."` | Create PR (opens editor) |

---

## State Machine Quick Reference

### State Types

| Type | Behavior |
|------|----------|
| `initial` | Entry point, no agent |
| `fan-out` | Run multiple agents in parallel |
| `single` | Run one agent (quality gates) |
| `orchestrator-task` | Orchestrator with session |
| `human-approval` | Pause for CLI input |
| `terminal` | Exit point |

### Circuit Breaker Rules

| Rule | Trigger |
|------|---------|
| `state_visit_limit` | Same state visited 3+ times |
| `cycle_detection` | A→B→A→B pattern |
| `transition_limit` | 20+ transitions |
| `timeout` | 30 minutes elapsed |
| `cost_limit` | $5.00 spent |

### Safety Limits (Orchestrator Can't Override)

| Limit | Value |
|-------|-------|
| `max_transitions_hard` | 50 |
| `max_runtime_hard` | 1 hour |
| `max_cost_hard` | $10.00 |

---

## References

- Main plan: `WORKFLOW_ORCHESTRATION_PLAN.md`
- Content strategy: `CLAUDE.md` (root)
- Testing templates: `TESTING_TEMPLATE.md`
