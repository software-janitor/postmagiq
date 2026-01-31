# Multi-Agent Workflow Orchestration Plan

**Project:** LinkedIn Content Automation - Multi-Agent Writing Pipeline
**Author:** Matthew Garcia
**Date:** 2026-01-07
**Status:** Planning

---

## 1. Executive Summary

### Goal
Build a config-driven, multi-agent orchestration system that:
1. Fans out writing tasks to multiple AI agents (Claude, Gemini, Codex, Ollama)
2. Collects and cross-audits outputs
3. Synthesizes the best elements into a final post
4. Tracks all interactions, tokens, and decisions in comprehensive logs

### Key Design Decisions
- **Python Runner** as the core orchestrator (not pure MCP)
- **Session persistence** via native CLI flags (Claude, Gemini, Codex) or file-based (Ollama)
- **MCP layer optional** - can be added later without rewriting
- **Modular agent architecture** - easy to add new agents
- **GPU-aware model selection** for Ollama
- **Full token tracking** across all agents

---

## 2. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         MAKE COMMAND                             │
│                    make workflow STORY=post_03                   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                       PYTHON RUNNER                              │
│                                                                  │
│  • Reads workflow_config.yaml                                    │
│  • Manages state machine transitions                             │
│  • Invokes orchestrator with session persistence                 │
│  • Fans out to worker agents                                     │
│  • Logs everything (state, tokens, results)                      │
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
│  codex resume   │  │  codex          │  │  • Results      │
│                 │  │  ollama         │  │  • Decisions    │
└─────────────────┘  └─────────────────┘  └─────────────────┘
```

---

## 3. Workflow State Machine

### States

```
┌─────────┐
│  START  │
└────┬────┘
     │
     ▼
┌─────────┐     ┌─────────────────────────────────────────┐
│  DRAFT  │────▶│  Fan-out: Claude, Gemini, Codex write   │
└────┬────┘     │  Output: claude_draft.md, gemini_draft.md, gpt_draft.md
     │          └─────────────────────────────────────────┘
     ▼
┌─────────────┐ ┌─────────────────────────────────────────┐
│ CROSS-AUDIT │─▶│  Fan-out: Each agent audits ALL drafts  │
└──────┬──────┘ │  Output: claude_audit.md, gemini_audit.md, gpt_audit.md
       │        └─────────────────────────────────────────┘
       ▼
┌─────────────┐ ┌─────────────────────────────────────────┐
│ SYNTHESIZE  │─▶│  Orchestrator combines best elements    │
└──────┬──────┘ │  Output: final_post.md                   │
       │        └─────────────────────────────────────────┘
       ▼
┌─────────────┐ ┌─────────────────────────────────────────┐
│ FINAL-AUDIT │─▶│  Fan-out: Each agent audits final post  │
└──────┬──────┘ │  Output: claude_final_audit.md, etc.     │
       │        └─────────────────────────────────────────┘
       ▼
┌─────────────────┐ ┌─────────────────────────────────────┐
│ FINAL-ANALYSIS  │─▶│  Orchestrator reviews all audits     │
└────────┬────────┘ │  Output: final_analysis.md           │
         │          └─────────────────────────────────────┘
         ▼
    ┌──────────┐
    │ COMPLETE │
    └──────────┘
```

### Transitions

| From | To | Condition |
|------|-----|-----------|
| start | draft | Input story exists |
| draft | cross-audit | All agents complete (or partial success) |
| draft | halt | All agents fail |
| cross-audit | synthesize | All audits complete |
| cross-audit | draft | All audits fail (retry) |
| synthesize | final-audit | Final post created |
| synthesize | cross-audit | Synthesis failed |
| final-audit | final-analysis | All audits complete |
| final-audit | synthesize | All audits fail (retry) |
| final-analysis | complete | Analysis complete |
| final-analysis | final-audit | Analysis failed |

### File IO Safety (Fan-Out States)

During fan-out, multiple agents run in parallel. To prevent race conditions:

1. **Each agent writes to a unique file** - never shared files
2. **Runner waits for ALL processes to exit** before reading outputs
3. **Use atomic writes** - write to temp file, then rename

```python
# runner/state_machine.py

import subprocess
import time

def execute_fanout(self, state: dict) -> dict:
    """Execute fan-out state with timeout enforcement and proper file safety.

    Uses timeout_per_agent from settings. Kills and cleans up timed-out processes.
    """
    timeout = self.config.get("settings", {}).get("timeout_per_agent", 300)
    processes = []

    # Launch all agents in parallel
    for agent_name in state["agents"]:
        # Each agent writes to its own file
        output_path = state["output"].format(agent=agent_name)
        proc = self.launch_agent(agent_name, state["input"], output_path)
        processes.append((agent_name, proc, output_path, time.time()))

    # Wait for ALL to complete before reading ANY outputs
    results = {}
    for agent_name, proc, output_path, start_time in processes:
        # Calculate remaining time for this agent
        elapsed = time.time() - start_time
        remaining = max(0, timeout - elapsed)

        try:
            returncode = proc.wait(timeout=remaining)

            if returncode == 0 and os.path.exists(output_path):
                # Only read after process has fully exited
                results[agent_name] = {
                    "status": "success",
                    "output": self.read_output(output_path)
                }
            else:
                results[agent_name] = {
                    "status": "failed",
                    "returncode": returncode
                }

        except subprocess.TimeoutExpired:
            # Kill the process and clean up zombie
            proc.kill()
            proc.wait()  # Reap the zombie process

            results[agent_name] = {
                "status": "timeout",
                "elapsed": timeout
            }
            self.log({
                "event": "agent_timeout",
                "agent": agent_name,
                "timeout_seconds": timeout
            })

    # Determine transition based on results
    success_count = sum(1 for r in results.values() if r["status"] == "success")
    if success_count == len(state["agents"]):
        return {"transition": "all_success", "results": results}
    elif success_count > 0:
        return {"transition": "partial_success", "results": results}
    else:
        return {"transition": "all_failure", "results": results}
```

**File naming pattern:**
```
drafts/
├── claude_draft.md      # Claude's output
├── gemini_draft.md      # Gemini's output
└── codex_draft.md       # Codex's output
```

**Never:**
- Have multiple agents write to the same file
- Read a file while an agent might still be writing
- Use shared log files during parallel execution (aggregate after)

### Dynamic Prompts for Partial Failures

When some agents fail in a fan-out phase, downstream states must adapt their prompts. The synthesizer cannot reference an agent that didn't produce output.

**Problem:** If Gemini times out during draft, the synthesizer prompt cannot say "Compare Claude and Gemini drafts."

**Solution:** Build prompts dynamically based on available outputs.

```python
# runner/prompts.py

def build_synthesizer_prompt(
    available_drafts: dict[str, str],
    available_audits: dict[str, str],
    persona_template: str
) -> str:
    """Build synthesizer prompt based on what actually succeeded.

    Args:
        available_drafts: {agent_name: draft_content} for successful agents
        available_audits: {agent_name: audit_content} for successful agents
        persona_template: Base persona with {drafts}, {audits}, {agent_list} placeholders
    """

    # Build dynamic list of available agents
    agent_list = ", ".join(available_drafts.keys())

    # Format drafts section
    drafts_section = ""
    for agent, content in available_drafts.items():
        drafts_section += f"## Draft from {agent}\n\n{content}\n\n"

    # Format audits section
    audits_section = ""
    for agent, content in available_audits.items():
        audits_section += f"## Audit from {agent}\n\n{content}\n\n"

    # Build final prompt
    prompt = persona_template.format(
        drafts=drafts_section,
        audits=audits_section,
        agent_list=agent_list
    )

    return prompt


# Example persona template (prompts/synthesizer_persona.md)
SYNTHESIZER_TEMPLATE = """
You are synthesizing the best elements from available drafts.

## Available Drafts
{drafts}

## Available Audits
{audits}

## Task
Compare the drafts from: {agent_list}
Extract the strongest elements from each and synthesize into a final post.

Note: Some agents may have failed. Work only with what's available above.
Do NOT reference any agent not listed in the drafts section.

## Output
Write a single cohesive post that combines the best elements.
"""
```

**Usage in state machine:**

```python
# runner/state_machine.py

def execute_synthesize(self, state: dict) -> dict:
    """Execute synthesizer with dynamic prompt."""

    # Get results from previous fan-out
    drafts = self.get_successful_outputs("draft")
    audits = self.get_successful_outputs("cross-audit")

    if not drafts:
        return {"transition": "failure", "reason": "No drafts available"}

    # Load persona template
    persona_template = self.load_persona(state["persona"])

    # Build dynamic prompt
    prompt = build_synthesizer_prompt(drafts, audits, persona_template)

    # Execute orchestrator with dynamic prompt
    result = self.orchestrator.invoke(prompt)

    return {"transition": "success", "output": result}
```

**Key principle:** Prompts are templates with placeholders, not hardcoded strings. The runner fills placeholders based on actual available data.

---

## 4. Configuration Schema

### workflow_config.yaml

```yaml
# ============================================================================
# ORCHESTRATOR CONFIGURATION
# ============================================================================

orchestrator:
  agent: claude                      # claude | gemini | codex
  persona: prompts/orchestrator_persona.md
  session:
    enabled: true
    name_format: "workflow_{story}_{date}"

# ============================================================================
# AGENT DEFINITIONS
# ============================================================================

