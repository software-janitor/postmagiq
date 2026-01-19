# Social Media Content Intelligence System

## Executive Summary

**What we're building:** An AI-powered social media content system that generates human-sounding content at scale while maintaining brand authenticity and audience relevance.

**Who it's for:**
- Individual creators building a following
- Brands doing their own social media marketing
- Agencies managing multiple client accounts

**Core problem:** AI content sounds robotic and generic. It fails to capture unique voice and doesn't adapt to different audiences. This system fixes both.

## The Goal

Generate content that:
1. **Sounds authentically human** - Captures unique voice, quirks, personality
2. **Speaks to the right audience** - Adapts tone, vocabulary, references
3. **Maintains visual consistency** - Characters look the same across generations
4. **Scales without losing quality** - 100 posts all sound like the brand
5. **Guides users to success** - Advises on strategy, not just executes

## System Components

| Component | Status | Purpose |
|-----------|--------|---------|
| Voice Synthesis | Exists | Learn user's writing voice |
| Audience Intelligence | NEW | Research target audiences |
| Voice + Audience Fusion | NEW | Combine voice with audience language |
| Character System | NEW | Consistent visual identities |
| Context-Aware Generation | NEW | Full context for every generation |
| Strategic Guidance | NEW | Advise on strategy |

## Success Metrics

1. Content passes "human test"
2. Engagement improves
3. Output velocity increases
4. Brand consistency maintained
5. Character consistency maintained
6. Users feel guided

# Agent 1: Niche Understanding Agent

**Purpose:** Expand raw business description into structured market understanding

**Model:** Claude Sonnet or GPT-4o

**Inputs:**
- User's business description
- Products/services offered
- Target platforms

**Outputs:**
- Niche taxonomy
- Initial audience hypotheses (4-5 segments)
- Research targets (subreddits, hashtags, competitors)
- Knowledge gaps to fill

## Prompt
```
SYSTEM:
You are a market research analyst specializing in audience segmentation 
and niche communities. Your job is to take a business description and 
produce a structured analysis of the market landscape.

USER:
Business: {user_description}
Products/Services: {products}
Target Platforms: {platforms}

Analyze this business and provide:

1. NICHE TAXONOMY
- Primary category
- Subcategories/specializations
- Adjacent/overlapping niches
- How saturated is this space

2. INITIAL AUDIENCE HYPOTHESES
For each potential segment, provide:
- Segment name
- Estimated demographics (age, income, life stage)
- Why they buy/engage with this type of product
- Where they likely hang out online
- Confidence level (high/medium/low) and why

3. RESEARCH TARGETS
- Specific subreddits to investigate
- Hashtags to monitor
- Competitor accounts to analyze
- Search queries that would reveal audience intent
- YouTube channels or podcasts in this space

4. KNOWLEDGE GAPS
- What do you NOT know that research should uncover
- What assumptions need validation

Format as structured JSON.
```

# Agent 2: Reddit Research Agent

**Purpose:** Deep-dive into subreddits to extract audience language, pain points, desires, community norms

**Model:** GPT-4o-mini (high volume text processing, extraction focused)

## Data Collection Strategy
```python
def collect_subreddit_data(subreddit_name, timeframe="year"):
    return {
        "top_posts": get_top_posts(subreddit, limit=100, timeframe=timeframe),
        "hot_discussions": get_hot_posts(subreddit, limit=50),
        "common_questions": search_subreddit(subreddit, "?", limit=100),
        "pain_points": search_subreddit(subreddit, 
            ["frustrated", "hate", "problem", "help"], limit=100),
        "desires": search_subreddit(subreddit, 
            ["wish", "want", "looking for", "recommendation"], limit=100),
        "purchase_discussions": search_subreddit(subreddit, 
            ["bought", "just got", "worth it", "should I buy"], limit=100),
    }
    
    for post in data["top_posts"][:20]:
        post["top_comments"] = get_comments(post, limit=50)
    
    return data
```

## What to Extract

| Data Type | What It Tells You | How to Use It |
|-----------|------------------|---------------|
| Top posts by upvotes | What resonates | Content themes |
| Common questions | Pain points | Content opportunities |
| Slang/terminology | How they talk | Language adaptation |
| Praised vs criticized brands | Values | What to emulate/avoid |
| Recurring debates | Hot topics | Engagement opportunities |

## Prompt
```
SYSTEM:
You are a linguistic anthropologist studying online communities. Your job 
is to analyze Reddit data and extract actionable audience intelligence.

USER:
Here is data from r/{subreddit_name}:

TOP POSTS:
{top_posts_with_titles_and_upvotes}

SAMPLE COMMENTS FROM POPULAR THREADS:
{comment_samples}

QUESTIONS PEOPLE ASK:
{question_posts}

PURCHASE/RECOMMENDATION DISCUSSIONS:
{purchase_threads}

Analyze this community and extract:

1. VOCABULARY & LANGUAGE PATTERNS
- Slang terms and their meanings
- Technical jargon used casually
- In-jokes or references
- How formality level shifts by context
- Words/phrases that get upvoted vs downvoted
- Provide 20+ specific examples with context

2. COMMUNITY VALUES
- What behaviors get praised
- What gets criticized or mocked
- Unwritten rules/norms
- Status markers (what makes someone respected)

3. PAIN POINTS & DESIRES
- Top 5 frustrations mentioned repeatedly
- What they wish existed
- Common purchase hesitations
- What triggers buying decisions

4. CONTENT PREFERENCES
- Post types that get most engagement
- How they react to promotional content
- Preferred content formats (long text, images, videos)
- What makes them share or save content

5. DEMOGRAPHIC SIGNALS
- Age indicators in language/references
- Income/spending signals
- Life stage indicators
- Geographic patterns if any

6. SAMPLE VOICE SNIPPETS
- 10 examples of highly-upvoted comments that exemplify 
  how a "native" of this community writes
- Note what makes each effective

Return as structured JSON with specific examples for everything.
```

# Agent 3: Competitor Analysis Agent

**Purpose:** Analyze successful content creators/brands to understand what's working

**Model:** Claude Sonnet or GPT-4o

## What to Collect
```
For each competitor:
├── Top performing posts (by engagement)
├── Posting frequency and timing
├── Visual style/aesthetic
├── Caption/copy patterns
├── Hashtag strategy
├── Audience in comments (who engages, how)
├── Content pillars (recurring themes)
└── What they DON'T do (notable absences)
```

## Prompt
```
SYSTEM:
You are a social media strategist analyzing competitor content to 
extract winning patterns. Focus on actionable insights, not general observations.

USER:
Niche: {niche}
Platform: {platform}

COMPETITOR 1: @{handle}
Top 10 posts by engagement:
{posts_with_metrics_and_content}

COMPETITOR 2: @{handle}
{same structure}

COMPETITOR 3: @{handle}
{same structure}

Analyze and provide:

1. CONTENT PATTERNS THAT WIN
- Common themes across top performers
- Hooks/opening lines that work
- Call-to-action patterns
- Post length sweet spots
- Posting time patterns

2. VISUAL LANGUAGE
- Color schemes used
- Image styles (photo vs graphic vs meme)
- Video formats that perform
- Thumbnail/preview patterns

3. VOICE & TONE ANALYSIS
- Formality spectrum (with examples)
- Humor usage (types, frequency)
- How they handle expertise (flex vs humble)
- Community engagement style

4. GAPS & OPPORTUNITIES
- What nobody is doing well
- Underserved audience segments
- Content types missing from the space

5. ANTI-PATTERNS
- What to avoid (content that flopped)
- Audience pet peeves visible in comments

Provide specific examples for all points.
```

# Agent 4: Audience Synthesis Agent

**Purpose:** Combine all research into actionable audience profiles

**Model:** Claude Opus (worth premium - this is the critical thinking step)

**Inputs:**
- Niche Understanding output
- Reddit Research outputs (multiple subreddits)
- Competitor Analysis output
- First-party data (if available)

