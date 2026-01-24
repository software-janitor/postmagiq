Groq Implementation Plan (v1)

This document covers Phase 0 of LAUNCH_SIMPLIFICATION_PLAN.md - implementing Groq as the sole LLM provider for launch.

Overview
- Groq is the only enabled LLM provider for launch.
- Use the official Groq Python SDK for backend inference.
- All existing claude/gemini/gpt agents are disabled (enabled: false).
- State machine updated to use Groq agents exclusively.

Dependencies
- groq>=0.12.0 (official Python SDK)
- Environment variables (REQUIRED):
  - GROQ_API_KEY - Groq API key
  - AGENT_MODE=api - Forces SDK-based agents (default is "cli" which will fail for Groq)

Files to Create/Modify
| File | Action | Purpose |
| --- | --- | --- |
| runner/agents/groq_api.py | CREATE | GroqAPIAgent class |
| runner/agents/factory.py | EDIT | Register in API_AGENT_REGISTRY |
| runner/agents/__init__.py | EDIT | Export GroqAPIAgent |
| pyproject.toml | EDIT | Add groq dependency |
| requirements-api.txt | EDIT | Add groq (Docker builds from this, not pyproject.toml) |
| workflows/configs/groq-production.yaml | CREATE | Groq-only workflow config |
| tests/unit/test_api_agents.py | EDIT | Add TestGroqAPIAgent |

**Note:** Groq config goes directly into `workflows/configs/groq-production.yaml` per Phase 11 (Dynamic Workflow Configuration). The legacy `workflow_config.yaml` remains unchanged and will be moved to `workflows/configs/legacy-claude.yaml` as part of Phase 11.2.

---

State Machine Mapping (REQUIRED)

**Target file:** `workflows/configs/groq-production.yaml` (copy structure from legacy config, replace agents)

Current legacy config uses these agents:
| State | Current Agent(s) | Groq Replacement |
| --- | --- | --- |
| orchestrator.agent | claude | groq-llama-70b |
| story-review | gemini | groq-llama-70b |
| story-process | claude | groq-llama-70b |
| draft (fan-out) | [claude-sonnet, gemini-3-pro, gpt-5.2-medium] | [groq-llama-70b, groq-llama-8b, groq-mixtral] |
| cross-audit (fan-out) | [claude-sonnet, gemini-3-pro] | [groq-llama-70b, groq-llama-8b] |
| synthesize | claude | groq-llama-70b |
| final-audit (fan-out) | [claude-sonnet, gemini-3-pro] | [groq-llama-70b, groq-llama-8b] |

Explicit groq-production.yaml structure (copy from legacy, apply these changes):
```yaml
# Orchestrator
orchestrator:
  agent: groq-llama-70b  # was: claude

# States
states:
  story-review:
    agent: groq-llama-70b  # was: gemini

  story-process:
    agent: groq-llama-70b  # was: claude

  draft:
    agents: [groq-llama-70b, groq-llama-8b, groq-mixtral]  # was: [claude-sonnet, gemini-3-pro, gpt-5.2-medium]

  cross-audit:
    agents: [groq-llama-70b, groq-llama-8b]  # was: [claude-sonnet, gemini-3-pro]

  synthesize:
    agent: groq-llama-70b  # was: claude

  final-audit:
    agents: [groq-llama-70b, groq-llama-8b]  # was: [claude-sonnet, gemini-3-pro]
```

---

Groq Agent Definitions (groq-production.yaml)

Groq agent selection is name-based. The factory uses the agent name and prefix, not a `type` field.

**Agent routing mechanism:**
1. State references agent by name (must be `groq-*`, e.g., `groq-llama-70b`)
2. Factory finds `groq` as the base agent from the `groq-*` prefix
3. Factory uses `API_AGENT_REGISTRY["groq"]` → `GroqAPIAgent` (requires AGENT_MODE=api)
4. GroqAPIAgent uses `model` param to select specific Groq model

The `model` parameter selects the specific model. Agent names are explicit so you know exactly what model is used.