agents:
  claude:
    type: cli
    enabled: true
    # IMPORTANT: --output-format json required for token tracking
    # NOTE: No quotes around {prompt} - shlex.quote() handles quoting in get_command()
    command: "claude --output-format json -p {prompt}"
    resume_command: "claude --output-format json --resume {session_id} -p {prompt}"
    session_support: native
    token_tracking:
      method: json_output
      input_field: "usage.input_tokens"
      output_field: "usage.output_tokens"
    context_window: 200000
    cost_per_1k:
      input: 0.003
      output: 0.015

  gemini:
    type: cli
    enabled: true
    # NOTE: Verify actual Gemini CLI JSON output flag before implementation
    # NOTE: No quotes around {prompt} - shlex.quote() handles quoting in get_command()
    command: "gemini --format json {prompt}"
    resume_command: "gemini --format json --resume {session_id} {prompt}"
    session_support: native
    token_tracking:
      method: json_output
      input_field: "usageMetadata.promptTokenCount"
      output_field: "usageMetadata.candidatesTokenCount"
    context_window: 1000000
    cost_per_1k:
      input: 0.00125
      output: 0.005

  codex:
    type: cli
    enabled: true
    # NOTE: Verify actual Codex CLI JSON output flag before implementation
    # NOTE: No quotes around {prompt} - shlex.quote() handles quoting in get_command()
    command: "codex --json {prompt}"
    resume_command: "codex --json resume {session_id} {prompt}"
    session_support: native
    token_tracking:
      method: json_output
      input_field: "usage.prompt_tokens"
      output_field: "usage.completion_tokens"
    context_window: 128000
    cost_per_1k:
      input: 0.005
      output: 0.015

  # Ollama (GPU-aware local LLM)
  ollama:
    type: ollama
    enabled: false                   # Enable when ready
    session_support: file
    session_dir: "workflow/sessions"
    auto_select_model: true
    token_tracking:
      method: ollama_api
      input_field: "prompt_eval_count"
      output_field: "eval_count"

    model_tiers:
      tier_8gb:
        vram_range: [6, 10]
        recommended:
          writer: "llama3.2:8b-instruct-q4_K_M"
          auditor: "mistral:7b-instruct-q4_K_M"
          coder: "deepseek-coder:6.7b-instruct-q4_K_M"
        fallback: "phi3:mini"
        max_context_tokens: 8192

      tier_16gb:
        vram_range: [12, 18]
        recommended:
          writer: "llama3.1:13b-instruct-q4_K_M"
          auditor: "llama3.1:13b-instruct-q4_K_M"
          coder: "deepseek-coder:33b-instruct-q4_K_M"
        fallback: "llama3.2:8b-instruct"
        max_context_tokens: 32768

      tier_24gb:
        vram_range: [20, 26]
        recommended:
          writer: "llama3.1:70b-instruct-q4_K_M"
          auditor: "llama3.1:70b-instruct-q4_K_M"
          coder: "deepseek-coder:33b-instruct"
        fallback: "llama3.1:13b-instruct"
        max_context_tokens: 65536

      tier_48gb:
        vram_range: [40, 100]
        recommended:
          writer: "llama3.1:70b-instruct"
          auditor: "llama3.1:70b-instruct"
          coder: "deepseek-coder:33b-instruct"
        fallback: "llama3.1:70b-instruct-q4_K_M"
        max_context_tokens: 131072

      tier_cpu:
        vram_range: [0, 6]
        recommended:
          writer: "phi3:mini"
          auditor: "phi3:mini"
          coder: "qwen2.5-coder:1.5b"
        fallback: "tinyllama"
        max_context_tokens: 4096

# ============================================================================
# PERSONA DEFINITIONS
# ============================================================================

personas:
  writer: prompts/writer_persona.md
  auditor: prompts/auditor_persona.md
  synthesizer: prompts/synthesizer_persona.md
  orchestrator: prompts/orchestrator_persona.md

# ============================================================================
# STATE MACHINE
# ============================================================================

states:
  start:
    type: initial
    on_enter:
      - log: "Starting workflow"
      - validate: input_exists
    next: draft

  draft:
    type: fan-out
    description: "Generate drafts from all agents"
    agents: [claude, gemini, codex]
    persona: writer
    input: "input/story_input.md"
    output: "drafts/{agent}_draft.md"
    transitions:
      all_success: cross-audit
      partial_success: cross-audit
      all_failure: halt

  cross-audit:
    type: fan-out
    description: "Each agent audits all drafts"
    agents: [claude, gemini, codex]
    persona: auditor
    input: "drafts/*.md"
    output: "audits/{agent}_audit.md"
    transitions:
      all_success: synthesize
      partial_success: synthesize
      all_failure: draft

  synthesize:
    type: orchestrator-task
    description: "Orchestrator combines best elements"
    persona: synthesizer
    input:
      - "drafts/*.md"
      - "audits/*.md"
    output: "final/final_post.md"
    transitions:
      success: final-audit
      failure: cross-audit

  final-audit:
    type: fan-out
    description: "Audit the final post"
    agents: [claude, gemini, codex]
    persona: auditor
    input: "final/final_post.md"
    output: "final/{agent}_final_audit.md"
    transitions:
      all_success: final-analysis
      partial_success: final-analysis
      all_failure: synthesize

  final-analysis:
    type: orchestrator-task
    description: "Final determination"
    persona: orchestrator
    input: "final/*_final_audit.md"
    output: "analysis/final_analysis.md"
    transitions:
      success: complete
      failure: final-audit

  complete:
    type: terminal
    on_enter:
      - log: "Workflow complete"
      - generate: run_summary.md

  halt:
    type: terminal
    error: true
    on_enter:
      - log: "Workflow halted due to errors"

# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================

logging:
  enabled: true
  runs_dir: "workflow/runs"
  run_id_format: "{date}_{time}_{story}"

  capture:
    prompts: true
    input_content: true
    output_content: true
    stdout_stream: true
    reasoning: true
    tokens: true                    # Track token usage

  summaries:
    generate_markdown: true
    include_previews: true
    include_scores: true
    include_token_summary: true     # Token totals per agent

  retention_days: 30

# ============================================================================
# SETTINGS
# ============================================================================

settings:
  working_dir: "workflow/"
  parallel_fanout: true
  timeout_per_agent: 300
  retry_count: 2
```

---

## 5. File Structure

```
linkedin_articles/
├── WORKFLOW_ORCHESTRATION_PLAN.md    # This file
├── workflow_config.yaml              # State machine config
│
├── runner/                           # Python runner package
│   ├── __init__.py
│   ├── runner.py                     # Main orchestrator
│   ├── config.py                     # Config loader
│   ├── state_machine.py              # State transitions
│   │
│   ├── agents/                       # Agent implementations
│   │   ├── __init__.py               # Agent factory
│   │   ├── base.py                   # Abstract base class
│   │   ├── claude.py                 # Claude CLI agent
│   │   ├── gemini.py                 # Gemini CLI agent
│   │   ├── codex.py                  # Codex CLI agent
│   │   ├── ollama.py                 # Ollama agent (GPU-aware)
│   │   └── gpu_detect.py             # GPU detection for model tiers
│   │
│   ├── sessions/                     # Session management
│   │   ├── __init__.py
│   │   ├── base.py                   # Session interface
│   │   ├── native.py                 # For CLI --resume
│   │   └── file_based.py             # JSON sessions for Ollama
│   │
│   ├── metrics/                      # Token tracking
│   │   ├── __init__.py
│   │   ├── tokens.py                 # Token counter
│   │   └── costs.py                  # Cost calculator
│   │
│   ├── logging/                      # Run logging
│   │   ├── __init__.py
│   │   ├── state_logger.py           # State transitions
│   │   ├── agent_logger.py           # Agent invocations
│   │   └── summary_generator.py      # Human-readable summaries
│   │
│   ├── history/                      # Historical tracking (Postgres-backed)
│   │   ├── __init__.py
│   │   ├── queries.py                # Evaluation queries
│   │   ├── service.py                # Query helpers
│   │   └── eval.py                   # CLI for evaluation
│   │
│   └── mcp/                          # MCP layer (future)
│       ├── __init__.py
│       └── server.py                 # MCP tool definitions
│
├── prompts/                          # Persona prompts
│   ├── orchestrator_persona.md
│   ├── writer_persona.md
│   ├── auditor_persona.md
│   └── synthesizer_persona.md
│
├── workflow/                         # Workflow working directory
│   ├── input/                        # Story input for current run
│   │   └── story_input.md
│   ├── drafts/                       # Generated drafts
│   ├── audits/                       # Audit results
│   ├── final/                        # Final post + audits
│   ├── analysis/                     # Final analysis
│   ├── sessions/                     # Ollama session files (JSON)
│   ├── history/                      # Historical tracking artifacts
│   └── runs/                         # Historical run logs
│       └── 2026-01-07_143022_post03/
│           ├── run_manifest.yaml
│           ├── state_log.jsonl
│           ├── token_usage.jsonl
│           ├── agent_logs/
│           ├── drafts/
│           ├── audits/
│           ├── final/
│           ├── analysis/
│           └── run_summary.md
│
└── Makefile                          # CLI entry points
```

---

## 6. Token Tracking System

### Data Structures

```python
@dataclass
class TokenUsage:
    """Single invocation token usage"""
    timestamp: str
    agent: str
    state: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    context_window_max: int
    context_used_percent: float
    cost_usd: Optional[float]

@dataclass
class SessionTokens:
    """Cumulative session token tracking"""
    session_id: str
    agent: str
    invocations: int
    cumulative_input: int
    cumulative_output: int
    cumulative_total: int
    context_remaining: int
    context_used_percent: float
    total_cost_usd: float
    history: list[TokenUsage]

@dataclass
class RunTokenSummary:
    """Full run token summary"""
    run_id: str
    total_input_tokens: int
    total_output_tokens: int
    total_tokens: int
    total_cost_usd: float
    by_agent: dict[str, SessionTokens]
    by_state: dict[str, int]
```

### Token Extraction by Agent

| Agent | Method | Input Field | Output Field |
|-------|--------|-------------|--------------|
| Claude | JSON output | `input_tokens` | `output_tokens` |
| Gemini | API response | `usageMetadata.promptTokenCount` | `usageMetadata.candidatesTokenCount` |
| Codex | API response | `usage.prompt_tokens` | `usage.completion_tokens` |
| Ollama | API response | `prompt_eval_count` | `eval_count` |

### Token Log Format

**token_usage.jsonl:**
```json
{"ts": "2026-01-07T14:30:23Z", "agent": "claude", "state": "draft", "input_tokens": 1250, "output_tokens": 380, "total": 1630, "context_max": 200000, "context_used_pct": 0.8, "cost_usd": 0.0095}
{"ts": "2026-01-07T14:32:45Z", "agent": "gemini", "state": "draft", "input_tokens": 1250, "output_tokens": 425, "total": 1675, "context_max": 1000000, "context_used_pct": 0.2, "cost_usd": 0.0037}
{"ts": "2026-01-07T14:33:01Z", "agent": "codex", "state": "draft", "input_tokens": 1250, "output_tokens": 352, "total": 1602, "context_max": 128000, "context_used_pct": 1.3, "cost_usd": 0.0115}
```

### Context Window Monitoring

```python
def check_context_health(session: SessionTokens) -> dict:
    """Monitor context window usage"""
    return {
        "status": "healthy" if session.context_used_percent < 80 else "warning",
        "used": session.cumulative_total,
        "max": session.context_remaining + session.cumulative_total,
        "remaining": session.context_remaining,
        "percent_used": session.context_used_percent,
        "recommendation": get_recommendation(session)
    }

def get_recommendation(session: SessionTokens) -> str:
    if session.context_used_percent > 90:
        return "Critical: Consider summarizing context or starting new session"
    elif session.context_used_percent > 80:
        return "Warning: Context window filling up"
    elif session.context_used_percent > 60:
        return "Note: Context usage moderate"
    else:
        return "Healthy: Plenty of context remaining"
