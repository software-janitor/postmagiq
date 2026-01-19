"""Pydantic models for content strategy database records."""

from datetime import datetime
from typing import Optional, Union
from uuid import UUID

from pydantic import BaseModel

IdType = Union[str, UUID]
IdOpt = Optional[IdType]


class UserRecord(BaseModel):
    """User record."""
    id: IdOpt = None
    name: str
    email: Optional[str] = None
    created_at: Optional[str] = None


class PlatformRecord(BaseModel):
    """Content platform/stream (LinkedIn, Threads, etc.)."""
    id: IdOpt = None
    user_id: IdType
    name: str  # "LinkedIn", "Threads", "Twitter/X"
    description: Optional[str] = None  # "52-week thought leadership campaign"
    post_format: Optional[str] = None  # "long-form", "short-form", "thread"
    default_word_count: Optional[int] = None  # 300 for LinkedIn, 280 for Twitter
    uses_enemies: bool = True  # Whether this platform uses the enemy/thesis structure
    is_active: bool = True
    created_at: Optional[str] = None


class GoalRecord(BaseModel):
    """Content positioning goals."""
    id: IdOpt = None
    user_id: IdType
    platform_id: IdOpt = None  # Which platform this strategy is for
    voice_profile_id: IdOpt = None  # Attached voice profile
    image_config_set_id: IdOpt = None  # Attached image config set
    strategy_type: str = "series"  # "series" (chapters), "daily" (no chapters), "campaign" (fixed period)
    positioning: Optional[str] = None  # "Distinguished Engineer", etc.
    signature_thesis: Optional[str] = None
    target_audience: Optional[str] = None
    content_style: Optional[str] = None  # "narrative", "teaching", "informational", "mixed"
    onboarding_mode: Optional[str] = None  # "quick" or "deep"
    onboarding_transcript: Optional[str] = None  # JSON of conversation
    created_at: Optional[str] = None


class ChapterRecord(BaseModel):
    """Content chapter/theme."""
    id: IdOpt = None
    user_id: IdType
    platform_id: IdOpt = None  # Which platform this chapter belongs to
    chapter_number: int
    title: str
    description: Optional[str] = None
    theme: Optional[str] = None  # "enemy" for teaching, or other framing
    theme_description: Optional[str] = None
    weeks_start: Optional[int] = None
    weeks_end: Optional[int] = None


class PostRecord(BaseModel):
    """Individual content post."""
    id: IdOpt = None
    user_id: IdType
    chapter_id: IdType
    post_number: int
    topic: Optional[str] = None
    shape: Optional[str] = None  # "FULL", "PARTIAL", "OBSERVATION", "SHORT", "REVERSAL"
    cadence: Optional[str] = None  # "Teaching", "Field Note", "Informational"
    entry_point: Optional[str] = None
    status: str = "not_started"  # "not_started", "needs_story", "draft", "ready", "published"
    story_used: Optional[str] = None
    published_at: Optional[str] = None
    published_url: Optional[str] = None
    guidance: Optional[str] = None  # LLM-generated guidance


class WritingSampleRecord(BaseModel):
    """Writing sample for voice learning."""
    id: IdOpt = None
    user_id: IdType
    source_type: str  # "prompt" or "upload"
    prompt_id: IdOpt = None
    prompt_text: Optional[str] = None
    title: Optional[str] = None
    content: str
    word_count: Optional[int] = None
    created_at: Optional[str] = None


