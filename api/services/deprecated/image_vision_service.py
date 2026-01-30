"""Service for AI-powered image analysis using Gemini Vision."""

import base64
import json
from typing import Optional

from pydantic import BaseModel, Field

from runner.agents import create_agent


class FaceDetails(BaseModel):
    """Structured face details for human characters."""

    skin_tone: Optional[str] = None
    face_shape: Optional[str] = None
    eye_details: Optional[str] = None
    hair_details: Optional[str] = None
    facial_hair: Optional[str] = None
    distinguishing_features: Optional[str] = None


class OutfitAnalysis(BaseModel):
    """Analyzed outfit components from image."""

    hat: Optional[str] = None
    glasses: Optional[str] = None
    jacket: Optional[str] = None
    vest: Optional[str] = None
    cardigan: Optional[str] = None
    sweater: Optional[str] = None
    shirt: Optional[str] = None
    blouse: Optional[str] = None
    top: Optional[str] = None
    tie: Optional[str] = None
    scarf: Optional[str] = None
    necklace: Optional[str] = None
    belt: Optional[str] = None
    pants: Optional[str] = None
    skirt: Optional[str] = None
    dress: Optional[str] = None
    shoes: Optional[str] = None
    heels: Optional[str] = None
    boots: Optional[str] = None
    watch: Optional[str] = None
    bracelet: Optional[str] = None
    earrings: Optional[str] = None
    bag: Optional[str] = None


class PhysicalTraits(BaseModel):
    """Physical traits for non-human or general body details."""

    body_type: Optional[str] = None
    posture: Optional[str] = None
    height_impression: Optional[str] = None
    # For non-human characters
    materials: Optional[str] = None
    colors: Optional[str] = None
    mechanical_features: Optional[str] = None
    expression_system: Optional[str] = None
    distinctive_elements: Optional[str] = None


class CharacterAnalysisResult(BaseModel):
    """Result of analyzing a character image."""

    template_type: str = Field(description="human_male, human_female, or non_human")
    face_details: Optional[FaceDetails] = None
    physical_traits: Optional[PhysicalTraits] = None
    outfit: Optional[OutfitAnalysis] = None
    clothing_rules: Optional[str] = None
    style_notes: Optional[str] = None
    raw_description: Optional[str] = None


ANALYZE_CHARACTER_PROMPT = """Analyze this character image for illustration generation.

The image is provided as base64 encoded data:
{base64_data}

Template type hint: {template_type}

Extract STRUCTURED details and return as JSON.

For HUMAN characters:
1. Face Details:
   - skin_tone: warm/cool tone, ethnicity cues
   - face_shape: oval, square, round, heart, etc.
   - eye_details: color, shape, expression tendencies
   - hair_details: color, length, style, texture
   - facial_hair: none, stubble, beard, mustache (null for female if not applicable)
   - distinguishing_features: scars, freckles, wrinkles, etc.

2. Physical Traits:
   - body_type: slim, athletic, stocky, etc.
   - posture: upright, relaxed, hunched
   - height_impression: tall, average, short

3. Current Outfit (describe each visible piece):
   - hat, glasses, jacket, vest, cardigan, sweater
   - shirt, blouse, top, tie, scarf, necklace
   - belt, pants, skirt, dress
   - shoes, heels, boots
   - watch, bracelet, earrings, bag

4. Clothing Rules: Descriptive text about how clothes are worn
   Example: "Vest always buttoned. Shirt collar open. Sleeves rolled to forearms."

For NON-HUMAN characters:
1. Physical Traits:
   - materials: metal, plastic, organic, etc.
   - colors: primary color scheme
   - mechanical_features: joints, panels, lights, etc.
   - expression_system: how emotions are conveyed (LED eyes, antenna position, etc.)
   - distinctive_elements: unique visual identifiers

Return ONLY valid JSON in this format:
{{
  "template_type": "human_male" | "human_female" | "non_human",
  "face_details": {{
    "skin_tone": "...",
    "face_shape": "...",
    "eye_details": "...",
    "hair_details": "...",
    "facial_hair": "...",
    "distinguishing_features": "..."
  }},
  "physical_traits": {{
    "body_type": "...",
    "posture": "...",
    "height_impression": "..."
  }},
  "outfit": {{
    "jacket": null or "description",
    "vest": null or "description",
    "shirt": null or "description",
    "pants": null or "description",
    ...include all visible items
  }},
  "clothing_rules": "Descriptive text about how clothes are worn...",
  "style_notes": "Overall style impression..."
}}

For non-human characters, face_details should be null and physical_traits should include materials, colors, mechanical_features, expression_system, distinctive_elements instead."""


