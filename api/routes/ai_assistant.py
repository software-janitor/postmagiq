"""API routes for AI assistant chat."""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

from runner.agents import create_agent
from api.services.onboarding_service import OnboardingService, GeneratedPlan
from api.services.strategy_chat_service import (
    StrategyChatService,
    StrategyConversation,
    StrategyMessage,
)

router = APIRouter(prefix="/ai-assistant", tags=["ai-assistant"])

# Strategy chat service instance
strategy_chat = StrategyChatService()
onboarding_service = OnboardingService()


class ChatRequest(BaseModel):
    message: str
    context: str  # What the user is working on (scenes, poses, etc.)
    agent_type: str = "gemini"  # Default to Gemini, can be "claude" or "ollama"


class ChatResponse(BaseModel):
    response: str
    success: bool
    error: Optional[str] = None


# System prompts for different contexts
CONTEXT_PROMPTS = {
    "scenes": """You are helping create image scene descriptions for a professional content creator.
Scenes describe environments where an Engineer and a Robot work together.
Each scene has:
- A code (e.g., A27 for success, B29 for failure, C28 for unresolved)
- A name (short descriptive title)
- A sentiment (SUCCESS, FAILURE, or UNRESOLVED)
- A viewpoint (standard, wide, close_up, over_shoulder, birds_eye, high_angle, profile)
- A description (detailed visual description of the scene)
- Optional flags: is_hardware_only (uses hardware props), no_desk_props (empty desk)

Keep descriptions visual and specific. Include what's on monitors, how people are positioned, robot actions.
When suggesting scenes, provide complete JSON that can be added to the database.""",

    "poses": """You are helping create pose descriptions for a professional content creator.
Poses describe how the Engineer is positioned/gesturing in images.
Each pose has:
- A code (e.g., S11 for success, F13 for failure, U13 for unresolved)
- A sentiment (SUCCESS, FAILURE, or UNRESOLVED)
- A description (the physical pose)
- An emotional note (what feeling it conveys)

Match poses to their sentiment. SUCCESS poses show confidence, satisfaction.
FAILURE poses show frustration, defeat. UNRESOLVED poses show thinking, uncertainty.
When suggesting poses, provide complete JSON that can be added to the database.""",

    "outfits": """You are helping create outfit descriptions for a professional content creator.
Outfits describe what the Engineer wears (professional casual style).
Each outfit has:
- A vest (suit vest color/style)
- A shirt (shirt color/pattern)
- Pants (pants color/style)

The style is always professional but approachable: vest buttoned, shirt collar open (no tie), sleeves rolled up.
When suggesting outfits, provide complete JSON that can be added to the database.""",

    "props": """You are helping create prop descriptions for a professional content creator.
Props are items on the desk in images.
Each prop has:
- A category (notes, drinks, tech, plants, hardware_boards, hardware_tools)
- A description (detailed visual description)
- A context (all, software, hardware) - when this prop appears

Props add realism and personality to scenes.
When suggesting props, provide complete JSON that can be added to the database.""",

    "characters": """You are helping refine character descriptions for image generation.
There are two characters:
1. The Engineer - a male professional in his mid-30s with specific appearance details
2. The Robot - a small hovering assistant robot with LED face

Help refine appearance details, facial features, clothing rules, or robot design.
Be specific and visual in descriptions.""",

    "strategy": """You are helping refine a LinkedIn content strategy.
The strategy includes:
- A signature thesis (core message)
- Target audience
- Positioning (how they want to be seen)
- Content style
- Chapters with themes and posts

Help improve:
- Making the thesis more compelling and specific
- Refining the target audience description
- Sharpening the positioning statement
- Suggesting chapter themes that support the thesis
- Improving enemy definitions (what the posts argue against)

Be strategic and specific. Good content strategy is opinionated.""",

    "voice": """You are helping refine a voice profile for content creation.
A voice profile captures:
- Tone (how the writing feels)
- Storytelling style (how stories are structured)
- Emotional register (what emotions are expressed)
- Vocabulary level (sophistication of language)
- Signature phrases (recurring expressions)
- Sentence patterns (rhythm and structure)

Help improve:
- Making the tone description more precise
- Identifying patterns the AI should capture
- Suggesting signature phrases that feel authentic
- Recommending storytelling techniques to emphasize

Be specific about linguistic patterns.""",

    "personas": """You are helping improve AI workflow persona instructions.
Personas are instructions for AI agents in a content workflow:
- Writer: Drafts content in the user's voice
- Auditor: Reviews drafts against quality guidelines
- Synthesizer: Combines feedback and improves drafts
- Orchestrator: Controls workflow decisions

Help improve:
- Making instructions clearer and more specific
- Adding examples of good/bad outputs
- Defining edge cases and how to handle them
- Setting appropriate quality thresholds

Persona instructions should be clear, specific, and actionable.""",
}


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Send a message to the AI assistant."""
    try:
        # Get context-specific system prompt
        system_prompt = CONTEXT_PROMPTS.get(request.context, "")

        # Build full prompt
        full_prompt = f"""System: {system_prompt}

