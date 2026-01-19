"""Tests for agent implementations."""

import pytest
from unittest.mock import patch, MagicMock
import subprocess

from runner.agents import create_agent, ClaudeAgent, GeminiAgent, CodexAgent, OllamaAgent
from runner.models import TokenUsage


@pytest.fixture
def session_dir(tmp_path):
    return str(tmp_path / "sessions")


class TestAgentFactory:
    def test_create_claude_agent(self, session_dir):
        agent = create_agent("claude", {}, session_dir)
        assert isinstance(agent, ClaudeAgent)
        assert agent.name == "claude"

    def test_create_gemini_agent(self, session_dir):
        agent = create_agent("gemini", {}, session_dir)
        assert isinstance(agent, GeminiAgent)
        assert agent.name == "gemini"

    def test_create_codex_agent(self, session_dir):
        agent = create_agent("codex", {}, session_dir)
        assert isinstance(agent, CodexAgent)
        assert agent.name == "codex"

    def test_unknown_agent_raises(self, session_dir):
        with pytest.raises(ValueError, match="Unknown CLI agent"):
            create_agent("unknown", {}, session_dir)

    def test_create_ollama_agent(self, session_dir):
        agent = create_agent("ollama", {"name": "ollama"}, session_dir)
        assert isinstance(agent, OllamaAgent)
        assert agent.name == "ollama"
        assert agent.session_type == "file"


class TestClaudeAgent:
    def test_default_config(self, session_dir):
        agent = ClaudeAgent({}, session_dir)
        assert agent.context_window == 200000
        assert agent.cost_per_1k["input"] == 0.003
        assert agent.cost_per_1k["output"] == 0.015

    def test_parse_json_output(self, session_dir):
        agent = ClaudeAgent({}, session_dir)
        stdout = '{"result": "Hello world", "usage": {"input_tokens": 100, "output_tokens": 50}}'

        content, tokens = agent._parse_output(stdout)

        assert content == "Hello world"
        assert tokens.input_tokens == 100
        assert tokens.output_tokens == 50

    def test_parse_content_blocks(self, session_dir):
        agent = ClaudeAgent({}, session_dir)
        stdout = '{"content": [{"type": "text", "text": "Line 1"}, {"type": "text", "text": "Line 2"}], "usage": {"input_tokens": 10, "output_tokens": 5}}'

        content, tokens = agent._parse_output(stdout)

        assert "Line 1" in content
        assert "Line 2" in content

    def test_parse_invalid_json_returns_raw(self, session_dir):
        agent = ClaudeAgent({}, session_dir)
        stdout = "Not valid JSON"

        content, tokens = agent._parse_output(stdout)

        assert content == "Not valid JSON"
        assert tokens.input_tokens == 0

    def test_command_args_without_session(self, session_dir):
        agent = ClaudeAgent({}, session_dir)

        args = agent._get_command_args("Test prompt", use_session=False)

        assert args[0] == "claude"
        assert "--output-format" in args
        assert "json" in args
        assert "-p" in args
        assert "Test prompt" in args

    def test_command_args_with_session(self, session_dir):
        agent = ClaudeAgent({}, session_dir)
        agent.session_manager.session_id = "test-session"

        args = agent._get_command_args("Test prompt", use_session=True)

        assert "--resume" in args
        assert "test-session" in args

    def test_calculate_cost(self, session_dir):
        agent = ClaudeAgent({}, session_dir)
        tokens = TokenUsage(input_tokens=1000, output_tokens=500)

        cost = agent.calculate_cost(tokens)

        expected = (1000 / 1000) * 0.003 + (500 / 1000) * 0.015
        assert cost == pytest.approx(expected)

    def test_model_selection_in_args(self, session_dir):
        """Test that model config is included in command args."""
        agent = ClaudeAgent({"model": "opus"}, session_dir)

        args = agent._get_command_args("Test prompt", use_session=False)

        assert "--model" in args
        model_idx = args.index("--model")
        assert args[model_idx + 1] == "opus"

    def test_model_selection_with_session(self, session_dir):
        """Test that model config works with session resume."""
        agent = ClaudeAgent({"model": "haiku"}, session_dir)
        agent.session_manager.session_id = "test-session"

        args = agent._get_command_args("Test prompt", use_session=True)

        assert "--model" in args
        assert "--resume" in args
        assert "haiku" in args
        assert "test-session" in args

    def test_default_model_when_not_configured(self, session_dir):
        """Test that model flag defaults to 'sonnet' when not configured."""
        agent = ClaudeAgent({}, session_dir)

        args = agent._get_command_args("Test prompt", use_session=False)

        assert "--model" in args
        model_idx = args.index("--model")
        assert args[model_idx + 1] == "sonnet"