class ImageVisionService:
    """Service for analyzing character images using Gemini Vision."""

    def __init__(self, agent_type: str = "gemini"):
        self.agent_type = agent_type

    def analyze_character_image(
        self,
        image_bytes: bytes,
        template_type: str = "human_male",
        mime_type: str = "image/png",
    ) -> CharacterAnalysisResult:
        """
        Analyze a character image and extract structured details.

        Args:
            image_bytes: Raw image bytes
            template_type: Hint for expected character type (human_male, human_female, non_human)
            mime_type: MIME type of the image

        Returns:
            CharacterAnalysisResult with extracted details
        """
        # Encode image to base64
        base64_data = base64.b64encode(image_bytes).decode("utf-8")

        # Format as data URL for clarity
        data_url = f"data:{mime_type};base64,{base64_data}"

        # Build prompt with base64 data
        prompt = ANALYZE_CHARACTER_PROMPT.format(
            base64_data=data_url,
            template_type=template_type,
        )

        # Invoke Gemini agent
        agent = create_agent(self.agent_type, {"name": self.agent_type})
        result = agent.invoke(prompt)

        if not result.success:
            return CharacterAnalysisResult(
                template_type=template_type,
                raw_description=f"Analysis failed: {result.error}",
            )

        # Parse JSON response
        try:
            content = result.content.strip()
            # Remove markdown code blocks if present
            if content.startswith("```"):
                lines = content.split("\n")
                content = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])
                if content.startswith("json"):
                    content = content[4:].strip()

            data = json.loads(content)

            # Build result from parsed data
            face_details = None
            if data.get("face_details"):
                face_details = FaceDetails(**data["face_details"])

            physical_traits = None
            if data.get("physical_traits"):
                physical_traits = PhysicalTraits(**data["physical_traits"])

            outfit = None
            if data.get("outfit"):
                outfit = OutfitAnalysis(**data["outfit"])

            return CharacterAnalysisResult(
                template_type=data.get("template_type", template_type),
                face_details=face_details,
                physical_traits=physical_traits,
                outfit=outfit,
                clothing_rules=data.get("clothing_rules"),
                style_notes=data.get("style_notes"),
                raw_description=content,
            )

        except json.JSONDecodeError:
            # Return raw content if JSON parsing fails
            return CharacterAnalysisResult(
                template_type=template_type,
                raw_description=result.content,
            )

    def suggest_outfit_description(
        self,
        part_type: str,
        style_hints: str = "",
        existing_parts: list[str] | None = None,
    ) -> list[str]:
        """
        Suggest descriptions for an outfit part.

        Args:
            part_type: Type of outfit part (vest, shirt, pants, etc.)
            style_hints: Optional style guidance
            existing_parts: Other parts in the outfit for coordination

        Returns:
            List of 3-5 description suggestions
        """
        existing_str = ""
        if existing_parts:
            existing_str = (
                "\n\nCoordinate with these existing items:\n- "
                + "\n- ".join(existing_parts)
            )

        prompt = f"""Suggest 3-5 descriptions for a {part_type} for character illustration.

Style hints: {style_hints or "professional, versatile"}{existing_str}

Each description should be:
- Specific enough for consistent image generation
- Include color, material, and style details
- 1-2 sentences max

Return ONLY a JSON array of strings:
["description 1", "description 2", "description 3"]"""

        agent = create_agent(self.agent_type, {"name": self.agent_type})
        result = agent.invoke(prompt)

        if not result.success:
            return [f"A {style_hints or 'professional'} {part_type}"]

        try:
            content = result.content.strip()
            if content.startswith("```"):
                lines = content.split("\n")
                content = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])
                if content.startswith("json"):
                    content = content[4:].strip()

            suggestions = json.loads(content)
            if isinstance(suggestions, list):
                return suggestions[:5]
        except json.JSONDecodeError:
            pass

        return [f"A {style_hints or 'professional'} {part_type}"]

    def generate_outfit(
        self,
        template_type: str,
        style: str = "professional",
        mood: str = "",
        count: int = 3,
        reference_outfits: list[dict] | None = None,
        parts_to_vary: list[str] | None = None,
        keep_parts: dict[str, str] | None = None,
    ) -> list[dict]:
        """
        Generate complete outfit suggestions with optional style references.

        Args:
            template_type: Character template (human_male, human_female, non_human)
            style: Overall style (professional, casual, creative, formal)
            mood: Optional mood/vibe
            count: Number of variations to generate
            reference_outfits: List of existing outfits to use as style reference
            parts_to_vary: Which parts to generate (empty/None = all parts)
            keep_parts: Dict of part_type -> description to keep unchanged

        Returns:
            List of outfit dictionaries with part descriptions
        """
        parts_by_template = {
            "human_male": ["shirt", "vest", "jacket", "pants", "shoes", "tie", "watch"],
            "human_female": [
                "blouse",
                "jacket",
                "skirt",
                "pants",
                "heels",
                "necklace",
                "earrings",
            ],
            "non_human": ["hat", "glasses", "scarf"],
        }

        all_parts = parts_by_template.get(
            template_type, parts_by_template["human_male"]
        )

        # Determine which parts to generate
        if parts_to_vary:
            parts_to_generate = [p for p in parts_to_vary if p in all_parts]
        else:
            parts_to_generate = all_parts

        # Build reference section if provided
        reference_section = ""
        if reference_outfits:
            reference_section = "\n\nSTYLE REFERENCE - Generate variations that maintain consistency with these existing outfits:\n"
            for i, ref in enumerate(reference_outfits, 1):
                reference_section += f"\nReference {i}: {ref.get('name', 'Unnamed')}"
                if ref.get("description"):
                    reference_section += f" - {ref['description']}"
                parts = ref.get("parts", {})
                if parts:
                    reference_section += "\n  Parts:"
                    for part_type, desc in parts.items():
                        if desc:
                            reference_section += f"\n    - {part_type}: {desc}"
            reference_section += "\n\nIMPORTANT: The generated outfits should match the overall aesthetic, color palette, and formality level of these references. Create variations, not duplicates."

        # Build keep parts section
        keep_section = ""
        if keep_parts:
            keep_section = "\n\nKEEP THESE PARTS EXACTLY AS SPECIFIED (include them in output unchanged):\n"
            for part_type, desc in keep_parts.items():
                keep_section += f"  - {part_type}: {desc}\n"

        parts_str = ", ".join(parts_to_generate)
        mood_str = f" with a {mood} vibe" if mood else ""

        prompt = f"""Generate {count} complete outfit variations for a {template_type} character illustration.

Style: {style}{mood_str}
Generate these parts: {parts_str}{reference_section}{keep_section}

Each outfit should be distinct and suitable for professional illustration.
Include specific colors, materials, and style details.

Return ONLY valid JSON array:
[
  {{
    "name": "Outfit Name",
    "description": "Brief overall description",
    "parts": {{
      "shirt": "description or null",
      "vest": "description or null",
      ...include all parts from the list above
    }}
  }}
]"""

        agent = create_agent(self.agent_type, {"name": self.agent_type})
        result = agent.invoke(prompt)

        if not result.success:
            return []

        try:
            content = result.content.strip()
            if content.startswith("```"):
                lines = content.split("\n")
                content = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])
                if content.startswith("json"):
                    content = content[4:].strip()

            outfits = json.loads(content)
            if isinstance(outfits, list):
                # Merge keep_parts into each generated outfit
                if keep_parts:
                    for outfit in outfits:
                        if "parts" in outfit:
                            for part_type, desc in keep_parts.items():
                                outfit["parts"][part_type] = desc
                return outfits[:count]
        except json.JSONDecodeError:
            pass

        return []


# Singleton instance
image_vision_service = ImageVisionService()