```

---

## 7. Logging System

### Log Files per Run

| File | Format | Contents |
|------|--------|----------|
| `run_manifest.yaml` | YAML | Run metadata, config, status |
| `state_log.jsonl` | JSONL | State transitions, timing |
| `token_usage.jsonl` | JSONL | Token counts per invocation |
| `agent_logs/{agent}_{state}.jsonl` | JSONL | Full agent interaction |
| `run_summary.md` | Markdown | Human-readable summary |

### State Log Entry

```json
{
  "ts": "2026-01-07T14:33:15Z",
  "event": "fan_out_complete",
  "state": "draft",
  "result": "all_success",
  "duration_s": 172,
  "outputs": {
    "claude": {
      "file": "drafts/claude_draft.md",
      "word_count": 342,
      "tokens": {"input": 1250, "output": 380},
      "preview": "The GPU hit 94°C and the fans sounded like..."
    },
    "gemini": {
      "file": "drafts/gemini_draft.md",
      "word_count": 385,
      "tokens": {"input": 1250, "output": 425},
      "preview": "I wanted to keep everything local. Privacy..."
    },
    "codex": {
      "file": "drafts/gpt_draft.md",
      "word_count": 298,
      "tokens": {"input": 1250, "output": 352},
      "preview": "Self-hosting seemed like the responsible..."
    }
  },
  "token_totals": {
    "input": 3750,
    "output": 1157,
    "total": 4907,
    "cost_usd": 0.0247
  }
}
```

### Agent Log Entry

```json
{
  "ts": "2026-01-07T14:30:23Z",
  "event": "invoke",
  "agent": "claude",
  "state": "draft",
  "persona": "writer",
  "persona_hash": "a1b2c3d4",
  "input_files": ["input/story_input.md"],
  "input_content": {
    "input/story_input.md": "Post 3 raw story about building the content pipeline..."
  },
  "prompt_preview": "You are a writer for Matthew Garcia's LinkedIn...",
  "command": "claude -p '...'"
}
{
  "ts": "2026-01-07T14:32:45Z",
  "event": "complete",
  "agent": "claude",
  "state": "draft",
  "success": true,
  "exit_code": 0,
  "duration_s": 142,
  "output_file": "drafts/claude_draft.md",
  "output_content": "The GPU hit 94°C and the fans sounded like a jet engine...",
  "tokens": {
    "input": 1250,
    "output": 380,
    "total": 1630
  },
  "context": {
    "max": 200000,
    "used": 1630,
    "percent": 0.8
  },
  "cost_usd": 0.0095
}
```

### Run Summary (Markdown)

```markdown
# Workflow Run: 2026-01-07_143022_post03

**Input:** story_bank/processed/post_03.md
**Duration:** 14m 56s
**Status:** Complete

---

## Token Usage Summary

| Agent | Input | Output | Total | Cost |
|-------|-------|--------|-------|------|
| Claude | 4,250 | 1,520 | 5,770 | $0.028 |
| Gemini | 4,250 | 1,680 | 5,930 | $0.014 |
| Codex | 4,250 | 1,410 | 5,660 | $0.032 |
| **Total** | **12,750** | **4,610** | **17,360** | **$0.074** |

### Context Window Status

| Agent | Used | Max | % Used | Status |
|-------|------|-----|--------|--------|
| Claude | 5,770 | 200,000 | 2.9% | Healthy |
| Gemini | 5,930 | 1,000,000 | 0.6% | Healthy |
| Codex | 5,660 | 128,000 | 4.4% | Healthy |

---

## Draft Phase

| Agent | Words | Hook Quality | Specifics | Tokens |
|-------|-------|--------------|-----------|--------|
| Claude | 342 | ⭐⭐⭐ Strong | Missing token speed | 1,630 |
| Gemini | 385 | ⭐⭐ Abstract | Good technical detail | 1,675 |
| Codex | 298 | ⭐⭐ Generic | Strong constraint framing | 1,602 |

## Audit Consensus

All three auditors agreed:
- Claude draft has best hook
- Missing artifact: token generation speed
- Missing artifact: specific error message

## Final Post

**Word count:** 356
**File:** final/final_post.md

### Preview:
> The GPU hit 94°C and the fans sounded like a jet engine.
> Llama 3.2 was generating at 2 tokens per second—I needed 50...

## Final Audit Scores

| Agent | Overall | Hook | Specifics | Voice | Tokens |
|-------|---------|------|-----------|-------|--------|
| Claude | 8/10 | 9/10 | 7/10 | 8/10 | 1,580 |
| Gemini | 8/10 | 9/10 | 8/10 | 7/10 | 1,620 |
| Codex | 9/10 | 9/10 | 8/10 | 9/10 | 1,540 |

## Final Determination

Post is ready for publication. Minor suggestion: add one more
sensory detail in paragraph 3.

---

*Generated by Workflow Runner v1.0*
```

---

## 8. Agent Interface

### Base Agent Class

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

@dataclass
class AgentResult:
    success: bool
    output: str
    exit_code: int
    duration_s: float
    session_id: Optional[str] = None
    tokens: Optional[dict] = None      # {input, output, total}
    context: Optional[dict] = None     # {max, used, percent}
    cost_usd: Optional[float] = None
    error: Optional[str] = None

class BaseAgent(ABC):
    """Abstract base for all agent implementations"""

    def __init__(self, config: dict):
        self.config = config
        self.name = config.get("name", "unknown")
        self.context_window = config.get("context_window", 100000)
        self.cost_per_1k = config.get("cost_per_1k", {"input": 0, "output": 0})

    @abstractmethod
    def invoke(self, prompt: str, input_files: list[str]) -> AgentResult:
        """One-shot invocation (stateless)"""
        pass

    @abstractmethod
    def invoke_with_session(
        self,
        session_id: str,
        prompt: str,
        input_files: list[str]
    ) -> AgentResult:
        """Invocation with session context (stateful)"""
        pass

    @abstractmethod
    def extract_tokens(self, raw_response: str) -> dict:
        """Extract token counts from agent response"""
        pass

    @abstractmethod
    def supports_native_session(self) -> bool:
        """Does this agent have native session support?"""
        pass

    @property
    @abstractmethod
    def session_type(self) -> str:
        """'native', 'file', or 'none'"""
        pass

    def calculate_cost(self, tokens: dict) -> float:
        """Calculate cost in USD"""
        input_cost = (tokens["input"] / 1000) * self.cost_per_1k["input"]
        output_cost = (tokens["output"] / 1000) * self.cost_per_1k["output"]
        return input_cost + output_cost

    def calculate_context_usage(self, tokens: dict) -> dict:
        """Calculate context window usage"""
        total = tokens.get("total", tokens["input"] + tokens["output"])
        return {
            "max": self.context_window,
            "used": total,
            "percent": (total / self.context_window) * 100
        }
```

### Agent Factory

```python
# runner/agents/__init__.py

from .claude import ClaudeAgent
from .gemini import GeminiAgent
from .codex import CodexAgent
from .ollama import OllamaAgent

AGENT_REGISTRY = {
    "claude": ClaudeAgent,
    "gemini": GeminiAgent,
    "codex": CodexAgent,
    "ollama": OllamaAgent,
}

def create_agent(name: str, config: dict, session_dir: str) -> BaseAgent:
    """Factory to create agent instances"""
    agent_type = config.get("type", name)

    if agent_type not in AGENT_REGISTRY:
        raise ValueError(f"Unknown agent type: {agent_type}")

    agent_config = {**config, "name": name}
    return AGENT_REGISTRY[agent_type](agent_config, session_dir)
```

---

## 9. Session Management

### Native Session (Claude, Gemini, Codex)

**IMPORTANT:** CLI tools generate their own opaque session IDs. We must capture the real ID from the first invocation's output, not use a friendly name.

```python
# runner/sessions/native.py

import re
import os
import json
from typing import Optional

class NativeSessionManager:
    """For agents with built-in --resume support"""

    # Regex patterns to extract session IDs from CLI output
    SESSION_PATTERNS = {
        "claude": r"Session(?:\s+ID)?:\s*(\S+)",
        "gemini": r"session_id[\"']?:\s*[\"']?(\S+)[\"']?",
        "codex": r"Session\s+ID:\s*(\S+)"
    }

    def __init__(self, agent_name: str, session_dir: str):
        self.agent_name = agent_name
        self.session_dir = session_dir
        self.session_file = f"{session_dir}/{agent_name}_session.json"
        self.session_id = self._load_session_id()

    def _load_session_id(self) -> Optional[str]:
        """Load persisted session ID if exists."""
        if os.path.exists(self.session_file):
            with open(self.session_file) as f:
                return json.load(f).get("session_id")
        return None

    def capture_session_id(self, cli_output: str) -> Optional[str]:
        """Parse CLI output to extract real session ID.

        Call this after the first invocation to capture the CLI-generated ID.
        """
        pattern = self.SESSION_PATTERNS.get(self.agent_name)
        if not pattern:
            return None

        match = re.search(pattern, cli_output, re.IGNORECASE)
        if match:
            self.session_id = match.group(1)
            self._persist_session_id()
            return self.session_id
        return None

    def _persist_session_id(self):
        """Save session ID to disk for resume across runs."""
        os.makedirs(self.session_dir, exist_ok=True)
        with open(self.session_file, "w") as f:
            json.dump({
                "session_id": self.session_id,
                "agent": self.agent_name
            }, f, indent=2)

    def has_session(self) -> bool:
        """Check if we have a valid session ID."""
        return self.session_id is not None

    def get_command(self, agent_config: dict, prompt: str) -> str:
        """Get command - uses resume_command from config if session exists.

        IMPORTANT: Uses resume_command from config to preserve JSON output flags.
        Hardcoding commands here would drop --output-format json, breaking token tracking.
        """
        import shlex
        safe_prompt = shlex.quote(prompt)  # Prevent shell injection

        if not self.session_id:
            # First invocation - use base command from config
            return agent_config["command"].format(prompt=safe_prompt)

        # Subsequent invocations - use resume_command from config (preserves JSON flags)
        return agent_config["resume_command"].format(
            session_id=self.session_id,
            prompt=safe_prompt
        )

    def clear_session(self):
        """Clear session (e.g., when starting a new workflow run)."""
        self.session_id = None
        if os.path.exists(self.session_file):
            os.remove(self.session_file)
```

### Session Capture Flow

```python
# In runner/agents/base.py

def invoke(self, prompt: str) -> dict:
    """Invoke agent and capture session ID if first call."""

    command = self.session_manager.get_command(self.config, prompt)
    result = subprocess.run(command, shell=True, capture_output=True, text=True)

    # On first invocation, capture the CLI-generated session ID
    if not self.session_manager.has_session():
        self.session_manager.capture_session_id(result.stdout)

    return self.parse_result(result)
```

### Shell Injection Prevention

**IMPORTANT:** Prompts can contain apostrophes, quotes, and shell metacharacters.

The `get_command()` method uses `shlex.quote()` to safely escape prompts before
shell execution. This prevents injection like:

```
Prompt: "'; rm -rf / #"
Without escaping: claude -p ''; rm -rf / #''
With shlex.quote: claude -p ''\''; rm -rf / #'  (safely quoted)
```