class VoiceProfileRecord(BaseModel):
    """Extracted voice characteristics."""
    id: IdOpt = None
    user_id: IdType
    name: str = "Default"  # Profile name for library
    description: Optional[str] = None  # Optional description
    is_default: bool = False  # Whether this is the default profile
    tone: Optional[str] = None  # "reflective", "direct", "warm", etc.
    sentence_patterns: Optional[str] = None  # JSON
    vocabulary_level: Optional[str] = None  # "technical", "accessible", "mixed"
    signature_phrases: Optional[str] = None  # JSON
    storytelling_style: Optional[str] = None  # "chronological", "in-media-res"
    emotional_register: Optional[str] = None  # "vulnerable", "confident", "analytical"
    raw_analysis: Optional[str] = None  # Full LLM analysis JSON
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class ImagePromptRecord(BaseModel):
    """Generated image prompt for a post."""
    id: IdOpt = None
    user_id: IdType
    post_id: IdType  # e.g., "c1p1"
    sentiment: Optional[str] = None  # "SUCCESS", "FAILURE", "UNRESOLVED"
    context: str = "software"  # "software" or "hardware"
    scene_code: Optional[str] = None  # e.g., "A1", "B3", "C5"
    scene_name: Optional[str] = None
    pose_code: Optional[str] = None  # e.g., "S1", "F2", "U3"
    outfit_vest: Optional[str] = None
    outfit_shirt: Optional[str] = None
    prompt_content: str
    version: int = 1
    image_data: Optional[str] = None  # Base64 encoded image (watermark removed)
    created_at: Optional[str] = None


class ImageConfigSetRecord(BaseModel):
    """Image configuration set that groups scenes, poses, and props."""
    id: IdOpt = None
    user_id: IdType
    name: str  # "Robot + Engineer", "Minimalist", etc.
    description: Optional[str] = None
    is_default: bool = False
    created_at: Optional[str] = None


class WorkflowPersonaRecord(BaseModel):
    """Workflow persona definition for AI agents."""
    id: IdOpt = None
    user_id: IdType
    name: str  # "Writer", "Auditor", "Input Validator"
    slug: str  # "writer", "auditor", "input-validator"
    description: Optional[str] = None
    content: str  # The full persona prompt content
    is_system: bool = False  # True for built-in personas
    model_tier: Optional[str] = None  # "writer", "auditor", "coder" for Ollama model selection
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class WorkflowRunRecord(BaseModel):
    """Workflow execution run."""
    id: IdOpt = None
    user_id: IdType
    run_id: IdType  # e.g., "2024-01-15_143022_post_03"
    story: str  # e.g., "post_03"
    status: str = "running"  # "running", "paused", "complete", "error", "aborted"
    current_state: Optional[str] = None
    final_state: Optional[str] = None
    total_tokens: int = 0
    total_cost_usd: float = 0.0
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error: Optional[str] = None


class WorkflowOutputRecord(BaseModel):
    """Output from a workflow step."""
    id: IdOpt = None
    run_id: IdType
    state_name: str  # e.g., "story-review", "story-process", "draft"
    agent: Optional[str] = None  # e.g., "claude", "gemini"
    output_type: str  # "review", "processed", "draft", "audit", "final"
    content: str
    created_at: Optional[str] = None


class WorkflowSessionRecord(BaseModel):
    """CLI session for workflow agents."""
    id: IdOpt = None
    user_id: IdType
    run_id: IdOpt = None  # Link to workflow run (optional)
    agent_name: str  # "claude", "gemini", "codex"
    session_id: IdType  # The CLI-provided session ID
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


# =============================================================================
# API Response Models (for endpoints)
# =============================================================================

class UserResponse(BaseModel):
    """User data for API responses."""
    id: IdType  # UUID string
    name: str
    email: Optional[str] = None
    has_goal: bool = False
    has_voice_profile: bool = False
    post_count: int = 0


class PlatformResponse(BaseModel):
    """Platform data for API responses."""
    id: IdType  # UUID string
    user_id: IdType
    name: str
    description: Optional[str] = None
    post_format: Optional[str] = None
    default_word_count: Optional[int] = None
    uses_enemies: bool = True
    is_active: bool = True
    created_at: Optional[str] = None


class GoalResponse(BaseModel):
    """Goal data for API responses."""
    id: IdType  # UUID string
    strategy_type: str = "series"
    voice_profile_id: IdOpt = None
    image_config_set_id: IdOpt = None
    positioning: Optional[str] = None
    signature_thesis: Optional[str] = None
    target_audience: Optional[str] = None
    content_style: Optional[str] = None
    onboarding_mode: Optional[str] = None