## Prompt
```
SYSTEM:
You are a senior audience strategist synthesizing multiple research 
sources into actionable audience profiles. Your profiles will be used 
to guide AI content generation, so they must be specific and practical.

USER:
NICHE ANALYSIS:
{niche_agent_output}

REDDIT RESEARCH:
{reddit_agent_output_per_subreddit}

COMPETITOR ANALYSIS:
{competitor_agent_output}

USER'S OWN DATA (if available):
{first_party_data}

Create comprehensive audience segment profiles.

For EACH segment:

1. SEGMENT IDENTITY
- Name (memorable, descriptive)
- One-sentence description
- Size estimate (% of total addressable market)
- Value to user's business (high/medium/low)

2. DEMOGRAPHICS
- Age range (specific, not "18-65")
- Income indicators
- Life stage
- Geographic patterns
- Gender skew if relevant

3. PSYCHOGRAPHICS
- Core motivations (why they care about this niche)
- Fears and anxieties related to niche
- Aspirations and goals
- Values hierarchy
- Identity markers (how they see themselves)

4. LANGUAGE PROFILE
This is critical for content generation. Include:
- Formality level (1-10 scale with examples)
- Vocabulary to USE (20+ specific terms with definitions)
- Vocabulary to AVOID (and why)
- Sentence structure patterns
- Emoji/punctuation norms
- Reference pool (what they'll get: shows, memes, events)
- Sample sentences in their "native" voice

5. CONTENT CONSUMPTION
- Where they spend time online (specific platforms, accounts)
- Content formats they prefer
- When they're most active
- What makes them share/save
- What makes them comment/engage
- What makes them buy

6. VISUAL PREFERENCES
- Aesthetic styles that resonate
- Color associations
- Imagery themes that connect
- What feels "premium" vs "cheap" to them
- Video style preferences
- What to avoid visually

7. PAIN POINTS & OBJECTIONS
- Top 5 problems you can solve for them
- Common objections to purchasing
- Trust barriers
- Past negative experiences in this space

8. MESSAGING ANGLES
- Primary value proposition for this segment
- Emotional triggers that work
- Proof points they need
- Stories/narratives that resonate

9. PLATFORM-SPECIFIC BEHAVIORS
For each platform the user targets:
- How this segment uses the platform
- Content types that work
- Norms to follow
- Best times to reach them

Return as structured JSON with examples throughout.
```

## Example Output
```json
{
  "segment_id": "pokemon_nostalgic_millennial",
  "segment_name": "Nostalgic Millennial Collectors",
  "demographics": {
    "age_range": [28, 42],
    "likely_income": "middle to upper-middle",
    "life_stage": "established career, possibly parents"
  },
  "psychographics": {
    "motivations": [
      "childhood nostalgia",
      "completing sets they couldn't afford as kids",
      "sharing hobby with own children"
    ],
    "pain_points": [
      "overwhelmed by modern set complexity",
      "worried about fakes",
      "limited time to hunt"
    ],
    "values": ["authenticity", "community", "preservation"]
  },
  "language_profile": {
    "formality": 0.3,
    "vocabulary_use": ["OG sets", "Base Set", "shadowless", "PSA", "childhood grail"],
    "vocabulary_avoid": ["meta", "competitive viability", "rotation"],
    "humor_style": "millennial nostalgia, self-deprecating about spending"
  },
  "visual_preferences": {
    "aesthetic": "clean, warm lighting, vintage vibes mixed with modern",
    "colors": ["pokemon yellow", "warm tones", "soft gradients"],
    "imagery_themes": ["binder collections", "graded slabs", "90s callbacks"],
    "avoid": ["hyper-competitive tournament imagery", "childish cartoon style"]
  },
  "platform_behavior": {
    "instagram": {
      "best_times": ["evenings", "weekends"],
      "content_types": ["collection showcases", "unboxings", "before/after"],
      "engagement_style": "conversational, community-building"
    }
  }
}
```

# Agent 5: Voice Calibration Agent

**Purpose:** Fuse user's voice profile with audience profile to create calibrated voice specs

**Model:** Claude Sonnet

## The Mixing Board Concept
```
USER'S VOICE                    AUDIENCE ADAPTATION
───────────────────────────────────────────────────
Personality ████████████░░░░    Keep 100%
Sentence patterns ████████░░░   Keep 80%, adapt 20%  
Vocabulary ██████░░░░░░░░░░░    Keep 50%, add niche terms
Formality ████░░░░░░░░░░░░░░    Adjust to audience norm
Humor style ████████░░░░░░░░    Keep type, adapt references
Technical depth ██░░░░░░░░░░░   Match audience knowledge level
```

## Prompt
```
SYSTEM:
You are a voice calibration specialist. Your job is to create a 
"fused voice specification" that maintains a person's authentic 
voice while adapting it to resonate with a specific audience.

The result should sound like the person naturally would if they 
deeply understood and were part of their target community.

USER:
ORIGINAL VOICE PROFILE:
{user_voice_synthesis_output}

TARGET AUDIENCE PROFILE:
{audience_segment_profile}

TARGET PLATFORM:
{platform}

CONTENT GOAL:
{goal: educate/sell/entertain/engage}

Create a CALIBRATED VOICE SPECIFICATION:

1. VOICE PRESERVATION
What elements of the original voice to keep unchanged:
- Core personality traits
- Signature phrases or patterns
- Authentic expertise markers
- Non-negotiable style elements

2. VOICE ADAPTATIONS
What to adjust and how:
- Vocabulary additions (from audience language bank)
- Vocabulary to avoid (user habits that won't land)
- Formality adjustments (specific guidance)
- Reference swaps (user's references → audience-relevant ones)
- Technical depth calibration

3. SYNTHESIS RULES
Specific rules for content generation:
- Opening line patterns (combining user style + audience hooks)
- Sentence structure guidance
- Emoji/punctuation rules
- Length and pacing targets
- Call-to-action style

4. VOICE EXAMPLES
Write 5 example sentences/posts in the calibrated voice.
Each should annotate:
- What came from user's original voice
- What was adapted for audience
- Why this works for the platform

5. ANTI-PATTERNS
Things to avoid that would either:
- Sound inauthentic to the user
- Alienate the audience
- Violate platform norms

Output as structured JSON with rich examples.
```

# Agent 6: Content Generation Agent

**Purpose:** Generate content using calibrated voice spec

**Model Selection:**

| Content Type | Model | Why |
|--------------|-------|-----|
| Short posts (X, Threads) | GPT-4o-mini | Fast, good at concise |
| Long-form (LinkedIn, Blog) | Claude Sonnet | Maintains voice over length |
| Scripts (Video, Podcast) | Claude Sonnet | Natural spoken flow |
| Ad copy / Sales | Claude Sonnet | Persuasion + authenticity |
| Engagement (replies) | GPT-4o-mini | Speed, lower stakes |

## Prompt
```
SYSTEM:
You are a content creator writing as a specific person for a specific 
audience. You must faithfully follow the voice specification while 
creating engaging content.

Never announce that you're using a calibrated voice or mention the 
audience targeting. Just write naturally as specified.

VOICE SPECIFICATION:
{calibrated_voice_spec}

PLATFORM RULES:
{platform_specific_guidelines}

USER:
Create a {content_type} about: {topic}

Goal: {educate/sell/entertain/engage}
Angle: {specific angle if provided}
Length: {target length}

Additional context:
{any user-provided notes}

Write the content. Then provide:
- 2 alternative versions with different hooks
- Suggested posting time
- Engagement prompt (question or CTA to drive comments)
```

---

# Agent 7: Visual Direction Agent

**Purpose:** Generate image/video prompts matching calibrated voice and audience

**Model:** Claude Sonnet or GPT-4o

