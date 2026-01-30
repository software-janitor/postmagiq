"""Service for voice learning and analysis."""

import json
import os
from typing import Optional, Union
from uuid import UUID
from pydantic import BaseModel

import requests

try:
    from groq import Groq
except ImportError:
    Groq = None

from api.services.content_service import ContentService
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
    signature_phrases: list[str]
    storytelling_style: str
    emotional_register: str
    summary: str


# =============================================================================
# LLM Prompts
# =============================================================================


VOICE_ANALYSIS_PROMPT = """Analyze these writing samples from the same author and extract their natural voice characteristics.

Writing samples:
{samples}

Analyze the following dimensions:

1. **Tone** (2-3 adjectives): e.g., "reflective, warm, technically grounded"
2. **Sentence Patterns**:
   - Average sentence length (short/medium/long)
   - Length variation (consistent/varied/dramatic)
   - Common structures (simple, compound, lists, fragments)
3. **Vocabulary Level**:
   - Technical depth (jargon-heavy, accessible, mixed)
   - Register (formal, casual, conversational)
4. **Signature Phrases**: Phrases or constructions that recur across samples
5. **Storytelling Style**:
   - Opening approach (chronological, in-media-res, thesis-first)
   - Detail preference (concrete specifics, abstractions, metaphors)
6. **Emotional Register**:
   - How they handle vulnerability (open, guarded, analytical)
   - How they express confidence (direct, humble, qualified)
7. **Summary**: A 2-3 sentence description of their unique voice

Include specific examples from the samples to support each observation.

Output ONLY valid JSON matching this structure:
{
  "tone": "adjective1, adjective2, adjective3",
  "sentence_patterns": {
    "average_length": "short|medium|long",
    "variation": "consistent|varied|dramatic",
    "common_structures": ["structure1", "structure2"]
  },
  "vocabulary_level": "Description of vocabulary style",
  "signature_phrases": ["phrase1", "phrase2", "phrase3"],
  "storytelling_style": "Description of storytelling approach",
  "emotional_register": "Description of emotional expression",
  "summary": "2-3 sentence summary of their unique voice"
}
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

        # Groq configuration
        if self.llm_provider == "groq":
            self.groq_api_key = os.environ.get("GROQ_API_KEY", "")
            self.model = os.environ.get("VOICE_MODEL", "openai/gpt-oss-120b")
            if Groq and self.groq_api_key:
                self.groq_client = Groq(api_key=self.groq_api_key)
            else:
                self.groq_client = None
        else:
            # Ollama configuration
            self.ollama_host = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
            self.model = os.environ.get(
                "VOICE_MODEL", os.environ.get("OLLAMA_MODEL", "llama3.2")
            )
            self.groq_client = None

    def _call_llm(self, prompt: str) -> str:
        """Call LLM based on configured provider."""
        if self.llm_provider == "groq" and self.groq_client:
            return self._call_groq(prompt)
        return self._call_ollama(prompt)

    def _call_groq(self, prompt: str) -> str:
        """Call Groq LLM."""
        try:
            response = self.groq_client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=4096,
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            raise RuntimeError(f"Groq LLM request failed: {e}")

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
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            pass

        import re

        json_match = re.search(r"\{[\s\S]*\}", response)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass

        raise ValueError(f"Could not parse JSON from response: {response[:200]}...")

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

        # Call LLM
        response = self._call_llm(prompt)
        data = self._parse_json_response(response)

        return VoiceAnalysis(
            tone=data.get("tone", ""),
            sentence_patterns=data.get("sentence_patterns", {}),
            vocabulary_level=data.get("vocabulary_level", ""),
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

        # Call LLM
        response = self._call_llm(prompt)
        data = self._parse_json_response(response)

        return VoiceAnalysis(
            tone=data.get("tone", ""),
            sentence_patterns=data.get("sentence_patterns", {}),
            vocabulary_level=data.get("vocabulary_level", ""),
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