class ChapterResponse(BaseModel):
    """Chapter data with post counts."""
    id: IdType  # UUID string
    chapter_number: int
    title: str
    description: Optional[str] = None
    theme: Optional[str] = None
    theme_description: Optional[str] = None
    weeks_start: Optional[int] = None
    weeks_end: Optional[int] = None
    post_count: int = 0
    completed_count: int = 0


class PostResponse(BaseModel):
    """Post data for API responses."""
    id: IdType  # UUID string
    post_number: int
    chapter_id: IdType
    chapter_number: int
    chapter_title: str
    topic: Optional[str] = None
    shape: Optional[str] = None
    cadence: Optional[str] = None
    entry_point: Optional[str] = None
    status: str
    guidance: Optional[str] = None
    published_url: Optional[str] = None


class VoiceProfileResponse(BaseModel):
    """Voice profile for API responses."""
    id: IdType  # UUID string
    name: str = "Default"
    description: Optional[str] = None
    is_default: bool = False
    tone: Optional[str] = None
    sentence_patterns: Optional[str] = None
    vocabulary_level: Optional[str] = None
    signature_phrases: Optional[str] = None
    storytelling_style: Optional[str] = None
    emotional_register: Optional[str] = None
    created_at: Optional[str] = None


class ImagePromptResponse(BaseModel):
    """Image prompt for API responses."""
    id: IdType
    post_id: IdType
    sentiment: Optional[str] = None
    context: str = "software"
    scene_code: Optional[str] = None
    scene_name: Optional[str] = None
    pose_code: Optional[str] = None
    outfit_vest: Optional[str] = None
    outfit_shirt: Optional[str] = None
    prompt_content: str
    version: int = 1
    image_data: Optional[str] = None  # Base64 encoded image
    has_image: bool = False  # Quick check without loading full base64
    created_at: Optional[str] = None


class ImageConfigSetResponse(BaseModel):
    """Image config set for API responses."""
    id: IdType
    user_id: IdType
    name: str
    description: Optional[str] = None
    is_default: bool = False
    created_at: Optional[str] = None


# =============================================================================
# Character & Outfit Configuration Models
# =============================================================================


class CharacterTemplateRecord(BaseModel):
    """Character template (human_male, human_female, robot, etc.)."""
    id: IdOpt = None
    name: str  # 'human_male', 'human_female', 'robot', etc.
    description: Optional[str] = None
    default_parts: Optional[str] = None  # JSON array of applicable part types
    created_at: Optional[str] = None


class OutfitPartRecord(BaseModel):
    """Individual outfit part (hat, glasses, jacket, etc.)."""
    id: IdOpt = None
    user_id: IdType
    part_type: str  # 'hat', 'glasses', 'jacket', 'vest', 'blouse', etc.
    name: str  # 'Red Baseball Cap', 'Aviator Sunglasses'
    description: Optional[str] = None  # Full description for image prompts
    created_at: Optional[str] = None


class OutfitRecord(BaseModel):
    """Complete outfit in the Outfit Bank."""
    id: IdOpt = None
    user_id: IdType
    name: str  # 'Casual Friday', 'Conference Speaker'
    description: Optional[str] = None
    template_id: IdOpt = None  # Which template this outfit is for
    created_at: Optional[str] = None


class OutfitItemRecord(BaseModel):
    """Link between outfit and parts."""
    id: IdOpt = None
    outfit_id: IdType
    part_id: IdType


class CharacterRecord(BaseModel):
    """Character with structured face details."""
    id: IdOpt = None
    user_id: IdType
    name: str  # 'Engineer', 'Robot Sidekick'
    template_id: IdOpt = None
    description: Optional[str] = None  # AI-generated or manual description
    # Structured face details (for human templates)
    skin_tone: Optional[str] = None
    face_shape: Optional[str] = None
    eye_details: Optional[str] = None
    hair_details: Optional[str] = None
    facial_hair: Optional[str] = None
    distinguishing_features: Optional[str] = None
    # For non-human templates
    physical_traits: Optional[str] = None  # JSON
    # Clothing rules
    clothing_rules: Optional[str] = None  # Descriptive text
    visible_parts: Optional[str] = None  # JSON array of visible part types
    created_at: Optional[str] = None


