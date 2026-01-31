# Modular Persona System Plan

**Status:** Planning
**Created:** 2026-01-16
**Last Updated:** 2026-01-16

## Overview

Transform the monolithic persona system into a modular architecture with:
- Universal rules (apply to all personas)
- Voice profiles (user's writing style)
- Persona templates (role-specific instructions)
- AI detector (scores writing for "AI tells")

### Voice Profile Assignment

| Persona | Gets Voice? | Reason |
|---------|-------------|--------|
| Writer | Yes | Produces drafts in user's voice |
| Synthesizer | Yes | Produces final post in user's voice |
| Auditor | Yes | Evaluates if drafts match user's voice |
| Story Reviewer | No | Asks clarifying questions (analytical) |
| Story Processor | No | Extracts elements (structured output) |
| Input Validator | No | Validates input (analytical) |
| AI Detector | No | Scores for tells (analytical) |

---

## Task Tracker

### Phase 1: Database + API Foundation
| Task | Status | Notes |
|------|--------|-------|
| Create `voice_profiles` table model | [ ] Pending | `runner/content/models.py` |
| Create `universal_rules` table model | [ ] Pending | `runner/content/models.py` |
| Add `voice_profile_id` FK to `workflow_personas` | [ ] Pending | Migration needed |
| Create Alembic migration | [ ] Pending | `alembic/versions/xxx_voice_profiles.py` |
| Add voice profile DB methods | [ ] Pending | `runner/content/database.py` |
| Create voice profiles API routes | [ ] Pending | `api/routes/voice_profiles.py` |
| Update personas API for composition | [ ] Pending | `api/routes/workflow_personas.py` |

### Phase 2: Content Extraction & Refactor
| Task | Status | Notes |
|------|--------|-------|
| Extract universal rules from CLAUDE.md | [ ] Pending | `prompts/universal_rules.md` |
| Extract Matthew's voice profile | [ ] Pending | `prompts/voice_profiles/matthew-garcia.md` |
| Create professional preset | [ ] Pending | `prompts/voice_profiles/professional.md` |
| Create conversational preset | [ ] Pending | `prompts/voice_profiles/conversational.md` |
| Refactor writer template (remove voice) | [ ] Pending | `prompts/templates/writer.md` |
| Refactor auditor template | [ ] Pending | `prompts/templates/auditor.md` |
| Refactor synthesizer template | [ ] Pending | `prompts/templates/synthesizer.md` |
| Refactor all other templates | [ ] Pending | story-reviewer, story-processor, etc. |

### Phase 3: GUI Updates
| Task | Status | Notes |
|------|--------|-------|
| Create Voice Profiles page | [ ] Pending | `gui/src/pages/VoiceProfiles.tsx` |
| Update AI Personas page | [ ] Pending | Show composition preview |
| Add voice profile selector | [ ] Pending | In workflow settings |
| Add "Preview composed prompt" | [ ] Pending | |

### Phase 4: Voice Upload Feature
| Task | Status | Notes |
|------|--------|-------|
| Create upload endpoint | [ ] Pending | Accept writing samples |
| AI extraction of voice characteristics | [ ] Pending | Analyze tone, phrases, style |
| Generate voice profile from samples | [ ] Pending | Store as custom profile |

### Phase 5: AI Detector Audit
| Task | Status | Notes |
|------|--------|-------|
| Create ai-detector persona template | [ ] Pending | `prompts/templates/ai-detector.md` |
| Add to workflow config | [ ] Pending | After final-audit or integrated |
| Return score (1-10) + tells list | [ ] Pending | |

### Migration & Testing
| Task | Status | Notes |
|------|--------|-------|
| Create migration script | [ ] Pending | `scripts/migrate_personas.py` |
| Seed Matthew Garcia voice profile | [ ] Pending | |
| Validate existing workflows work | [ ] Pending | Regression test |
| Integration tests for composition | [ ] Pending | |

---

## Architecture

### Data Model

```
┌─────────────────────┐
│  universal_rules    │
├─────────────────────┤
│ id                  │
│ content             │ ← "Never expose framework", "No em-dashes", etc.
│ is_active           │
└─────────────────────┘

┌─────────────────────┐
│  voice_profiles     │
├─────────────────────┤
│ id                  │
│ user_id             │
│ name                │ ← "Matthew Garcia", "Professional", etc.
│ slug                │
│ content             │ ← Tone, phrases, examples, word choices
│ is_preset           │ ← True for system presets
└─────────────────────┘

┌─────────────────────┐
│  workflow_personas  │
├─────────────────────┤
│ id                  │
│ user_id             │
│ name                │ ← "Writer", "Auditor", "Synthesizer"
│ slug                │
│ content             │ ← Role-specific task instructions ONLY
│ voice_profile_id    │ ← FK to voice_profiles (optional)
│ is_system           │
└─────────────────────┘
```

### Composition at Runtime

```python
def get_composed_prompt(persona_id: int, user_id: int) -> str:
    persona = db.get_workflow_persona(persona_id)
    voice = db.get_voice_profile(persona.voice_profile_id or user_default)
    rules = db.get_universal_rules()

    return f"""
{rules.content}

{voice.content}

{persona.content}
"""
```

---

## Content Structure

### Universal Rules (`prompts/universal_rules.md`)
```markdown
# Universal Rules (Apply to ALL Personas)

## NEVER Expose Framework
These are internal labels. NEVER use them in output:
- "the scar was...", "the turning point was...", "the shift was..."
- "the lesson here is...", "the takeaway is...", "what I learned was..."
- "the failure was...", "the misconception is...", "the enemy is..."

## Sound Human
- Write like thinking out loud to a peer
- No keynote energy, no corporate speak
- Use natural contractions ("didn't" not "did not")
- The Bar Test: Would you say this at a bar?

## Style Rules
- NO em-dashes (—) — use periods, commas, short sentences
- NO passive voice ("It was ignored" → "Claude ignored it")
- NO essay transitions ("Ultimately," "In summary," "Overall")
- NO filler words ("completely," "very," "really")
```

### Voice Profile (`prompts/voice_profiles/matthew-garcia.md`)
```markdown
# Matthew Garcia's Voice

## Tone
- Reflective and personal
- Vulnerable about what you didn't know
- Self-critical but not self-flagellating
- Warm, humble, human

## Signature Phrases (use sparingly)
- "I never imagined..."
- "What I didn't realize was..."
- "It took me time to realize..."
- "I learned the hard way that..."
- "AI amplifies whatever already exists..."
- "The tool wasn't the problem. The system was."

## Word Choices
- "assuming" over "hoping" (shows ownership)
- "a familiar trap" over "the classic trap" (less cliche)
- "well-scoped" over "focused" (technical credibility)
- "advice" over "wisdom" (more grounded)

## Example Excerpts
> "I accepted the changes anyway."
>
> "The build broke."

> "I'm still refining my assistant. We'll see how this year turns out."
```

### Persona Template (`prompts/templates/synthesizer.md`)
```markdown
# Synthesizer Template

## Your Role
Editor combining the best parts of multiple drafts into one cohesive post.

## Task
1. Read all drafts and audit feedback
2. Pick the best elements (strongest opening, most natural voice, best details)
3. Weave into single post that reads like one person wrote it
4. 250-400 words, flowing prose

## Rules
- ZERO FABRICATION: Only use details from source drafts
- PRESERVE QUOTES: Keep exact wording when source quotes someone
- MINIMAL REVISION: When given small edit requests, make only those edits

## Output
Write the post directly. No meta-commentary.
```

---

## Migration Path

1. Extract voice content from existing personas into voice profile
2. Extract universal rules into separate file
3. Refactor persona files to contain only role-specific content
4. Run migration script to create DB records
5. Validate existing workflows produce same quality

---

## Verification Checklist

- [ ] Voice profile CRUD works via API
- [ ] Personas compose correctly (universal + voice + template)
- [ ] GUI can manage voice profiles
- [ ] Existing workflows still function
- [ ] Synthesizer produces natural voice
- [ ] AI detector scores output and lists tells
- [ ] Matthew's voice profile matches current quality
