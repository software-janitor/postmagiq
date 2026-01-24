"""Tests for ImageVisionService."""

import pytest
import json
import base64
from unittest.mock import patch, MagicMock

from api.services.image_vision_service import (
    ImageVisionService,
    CharacterAnalysisResult,
    FaceDetails,
    OutfitAnalysis,
    PhysicalTraits,
)
from runner.models import AgentResult, TokenUsage


@pytest.fixture
def service():
    return ImageVisionService(agent_type="gemini")


@pytest.fixture
def sample_image_bytes():
    # Minimal 1x1 PNG (smallest valid PNG)
    return base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
    )


class TestCharacterAnalysis:
    def test_successful_human_analysis(self, service, sample_image_bytes):
        """Test analyzing a human character image."""
        mock_response = json.dumps({
            "template_type": "human_male",
            "face_details": {
                "skin_tone": "warm olive",
                "face_shape": "oval",
                "eye_details": "brown eyes, tired expression",
                "hair_details": "short dark hair, graying at temples",
                "facial_hair": "stubble",
                "distinguishing_features": "small scar on chin"
            },
            "physical_traits": {
                "body_type": "athletic",
                "posture": "relaxed",
                "height_impression": "average"
            },
            "outfit": {
                "vest": "charcoal gray wool vest",
                "shirt": "white cotton button-up",
                "pants": "dark navy chinos",
                "shoes": "brown leather oxford shoes"
            },
            "clothing_rules": "Vest always buttoned. Shirt collar open. Sleeves rolled to forearms.",
            "style_notes": "Professional but approachable"
        })

        with patch("api.services.image_vision_service.create_agent") as mock_create:
            mock_agent = MagicMock()
            mock_agent.invoke.return_value = AgentResult(
                success=True,
                content=mock_response,
                tokens=TokenUsage(input_tokens=100, output_tokens=50),
            )
            mock_create.return_value = mock_agent

            result = service.analyze_character_image(
                sample_image_bytes,
                template_type="human_male",
            )

            assert result.template_type == "human_male"
            assert result.face_details is not None
            assert result.face_details.skin_tone == "warm olive"
            assert result.outfit is not None
            assert result.outfit.vest == "charcoal gray wool vest"
            assert "Vest always buttoned" in result.clothing_rules

    def test_successful_nonhuman_analysis(self, service, sample_image_bytes):
        """Test analyzing a non-human character image."""
        mock_response = json.dumps({
            "template_type": "non_human",
            "face_details": None,
            "physical_traits": {
                "materials": "brushed aluminum and carbon fiber",
                "colors": "silver with cyan accents",
                "mechanical_features": "articulated joints, LED panel eyes",
                "expression_system": "LED color changes and antenna position",
                "distinctive_elements": "glowing chest panel, antenna ears"
            },
            "outfit": None,
            "clothing_rules": None,
            "style_notes": "Friendly robot companion"
        })

        with patch("api.services.image_vision_service.create_agent") as mock_create:
            mock_agent = MagicMock()
            mock_agent.invoke.return_value = AgentResult(
                success=True,
                content=mock_response,
                tokens=TokenUsage(input_tokens=100, output_tokens=50),
            )
            mock_create.return_value = mock_agent

            result = service.analyze_character_image(
                sample_image_bytes,
                template_type="non_human",
            )

            assert result.template_type == "non_human"
            assert result.face_details is None
            assert result.physical_traits is not None
            assert "brushed aluminum" in result.physical_traits.materials

    def test_handles_json_in_code_block(self, service, sample_image_bytes):
        """Test parsing JSON wrapped in markdown code blocks."""
        mock_response = """```json
{
    "template_type": "human_female",
    "face_details": {"skin_tone": "light", "face_shape": "oval"},
    "physical_traits": null,
    "outfit": null,
    "clothing_rules": null,
    "style_notes": null
}
```"""

        with patch("api.services.image_vision_service.create_agent") as mock_create:
            mock_agent = MagicMock()
            mock_agent.invoke.return_value = AgentResult(
                success=True,
                content=mock_response,
                tokens=TokenUsage(input_tokens=100, output_tokens=50),
            )
            mock_create.return_value = mock_agent

            result = service.analyze_character_image(
                sample_image_bytes,
                template_type="human_female",
            )

            assert result.template_type == "human_female"
            assert result.face_details.skin_tone == "light"

    def test_handles_agent_failure(self, service, sample_image_bytes):
        """Test graceful handling of agent failure."""
        with patch("api.services.image_vision_service.create_agent") as mock_create:
            mock_agent = MagicMock()
            mock_agent.invoke.return_value = AgentResult(
                success=False,
                content="",
                error="API timeout",
                tokens=TokenUsage(input_tokens=0, output_tokens=0),
            )
            mock_create.return_value = mock_agent

            result = service.analyze_character_image(
                sample_image_bytes,
                template_type="human_male",
            )

            assert result.template_type == "human_male"
            assert "Analysis failed" in result.raw_description

    def test_handles_invalid_json(self, service, sample_image_bytes):
        """Test graceful handling of invalid JSON response."""
        with patch("api.services.image_vision_service.create_agent") as mock_create:
            mock_agent = MagicMock()
            mock_agent.invoke.return_value = AgentResult(
                success=True,
                content="This is not valid JSON at all",
                tokens=TokenUsage(input_tokens=100, output_tokens=50),
            )
            mock_create.return_value = mock_agent

            result = service.analyze_character_image(
                sample_image_bytes,
                template_type="human_male",
            )

            assert result.template_type == "human_male"
            assert result.raw_description == "This is not valid JSON at all"

    def test_base64_encoding_in_prompt(self, service, sample_image_bytes):
        """Test that image is properly base64 encoded in prompt."""
        with patch("api.services.image_vision_service.create_agent") as mock_create:
            mock_agent = MagicMock()
            mock_agent.invoke.return_value = AgentResult(
                success=True,
                content='{"template_type": "human_male"}',
                tokens=TokenUsage(input_tokens=100, output_tokens=50),
            )
            mock_create.return_value = mock_agent

            service.analyze_character_image(sample_image_bytes)

            # Check the prompt contains base64 data
            call_args = mock_agent.invoke.call_args[0][0]
            assert "data:image/png;base64," in call_args