**Alternative (Preferred for new code):** Use subprocess with args list, no shell:

```python
# Option B: No shell=True, build args list directly
def invoke_safe(self, prompt: str) -> dict:
    """Invoke agent safely without shell."""
    args = ["claude", "--output-format", "json", "-p", prompt]
    result = subprocess.run(args, capture_output=True, text=True)
    return self.parse_result(result)
```

This approach is inherently safe because the prompt is never parsed by a shell.

### File-Based Session (Ollama)

```python
# runner/sessions/file_based.py

class FileBasedSessionManager:
    """For agents without native session support"""

    def __init__(self, session_dir: str, max_messages: int = 50):
        self.session_dir = session_dir
        self.max_messages = max_messages

    def load_session(self, session_id: str) -> dict:
        path = f"{self.session_dir}/{session_id}.json"
        if os.path.exists(path):
            return json.load(open(path))
        return {"session_id": session_id, "messages": [], "tokens": []}

    def save_session(self, session: dict):
        path = f"{self.session_dir}/{session['session_id']}.json"
        json.dump(session, open(path, "w"), indent=2)

    def add_message(self, session: dict, role: str, content: str, tokens: dict):
        session["messages"].append({
            "role": role,
            "content": content,
            "tokens": tokens,
            "timestamp": datetime.utcnow().isoformat()
        })
        session["tokens"].append(tokens)
        return self.trim_if_needed(session)

    def trim_if_needed(self, session: dict) -> dict:
        """Keep session within max_messages limit"""
        messages = session["messages"]
        if len(messages) <= self.max_messages:
            return session

        # Keep system prompt + last N messages
        system = [m for m in messages if m["role"] == "system"]
        rest = [m for m in messages if m["role"] != "system"]
        session["messages"] = system + rest[-(self.max_messages - len(system)):]
        return session

    def get_context_for_ollama(self, session: dict) -> list:
        """Format messages for Ollama API"""
        return [
            {"role": m["role"], "content": m["content"]}
            for m in session["messages"]
        ]
```

---

## 10. Makefile Commands

```makefile
# ============================================================================
# WORKFLOW COMMANDS
# ============================================================================

.PHONY: workflow workflow-step check-config check-gpu logs

# Run full workflow
# Usage: make workflow STORY=post_03
workflow:
ifndef STORY
	$(error STORY required. Usage: make workflow STORY=post_03)
endif
	@python3 -m runner.runner --config workflow_config.yaml --story $(STORY)

# Run single workflow step
# Usage: make workflow-step STEP=draft
workflow-step:
ifndef STEP
	$(error STEP required. Usage: make workflow-step STEP=draft)
endif
	@python3 -m runner.runner --config workflow_config.yaml --step $(STEP)

# Validate configuration
check-config:
	@python3 -m runner.config --validate workflow_config.yaml

# Check GPU resources (for Ollama)
check-gpu:
	@python3 -m runner.agents.ollama --check-resources

# ============================================================================
# LOG COMMANDS
# ============================================================================

# List all runs
logs:
	@ls -la workflow/runs/

# Show state log for a run
# Usage: make log-states RUN=2026-01-07_143022_post03
log-states:
ifndef RUN
	$(error RUN required)
endif
	@cat workflow/runs/$(RUN)/state_log.jsonl | python3 -m json.tool

# Show token usage for a run
log-tokens:
ifndef RUN
	$(error RUN required)
endif
	@cat workflow/runs/$(RUN)/token_usage.jsonl | python3 -c "\
		import sys, json; \
		total_in, total_out, total_cost = 0, 0, 0; \
		for line in sys.stdin: \
			d = json.loads(line); \
			total_in += d['input_tokens']; \
			total_out += d['output_tokens']; \
			total_cost += d.get('cost_usd', 0); \
		print(f'Input: {total_in:,} tokens'); \
		print(f'Output: {total_out:,} tokens'); \
		print(f'Total: {total_in + total_out:,} tokens'); \
		print(f'Cost: \${total_cost:.4f}')"

# Show run summary
log-summary:
ifndef RUN
	$(error RUN required)
endif
	@cat workflow/runs/$(RUN)/run_summary.md

# ============================================================================
# PERSONA COMMANDS
# ============================================================================

# List personas
list-personas:
	@ls -la prompts/*.md

# Validate personas have required sections
check-personas:
	@python3 -m runner.config --validate-personas prompts/
```

---

## 11. Persona Prompts

### orchestrator_persona.md (Summary)

The orchestrator:
- Reads workflow config and understands states
- Makes decisions about transitions
- Evaluates outputs and determines quality
- Logs reasoning for all decisions
- Knows when to retry vs proceed vs halt

### writer_persona.md (Summary)

Derived from CLAUDE.md voice guidelines:
- 250-400 words, flowing prose
- No bullets, no headers, no CTAs
- Sensory details, failure artifacts, tangible consequences
- Attack the chapter's enemy
- Signature phrases used sparingly

### auditor_persona.md (Summary)

The quality gate:
- Hook checklist (sensory, artifacts, consequences)
- 5 elements check (failure, misconception, AI amplification, fix, scar)
- Vague language scan (flag category words without artifacts)
- Shape compliance (FULL/PARTIAL/OBSERVATION/SHORT)
- Entry point variation check
- Provide specific line-by-line feedback

### synthesizer_persona.md (Summary)

The combiner:
- Read all drafts and audits
- Identify best elements from each
- Combine without losing voice consistency
- Resolve conflicts between recommendations
- Output single cohesive post

---

## 12. Build Phases

| Phase | Components | Priority | Dependencies |
|-------|------------|----------|--------------|
| **1** | Base agent interface (`agents/base.py`) | Now | None |
| **2** | Claude agent (`agents/claude.py`) | Now | Phase 1 |
| **3** | Gemini agent (`agents/gemini.py`) | Now | Phase 1 |
| **4** | Codex agent (`agents/codex.py`) | Now | Phase 1 |
| **5** | Token tracking (`metrics/tokens.py`) | Now | Phases 2-4 |
| **6** | State machine (`state_machine.py`) | Now | Phase 1 |
| **7** | Logging system (`logging/`) | Now | Phases 5-6 |
| **8** | Runner (`runner.py`) | Now | Phases 1-7 |
| **9** | Persona prompts (`prompts/`) | Now | None |
| **10** | Config + Makefile | Now | Phases 1-9 |
| **11** | Historical tracking (`history/`) | ✅ Done | Phases 7-8 |
| **12** | Evaluation queries + CLI | ✅ Done | Phase 11 |
| **13** | MCP server layer (optional) | Later | Phases 1-12 |
| **14** | Ollama agent + file sessions | ✅ Done | Phases 1-12 |
| **15** | Dashboard (Evaluation UI) | ✅ Done | Phase 11-12 |

---

## 13. Circuit Breakers (Rule-Based)

### The Problem

Without safeguards, the state machine can loop infinitely:
```
draft → draft-check → draft → draft-check → draft → ...
```

### Design Principle

**Circuit breakers are rule-based.** They don't think. They break.

When a rule triggers:
1. Execution **STOPS** immediately
2. Orchestrator is **INFORMED** with full context
3. Orchestrator **DECIDES** what to do

### Rules (Config)

```yaml
# workflow_config.yaml

circuit_breaker:
  rules:
    - name: state_visit_limit
      condition: "state_visits[state] >= 3"

    - name: cycle_detection
      condition: "A→B→A→B pattern in last 4 transitions"

    - name: transition_limit
      condition: "transition_count >= 20"

    - name: timeout
      condition: "elapsed_s >= 1800"

    - name: cost_limit
      condition: "total_cost_usd >= 5.00"

  # Hard limits (safety net - orchestrator can't override)
  safety_limits:
    max_transitions_hard: 50
    max_runtime_hard: 3600          # 1 hour
    max_cost_hard: 10.00            # $10
```

### Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                     CIRCUIT BREAKER                              │
│                   (rule-based, mechanical)                       │
│                                                                  │
│  Tracks: state visits, transitions, time, cost                  │
│  Checks: rules on every transition                              │
│  On rule trigger: BREAK                                         │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ rule triggered → BREAK
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                       ORCHESTRATOR                               │
│                   (informed, then decides)                       │
│                                                                  │
│  Receives:                                                       │
│  • Which rule triggered                                          │
│  • Full state history                                            │
│  • All outputs so far                                            │
│  • Quality scores                                                │
│                                                                  │
│  Decides:                                                        │
│  • force_complete - use best output, finish                     │
│  • retry_different - new guidance, retry                        │
│  • halt - stop, mark failed                                     │
│  • dump_context - error out with debug info                     │
└─────────────────────────────────────────────────────────────────┘
```

### Implementation

```python
# runner/circuit_breaker.py

class CircuitBreaker:
    """Rule-based. No LLM decisions here."""

    def __init__(self, config: dict):
        self.rules = config.get("rules", [])
        self.safety_limits = config.get("safety_limits", {})
        self.state_visits = defaultdict(int)
        self.transition_history = []
        self.transition_count = 0
        self.start_time = time.time()
        self.total_cost = 0.0

    def check(self, from_state: str, to_state: str) -> dict:
        """Check rules. Returns break info if triggered."""

        self.state_visits[to_state] += 1
        self.transition_count += 1
        self.transition_history.append((from_state, to_state))

        for rule in self.rules:
            if self.evaluate_rule(rule, to_state):
                return {
                    "triggered": True,
                    "rule": rule["name"],
                    "context": self.get_context()
                }

        return {"triggered": False}

    def evaluate_rule(self, rule: dict, state: str) -> bool:
        if rule["name"] == "state_visit_limit":
            return self.state_visits[state] >= 3

        elif rule["name"] == "cycle_detection":
            return self.detect_cycle()

        elif rule["name"] == "transition_limit":
            return self.transition_count >= 20

        elif rule["name"] == "timeout":
            return (time.time() - self.start_time) >= 1800

        elif rule["name"] == "cost_limit":
            return self.total_cost >= 5.00

        return False

    def detect_cycle(self) -> bool:
        """Detect A→B→A→B pattern"""
        if len(self.transition_history) < 4:
            return False
        recent = self.transition_history[-4:]
        return recent[:2] == recent[2:]

    def get_context(self) -> dict:
        return {
            "state_visits": dict(self.state_visits),
            "transition_history": self.transition_history,
            "transition_count": self.transition_count,
            "elapsed_s": time.time() - self.start_time,
            "total_cost_usd": self.total_cost
        }

    def update_cost(self, cost_usd: float):
        """Call after each agent invocation with the cost."""
        self.total_cost += cost_usd

    def check_safety_limits(self) -> dict:
        """Check hard limits that orchestrator can't override."""
        if self.transition_count >= self.safety_limits.get("max_transitions_hard", 50):
            return {"triggered": True, "rule": "hard_transition_limit", "overridable": False}
        if (time.time() - self.start_time) >= self.safety_limits.get("max_runtime_hard", 3600):
            return {"triggered": True, "rule": "hard_timeout", "overridable": False}
        if self.total_cost >= self.safety_limits.get("max_cost_hard", 10.00):
            return {"triggered": True, "rule": "hard_cost_limit", "overridable": False}
        return {"triggered": False}
