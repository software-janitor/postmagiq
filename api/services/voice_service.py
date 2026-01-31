"""Service for voice learning and analysis."""

import json
import logging
import os
from typing import Optional, Union
from uuid import UUID
from pydantic import BaseModel

import requests

logger = logging.getLogger(__name__)

from api.services.content_service import ContentService
from runner.agents.groq_api import GroqAPIAgent
from runner.content.models import VOICE_PROMPTS


# =============================================================================
# Models
# =============================================================================


class WritingSample(BaseModel):
    """A writing sample for voice analysis."""

    source_type: str  # "prompt" or "upload"
    prompt_id: Optional[str] = None
    prompt_text: Optional[str] = None
    title: Optional[str] = None
    content: str


class VoiceAnalysis(BaseModel):
    """Extracted voice characteristics."""

    tone: str
    sentence_patterns: dict
    vocabulary_level: str
    punctuation_style: Optional[dict] = None
    transition_style: Optional[str] = None
    paragraph_rhythm: Optional[dict] = None
    reader_address: Optional[dict] = None
    signature_phrases: list[str]
    storytelling_style: str
    emotional_register: str
    summary: str


# =============================================================================
# LLM Prompts
# =============================================================================


VOICE_SYSTEM_PROMPT = """You are an expert writing voice analyst. Your job is to extract REUSABLE voice characteristics that can guide AI to write NEW content in this author's authentic style.

CRITICAL: Focus on TRANSFERABLE patterns, not content-specific details. The goal is to capture HOW they write, not WHAT they write about.

AVOID extracting:
- Product names, brand names, or specific topics
- Quotes that only make sense in original context
- Content-specific phrases that can't be reused

FOCUS on extracting:
- Syntactic patterns and sentence structures
- Punctuation habits (especially: do they use em-dashes, semicolons, ellipses?)
- Transition word preferences
- How they open and close paragraphs
- Their relationship with the reader (formal/casual, direct/indirect)

Output valid JSON only. No markdown, no explanation."""

VOICE_ANALYSIS_PROMPT = """Analyze these writing samples and extract the author's voice characteristics for use in generating NEW content.

Writing samples:
{samples}

Analyze these dimensions:

1. **Tone** (2-3 adjectives): The emotional quality of their writing

2. **Sentence Patterns**:
   - Average length (short/medium/long)
   - Variation (consistent/varied/dramatic)
   - Common structures (simple, compound, fragments, lists)

3. **Vocabulary Level**: Technical depth and formality register

4. **Punctuation Style** (IMPORTANT - helps avoid AI-sounding patterns):
   - Em-dash usage (none/rare/moderate/heavy)
   - Semicolon usage (none/rare/moderate/heavy)
   - Exclamation points (none/rare/moderate/heavy)
   - Ellipses usage (none/rare/moderate/heavy)
   - Parenthetical asides (none/rare/moderate/heavy)

5. **Transition Style**: How they connect ideas
   - Formal transitions ("However," "Furthermore,") vs casual ("But," "And,") vs minimal

6. **Paragraph Rhythm**:
   - Length preference (short punchy / medium / long flowing)
   - Opening style (topic sentence / hook / question / statement)

7. **Reader Address**:
   - Point of view (first person "I" / inclusive "we" / direct "you" / third person)
   - Relationship (peer/mentor/expert/friend)

8. **Signature Phrases**: Recurring SYNTACTIC patterns only (e.g., "The thing is...", "What I've learned is...", "Here's the deal:")
   - Must be reusable templates, NOT content-specific quotes

9. **Storytelling Style**: Opening approach, detail preference, how they build arguments

10. **Emotional Register**: How they handle vulnerability and express confidence

11. **Summary**: 2-3 sentences capturing their unique voice DNA

Output this JSON structure:
{{
  "tone": "adjective1, adjective2, adjective3",
  "sentence_patterns": {{
    "average_length": "short|medium|long",
    "variation": "consistent|varied|dramatic",
    "common_structures": ["structure1", "structure2"]
  }},
  "vocabulary_level": "description",
  "punctuation_style": {{
    "em_dashes": "none|rare|moderate|heavy",
    "semicolons": "none|rare|moderate|heavy",
    "exclamations": "none|rare|moderate|heavy",
    "ellipses": "none|rare|moderate|heavy",
    "parentheticals": "none|rare|moderate|heavy"
  }},
  "transition_style": "description of how they connect ideas",
  "paragraph_rhythm": {{
    "length": "short|medium|long",
    "opening_style": "description"
  }},
  "reader_address": {{
    "point_of_view": "first person|inclusive we|direct you|third person",
    "relationship": "peer|mentor|expert|friend"
  }},
  "signature_phrases": ["reusable pattern 1...", "reusable pattern 2..."],
  "storytelling_style": "description",
  "emotional_register": "description",
  "summary": "2-3 sentence voice DNA summary"
}}
"""