class TestGeminiAgent:
    def test_default_config(self, session_dir):
        agent = GeminiAgent({}, session_dir)
        assert agent.context_window == 1000000
        assert agent.cost_per_1k["input"] == 0.003  # Default "pro" tier pricing

    def test_parse_json_output(self, session_dir):
        agent = GeminiAgent({}, session_dir)
        stdout = '{"text": "Response text", "usageMetadata": {"promptTokenCount": 80, "candidatesTokenCount": 40}}'

        content, tokens = agent._parse_output(stdout)

        assert content == "Response text"
        assert tokens.input_tokens == 80
        assert tokens.output_tokens == 40

    def test_model_selection_in_args(self, session_dir):
        """Test that model config is included in command args."""
        agent = GeminiAgent({"model": "gemini-2.0-flash"}, session_dir)

        args = agent._get_command_args("Test prompt", use_session=False)

        assert "-m" in args
        model_idx = args.index("-m")
        assert args[model_idx + 1] == "gemini-2.0-flash"

    def test_no_model_when_not_configured(self, session_dir):
        """Test that model flag is omitted when not configured."""
        agent = GeminiAgent({}, session_dir)

        args = agent._get_command_args("Test prompt", use_session=False)

        assert "-m" not in args


class TestCodexAgent:
    def test_default_config(self, session_dir):
        agent = CodexAgent({}, session_dir)
        assert agent.context_window == 128000
        assert agent.cost_per_1k["output"] == 0.015

    def test_parse_json_output(self, session_dir):
        agent = CodexAgent({}, session_dir)
        stdout = '{"response": "Codex response", "usage": {"prompt_tokens": 60, "completion_tokens": 30}}'

        content, tokens = agent._parse_output(stdout)

        assert content == "Codex response"
        assert tokens.input_tokens == 60
        assert tokens.output_tokens == 30

    def test_model_selection_in_args(self, session_dir):
        """Test that model config is included in command args."""
        agent = CodexAgent({"model": "o3"}, session_dir)

        args = agent._get_command_args("Test prompt", use_session=False)

        assert "-m" in args
        model_idx = args.index("-m")
        assert args[model_idx + 1] == "o3"

    def test_no_model_when_not_configured(self, session_dir):
        """Test that model flag is omitted when not configured."""
        agent = CodexAgent({}, session_dir)

        args = agent._get_command_args("Test prompt", use_session=False)

        assert "-m" not in args


class TestCLIAgentExecution:
    @patch("subprocess.Popen")
    def test_successful_invocation(self, mock_popen, session_dir):
        mock_proc = MagicMock()
        mock_proc.communicate.return_value = (
            '{"result": "Success", "usage": {"input_tokens": 10, "output_tokens": 5}}',
            "",
        )
        mock_proc.returncode = 0
        mock_popen.return_value = mock_proc

        agent = ClaudeAgent({}, session_dir)
        result = agent.invoke("Test prompt")

        assert result.success
        assert result.content == "Success"
        assert result.tokens.total == 15

    @patch("subprocess.Popen")
    def test_failed_invocation(self, mock_popen, session_dir):
        mock_proc = MagicMock()
        mock_proc.communicate.return_value = ("", "Error: API key invalid")
        mock_proc.returncode = 1
        mock_popen.return_value = mock_proc

        agent = ClaudeAgent({}, session_dir)
        result = agent.invoke("Test prompt")

        assert not result.success
        assert "API key invalid" in result.error

    @patch("subprocess.Popen")
    def test_timeout_handling(self, mock_popen, session_dir):
        mock_proc = MagicMock()
        mock_proc.communicate.side_effect = subprocess.TimeoutExpired(
            cmd="claude", timeout=300
        )
        mock_proc.terminate = MagicMock()
        mock_proc.wait = MagicMock()
        mock_proc.kill = MagicMock()
        mock_popen.return_value = mock_proc

        agent = ClaudeAgent({"timeout": 300}, session_dir)
        result = agent.invoke("Test prompt")

        assert not result.success
        assert "Timeout" in result.error

    @patch("subprocess.Popen")
    def test_input_files_included_in_prompt(self, mock_popen, tmp_path, session_dir):
        test_file = tmp_path / "input.md"
        test_file.write_text("File content here")

        mock_proc = MagicMock()
        mock_proc.communicate.return_value = (
            '{"result": "Done", "usage": {"input_tokens": 20, "output_tokens": 10}}',
            "",
        )
        mock_proc.returncode = 0
        mock_popen.return_value = mock_proc

        agent = ClaudeAgent({}, session_dir)
        result = agent.invoke("Process this:", input_files=[str(test_file)])

        call_args = mock_popen.call_args[0][0]
        prompt_arg = call_args[-1]
        assert "File content here" in prompt_arg

    @patch("subprocess.Popen")
    def test_session_captured_on_first_call(self, mock_popen, session_dir):
        mock_proc = MagicMock()
        mock_proc.communicate.return_value = (
            '{"result": "Hi", "usage": {"input_tokens": 5, "output_tokens": 3}}\nSession ID: new-session-123',
            "",
        )
        mock_proc.returncode = 0
        mock_popen.return_value = mock_proc

        agent = ClaudeAgent({}, session_dir)
        result = agent.invoke_with_session("", "Hello")

        assert agent.session_manager.session_id == "new-session-123"