```

### Runner Integration

```python
# After each agent call in runner/state_machine.py
tokens = agent.extract_tokens(result)
cost = calculate_cost(tokens, agent.cost_per_1k)
circuit_breaker.update_cost(cost)

# Check safety limits (can't be overridden)
safety_check = circuit_breaker.check_safety_limits()
if safety_check["triggered"]:
    return self.hard_stop(safety_check)
```

### Logging

```json
{
  "ts": "2026-01-07T14:45:00Z",
  "event": "circuit_break",
  "rule": "state_visit_limit",
  "context": {
    "state_visits": {"draft": 3, "draft-check": 3},
    "transition_count": 8,
    "elapsed_s": 423,
    "total_cost_usd": 0.45
  }
}
```

### Makefile Commands

```makefile
log-transitions:
ifndef RUN
	$(error RUN required)
endif
	@cat workflow/runs/$(RUN)/state_log.jsonl | \
		jq -r 'select(.event=="transition") | "\(.from) → \(.to)"'

log-breaker:
ifndef RUN
	$(error RUN required)
endif
	@cat workflow/runs/$(RUN)/state_log.jsonl | \
		jq 'select(.event=="circuit_break")'
```

---

## 14. Quality Gate States (Manager/Auditor)

### Core Insight

**A manager/auditor is just an agent. A quality gate is just a state.**

No special config. No special state types. You add a quality gate by:
1. Adding an agent with a quality-gate persona
2. Adding a state that uses that agent
3. Configuring transitions (proceed, retry, halt)

The circuit breaker (Section 13) prevents infinite retry loops.

### State Types

| Type | Behavior | Example Use |
|------|----------|-------------|
| `initial` | Entry point, no agent | `start` state |
| `fan-out` | Run multiple agents in parallel | `draft`, `cross-audit` |
| `single` | Run one agent | Quality gates, synthesizer |
| `orchestrator-task` | Run orchestrator with session persistence | High-stakes decisions |
| `human-approval` | Pause for CLI confirmation | Final review before complete |
| `terminal` | Exit point | `complete`, `halt` |

### Retry Mechanism

When a quality gate returns `decision: retry`, the runner needs to:
1. Extract the `retry_guidance` from the quality gate output
2. Store it for injection into the target state
3. Transition to the retry target state
4. Inject the feedback as context in the next execution

```python
# runner/state_machine.py

class StateMachine:
    def __init__(self):
        self.retry_feedback = {}  # state_name -> feedback string

    def is_retry_transition(self, result: dict) -> bool:
        """Check if this is a retry decision from a quality gate."""
        return result.get("decision") == "retry"

    def get_retry_target(self, state: dict, result: dict) -> str:
        """Get the target state for a retry transition."""
        # The retry transition in config points to the target
        return state["transitions"].get("retry")

    def store_retry_feedback(self, target_state: str, feedback: str):
        """Store feedback to inject into target state's next execution."""
        self.retry_feedback[target_state] = feedback

    def get_retry_feedback(self, state_name: str) -> Optional[str]:
        """Get and consume stored retry feedback for a state."""
        return self.retry_feedback.pop(state_name, None)

    def execute_state(self, state_name: str) -> dict:
        """Execute a state, injecting retry feedback if available."""
        from copy import deepcopy

        # CRITICAL: Copy state to avoid mutating the canonical config dict
        # Without deepcopy, retry feedback would persist in self.states permanently
        state = deepcopy(self.states[state_name])

        # Check for feedback from a previous retry
        feedback = self.get_retry_feedback(state_name)
        if feedback:
            state["context"] = f"Previous attempt feedback:\n{feedback}"

        # Execute the state
        result = self.run_state(state)

        # Handle retry transition
        if self.is_retry_transition(result):
            target = self.get_retry_target(state, result)
            self.store_retry_feedback(target, result.get("retry_guidance", ""))
            return {"next": target, "transition_type": "retry"}

        # Normal transition
        return {"next": self.get_next_state(state, result)}
```

### Example: Adding a Quality Gate

```yaml
# workflow_config.yaml

agents:
  # Regular agents
  claude:
    type: cli
    command: "claude -p"
    # ...

  gemini:
    type: cli
    command: "gemini"
    # ...

  # Quality gate agent - just another agent
  quality-gate:
    type: cli
    command: "claude -p"            # can use any underlying model
    persona: prompts/quality_gate_persona.md
    session:
      enabled: true

states:
  start:
    type: initial
    next: draft

  draft:
    type: fan-out
    agents: [claude, gemini, codex]
    persona: writer
    input: "input/story_input.md"
    output: "drafts/{agent}_draft.md"
    transitions:
      all_success: draft-check      # → quality gate
      partial_success: draft-check
      all_failure: halt

  draft-check:                      # Quality gate - just a regular state
    type: single
    agent: quality-gate
    input: "drafts/*.md"
    output: "reviews/draft_review.json"
    transitions:
      proceed: cross-audit
      retry: draft                  # back to draft
      halt: halt

  cross-audit:
    type: fan-out
    agents: [claude, gemini, codex]
    persona: auditor
    input: "drafts/*.md"
    output: "audits/{agent}_audit.md"
    transitions:
      all_success: audit-check
      partial_success: audit-check
      all_failure: draft-check

  audit-check:                      # Another quality gate
    type: single
    agent: quality-gate
    input: "audits/*.md"
    output: "reviews/audit_review.json"
    transitions:
      proceed: synthesize
      retry: cross-audit
      halt: halt

  synthesize:
    type: orchestrator-task
    persona: synthesizer
    input:
      - "drafts/*.md"
      - "audits/*.md"
    output: "final/final_post.md"
    transitions:
      success: synth-check

  synth-check:
    type: single
    agent: quality-gate
    input: "final/final_post.md"
    output: "reviews/synth_review.json"
    transitions:
      proceed: final-audit
      retry: synthesize
      halt: halt

  # ... continue pattern
```

### Quality Gate Persona

```markdown
# prompts/quality_gate_persona.md

You are a Quality Gate reviewing AI-generated content.

## Your Task
1. Review the provided outputs
2. Score quality (1-10)
3. Decide: proceed, retry, or halt
4. If retry, provide specific actionable feedback

## Quality Criteria

For drafts:
- Word count 250-400
- Sensory opening (not abstract)
- Specific failure artifacts (not vague)
- Flows as prose
- No bullets/headers

For audits:
- Specific line references
- Concrete improvements
- Actionable recommendations

## Output Format

Return JSON:
{
  "decision": "proceed" | "retry" | "halt",
  "quality_score": 1-10,
  "issues": [
    {"severity": "critical|major|minor", "issue": "...", "fix": "..."}
  ],
  "retry_guidance": "specific instructions for retry"
}
```

### How Retry Feedback Works

When a quality gate returns `retry`, the runner:
1. Captures the `retry_guidance` from the review
2. Injects it into the next invocation of the target state
3. Agents see: "Previous attempt feedback: [guidance]"

```python
# runner/state_machine.py

def execute_state(self, state_name: str) -> dict:
    state = self.states[state_name]

    # Check for retry feedback from previous attempt
    if state_name in self.retry_feedback:
        state["context"] = self.retry_feedback[state_name]

    # Execute state
    outputs = self.run_state(state)

    # Get next state from transitions
    next_state = self.get_next_state(state, outputs)

    # If next state is a quality gate that returns retry
    if self.is_retry_transition(next_state):
        target = next_state["retry_target"]
        self.retry_feedback[target] = next_state["feedback"]
        return {"next": target}

    return {"next": next_state}
```

### Why This Design Works

| Principle | How It's Achieved |
|-----------|-------------------|
| **No special types** | Quality gate is `type: single` like any other |
| **No special config** | Just an agent + persona + transitions |
| **Composable** | Put quality gates anywhere in the workflow |
| **Configurable** | Different personas for different checks |
| **Loop-safe** | Circuit breaker (Section 13) prevents infinite retries |

### State Flow Visualization

```
┌─────────┐     ┌─────────┐     ┌─────────────┐
│  START  │────▶│  DRAFT  │────▶│ DRAFT-CHECK │
└─────────┘     └─────────┘     └──────┬──────┘
                     ▲                 │
                     │ retry           │ proceed
                     └─────────────────┤
                                       ▼
┌─────────────┐     ┌─────────────┐   │
│ AUDIT-CHECK │◀────│ CROSS-AUDIT │◀──┘
└──────┬──────┘     └─────────────┘
       │                   ▲
       │ retry             │
       └───────────────────┘
       │
       │ proceed
       ▼
┌─────────────┐     ┌─────────────┐
│ SYNTH-CHECK │◀────│  SYNTHESIZE │
└──────┬──────┘     └─────────────┘
       │                   ▲
       │ retry             │
       └───────────────────┘
       │
       │ proceed
       ▼
     (continue...)
```

### Multiple Quality Gate Types

You can have different quality gates for different purposes:

```yaml
agents:
  # Strict quality gate for final output
  quality-gate-strict:
    type: cli
    command: "claude -p"
    persona: prompts/quality_gate_strict.md

  # Lenient gate for early stages
  quality-gate-lenient:
    type: cli
    command: "gemini"
    persona: prompts/quality_gate_lenient.md

  # Technical reviewer
  tech-reviewer:
    type: cli
    command: "codex"
    persona: prompts/tech_reviewer.md

states:
  draft-check:
    type: single
    agent: quality-gate-lenient     # lenient early
    # ...

  final-check:
    type: single
    agent: quality-gate-strict      # strict at end
    # ...
```

### Human Approval State

Before completing a workflow, a human should review the final output. The `human-approval` state type pauses execution and waits for CLI input.

```yaml
states:
  # ... existing states ...

  final-audit:
    type: single
    agent: quality-gate-strict
    input: "final/final_post.md"
    output: "reviews/final_review.json"
    transitions:
      proceed: human-approval       # Go to human approval
      retry: synthesize
      halt: halt

  human-approval:
    type: human-approval
    input: "final/final_post.md"
    prompt: |
      Review the final post above.
      - Type 'yes' to approve and complete
      - Type 'abort' to cancel the workflow
      - Type anything else to provide feedback and retry synthesis
    transitions:
      approved: complete
      feedback: synthesize          # Inject feedback and retry
      abort: halt

  complete:
    type: terminal
    status: success

  halt:
    type: terminal
    status: failed
```

**Implementation:**

```python
# runner/state_machine.py