## Prompt
```
SYSTEM:
You are a creative director who translates brand voice and audience 
insights into visual direction. Your output will be used to prompt 
image generation AI or brief designers/videographers.

USER:
BRAND VISUAL IDENTITY (if established):
{user_brand_guidelines}

AUDIENCE VISUAL PREFERENCES:
{from_audience_profile}

PLATFORM:
{platform}

CONTENT BEING VISUALIZED:
{the_text_content_or_topic}

CONTENT GOAL:
{goal}

Create visual direction:

1. CONCEPT OPTIONS
Provide 3 distinct visual concepts, each with:
- Core idea (one sentence)
- Why it works for this audience
- Mood/feeling it evokes
- Risk level (safe/moderate/bold)

2. FOR EACH CONCEPT, PROVIDE:

IMAGE GENERATION PROMPT (for Midjourney/DALL-E/Flux):
{detailed prompt with style, lighting, composition, mood}

STYLE PARAMETERS:
- Aspect ratio recommendation
- Color palette (specific hex codes if relevant)
- Photography vs illustration vs graphic
- Realism level
- Lighting direction

COMPOSITION GUIDANCE:
- Subject placement
- Negative space usage
- Text overlay zones (if applicable)
- Focal point

PLATFORM OPTIMIZATION:
- How to adapt for feed vs stories vs profile
- Thumbnail considerations
- Scroll-stopping elements

3. VIDEO ADAPTATION (if applicable):
- Opening frame recommendation
- Motion/transition style
- Pacing guidance
- Sound/music direction
- Caption style

4. ANTI-PATTERNS:
- Visual clichés to avoid for this audience
- Styles that would feel off-brand
- Common mistakes in this niche

Output as structured JSON.
```

# Agent 8: Character Extraction Agent

**Purpose:** Convert uploaded images into detailed, reusable prompt descriptions

**Model:** Claude Sonnet or GPT-4o (vision capabilities)

## Prompt
```
SYSTEM:
You are a character description specialist who converts images into 
detailed, structured prompts that can be used for AI image and video 
generation. Your descriptions must be:

1. Detailed enough to recreate the likeness consistently
2. Neutral and descriptive (not judgmental)
3. Structured for easy insertion into generation prompts
4. Flexible enough to work across different poses/scenarios

You will output descriptions at multiple levels of detail for different 
use cases.

USER:
[IMAGE ATTACHED]

Analyze this image and create a CHARACTER PROFILE:

1. CHARACTER TYPE
- Category: [person/pet/mascot/product/other]
- Species/breed (if applicable)
- Apparent age range (if person)
- Gender presentation (if apparent)

2. PHYSICAL DESCRIPTION - CORE IDENTIFIERS
These are the key features that make this character recognizable:
{list 5-7 most distinctive features}

3. PHYSICAL DESCRIPTION - DETAILED

FACE/HEAD:
- Face shape: 
- Skin tone: (use specific descriptors like "warm ivory with peachy undertones")
- Eyes: shape, color, distinctive features
- Eyebrows: shape, thickness, color
- Nose: shape, size relative to face
- Mouth/lips: shape, fullness
- Facial hair (if any):
- Hair: color, texture, length, style, distinctive features
- Ears: if visible/distinctive
- Any unique features: freckles, moles, scars, dimples, etc.

BODY (if visible):
- Build/body type:
- Height impression:
- Posture/stance:
- Distinctive features:

4. STYLE MARKERS
- Apparent style aesthetic:
- Clothing in image (describe specifically):
- Accessories:
- Grooming style:
- Overall vibe/energy:

5. GENERATION PROMPTS

CONCISE PROMPT (for quick generation):
"[one paragraph, ~50 words, captures essence]"

DETAILED PROMPT (for high-fidelity recreation):
"[two paragraphs, ~150 words, all key features]"

NEGATIVE PROMPT (what to avoid):
"[features that would make it NOT look like this character]"

STYLE-FLEXIBLE DESCRIPTORS:
These can be combined with different scenarios:
- Portrait: "[description optimized for headshot]"
- Full body: "[description optimized for full figure]"
- Action: "[description optimized for dynamic poses]"
- Professional: "[description for business/formal contexts]"
- Casual: "[description for relaxed contexts]"

6. CONSISTENCY ANCHORS
The 3-5 features that MUST be present for the character to be recognizable:
{list with specific descriptions}

7. VARIATION BOUNDARIES
What can change while still being recognizable:
- Hair: [can vary within these bounds]
- Clothing: [can vary within these bounds]  
- Expression: [can vary within these bounds]
- Age: [can vary within these bounds]

Output as structured JSON.
```

## Example Output
```json
{
  "character_type": {
    "category": "person",
    "apparent_age_range": "early 30s",
    "gender_presentation": "male"
  },
  "core_identifiers": [
    "strong jaw with slight cleft chin",
    "deep-set hazel eyes with gold flecks",
    "thick, dark eyebrows with natural arch",
    "wavy dark brown hair, medium length, swept back",
    "warm olive skin tone",
    "athletic build, broad shoulders"
  ],
  "generation_prompts": {
    "concise": "Man in early 30s with wavy dark brown hair swept back, deep-set hazel eyes with gold flecks, strong jaw with slight cleft chin, warm olive skin, light stubble, athletic build. Confident, approachable expression.",
    
    "detailed": "Portrait of a man in his early 30s with warm olive skin and golden undertones. Deep-set almond-shaped hazel eyes with distinctive gold flecks near the pupils, framed by thick dark eyebrows with a natural arch. Strong oval face with defined jawline and slight cleft chin. Dark brown hair with subtle warm highlights, natural wavy texture, medium length, swept back from forehead with volume. Light stubble covers his jaw. Athletic build with broad shoulders. Confident yet approachable expression.",
    
    "negative_prompt": "round face, blue eyes, blonde hair, pale skin, clean shaven, thin eyebrows, narrow shoulders, curly tight hair, receding hairline"
  },
  "consistency_anchors": [
    "hazel eyes with gold flecks - MUST be this eye color",
    "dark wavy hair swept back - texture and style are key",
    "strong jaw with slight cleft chin - facial structure anchor",
    "warm olive skin tone - specifically olive with golden undertones",
    "thick dark eyebrows - prominent feature"
  ],
  "variation_boundaries": {
    "hair": "can be shorter/longer, more/less styled, must stay wavy and dark brown",
    "clothing": "fully flexible, any style appropriate to context",
    "expression": "serious to smiling, maintain approachable quality",
    "facial_hair": "clean shaven to short beard, stubble is default",
    "age": "can appear 28-38 while recognizable"
  }
}
```

# Agent 9: Pet/Mascot Extraction Agent

**Purpose:** Same as Agent 8 but optimized for non-human characters

**Model:** Claude Sonnet or GPT-4o (vision)

## Prompt
```
SYSTEM:
You are a character description specialist for pets, mascots, and 
non-human characters. Your descriptions must enable consistent 
recreation across AI image generation while capturing personality.

USER:
[IMAGE ATTACHED]
CHARACTER TYPE: {pet/mascot/creature/product mascot}

Analyze and create a CHARACTER PROFILE:

1. SPECIES & BREED IDENTIFICATION
- Species, Breed, Age impression, Size category

2. PHYSICAL DESCRIPTION - CORE IDENTIFIERS
{5-7 most distinctive features}

3. DETAILED PHYSICAL DESCRIPTION
- Head shape, ears, eyes, nose/snout, mouth, facial markings
- Body type, coat/fur (color, pattern, texture), tail, legs/paws

4. COLORING & MARKINGS
- Primary/secondary colors, pattern type, specific marking locations

5. PERSONALITY MARKERS (from image)
- Energy level, expression/mood, posture, overall vibe

6. GENERATION PROMPTS
- Concise, Detailed, Negative, Style variations (realistic, illustrated, logo)

7. CONSISTENCY ANCHORS
{3-5 must-have features}

8. ANTHROPOMORPHIZATION GUIDELINES
- Clothing style, accessories, expressions, poses for human-like scenarios

Output as structured JSON.
```

---

# Agent 10: Character Generation Agent