```yaml
agents:
  # Groq models (enabled for launch)
  # GroqAPIAgent selected via groq-* name prefix in API mode
  groq-llama-70b:
    enabled: true
    model: llama-70b
    context_window: 128000
    cost_per_1k:
      input: 0.00059
      output: 0.00079

  groq-llama-8b:
    enabled: true
    model: llama-8b
    context_window: 128000
    cost_per_1k:
      input: 0.00005
      output: 0.00008

  groq-mixtral:
    enabled: true
    model: mixtral
    context_window: 32768
    cost_per_1k:
      input: 0.00024
      output: 0.00024

  # Disable all non-Groq agents
  claude:
    enabled: false
  claude-sonnet:
    enabled: false
  claude-opus:
    enabled: false
  claude-haiku:
    enabled: false
  gemini:
    enabled: false
  gemini-2.5-pro:
    enabled: false
  gemini-2.5-flash:
    enabled: false
  gemini-3-pro:
    enabled: false
  codex:
    enabled: false
  gpt-5.2-medium:
    enabled: false
  gpt-5.2-high:
    enabled: false
```

---

Tier Definitions (Groq-Only Launch)

```yaml
tiers:
  standard:
    draft_agents: [groq-llama-70b, groq-llama-8b, groq-mixtral]
    audit_agents: [groq-llama-70b, groq-llama-8b]
  premium:
    # Same as standard until premium providers re-enabled
    draft_agents: [groq-llama-70b, groq-llama-8b, groq-mixtral]
    audit_agents: [groq-llama-70b, groq-llama-8b]

credit_weights:
  base_cost: 2
  standard:
    - groq-llama-70b
    - groq-llama-8b
    - groq-mixtral
  premium:
    - groq-llama-70b
    - groq-llama-8b
    - groq-mixtral
```

---

GroqAPIAgent Implementation (runner/agents/groq_api.py)

```python
"""Groq API agent using the official Groq Python SDK."""

import os
from typing import Optional

from groq import Groq, RateLimitError as GroqRateLimitError

from runner.agents.api_base import APIAgent, RateLimitError
from runner.models import TokenUsage


class GroqAPIAgent(APIAgent):
    """Groq agent with chat completions and audio transcription."""

    MODEL_MAP = {
        # Llama 3.x
        "llama-70b": "llama-3.3-70b-versatile",
        "llama-8b": "llama-3.1-8b-instant",
        "llama-70b-specdec": "llama-3.3-70b-specdec",
        "llama-3.2-1b": "llama-3.2-1b-preview",
        "llama-3.2-3b": "llama-3.2-3b-preview",
        "llama-3.2-11b-vision": "llama-3.2-11b-vision-preview",
        "llama-3.2-90b-vision": "llama-3.2-90b-vision-preview",
        # Llama 4
        "llama4-scout": "meta-llama/llama-4-scout-17b-16e-instruct",
        "llama4-maverick": "meta-llama/llama-4-maverick-17b-128e-instruct",
        # Mixtral
        "mixtral": "mixtral-8x7b-32768",
        # Qwen
        "qwen-32b": "qwen/qwen3-32b",
        # Gemma
        "gemma2-9b": "gemma2-9b-it",
        # Whisper (audio transcription)
        "whisper": "whisper-large-v3",
        "whisper-turbo": "whisper-large-v3-turbo",
        "distil-whisper": "distil-whisper-large-v3-en",
    }

    MODEL_PRICING = {
        "llama-3.3-70b-versatile": {"input": 0.00059, "output": 0.00079},
        "llama-3.1-8b-instant": {"input": 0.00005, "output": 0.00008},
        "llama-3.3-70b-specdec": {"input": 0.00059, "output": 0.00079},
        "llama-3.2-1b-preview": {"input": 0.00004, "output": 0.00004},
        "llama-3.2-3b-preview": {"input": 0.00006, "output": 0.00006},
        "llama-3.2-11b-vision-preview": {"input": 0.00018, "output": 0.00018},
        "llama-3.2-90b-vision-preview": {"input": 0.00090, "output": 0.00090},
        "meta-llama/llama-4-scout-17b-16e-instruct": {"input": 0.00011, "output": 0.00034},
        "meta-llama/llama-4-maverick-17b-128e-instruct": {"input": 0.00020, "output": 0.00060},
        "mixtral-8x7b-32768": {"input": 0.00024, "output": 0.00024},
        "qwen/qwen3-32b": {"input": 0.00029, "output": 0.00039},
        "gemma2-9b-it": {"input": 0.00020, "output": 0.00020},
    }

    # Whisper pricing normalized to tokens (1 token = $0.01)
    WHISPER_TOKENS_PER_HOUR = {
        "whisper-large-v3": 11.1,
        "whisper-large-v3-turbo": 4.0,
        "distil-whisper-large-v3-en": 2.0,
    }

    def __init__(self, config: dict):
        super().__init__(config)
        self.client = Groq(api_key=self.api_key)
        self.max_tokens = config.get("max_tokens", 4096)
        self.system_prompt = config.get("system_prompt")

    def _get_api_key_from_env(self) -> str:
        return os.environ.get("GROQ_API_KEY", "")

    def _resolve_model_id(self) -> str:
        return self.MODEL_MAP.get(self.model, self.model)

    def _call_api(self, messages: list[dict]) -> tuple[str, TokenUsage]:
        try:
            api_messages = messages.copy()
            if self.system_prompt:
                api_messages = [{"role": "system", "content": self.system_prompt}] + api_messages

            response = self.client.chat.completions.create(
                model=self.model_id,
                messages=api_messages,
                max_tokens=self.max_tokens,
            )

            content = response.choices[0].message.content or ""
            tokens = TokenUsage(
                input_tokens=response.usage.prompt_tokens,
                output_tokens=response.usage.completion_tokens,
            )
            return content, tokens

        except GroqRateLimitError as e:
            raise RateLimitError(str(e))

    def transcribe(
        self,
        audio_file,
        model: str = "whisper-large-v3",
        language: Optional[str] = None,
        prompt: Optional[str] = None,
    ) -> dict:
        """Transcribe audio to text using Whisper.

        Args:
            audio_file: File-like object (opened in binary mode)
            model: Whisper model to use
            language: Optional language code (e.g., "en")
            prompt: Optional prompt to guide transcription

        Returns:
            dict with text, language, duration, tokens
        """
        kwargs = {"file": audio_file, "model": model}
        if language:
            kwargs["language"] = language
        if prompt:
            kwargs["prompt"] = prompt

        response = self.client.audio.transcriptions.create(**kwargs)

        duration_seconds = getattr(response, "duration", 0) or 0
        duration_hours = duration_seconds / 3600
        tokens_per_hour = self.WHISPER_TOKENS_PER_HOUR.get(model, 11.1)
        # Ensure at least 1 token for any transcription (fixes short audio returning 0)
        tokens = max(1, int(duration_hours * tokens_per_hour))

        return {
            "text": response.text,
            "language": getattr(response, "language", None),
            "duration": duration_seconds,
            "tokens": tokens,
        }
```