def execute_human_approval(self, state: dict) -> dict:
    """Pause and wait for human input."""
    input_file = state.get("input")

    # Display the content for review
    print(f"\n{'='*60}")
    print("HUMAN APPROVAL REQUIRED")
    print(f"{'='*60}")

    if input_file and os.path.exists(input_file):
        print(f"\n--- {input_file} ---")
        with open(input_file) as f:
            print(f.read())
        print(f"--- end {input_file} ---\n")

    print(state.get("prompt", "Approve? (yes/no/feedback)"))

    response = input("\n> ").strip()

    if response.lower() == "yes":
        self.log({"event": "human_approval", "decision": "approved"})
        return {"decision": "approved"}
    elif response.lower() == "abort":
        self.log({"event": "human_approval", "decision": "abort"})
        return {"decision": "abort"}
    else:
        self.log({"event": "human_approval", "decision": "feedback", "feedback": response})
        # Store feedback for injection into retry target
        target = state["transitions"].get("feedback")
        if target:
            self.store_retry_feedback(target, response)
        return {"decision": "feedback"}
```

**Why This Matters:**

- Prevents wasted cycles if the synthesizer produces a generic post
- Human can steer the workflow without restarting from scratch
- Feedback is injected into the retry, improving next attempt

### Runner vs Orchestrator Roles

The **runner** is mechanical. The **orchestrator** is intelligent.

```
┌─────────────────────────────────────────────────────────────────┐
│                        ORCHESTRATOR                              │
│                   (watches everything)                           │
│                                                                  │
│  • Monitors all state transitions                                │
│  • Decides when to break loops (not hardcoded limits)           │
│  • Determines if workflow is done or stuck                      │
│  • Can intervene at any point                                   │
│  • Has full context via persistent session                      │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               │ observes + directs
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                          RUNNER                                  │
│                    (executes mechanically)                       │
│                                                                  │
│  • Executes states                                               │
│  • Invokes agents                                                │
│  • Manages files                                                 │
│  • Logs everything                                               │
│  • Reports to orchestrator                                       │
└─────────────────────────────────────────────────────────────────┘
```

### Orchestrator Responsibilities

| Responsibility | How |
|---------------|-----|
| **Loop detection** | Orchestrator sees pattern, decides to break (not hardcoded limit) |
| **Completion** | Orchestrator decides "good enough" based on quality, not just state reached |
| **Intervention** | Orchestrator can inject guidance mid-workflow |
| **Escalation** | When quality gates disagree, orchestrator decides |
| **Context** | Orchestrator has persistent session, remembers full history |

### When Circuit Breaker Triggers

See **Section 13** for circuit breaker rules and implementation. When a break triggers, the state machine handles it as follows:

```python
# runner/state_machine.py

def transition(self, from_state: str, to_state: str) -> dict:
    """Attempt state transition"""

    # Check circuit breaker (rule-based)
    check = self.circuit_breaker.check(from_state, to_state)

    if check["triggered"]:
        # STOP execution immediately
        # Notify orchestrator with full context
        return self.handle_circuit_break(check)

    # Normal transition
    return self.execute_transition(from_state, to_state)

def handle_circuit_break(self, break_info: dict) -> dict:
    """Handle a circuit break - inform orchestrator"""

    # Log the break
    self.log({
        "event": "circuit_break",
        "rule": break_info["rule"],
        "context": break_info["context"]
    })

    # Inform orchestrator and get decision
    decision = self.orchestrator.invoke_with_session(
        session_id=self.orchestrator_session,
        prompt=f"""
## Circuit Break

A circuit breaker rule was triggered. Execution has stopped.

**Rule triggered:** {break_info["rule"]}

**Full context:**
- State visits: {break_info["context"]["state_visits"]}
- Transition history: {break_info["context"]["transition_history"]}
- Total transitions: {break_info["context"]["transition_count"]}
- Elapsed time: {break_info["context"]["elapsed_s"]}s
- Total cost: ${break_info["context"]["total_cost_usd"]:.2f}

**Available outputs:**
{self.list_available_outputs()}

**Quality scores so far:**
{self.get_quality_scores()}

## Your Options

1. **force_complete** - Use the best available output and finish
2. **retry_different** - Provide new guidance and retry from a specific state
3. **halt** - Stop workflow, mark as failed
4. **dump_context** - Error out and dump full context for debugging

What should we do? Respond with your decision and reasoning.
""",
        input_files=self.get_output_files()
    )

    return self.execute_orchestrator_decision(decision)
```

### Orchestrator Response Examples

**Force complete:**
```json
{
  "decision": "force_complete",
  "reasoning": "Quality plateaued at 6/10 after 3 attempts. Best draft is claude_draft_v2.md.",
  "use_output": "drafts/claude_draft_v2.md",
  "proceed_from": "synthesize"
}
```

**Retry different:**
```json
{
  "decision": "retry_different",
  "reasoning": "All drafts missing sensory details. Retry with explicit instruction.",
  "retry_from": "draft",
  "guidance": "Focus on the GPU temperature. What did the screen show? What sound?"
}
```

**Halt:**
```json
{
  "decision": "halt",
  "reasoning": "Input story lacks required failure artifact. Cannot produce quality output.",
  "error": "Missing required story element: failure artifact"
}
```

**Dump context:**
```json
{
  "decision": "dump_context",
  "reasoning": "Unexpected state. Dumping for debugging.",
  "dump_path": "workflow/runs/xxx/debug_dump.json"
}
```

### Orchestrator Checkpoints

The orchestrator is consulted at key moments:

```yaml
orchestrator:
  agent: claude
  persona: prompts/orchestrator_persona.md
  session:
    enabled: true

  checkpoints:
    - on: loop_warning           # circuit breaker triggered
    - on: quality_gate_disagree  # multiple gates give different scores
    - on: repeated_retry         # same state retried 2+ times
    - on: timeout_warning        # approaching timeout
    - on: workflow_complete      # final review before done
```

### Example: Orchestrator Breaking a Loop

```json
{
  "ts": "2026-01-07T14:50:00Z",
  "event": "orchestrator_decision",
  "trigger": "loop_warning",
  "warnings": [
    "State 'draft' visited 3x",
    "Potential cycle: draft → draft-check → draft"
  ],
  "context": {
    "quality_scores": {"draft_v1": 4, "draft_v2": 5, "draft_v3": 6},
    "trend": "improving"
  },
  "orchestrator_response": {
    "decision": "proceed",
    "reasoning": "Quality is improving each iteration. Allow one more try.",
    "override_limit": true
  }
}
```

vs.

```json
{
  "ts": "2026-01-07T14:55:00Z",
  "event": "orchestrator_decision",
  "trigger": "loop_warning",
  "warnings": [
    "State 'draft' visited 4x",
    "Cycle confirmed"
  ],
  "context": {
    "quality_scores": {"draft_v1": 4, "draft_v2": 5, "draft_v3": 5, "draft_v4": 5},
    "trend": "plateaued"
  },
  "orchestrator_response": {
    "decision": "force_complete",
    "reasoning": "Quality plateaued at 5/10. Use draft_v3 (best) and proceed.",
    "use_output": "drafts/draft_v3/claude_draft.md"
  }
}
```

### Hard Limits (Safety Net)

The runner still has hard limits as a safety net in case orchestrator fails:

```yaml
safety_limits:
  max_transitions_hard: 50        # absolute max, orchestrator can't override
  max_runtime_hard: 3600          # 1 hour absolute max
  max_cost_hard: 10.00            # $10 max spend
```

These exist to prevent runaway costs if orchestrator makes bad decisions.

### No Special Manager Code

With this design:

1. **Quality gates** — just states with `type: single` and a quality-gate persona
2. **Retry logic** — transitions that point back
3. **Loop detection** — circuit breaker signals + orchestrator decisions
4. **Completion** — orchestrator decides, not hardcoded state

All existing state machine logic, plus orchestrator consultation at checkpoints.

---

## 15. Open Questions

### Resolved
- ✅ Session management: Use native CLI flags for Claude/Gemini/Codex, file-based for Ollama
- ✅ Token tracking: Extract from each agent's response format
- ✅ Ollama model selection: GPU-aware tiers based on VRAM
- ✅ MCP: Optional layer, not required for core functionality
- ✅ Loop prevention: Circuit breaker with state visit limits, transition limits, cycle detection

### To Decide
- [ ] Should orchestrator be configurable per-run, or fixed in config?
- [ ] How to handle partial failures in fan-out (e.g., 2/3 succeed)?
- [ ] Should we support mid-workflow manual intervention?
- [ ] Notification system for long-running workflows?

---

## 15. Success Criteria

### Phase 1-10 Complete When:
- [ ] `make workflow STORY=post_03` runs full pipeline
- [ ] All three agents (Claude, Gemini, Codex) produce drafts
- [ ] Cross-audit compares all three drafts
- [ ] Final post combines best elements
- [ ] Full token tracking in logs
- [ ] Human-readable run summary generated
- [ ] Runs are reproducible from logs

### Future (Phase 13):
- [ ] MCP server exposes workflow tools
- [ ] Any MCP-compatible agent can orchestrate

### Completed (Phase 11-12, 14-15):
- [x] Historical tracking with database-backed store
- [x] Evaluation queries + CLI (`make eval-*`)
- [x] Ollama works with GPU-aware model selection
- [x] File-based sessions work for Ollama
- [x] Evaluation dashboard UI with Recharts

---

## 16. References

- [Claude Code Session Management](https://stevekinney.com/courses/ai-development/claude-code-session-management)
- [Gemini CLI Session Management](https://geminicli.com/docs/cli/session-management/)
- [Codex CLI Features](https://developers.openai.com/codex/cli/features/)
- [Ollama Python Conversation History](https://deepwiki.com/ollama/ollama-python/4.7-conversation-history)

---

## 17. Historical Tracking & Evaluation

### Purpose

Track performance across all runs over time to:
- Evaluate which agents perform best for different tasks
- Track cost trends and optimization opportunities
- Compare quality metrics across post iterations
- Identify patterns in audit feedback
- Measure improvement in final post quality

### Historical Database

```
workflow/
└── history/
    ├── runs_index.jsonl            # Flat file backup
    └── exports/                    # CSV/JSON exports for analysis
```

### Schema

```sql
-- Runs table
CREATE TABLE runs (
    run_id TEXT PRIMARY KEY,
    story TEXT,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    status TEXT,                    -- complete, failed, halted
    duration_s REAL,
    total_tokens INTEGER,
    total_cost_usd REAL,
    final_post_path TEXT,
    final_score REAL                -- from final audit
);

-- Agent invocations
CREATE TABLE invocations (
    id INTEGER PRIMARY KEY,
    run_id TEXT,
    agent TEXT,
    state TEXT,                     -- draft, audit, etc.
    persona TEXT,
    started_at TIMESTAMP,
    duration_s REAL,
    success BOOLEAN,
    input_tokens INTEGER,
    output_tokens INTEGER,
    total_tokens INTEGER,
    cost_usd REAL,
    output_word_count INTEGER,
    FOREIGN KEY (run_id) REFERENCES runs(run_id)
);