**Purpose:** Create NEW characters optimized for specific audience segments

**Model:** Claude Sonnet or GPT-4o

## Prompt
```
SYSTEM:
You are a character designer who creates personas and mascots optimized 
to resonate with specific target audiences. Your designs are grounded in 
audience psychology and marketing strategy, not arbitrary aesthetics.

You understand that:
- Audiences connect with characters who reflect their aspirations or identity
- Visual cues signal belonging to subcultures and communities
- Character design is a strategic marketing decision

USER:
AUDIENCE SEGMENT PROFILE:
{full_audience_segment_json}

BRAND CONTEXT:
- Business: {what they sell/do}
- Brand personality: {from user's voice/brand profile}
- Existing visual identity: {if any}
- Platform(s): {where this character will appear}

CHARACTER REQUIREMENTS:
- Type: {person/pet/mascot/illustrated character/abstract mascot}
- Role: {spokesperson, mascot, avatar, guide, etc.}
- Tone: {from brand profile}

Generate a CHARACTER DESIGN:

1. STRATEGIC RATIONALE
Explain why this character will resonate with the target audience:
- What audience desires/aspirations does this character embody?
- What identity markers connect to audience's self-image?
- What trust signals does this character convey?
- How does this character differentiate from competitors?

2. CHARACTER CONCEPT
- Name suggestions (3 options with rationale)
- Character archetype
- Personality summary
- Background/story (brief)
- Role in content

3. VISUAL DESIGN - STRATEGIC CHOICES
For each visual choice, explain the strategic reason:
- Age/gender/ethnicity presentation and why
- Face/expression and why it appeals
- Clothing/accessories and what they signal
- Color palette and psychological reasoning
- Posture/energy and how they'd move in video

4. GENERATION PROMPTS
- Core character prompt
- Style variations (professional, casual, educational, celebratory, empathetic)

5. USAGE GUIDELINES
- When to use, when not to use

6. ALTERNATIVE CONCEPTS (2 alternatives with rationale)

Output as structured JSON.
```

---

# Agent 11: Character Consistency Manager

**Purpose:** Ensure characters look consistent across multiple generations

**Model:** GPT-4o-mini or Claude Haiku (utility function, high volume)

## Prompt
```
SYSTEM:
You are a character consistency specialist. Your job is to take a 
stored character profile and adapt it for a specific generation 
context while maintaining recognizability.

You must:
1. Preserve all consistency anchors
2. Adapt flexible elements appropriately
3. Add context-specific details
4. Include strong negative prompts to prevent drift

USER:
STORED CHARACTER PROFILE:
{character_json}

NEW GENERATION CONTEXT:
- Scene/scenario: {description}
- Mood/emotion needed: {emotion}
- Setting: {location/background}
- Clothing context: {if relevant}
- Platform/format: {where this will be used}
- Style: {photo-realistic / illustrated / etc.}

Generate:

1. ADAPTED PROMPT
Full generation prompt that:
- Includes all consistency anchors verbatim
- Adapts flexible elements to context
- Describes the scene/scenario
- Specifies style and mood

2. NEGATIVE PROMPT
Extended negative prompt including:
- Character-specific negatives (what would break likeness)
- Context-specific negatives (what would break the scene)
- Quality negatives (artifacts, errors to avoid)

3. GENERATION PARAMETERS
- Aspect ratio, style strength, CFG/guidance, seed strategy

4. CONSISTENCY CHECKLIST
After generation, verify:
[ ] {anchor 1 present}
[ ] {anchor 2 present}
[ ] {anchor 3 present}
[ ] Expression matches mood
[ ] Context appropriate
[ ] No feature drift

Output as structured JSON with prompt as clean string ready for use.
```

# Database Schema (PostgreSQL)

## Storage Strategy

| Data | Storage | Why |
|------|---------|-----|
| Users, settings | Postgres | Relational, ACID |
| Characters, segments | Postgres JSONB | Structured, exact retrieval |
| Vocabulary, research | Vector + Postgres | Semantic search |
| Content history | Postgres + Vector | Metadata + semantic |

**Key Insight:**
- **Postgres for "what"** - exact lookups, relationships
- **Vector for "like what"** - semantic similarity, fuzzy matching

## Schema - Core Tables
```sql
-- ORGANIZATIONS & USERS
CREATE TABLE organizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    plan_tier VARCHAR(50) DEFAULT 'free',
    settings JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID REFERENCES organizations(id),
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255),
    role VARCHAR(50) DEFAULT 'member',
    preferences JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- WORKSPACES & VOICE
CREATE TABLE workspaces (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID REFERENCES organizations(id),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    brand_guidelines JSONB DEFAULT '{}',
    /*
    {
        "mission": "...",
        "values": ["..."],
        "tone_keywords": ["friendly", "expert"],
        "visual_identity": {
            "primary_colors": ["#hex"],
            "imagery_style": "..."
        },
        "dos_and_donts": {...}
    }
    */
    voice_profile JSONB DEFAULT '{}',
    /*
    {
        "personality_markers": ["..."],
        "sentence_patterns": {...},
        "vocabulary_tendencies": {...},
        "formality_baseline": 0.4,
        "humor_style": "..."
    }
    */
    voice_sample_ids UUID[],
    is_primary BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE voice_samples (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    source VARCHAR(100), -- 'uploaded', 'generated', 'approved_content'
    embedding_id VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

## Schema - Audience Intelligence
```sql
CREATE TABLE audience_segments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    profile JSONB NOT NULL,
    /*
    {
        "demographics": {...},
        "psychographics": {...},
        "language_profile": {
            "formality_level": 0.3,
            "vocabulary_to_use": ["term1", "term2"],
            "vocabulary_to_avoid": ["term1"],
            "sample_sentences": ["..."],
            "reference_pool": ["shows", "memes"]
        },
        "visual_preferences": {...},
        "platform_behaviors": {...},
        "pain_points": [...],
        "messaging_angles": [...]
    }
    */
    confidence_score DECIMAL(3,2),
    source_research_ids UUID[],
    is_primary BOOLEAN DEFAULT FALSE,
    is_validated BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE niche_vocabulary (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE,
    term VARCHAR(255) NOT NULL,
    definition TEXT,
    usage_examples TEXT[],
    sentiment VARCHAR(20), -- positive, negative, neutral
    formality_level DECIMAL(3,2),
    segment_ids UUID[],
    embedding_id VARCHAR(255),
    source VARCHAR(100), -- 'reddit', 'competitor', 'user_added'
    source_url TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(workspace_id, term)
);

