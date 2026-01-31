"""Service for LLM-guided onboarding flow."""

import json
import os
from typing import Optional, Union
from uuid import UUID
from pydantic import BaseModel, Field

from api.services.config_service import ConfigService
from api.services.content_service import ContentService
from runner.agents import create_agent
from runner.content.models import CONTENT_STYLES


# =============================================================================
# Request/Response Models
# =============================================================================


class QuickOnboardingAnswers(BaseModel):
    """User answers from quick onboarding mode."""

    professional_role: str
    known_for: str
    target_audience: str
    content_style: str  # "narrative", "teaching", "informational", "mixed"
    posts_per_week: int = Field(ge=1, le=7)


class GeneratedPlan(BaseModel):
    """LLM-generated content plan."""

    signature_thesis: str
    chapters: list[dict]  # [{chapter_number, title, theme, description, posts: [...]}]


class DeepModeMessage(BaseModel):
    """A message in the deep discovery conversation."""

    role: str  # "user" or "assistant"
    content: str


class DeepModeState(BaseModel):
    """State for deep discovery conversation."""

    messages: list[DeepModeMessage] = Field(default_factory=list)
    turn_count: int = 0
    ready_to_generate: bool = False


# =============================================================================
# LLM Prompts
# =============================================================================


QUICK_MODE_SYSTEM_PROMPT = """You are a content strategist helping professionals build thought leadership.

Based on the user's answers, generate a personalized content strategy with:
1. A signature thesis (1-2 sentences that capture their unique perspective)
2. 4-6 content chapters, each with:
   - A clear title
   - A theme (for teaching style: an "enemy" to fight; for others: a topic/angle)
   - A description of what this chapter covers
   - 4-6 posts with topics and suggested shapes

Content styles and their chapter framing:
- "narrative": Story-driven, personal experiences. Chapters have themes (not enemies).
- "teaching": Lesson-based, contrarian takes. Chapters have enemies to fight.
- "informational": How-to, educational. Chapters have topics to cover.
- "mixed": Combination based on topic. Chapters have flexible framing.

Post shapes to distribute across chapters:
- FULL: Complete arc with resolution
- PARTIAL: Unresolved, ends messy
- OBSERVATION: Noticing, no lesson
- SHORT: Under 200 words
- REVERSAL: Updates previous stance

Output ONLY valid JSON matching this structure:
{
  "signature_thesis": "Their unique perspective in 1-2 sentences",
  "chapters": [
    {
      "chapter_number": 1,
      "title": "Chapter Title",
      "theme": "Enemy or theme name",
      "theme_description": "What this theme means",
      "posts": [
        {"post_number": 1, "topic": "Post topic", "shape": "FULL", "cadence": "Teaching"},
        {"post_number": 2, "topic": "Post topic", "shape": "OBSERVATION", "cadence": "Field Note"}
      ]
    }
  ]
}

IMPORTANT:
- Make the thesis specific to their expertise, not generic
- Vary post shapes - not all FULL posts
- Alternate Teaching and Field Note cadence
- Total posts should be approximately 40-50 across all chapters
"""


DEEP_MODE_SYSTEM_PROMPT = """You are a content strategist having a discovery conversation to help someone build thought leadership.

Your goal: understand what makes this person's perspective unique and valuable.

Ask open-ended questions about:
- Their work and areas of expertise
- Problems they've solved that others struggle with
- Contrarian views they hold about their industry
- What frustrates them about common practices
- What they wish more people understood
- Moments that shaped their thinking

Conversation guidelines:
- Ask ONE question at a time
- Build on what they share - show genuine curiosity
- Reflect back insights you notice
- Don't be generic - make questions specific to their domain
- After 8-12 exchanges, offer to synthesize their thesis

When you've gathered enough information (usually 8-12 exchanges), say:
"I think I have a good sense of your perspective now. Would you like me to synthesize this into a content strategy?"

If they agree, end your message with: [READY_TO_GENERATE]

Be conversational, not clinical. This should feel like a productive coffee chat, not an interview.
"""


SYNTHESIS_PROMPT = """Based on our conversation, generate a content strategy for this person.

Here's what we discussed:
{conversation}

Generate a personalized content strategy with:
1. A signature thesis (1-2 sentences that capture their unique perspective)
2. 4-6 content chapters based on the themes that emerged
3. 4-6 posts per chapter with specific topics

The content style should be: {content_style}

Output ONLY valid JSON matching this structure:
{
  "signature_thesis": "Their unique perspective in 1-2 sentences",
  "chapters": [
    {
      "chapter_number": 1,
      "title": "Chapter Title",
      "theme": "Theme name",
      "theme_description": "What this theme means",
      "posts": [
        {"post_number": 1, "topic": "Post topic", "shape": "FULL", "cadence": "Teaching"},
        {"post_number": 2, "topic": "Post topic", "shape": "OBSERVATION", "cadence": "Field Note"}
      ]
    }
  ]
}
"""