User: {request.message}

Respond helpfully and concisely. If suggesting new items to add, format them as JSON."""

        # Create agent with minimal config and invoke
        agent_config = {"name": request.agent_type}
        agent = create_agent(request.agent_type, agent_config)
        result = agent.invoke(full_prompt)

        if result.success:
            return ChatResponse(
                response=result.content,
                success=True
            )
        else:
            return ChatResponse(
                response="",
                success=False,
                error=result.error or "Agent invocation failed"
            )

    except Exception as e:
        return ChatResponse(
            response="",
            success=False,
            error=str(e)
        )


@router.get("/available-agents")
async def available_agents():
    """List available AI agents."""
    return {
        "agents": [
            {"id": "ollama", "name": "Ollama (Local)", "description": "Fast local model"},
            {"id": "claude", "name": "Claude", "description": "Anthropic Claude"},
            {"id": "gemini", "name": "Gemini", "description": "Google Gemini"},
        ]
    }


# =============================================================================
# Strategy Chat Endpoints
# =============================================================================


class StrategyChatMessageRequest(BaseModel):
    """Request to send a message in strategy chat."""
    message: str
    state: Optional[dict] = None  # StrategyConversation as dict


class StrategyChatResponse(BaseModel):
    """Response from strategy chat."""
    assistant_message: str
    state: dict  # StrategyConversation as dict
    ready_to_create: bool
    success: bool
    error: Optional[str] = None


class StrategyCreateRequest(BaseModel):
    """Request to create strategy from chat."""
    state: dict  # StrategyConversation as dict


class StrategyCreateResponse(BaseModel):
    """Response with extracted strategy."""
    strategy: dict
    success: bool
    error: Optional[str] = None


class StrategyPlanRequest(BaseModel):
    """Request to generate a plan from strategy summary."""
    strategy: dict


class StrategyPlanResponse(BaseModel):
    """Response with generated plan."""
    plan: GeneratedPlan
    success: bool
    error: Optional[str] = None


@router.post("/strategy/start", response_model=StrategyChatResponse)
async def start_strategy_chat():
    """Start a new strategy creation conversation."""
    try:
        state = strategy_chat.start_conversation()
        return StrategyChatResponse(
            assistant_message=state.messages[-1].content,
            state=state.model_dump(),
            ready_to_create=state.ready_to_create,
            success=True,
        )
    except Exception as e:
        return StrategyChatResponse(
            assistant_message="",
            state={},
            ready_to_create=False,
            success=False,
            error=str(e),
        )


@router.post("/strategy/message", response_model=StrategyChatResponse)
async def send_strategy_message(request: StrategyChatMessageRequest):
    """Send a message in the strategy chat conversation."""
    try:
        # Reconstruct state from dict
        if request.state:
            state = StrategyConversation(**request.state)
        else:
            state = strategy_chat.start_conversation()

        # Continue conversation
        state = strategy_chat.continue_conversation(state, request.message)

        return StrategyChatResponse(
            assistant_message=state.messages[-1].content,
            state=state.model_dump(),
            ready_to_create=state.ready_to_create,
            success=True,
        )
    except Exception as e:
        return StrategyChatResponse(
            assistant_message="",
            state=request.state or {},
            ready_to_create=False,
            success=False,
            error=str(e),
        )


@router.post("/strategy/extract", response_model=StrategyCreateResponse)
async def extract_strategy(request: StrategyCreateRequest):
    """Extract a structured strategy from the conversation."""
    try:
        state = StrategyConversation(**request.state)
        strategy = strategy_chat.generate_strategy_summary(state)

        return StrategyCreateResponse(
            strategy=strategy,
            success=True,
        )
    except Exception as e:
        return StrategyCreateResponse(
            strategy={},
            success=False,
            error=str(e),
        )


@router.post("/strategy/plan", response_model=StrategyPlanResponse)
async def generate_strategy_plan(request: StrategyPlanRequest):
    """Generate a full content plan from extracted strategy summary."""
    try:
        plan = onboarding_service.generate_plan_from_strategy(request.strategy)
        return StrategyPlanResponse(
            plan=plan,
            success=True,
        )
    except Exception as e:
        return StrategyPlanResponse(
            plan=GeneratedPlan(signature_thesis="", chapters=[]),
            success=False,
            error=str(e),
        )