-- Audit scores (from auditor agents)
CREATE TABLE audit_scores (
    id INTEGER PRIMARY KEY,
    run_id TEXT,
    auditor_agent TEXT,             -- who did the audit
    target_agent TEXT,              -- whose draft was audited
    state TEXT,                     -- cross-audit, final-audit
    overall_score REAL,
    hook_score REAL,
    specifics_score REAL,
    voice_score REAL,
    structure_score REAL,
    feedback TEXT,                  -- full feedback text
    FOREIGN KEY (run_id) REFERENCES runs(run_id)
);

-- Post iterations (same story, multiple runs)
CREATE TABLE post_iterations (
    story TEXT,
    run_id TEXT,
    iteration INTEGER,
    final_score REAL,
    total_cost_usd REAL,
    improvements TEXT,              -- what changed from last iteration
    PRIMARY KEY (story, run_id),
    FOREIGN KEY (run_id) REFERENCES runs(run_id)
);
```

### Metrics Tracked

| Metric | Level | Purpose |
|--------|-------|---------|
| **Token usage** | Per invocation | Cost tracking, context monitoring |
| **Duration** | Per invocation, per run | Performance optimization |
| **Audit scores** | Per draft, per agent | Quality comparison |
| **Word count** | Per draft | Consistency with 250-400 target |
| **Final score** | Per run | Overall quality tracking |
| **Cost** | Per run, cumulative | Budget monitoring |

### Evaluation Queries

```python
# runner/history/queries.py

class HistoryQueries:
    def __init__(self, db_url: str):
        self.conn = psycopg.connect(db_url)

    def agent_performance_over_time(self, agent: str) -> pd.DataFrame:
        """Track an agent's audit scores over time"""
        return pd.read_sql("""
            SELECT
                r.run_id,
                r.started_at,
                AVG(a.overall_score) as avg_score,
                AVG(a.hook_score) as avg_hook,
                AVG(a.specifics_score) as avg_specifics
            FROM audit_scores a
            JOIN runs r ON a.run_id = r.run_id
            WHERE a.target_agent = ?
            GROUP BY r.run_id
            ORDER BY r.started_at
        """, self.conn, params=(agent,))

    def cost_by_agent(self) -> pd.DataFrame:
        """Total cost by agent across all runs"""
        return pd.read_sql("""
            SELECT
                agent,
                COUNT(*) as invocations,
                SUM(total_tokens) as total_tokens,
                SUM(cost_usd) as total_cost,
                AVG(cost_usd) as avg_cost_per_invocation
            FROM invocations
            GROUP BY agent
            ORDER BY total_cost DESC
        """, self.conn)

    def best_agent_for_task(self, state: str) -> pd.DataFrame:
        """Which agent performs best for a given task (draft, audit)?"""
        return pd.read_sql("""
            SELECT
                i.agent,
                AVG(a.overall_score) as avg_score,
                COUNT(*) as sample_size
            FROM invocations i
            JOIN audit_scores a ON i.run_id = a.run_id
                AND i.agent = a.target_agent
            WHERE i.state = ?
            GROUP BY i.agent
            ORDER BY avg_score DESC
        """, self.conn, params=(state,))

    def post_iteration_improvement(self, story: str) -> pd.DataFrame:
        """Track quality improvement across iterations of same post"""
        return pd.read_sql("""
            SELECT
                iteration,
                final_score,
                total_cost_usd,
                improvements
            FROM post_iterations
            WHERE story = ?
            ORDER BY iteration
        """, self.conn, params=(story,))

    def weekly_summary(self) -> pd.DataFrame:
        """Weekly cost and quality summary"""
        return pd.read_sql("""
            SELECT
                strftime('%Y-%W', started_at) as week,
                COUNT(*) as runs,
                AVG(final_score) as avg_quality,
                SUM(total_cost_usd) as total_cost,
                SUM(total_tokens) as total_tokens
            FROM runs
            WHERE status = 'complete'
            GROUP BY week
            ORDER BY week
        """, self.conn)
```

### Makefile Commands for Evaluation

```makefile
# ============================================================================
# EVALUATION COMMANDS
# ============================================================================

# Show agent performance comparison
eval-agents:
	@python3 -m runner.history.eval --query agent_comparison

# Show cost breakdown by agent
eval-costs:
	@python3 -m runner.history.eval --query cost_by_agent

# Show quality trend over time
eval-trend:
	@python3 -m runner.history.eval --query quality_trend

# Show iterations for a specific post
eval-post:
ifndef STORY
	$(error STORY required)
endif
	@python3 -m runner.history.eval --query post_iterations --story $(STORY)

# Export all metrics to CSV
eval-export:
	@python3 -m runner.history.eval --export workflow/history/exports/

# Weekly summary report
eval-weekly:
	@python3 -m runner.history.eval --query weekly_summary
```

### Sample Evaluation Output

```
$ make eval-agents

Agent Performance Comparison (Last 30 Days)
============================================

| Agent  | Avg Score | Hook | Specifics | Voice | Runs |
|--------|-----------|------|-----------|-------|------|
| Claude | 8.2       | 8.8  | 7.4       | 8.5   | 12   |
| Gemini | 7.9       | 7.5  | 8.6       | 7.2   | 12   |
| Codex  | 8.0       | 8.1  | 8.0       | 8.2   | 12   |

Insights:
- Claude consistently best at hooks
- Gemini provides most technical specifics
- Codex most balanced across categories

$ make eval-costs

Cost by Agent (All Time)
========================

| Agent  | Invocations | Tokens    | Cost    | Avg/Run |
|--------|-------------|-----------|---------|---------|
| Claude | 48          | 185,000   | $2.85   | $0.06   |
| Codex  | 48          | 172,000   | $3.10   | $0.06   |
| Gemini | 48          | 195,000   | $1.45   | $0.03   |
| Total  | 144         | 552,000   | $7.40   | $0.15   |

$ make eval-post STORY=post_03

Post Iterations: post_03
========================

| Iter | Date       | Score | Cost  | Changes |
|------|------------|-------|-------|---------|
| 1    | 2026-01-07 | 7.2   | $0.15 | Initial |
| 2    | 2026-01-08 | 8.1   | $0.14 | Added GPU temp detail |
| 3    | 2026-01-09 | 8.8   | $0.13 | Stronger hook |

Trend: +1.6 score improvement over 3 iterations
```

### Run Summary with Historical Context

The run_summary.md now includes comparison to previous runs:

```markdown
## Historical Context

### This Post (post_03)
- **Iteration:** 3 of 3
- **Previous best score:** 8.1
- **Current score:** 8.8 (+0.7 improvement)

### Agent Performance (Last 10 Runs)
| Agent | This Run | Avg | Trend |
|-------|----------|-----|-------|
| Claude | 8.5 | 8.2 | ↑ +0.3 |
| Gemini | 8.2 | 7.9 | ↑ +0.3 |
| Codex | 9.0 | 8.0 | ↑ +1.0 |

### Cost Comparison
- **This run:** $0.13
- **Average run:** $0.15
- **Trend:** 13% below average (efficiency improving)
```

---

## 18. Testing Strategy

### Test Structure

```
tests/
├── unit/                    # Fast, no API calls, mock everything
│   ├── test_state_machine.py
│   ├── test_circuit_breaker.py
│   ├── test_session_manager.py
│   └── test_token_tracker.py
├── integration/             # Fixture-based, mock agents but real file IO
│   ├── test_workflow_execution.py
│   ├── test_fanout_coordination.py
│   └── fixtures/
│       ├── sample_drafts/
│       └── sample_audits/
├── e2e/                     # Real API calls (run sparingly, costs money)
│   └── test_full_workflow.py
└── conftest.py              # Shared fixtures and MockAgent
```

### Pydantic Models for LLM Outputs

Use Pydantic for type-safe, validated LLM responses. This eliminates JSON parsing errors and provides clear schemas.

```python
# runner/models.py

from pydantic import BaseModel, Field
from typing import Literal, Optional

class TokenUsage(BaseModel):
    """Token counts from an agent invocation."""
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)

    @property
    def total(self) -> int:
        return self.input_tokens + self.output_tokens

class AgentResult(BaseModel):
    """Validated result from any agent invocation."""
    success: bool
    content: str
    tokens: TokenUsage
    session_id: Optional[str] = None
    cost_usd: Optional[float] = None
    error: Optional[str] = None

class AuditIssue(BaseModel):
    """Single issue from an audit."""
    severity: Literal["critical", "major", "minor"]
    issue: str
    fix: str
    line_reference: Optional[str] = None

class AuditResult(BaseModel):
    """Structured output from quality gate audits."""
    score: int = Field(ge=1, le=10)
    decision: Literal["proceed", "retry", "halt"]
    feedback: str
    issues: list[AuditIssue] = []

    @property
    def has_critical_issues(self) -> bool:
        return any(i.severity == "critical" for i in self.issues)

class CircuitBreakerDecision(BaseModel):
    """Orchestrator's response when circuit breaker triggers."""
    decision: Literal["force_complete", "retry_different", "halt", "dump_context"]
    reasoning: str
    use_output: Optional[str] = None    # For force_complete
    retry_from: Optional[str] = None     # For retry_different
    retry_guidance: Optional[str] = None # Feedback for retry
```

### Mock Agent Pattern

```python
# tests/conftest.py

from runner.models import AgentResult, TokenUsage

class MockAgent:
    """Mock agent for testing without API calls."""

    def __init__(self, responses: list[str], tokens_per_call: int = 100):
        self.responses = responses
        self.tokens_per_call = tokens_per_call
        self.call_count = 0
        self.prompts_received: list[str] = []

    def invoke(self, prompt: str) -> AgentResult:
        """Return next canned response."""
        self.prompts_received.append(prompt)
        response = self.responses[self.call_count % len(self.responses)]
        self.call_count += 1

        return AgentResult(
            success=True,
            content=response,
            tokens=TokenUsage(
                input_tokens=len(prompt.split()) * 2,
                output_tokens=self.tokens_per_call
            )
        )

    def reset(self):
        """Reset for new test."""
        self.call_count = 0
        self.prompts_received = []


class FailingAgent(MockAgent):
    """Agent that fails after N successful calls."""

    def __init__(self, responses: list[str], fail_after: int = 1):
        super().__init__(responses)
        self.fail_after = fail_after

    def invoke(self, prompt: str) -> AgentResult:
        if self.call_count >= self.fail_after:
            return AgentResult(
                success=False,
                content="",
                tokens=TokenUsage(input_tokens=0, output_tokens=0),
                error="Simulated failure"
            )
        return super().invoke(prompt)