# =============================================================================
# Service Implementation
# =============================================================================


class VoiceService:
    """Service for voice learning and analysis."""

    def __init__(self, content_service: Optional[ContentService] = None):
        self.content_service = content_service or ContentService()
        self.llm_provider = os.environ.get("LLM_PROVIDER", "ollama")
        self.timeout = 180  # Voice analysis can take longer

        # Groq configuration - use shared GroqAPIAgent
        if self.llm_provider == "groq":
            self.model = os.environ.get("VOICE_MODEL", "openai/gpt-oss-120b")
            self.groq_agent = GroqAPIAgent({
                "name": "voice-analyzer",
                "model": self.model,
                "max_tokens": 4096,
            })
        else:
            # Ollama configuration
            self.ollama_host = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
            self.model = os.environ.get(
                "VOICE_MODEL", os.environ.get("OLLAMA_MODEL", "llama3.2")
            )
            self.groq_agent = None

        # Track last result for token/cost info
        self.last_result = None

    def _call_llm(self, prompt: str, system_prompt: str = None) -> str:
        """Call LLM based on configured provider."""
        if self.llm_provider == "groq" and self.groq_agent:
            return self._call_groq(prompt, system_prompt)
        return self._call_ollama(prompt)

    def _call_groq(self, prompt: str, system_prompt: str = None) -> str:
        """Call Groq LLM with optional system prompt and JSON mode."""
        result = self.groq_agent.invoke_json(prompt, system_prompt=system_prompt)
        self.last_result = result  # Store for token tracking

        if not result.success:
            raise RuntimeError(f"Groq LLM request failed: {result.error}")

        logger.warning(
            f"GROQ response: {result.tokens.input_tokens} in / "
            f"{result.tokens.output_tokens} out, ${result.cost_usd:.4f}"
        )
        return result.content

    def _call_ollama(self, prompt: str) -> str:
        """Call Ollama LLM."""
        try:
            response = requests.post(
                f"{self.ollama_host}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                },
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json()
            return data.get("response", "")
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"Ollama LLM request failed: {e}")

    def _parse_json_response(self, response: str) -> dict:
        """Extract JSON from LLM response."""
        logger.warning(f"PARSE: response length={len(response)}")

        # Try direct parse
        try:
            return json.loads(response)
        except json.JSONDecodeError as e:
            logger.warning(f"PARSE: direct failed: {e}")

        import re

        # Try extracting JSON block
        json_match = re.search(r"\{[\s\S]*\}", response)
        if json_match:
            matched = json_match.group()
            logger.warning(f"PARSE: regex matched len={len(matched)}")
            try:
                return json.loads(matched)
            except json.JSONDecodeError as e:
                logger.warning(f"PARSE: regex failed: {e}")

        # Try extracting from markdown code block
        code_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", response)
        if code_match:
            code_content = code_match.group(1).strip()
            logger.warning(f"PARSE: code block matched len={len(code_content)}")
            try:
                return json.loads(code_content)
            except json.JSONDecodeError as e:
                logger.warning(f"PARSE: code block failed: {e}")

        raise ValueError(f"Could not parse JSON: {response[:300]}...")

    # =========================================================================
    # Voice Prompts
    # =========================================================================

    @staticmethod
    def get_prompts() -> list[dict]:
        """Get the 10 voice learning prompts."""
        return VOICE_PROMPTS

    @staticmethod
    def get_prompt_by_id(prompt_id: str) -> Optional[dict]:
        """Get a specific prompt by ID."""
        for prompt in VOICE_PROMPTS:
            if prompt["id"] == prompt_id:
                return prompt
        return None

    # =========================================================================
    # Sample Management
    # =========================================================================

    def save_sample(
        self,
        user_id: Union[str, UUID],
        sample: WritingSample,
        workspace_id: Optional[UUID] = None,
    ) -> str:
        """Save a writing sample, optionally with workspace scope."""
        return self.content_service.save_writing_sample(
            user_id=user_id,
            source_type=sample.source_type,
            content=sample.content,
            prompt_id=sample.prompt_id,
            prompt_text=sample.prompt_text,
            title=sample.title,
            workspace_id=workspace_id,
        )

    def get_samples(self, user_id: Union[str, UUID]) -> list[dict]:
        """Get all writing samples for a user."""
        samples = self.content_service.get_writing_samples(user_id)
        return [
            {
                "id": s.id,
                "source_type": s.source_type,
                "prompt_id": s.prompt_id,
                "prompt_text": s.prompt_text,
                "title": s.title,
                "content": s.content,
                "word_count": s.word_count,
                "created_at": s.created_at,
            }
            for s in samples
        ]

    def get_total_word_count(self, user_id: Union[str, UUID]) -> int:
        """Get total word count across all samples."""
        samples = self.content_service.get_writing_samples(user_id)
        return sum(s.word_count or 0 for s in samples)

    # =========================================================================
    # Voice Analysis
    # =========================================================================

    def analyze_voice(self, user_id: Union[str, UUID]) -> VoiceAnalysis:
        """Analyze voice from all writing samples."""
        samples = self.content_service.get_writing_samples(user_id)

        if not samples:
            raise ValueError("No writing samples found for user")

        total_words = sum(s.word_count or 0 for s in samples)
        if total_words < 500:
            raise ValueError(
                f"Need at least 500 words for analysis (have {total_words})"
            )

        # Format samples for prompt
        formatted_samples = []
        for i, sample in enumerate(samples, 1):
            header = f"SAMPLE {i}"
            if sample.source_type == "prompt" and sample.prompt_text:
                header += f" (Prompt: {sample.prompt_text})"
            elif sample.title:
                header += f" ({sample.title})"
            formatted_samples.append(f"{header}\n{sample.content}")

        samples_text = "\n\n---\n\n".join(formatted_samples)
        prompt = VOICE_ANALYSIS_PROMPT.format(samples=samples_text)

        # Call LLM with system prompt
        response = self._call_llm(prompt, system_prompt=VOICE_SYSTEM_PROMPT)
        data = self._parse_json_response(response)

        return VoiceAnalysis(
            tone=data.get("tone", ""),
            sentence_patterns=data.get("sentence_patterns", {}),
            vocabulary_level=data.get("vocabulary_level", ""),
            punctuation_style=data.get("punctuation_style"),
            transition_style=data.get("transition_style"),
            paragraph_rhythm=data.get("paragraph_rhythm"),
            reader_address=data.get("reader_address"),
            signature_phrases=data.get("signature_phrases", []),
            storytelling_style=data.get("storytelling_style", ""),
            emotional_register=data.get("emotional_register", ""),
            summary=data.get("summary", ""),
        )

    def save_voice_profile(
        self,
        user_id: Union[str, UUID],
        analysis: VoiceAnalysis,
        raw_response: Optional[str] = None,
    ) -> str:
        """Save analyzed voice profile to database."""
        return self.content_service.save_voice_profile(
            user_id=user_id,
            tone=analysis.tone,
            sentence_patterns=json.dumps(analysis.sentence_patterns),
            vocabulary_level=analysis.vocabulary_level,
            signature_phrases=json.dumps(analysis.signature_phrases),
            storytelling_style=analysis.storytelling_style,
            emotional_register=analysis.emotional_register,
            raw_analysis=raw_response,
        )

    def analyze_and_save(self, user_id: Union[str, UUID]) -> dict:
        """Analyze voice and save profile in one step."""
        analysis = self.analyze_voice(user_id)
        profile_id = self.save_voice_profile(user_id, analysis)

        return {
            "profile_id": profile_id,
            "analysis": analysis.model_dump(),
        }

    # =========================================================================
    # Profile Retrieval
    # =========================================================================

    def _format_profile(self, profile) -> dict:
        """Format a profile record for display."""
        # Parse JSON fields
        sentence_patterns = profile.sentence_patterns or {}
        signature_phrases = profile.signature_phrases or []
        try:
            if isinstance(sentence_patterns, str):
                sentence_patterns = json.loads(sentence_patterns)
            if isinstance(signature_phrases, str):
                signature_phrases = json.loads(signature_phrases)
        except json.JSONDecodeError:
            if isinstance(sentence_patterns, str):
                sentence_patterns = {}
            if isinstance(signature_phrases, str):
                signature_phrases = []

        return {
            "id": profile.id,
            "name": profile.name,
            "description": profile.description,
            "is_default": profile.is_default,
            "tone": profile.tone,
            "sentence_patterns": sentence_patterns,
            "vocabulary_level": profile.vocabulary_level,
            "signature_phrases": signature_phrases,
            "storytelling_style": profile.storytelling_style,
            "emotional_register": profile.emotional_register,
            "created_at": profile.created_at,
        }

    def get_voice_profile(self, user_id: Union[str, UUID]) -> Optional[dict]:
        """Get user's default voice profile formatted for display."""
        profile = self.content_service.get_voice_profile(user_id)
        if not profile:
            return None
        return self._format_profile(profile)

    def get_profile_by_id(self, profile_id: Union[str, UUID]) -> Optional[dict]:
        """Get a specific voice profile by ID."""
        profile = self.content_service.get_voice_profile_by_id(profile_id)
        if not profile:
            return None
        return self._format_profile(profile)

    def get_all_profiles(self, user_id: Union[str, UUID]) -> list[dict]:
        """Get all voice profiles for a user."""
        profiles = self.content_service.get_all_voice_profiles(user_id)
        return [self._format_profile(p) for p in profiles]

    def clone_profile(self, profile_id: Union[str, UUID], new_name: str) -> str:
        """Clone a voice profile with a new name."""
        return self.content_service.clone_voice_profile(profile_id, new_name)

    def set_default_profile(
        self, user_id: Union[str, UUID], profile_id: Union[str, UUID]
    ) -> None:
        """Set a voice profile as the default."""
        self.content_service.set_default_voice_profile(user_id, profile_id)

    def update_profile(self, profile_id: Union[str, UUID], **kwargs) -> None:
        """Update voice profile fields."""
        self.content_service.update_voice_profile(profile_id, **kwargs)

    def delete_profile(self, profile_id: Union[str, UUID]) -> None:
        """Delete a voice profile."""
        self.content_service.delete_voice_profile(profile_id)

    # =========================================================================
    # Validation
    # =========================================================================

    @staticmethod
    def validate_sample_word_count(
        content: str, max_words: int = 500
    ) -> tuple[bool, int]:
        """Validate sample word count.

        Returns:
            (is_valid, word_count)
        """
        word_count = len(content.split())
        return word_count <= max_words, word_count

    def can_analyze(
        self, user_id: Union[str, UUID], min_words: int = 500
    ) -> tuple[bool, int]:
        """Check if user has enough samples for analysis.

        Returns:
            (can_analyze, total_words)
        """
        total = self.get_total_word_count(user_id)
        return total >= min_words, total

    # =========================================================================
    # Workspace-Scoped Methods (for v1 API)
    # =========================================================================

    def get_samples_for_workspace(self, workspace_id: UUID) -> list[dict]:
        """Get all writing samples for a workspace."""
        samples = self.content_service.get_writing_samples_for_workspace(workspace_id)
        return [
            {
                "id": str(s.id),
                "source_type": s.source_type,
                "prompt_id": s.prompt_id,
                "prompt_text": s.prompt_text,
                "title": s.title,
                "content": s.content,
                "word_count": s.word_count,
                "created_at": (
                    s.created_at if isinstance(s.created_at, str)
                    else s.created_at.isoformat() if s.created_at
                    else None
                ),
            }
            for s in samples
        ]

    def get_total_word_count_for_workspace(self, workspace_id: UUID) -> int:
        """Get total word count across all workspace samples."""
        samples = self.content_service.get_writing_samples_for_workspace(workspace_id)
        return sum(s.word_count or 0 for s in samples)

    def analyze_voice_for_workspace(self, workspace_id: UUID) -> VoiceAnalysis:
        """Analyze voice from all workspace writing samples."""
        samples = self.content_service.get_writing_samples_for_workspace(workspace_id)

        if not samples:
            raise ValueError("No writing samples found for workspace")

        total_words = sum(s.word_count or 0 for s in samples)
        if total_words < 500:
            raise ValueError(
                f"Need at least 500 words for analysis (have {total_words})"
            )

        # Format samples for prompt
        formatted_samples = []
        for i, sample in enumerate(samples, 1):
            header = f"SAMPLE {i}"
            if sample.source_type == "prompt" and sample.prompt_text:
                header += f" (Prompt: {sample.prompt_text})"
            elif sample.title:
                header += f" ({sample.title})"
            formatted_samples.append(f"{header}\n{sample.content}")

        samples_text = "\n\n---\n\n".join(formatted_samples)
        prompt = VOICE_ANALYSIS_PROMPT.format(samples=samples_text)

        # Call LLM with system prompt
        response = self._call_llm(prompt, system_prompt=VOICE_SYSTEM_PROMPT)
        data = self._parse_json_response(response)

        return VoiceAnalysis(
            tone=data.get("tone", ""),
            sentence_patterns=data.get("sentence_patterns", {}),
            vocabulary_level=data.get("vocabulary_level", ""),
            punctuation_style=data.get("punctuation_style"),
            transition_style=data.get("transition_style"),
            paragraph_rhythm=data.get("paragraph_rhythm"),
            reader_address=data.get("reader_address"),
            signature_phrases=data.get("signature_phrases", []),
            storytelling_style=data.get("storytelling_style", ""),
            emotional_register=data.get("emotional_register", ""),
            summary=data.get("summary", ""),
        )

    def save_voice_profile_for_workspace(
        self,
        workspace_id: UUID,
        user_id: UUID,
        analysis: VoiceAnalysis,
        raw_response: Optional[str] = None,
    ) -> str:
        """Save analyzed voice profile to database with workspace scope."""
        return self.content_service.save_voice_profile_for_workspace(
            workspace_id=workspace_id,
            user_id=user_id,
            tone=analysis.tone,
            sentence_patterns=json.dumps(analysis.sentence_patterns),
            vocabulary_level=analysis.vocabulary_level,
            signature_phrases=json.dumps(analysis.signature_phrases),
            storytelling_style=analysis.storytelling_style,
            emotional_register=analysis.emotional_register,
            raw_analysis=raw_response,
        )

    def analyze_and_save_for_workspace(
        self,
        workspace_id: UUID,
        user_id: UUID,
    ) -> dict:
        """Analyze voice and save profile for workspace."""
        analysis = self.analyze_voice_for_workspace(workspace_id)
        profile_id = self.save_voice_profile_for_workspace(
            workspace_id, user_id, analysis
        )

        return {
            "profile_id": profile_id,
            "analysis": analysis.model_dump(),
        }