class TestOutfitSuggestions:
    def test_suggest_outfit_description(self, service):
        """Test generating outfit part suggestions."""
        mock_response = json.dumps([
            "Navy blue wool vest with brass buttons",
            "Charcoal gray herringbone vest",
            "Black cotton vest with subtle pinstripe"
        ])

        with patch("api.services.image_vision_service.create_agent") as mock_create:
            mock_agent = MagicMock()
            mock_agent.invoke.return_value = AgentResult(
                success=True,
                content=mock_response,
                tokens=TokenUsage(input_tokens=50, output_tokens=30),
            )
            mock_create.return_value = mock_agent

            suggestions = service.suggest_outfit_description(
                part_type="vest",
                style_hints="professional, classic"
            )

            assert len(suggestions) == 3
            assert "Navy blue wool vest" in suggestions[0]

    def test_suggest_with_existing_parts(self, service):
        """Test coordination with existing outfit parts."""
        mock_response = json.dumps([
            "White cotton oxford shirt",
            "Light blue chambray button-down"
        ])

        with patch("api.services.image_vision_service.create_agent") as mock_create:
            mock_agent = MagicMock()
            mock_agent.invoke.return_value = AgentResult(
                success=True,
                content=mock_response,
                tokens=TokenUsage(input_tokens=50, output_tokens=30),
            )
            mock_create.return_value = mock_agent

            suggestions = service.suggest_outfit_description(
                part_type="shirt",
                existing_parts=["charcoal vest", "navy pants"]
            )

            # Check that existing parts were included in prompt
            call_args = mock_agent.invoke.call_args[0][0]
            assert "charcoal vest" in call_args
            assert "navy pants" in call_args

    def test_fallback_on_failure(self, service):
        """Test fallback suggestion when agent fails."""
        with patch("api.services.image_vision_service.create_agent") as mock_create:
            mock_agent = MagicMock()
            mock_agent.invoke.return_value = AgentResult(
                success=False,
                content="",
                error="API error",
                tokens=TokenUsage(input_tokens=0, output_tokens=0),
            )
            mock_create.return_value = mock_agent

            suggestions = service.suggest_outfit_description(
                part_type="vest",
                style_hints="casual"
            )

            assert len(suggestions) == 1
            assert "casual" in suggestions[0]
            assert "vest" in suggestions[0]


