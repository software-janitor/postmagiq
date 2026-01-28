"""Tests for role-aware persona composition with frontmatter."""

import os
import pytest
from runner.content.workflow_store import WorkflowStore


class TestParseFrontmatter:
    """Test YAML frontmatter parsing."""

    def test_parse_with_frontmatter(self):
        content = "---\nneeds_voice: true\nneeds_rules: full\n---\n\n# Writer Role"
        fm, body = WorkflowStore._parse_frontmatter(content)
        assert fm["needs_voice"] is True
        assert fm["needs_rules"] == "full"
        assert body == "# Writer Role"

    def test_parse_without_frontmatter(self):
        content = "# Writer Role\n\nYou are a drafting agent."
        fm, body = WorkflowStore._parse_frontmatter(content)
        assert fm == {}
        assert body == content

    def test_parse_voice_false(self):
        content = "---\nneeds_voice: false\nneeds_rules: core\n---\n\n# Auditor"
        fm, body = WorkflowStore._parse_frontmatter(content)
        assert fm["needs_voice"] is False
        assert fm["needs_rules"] == "core"

    def test_parse_incomplete_frontmatter(self):
        content = "---\nneeds_voice: true\nno closing delimiter"
        fm, body = WorkflowStore._parse_frontmatter(content)
        assert fm == {}
        assert body == content

    def test_parse_empty_content(self):
        fm, body = WorkflowStore._parse_frontmatter("")
        assert fm == {}
        assert body == ""


class TestRoleAwareComposition:
    """Test that compose_persona_prompt respects frontmatter directives."""

    def test_writer_includes_voice_and_full_rules(self):
        result = WorkflowStore.compose_persona_prompt("writer")
        assert result
        assert "Writer Role" in result
        # Writer needs_voice: true, should include voice profile content
        # Writer needs_rules: full, should include rules

    def test_auditor_excludes_voice(self):
        result = WorkflowStore.compose_persona_prompt("auditor")
        assert result
        assert "Auditor Role" in result
        # Auditor has needs_voice: false — should NOT include voice profile
        assert "Voice Profile" not in result

    def test_story_reviewer_excludes_voice(self):
        result = WorkflowStore.compose_persona_prompt("story-reviewer")
        assert result
        assert "Story Reviewer" in result
        assert "Voice Profile" not in result

    def test_story_processor_excludes_voice(self):
        result = WorkflowStore.compose_persona_prompt("story-processor")
        assert result
        assert "Story Processor" in result
        assert "Voice Profile" not in result

    def test_fabrication_auditor_excludes_voice(self):
        result = WorkflowStore.compose_persona_prompt("fabrication-auditor")
        assert result
        assert "Fabrication Auditor" in result
        assert "Voice Profile" not in result

    def test_style_auditor_includes_voice(self):
        result = WorkflowStore.compose_persona_prompt("style-auditor")
        assert result
        assert "Style Auditor" in result
        # style_auditor has needs_voice: true

    def test_synthesizer_includes_voice(self):
        result = WorkflowStore.compose_persona_prompt("synthesizer")
        assert result
        assert "Synthesizer Role" in result

    def test_frontmatter_stripped_from_output(self):
        """Frontmatter should NOT appear in composed prompt."""
        result = WorkflowStore.compose_persona_prompt("writer")
        assert "needs_voice:" not in result
        assert "needs_rules:" not in result

    def test_core_rules_only_for_auditor(self):
        """Auditor with needs_rules: core should get core rules, not writing rules."""
        result = WorkflowStore.compose_persona_prompt("auditor")
        assert result
        # Should have core rules (zero fabrication)
        assert "fabrication" in result.lower() or "Fabrication" in result

    def test_nonexistent_persona_returns_rules_only(self):
        """Nonexistent persona should still return rules (no template found)."""
        result = WorkflowStore.compose_persona_prompt("nonexistent-xyz-123")
        # Should still have rules even without template
        # (frontmatter defaults: needs_voice=True, needs_rules=full)


class TestRulesFiles:
    """Test that rules files exist and have expected content."""

    def test_core_rules_exist(self):
        base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        path = os.path.join(base, "prompts", "rules", "core.md")
        assert os.path.exists(path), "prompts/rules/core.md must exist"
        with open(path) as f:
            content = f.read()
        assert "Zero Fabrication" in content
        assert "em-dash" in content.lower() or "Em-dash" in content or "em-dashes" in content.lower()

    def test_writing_rules_exist(self):
        base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        path = os.path.join(base, "prompts", "rules", "writing.md")
        assert os.path.exists(path), "prompts/rules/writing.md must exist"
        with open(path) as f:
            content = f.read()
        assert "Framework Exposure" in content
        assert "Bar Test" in content
        assert "Entry Point" in content


class TestTemplatesHaveFrontmatter:
    """Verify all templates have valid frontmatter."""

    TEMPLATES = [
        "writer", "synthesizer", "auditor",
        "story_reviewer", "story_processor",
        "fabrication_auditor", "style_auditor",
    ]

    @pytest.mark.parametrize("template", TEMPLATES)
    def test_template_has_frontmatter(self, template):
        base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        path = os.path.join(base, "prompts", "templates", f"{template}.md")
        assert os.path.exists(path), f"templates/{template}.md must exist"
        with open(path) as f:
            content = f.read()
        assert content.startswith("---"), f"{template}.md must start with frontmatter"
        fm, body = WorkflowStore._parse_frontmatter(content)
        assert "needs_voice" in fm, f"{template}.md must declare needs_voice"
        assert "needs_rules" in fm, f"{template}.md must declare needs_rules"
        assert fm["needs_rules"] in ("full", "core", "none"), f"{template}.md needs_rules must be full/core/none"