Note: TTS (text_to_speech) method removed - Groq does not support TTS.

---

Factory Registration (runner/agents/factory.py)

Add after line 59:
```python
try:
    from runner.agents.groq_api import GroqAPIAgent
    API_AGENT_REGISTRY["groq"] = GroqAPIAgent
except ImportError:
    pass
```

---

Package Export (runner/agents/__init__.py)

Add after line 51:
```python
GroqAPIAgent = None

try:
    from runner.agents.groq_api import GroqAPIAgent
except ImportError:
    pass
```

Add "GroqAPIAgent" to __all__.

---

Test Code (tests/unit/test_api_agents.py)

```python
from unittest.mock import MagicMock, patch, mock_open
import pytest


class TestGroqAPIAgent:
    def test_model_resolution_alias(self):
        with patch.object(GroqAPIAgent, '_get_api_key_from_env', return_value='test-key'):
            agent = GroqAPIAgent({"model": "llama-70b"})
            assert agent.model_id == "llama-3.3-70b-versatile"

    def test_model_resolution_direct(self):
        with patch.object(GroqAPIAgent, '_get_api_key_from_env', return_value='test-key'):
            agent = GroqAPIAgent({"model": "llama-3.3-70b-versatile"})
            assert agent.model_id == "llama-3.3-70b-versatile"

    def test_invoke_success(self):
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Response"
        mock_response.usage.prompt_tokens = 10
        mock_response.usage.completion_tokens = 20

        with patch.object(GroqAPIAgent, '_get_api_key_from_env', return_value='test-key'):
            agent = GroqAPIAgent({"model": "llama-70b"})
            agent.client = MagicMock()
            agent.client.chat.completions.create.return_value = mock_response
            result = agent.invoke("Hello")
            assert result.success is True
            assert result.content == "Response"
            assert result.tokens.input_tokens == 10
            assert result.tokens.output_tokens == 20

    def test_transcribe_returns_tokens(self):
        mock_response = MagicMock()
        mock_response.text = "Transcribed text"
        mock_response.duration = 60  # 1 minute

        with patch.object(GroqAPIAgent, '_get_api_key_from_env', return_value='test-key'):
            agent = GroqAPIAgent({"model": "whisper"})
            agent.client = MagicMock()
            agent.client.audio.transcriptions.create.return_value = mock_response

            # Must pass file-like object, not string
            mock_file = MagicMock()
            result = agent.transcribe(mock_file)

            assert result["text"] == "Transcribed text"
            assert result["duration"] == 60
            # 1 minute = 1/60 hour, tokens = max(1, int(1/60 * 11.1)) = 1
            assert result["tokens"] >= 1

    def test_transcribe_short_audio_minimum_token(self):
        """Ensure short audio files return at least 1 token."""
        mock_response = MagicMock()
        mock_response.text = "Hi"
        mock_response.duration = 1  # 1 second

        with patch.object(GroqAPIAgent, '_get_api_key_from_env', return_value='test-key'):
            agent = GroqAPIAgent({"model": "whisper"})
            agent.client = MagicMock()
            agent.client.audio.transcriptions.create.return_value = mock_response

            mock_file = MagicMock()
            result = agent.transcribe(mock_file)

            # Even 1 second should return at least 1 token
            assert result["tokens"] == 1

    def test_rate_limit_error(self):
        from groq import RateLimitError as GroqRateLimitError
        from runner.agents.api_base import RateLimitError

        with patch.object(GroqAPIAgent, '_get_api_key_from_env', return_value='test-key'):
            agent = GroqAPIAgent({"model": "llama-70b"})
            agent.client = MagicMock()
            agent.client.chat.completions.create.side_effect = GroqRateLimitError("Rate limited")

            with pytest.raises(RateLimitError):
                agent._call_api([{"role": "user", "content": "test"}])
```

