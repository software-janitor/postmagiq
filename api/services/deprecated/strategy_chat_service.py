"""Service for AI-guided strategy creation through conversation."""

import json
import os
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field

from api.services.config_service import ConfigService
from runner.agents import create_agent


class StrategyMessage(BaseModel):
    """A message in the strategy conversation."""
    role: str  # 'user' or 'assistant'
    content: str


class ExtractedStrategyInfo(BaseModel):
    """Information extracted from the conversation."""
    strategy_type: Optional[str] = None  # series, daily, campaign
    positioning: Optional[str] = None
    signature_thesis: Optional[str] = None
    target_audience: Optional[str] = None
    target_roles: list[str] = Field(default_factory=list)
    content_style: Optional[str] = None
    post_frequency: Optional[str] = None
    posts_per_week: Optional[int] = None
    post_length: Optional[str] = None
    voice_constraints: Optional[str] = None
    series_length_weeks: Optional[int] = None
    intellectual_enemies: list[str] = Field(default_factory=list)
    platforms: list[str] = Field(default_factory=list)
    chapter_themes: list[str] = Field(default_factory=list)


class StrategyConversation(BaseModel):
    """Track AI strategy conversation state."""
    messages: list[StrategyMessage] = Field(default_factory=list)
    extracted_info: ExtractedStrategyInfo = Field(default_factory=ExtractedStrategyInfo)
    ready_to_create: bool = False
    turn_count: int = 0


STRATEGY_SYSTEM_PROMPT = """You are a content strategy consultant helping someone create a LinkedIn content strategy.

Your job is to have a natural conversation to understand:
1. What platforms they want to post on (LinkedIn, Threads, X, etc.)
2. What their professional positioning is (how they want to be seen)
3. Who their target audience is
4. What style of content they want (teaching, storytelling, informational, etc.)
5. How often they want to post (daily, weekly, etc.)
6. Whether they want a series with chapters or daily standalone posts

Guidelines:
- Be conversational and warm, not formal
- Ask one or two questions at a time, not a long list
- Pick up on what they share and ask follow-up questions
- After 3-4 exchanges, you should have enough to suggest a strategy
- When you have enough info, summarize what you've learned and propose a strategy

When proposing a strategy, format it clearly with:
- Strategy Type: (series/daily/campaign)
- Positioning: (how they'll be seen)
- Core Thesis: (their main message)
- Target Audience: (who they're writing for)
- Content Style: (how they'll write)

End your strategy proposal with: "Does this capture what you're going for? I can adjust any part of it."

IMPORTANT: Keep responses concise (2-3 paragraphs max). Don't overwhelm with questions."""