STRATEGY_PLAN_PROMPT = """You are generating a content plan from a strategy summary.

Strategy summary (JSON):
{strategy_json}

Generate a personalized content strategy with:
1. A signature thesis (1-2 sentences)
2. 4-8 content chapters based on the summary themes
3. Posts per chapter that align to cadence and series length

Guidelines:
- If chapter_themes are provided, use them as chapter titles/themes.
- If intellectual_enemies are provided and content_style is "teaching", use them as themes.
- If posts_per_week and series_length_weeks are provided, target
  posts_per_week * series_length_weeks total posts.
- Distribute posts evenly across chapters (6-8 weeks per chapter is a good default).
- Vary post shapes and alternate Teaching and Field Note cadence.
- Keep the thesis aligned to the positioning and target audience.

Output ONLY valid JSON matching this structure:
{
  "signature_thesis": "Their unique perspective in 1-2 sentences",
  "chapters": [
    {
      "chapter_number": 1,
      "title": "Chapter Title",
      "theme": "Enemy or theme name",
      "theme_description": "What this theme means",
      "posts": [
        {"post_number": 1, "topic": "Post topic", "shape": "FULL", "cadence": "Teaching"},
        {"post_number": 2, "topic": "Post topic", "shape": "OBSERVATION", "cadence": "Field Note"}
      ]
    }
  ]
}
"""


# =============================================================================
# Service Implementation
# =============================================================================