class CharacterOutfitRecord(BaseModel):
    """Link between character and outfit."""
    id: IdOpt = None
    character_id: IdType
    outfit_id: IdType
    is_default: bool = False


class SentimentRecord(BaseModel):
    """Configurable scene sentiment."""
    id: IdOpt = None
    user_id: IdType
    name: str  # 'success', 'failure', 'discovery', etc.
    description: Optional[str] = None
    color_hint: Optional[str] = None  # Primary color for UI
    robot_color: Optional[str] = None  # Robot color for this sentiment
    robot_eyes: Optional[str] = None  # Robot eye expression
    robot_posture: Optional[str] = None  # Robot posture
    is_system: bool = False
    created_at: Optional[str] = None


class SceneCharacterRecord(BaseModel):
    """Link between scene and character."""
    id: IdOpt = None
    scene_id: IdType
    character_id: IdType
    outfit_id: IdOpt = None  # Optional specific outfit for this scene
    position: Optional[str] = None  # 'left', 'right', 'center'


class PropCategoryRecord(BaseModel):
    """Dynamic prop category."""
    id: IdOpt = None
    user_id: IdType
    name: str  # 'notes', 'drinks', 'tech'
    description: Optional[str] = None
    context: str = "all"  # 'all', 'software', 'hardware'
    is_system: bool = False
    created_at: Optional[str] = None


class ScenePropRuleRecord(BaseModel):
    """Prop rules per scene."""
    id: IdOpt = None
    scene_id: IdType
    prop_category_id: IdOpt = None
    prop_id: IdOpt = None
    required: bool = False
    excluded: bool = False
    max_count: int = 1


class ContextPropRuleRecord(BaseModel):
    """Prop rules per context."""
    id: IdOpt = None
    user_id: IdType
    context: str  # 'software', 'hardware'
    prop_category_id: IdType
    weight: int = 1


# API Response Models for Character/Outfit System


class CharacterTemplateResponse(BaseModel):
    """Character template for API responses."""
    id: IdType
    name: str
    description: Optional[str] = None
    default_parts: Optional[list[str]] = None  # Parsed JSON
    created_at: Optional[str] = None


class OutfitPartResponse(BaseModel):
    """Outfit part for API responses."""
    id: IdType
    user_id: IdType
    part_type: str
    name: str
    description: Optional[str] = None
    created_at: Optional[str] = None


class OutfitResponse(BaseModel):
    """Outfit for API responses."""
    id: IdType
    user_id: IdType
    name: str
    description: Optional[str] = None
    template_id: IdOpt = None
    template_name: Optional[str] = None  # Joined from character_templates
    parts: list[OutfitPartResponse] = []  # Joined from outfit_items
    created_at: Optional[str] = None


class CharacterResponse(BaseModel):
    """Character for API responses."""
    id: IdType
    user_id: IdType
    name: str
    template_id: IdOpt = None
    template_name: Optional[str] = None  # Joined from character_templates
    description: Optional[str] = None
    skin_tone: Optional[str] = None
    face_shape: Optional[str] = None
    eye_details: Optional[str] = None
    hair_details: Optional[str] = None
    facial_hair: Optional[str] = None
    distinguishing_features: Optional[str] = None
    physical_traits: Optional[dict] = None  # Parsed JSON
    clothing_rules: Optional[str] = None
    visible_parts: Optional[list[str]] = None  # Parsed JSON
    outfits: list[OutfitResponse] = []  # Joined from character_outfits
    created_at: Optional[str] = None


class SentimentResponse(BaseModel):
    """Sentiment for API responses."""
    id: IdType
    user_id: IdType
    name: str
    description: Optional[str] = None
    color_hint: Optional[str] = None
    robot_color: Optional[str] = None
    robot_eyes: Optional[str] = None
    robot_posture: Optional[str] = None
    is_system: bool = False
    created_at: Optional[str] = None


class PropCategoryResponse(BaseModel):
    """Prop category for API responses."""
    id: IdType
    user_id: IdType
    name: str
    description: Optional[str] = None
    context: str = "all"
    is_system: bool = False
    prop_count: int = 0  # Number of props in this category
    created_at: Optional[str] = None