class TimeoutAgent(MockAgent):
    """Agent that simulates timeout."""

    def __init__(self, delay_seconds: float = 10):
        super().__init__([])
        self.delay = delay_seconds

    def invoke(self, prompt: str) -> AgentResult:
        import time
        time.sleep(self.delay)
        return AgentResult(
            success=False,
            content="",
            tokens=TokenUsage(input_tokens=0, output_tokens=0),
            error="Timeout"
        )
```

### Example Unit Tests

```python
# tests/unit/test_circuit_breaker.py

import pytest
from runner.circuit_breaker import CircuitBreaker

@pytest.fixture
def breaker():
    config = {
        "rules": [
            {"name": "state_visit_limit"},
            {"name": "cycle_detection"},
            {"name": "transition_limit"}
        ],
        "safety_limits": {
            "max_transitions_hard": 50,
            "max_cost_hard": 10.00
        }
    }
    return CircuitBreaker(config)

def test_state_visit_limit_triggers(breaker):
    """Visiting same state 3 times triggers breaker."""
    breaker.check("start", "draft")
    breaker.check("draft", "check")
    breaker.check("check", "draft")
    breaker.check("draft", "check")
    result = breaker.check("check", "draft")  # 3rd visit to draft

    assert result["triggered"] is True
    assert result["rule"] == "state_visit_limit"

def test_cycle_detection_triggers(breaker):
    """A→B→A→B pattern triggers breaker."""
    breaker.check("start", "A")
    breaker.check("A", "B")
    breaker.check("B", "A")
    result = breaker.check("A", "B")  # A→B→A→B detected

    assert result["triggered"] is True
    assert result["rule"] == "cycle_detection"

def test_cost_tracking(breaker):
    """Cost limit triggers when exceeded."""
    breaker.update_cost(4.50)
    assert breaker.check_safety_limits()["triggered"] is False

    breaker.update_cost(6.00)  # Now at $10.50
    result = breaker.check_safety_limits()

    assert result["triggered"] is True
    assert result["rule"] == "hard_cost_limit"
```

### Example Integration Tests

```python
# tests/integration/test_workflow_execution.py

import pytest
from pathlib import Path
from runner.state_machine import StateMachine
from tests.conftest import MockAgent

@pytest.fixture
def mock_agents():
    return {
        "claude": MockAgent(["Draft from Claude: The GPU hit 94°C..."]),
        "gemini": MockAgent(["Draft from Gemini: I wanted to keep..."]),
        "codex": MockAgent(["Draft from Codex: Self-hosting seemed..."])
    }

@pytest.fixture
def workflow_config(tmp_path):
    """Minimal workflow config for testing."""
    return {
        "states": {
            "start": {"type": "initial", "next": "draft"},
            "draft": {
                "type": "fan-out",
                "agents": ["claude", "gemini", "codex"],
                "output": str(tmp_path / "drafts/{agent}_draft.md"),
                "transitions": {
                    "all_success": "complete",
                    "partial_success": "complete",
                    "all_failure": "halt"
                }
            },
            "complete": {"type": "terminal"},
            "halt": {"type": "terminal", "error": True}
        },
        "settings": {"timeout_per_agent": 30}
    }

def test_fanout_creates_all_draft_files(workflow_config, mock_agents, tmp_path):
    """Fan-out state creates one file per agent."""
    sm = StateMachine(workflow_config, agents=mock_agents)
    result = sm.run()

    assert result["final_state"] == "complete"
    assert (tmp_path / "drafts/claude_draft.md").exists()
    assert (tmp_path / "drafts/gemini_draft.md").exists()
    assert (tmp_path / "drafts/codex_draft.md").exists()

def test_partial_failure_still_proceeds(workflow_config, mock_agents, tmp_path):
    """Workflow continues if 2/3 agents succeed."""
    mock_agents["gemini"] = FailingAgent([], fail_after=0)

    sm = StateMachine(workflow_config, agents=mock_agents)
    result = sm.run()

    assert result["final_state"] == "complete"
    assert (tmp_path / "drafts/claude_draft.md").exists()
    assert not (tmp_path / "drafts/gemini_draft.md").exists()
    assert (tmp_path / "drafts/codex_draft.md").exists()
```

### Makefile Commands

```makefile
# ============================================================================
# TEST COMMANDS
# ============================================================================

.PHONY: test test-unit test-int test-e2e coverage

# Run unit tests (fast, no API calls)
test: test-unit

test-unit:
	pytest tests/unit -v --tb=short

# Run integration tests (uses fixtures, mock agents)
test-int:
	pytest tests/integration -v --tb=short

# Run e2e tests (REAL API CALLS - costs money)
test-e2e:
	pytest tests/e2e -v --tb=short -m e2e

# Run all tests with coverage
coverage:
	pytest tests/unit tests/integration \
		--cov=runner \
		--cov-report=html \
		--cov-report=term-missing

# Run specific test file
test-file:
ifndef FILE
	$(error FILE required. Usage: make test-file FILE=tests/unit/test_circuit_breaker.py)
endif
	pytest $(FILE) -v --tb=long
```

### Test Markers

```python
# pytest.ini or pyproject.toml

[tool.pytest.ini_options]
markers = [
    "e2e: marks tests as end-to-end (deselect with '-m \"not e2e\"')",
    "slow: marks tests as slow (deselect with '-m \"not slow\"')",
]
```

### Why Pydantic Over Dataclasses

| Feature | Pydantic | dataclasses |
|---------|----------|-------------|
| **Runtime validation** | Built-in | Requires manual checks |
| **JSON parsing** | `model.model_validate_json(s)` | Manual `json.loads()` + construction |
| **Schema export** | `model.model_json_schema()` | Not available |
| **Error messages** | Clear field-level errors | Generic TypeErrors |
| **Nested validation** | Automatic | Manual |
| **LLM output parsing** | Perfect fit | Requires wrapper |

Example difference:

```python
# With dataclasses (manual validation)
import json
from dataclasses import dataclass

@dataclass
class AuditResult:
    score: int
    decision: str

def parse_audit(raw: str) -> AuditResult:
    data = json.loads(raw)
    if not 1 <= data["score"] <= 10:
        raise ValueError("score must be 1-10")
    if data["decision"] not in ["proceed", "retry", "halt"]:
        raise ValueError("invalid decision")
    return AuditResult(**data)

# With Pydantic (declarative)
from pydantic import BaseModel, Field
from typing import Literal

class AuditResult(BaseModel):
    score: int = Field(ge=1, le=10)
    decision: Literal["proceed", "retry", "halt"]

# Just call:
result = AuditResult.model_validate_json(raw)  # Validation automatic
```

---

## 19. Dashboard (Future)

For visual evaluation, consider a simple dashboard:

```
workflow/
└── dashboard/
    ├── index.html              # Static HTML dashboard
    ├── data.json               # Exported metrics
    └── generate_dashboard.py   # Builds HTML from DB
```

Features:
- Quality trend chart over time
- Cost breakdown pie chart
- Agent comparison bar charts
- Post iteration timeline
- Recent runs table

Could use simple libraries like Chart.js or just generate static HTML.

---

## 20. Future Enhancements

This section documents architectural improvements deferred for Phase 2+. The current CLI-based approach was chosen for:
- **Simplicity** — No SDK setup, API keys already handled by CLI tools
- **Leverage existing tooling** — Claude Code, Gemini CLI, Codex CLI already work
- **Faster MVP development** — Get working system before optimizing

### Enhancement Roadmap

| Enhancement | Current Approach | Recommended Upgrade | Benefit |
|-------------|-----------------|---------------------|---------|
| **Agent Interface** | CLI subprocess | litellm + native SDKs | Reliability, typed responses, no stdout parsing |
| **Data Parsing** | JSON + try/except | Pydantic models | Zero parse errors, type safety, schema validation |
| **Session State** | CLI --resume | Explicit `List[Message]` | Full control over context pruning and message ordering |
| **Observability** | JSONL files | OpenTelemetry / LangSmith | Visual traces, latency waterfall, cost tracking |
| **Orchestration** | Custom state machine | Temporal / Dagster | Durable workflows, built-in retries, persistence |
| **Queue** | subprocess | Redis/RQ or Celery | Horizontal scaling, health checks, task routing |
| **Database** | PostgreSQL | DuckDB / TimescaleDB | Faster analytics queries, better time-series support |

### Why CLI-Based for Now

1. **Claude Code, Gemini CLI, Codex CLI handle auth** — No API key management
2. **Session persistence is built-in** — `--resume` flags handle context
3. **Output is human-readable** — Easy debugging during development
4. **Lower barrier to entry** — No SDK installation or configuration

### When to Upgrade

Consider migrating when:
- **Token tracking becomes unreliable** — CLI JSON parsing is fragile
- **Horizontal scaling needed** — Multiple workflows running in parallel
- **Cost tracking is critical** — Need real-time budget enforcement
- **Context pruning needed** — CLI sessions can't be trimmed

### litellm Migration Path

```python
# Current: CLI-based
command = "claude --output-format json -p 'prompt'"
result = subprocess.run(command, shell=True, capture_output=True)
tokens = parse_json_output(result.stdout)  # Fragile

# Future: litellm
import litellm

response = litellm.completion(
    model="claude-3-opus-20240229",
    messages=[{"role": "user", "content": "prompt"}]
)
tokens = response.usage  # Typed, reliable
```

### Temporal Migration Path

```python
# Current: Custom state machine
class StateMachine:
    def run(self):
        state = "start"
        while state != "complete":
            result = self.execute_state(state)
            state = result["next"]

# Future: Temporal workflow
from temporalio import workflow

@workflow.defn
class ContentWorkflow:
    @workflow.run
    async def run(self, story_id: str):
        drafts = await workflow.execute_activity(
            generate_drafts,
            story_id,
            start_to_close_timeout=timedelta(minutes=5)
        )
        audits = await workflow.execute_activity(
            cross_audit_drafts,
            drafts,
            start_to_close_timeout=timedelta(minutes=5)
        )
        return await workflow.execute_activity(
            synthesize,
            drafts,
            audits
        )
```

### Observability Upgrade

```python
# Current: JSONL logging
with open("state_log.jsonl", "a") as f:
    f.write(json.dumps({"event": "transition", ...}) + "\n")

# Future: OpenTelemetry
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

with tracer.start_as_current_span("execute_state") as span:
    span.set_attribute("state.name", state_name)
    span.set_attribute("agent.name", agent_name)
    result = self.run_state(state)
    span.set_attribute("tokens.total", result.tokens.total)
```

### DuckDB for Analytics

```sql
-- Current: PostgreSQL with pandas
-- Works but slow for large datasets

-- Future: DuckDB (columnar, fast analytics)
SELECT
    agent,
    DATE_TRUNC('week', started_at) as week,
    AVG(overall_score) as avg_score,
    SUM(cost_usd) as total_cost
FROM invocations
WHERE started_at > NOW() - INTERVAL '30 days'
GROUP BY agent, week
ORDER BY week, agent;
```

---

*Last updated: 2026-01-07*