class OnboardingService:
    """Service for LLM-guided onboarding flow."""

    def __init__(self, content_service: Optional[ContentService] = None):
        self.content_service = content_service or ContentService()
        config = ConfigService().get_config()
        default_agent = (
            config.get("orchestrator", {}).get("agent")
            or os.environ.get("ONBOARDING_AGENT")
            or "claude"
        )
        self.agent_type = os.environ.get("ONBOARDING_AGENT", default_agent)
        agent_config = dict(config.get("agents", {}).get(self.agent_type, {}))
        override_model = os.environ.get("ONBOARDING_MODEL")
        if override_model:
            agent_config["model"] = override_model
        self.timeout = int(os.environ.get("ONBOARDING_TIMEOUT", "120"))
        agent_config.setdefault("timeout", self.timeout)
        self.agent_config = agent_config

    def _call_llm(
        self,
        messages: list[dict],
        system_prompt: Optional[str] = None,
    ) -> str:
        """Call configured workflow agent with messages."""
        prompt_sections = []
        if system_prompt:
            prompt_sections.append(system_prompt.strip())

        if messages:
            conversation = "\n".join(
                f"{msg['role'].upper()}: {msg['content']}" for msg in messages
            )
            prompt_sections.append(f"CONVERSATION:\n{conversation}")

        prompt_sections.append("Respond as the assistant.")
        prompt = "\n\n".join(prompt_sections)

        agent = create_agent(self.agent_type, self.agent_config)
        result = agent.invoke(prompt)
        if not result.success:
            raise RuntimeError(f"LLM request failed: {result.error or 'unknown error'}")
        return result.content.strip()

    def _build_fallback_plan(
        self,
        base_topic: str,
        content_style: str,
        target_audience: Optional[str] = None,
    ) -> GeneratedPlan:
        base = " ".join(base_topic.split()).strip() or "your work"
        if len(base) > 80:
            base = base[:80].rsplit(" ", 1)[0] or base[:80]
        audience = f" for {target_audience}" if target_audience else ""
        signature_thesis = (
            f"I share practical, experience-backed insights on {base}{audience}."
        )

        if content_style == "teaching":
            themes = [
                "Enemy: cargo-culting",
                "Enemy: over-engineering",
                "Enemy: shiny tools over fundamentals",
                "Enemy: optimizing too early",
            ]
        elif content_style == "narrative":
            themes = [
                "Turning points",
                "Lessons from hard moments",
                "Unexpected wins",
                "Behind-the-scenes decisions",
            ]
        elif content_style == "informational":
            themes = [
                "Core fundamentals",
                "Common pitfalls",
                "Practical frameworks",
                "Execution playbook",
            ]
        else:
            themes = [
                "Core beliefs",
                "Lessons learned",
                "Frameworks and tools",
                "Execution playbook",
            ]

        chapter_titles = [
            "Foundations",
            "Lessons Learned",
            "Frameworks",
            "Execution",
        ]
        chapter_descriptions = [
            f"First principles and key tradeoffs in {base}.",
            f"Hard-won lessons from doing {base} in real settings.",
            f"Repeatable frameworks that make {base} easier to execute.",
            f"Habits and tactics that move {base} forward consistently.",
        ]
        shapes = ["FULL", "OBSERVATION", "SHORT", "PARTIAL", "REVERSAL"]
        cadences = ["Teaching", "Field Note"]

        chapters: list[dict] = []
        for index, title in enumerate(chapter_titles):
            posts = []
            for post_index in range(4):
                topic = [
                    f"{title}: what most people miss about {base}",
                    f"{title}: a simple checklist for {base}",
                    f"{title}: a field note from recent work",
                    f"{title}: the tradeoff I manage in {base}",
                ][post_index]
                posts.append(
                    {
                        "post_number": post_index + 1,
                        "topic": topic,
                        "shape": shapes[(index + post_index) % len(shapes)],
                        "cadence": cadences[(index + post_index) % len(cadences)],
                    }
                )
            chapters.append(
                {
                    "chapter_number": index + 1,
                    "title": title,
                    "theme": themes[index],
                    "theme_description": chapter_descriptions[index],
                    "posts": posts,
                }
            )

        return GeneratedPlan(signature_thesis=signature_thesis, chapters=chapters)

    def _parse_json_response(self, response: str) -> dict:
        """Extract JSON from LLM response."""
        # Try to find JSON in the response
        try:
            # First try direct parse
            return json.loads(response)
        except json.JSONDecodeError:
            pass

        # Try to find JSON block
        import re

        json_match = re.search(r"\{[\s\S]*\}", response)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass

        raise ValueError(f"Could not parse JSON from response: {response[:200]}...")

    # =========================================================================
    # Quick Mode
    # =========================================================================

    def generate_quick_plan(self, answers: QuickOnboardingAnswers) -> GeneratedPlan:
        """Generate content plan from quick mode answers."""
        user_input = f"""
Professional Role: {answers.professional_role}
What they want to be known for: {answers.known_for}
Target Audience: {answers.target_audience}
Preferred Content Style: {answers.content_style}
Posts per Week: {answers.posts_per_week}
"""
        messages = [{"role": "user", "content": user_input}]
        try:
            response = self._call_llm(messages, system_prompt=QUICK_MODE_SYSTEM_PROMPT)
            data = self._parse_json_response(response)
            return GeneratedPlan(**data)
        except Exception:
            base_topic = answers.known_for or answers.professional_role
            return self._build_fallback_plan(
                base_topic=base_topic,
                content_style=answers.content_style,
                target_audience=answers.target_audience,
            )

    # =========================================================================
    # Deep Mode
    # =========================================================================

    def start_deep_discovery(self) -> DeepModeState:
        """Start a new deep discovery conversation."""
        # Get initial message from LLM
        initial_prompt = "Start a discovery conversation with a professional who wants to build thought leadership through content. Ask your first question."
        messages = [{"role": "user", "content": initial_prompt}]
        try:
            response = self._call_llm(messages, system_prompt=DEEP_MODE_SYSTEM_PROMPT)
        except Exception:
            response = (
                "Let's start with the basics. What do you do professionally, and "
                "what do you want to be known for?"
            )

        return DeepModeState(
            messages=[DeepModeMessage(role="assistant", content=response)],
            turn_count=1,
            ready_to_generate=False,
        )

    def continue_deep_discovery(
        self,
        state: DeepModeState,
        user_message: str,
        force_ready: bool = False,
    ) -> DeepModeState:
        """Continue deep discovery conversation.

        Args:
            state: Current conversation state
            user_message: User's message
            force_ready: If True, mark as ready to generate (user triggered)
        """
        # Add user message
        new_messages = state.messages + [
            DeepModeMessage(role="user", content=user_message)
        ]
        new_turn_count = state.turn_count + 1

        # If user forces ready, skip LLM call and return ready state
        if force_ready:
            return DeepModeState(
                messages=new_messages,
                turn_count=new_turn_count,
                ready_to_generate=True,
            )

        # Build messages for LLM
        llm_messages = [
            {"role": msg.role, "content": msg.content} for msg in new_messages
        ]

        # Get LLM response
        try:
            response = self._call_llm(
                llm_messages, system_prompt=DEEP_MODE_SYSTEM_PROMPT
            )
        except Exception:
            response = (
                "Thanks, that helps. Would you like me to synthesize this into a "
                "content strategy?"
            )

        # Check if ready to generate - LLM marker or turn count fallback
        ready_to_generate = "[READY_TO_GENERATE]" in response
        if ready_to_generate:
            response = response.replace("[READY_TO_GENERATE]", "").strip()

        # Fallback: after 4+ turns, automatically suggest generation
        if not ready_to_generate and new_turn_count >= 4:
            ready_to_generate = True

        # Add assistant message
        new_messages.append(DeepModeMessage(role="assistant", content=response))

        return DeepModeState(
            messages=new_messages,
            turn_count=new_turn_count,
            ready_to_generate=ready_to_generate,
        )

    def generate_deep_plan(
        self,
        state: DeepModeState,
        content_style: str = "mixed",
    ) -> GeneratedPlan:
        """Generate plan from deep discovery conversation."""
        # Format conversation
        conversation = "\n".join(
            [f"{msg.role.upper()}: {msg.content}" for msg in state.messages]
        )

        prompt = SYNTHESIS_PROMPT.format(
            conversation=conversation,
            content_style=content_style,
        )
        messages = [{"role": "user", "content": prompt}]
        try:
            response = self._call_llm(messages)
            data = self._parse_json_response(response)
            return GeneratedPlan(**data)
        except Exception:
            last_user_message = next(
                (msg.content for msg in reversed(state.messages) if msg.role == "user"),
                "",
            )
            return self._build_fallback_plan(
                base_topic=last_user_message or "your work",
                content_style=content_style,
            )

    def generate_plan_from_strategy(self, strategy: dict) -> GeneratedPlan:
        """Generate plan from a structured strategy summary."""
        try:
            strategy_json = json.dumps(strategy, indent=2)
            prompt = STRATEGY_PLAN_PROMPT.format(strategy_json=strategy_json)
            messages = [{"role": "user", "content": prompt}]
            response = self._call_llm(messages)
            data = self._parse_json_response(response)
            return GeneratedPlan(**data)
        except Exception:
            base_topic = (
                strategy.get("positioning")
                or strategy.get("signature_thesis")
                or "your work"
            )
            content_style = strategy.get("content_style", "mixed")
            target_audience = strategy.get("target_audience")
            return self._build_fallback_plan(
                base_topic=base_topic,
                content_style=content_style,
                target_audience=target_audience,
            )

    # =========================================================================
    # Save Plan to Database
    # =========================================================================

    def save_plan(
        self,
        user_id: Union[str, UUID],
        plan: GeneratedPlan,
        positioning: str,
        target_audience: str,
        content_style: str,
        onboarding_mode: str,
        onboarding_transcript: Optional[str] = None,
        workspace_id: Optional[Union[str, UUID]] = None,
    ) -> int:
        """Save generated plan to database.

        Returns:
            Goal ID
        """
        # Save goal
        goal_id = self.content_service.save_goal(
            user_id=user_id,
            positioning=positioning,
            signature_thesis=plan.signature_thesis,
            target_audience=target_audience,
            content_style=content_style,
            onboarding_mode=onboarding_mode,
            onboarding_transcript=onboarding_transcript,
            workspace_id=workspace_id,
        )

        # Save chapters and posts
        post_number = 1
        for chapter_data in plan.chapters:
            chapter_id = self.content_service.save_chapter(
                user_id=user_id,
                chapter_number=chapter_data["chapter_number"],
                title=chapter_data["title"],
                description=chapter_data.get("theme_description"),
                theme=chapter_data.get("theme"),
                theme_description=chapter_data.get("theme_description"),
                workspace_id=workspace_id,
            )

            for post_data in chapter_data.get("posts", []):
                self.content_service.save_post(
                    user_id=user_id,
                    chapter_id=chapter_id,
                    post_number=post_number,
                    topic=post_data.get("topic"),
                    shape=post_data.get("shape"),
                    cadence=post_data.get("cadence"),
                    status="not_started",
                    workspace_id=workspace_id,
                )
                post_number += 1

        return goal_id

    # =========================================================================
    # Quick Mode Questions
    # =========================================================================

    @staticmethod
    def get_quick_mode_questions() -> list[dict]:
        """Get the questions for quick onboarding mode."""
        return [
            {
                "id": "professional_role",
                "question": "What's your professional role?",
                "placeholder": "e.g., Senior Software Engineer, Product Manager, Engineering Director",
                "type": "text",
            },
            {
                "id": "known_for",
                "question": "What do you want to be known for?",
                "placeholder": "e.g., AI systems architecture, Developer productivity, Technical leadership",
                "type": "text",
            },
            {
                "id": "target_audience",
                "question": "Who is your target audience?",
                "placeholder": "e.g., Engineering leaders, Senior developers, Tech founders",
                "type": "text",
            },
            {
                "id": "content_style",
                "question": "What style of content resonates with you?",
                "type": "select",
                "options": CONTENT_STYLES,
            },
            {
                "id": "posts_per_week",
                "question": "How many posts per week can you commit to?",
                "type": "select",
                "options": [
                    {
                        "id": "1",
                        "name": "1 post",
                        "description": "Sustainable, low pressure",
                    },
                    {"id": "2", "name": "2 posts", "description": "Good momentum"},
                    {"id": "3", "name": "3 posts", "description": "Active presence"},
                ],
            },
        ]