class SceneCharacterResponse(BaseModel):
    """Scene-character link for API responses."""
    id: IdType
    scene_id: IdType
    character_id: IdType
    character_name: str  # Joined from characters
    outfit_id: IdOpt = None
    outfit_name: Optional[str] = None  # Joined from outfits
    position: Optional[str] = None


# =============================================================================
# Analytics Models
# =============================================================================


class AnalyticsImportRecord(BaseModel):
    """Track uploaded analytics files."""
    id: IdOpt = None
    user_id: IdType
    platform_name: str  # 'linkedin', 'threads', 'x'
    filename: str
    import_date: Optional[str] = None
    row_count: Optional[int] = None
    status: str = "pending"  # 'pending', 'processed', 'error'
    error_message: Optional[str] = None
    import_type: Optional[str] = None  # 'content_export' or 'post_analytics'


class PostMetricRecord(BaseModel):
    """Normalized metrics from all platforms."""
    id: IdOpt = None
    user_id: IdType
    post_id: IdOpt = None  # Link to internal post
    platform_name: str
    import_id: IdOpt = None
    external_url: Optional[str] = None
    post_date: Optional[str] = None
    impressions: Optional[int] = None
    engagement_count: Optional[int] = None
    engagement_rate: Optional[float] = None
    likes: Optional[int] = None
    comments: Optional[int] = None
    shares: Optional[int] = None
    clicks: Optional[int] = None
    metric_date: str
    created_at: Optional[str] = None
    # Delta tracking
    impressions_delta: Optional[int] = None
    reactions_delta: Optional[int] = None
    last_updated: Optional[str] = None


class AnalyticsImportResponse(BaseModel):
    """Analytics import for API responses."""
    id: IdType
    platform_name: str
    filename: str
    import_date: Optional[str] = None
    row_count: Optional[int] = None
    status: str
    error_message: Optional[str] = None
    import_type: Optional[str] = None


class PostMetricResponse(BaseModel):
    """Post metric for API responses."""
    id: IdType
    post_id: IdOpt = None
    platform_name: str
    external_url: Optional[str] = None
    post_date: Optional[str] = None
    impressions: Optional[int] = None
    engagement_count: Optional[int] = None
    engagement_rate: Optional[float] = None
    likes: Optional[int] = None
    comments: Optional[int] = None
    shares: Optional[int] = None
    clicks: Optional[int] = None
    metric_date: str
    impressions_delta: Optional[int] = None
    reactions_delta: Optional[int] = None


class AnalyticsSummary(BaseModel):
    """Summary analytics for a user/strategy."""
    total_impressions: int = 0
    total_engagements: int = 0
    total_likes: int = 0
    total_comments: int = 0
    total_shares: int = 0
    total_clicks: int = 0
    avg_engagement_rate: float = 0.0
    post_count: int = 0
    top_posts: list[PostMetricResponse] = []


class DailyMetricRecord(BaseModel):
    """Daily aggregate metrics from ENGAGEMENT sheet."""
    id: IdOpt = None
    user_id: IdType
    platform_name: str
    metric_date: str
    impressions: Optional[int] = None
    engagements: Optional[int] = None
    import_id: IdOpt = None
    created_at: Optional[str] = None


class DailyMetricResponse(BaseModel):
    """Daily metric for API responses."""
    id: IdType
    platform_name: str
    metric_date: str
    impressions: Optional[int] = None
    engagements: Optional[int] = None


class FollowerMetricRecord(BaseModel):
    """Daily follower data from FOLLOWERS sheet."""
    id: IdOpt = None
    user_id: IdType
    platform_name: str
    metric_date: str
    new_followers: Optional[int] = None
    total_followers: Optional[int] = None
    import_id: IdOpt = None
    created_at: Optional[str] = None


class FollowerMetricResponse(BaseModel):
    """Follower metric for API responses."""
    id: IdType
    platform_name: str
    metric_date: str
    new_followers: Optional[int] = None
    total_followers: Optional[int] = None