-- CHARACTERS
CREATE TABLE characters (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    character_type VARCHAR(50) NOT NULL, -- person, pet, mascot, illustrated
    source_type VARCHAR(50) NOT NULL, -- uploaded, generated, described
    source_image_url TEXT,
    reference_images TEXT[],
    profile JSONB NOT NULL,
    /*
    {
        "core_identifiers": [...],
        "detailed_description": {...},
        "generation_prompts": {
            "concise": "...",
            "detailed": "...",
            "negative": "...",
            "style_variations": {...}
        },
        "consistency_anchors": [...],
        "variation_boundaries": {...},
        "strategic_rationale": {...}
    }
    */
    target_segment_id UUID REFERENCES audience_segments(id),
    is_primary BOOLEAN DEFAULT FALSE,
    usage_count INTEGER DEFAULT 0,
    last_used_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE character_generations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    character_id UUID REFERENCES characters(id) ON DELETE CASCADE,
    prompt_used TEXT NOT NULL,
    context_description TEXT,
    image_url TEXT NOT NULL,
    model_used VARCHAR(100),
    generation_params JSONB,
    seed BIGINT,
    consistency_score DECIMAL(3,2),
    user_approved BOOLEAN,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

## Schema - Research & Content
```sql
-- RESEARCH SOURCES
CREATE TABLE research_sources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE,
    source_type VARCHAR(50) NOT NULL, -- reddit, competitor, youtube
    source_identifier VARCHAR(255) NOT NULL,
    source_url TEXT,
    raw_data JSONB,
    processed_insights JSONB,
    /*
    {
        "vocabulary_extracted": [...],
        "pain_points": [...],
        "content_patterns": [...],
        "audience_signals": [...]
    }
    */
    embedding_ids VARCHAR(255)[],
    collected_at TIMESTAMPTZ DEFAULT NOW(),
    processed_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ,
    UNIQUE(workspace_id, source_type, source_identifier)
);

CREATE TABLE competitor_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE,
    platform VARCHAR(50) NOT NULL,
    handle VARCHAR(255) NOT NULL,
    profile_url TEXT,
    analysis JSONB,
    /*
    {
        "content_pillars": [...],
        "posting_patterns": {...},
        "engagement_metrics": {...},
        "voice_analysis": {...},
        "visual_style": {...},
        "top_performing_content": [...]
    }
    */
    last_analyzed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(workspace_id, platform, handle)
);

-- CALIBRATED VOICES
CREATE TABLE calibrated_voices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE,
    segment_id UUID REFERENCES audience_segments(id) ON DELETE CASCADE,
    platform VARCHAR(50) NOT NULL,
    voice_spec JSONB NOT NULL,
    /*
    {
        "preservation": {...},
        "adaptations": {...},
        "synthesis_rules": {...},
        "examples": [...],
        "anti_patterns": [...]
    }
    */
    usage_count INTEGER DEFAULT 0,
    avg_engagement_score DECIMAL(5,2),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(workspace_id, segment_id, platform)
);

-- GENERATED CONTENT
CREATE TABLE generated_content (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE,
    content_type VARCHAR(50) NOT NULL, -- post, image, video_script
    platform VARCHAR(50) NOT NULL,
    text_content TEXT,
    image_urls TEXT[],
    video_url TEXT,
    calibrated_voice_id UUID REFERENCES calibrated_voices(id),
    character_id UUID REFERENCES characters(id),
    segment_id UUID REFERENCES audience_segments(id),
    generation_prompts JSONB,
    embedding_id VARCHAR(255),
    status VARCHAR(50) DEFAULT 'draft', -- draft, approved, posted, archived
    posted_at TIMESTAMPTZ,
    post_url TEXT,
    engagement_metrics JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- PLATFORM CONNECTIONS
CREATE TABLE platform_connections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE,
    platform VARCHAR(50) NOT NULL,
    account_id VARCHAR(255),
    account_handle VARCHAR(255),
    access_token TEXT,
    refresh_token TEXT,
    token_expires_at TIMESTAMPTZ,
    settings JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT TRUE,
    last_sync_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(workspace_id, platform)
);

CREATE TABLE posting_schedule (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE,
    platform_connection_id UUID REFERENCES platform_connections(id) ON DELETE CASCADE,
    segment_id UUID REFERENCES audience_segments(id),
    schedule_config JSONB NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- INDEXES
CREATE INDEX idx_workspaces_org ON workspaces(organization_id);
CREATE INDEX idx_segments_workspace ON audience_segments(workspace_id);
CREATE INDEX idx_characters_workspace ON characters(workspace_id);
CREATE INDEX idx_content_workspace ON generated_content(workspace_id);
CREATE INDEX idx_calibrated_voices_lookup ON calibrated_voices(workspace_id, segment_id, platform);
CREATE INDEX idx_content_status ON generated_content(workspace_id, status);
CREATE INDEX idx_segment_profile ON audience_segments USING GIN (profile);
CREATE INDEX idx_character_profile ON characters USING GIN (profile);
CREATE INDEX idx_vocab_term ON niche_vocabulary(workspace_id, term);
```

# Vector Store (pgvector)

## Setup
```sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_type VARCHAR(50) NOT NULL, 
    -- 'voice_sample', 'research_chunk', 'vocabulary', 'content', 'brand_guideline'
    source_id UUID NOT NULL,
    workspace_id UUID NOT NULL,
    embedding vector(1536), -- OpenAI ada-002 dimension
    chunk_text TEXT NOT NULL,
    chunk_index INTEGER DEFAULT 0,
    metadata JSONB DEFAULT '{}',
    /*
    {
        "segment_ids": [...],
        "platform": "...",
        "content_type": "...",
        "source_url": "...",
        "collected_at": "..."
    }
    */
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_embeddings_vector ON embeddings 
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

CREATE INDEX idx_embeddings_workspace ON embeddings(workspace_id);
CREATE INDEX idx_embeddings_source ON embeddings(source_type, source_id);
CREATE INDEX idx_embeddings_metadata ON embeddings USING GIN (metadata);
```

## What Gets Embedded

| Content Type | Chunking | Why Embed |
|--------------|----------|-----------|
| Voice samples | Whole doc | Find similar writing |
| Reddit posts | Per post | Find relevant discussions |
| Competitor content | Per post | Find similar themes |
| Vocabulary | Term + definition | Semantic lookup |
| Generated content | Whole post | Find past similar |
| Brand guidelines | By section | Retrieve relevant rules |

## Embedding Pipeline
```python
from openai import OpenAI
import tiktoken

client = OpenAI()
EMBEDDING_MODEL = "text-embedding-3-small"

def chunk_text(text: str, max_tokens: int = 500, overlap: int = 50):
    encoder = tiktoken.encoding_for_model(EMBEDDING_MODEL)
    tokens = encoder.encode(text)
    chunks = []
    start = 0
    while start < len(tokens):
        end = start + max_tokens
        chunks.append(encoder.decode(tokens[start:end]))
        start = end - overlap
    return chunks

def embed_and_store(text, source_type, source_id, workspace_id, metadata=None):
    chunks = chunk_text(text)
    for i, chunk in enumerate(chunks):
        response = client.embeddings.create(model=EMBEDDING_MODEL, input=chunk)
        embedding = response.data[0].embedding
        db.execute("""
            INSERT INTO embeddings 
            (source_type, source_id, workspace_id, embedding, chunk_text, chunk_index, metadata)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (source_type, source_id, workspace_id, embedding, chunk, i, metadata))

def semantic_search(query, workspace_id, source_types=None, segment_ids=None, limit=10):
    response = client.embeddings.create(model=EMBEDDING_MODEL, input=query)
    query_embedding = response.data[0].embedding
    
    filters = ["workspace_id = %s"]
    params = [workspace_id]
    
    if source_types:
        filters.append("source_type = ANY(%s)")
        params.append(source_types)
    
    if segment_ids:
        filters.append("metadata->'segment_ids' ?| %s")
        params.append(segment_ids)
    
    return db.execute(f"""
        SELECT source_type, source_id, chunk_text, metadata,
               1 - (embedding <=> %s) as similarity
        FROM embeddings
        WHERE {' AND '.join(filters)}
        ORDER BY embedding <=> %s
        LIMIT %s
    """, [query_embedding] + params + [query_embedding, limit])
```

# RAG Context Assembly

## Pipeline Overview
```
┌─────────────────────────────────────────────────────────────────┐
│                    CONTEXT ASSEMBLY LAYER                        │
│  Every agent call goes through this to get relevant context      │
└─────────────────────────────────────────────────────────────────┘
                              │
         ┌────────────────────┼────────────────────┐
         │                    │                    │
         ▼                    ▼                    ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│ STRUCTURED      │  │ SEMANTIC        │  │ SESSION         │
│ (Postgres)      │  │ (Vector)        │  │ (Redis)         │
│                 │  │                 │  │                 │
│ - Brand profile │  │ - Vocabulary    │  │ - Current task  │
│ - Voice profile │  │ - Past content  │  │ - User inputs   │
│ - Segments      │  │ - Research      │  │ - Intermediate  │
│ - Characters    │  │ - Guidelines    │  │   results       │
└─────────────────┘  └─────────────────┘  └─────────────────┘
         │                    │                    │
         └────────────────────┼────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    CONTEXT COMPILER                              │
│  - Combines sources into agent-specific prompt                   │
│  - Manages token budget                                          │
│  - Prioritizes by relevance                                      │
└─────────────────────────────────────────────────────────────────┘
```

## Context Assembler
```python
from dataclasses import dataclass
from typing import Optional

@dataclass
class AgentContext:
    workspace: dict
    voice_profile: dict
    audience_segment: Optional[dict]
    character: Optional[dict]
    platform_context: Optional[dict]
    semantic_context: list[dict]
    session_context: dict

class ContextAssembler:
    def __init__(self, db, vector_store):
        self.db = db
        self.vector = vector_store
    
    def assemble_for_content_generation(
        self, workspace_id, segment_id, platform, content_topic, character_id=None
    ):
        # 1. STRUCTURED (Postgres)
        workspace = self.db.get_workspace(workspace_id)
        audience_segment = self.db.get_segment(segment_id)
        character = self.db.get_character(character_id) if character_id else None
        calibrated_voice = self.db.get_calibrated_voice(workspace_id, segment_id, platform)
        
        # 2. SEMANTIC (Vector search)
        semantic_context = []
        
        # Vocabulary
        semantic_context.extend(self.vector.search(
            query=content_topic, workspace_id=workspace_id,
            source_types=['vocabulary'], segment_ids=[segment_id], limit=20
        ))
        
        # Past high-performing content
        semantic_context.extend(self.vector.search(
            query=content_topic, workspace_id=workspace_id,
            source_types=['content'],
            metadata_filter={'engagement_score_gte': 0.7}, limit=5
        ))
        
        # Research
        semantic_context.extend(self.vector.search(
            query=f"{content_topic} {audience_segment['name']}",
            workspace_id=workspace_id, source_types=['research_chunk'], limit=10
        ))
        
        # Guidelines
        semantic_context.extend(self.vector.search(
            query=f"{content_topic} {platform} guidelines",
            workspace_id=workspace_id, source_types=['brand_guideline'], limit=5
        ))
        
        # 3. SESSION
        session_context = {
            'task': 'content_generation',
            'topic': content_topic,
            'platform': platform,
            'calibrated_voice': calibrated_voice
        }
        
        return AgentContext(
            workspace=workspace, voice_profile=workspace.voice_profile,
            audience_segment=audience_segment, character=character,
            platform_context=None, semantic_context=semantic_context,
            session_context=session_context
        )
```

## Token Budget Management
```python
class TokenBudgetManager:
    MODEL_LIMITS = {
        'claude-opus': 200000,
        'claude-sonnet': 200000,
        'gpt-4o': 128000,
        'gpt-4o-mini': 128000,
    }
    
    def __init__(self, model, reserve=4000):
        self.total = self.MODEL_LIMITS.get(model, 100000)
        self.available = self.total - reserve
    
    def get_budget(self, category):
        allocations = {
            'brand_voice': 0.15,
            'calibrated_voice': 0.20,
            'audience_segment': 0.15,
            'character': 0.10,
            'semantic_vocabulary': 0.10,
            'semantic_past_content': 0.10,
            'semantic_research': 0.10,
            'task_instructions': 0.10,
        }
        return int(self.available * allocations.get(category, 0.05))
```

# System Architecture
```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              USER INTERFACE                                  │
│  Dashboard │ Content Studio │ Audience Hub │ Character Manager │ Settings   │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              API GATEWAY                                     │
│  Authentication │ Rate Limiting │ Request Routing │ Response Formatting      │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           ORCHESTRATION LAYER                                │
│  Task Router │ Agent Scheduler │ Result Aggregator                           │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           CONTEXT ASSEMBLY LAYER                             │
│  Structured Retriever (Postgres) │ Semantic Retriever (Vector) │ Session    │
│  Context Compiler (Token budgeting, Priority ranking, Prompt templating)     │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              AGENT LAYER                                     │
│  Research: Niche, Reddit, Competitor │ Audience: Synthesis, Validate         │
│  Voice: Calibrate, Adapt │ Content: Generate, Visual, Video                  │
│  Character: Extract, Generate, Consistency                                   │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              MODEL ROUTER                                    │
│  Claude Opus │ Claude Sonnet │ GPT-4o │ GPT-4o-mini                          │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           GENERATION SERVICES                                │
│  Image: Flux, Midjourney, DALL-E │ Video: Runway, Kling │ Voice: ElevenLabs │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              DATA LAYER                                      │
│  PostgreSQL │ Vector Store (pgvector) │ Redis │ S3 │ CDN                     │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Model Selection Summary

| Agent | Model | Why |
|-------|-------|-----|
| Niche Understanding | Claude Sonnet | Reasoning, broad knowledge |
| Reddit Research | GPT-4o-mini | High volume, extraction |
| Competitor Analysis | Claude Sonnet | Pattern recognition |
| Audience Synthesis | Claude Opus | Critical synthesis, worth premium |
| Voice Calibration | Claude Sonnet | Nuanced language |
| Content Gen (short) | GPT-4o-mini | Fast, concise |
| Content Gen (long) | Claude Sonnet | Maintains voice |
| Visual Direction | Claude Sonnet | Creative direction |
| Character Extract | GPT-4o | Vision + description |
| Consistency Manager | GPT-4o-mini | Utility, high volume |

## Model Router
```python
class ModelRouter:
    RULES = {
        'niche_understanding': {'default': 'claude-sonnet'},
        'reddit_research': {'default': 'gpt-4o-mini'},
        'competitor_analysis': {'default': 'claude-sonnet'},
        'audience_synthesis': {'default': 'claude-opus'},
        'voice_calibration': {'default': 'claude-sonnet'},
        'content_generation': {
            'short_form': 'gpt-4o-mini',
            'long_form': 'claude-sonnet',
            'high_stakes': 'claude-opus'
        },
        'visual_direction': {'default': 'claude-sonnet'},
        'character_extraction': {'default': 'gpt-4o'},
        'character_consistency': {'default': 'gpt-4o-mini'}
    }
    
    def route(self, agent_type, context):
        rules = self.RULES.get(agent_type, {'default': 'claude-sonnet'})
        
        if agent_type == 'content_generation':
            if context.get('content_length', 0) < 280:
                return rules['short_form']
            elif context.get('is_campaign'):
                return rules['high_stakes']
            return rules['long_form']
        
        return rules['default']
```

# Request Flow Examples

## Flow 1: Generate Post with Character
```
User: "Create Instagram post about Base Set restock"
Segment: "Nostalgic Millennials"
Character: "Alex"

STEP 1: TASK ROUTER
→ Needed: Content Gen, Visual Direction, Character Consistency

STEP 2: CONTEXT ASSEMBLY
Postgres:
- Brand, Segment, Character, Calibrated Voice

Vector:
- "Base Set Pokemon restock" → vocabulary (20)
- "Base Set Instagram" → past content (5)
- "Instagram guidelines" → brand rules (3)

STEP 3: CONTEXT COMPILATION
Budget ~3700 tokens:
- Brand + Voice: 500
- Calibrated Voice: 800
- Audience: 600
- Character: 400
- Vocabulary: 300
- Past Content: 400
- Guidelines: 200
- Instructions: 500

STEP 4: PARALLEL AGENT EXECUTION
Content Gen (Claude Sonnet) → Caption + alternatives
Visual Direction (Claude Sonnet) → 3 visual concepts
Character Consistency (GPT-4o-mini) → Adapted prompt

STEP 5: IMAGE GENERATION
Flux Pro → 4 variations

STEP 6: RESULT
→ Store in Postgres + embed caption
→ Return to user: caption + images
```

## Flow 2: New User Onboarding
```
User: "I sell vintage Pokemon cards"
Platforms: X, Threads, Instagram

PHASE 1: NICHE UNDERSTANDING (Claude Sonnet)
→ Taxonomy, 4-5 segment hypotheses, research targets

PHASE 2: PARALLEL RESEARCH (Background)
Reddit Agent ×4 (GPT-4o-mini):
- r/pokemontcg
- r/pkmntcgtrades
- r/pokemoncardcollectors
- r/pokemoninvesting

Competitor Agent (Claude Sonnet):
- Top 5 per platform

PHASE 3: AUDIENCE SYNTHESIS (Claude Opus)
→ Full segment profiles from all research

PHASE 4: USER VALIDATION
→ Present segments, user confirms/edits

PHASE 5: VOICE CALIBRATION
→ 4 segments × 3 platforms = 12 calibrated voices

RESULT: Ready to generate content!
```

## Implementation Checklist

**Phase 1: Foundation**
- [ ] PostgreSQL with full schema
- [ ] pgvector extension
- [ ] Redis for caching
- [ ] Basic API structure

**Phase 2: Agents**
- [ ] Agent 1: Niche Understanding
- [ ] Agent 2: Reddit Research
- [ ] Agent 3: Competitor Analysis
- [ ] Agent 4: Audience Synthesis
- [ ] Agent 5: Voice Calibration
- [ ] Agent 6: Content Generation
- [ ] Agent 7: Visual Direction

**Phase 3: Characters**
- [ ] Agent 8: Character Extraction
- [ ] Agent 9: Pet/Mascot Extraction
- [ ] Agent 10: Character Generation
- [ ] Agent 11: Consistency Manager

**Phase 4: Integration**
- [ ] Context Assembler
- [ ] Context Compiler + token budget
- [ ] Model Router
- [ ] Caching layer
- [ ] Image generation services

**Phase 5: UI**
- [ ] Onboarding flow
- [ ] Content Studio
- [ ] Audience Hub
- [ ] Character Manager
- [ ] Analytics

# Implementation Principles

## Core Principles

1. **Everything is context-aware** - No agent operates in isolation. Every generation has access to all relevant user data.

2. **Voice authenticity is paramount** - User's unique voice must come through. Audience adaptation is a dial, not a replacement.

3. **Consistency matters** - Characters look the same. Voice sounds the same. Brand identity preserved across outputs.

4. **Guide, don't just execute** - Help users make better decisions, not just follow orders.

5. **Scale without degradation** - 1 post or 100, quality and authenticity remain high.

## Questions During Implementation

- "Does this sound like a human wrote it, or like AI?"
- "Would someone in this audience recognize this as speaking to them?"
- "Is the character visually consistent?"
- "Does the user have enough context?"
- "Is the system helping the user succeed?"

## Cost Optimization

- Cache audience profiles aggressively (don't change often)
- Use cheaper models for high-volume tasks
- Invest in Opus for one-time research/synthesis
- Consider fine-tuning smaller models over time

## What Already Exists
- Basic voice synthesis
- Platform connections
- Basic image generation
- User accounts

## What Needs Building
- All 11 agents with prompts
- Full database schema
- Vector store + embeddings
- Context assembly layer
- RAG system
- Model routing
- Caching strategy
- Job queues for async research

---

# Plan Revisions (Post-Audit)

## Agent Consolidation: 11 → ~8 Agents

Based on the audit, the original 11 agents have been consolidated:

| Original | Status | Reason |
|----------|--------|--------|
| Agent 1: Niche Understanding | **EXPANDED** | Now includes audience profile generation |
| Agent 2: Reddit Research | **DELETED** | LLM generates vocabulary/pain points from training data instead of scraping |
| Agent 3: Competitor Analysis | **SIMPLIFIED** | Renamed to "Niche Patterns Agent" - LLM generates patterns, no live scraping |
| Agent 4: Audience Synthesis | **MERGED with Agent 1** | No research to synthesize - LLM generation + user input |
| Agent 5: Voice Calibration | Unchanged | |
| Agent 6: Content Generation | Unchanged | |
| Agent 7: Visual Direction | Unchanged | |
| Agents 8-11: Character System | Unchanged | |

### Rationale

**No external data collection.** The original plan called for:
- Reddit API scraping
- Competitor social media analysis
- SimilarWeb-style data

**Risks identified:**
- ToS violations (Reddit, social platforms)
- API costs for SimilarWeb
- Legal/compliance complexity
- Data freshness management

**New approach:** LLM generates audience categories based on:
1. User's business description
2. LLM training knowledge about the niche
3. Optional user-provided examples

### Benefits
- Zero compliance risk
- Zero API costs for data collection
- Simpler architecture
- Faster implementation

### Trade-offs
- Less real-time data
- May miss slang that emerged after training cutoff
- Users may need to provide more context

## Character/Likeness Consent

**Decision:** User attestation checkbox before upload.

**Implementation:**
- Checkbox: "I confirm I have the rights to use this image"
- Must be checked before upload proceeds
- Store attestation timestamp in database
- Shifts liability to user (documented in ToS)

## Data Collection Strategy

**Original approach (removed):**
```python
# DELETED - No longer collecting external data
def collect_subreddit_data(subreddit_name, timeframe="year"):
    ...
```

**New approach:**
```python
# LLM generates audience insights from training data
def generate_audience_insights(business_description, niche):
    prompt = f"""
    Based on your knowledge of {niche}, generate:
    1. Common vocabulary and slang used
    2. Pain points customers experience
    3. Content preferences
    4. Community norms

    Business context: {business_description}
    """
    return llm.generate(prompt)
```

## Revised Agent Structure

| # | Agent | Purpose | Model |
|---|-------|---------|-------|
| 1 | Niche + Audience | Generate segments from business description | Claude Sonnet |
| 2 | Voice Calibration | Fuse user voice with audience profile | Claude Sonnet |
| 3 | Content Generation | Generate content with calibrated voice | Claude Sonnet/GPT-4o-mini |
| 4 | Visual Direction | Generate image prompts | Claude Sonnet |
| 5 | Character Extraction | Extract character from uploaded image | GPT-4o (vision) |
| 6 | Pet/Mascot Extraction | Same for non-human characters | GPT-4o (vision) |
| 7 | Character Generation | Create new characters for segments | Claude Sonnet |
| 8 | Character Consistency | Adapt character for new contexts | GPT-4o-mini |

---

# Implementation Progress

## Executive Summary

### What Was Done ✅

| Category | Implementation |
|----------|----------------|
| **Database** | PostgreSQL is now the only backend. Removed USE_SQLMODEL flag. Added pgvector extension for vector search. Created Alembic migration for 7 new tables. |
| **Infrastructure** | Added Redis service. Updated Postgres to pgvector image. Added new Python dependencies. |
| **Safety/Moderation** | Created `runner/moderation/` module with policy checks (spam + prompt injection, optional OpenAI moderation), plagiarism detection (n-gram similarity), and brand safety checks. |
| **Error Handling** | Created `runner/resilience/` module with retry policies (exponential backoff), model fallback chains (Opus→Sonnet→GPT-4o), rate limiting (token bucket), and budget enforcement ($5/day default). |
| **Observability** | Created `runner/observability/` module with structured logging (structlog), latency tracking (p50/p95/p99), cost tracking per model, and quality drift detection. |
| **History Tracking** | HistoryService + SQLModel queries/eval in use; legacy HistoryDatabase removed. |
| **Legacy SQLite Removal** | Removed ContentDatabase/HistoryDatabase and migrated callers to SQLModel services. |
| **Plan Updates** | Documented agent consolidation (11→8), removed Reddit scraping approach, added character consent strategy. |

### What Was NOT Done ❌

| Task | Reason | Impact |
|------|--------|--------|
| **Implement the 8 agents** | Infrastructure-only phase; agents are next phase | No new agent code written |
| **Build Context Assembler / RAG** | Depends on agents being implemented | No RAG pipeline yet |
| **Build UI components** | Backend-first approach | No frontend changes |

### Migration Status

```
PostgreSQL Migration Progress:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Users, Platforms, Goals      ████████████ 100% (via SQLModel)
Chapters, Posts              ████████████ 100% (via SQLModel)
Voice Profiles (new schema)  ████████████ 100% (via SQLModel)
Voice Profiles (legacy)      ████████████ 100% (legacy fields stored in SQLModel JSON)
History Tracking             ████████████ 100% (queries/eval on SQLModel)
Content Database             ████████████ 100% (legacy module removed)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### Audit Corrections / Gaps Found (Status)

1. ✅ **Schema mismatch:** `runner/db/models/market_intelligence.py` now aligns with `runner/db/migrations/versions/20260116_phase13_market_intelligence.py` using SQLite-safe custom types.
2. ✅ **Vector storage mismatch:** added migration to upgrade embeddings to `vector(1536)` + ivfflat index.
3. ✅ **Docker/API deps gap:** `requirements-api.txt` now includes `pgvector`, `redis`, `tiktoken`, `structlog`.
4. ✅ **Legacy persistence removed:** runner/state_machine now uses SQLModel services, eval queries use SQLModel, legacy SQLite history/content modules deleted.
5. ✅ **Doc drift:** "Files Modified" now references `tests/unit/test_health.py`.
6. ✅ **Resilience edge cases:** fixed rate limiter acquire API and fallback degraded flag.

### Gap Closure Checklist (Post-Audit)

- [x] Align market intelligence SQLModel models with the Alembic schema (SQLite-safe types).
- [x] Upgrade embeddings to `vector(1536)` + ivfflat index as defined in the plan.
- [x] Add missing API/runtime deps to `requirements-api.txt` for Docker builds.
- [x] Migrate runner and state_machine off `ContentDatabase` (use SQLModel services).
- [x] Swap history queries/eval to SQLModel and delete legacy SQLite history code.
- [x] Fix resilience module edge cases (rate limiter acquire API, fallback degraded flag) and add tests.
- [x] Update plan schema snippets to use `workspace_id` consistently (replace legacy `brand_id` references).

---

## Phase 13: Market Upgrade Infrastructure (January 2026)

### ✅ Completed

| Task | Files | Notes |
|------|-------|-------|
| **pgvector support** | `docker-compose.yml` | Changed postgres image to `pgvector/pgvector:pg16` |
| **Redis service** | `docker-compose.yml` | Added Redis 7 with persistence |
| **New dependencies** | `pyproject.toml`, `requirements-api.txt` | Added `pgvector>=0.3.0`, `redis>=5.0.0`, `tiktoken>=0.7.0`, `structlog>=24.0.0` |
| **Market intelligence models** | `runner/db/models/market_intelligence.py` | SQLModel tables aligned to migration via SQLite-safe types |
| **Alembic migration** | `runner/db/migrations/versions/20260116_phase13_market_intelligence.py` | Creates pgvector extension and all new tables |
| **Embeddings vector upgrade** | `runner/db/migrations/versions/20260116_phase13_embeddings_vector.py` | Converts embeddings to `vector(1536)` and adds ivfflat index |
| **Remove USE_SQLMODEL flag** | `runner/config.py`, `runner/db/engine.py`, tests, scripts | PostgreSQL is now always used (no conditional logic) |
| **Content moderation module** | `runner/moderation/` | PolicyChecker (regex patterns + OpenAI API), SimilarityChecker (n-gram + semantic), ContentModerator orchestrator |
| **Resilience module** | `runner/resilience/` | RetryPolicy with exponential backoff, FallbackChain for model failover, TokenBucketRateLimiter, BudgetEnforcer for cost limits |
| **Observability module** | `runner/observability/` | AgentTracer (structured logging with structlog), MetricsCollector (latency percentiles p50/p95/p99, cost tracking), QualityMonitor (voice drift detection) |
| **History repositories** | `runner/content/repository.py` | RunRecordRepository, InvocationRecordRepository, AuditScoreRecordRepository, PostIterationRecordRepository |
| **HistoryService** | `runner/history/service.py` | SQLModel-based drop-in replacement for legacy HistoryDatabase |

### 🔶 Deferred (Large Refactors)

See "What Was NOT Done" for remaining roadmap items (agents, context assembly, UI).

### 📋 New Files Created

```
runner/moderation/
├── __init__.py
├── moderator.py        # ContentModerator class
├── policies.py         # PolicyChecker, PolicyResult
└── similarity.py       # SimilarityChecker, SimilarityResult

runner/resilience/
├── __init__.py
├── retry.py            # RetryPolicy, @with_retry decorator
├── fallback.py         # FallbackChain, ModelProvider
├── rate_limit.py       # TokenBucketRateLimiter
└── budget.py           # BudgetEnforcer, BudgetConfig

runner/observability/
├── __init__.py
├── tracer.py           # AgentTracer, Span, SpanContext
├── metrics.py          # MetricsCollector, MetricsSummary
└── quality.py          # QualityMonitor, QualityScore, DriftAlert

runner/history/
└── service.py          # HistoryService (new SQLModel-based)

runner/db/models/
└── market_intelligence.py  # All new market upgrade SQLModel tables

runner/db/migrations/versions/
└── 20260116_phase13_market_intelligence.py  # Alembic migration
└── 20260116_phase13_embeddings_vector.py  # Embeddings vector/index upgrade

runner/db/
└── types.py  # JSON/ARRAY/VECTOR dialect fallbacks
```

### 📋 Files Modified

```
docker-compose.yml          # pgvector image, Redis service
pyproject.toml              # New dependencies
runner/config.py            # Removed USE_SQLMODEL, added REDIS_URL
runner/db/engine.py         # Removed USE_SQLMODEL checks
runner/content/repository.py # Added history repositories
runner/history/__init__.py   # Export HistoryService
scripts/seed_test_users.py   # Removed USE_SQLMODEL
scripts/seed_voice_profiles.py # Removed USE_SQLMODEL
tests/integration/test_portal.py # Removed USE_SQLMODEL
tests/unit/test_health.py    # Removed USE_SQLMODEL
runner/db/models/market_intelligence.py # Align schema with migration
runner/resilience/rate_limit.py # Fix acquire API
runner/resilience/fallback.py # Fix degraded flag
requirements-api.txt # Add runtime deps for Docker
tests/unit/test_resilience.py # New tests for resilience fixes
```

### 🔧 Configuration Changes

**Database:**
- PostgreSQL is now the only database backend (no more SQLite option)
- pgvector extension enabled for vector similarity search
- Connection pooling via PgBouncer (already configured)

**Environment Variables:**
```bash
DATABASE_URL=postgresql://orchestrator:orchestrator_dev@localhost:6432/orchestrator
REDIS_URL=redis://localhost:6379/0
```

**Removed:**
- `USE_SQLMODEL` environment variable and flag
- `DATABASE_PATH` (deprecated, kept for backward compatibility warning)

### 🏗️ Architecture Notes

**Model Fallback Chain (from resilience/fallback.py):**
```
Claude Opus → Claude Sonnet → GPT-4o → GPT-4o-mini
```

**Budget Enforcement (from resilience/budget.py):**
- Default: $5/day, $50/month, $1/request
- Configurable via BudgetConfig
- Warning at 80% threshold

**Content Moderation Pipeline (from moderation/moderator.py):**
1. Policy checks (spam + prompt injection locally, optional OpenAI moderation)
2. Plagiarism check (n-gram similarity against sources)
3. Brand safety check (guideline keyword matching)

**Observability (from observability/):**
- Structured logging via structlog (JSON output)
- Per-model cost calculation using MODEL_PRICING dict
- Latency percentiles: p50, p95, p99
- Quality drift detection (baseline comparison)

### ⚠️ Migration Notes

**For developers:**
1. Run `alembic upgrade head` to create new tables
2. Start PostgreSQL with pgvector: `docker-compose up postgres`
3. Start Redis: `docker-compose up redis`
4. Legacy SQLite files still exist but are deprecated

**Breaking changes:**
- `USE_SQLMODEL` no longer supported - always uses PostgreSQL
- Legacy routes (`/voice/*`) still use SQLite until migrated