---

Whisper Pricing Reference

| Model | Rate | Tokens/hour | Notes |
| --- | --- | --- | --- |
| whisper-large-v3 | $0.111/hr | 11.1 | Best quality |
| whisper-large-v3-turbo | $0.04/hr | 4.0 | Faster, good quality |
| distil-whisper-large-v3-en | $0.02/hr | 2.0 | English only, fastest |

Token normalization: 1 token = $0.01 (1 cent)

Important: Short audio files (under ~5 minutes) would calculate to 0 tokens with simple math. The implementation uses `max(1, int(...))` to ensure at least 1 token is returned.

---

Implementation Checklist

Phase G1: GroqAPIAgent (LAUNCH BLOCKER)
- [ ] Add groq>=0.12.0 to pyproject.toml
- [ ] Run pip install -e .
- [ ] Create runner/agents/groq_api.py with GroqAPIAgent class
- [ ] Add MODEL_MAP with all models
- [ ] Add MODEL_PRICING table (complete)
- [ ] Add WHISPER_TOKENS_PER_HOUR dict
- [ ] Implement _call_api() for chat
- [ ] Implement transcribe() for Whisper (with max(1, ...) fix)
- [ ] Update runner/agents/factory.py - add to API_AGENT_REGISTRY
- [ ] Update runner/agents/__init__.py - export GroqAPIAgent
- [ ] Update workflows/configs/groq-production.yaml:
  - [ ] Add groq-llama-70b, groq-llama-8b, groq-mixtral agents
  - [ ] Set orchestrator.agent to groq-llama-70b
  - [ ] Update story-review agent to groq-llama-70b
  - [ ] Update story-process agent to groq-llama-70b
  - [ ] Update draft agents to [groq-llama-70b, groq-llama-8b, groq-mixtral]
  - [ ] Update cross-audit agents to [groq-llama-70b, groq-llama-8b]
  - [ ] Update synthesize agent to groq-llama-70b
  - [ ] Update final-audit agents to [groq-llama-70b, groq-llama-8b]
  - [ ] Disable all claude*, gemini*, gpt-5.2-*, codex agents
  - [ ] Update tiers to use Groq agents only
  - [ ] Update credit_weights
- [ ] Add TestGroqAPIAgent to tests/unit/test_api_agents.py
- [ ] Run make test - all pass
- [ ] Set GROQ_API_KEY env var
- [ ] Manual test: create_agent("groq", {"model": "llama-70b"}, mode="api").invoke("Hello")
- [ ] Committed and pushed