class AudienceDemographicRecord(BaseModel):
    """Overall audience demographics from DEMOGRAPHICS sheet."""
    id: IdOpt = None
    user_id: IdType
    platform_name: str
    category: str  # 'job_title', 'location'
    value: str  # 'Software Engineer', 'LA Metro'
    percentage: Optional[float] = None
    import_id: IdOpt = None
    metric_date: Optional[str] = None
    created_at: Optional[str] = None


class AudienceDemographicResponse(BaseModel):
    """Audience demographic for API responses."""
    id: IdType
    platform_name: str
    category: str
    value: str
    percentage: Optional[float] = None
    metric_date: Optional[str] = None


class PostDemographicRecord(BaseModel):
    """Per-post demographics from TOP DEMOGRAPHICS sheet."""
    id: IdOpt = None
    user_id: IdType
    platform_name: str
    external_url: str
    category: str  # 'job_title', 'location', 'company_size'
    value: str
    percentage: Optional[float] = None
    import_id: IdOpt = None
    created_at: Optional[str] = None


class PostDemographicResponse(BaseModel):
    """Post demographic for API responses."""
    id: IdType
    platform_name: str
    external_url: str
    category: str
    value: str
    percentage: Optional[float] = None


# =============================================================================
# Voice Learning Prompts
# =============================================================================

VOICE_PROMPTS = [
    {
        "id": "crisis",
        "prompt": "Tell me about a time something broke at work and you had to fix it under pressure.",
        "reveals": "Crisis narrative style, technical detail level",
    },
    {
        "id": "lesson",
        "prompt": "Describe a lesson you learned the hard way - something that took failure to understand.",
        "reveals": "Vulnerability, reflection depth",
    },
    {
        "id": "contrarian",
        "prompt": "What's something most people in your field get wrong? Why do you think differently?",
        "reveals": "Contrarian voice, argumentation style",
    },
    {
        "id": "mentor",
        "prompt": "Tell me about a mentor, colleague, or moment that changed how you approach your work.",
        "reveals": "Gratitude expression, relationship framing",
    },
    {
        "id": "proud",
        "prompt": "Describe a project you're proud of - what made it meaningful to you?",
        "reveals": "Pride expression, value articulation",
    },
    {
        "id": "abandoned",
        "prompt": "What's a tool, process, or idea you used to believe in but have since abandoned? Why?",
        "reveals": "Intellectual evolution, self-critique",
    },
    {
        "id": "convince",
        "prompt": "Tell me about a time you had to convince someone skeptical - how did you approach it?",
        "reveals": "Persuasion style, stakeholder awareness",
    },
    {
        "id": "explain",
        "prompt": "Describe something complex you've explained to a non-expert. How did you make it clear?",
        "reveals": "Teaching voice, metaphor use",
    },
    {
        "id": "detail",
        "prompt": "What's a small detail in your work that most people overlook but you think matters?",
        "reveals": "Attention to craft, precision level",
    },
    {
        "id": "aha",
        "prompt": "Tell me about a recent 'aha moment' - something that clicked or surprised you.",
        "reveals": "Curiosity expression, insight framing",
    },
]


# =============================================================================
# Content Styles
# =============================================================================

CONTENT_STYLES = [
    {
        "id": "narrative",
        "name": "Narrative",
        "description": "Story-driven, personal experiences",
        "chapter_framing": "Themes (not enemies)",
    },
    {
        "id": "teaching",
        "name": "Teaching",
        "description": "Lesson-based, contrarian takes",
        "chapter_framing": "Enemies to fight",
    },
    {
        "id": "informational",
        "name": "Informational",
        "description": "How-to, educational",
        "chapter_framing": "Topics to cover",
    },
    {
        "id": "mixed",
        "name": "Mixed",
        "description": "Combination based on topic",
        "chapter_framing": "Flexible framing",
    },
]


POST_SHAPES = [
    {"id": "FULL", "name": "Full", "description": "Complete arc with resolution"},
    {"id": "PARTIAL", "name": "Partial", "description": "Unresolved, ends messy"},
    {"id": "OBSERVATION", "name": "Observation", "description": "Noticing, no lesson"},
    {"id": "SHORT", "name": "Short", "description": "Under 200 words"},
    {"id": "REVERSAL", "name": "Reversal", "description": "Updates previous stance"},
]