class StrategyChatService:
    """Service for AI-guided strategy creation."""

    def __init__(self, agent_type: Optional[str] = None):
        config = ConfigService().get_config()
        default_agent = (
            config.get("orchestrator", {}).get("agent")
            or os.environ.get("STRATEGY_CHAT_AGENT")
            or "claude"
        )
        self.agent_type = agent_type or os.environ.get("STRATEGY_CHAT_AGENT", default_agent)
        agent_config = dict(config.get("agents", {}).get(self.agent_type, {}))
        timeout = int(os.environ.get("STRATEGY_CHAT_TIMEOUT", "120"))
        agent_config.setdefault("timeout", timeout)
        self.agent_config = agent_config
        prompt_path = Path(
            os.environ.get(
                "STRATEGY_CHAT_PROMPT",
                "prompts/strategy_onboarding_persona.md",
            )
        )
        if prompt_path.exists():
            self.system_prompt = prompt_path.read_text().strip()
        else:
            self.system_prompt = STRATEGY_SYSTEM_PROMPT

    def start_conversation(self) -> StrategyConversation:
        """Start a new strategy conversation."""
        state = StrategyConversation()

        opening = """Hi! I'm here to help you create a content strategy.

Let's start simple: What do you do professionally, and what would you like to be known for in your industry?"""

        state.messages.append(StrategyMessage(role="assistant", content=opening))
        return state

    def continue_conversation(
        self,
        state: StrategyConversation,
        user_message: str,
    ) -> StrategyConversation:
        """Continue the conversation with a user message."""
        # Add user message
        state.messages.append(StrategyMessage(role="user", content=user_message))
        state.turn_count += 1

        # Build conversation history for the AI
        conversation_history = "\n\n".join([
            f"{msg.role.upper()}: {msg.content}"
            for msg in state.messages
        ])

        # Build prompt
        prompt = f"""{self.system_prompt}

CONVERSATION SO FAR:
{conversation_history}

Respond as the ASSISTANT. Remember to be concise and conversational."""

        # Get AI response
        agent = create_agent(self.agent_type, self.agent_config)
        result = agent.invoke(prompt)

        if result.success:
            assistant_response = result.content.strip()
        else:
            assistant_response = (
                "I can synthesize a strategy from what you've shared so far. "
                "Want me to generate it?"
            )
            state.ready_to_create = True

        # Remove any "ASSISTANT:" prefix if the model added it
        if assistant_response.upper().startswith("ASSISTANT:"):
            assistant_response = assistant_response[10:].strip()

        if "[READY_TO_CREATE]" in assistant_response:
            assistant_response = assistant_response.replace("[READY_TO_CREATE]", "").strip()
            state.ready_to_create = True

        state.messages.append(StrategyMessage(role="assistant", content=assistant_response))

        # Check if we have enough info to create a strategy
        # Look for strategy proposal patterns
        lower_response = assistant_response.lower()
        if any(phrase in lower_response for phrase in [
            "strategy type:",
            "does this capture",
            "here's what i'm thinking",
            "based on what you've shared",
            "i'd suggest",
        ]):
            state.ready_to_create = True

        if not state.ready_to_create and state.turn_count >= 4:
            state.ready_to_create = True

        # Try to extract info from the conversation
        self._extract_info(state)

        return state

    def _extract_info(self, state: StrategyConversation) -> None:
        """Extract strategy information from the conversation."""
        # Simple extraction from conversation - look for patterns
        full_text = " ".join([m.content for m in state.messages]).lower()

        # Detect strategy type
        if "daily" in full_text and ("post" in full_text or "tip" in full_text):
            state.extracted_info.strategy_type = "daily"
        elif "series" in full_text or "chapter" in full_text or "week" in full_text:
            state.extracted_info.strategy_type = "series"
        elif "campaign" in full_text:
            state.extracted_info.strategy_type = "campaign"

        # Detect platforms
        platforms = []
        if "linkedin" in full_text:
            platforms.append("LinkedIn")
        if "thread" in full_text:
            platforms.append("Threads")
        if "twitter" in full_text or " x " in full_text:
            platforms.append("X/Twitter")
        state.extracted_info.platforms = platforms

    def generate_strategy_summary(self, state: StrategyConversation) -> dict:
        """Generate a structured strategy summary from the conversation."""
        # Ask the AI to extract the strategy as JSON
        conversation_history = "\n\n".join([
            f"{msg.role.upper()}: {msg.content}"
            for msg in state.messages
        ])

        prompt = f"""Based on this conversation, extract the content strategy as JSON.

CONVERSATION:
{conversation_history}

Return ONLY valid JSON in this exact format (no markdown, no explanation):
{{
    "strategy_type": "series" or "daily" or "campaign",
    "positioning": "how they want to be seen professionally",
    "signature_thesis": "their core message in one sentence",
    "target_audience": "who they're writing for",
    "target_roles": ["role 1", "role 2"],
    "content_style": "teaching" or "narrative" or "informational" or "mixed",
    "post_frequency": "daily" or "weekly" or "2x per week" etc,
    "posts_per_week": 1,
    "post_length": "250-400 words" or "short" or "long",
    "voice_constraints": "short summary of tone/structure constraints",
    "series_length_weeks": 6,
    "intellectual_enemies": ["enemy 1", "enemy 2"],
    "platforms": ["LinkedIn", "Threads", etc],
    "chapter_themes": ["theme 1", "theme 2", ...] (only if series type, otherwise empty array)
}}"""

        agent = create_agent(self.agent_type, self.agent_config)
        result = agent.invoke(prompt)

        if result.success:
            try:
                # Try to parse JSON from response
                content = result.content.strip()
                # Remove markdown code blocks if present
                if content.startswith("```"):
                    content = content.split("```")[1]
                    if content.startswith("json"):
                        content = content[4:]
                    content = content.strip()

                return json.loads(content)
            except json.JSONDecodeError:
                pass

        # Return extracted info as fallback
        return self._fallback_strategy_summary(state)

    def _fallback_strategy_summary(self, state: StrategyConversation) -> dict:
        """Return a usable strategy summary when JSON extraction fails."""
        info = state.extracted_info.model_dump()
        last_user_message = next(
            (msg.content for msg in reversed(state.messages) if msg.role == "user"),
            "",
        )
        positioning = info.get("positioning") or last_user_message or "Content creator"
        signature_thesis = info.get("signature_thesis") or (
            f"I share practical, experience-backed insights about {positioning}."
        )
        chapter_themes = info.get("chapter_themes") or [
            "Foundations",
            "Lessons Learned",
            "Frameworks",
            "Execution",
        ]

        return {
            "strategy_type": info.get("strategy_type") or "series",
            "positioning": positioning,
            "signature_thesis": signature_thesis,
            "target_audience": info.get("target_audience") or "Professionals",
            "target_roles": info.get("target_roles") or [],
            "content_style": info.get("content_style") or "mixed",
            "post_frequency": info.get("post_frequency") or "2x per week",
            "posts_per_week": info.get("posts_per_week") or 2,
            "post_length": info.get("post_length") or "250-400 words",
            "voice_constraints": info.get("voice_constraints") or "Story-driven, no bullets.",
            "series_length_weeks": info.get("series_length_weeks") or 6,
            "intellectual_enemies": info.get("intellectual_enemies") or [],
            "platforms": info.get("platforms") or ["LinkedIn"],
            "chapter_themes": chapter_themes,
        }


# Singleton instance
strategy_chat_service = StrategyChatService()