Phase G1 Complete When:
- [ ] create_agent("groq", ...) works
- [ ] agent.invoke() returns correct TokenUsage
- [ ] agent.transcribe() returns tokens >= 1
- [ ] All unit tests pass
- [ ] workflow runs end-to-end with Groq agents

---

Feedback Loop Handling

**Key Finding: APIAgent already handles feedback loops correctly.**

Groq is stateless (no `--resume` like CLI agents), but this is not a problem because the `APIAgent` base class maintains conversation history in-memory:

```python
# runner/agents/api_base.py lines 75-88
def invoke_with_session(self, session_id: str, prompt: str, ...):
    self.messages.append({"role": "user", "content": full_prompt})  # Accumulate
    result = self._execute(self.messages)  # Send FULL history
    if result.success:
        self.messages.append({"role": "assistant", "content": result.content})
    return result
```

**How it works:**
- Each call appends to `self.messages` list (in-memory)
- Full conversation history sent to Groq with each API call
- Groq sees all prior context and responds appropriately
- "One-shot from Groq's perspective, stateful from ours"

**Limitations:**
- No cross-process persistence (agent instance must stay alive)
- Single workflow run is fine; resuming a crashed run would lose context
- For production, consider persisting messages to DB (deferred)

**No changes needed to GroqAPIAgent for feedback handling.**

---

Dynamic Workflow Configuration System

**Goal:** GUI-selectable workflow configs with deployment filtering.

**Directory Structure:**
```
workflows/
├── configs/
│   ├── groq-production.yaml     # Groq agents (cloud)
│   ├── ollama-local.yaml        # Ollama agents (local testing)
│   ├── legacy-claude.yaml       # Original multi-provider (disabled)
│   └── custom-workflow.yaml     # User-created workflows
└── registry.yaml                # Metadata about available workflows
```

**Registry Schema (workflows/registry.yaml):**
```yaml
workflows:
  groq-production:
    name: "Groq Production"
    description: "Fast cloud inference via Groq"
    config_file: "configs/groq-production.yaml"
    environment: production
    enabled: true
    tier_required: null  # Available to all tiers

  ollama-local:
    name: "Ollama Local"
    description: "Local testing with Ollama"
    config_file: "configs/ollama-local.yaml"
    environment: development
    enabled: true
    tier_required: null

deployment:
  production:
    include_environments: [production]
  development:
    include_environments: [production, development]
```

**Database Integration:**
- `workflow_configs` table stores available configs (synced from registry.yaml)
- `workspaces.workflow_config_id` stores workspace preference
- API endpoints for listing/selecting configs
- GUI selector in Settings page

**Deployment Filtering:**
- `DEPLOYMENT_ENV=production` only loads workflows with `environment: production`
- `DEPLOYMENT_ENV=development` loads all workflows
- `make sync-workflows` syncs registry.yaml to database

**Implementation:** See Phases 2-15 in IMPLEMENTATION_TRACKER.md.

---

Post-Launch Features (Deferred)

These are NOT launch blockers. See LAUNCH_SIMPLIFICATION_PLAN.md Deferred Work section.

Phase G2: YouTube Audio Helper
- yt-dlp wrapper for audio extraction
- Not needed for launch (text input only)

Phase G3: Content Input Flexibility
- UI choice: paste text OR upload audio
- New TranscriptionService (separate from content_service.py)
- Not needed for launch

Phase G4: Tier-Gated Model Presets
- Premium tier with different Groq models
- DB migration for workflow_tier field
- Not needed for launch

---

Verification Commands

```bash
# Install dependencies
pip install -e .

# Run tests
make test

# Manual verification (AGENT_MODE=api is REQUIRED)
GROQ_API_KEY=xxx AGENT_MODE=api python -c "
from runner.agents import create_agent
agent = create_agent('groq', {'model': 'llama-70b'}, mode='api')
result = agent.invoke('Say hello')
print(f'Success: {result.success}')
print(f'Content: {result.content[:100]}...')
print(f'Tokens: {result.tokens}')
"

# Workflow test (both env vars required)
GROQ_API_KEY=xxx AGENT_MODE=api make workflow CONFIG=groq-production STORY=post_01
```
