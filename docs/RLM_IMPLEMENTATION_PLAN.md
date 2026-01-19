# RLM Implementation Plan for Postmagiq Orchestrator

> **Document Version:** 1.1
> **Created:** 2026-01-18
> **Updated:** 2026-01-19
> **Purpose:** Comprehensive plan for applying Recursive Language Model (RLM) patterns to improve instruction-following and multi-agent coordination in the Postmagiq Orchestrator system.

### Related Documentation

| Document | Purpose |
|----------|---------|
| **This document** | Project-specific implementation plan. Directory: `runner/rlm/` |
| [RLM_FRAMEWORK_COMPLETE.md](./RLM_FRAMEWORK_COMPLETE.md) | Generic, LLM-agnostic framework reference. Directory: `.rlm/` |

**Note:** This plan implements RLM patterns within the existing `runner/` directory structure.
The Framework Complete document describes a standalone framework that could be used in any project.
Concepts are shared; directory structures differ by design.

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Problem Analysis](#problem-analysis)
3. [RLM Core Concepts](#rlm-core-concepts)
4. [Solution Patterns](#solution-patterns)
5. [Implementation Phases](#implementation-phases)
6. [Component Specifications](#component-specifications)
7. [Configuration Schemas](#configuration-schemas)
8. [Success Metrics](#success-metrics)
9. [Risk Mitigation](#risk-mitigation)
10. [Appendices](#appendices)

---

## Executive Summary

### The Problem

The Postmagiq Orchestrator system experiences three critical issues:

1. **AI Devs Break Things** - Claude Code forgets earlier instructions as context grows, makes changes without verification, and loses track of completed work.

2. **Personas Struggle to Follow Instructions** - Writer, Auditor, and Synthesizer personas juggle too much information (voice profiles, rules, task requirements) simultaneously, leading to instruction drift.

3. **Multi-Agent Pipeline Fails** - Information is lost between state transitions, parallel agents can't coordinate effectively, and the Synthesizer receives overwhelming context.

### The Solution

Apply **Recursive Language Model (RLM)** patterns from recent research to transform how agents interact with context:

**Before (Current State):**
```
"Here's everything you need to know: [9000 tokens]
 Now do the task."

Result: Context rot, instruction drift, unreliable outputs
```

**After (RLM-Enhanced):**
```
"Here's your task: [200 tokens]
 Here are tools to query context and verify your work.
 Work iteratively until you have a verified answer."

Result: Focused execution, verified compliance, reliable outputs
```

### Core Insight

> Long prompts should not be fed into the neural network directly but should
> instead be treated as part of the environment that the LLM can symbolically
> interact with.

This principle emerges from practical experience with context window limitations:
- LLMs perform better with focused, relevant context than with everything dumped upfront
- Tool-based retrieval allows selective access to what's needed, when it's needed
- Iterative verification catches errors that single-pass generation misses

The RLM pattern treats documentation, rules, and previous state as a **queryable database**
rather than prompt content.

### Expected Outcomes

| Metric | Before RLM | After RLM |
|--------|------------|-----------|
| Word count compliance | ~70% | 95%+ |
| Voice match score | ~6/10 | 8+/10 |
| Formatting violations | ~20% | <5% |
| Code pattern compliance | ~60% | 90%+ |
| Tests pass after changes | ~70% | 95%+ |

---

## Problem Analysis

### Current Architecture Pain Points

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     CURRENT PAIN POINTS                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  1. AI DEVS BREAK THINGS                                                     │
│     └─> Context rot: Claude forgets earlier instructions as context grows   │
│     └─> No verification: Changes made without checking consequences         │
│     └─> Lost state: Agent loses track of what it already did                │
│                                                                              │
│  2. PERSONAS STRUGGLE TO FOLLOW INSTRUCTIONS                                 │
│     └─> Prompt overload: Too much instruction crammed into one call         │
│     └─> Information density: Voice profiles + rules + task = confusion      │
│     └─> No decomposition: Complex tasks not broken into verifiable steps    │
│                                                                              │
│  3. MULTI-AGENT PIPELINE FAILS                                               │
│     └─> State handoff: Information lost between Writer → Auditor → Synth    │
│     └─> No symbolic reasoning: Everything is "in the prompt" not queryable  │
│     └─> Fan-out chaos: Parallel agents can't coordinate or verify each other│
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Current Prompt Structure (The Problem)

```
┌──────────────────────────────────────────────────────────────────┐
│  CURRENT: Everything in the Prompt                                │
├──────────────────────────────────────────────────────────────────┤
│                                                                   │
│  [System Prompt: 2000 tokens]                                     │
│  [Persona Template: 800 tokens]                                   │
│  [Voice Profile: 500 tokens]                                      │
│  [Universal Rules: 400 tokens]                                    │
│  [Previous Drafts: 3000 tokens]                                   │
│  [Audit Feedback: 600 tokens]                                     │
│  [Story Context: 1200 tokens]                                     │
│  [Task Instructions: 500 tokens]                                  │
│                                                                   │
│  TOTAL: ~9000 tokens of "stuff" before the LLM even thinks        │
│                                                                   │
│  RESULT: Context rot, instruction drift, persona bleed            │
│                                                                   │
└──────────────────────────────────────────────────────────────────┘
```

### RLM Approach (The Solution)

```
┌──────────────────────────────────────────────────────────────────┐
│  RLM: Context as Queryable Environment                            │
├──────────────────────────────────────────────────────────────────┤
│                                                                   │
│  [Minimal System Prompt: 400 tokens]                              │
│     "You have access to these tools:                              │
│      - get_voice_rules() → returns voice profile                  │
│      - get_universal_constraints() → returns formatting rules     │
│      - get_previous_drafts() → returns what others wrote          │
│      - get_audit_feedback() → returns specific critique           │
│      - verify_constraint(draft, rule) → checks compliance         │
│      - sub_agent(task, context) → delegates sub-problem"          │
│                                                                   │
│  [Task: 200 tokens]                                               │
│     "Write a LinkedIn post about {topic}. Query the environment   │
│      for voice rules and constraints as needed."                  │
│                                                                   │
│  TOTAL: ~600 tokens of instruction                                │
│                                                                   │
│  RESULT: Agent pulls what it needs, when it needs it              │
│                                                                   │
└──────────────────────────────────────────────────────────────────┘
```

---

## RLM Core Concepts

### What is an RLM?

A Recursive Language Model (RLM) is an inference strategy that:

1. **Externalizes the prompt** - Long context is stored outside the model and accessed via tools
2. **Provides programmatic access** - The LLM can query, filter, and transform context
3. **Enables recursive delegation** - Complex sub-tasks can be delegated to sub-agents
4. **Supports iterative verification** - The LLM verifies its work before completing

### RLM vs Traditional LLM Invocation

| Aspect | Traditional | RLM |
|--------|-------------|-----|
| Context delivery | All at once in prompt | Queried on demand |
| Context size | Limited by window | Virtually unlimited |
| Verification | None (hope it works) | Tool-based validation |
| Sub-task handling | Manual decomposition | Recursive delegation |
| Memory | Decays over conversation | Persistent in environment |

### Why RLM Patterns Work

Based on empirical observations from building LLM-powered systems:

1. **Scales beyond context windows** - External storage handles arbitrary amounts of context
2. **Quality improves with focus** - Agents with targeted context outperform those with everything
3. **Cost comparable or lower** - Selective retrieval reduces total tokens processed
4. **Handles complexity** - Information-dense tasks that fail with monolithic prompts succeed with decomposition

---

## Solution Patterns

### Pattern 1: Externalized Context for AI Dev Work

**Problem:** Claude Code forgets instructions, makes breaking changes, loses track of state.

**Solution:** Treat codebase and requirements as queryable environment.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     RLM-STYLE AI DEV WORKFLOW                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  User: "Add a new agent type for Mistral"                                    │
│                                                                              │
│  Claude receives:                                                            │
│    - Minimal task prompt (200 tokens)                                        │
│    - Environment tools:                                                      │
│        search_codebase(pattern) → search for relevant files                   │
│        get_coding_rule(topic) → retrieve specific rule from CLAUDE.md       │
│        get_existing_pattern(pattern_name) → get example from codebase       │
│        verify_follows_pattern(code, pattern) → check compliance             │
│        run_tests(file) → execute tests for feedback                         │
│                                                                              │
│  Claude's workflow:                                                          │
│    1. search_codebase("agent implementation") → finds runner/agents/          │
│    2. get_existing_pattern("agent_factory") → sees how to register          │
│    3. get_coding_rule("pydantic") → retrieves Pydantic pattern              │
│    4. Writes code                                                            │
│    5. verify_follows_pattern(new_code, "agent_base") → validates            │
│    6. run_tests("test_agents.py") → confirms nothing broke                  │
│                                                                              │
│  Result: Each step has fresh, focused context                                │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Pattern 2: Recursive Sub-Agents for Persona Tasks

**Problem:** Personas juggle voice profile, rules, and task simultaneously, leading to drift.

**Solution:** Main agent delegates specific concerns to focused sub-agents.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│              RLM-STYLE WRITER PERSONA EXECUTION                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Root Writer Agent (lightweight prompt):                                     │
│    "Write a post about {topic}. Use sub-agents to check your work."         │
│                                                                              │
│  Available sub-agents:                                                       │
│    voice_checker(draft) → "Does this match the voice profile?"              │
│    constraint_checker(draft) → "Does this follow universal rules?"          │
│    word_count_fixer(draft, target) → "Adjust to target length"              │
│    signature_phrase_injector(draft) → "Add voice-specific phrases"          │
│                                                                              │
│  Writer workflow:                                                            │
│    1. Generate raw draft (focused only on content)                           │
│    2. voice_checker(draft) → feedback on tone issues                        │
│    3. Revise based on feedback                                               │
│    4. constraint_checker(draft) → catches rule violations                   │
│    5. Fix violations                                                         │
│    6. word_count_fixer(draft, 300) → adjusts length                         │
│    7. Return final draft                                                     │
│                                                                              │
│  Result: Each sub-agent is focused, root agent coordinates                   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Pattern 3: REPL-Style Verification for Auditor

**Problem:** Auditor gives holistic scores that miss specific violations.

**Solution:** Auditor uses programmatic tools to verify each criterion.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│              RLM-STYLE AUDITOR WITH VERIFICATION TOOLS                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Auditor receives:                                                           │
│    - Draft to evaluate                                                       │
│    - Verification environment                                                │
│                                                                              │
│  Available tools:                                                            │
│    count_words(draft) → exact word count                                    │
│    check_forbidden_phrases(draft) → list of violations                      │
│    check_bullet_points(draft) → boolean                                     │
│    check_headers(draft) → boolean                                           │
│    score_voice_match(draft, profile) → 1-10 score with reasoning            │
│    find_signature_phrases(draft, expected) → which are present/missing      │
│    check_opening_hook(draft) → analysis of first line                       │
│    check_cta(draft) → analysis of call-to-action                            │
│                                                                              │
│  Auditor workflow (in REPL):                                                 │
│    word_count = count_words(draft)           # 287 - within range           │
│    forbidden = check_forbidden_phrases(draft) # ["leverage"] - violation!   │
│    has_bullets = check_bullet_points(draft)   # False - good                │
│    voice_score = score_voice_match(draft)     # 6/10 - needs work           │
│                                                                              │
│    # Compile evidence-based score                                            │
│    issues = [forbidden, voice_score < 8]                                     │
│    final_score = calculate_score(issues)                                     │
│                                                                              │
│  Result: Auditor score is derived from verifiable checks                     │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Pattern 4: Queryable State for Fan-Out → Synthesize

**Problem:** Synthesizer receives all drafts in prompt, often just picks one.

**Solution:** Drafts stored as queryable state, Synthesizer analyzes selectively.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│              RLM-STYLE SYNTHESIZER WITH QUERYABLE STATE                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Drafts stored as environment variables (not in prompt):                     │
│    drafts = {                                                                │
│      "claude": <draft_1>,                                                    │
│      "ollama": <draft_2>,                                                    │
│      "gemini": <draft_3>                                                     │
│    }                                                                         │
│                                                                              │
│  Synthesizer tools:                                                          │
│    list_drafts() → ["claude", "ollama", "gemini"]                           │
│    get_draft(name) → full text of that draft                                │
│    compare_openings() → analysis of first lines across all                  │
│    compare_closings() → analysis of CTAs across all                         │
│    extract_best_phrases(criteria) → finds standout phrases                  │
│    sub_agent_evaluate(draft, criteria) → focused sub-evaluation             │
│                                                                              │
│  Synthesizer workflow:                                                       │
│    openings = compare_openings()                                             │
│    # "Claude's opening has stronger hook, Ollama's is more personal"        │
│                                                                              │
│    closings = compare_closings()                                             │
│    # "Gemini has clearest CTA"                                               │
│                                                                              │
│    phrases = extract_best_phrases("vulnerability")                           │
│    # Returns specific phrases from each that show vulnerability              │
│                                                                              │
│    # Synthesizer now has focused insights to combine                         │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Implementation Phases

### Phase Overview

| Phase | Focus | Duration | Dependencies |
|-------|-------|----------|--------------|
| Phase 1 | RLM Infrastructure Layer | 1-2 weeks | None |
| Phase 2 | Persona Transformation | 2-3 weeks | Phase 1 |
| Phase 3 | State Machine Modifications | 1-2 weeks | Phase 1, 2 |
| Phase 4 | AI Dev RLM Mode | 1-2 weeks | Phase 1 |
| Phase 5 | Circuit Breaker Enhancements | 1 week | Phase 1-4 |

**Total Estimated Duration:** 6-10 weeks

---

### Phase 1: RLM Infrastructure Layer

**Goal:** Build the foundation that allows any agent to treat context as environment.

**Duration:** 1-2 weeks

#### New Directory Structure

```
runner/
├── rlm/                          # New RLM infrastructure
│   ├── __init__.py
│   ├── environment.py            # REPL-like execution environment
│   ├── context_store.py          # External context storage
│   ├── tool_registry.py          # Register available tools
│   ├── sub_agent_manager.py      # Handle recursive sub-calls
│   └── tools/                    # Built-in verification tools
│       ├── __init__.py
│       ├── text_analysis.py      # Word count, structure checks
│       ├── voice_matching.py     # Voice profile verification
│       ├── constraint_checks.py  # Rule compliance
│       └── codebase_query.py     # For AI dev work
│
└── agents/
    ├── base.py                   # Add RLM capability to BaseAgent
    └── rlm_agent.py              # New RLM-capable agent wrapper
```

#### Component 1: Context Store

**Purpose:** Store context externally so agents can query it rather than receiving it all in the prompt.

```
class ContextStore:
    """Stores context as queryable environment variables."""
    
    storage: Dict[string, Any]  # Key-value store for context
    
    method store(key, value, metadata):
        """Store a piece of context with optional metadata."""
        storage[key] = {
            "value": value,
            "metadata": metadata,
            "stored_at": timestamp,
            "token_count": count_tokens(value)
        }
    
    method retrieve(key) -> Any:
        """Retrieve specific context by key."""
        return storage[key]["value"]
    
    method query(pattern) -> List[Match]:
        """Search across stored context using pattern."""
        results = []
        for key, item in storage:
            if pattern matches item["value"]:
                results.append(Match(key, snippet, score))
        return results
    
    method get_summary(key) -> string:
        """Get a condensed summary of stored context."""
        return summarize(storage[key]["value"])
    
    method list_available() -> List[string]:
        """List all available context keys."""
        return list(storage.keys())
```

**Usage in Workflow:**

```
# At workflow start, store context externally
context_store.store("voice_profile", voice_profile_data)
context_store.store("universal_rules", rules_data)
context_store.store("story_context", story_data)
context_store.store("previous_drafts", drafts_data)

# Agent receives minimal prompt + access to context_store
# Agent queries what it needs, when it needs it
```

#### Component 2: Tool Registry

**Purpose:** Provide agents with tools they can call to interact with context and verify their work.

```
class ToolRegistry:
    """Registry of tools available to RLM agents."""
    
    tools: Dict[string, Callable]
    
    method register(tool_or_name, function=None, description=None, schema=None):
        """Register a tool that agents can call.

        Accepts either:
        - A Tool object: register(tool)
        - Discrete args: register(name, function, description, schema)
        """
        if isinstance(tool_or_name, Tool):
            tool = tool_or_name
            name = tool.name
            function = tool.function
            description = tool.description
            schema = tool.input_schema
        else:
            name = tool_or_name

        tools[name] = {
            "function": function,
            "description": description,
            "input_schema": schema,
            "output_schema": infer_output_schema(function)
        }
    
    method execute(tool_name, arguments) -> ToolResult:
        """Execute a tool and return structured result."""
        tool = tools[tool_name]
        try:
            result = tool["function"](**arguments)
            return ToolResult(success=True, output=result)
        except Exception as e:
            return ToolResult(success=False, error=str(e))
    
    method get_tool_descriptions() -> string:
        """Generate prompt-friendly tool descriptions."""
        descriptions = []
        for name, tool in tools:
            descriptions.append(format_tool_description(name, tool))
        return join(descriptions, "\n")
```

**Built-in Tools to Register:**

```
# Text Analysis Tools
register("count_words", count_words_fn, 
         "Count words in text", {text: string})

register("check_structure", check_structure_fn,
         "Check for bullets, headers, lists", {text: string})

register("find_phrases", find_phrases_fn,
         "Find occurrences of specific phrases", 
         {text: string, phrases: List[string]})

# Voice Matching Tools  
register("score_voice_match", score_voice_fn,
         "Score how well text matches a voice profile",
         {text: string, profile_key: string})

register("suggest_voice_improvements", suggest_improvements_fn,
         "Suggest edits to better match voice",
         {text: string, profile_key: string})

# Constraint Tools
register("check_constraints", check_constraints_fn,
         "Verify text against universal rules",
         {text: string})

register("check_forbidden_content", check_forbidden_fn,
         "Check for forbidden phrases or patterns",
         {text: string, forbidden_list: List[string]})

# Sub-Agent Tools
register("delegate_to_sub_agent", delegate_fn,
         "Delegate a focused task to a sub-agent",
         {task: string, context_keys: List[string]})
```

#### Component 3: RLM Environment

**Purpose:** Execution environment where agents can run tools and sub-agent calls iteratively.

```
class RLMEnvironment:
    """REPL-like environment for RLM agent execution."""
    
    context_store: ContextStore
    tool_registry: ToolRegistry
    execution_history: List[ExecutionStep]
    max_iterations: int = 10
    
    method initialize(context: Dict, tools: ToolRegistry, config: RLMConfig):
        """Set up environment with initial context, tools, and configuration."""
        for key, value in context.items():
            context_store.store(key, value)
        self.tool_registry = tools
        self.max_iterations = config.max_iterations
        self.allow_sub_agents = config.allow_sub_agents
    
    method run(agent, task) -> RLMResult:
        """Execute agent in RLM mode with iterative tool use."""
        
        iteration = 0
        while iteration < max_iterations:
            # Build minimal prompt with tool descriptions
            prompt = build_rlm_prompt(
                task=task,
                tools=tool_registry.get_tool_descriptions(),
                available_context=context_store.list_available(),
                history=execution_history[-5:]  # Recent history only
            )
            
            # Agent generates response (may include tool calls)
            response = agent.invoke(prompt)
            
            # Parse response for tool calls or final answer
            if response.has_tool_calls():
                for tool_call in response.tool_calls:
                    result = tool_registry.execute(
                        tool_call.name, 
                        tool_call.arguments
                    )
                    execution_history.append(
                        ExecutionStep(tool_call, result)
                    )
            
            elif response.has_final_answer():
                return RLMResult(
                    success=True,
                    answer=response.final_answer,
                    history=execution_history
                )
            
            elif response.has_sub_agent_call():
                sub_result = handle_sub_agent_call(response.sub_agent_call)
                execution_history.append(sub_result)
            
            iteration += 1
        
        # Max iterations reached
        return RLMResult(
            success=False,
            error="Max iterations exceeded",
            history=execution_history
        )
    
    method handle_sub_agent_call(call) -> SubAgentResult:
        """Handle recursive sub-agent delegation."""
        
        # Create child environment with subset of context
        child_env = RLMEnvironment()
        for key in call.context_keys:
            child_env.context_store.store(
                key, 
                self.context_store.retrieve(key)
            )
        
        # Run sub-agent (could be same or different agent)
        sub_agent = get_agent(call.agent_type or "default")
        result = child_env.run(sub_agent, call.task)
        
        return SubAgentResult(
            task=call.task,
            result=result.answer
        )
```

#### RLM Environment Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     RLM ENVIRONMENT EXECUTION FLOW                           │
└─────────────────────────────────────────────────────────────────────────────┘

                    ┌─────────────────────────────────┐
                    │         TASK INPUT              │
                    │  "Write LinkedIn post about X"  │
                    └───────────────┬─────────────────┘
                                    │
                                    ▼
┌───────────────────────────────────────────────────────────────────────────┐
│                         RLM ENVIRONMENT                                    │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │                      CONTEXT STORE                                   │  │
│  │  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐        │  │
│  │  │   voice    │ │  rules     │ │   story    │ │  drafts    │        │  │
│  │  │  profile   │ │            │ │  context   │ │            │        │  │
│  │  └────────────┘ └────────────┘ └────────────┘ └────────────┘        │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                    ▲                                       │
│                                    │ query                                 │
│                                    │                                       │
│  ┌─────────────────────────────────┴───────────────────────────────────┐  │
│  │                         AGENT                                        │  │
│  │                                                                      │  │
│  │  Iteration 1:                                                        │  │
│  │    Agent: "What voice should I use?"                                 │  │
│  │    → calls: get_context("voice_profile")                            │  │
│  │    → receives: {tone: "reflective", phrases: [...]}                 │  │
│  │                                                                      │  │
│  │  Iteration 2:                                                        │  │
│  │    Agent: "Here's my draft: [draft text]"                           │  │
│  │    Agent: "Let me verify it matches the voice"                      │  │
│  │    → calls: score_voice_match(draft, "voice_profile")               │  │
│  │    → receives: {score: 6, issues: ["too formal", "missing hook"]}   │  │
│  │                                                                      │  │
│  │  Iteration 3:                                                        │  │
│  │    Agent: "I'll revise and delegate opening to sub-agent"           │  │
│  │    → calls: delegate_to_sub_agent(                                  │  │
│  │        task="Write engaging opening hook",                          │  │
│  │        context_keys=["voice_profile", "story_context"]              │  │
│  │      )                                                               │  │
│  │    → receives: "What if I told you..."                              │  │
│  │                                                                      │  │
│  │  Iteration 4:                                                        │  │
│  │    Agent: "Final draft: [revised text]"                             │  │
│  │    → calls: check_constraints(draft)                                │  │
│  │    → receives: {passes: true, word_count: 287}                      │  │
│  │    → returns: FINAL(draft)                                          │  │
│  │                                                                      │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                    │                                       │
│  ┌─────────────────────────────────┴───────────────────────────────────┐  │
│  │                      TOOL REGISTRY                                   │  │
│  │  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐        │  │
│  │  │  count_    │ │  score_    │ │  check_    │ │ delegate_  │        │  │
│  │  │  words     │ │  voice     │ │constraints │ │ sub_agent  │        │  │
│  │  └────────────┘ └────────────┘ └────────────┘ └────────────┘        │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                                                            │
└────────────────────────────────────┬───────────────────────────────────────┘
                                     │
                                     ▼
                    ┌─────────────────────────────────┐
                    │         TASK OUTPUT             │
                    │  Draft with verified compliance │
                    └─────────────────────────────────┘
```

#### Phase 1 Deliverables

| Deliverable | Description | Acceptance Criteria |
|-------------|-------------|---------------------|
| `context_store.py` | External context storage | Can store, retrieve, query context |
| `tool_registry.py` | Tool management system | Can register, execute, describe tools |
| `environment.py` | RLM execution environment | Can run agent with tool loop |
| `tools/text_analysis.py` | Text verification tools | Word count, structure checks work |
| `tools/voice_matching.py` | Voice matching tools | Can score voice match |
| `tools/constraint_checks.py` | Rule verification tools | Can check all constraints |
| Unit tests | Test coverage for all components | 90%+ coverage |

---

### Phase 2: Persona Transformation

**Goal:** Convert Writer, Auditor, and Synthesizer personas to use RLM patterns.

**Duration:** 2-3 weeks

#### Step 2.1: RLM System Prompts

**Current Writer Prompt (simplified):**

```
You are a LinkedIn content writer. Your task is to write a post
about {topic} in the voice of {user}.

VOICE PROFILE:
- Tone: reflective, vulnerable, generous
- Signature phrases: "Here's what I learned...", "The truth is..."
- Avoid: corporate jargon, bullet points, emojis

RULES:
- 250-400 words
- No headers or bullet points
- Strong opening hook
- Clear call to action

PREVIOUS DRAFTS:
[Draft 1: 600 tokens]
[Draft 2: 550 tokens]

Write the post now.
```

**RLM Writer Prompt:**

```
You are a LinkedIn content writer working in an interactive environment.

YOUR TASK: Write a post about {topic}

AVAILABLE CONTEXT (query as needed):
- "voice_profile": The user's writing voice and style
- "universal_rules": Formatting and content rules
- "story_context": Background for this post
- "previous_drafts": What other writers produced (if any)

AVAILABLE TOOLS:
- get_context(key): Retrieve specific context
- score_voice_match(draft): Check if draft matches voice (1-10)
- check_constraints(draft): Verify rules compliance
- count_words(draft): Get exact word count
- suggest_voice_improvements(draft): Get specific edit suggestions
- delegate_to_sub_agent(task, context_keys): Get help on sub-task

WORKFLOW:
1. First, query the voice_profile and universal_rules to understand requirements
2. Write your draft
3. Use tools to verify your draft meets requirements
4. Revise if needed based on tool feedback
5. Return your final draft with FINAL(draft)

You can iterate as many times as needed. Each tool call gives you
fresh, accurate feedback.
```

#### Step 2.2: Persona-Specific Tools

**Writer Persona Tools:**

```
tools_for_writer = [
    # Context access
    Tool("get_voice_profile", get_voice_profile_fn,
         "Get the user's voice profile including tone and phrases"),
    
    Tool("get_story_context", get_story_context_fn,
         "Get background context for this story"),
    
    # Verification
    Tool("score_voice_match", score_voice_match_fn,
         "Score how well draft matches voice (1-10) with feedback"),
    
    Tool("check_word_count", check_word_count_fn,
         "Check if draft is within 250-400 word range"),
    
    Tool("check_formatting", check_formatting_fn,
         "Verify no bullets, headers, or forbidden elements"),
    
    # Improvement
    Tool("suggest_opening_hooks", suggest_hooks_fn,
         "Generate 3 alternative opening hooks"),
    
    Tool("suggest_voice_edits", suggest_edits_fn,
         "Get specific edits to improve voice match"),
    
    # Delegation
    Tool("delegate_opening", delegate_opening_fn,
         "Have a sub-agent write just the opening paragraph"),
    
    Tool("delegate_cta", delegate_cta_fn,
         "Have a sub-agent write just the call-to-action"),
]
```

**Auditor Persona Tools:**

```
tools_for_auditor = [
    # Programmatic verification (not subjective)
    Tool("count_words", count_words_fn,
         "Get exact word count"),
    
    Tool("find_forbidden_phrases", find_forbidden_fn,
         "Find any forbidden phrases in the draft"),
    
    Tool("check_has_bullets", check_bullets_fn,
         "Check if draft contains bullet points"),
    
    Tool("check_has_headers", check_headers_fn,
         "Check if draft contains headers"),
    
    Tool("count_paragraphs", count_paragraphs_fn,
         "Count number of paragraphs"),
    
    # Sub-agent verification (for subjective criteria)
    Tool("evaluate_opening_hook", eval_hook_fn,
         "Have sub-agent evaluate opening hook strength (1-10)"),
    
    Tool("evaluate_voice_authenticity", eval_voice_fn,
         "Have sub-agent score voice authenticity (1-10)"),
    
    Tool("evaluate_cta_clarity", eval_cta_fn,
         "Have sub-agent score CTA clarity (1-10)"),
    
    # Comparison
    Tool("compare_to_examples", compare_fn,
         "Compare draft to example posts in voice profile"),
]
```

**Synthesizer Persona Tools:**

```
tools_for_synthesizer = [
    # Draft access
    Tool("list_drafts", list_drafts_fn,
         "List all available drafts to synthesize"),
    
    Tool("get_draft", get_draft_fn,
         "Get full text of a specific draft"),
    
    # Comparison
    Tool("compare_openings", compare_openings_fn,
         "Compare opening hooks across all drafts"),
    
    Tool("compare_closings", compare_closings_fn,
         "Compare CTAs across all drafts"),
    
    Tool("find_best_phrases", find_best_phrases_fn,
         "Find standout phrases across all drafts for a quality"),
    
    # Evaluation delegation
    Tool("rank_drafts_by_voice", rank_by_voice_fn,
         "Have sub-agent rank drafts by voice authenticity"),
    
    Tool("rank_drafts_by_engagement", rank_by_engagement_fn,
         "Have sub-agent rank drafts by engagement potential"),
    
    # Construction
    Tool("extract_section", extract_section_fn,
         "Extract opening/middle/closing from a specific draft"),
]
```

#### Writer Persona Tool Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     WRITER PERSONA WITH RLM TOOLS                            │
└─────────────────────────────────────────────────────────────────────────────┘

  ┌─────────────────────────────────────────────────────────────────────────┐
  │                           WRITER AGENT                                   │
  │                                                                          │
  │   1. "Let me check what voice I should use"                             │
  │      ↓                                                                   │
  │   ┌─────────────────────────────────────────────────────────────────┐   │
  │   │ get_voice_profile()                                              │   │
  │   │ → {                                                              │   │
  │   │     tone: "reflective, vulnerable",                             │   │
  │   │     phrases: ["Here's what I learned", "The truth is"],         │   │
  │   │     avoid: ["leverage", "synergy", "circle back"]               │   │
  │   │   }                                                              │   │
  │   └─────────────────────────────────────────────────────────────────┘   │
  │                                                                          │
  │   2. "Now I'll write my draft..."                                       │
  │      [Writes draft focusing only on content]                            │
  │                                                                          │
  │   3. "Let me verify my draft"                                           │
  │      ↓                                                                   │
  │   ┌─────────────────────────────────────────────────────────────────┐   │
  │   │ score_voice_match(draft)                                         │   │
  │   │ → {                                                              │   │
  │   │     score: 6,                                                    │   │
  │   │     issues: [                                                    │   │
  │   │       "Opening feels too formal",                                │   │
  │   │       "Missing signature phrase",                                │   │
  │   │       "Closing lacks vulnerability"                              │   │
  │   │     ],                                                           │   │
  │   │     strengths: ["Good story arc", "Clear message"]              │   │
  │   │   }                                                              │   │
  │   └─────────────────────────────────────────────────────────────────┘   │
  │      ↓                                                                   │
  │   ┌─────────────────────────────────────────────────────────────────┐   │
  │   │ check_word_count(draft)                                          │   │
  │   │ → { count: 312, in_range: true }                                │   │
  │   └─────────────────────────────────────────────────────────────────┘   │
  │      ↓                                                                   │
  │   ┌─────────────────────────────────────────────────────────────────┐   │
  │   │ check_formatting(draft)                                          │   │
  │   │ → { has_bullets: false, has_headers: false, valid: true }       │   │
  │   └─────────────────────────────────────────────────────────────────┘   │
  │                                                                          │
  │   4. "Voice score is 6, I need to fix the opening"                      │
  │      ↓                                                                   │
  │   ┌─────────────────────────────────────────────────────────────────┐   │
  │   │ delegate_opening(task="Write vulnerable opening hook",           │   │
  │   │                  context=["voice_profile", "story_context"])     │   │
  │   │                                                                  │   │
  │   │ SUB-AGENT RUNS:                                                  │   │
  │   │   → Receives only voice_profile and story_context               │   │
  │   │   → Focuses solely on opening hook                              │   │
  │   │   → Returns: "I used to think success meant..."                 │   │
  │   └─────────────────────────────────────────────────────────────────┘   │
  │                                                                          │
  │   5. "I'll incorporate that opening and add signature phrase"           │
  │      [Revises draft]                                                    │
  │                                                                          │
  │   6. "Final verification"                                               │
  │      ↓                                                                   │
  │   ┌─────────────────────────────────────────────────────────────────┐   │
  │   │ score_voice_match(revised_draft)                                 │   │
  │   │ → { score: 8, issues: [], strengths: [...] }                    │   │
  │   └─────────────────────────────────────────────────────────────────┘   │
  │                                                                          │
  │   7. FINAL(revised_draft)                                               │
  │                                                                          │
  └─────────────────────────────────────────────────────────────────────────┘
```

#### Phase 2 Deliverables

| Deliverable | Description | Acceptance Criteria |
|-------------|-------------|---------------------|
| `prompts/writer_rlm.md` | RLM-enhanced writer prompt | Tool-aware, iterative |
| `prompts/auditor_rlm.md` | RLM-enhanced auditor prompt | Evidence-based scoring |
| `prompts/synthesizer_rlm.md` | RLM-enhanced synthesizer prompt | Query-based comparison |
| `tools/writer_tools.py` | Writer-specific tools | All tools functional |
| `tools/auditor_tools.py` | Auditor-specific tools | All tools functional |
| `tools/synthesizer_tools.py` | Synthesizer-specific tools | All tools functional |
| Integration tests | Test personas in RLM mode | Pass rate > 90% |

---

### Phase 3: State Machine Modifications

**Goal:** Update state machine to use RLM environments instead of direct invocation.

**Duration:** 1-2 weeks

#### New State Configuration Schema

**Current workflow_config.yaml (simplified):**

```yaml
states:
  draft:
    type: fan-out
    agents:
      - name: writer_claude
        type: claude
        persona: writer
    transitions:
      - target: audit
        condition: all_complete
```

**Enhanced workflow_config.yaml with RLM:**

```yaml
states:
  draft:
    type: fan-out
    execution_mode: rlm              # NEW: Enable RLM mode
    
    context_setup:                   # NEW: What to load into context store
      - key: voice_profile
        source: database
        query: "voice_profiles/{workspace_id}/{voice_id}"
      
      - key: universal_rules
        source: file
        path: "prompts/universal_rules.md"
      
      - key: story_context
        source: workflow_state
        field: story_entry
    
    tools:                           # NEW: Tools available to this state's agents
      - name: score_voice_match
        type: sub_agent
        agent: auditor_mini
      
      - name: check_constraints
        type: programmatic
        function: constraint_checker
      
      - name: delegate_sub_task
        type: recursive
        max_depth: 2
    
    agents:
      - name: writer_claude
        type: claude
        persona: writer_rlm          # NEW: RLM-specific prompt
        max_iterations: 8            # NEW: Max tool-use iterations
    
    outputs:                         # NEW: What to store after execution
      - key: draft_{agent_name}
        store_in: context_store      # Available for next states
    
    transitions:
      - target: audit
        condition: all_complete
```

#### Modified State Machine Execution

```
class StateMachine:
    
    context_store: ContextStore          # Shared across states
    tool_registry: ToolRegistry
    
    method execute_state(state_config, workflow_context):
        
        if state_config.execution_mode == "rlm":
            return execute_rlm_state(state_config, workflow_context)
        else:
            return execute_legacy_state(state_config, workflow_context)
    
    method execute_rlm_state(state_config, workflow_context):
        
        # 1. Load context into store
        for context_item in state_config.context_setup:
            value = load_context_value(context_item, workflow_context)
            context_store.store(context_item.key, value)
        
        # 2. Register tools for this state
        state_tools = ToolRegistry()
        for tool_config in state_config.tools:
            tool = create_tool(tool_config)
            state_tools.register(tool)
        
        # 3. Execute agents
        # IMPORTANT: For fan-out, create separate environment per agent
        # to avoid shared mutable state (execution_history, tool state)
        if state_config.type == "fan-out":
            # 4a. Parallel execution with isolated environments
            def run_agent(agent):
                agent_env = RLMEnvironment(
                    context_store=context_store.snapshot(),  # Immutable snapshot
                    tool_registry=state_tools.copy(),        # Copy for isolation
                    max_iterations=state_config.max_iterations or 10
                )
                return agent_env.run(agent, state_config.task)

            results = parallel_execute([
                run_agent(agent) for agent in state_config.agents
            ])
        else:
            # 4b. Single agent execution
            env = RLMEnvironment(
                context_store=context_store,
                tool_registry=state_tools,
                max_iterations=state_config.max_iterations or 10
            )
            results = [env.run(state_config.agent, state_config.task)]
        
        # 5. Store outputs in context store for next states
        # NOTE: For fan-out, a single output template is expanded for each agent
        # using {agent_name} substitution. For single-agent, outputs match 1:1.
        output_template = state_config.outputs[0] if state_config.outputs else None
        if output_template:
            for result in results:
                key = output_template.key.format(agent_name=result.agent_name)
                context_store.store(key, result.answer)
        
        return StateResult(
            outputs=results,
            context_updates=context_store.get_recent_updates()
        )
```

#### RLM-Enhanced State Machine Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│               RLM-ENHANCED STATE MACHINE EXECUTION                           │
└─────────────────────────────────────────────────────────────────────────────┘

                    ┌─────────────────────────────────┐
                    │         START STATE             │
                    │   Load initial context          │
                    └───────────────┬─────────────────┘
                                    │
                                    ▼
┌───────────────────────────────────────────────────────────────────────────────┐
│                        SHARED CONTEXT STORE                                    │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐              │
│  │   voice_    │ │  universal_ │ │   story_    │ │  (empty     │              │
│  │  profile    │ │   rules     │ │  context    │ │   slots)    │              │
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘              │
└───────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌───────────────────────────────────────────────────────────────────────────────┐
│                        DRAFT STATE (fan-out, RLM mode)                         │
│                                                                                │
│   ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐               │
│   │  RLM Env #1     │  │  RLM Env #2     │  │  RLM Env #3     │               │
│   │  writer_claude  │  │  writer_ollama  │  │  writer_gemini  │               │
│   │                 │  │                 │  │                 │               │
│   │  [queries]      │  │  [queries]      │  │  [queries]      │               │
│   │  [tools]        │  │  [tools]        │  │  [tools]        │               │
│   │  [sub-agents]   │  │  [sub-agents]   │  │  [sub-agents]   │               │
│   └────────┬────────┘  └────────┬────────┘  └────────┬────────┘               │
│            │                    │                    │                         │
│            ▼                    ▼                    ▼                         │
│       draft_claude         draft_ollama        draft_gemini                    │
│                                                                                │
└───────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ Store outputs in context
                                    ▼
┌───────────────────────────────────────────────────────────────────────────────┐
│                        SHARED CONTEXT STORE (updated)                          │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐              │
│  │   voice_    │ │  universal_ │ │   story_    │ │   draft_    │              │
│  │  profile    │ │   rules     │ │  context    │ │  claude     │              │
│  └─────────────┘ └─────────────┘ └─────────────┘ ├─────────────┤              │
│                                                  │   draft_    │              │
│                                                  │  ollama     │              │
│                                                  ├─────────────┤              │
│                                                  │   draft_    │              │
│                                                  │  gemini     │              │
│                                                  └─────────────┘              │
└───────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌───────────────────────────────────────────────────────────────────────────────┐
│                        AUDIT STATE (single, RLM mode)                          │
│                                                                                │
│   ┌─────────────────────────────────────────────────────────────────────┐     │
│   │  RLM Env - Auditor                                                  │     │
│   │                                                                      │     │
│   │  Available context: voice_profile, rules, draft_claude,             │     │
│   │                     draft_ollama, draft_gemini                      │     │
│   │                                                                      │     │
│   │  Tools: count_words, find_forbidden, score_voice (per draft)        │     │
│   │                                                                      │     │
│   │  Workflow:                                                           │     │
│   │    for each draft in [claude, ollama, gemini]:                      │     │
│   │      word_count = count_words(get_draft(draft))                     │     │
│   │      voice_score = score_voice(get_draft(draft))                    │     │
│   │      violations = find_forbidden(get_draft(draft))                  │     │
│   │    → Compiles evidence-based AuditResult                           │     │
│   │                                                                      │     │
│   └─────────────────────────────────────────────────────────────────────┘     │
│                                                                                │
└───────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌───────────────────────────────────────────────────────────────────────────────┐
│                        SYNTHESIZE STATE (RLM mode)                             │
│                                                                                │
│   ┌─────────────────────────────────────────────────────────────────────┐     │
│   │  RLM Env - Synthesizer                                              │     │
│   │                                                                      │     │
│   │  Tools: compare_openings, compare_closings, extract_best_phrases    │     │
│   │                                                                      │     │
│   │  Does NOT receive all drafts in prompt                              │     │
│   │  Instead: queries specific parts as needed                          │     │
│   │                                                                      │     │
│   └─────────────────────────────────────────────────────────────────────┘     │
│                                                                                │
└───────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
                    ┌─────────────────────────────────┐
                    │       COMPLETE STATE            │
                    │   Final post ready              │
                    └─────────────────────────────────┘
```

#### Phase 3 Deliverables

| Deliverable | Description | Acceptance Criteria |
|-------------|-------------|---------------------|
| `state_machine.py` updates | RLM execution mode | Backward compatible |
| `workflow_config.yaml` schema | New RLM fields | Validated by schema |
| Context passing mechanism | State-to-state context | No data loss |
| Parallel RLM execution | Fan-out with shared context | Thread-safe |
| Integration tests | Full workflow with RLM | End-to-end pass |

---

### Phase 4: AI Dev RLM Mode

**Goal:** Apply RLM patterns to how Claude Code works on the codebase.

**Duration:** 1-2 weeks

#### AI Dev Tools

**Codebase Query Tools:**

```
Tool("search_codebase", search_codebase_fn,
     "Search for files/code matching a pattern",
     {pattern: string, file_types: List[string]})

Tool("get_file_structure", get_structure_fn,
     "Get directory tree of a path",
     {path: string, depth: int})

Tool("get_file_content", get_file_fn,
     "Get content of a specific file",
     {path: string, lines: Optional[Tuple[int, int]]})

Tool("find_usages", find_usages_fn,
     "Find all usages of a function/class/variable",
     {symbol: string, scope: Optional[string]})

Tool("get_imports", get_imports_fn,
     "Get what a file imports and what imports it",
     {path: string})
```

**Pattern Verification Tools:**

```
Tool("get_coding_rule", get_rule_fn,
     "Get specific coding rule from CLAUDE.md",
     {topic: string})
     # e.g., get_coding_rule("pydantic") → returns Pydantic pattern

Tool("get_existing_pattern", get_pattern_fn,
     "Get example of existing pattern from codebase",
     {pattern_name: string})
     # e.g., get_existing_pattern("agent_factory") → returns factory code

Tool("verify_follows_pattern", verify_pattern_fn,
     "Check if code follows a required pattern",
     {code: string, pattern_name: string})

Tool("check_for_pitfalls", check_pitfalls_fn,
     "Check if code has any of the documented pitfalls",
     {code: string})
     # Checks against "Common Pitfalls" section of CLAUDE.md
```

**Test and Verify Tools:**

```
Tool("run_tests", run_tests_fn,
     "Run tests for a specific file or directory",
     {path: string, filter: Optional[string]})

Tool("run_type_check", run_type_check_fn,
     "Run mypy/pyright on code",
     {path: string})

Tool("check_imports_valid", check_imports_fn,
     "Verify all imports resolve correctly",
     {path: string})
```

**Sub-Agent Delegation:**

```
Tool("delegate_code_review", delegate_review_fn,
     "Have a sub-agent review code changes",
     {original: string, modified: string, context: string})

Tool("delegate_test_writing", delegate_tests_fn,
     "Have a sub-agent write tests for new code",
     {code: string, test_style: string})
```

#### AI Dev RLM Workflow

```
method handle_ai_dev_task(task_description):
    
    # Initialize RLM environment with codebase context
    env = RLMEnvironment()
    
    # Store CLAUDE.md rules as queryable context
    env.context_store.store("coding_rules", load_file("CLAUDE.md"))
    env.context_store.store("architecture", load_file("ARCHITECTURE.md"))
    env.context_store.store("test_patterns", load_file("tests/"))
    
    # Register AI dev tools
    env.tool_registry.register_all(ai_dev_tools)
    
    # Minimal prompt for the AI dev agent
    prompt = """
    TASK: {task_description}
    
    You have access to the codebase through tools. Before writing any code:
    1. Query the codebase to understand existing patterns
    2. Query coding_rules to understand required patterns
    3. Write code following those patterns
    4. Verify your code follows patterns before submitting
    5. Run tests to confirm nothing is broken
    
    Available tools: {tool_list}
    
    Work iteratively, verifying each step.
    """
    
    result = env.run(claude_agent, prompt)
    return result
```

#### Example AI Dev Interaction

```
Task: "Add a Mistral agent implementation"

Iteration 1:
  Agent: "Let me find existing agent implementations"
  → search_codebase("class.*Agent.*BaseAgent")
  → Returns: runner/agents/claude.py, runner/agents/gemini.py, etc.

Iteration 2:
  Agent: "Let me look at the agent factory pattern"
  → get_existing_pattern("agent_factory")
  → Returns: AgentFactory code from runner/agents/factory.py

Iteration 3:
  Agent: "What's the required structure for agents?"
  → get_file_content("runner/agents/base.py")
  → Returns: BaseAgent abstract class

Iteration 4:
  Agent: "Any specific rules I should follow?"
  → get_coding_rule("agent implementation")
  → Returns: Rules about invoke(), get_command(), etc.

Iteration 5:
  Agent: "Here's my Mistral agent code: [code]"
  Agent: "Let me verify it follows the pattern"
  → verify_follows_pattern(mistral_code, "agent_base")
  → Returns: {valid: true, notes: [...]}

Iteration 6:
  Agent: "Let me check for common pitfalls"
  → check_for_pitfalls(mistral_code)
  → Returns: {issues: ["Missing timeout in subprocess call"]}

Iteration 7:
  Agent: "I'll fix that and run tests"
  [Fixes code]
  → run_tests("tests/unit/test_agents.py")
  → Returns: {passed: 12, failed: 0}

Iteration 8:
  FINAL(mistral_agent_code)
```

#### Phase 4 Deliverables

| Deliverable | Description | Acceptance Criteria |
|-------------|-------------|---------------------|
| `tools/codebase_query.py` | Codebase navigation tools | Search, read, structure |
| `tools/pattern_verification.py` | Pattern compliance tools | Can verify against CLAUDE.md |
| `tools/test_runner.py` | Test execution tools | Run and parse tests |
| `tools/code_review.py` | Sub-agent code review | Delegation works |
| AI Dev RLM prompt | RLM-aware dev prompt | Tool-using workflow |
| Integration with Claude Code | Hook into existing flow | Transparent to user |

---

### Phase 5: Circuit Breaker Enhancements

**Goal:** Add RLM-specific safety limits to prevent runaway tool usage.

**Duration:** 1 week

#### New Limits

**Soft Limits (can be increased per-task):**

| Limit | Default | Description |
|-------|---------|-------------|
| `max_tool_calls_per_iteration` | 5 | Tool calls in single iteration |
| `max_iterations_per_state` | 10 | Iterations before forcing completion |
| `max_sub_agent_depth` | 2 | Levels of recursive delegation |
| `max_context_queries_per_iteration` | 10 | Context store queries |

**Hard Limits (cannot be overridden):**

| Limit | Value | Description |
|-------|-------|-------------|
| `max_tool_calls_total` | 100 | Total tool calls across all iterations |
| `max_iterations_total` | 50 | Total iterations regardless of state |
| `max_sub_agent_depth_hard` | 3 | Absolute max recursion |
| `max_tokens_per_sub_agent` | 50,000 | Token budget for sub-agents |

**Detection Rules:**

| Rule | Trigger | Action |
|------|---------|--------|
| `tool_loop_detection` | Same tool, same args 3+ times | Warn, then halt |
| `sub_agent_loop_detection` | Same sub-task delegated 3+ times | Halt |
| `progress_stall_detection` | No new info for 3 iterations | Force completion |

#### RLM Circuit Breaker Implementation

```
class RLMCircuitBreaker:
    
    # Tool usage tracking
    tool_call_history: List[ToolCall]
    sub_agent_history: List[SubAgentCall]
    
    method check_tool_call(tool_name, arguments) -> CircuitStatus:
        
        # Check for tool loops
        recent_same_calls = count_recent_calls(
            tool_name, arguments, 
            window=5  # Last 5 calls
        )
        if recent_same_calls >= 3:
            return CircuitStatus(
                tripped=True,
                reason="tool_loop",
                message=f"Tool {tool_name} called 3+ times with same args"
            )
        
        # Check total tool calls
        if len(tool_call_history) >= max_tool_calls_total:
            return CircuitStatus(
                tripped=True,
                reason="tool_limit",
                message="Max total tool calls exceeded"
            )
        
        return CircuitStatus(tripped=False)
    
    method check_sub_agent_call(task, context_keys) -> CircuitStatus:
        
        # Check depth
        current_depth = get_current_sub_agent_depth()
        if current_depth >= max_sub_agent_depth_hard:
            return CircuitStatus(
                tripped=True,
                reason="depth_limit",
                message=f"Sub-agent depth {current_depth} exceeds limit"
            )
        
        # Check for sub-agent loops
        similar_tasks = find_similar_tasks(task, sub_agent_history)
        if len(similar_tasks) >= 3:
            return CircuitStatus(
                tripped=True,
                reason="sub_agent_loop",
                message="Similar sub-task delegated 3+ times"
            )
        
        return CircuitStatus(tripped=False)
    
    method check_progress(execution_history) -> CircuitStatus:
        
        # Get last 3 iterations
        recent = execution_history[-3:]
        
        # Check if any new information was gained
        new_info = [
            iteration for iteration in recent
            if iteration.gained_new_info
        ]
        
        if len(recent) >= 3 and len(new_info) == 0:
            return CircuitStatus(
                tripped=True,
                reason="progress_stall",
                message="No progress in last 3 iterations"
            )
        
        return CircuitStatus(tripped=False)
```

#### Phase 5 Deliverables

| Deliverable | Description | Acceptance Criteria |
|-------------|-------------|---------------------|
| `circuit_breaker.py` updates | RLM-specific limits | All limits enforced |
| Tool loop detection | Detect repeated tool calls | Catches loops |
| Sub-agent depth tracking | Track recursion depth | Prevents infinite recursion |
| Progress stall detection | Detect lack of progress | Forces completion |
| Configuration options | Per-task limit overrides | Configurable via YAML |

---

## Component Specifications

### Context Store Specification

```yaml
# Context Store API

store:
  method: store(key, value, metadata)
  parameters:
    key: string            # Unique identifier
    value: any             # Content to store
    metadata:              # Optional metadata
      source: string       # Where this came from
      type: string         # Content type
      expires_at: datetime # Optional TTL
  returns: void

retrieve:
  method: retrieve(key)
  parameters:
    key: string
  returns: any
  raises: KeyError if not found

query:
  method: query(pattern, filters)
  parameters:
    pattern: string        # Search pattern
    filters:               # Optional filters
      types: List[string]
      min_score: float
  returns: List[Match]

list_available:
  method: list_available()
  returns: List[string]    # All keys

get_summary:
  method: get_summary(key, max_tokens)
  parameters:
    key: string
    max_tokens: int        # Summary length limit
  returns: string          # Condensed version

get_recent_updates:
  method: get_recent_updates(since_iteration)
  parameters:
    since_iteration: int   # Optional, defaults to 0
  returns: List[ContextUpdate]
    # ContextUpdate:
    #   key: string
    #   value: any
    #   iteration: int
    #   timestamp: datetime
  description: |
    Returns context items that were added or modified since a given iteration.
    Used by the state machine to track what changed during RLM execution.
```

### Tool Registry Specification

```yaml
# Tool Registry API

register:
  method: register(name, function, description, schema)
  parameters:
    name: string           # Tool name
    function: Callable     # Implementation
    description: string    # For agent prompt
    schema:                # Input schema
      type: object
      properties: Dict[string, TypeDef]
      required: List[string]
  returns: void

execute:
  method: execute(tool_name, arguments)
  parameters:
    tool_name: string
    arguments: Dict
  returns: ToolResult
    success: bool
    output: any
    error: Optional[string]
    execution_time: float

get_tool_descriptions:
  method: get_tool_descriptions(format)
  parameters:
    format: "prompt" | "json" | "openapi"
  returns: string | Dict
```

### RLM Environment Specification

```yaml
# RLM Environment API

initialize:
  method: initialize(context, tools, config)
  parameters:
    context: Dict[string, any]     # Initial context
    tools: ToolRegistry            # Available tools
    config:
      max_iterations: int
      max_tool_calls_per_iteration: int
      allow_sub_agents: bool
      sub_agent_config: SubAgentConfig
  returns: void

run:
  method: run(agent, task)
  parameters:
    agent: AgentAdapter            # The agent to run
    task: string                   # Task description
  returns: RLMResult
    success: bool
    answer: any
    history: List[ExecutionStep]
    metrics:
      iterations: int
      tool_calls: int
      sub_agent_calls: int
      tokens_used: int
      duration: float

# Execution Step Record
ExecutionStep:
  iteration: int
  type: "tool_call" | "sub_agent" | "response"
  content:
    tool_name: Optional[string]
    arguments: Optional[Dict]
    result: Optional[any]
    response_text: Optional[string]
  timestamp: datetime
```

---

## Configuration Schemas

### workflow_config.yaml RLM Extensions

```yaml
# Full schema for RLM-enabled workflow configuration

workflow:
  name: string
  initial_state: string
  
  # Global RLM settings
  rlm_defaults:
    max_iterations: 10
    max_tool_calls_per_iteration: 5
    allow_sub_agents: true
    sub_agent_model: "claude-haiku"
  
  states:
    <state_name>:
      type: initial | fan-out | single | orchestrator-task | human-approval | terminal
      
      # NEW: RLM execution mode
      execution_mode: legacy | rlm
      
      # NEW: Context setup (only for RLM mode)
      context_setup:
        - key: string                # Key in context store
          source: database | file | workflow_state | api
          query: string              # Source-specific query
          transform: Optional[string] # Optional transformation
      
      # NEW: Tools available to agents in this state
      tools:
        - name: string
          type: programmatic | sub_agent | recursive
          function: string           # For programmatic
          agent: string              # For sub_agent
          max_depth: int             # For recursive
          config: Dict               # Tool-specific config
      
      # Agent configuration (enhanced)
      agents:
        - name: string
          type: claude | gemini | openai | ollama  # Adapter type
          model: string              # e.g., "gpt-4o", "codex" (openai adapter)
          persona: string
          max_iterations: int        # NEW: Override default
          max_tool_calls: int        # NEW: Override default
      
      # NEW: Output storage
      outputs:
        - key: string                # Key pattern (can use {agent_name})
          store_in: context_store | workflow_state
          transform: Optional[string]
      
      transitions:
        - target: string
          condition: string
```

### Circuit Breaker Configuration

```yaml
# Circuit breaker configuration schema

circuit_breaker:
  # Soft limits (overridable per-state)
  soft_limits:
    max_iterations_per_state: 10
    max_tool_calls_per_iteration: 5
    max_sub_agent_depth: 2
    max_context_queries_per_iteration: 10
    timeout_seconds: 300
    cost_limit_usd: 1.00
  
  # Hard limits (never exceeded)
  hard_limits:
    max_iterations_total: 50
    max_tool_calls_total: 100
    max_sub_agent_depth_hard: 3   # Matches code reference at line 1438
    max_tokens_total: 500000
    timeout_seconds: 1800
    cost_limit_usd: 5.00

  # Detection rules
  detection:
    tool_loop:
      enabled: true
      threshold: 3              # Same tool+args this many times
      action: warn_then_halt
    
    sub_agent_loop:
      enabled: true
      threshold: 3              # Same sub-task this many times
      action: halt
    
    progress_stall:
      enabled: true
      iterations: 3             # No progress for this many iterations
      action: force_completion
    
    cost_spike:
      enabled: true
      threshold_multiplier: 3   # 3x expected cost
      action: warn
```

---

## Success Metrics

### Primary Metrics

| Metric | Current | Target | Measurement |
|--------|---------|--------|-------------|
| Word count compliance | ~70% | 95%+ | Automated check |
| Voice match score | ~6/10 | 8+/10 | Sub-agent evaluation |
| Formatting violations | ~20% | <5% | Automated check |
| Forbidden phrase usage | ~15% | <5% | Automated check |
| Code pattern compliance | ~60% | 90%+ | Tool verification |
| Tests pass after changes | ~70% | 95%+ | Test suite |
| Audit pass on first attempt | ~50% | 80%+ | Workflow logs |

### Secondary Metrics

| Metric | Description | Target |
|--------|-------------|--------|
| Tool calls per task | Average tools used | 5-15 |
| Iterations per state | Average iterations | 3-8 |
| Sub-agent delegations | Recursive calls | 1-3 |
| Cost per post | Total API cost | ≤ current |
| Time to completion | Wall clock time | ≤ 1.5x current |

### A/B Testing Plan

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     A/B TEST: LEGACY VS RLM MODE                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  SETUP:                                                                      │
│                                                                              │
│    Group A (Control): Legacy execution                                       │
│      - All context in prompt                                                 │
│      - Single-pass execution                                                 │
│      - Existing personas                                                     │
│                                                                              │
│    Group B (Treatment): RLM execution                                        │
│      - Context as queryable environment                                      │
│      - Iterative with tool verification                                      │
│      - RLM-enhanced personas                                                 │
│                                                                              │
│  METRICS TO COMPARE:                                                         │
│                                                                              │
│    1. Constraint Compliance Rate                                             │
│       - % of outputs meeting all constraints                                 │
│                                                                              │
│    2. Voice Match Score                                                      │
│       - Human evaluation: 1-10 scale                                         │
│       - Automated: embedding similarity to examples                          │
│                                                                              │
│    3. Audit Pass Rate                                                        │
│       - % of drafts passing audit on first attempt                          │
│                                                                              │
│    4. Total Cost Per Post                                                    │
│       - Including retries                                                    │
│                                                                              │
│    5. Time to Completion                                                     │
│       - Wall clock time for full workflow                                    │
│                                                                              │
│  SAMPLE SIZE: 50 posts per group                                             │
│  DURATION: 2 weeks                                                           │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Risk Mitigation

### Technical Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Tool loops drain budget | Medium | High | Circuit breaker detection |
| Sub-agent recursion explosion | Medium | High | Hard depth limits |
| Slower than legacy mode | Medium | Medium | Parallel execution, caching |
| Agent doesn't use tools | Low | High | Prompt engineering, examples |
| Context store memory bloat | Low | Medium | TTL, size limits |

### Operational Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Breaking existing workflows | Medium | High | Backward compatibility mode |
| Team learning curve | High | Medium | Documentation, training |
| Debugging complexity | Medium | Medium | Detailed logging, replay |

### Fallback Strategy

```
If RLM mode fails for a state:
  1. Log detailed error with execution history
  2. Attempt legacy mode execution
  3. If legacy succeeds, flag for investigation
  4. If legacy fails, trigger circuit breaker
  5. Human review of failed state
```

---

## Appendices

### Appendix A: RLM Pattern Origins

The Recursive Language Model (RLM) pattern described in this document is derived from
practical experience building LLM-powered systems, combined with established patterns
from the broader AI engineering community.

**Core Principles:**

1. **Externalized Context** - Treat long documents as queryable databases, not prompt content
2. **Tool-Based Verification** - Let agents verify their own work programmatically
3. **Recursive Delegation** - Complex tasks decompose into focused sub-agent calls
4. **REPL-Style Iteration** - Agents work in loops, refining until verification passes

**Influences:**

- ReAct (Reasoning + Acting) patterns for tool-using agents
- Chain-of-Thought prompting for step-by-step reasoning
- RAG (Retrieval-Augmented Generation) for external knowledge access
- Multi-agent orchestration patterns from AutoGPT, CrewAI, and similar systems

**Why "RLM":**

The name reflects the recursive nature of the pattern—agents can spawn sub-agents,
which can spawn their own sub-agents, with shared access to a context store.
This enables divide-and-conquer approaches to complex tasks.

### Appendix B: Glossary

| Term | Definition |
|------|------------|
| RLM | Recursive Language Model - inference strategy that externalizes context |
| Context Store | External storage for context that agents can query |
| Tool Registry | Collection of tools available to RLM agents |
| Sub-Agent | Delegated agent that handles a focused sub-task |
| Circuit Breaker | Safety mechanism to prevent runaway execution |
| Context Rot | Degradation of LLM performance as context grows |
| Fan-Out | State type where multiple agents run in parallel |

### Appendix C: File Change Summary

**New Files:**

```
runner/rlm/__init__.py
runner/rlm/environment.py
runner/rlm/context_store.py
runner/rlm/tool_registry.py
runner/rlm/sub_agent_manager.py
runner/rlm/tools/__init__.py
runner/rlm/tools/text_analysis.py
runner/rlm/tools/voice_matching.py
runner/rlm/tools/constraint_checks.py
runner/rlm/tools/codebase_query.py
runner/agents/rlm_agent.py
prompts/writer_rlm.md
prompts/auditor_rlm.md
prompts/synthesizer_rlm.md
tests/unit/test_context_store.py
tests/unit/test_tool_registry.py
tests/unit/test_rlm_environment.py
tests/integration/test_rlm_workflow.py
```

**Modified Files:**

```
runner/state_machine.py          # Add RLM execution mode
runner/circuit_breaker.py        # Add RLM-specific limits
runner/agents/base.py            # Add RLM capability
workflow_config.yaml             # Add RLM configuration
```

### Appendix D: Timeline

```
Week 1-2:   Phase 1 - RLM Infrastructure
Week 3-5:   Phase 2 - Persona Transformation
Week 5-6:   Phase 3 - State Machine Modifications
Week 6-8:   Phase 4 - AI Dev RLM Mode
Week 8-9:   Phase 5 - Circuit Breaker Enhancements
Week 9-10:  Testing, refinement, documentation
```

---

## Document History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-01-18 | Claude | Initial document |

---

*End of Document*
