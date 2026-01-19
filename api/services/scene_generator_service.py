"""Service for AI-powered scene generation."""

import json
from typing import Optional

from runner.agents import create_agent


class SceneGeneratorService:
    """Service for generating scene descriptions using AI."""

    def __init__(self, agent_type: str = "gemini"):
        self.agent_type = agent_type

    def generate_scenes(
        self,
        sentiment: str,
        count: int = 5,
        themes: list[str] | None = None,
        context: str = "software",
    ) -> list[dict]:
        """
        Generate multiple scene descriptions.

        Args:
            sentiment: Scene sentiment (SUCCESS, FAILURE, UNRESOLVED, etc.)
            count: Number of scenes to generate
            themes: Optional theme hints (debugging, deployment, etc.)
            context: software or hardware context

        Returns:
            List of scene dictionaries with name, description, viewpoint
        """
        themes_str = ""
        if themes:
            themes_str = f"\nTheme hints: {', '.join(themes)}"

        context_details = ""
        if context == "hardware":
            context_details = "\nContext: Hardware/embedded development - include physical components, circuits, oscilloscopes, etc."
        else:
            context_details = "\nContext: Software development - coding, debugging, deployments, etc."

        prompt = f"""Generate {count} distinct scene descriptions for illustration.

Sentiment: {sentiment}
- SUCCESS: Achievement, celebration, breakthrough moments
- FAILURE: Frustration, crisis, debugging struggles
- UNRESOLVED: Uncertainty, weighing tradeoffs, deliberation
{themes_str}{context_details}

Each scene should be:
- Specific enough for consistent illustration generation
- Focused on a single moment or situation
- Include environmental details
- 2-3 sentences describing the visual scene

Return ONLY valid JSON array:
[
  {{
    "code": "SHORT_CODE",
    "name": "Scene Name",
    "description": "Detailed scene description...",
    "viewpoint": "standard|close_up|wide|over_shoulder"
  }}
]

Code format: {sentiment[:3].upper()}_KEYWORD (e.g., SUC_DEPLOY, FAI_DEBUG)"""

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

            scenes = json.loads(content)
            if isinstance(scenes, list):
                return scenes[:count]
        except json.JSONDecodeError:
            pass

        return []

    def generate_scene_variations(
        self,
        original_scene: dict,
        count: int = 3,
        vary: list[str] | None = None,
    ) -> list[dict]:
        """
        Generate variations of an existing scene.

        Args:
            original_scene: The scene to create variations of
            count: Number of variations
            vary: What to vary (viewpoint, props, mood)

        Returns:
            List of scene variation dictionaries
        """
        vary_str = ""
        if vary:
            vary_str = f"\nVary these aspects: {', '.join(vary)}"
        else:
            vary_str = "\nVary: viewpoint, specific details, props visible"

        prompt = f"""Generate {count} variations of this scene:

Original:
- Name: {original_scene.get('name', 'Scene')}
- Description: {original_scene.get('description', '')}
- Sentiment: {original_scene.get('sentiment', 'UNRESOLVED')}
- Viewpoint: {original_scene.get('viewpoint', 'standard')}
{vary_str}

Keep the same sentiment and core concept, but change the specified aspects.

Return ONLY valid JSON array:
[
  {{
    "code": "SHORT_CODE",
    "name": "Variation Name",
    "description": "Detailed variation description...",
    "viewpoint": "standard|close_up|wide|over_shoulder"
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

            variations = json.loads(content)
            if isinstance(variations, list):
                return variations[:count]
        except json.JSONDecodeError:
            pass

        return []

    def preview_scene_prompt(
        self,
        scene: dict,
        characters: list[dict] | None = None,
        outfit_override: dict | None = None,
    ) -> str:
        """
        Generate a preview of the full image prompt for a scene.

        Args:
            scene: Scene dictionary with description
            characters: List of characters with their details
            outfit_override: Optional outfit to use instead of default

        Returns:
            Combined prompt string showing what will be generated
        """
        parts = []

        # Scene description
        parts.append(f"SCENE: {scene.get('description', '')}")
        parts.append(f"VIEWPOINT: {scene.get('viewpoint', 'standard')}")

        # Character descriptions
        if characters:
            for char in characters:
                char_parts = [f"CHARACTER: {char.get('name', 'Character')}"]

                # Face details
                face_details = []
                if char.get('skin_tone'):
                    face_details.append(f"skin: {char['skin_tone']}")
                if char.get('face_shape'):
                    face_details.append(f"face: {char['face_shape']}")
                if char.get('eye_details'):
                    face_details.append(f"eyes: {char['eye_details']}")
                if char.get('hair_details'):
                    face_details.append(f"hair: {char['hair_details']}")
                if face_details:
                    char_parts.append(f"  Face: {', '.join(face_details)}")

                # Physical traits
                if char.get('physical_traits'):
                    char_parts.append(f"  Build: {char['physical_traits']}")

                # Clothing rules
                if char.get('clothing_rules'):
                    char_parts.append(f"  Clothing rules: {char['clothing_rules']}")

                parts.append("\n".join(char_parts))

        # Outfit override
        if outfit_override:
            outfit_parts = []
            for part_type, description in outfit_override.items():
                if description:
                    outfit_parts.append(f"  {part_type}: {description}")
            if outfit_parts:
                parts.append("OUTFIT:\n" + "\n".join(outfit_parts))

        return "\n\n".join(parts)


# Singleton instance
scene_generator_service = SceneGeneratorService()