class TestOutfitGeneration:
    def test_generate_complete_outfits(self, service):
        """Test generating complete outfit variations."""
        mock_response = json.dumps([
            {
                "name": "Conference Speaker",
                "description": "Professional but approachable",
                "parts": {
                    "shirt": "White cotton button-up",
                    "vest": "Navy wool vest",
                    "pants": "Charcoal wool trousers",
                    "shoes": "Brown leather oxfords"
                }
            },
            {
                "name": "Casual Friday",
                "description": "Relaxed professional",
                "parts": {
                    "shirt": "Light blue chambray",
                    "vest": None,
                    "pants": "Dark denim jeans",
                    "shoes": "White leather sneakers"
                }
            }
        ])

        with patch("api.services.image_vision_service.create_agent") as mock_create:
            mock_agent = MagicMock()
            mock_agent.invoke.return_value = AgentResult(
                success=True,
                content=mock_response,
                tokens=TokenUsage(input_tokens=80, output_tokens=60),
            )
            mock_create.return_value = mock_agent

            outfits = service.generate_outfit(
                template_type="human_male",
                style="professional",
                count=2
            )

            assert len(outfits) == 2
            assert outfits[0]["name"] == "Conference Speaker"
            assert outfits[0]["parts"]["vest"] == "Navy wool vest"

    def test_generate_female_outfits(self, service):
        """Test generating female outfit variations."""
        mock_response = json.dumps([
            {
                "name": "Executive Meeting",
                "description": "Polished and confident",
                "parts": {
                    "blouse": "Silk cream blouse",
                    "jacket": "Black tailored blazer",
                    "skirt": "Charcoal pencil skirt",
                    "heels": "Black leather pumps"
                }
            }
        ])

        with patch("api.services.image_vision_service.create_agent") as mock_create:
            mock_agent = MagicMock()
            mock_agent.invoke.return_value = AgentResult(
                success=True,
                content=mock_response,
                tokens=TokenUsage(input_tokens=80, output_tokens=60),
            )
            mock_create.return_value = mock_agent

            outfits = service.generate_outfit(
                template_type="human_female",
                style="formal",
                count=1
            )

            # Check that female parts were requested
            call_args = mock_agent.invoke.call_args[0][0]
            assert "blouse" in call_args
            assert "heels" in call_args

    def test_empty_on_failure(self, service):
        """Test empty result when agent fails."""
        with patch("api.services.image_vision_service.create_agent") as mock_create:
            mock_agent = MagicMock()
            mock_agent.invoke.return_value = AgentResult(
                success=False,
                content="",
                error="API error",
                tokens=TokenUsage(input_tokens=0, output_tokens=0),
            )
            mock_create.return_value = mock_agent

            outfits = service.generate_outfit(
                template_type="human_male",
                style="casual"
            )

            assert outfits == []


class TestPydanticModels:
    def test_face_details_optional_fields(self):
        """Test FaceDetails with partial data."""
        details = FaceDetails(skin_tone="light", eye_details="blue eyes")
        assert details.skin_tone == "light"
        assert details.face_shape is None

    def test_outfit_analysis_optional_fields(self):
        """Test OutfitAnalysis with partial data."""
        outfit = OutfitAnalysis(vest="gray vest", shirt="white shirt")
        assert outfit.vest == "gray vest"
        assert outfit.pants is None
        assert outfit.dress is None

    def test_character_analysis_result_minimal(self):
        """Test CharacterAnalysisResult with minimal data."""
        result = CharacterAnalysisResult(template_type="human_male")
        assert result.template_type == "human_male"
        assert result.face_details is None
        assert result.outfit is None
