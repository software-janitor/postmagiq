# Optimization Plan: Workflow & Credit Weighting

**Date:** January 15, 2026
**Subject:** Reducing COGS while maintaining quality via tiered workflows
**Status:** Proposal

---

## 1. Executive Summary

This plan proposes optimizing the `workflow_config.yaml` to shift from a "one-size-fits-all" expensive configuration to a tiered model. By reducing the default fan-out and reserving premium models for higher tiers, we can improve gross margins from ~33% to ~85% for standard runs without sacrificing core quality.

| Metric | Current State | Optimized Standard | Premium (Agency) |
| :--- | :--- | :--- | :--- |
| **Draft Agents** | 7 (Mixed) | 3 (Strong Standard) | 5 (Standard + Premium) |
| **Audit Agents** | 3 (inc. Opus) | 2 (Standard) | 2 (Premium) |
| **Est. Cost/Run** | ~$1.00 | ~$0.20 | ~$1.20 |
| **Credits Required** | 12 (Flat) | 7 (Weighted) | 25 (Weighted) |
| **Gross Margin** | ~33% | **~85%** | **~70%** |

---

## 2. Optimized Workflow Configuration

### A. Standard Tier (The New Default)
Designed for individual creators and teams who need consistent, high-quality content without breaking the bank.

**Draft Phase:**
*   **Agents:** `claude-sonnet`, `gemini-3-pro`, `gpt-5.2-medium`
*   **Justification:**
    *   **Quality:** Claude 3.5 Sonnet consistently outperforms original Opus in writing benchmarks. Gemini 1.5 Pro (via `gemini-3-pro`) offers a distinct alternative voice. GPT-5.1 Medium provides a balanced third perspective.
    *   **Redundancy:** 3 distinct model families ensure we don't get stuck in a "mode collapse" where all drafts look the same.
    *   **Cost:** All three are priced in the ~$3-5/1M input range, vs $15/1M for Opus.

**Audit Phase:**
*   **Agents:** `claude-sonnet`, `gemini-3-pro`
*   **Justification:**
    *   **Capability:** Sonnet has excellent reasoning capabilities for critique. We don't need Opus's "creative" cost premium for the analytical task of auditing.
    *   **Speed:** These models are significantly faster, reducing workflow latency.

### B. Premium Tier (Agency / Enterprise)
Designed for clients who demand the absolute "state of the art" reasoning or complex nuance.

**Draft Phase:**
*   **Agents:** `claude-sonnet`, `gemini-3-pro`, `claude-opus`, `gpt-5.2-high`
*   **Justification:** Adds the "High Reasoning" models. Opus is exceptional at creative nuance; GPT-5.1 High excels at complex instruction following.

**Audit Phase:**
*   **Agents:** `claude-opus`, `gpt-5.2-high`
*   **Justification:** Uses the most expensive "thinking" models to catch subtle errors standard models might miss.

---

## 3. Weighted Credit System

To protect margins, we move from "1 Run = 12 Credits" to a dynamic calculation based on compute intensity.

### Weight Definitions

| Model Tier | Models | Credit Multiplier |
| :--- | :--- | :--- |
| **Standard (1x)** | `claude-sonnet`, `gemini-3-pro`, `claude-haiku`, `gpt-5.2-medium` | 1 credit per step |
| **Premium (5x)** | `claude-opus`, `gpt-5.2-high` | 5 credits per step |

### Calculation Logic (Per Workflow)

Total Credits = `Base Cost` + `Σ(Draft Agents * Weight)` + `Σ(Audit Agents * Weight)`

**Example 1: Optimized Standard Run**
*   **Base:** 2 credits (Orchestrator overhead)
*   **Draft:** 3 agents (3 * 1x) = 3 credits
*   **Audit:** 2 agents (2 * 1x) = 2 credits
*   **Total:** **7 Credits**
*   **Cost:** ~$0.20
*   **Rev (Individual Plan):** $0.29 * 7 = $2.03 -> **10x ROAS**

**Example 2: Premium Agency Run**
*   **Base:** 2 credits
*   **Draft:** 2 Standard (2) + 2 Premium (10) = 12 credits
*   **Audit:** 2 Premium (10) = 10 credits
*   **Total:** **24 Credits**
*   **Cost:** ~$1.20
*   **Rev (Agency Plan):** $0.12 * 24 = $2.88 -> **2.4x ROAS** (Healthy margin maintained)

---

## 4. Implementation Guide

### Step 1: Update `workflow_config.yaml`

Replace the current expensive fan-out lists with the Optimized Standard lists.

```yaml
# workflow_config.yaml (Snippet)

draft:
  agents: [claude-sonnet, gemini-3-pro, gpt-5.2-medium] 

cross-audit:
  agents: [claude-sonnet, gemini-3-pro]

final-audit:
  agents: [claude-sonnet, gemini-3-pro]
```

### Step 2: Implement Config Overrides (Future)

Allow passing a config overlay at runtime for Premium runs:

```python
# runner/runner.py

def load_config(tier="standard"):
    base = load_yaml("workflow_config.yaml")
    if tier == "premium":
        base['states']['draft']['agents'] = [...] # Premium list
    return base
```

### Step 3: Update Pricing Page
*   **Individual/Team:** "Includes Standard Generation (Claude Sonnet, Gemini Pro)"
*   **Agency:** "Includes Premium Generation (Claude Opus, GPT-High Reasoning)"

---

## 5. Justification on Quality vs. Cost

**Why remove Opus from the default?**
Recent benchmarks (Jan 2026 era) show `claude-3-5-sonnet` matching or exceeding `claude-3-opus` in writing quality and reasoning, while being **5x cheaper** and **2x faster**. Using Opus as a default draft writer is currently burning cash for diminishing returns. Opus remains valuable for specific "creative lateral thinking" tasks, which justifies its place in the Premium tier, but it is overkill for standard LinkedIn content generation.

**Why reduce fan-out from 7 to 3?**
Diminishing returns. Synthesizing 7 drafts often leads to a "mushy" average. 3 distinct, high-quality drafts (Sonnet, Gemini, GPT) provide enough variance for the synthesizer to pick "the best hook" or "the best structure" without overwhelming the context window with 7 versions of the same story.
