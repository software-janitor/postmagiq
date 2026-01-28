"""Ollama agent with GPU-aware model selection and file-based sessions."""

import os
import time
from typing import Optional, TYPE_CHECKING

import requests

from runner.agents.base import BaseAgent
from runner.agents.gpu_detect import detect_gpu, get_model_tier, GPUInfo
from runner.models import AgentResult, TokenUsage
from runner.sessions.file_based import FileBasedSessionManager

if TYPE_CHECKING:
    from runner.logging.dev_logger import DevLogger


# Model tier configurations
# These map GPU VRAM ranges to recommended models for different tasks
MODEL_TIERS = {
    "tier_cpu": {
        "vram_range": (0, 6),
        "models": {
            "writer": "phi3:mini",
            "auditor": "phi3:mini",
            "coder": "qwen2.5-coder:1.5b",
        },
        "fallback": "tinyllama",
        "max_context": 4096,
    },
    "tier_8gb": {
        "vram_range": (6, 10),
        "models": {
            "writer": "llama3.2:8b",
            "auditor": "mistral:7b",
            "coder": "deepseek-coder:6.7b",
        },
        "fallback": "phi3:mini",
        "max_context": 8192,
    },
    "tier_16gb": {
        "vram_range": (12, 18),
        "models": {
            "writer": "llama3.1:13b",
            "auditor": "llama3.1:13b",
            "coder": "deepseek-coder:6.7b",
        },
        "fallback": "llama3.2:8b",
        "max_context": 32768,
    },
    "tier_24gb": {
        "vram_range": (20, 26),
        "models": {
            "writer": "llama3.1:70b-q4_K_M",
            "auditor": "llama3.1:70b-q4_K_M",
            "coder": "deepseek-coder:33b",
        },
        "fallback": "llama3.1:13b",
        "max_context": 65536,
    },
    "tier_48gb": {
        "vram_range": (40, 100),
        "models": {
            "writer": "llama3.1:70b",
            "auditor": "llama3.1:70b",
            "coder": "deepseek-coder:33b",
        },
        "fallback": "llama3.1:70b-q4_K_M",
        "max_context": 131072,
    },
}


class OllamaAgent(BaseAgent):
    """Agent using Ollama HTTP API with GPU-aware model selection.

    Features:
    - Auto-detects GPU and selects appropriate model tier
    - File-based session persistence for multi-turn conversations
    - Automatic model pulling if model not available
    - Persona-aware model selection (writer vs auditor vs coder)
    """

    def __init__(
        self,
        config: dict,
        session_dir: str = "workflow/sessions",
    ):
        """Initialize Ollama agent.

        Args:
            config: Agent configuration dict
            session_dir: Directory for session files
        """
        super().__init__(config)
        self.host = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
        self.timeout = config.get("timeout", 300)
        self.cost_per_1k = {"input": 0.0, "output": 0.0}  # Local = free

        # GPU detection and tier selection
        self.gpu_info = detect_gpu()
        self.tier = get_model_tier(self.gpu_info)
        self.tier_config = MODEL_TIERS.get(self.tier, MODEL_TIERS["tier_cpu"])

        # Use model from config if specified, otherwise use tier default
        self.model = config.get("model") or self.tier_config["models"].get(
            "writer", "llama3.2"
        )

        # Context window: config override > per-model config > tier default
        models_config = config.get("models", {})
        model_config = models_config.get(self.model, {})
        self.context_window = (
            model_config.get("context_window")
            or config.get("context_window")
            or self.tier_config["max_context"]
        )

        # File-based session manager
        self.session_manager = FileBasedSessionManager(
            session_dir, max_messages=config.get("max_session_messages", 50)
        )

        # Auto-pull setting
        self.auto_pull = config.get("auto_pull", True)

    def get_model_for_persona(
        self, persona: str, model_tier: Optional[str] = None
    ) -> str:
        """Get appropriate model for persona type.

        Args:
            persona: Persona name (unused, kept for backward compatibility)
            model_tier: Model tier from database ("writer", "auditor", "coder").
                       Defaults to "writer" if not provided.

        Returns:
            Model name appropriate for the tier
        """
        # Use explicit model_tier from database, default to "writer"
        tier = model_tier if model_tier in self.tier_config["models"] else "writer"
        return self.tier_config["models"].get(tier, self.model)

    def invoke(
        self, prompt: str, input_files: Optional[list[str]] = None,
        json_mode: bool = None
    ) -> AgentResult:
        """One-shot invocation without session context.

        Args:
            prompt: The prompt to send
            input_files: Optional list of files to include as context
            json_mode: If True, force JSON output format. If None, auto-detect from prompt.

        Returns:
            AgentResult with response and metadata
        """
        # Auto-detect JSON mode if not explicitly set
        if json_mode is None:
            json_mode = self._should_use_json_mode(prompt)
        return self._invoke_internal(prompt, input_files, use_session=False, json_mode=json_mode)

    def _should_use_json_mode(self, prompt: str) -> bool:
        """Detect if prompt requires JSON output.

        Looks for indicators that the persona expects JSON output format.
        """
        json_indicators = [
            "Return ONLY valid JSON",
            "Output Format",
            '{"score":',
            '"decision":',
            "Required fields:",
            "# Auditor Persona",
            "# Story Reviewer Persona",
            "output_type: review",
        ]
        return any(indicator in prompt for indicator in json_indicators)

    def invoke_with_session(
        self,
        session_id: str,
        prompt: str,
        input_files: Optional[list[str]] = None,
        json_mode: bool = False,
    ) -> AgentResult:
        """Invocation with session context.

        Maintains conversation history across multiple calls.

        Args:
            session_id: Session identifier
            prompt: The prompt to send
            input_files: Optional list of files to include as context
            json_mode: If True, force JSON output format

        Returns:
            AgentResult with response and metadata
        """
        # Load or create session
        if not self.session_manager.load_session(session_id):
            self.session_manager.create_session(session_id)

        return self._invoke_internal(prompt, input_files, use_session=True, json_mode=json_mode)

    def _invoke_internal(
        self,
        prompt: str,
        input_files: Optional[list[str]],
        use_session: bool,
        json_mode: bool = False,
    ) -> AgentResult:
        """Internal invocation logic.

        Args:
            prompt: The prompt to send
            input_files: Optional list of files to include
            use_session: Whether to use session context
            json_mode: If True, force JSON output format

        Returns:
            AgentResult with response and metadata
        """
        start_time = time.time()

        # Build context from input files
        context = ""
        if input_files:
            for file_path in input_files:
                try:
                    with open(file_path) as f:
                        context += f"\n\n--- {file_path} ---\n{f.read()}"
                except Exception as e:
                    context += f"\n\n--- {file_path} ---\n[Error reading file: {e}]"

        full_prompt = f"{context}\n\n{prompt}" if context else prompt

        # Build messages for chat API
        # Split prompt into system (persona/instructions) and user (task/input) messages
        messages = []
        system_content = None
        user_content = full_prompt

        # Look for content markers as the split point
        # Everything before is system instructions, everything after is user input
        for marker in ["## Input Files", "## Reviewer Context", "## USER FEEDBACK", "## Context", "## File:"]:
            if marker in full_prompt:
                idx = full_prompt.find(marker)
                system_content = full_prompt[:idx].strip()
                user_content = full_prompt[idx:].strip()
                break

        if use_session:
            messages = self.session_manager.get_context_for_ollama()

        # Add system message if we extracted persona instructions
        if system_content and not any(m.get("role") == "system" for m in messages):
            messages.insert(0, {"role": "system", "content": system_content})

        messages.append({"role": "user", "content": user_content})

        # Extract system and user messages for dev logging
        system_prompt = None
        user_message_parts = []
        for m in messages:
            if m.get("role") == "system":
                system_prompt = m.get("content", "")
            elif m.get("role") == "user":
                user_message_parts.append(m.get("content", ""))
        user_message_combined = "\n\n".join(user_message_parts)

        # Dev logging: log request before API call
        if self._dev_logger and self._current_run_id and self._current_state:
            self._dev_logger.log_llm_request(
                run_id=self._current_run_id,
                state=self._current_state,
                agent=self.name,
                model=self.model,
                system_prompt=system_prompt,
                user_message=user_message_combined,
                context_window=self.context_window,
            )

        try:
            # Ensure model is available
            if self.auto_pull and not self._ensure_model_available(self.model):
                error_msg = f"Model {self.model} not available and could not be pulled"
                # Dev logging: log error
                if self._dev_logger and self._current_run_id and self._current_state:
                    self._dev_logger.log_llm_response(
                        run_id=self._current_run_id,
                        state=self._current_state,
                        agent=self.name,
                        model=self.model,
                        content="",
                        input_tokens=0,
                        output_tokens=0,
                        duration_ms=int((time.time() - start_time) * 1000),
                        context_window=self.context_window,
                        success=False,
                        error=error_msg,
                    )
                return AgentResult(
                    success=False,
                    content="",
                    tokens=TokenUsage(input_tokens=0, output_tokens=0),
                    duration_s=time.time() - start_time,
                    error=error_msg,
                )

            # Use chat API for proper multi-turn support
            request_body = {
                "model": self.model,
                "messages": messages,
                "stream": False,
            }
            # Force JSON output format if requested
            if json_mode:
                request_body["format"] = "json"

            response = requests.post(
                f"{self.host}/api/chat",
                json=request_body,
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json()

            duration = time.time() - start_time
            content = data.get("message", {}).get("content", "")

            # Extract token counts
            tokens = TokenUsage(
                input_tokens=data.get("prompt_eval_count", 0),
                output_tokens=data.get("eval_count", 0),
            )

            # Dev logging: log successful response
            if self._dev_logger and self._current_run_id and self._current_state:
                self._dev_logger.log_llm_response(
                    run_id=self._current_run_id,
                    state=self._current_state,
                    agent=self.name,
                    model=self.model,
                    content=content,
                    input_tokens=tokens.input_tokens,
                    output_tokens=tokens.output_tokens,
                    duration_ms=int(duration * 1000),
                    context_window=self.context_window,
                    success=True,
                )

            # Save to session if using sessions
            if use_session:
                self.session_manager.add_message("user", full_prompt)
                self.session_manager.add_message(
                    "assistant",
                    content,
                    {
                        "input": tokens.input_tokens,
                        "output": tokens.output_tokens,
                        "total": tokens.total,
                    },
                )

            return AgentResult(
                success=True,
                content=content,
                tokens=tokens,
                duration_s=duration,
                cost_usd=0.0,
                session_id=self.session_manager.get_session_id()
                if use_session
                else None,
            )

        except requests.exceptions.Timeout:
            error_msg = f"Ollama request timed out after {self.timeout}s"
            duration = time.time() - start_time
            # Dev logging: log timeout error
            if self._dev_logger and self._current_run_id and self._current_state:
                self._dev_logger.log_llm_response(
                    run_id=self._current_run_id,
                    state=self._current_state,
                    agent=self.name,
                    model=self.model,
                    content="",
                    input_tokens=0,
                    output_tokens=0,
                    duration_ms=int(duration * 1000),
                    context_window=self.context_window,
                    success=False,
                    error=error_msg,
                )
            return AgentResult(
                success=False,
                content="",
                tokens=TokenUsage(input_tokens=0, output_tokens=0),
                duration_s=duration,
                error=error_msg,
            )
        except requests.exceptions.RequestException as e:
            error_msg = f"Ollama request failed: {e}"
            duration = time.time() - start_time
            # Dev logging: log request error
            if self._dev_logger and self._current_run_id and self._current_state:
                self._dev_logger.log_llm_response(
                    run_id=self._current_run_id,
                    state=self._current_state,
                    agent=self.name,
                    model=self.model,
                    content="",
                    input_tokens=0,
                    output_tokens=0,
                    duration_ms=int(duration * 1000),
                    context_window=self.context_window,
                    success=False,
                    error=error_msg,
                )
            return AgentResult(
                success=False,
                content="",
                tokens=TokenUsage(input_tokens=0, output_tokens=0),
                duration_s=duration,
                error=error_msg,
            )

    def _ensure_model_available(self, model_name: str) -> bool:
        """Check if model is available, pull if not.

        Args:
            model_name: Name of model to check/pull

        Returns:
            True if model is available, False otherwise
        """
        available = self.list_models()

        # Check if exact match or base name match
        base_name = model_name.split(":")[0]
        for m in available:
            if m == model_name or m.startswith(base_name + ":"):
                return True

        # Try to pull model
        return self.pull_model(model_name)

    def list_models(self) -> list[str]:
        """List available models from Ollama.

        Returns:
            List of available model names
        """
        try:
            response = requests.get(f"{self.host}/api/tags", timeout=10)
            response.raise_for_status()
            data = response.json()
            return [m["name"] for m in data.get("models", [])]
        except Exception:
            return []

    def pull_model(self, model_name: str) -> bool:
        """Pull model from Ollama registry.

        Args:
            model_name: Name of model to pull

        Returns:
            True if pull succeeded, False otherwise
        """
        try:
            response = requests.post(
                f"{self.host}/api/pull",
                json={"name": model_name},
                timeout=600,  # Models can be large
                stream=True,
            )
            response.raise_for_status()
            # Consume stream to complete download
            for _ in response.iter_lines():
                pass
            return True
        except Exception:
            return False

    def extract_tokens(self, raw_response: str) -> TokenUsage:
        """Extract tokens from raw response.

        Not used for HTTP API - tokens extracted directly from response.

        Args:
            raw_response: Raw response string (unused)

        Returns:
            Empty TokenUsage
        """
        return TokenUsage(input_tokens=0, output_tokens=0)

    def supports_native_session(self) -> bool:
        """Check if agent has native session support.

        Returns:
            False - Ollama uses file-based sessions
        """
        return False

    @property
    def session_type(self) -> str:
        """Get session type.

        Returns:
            "file" - uses file-based session persistence
        """
        return "file"

    def get_gpu_info(self) -> dict:
        """Get GPU detection results.

        Returns:
            Dict with GPU info and model selection details
        """
        return {
            "vendor": self.gpu_info.vendor,
            "vram_gb": round(self.gpu_info.vram_gb, 1),
            "name": self.gpu_info.name,
            "tier": self.tier,
            "model": self.model,
            "context_window": self.context_window,
        }

    def set_model_for_persona(
        self, persona: str, model_tier: Optional[str] = None
    ) -> None:
        """Set the model based on persona.

        Args:
            persona: Persona name to use for model selection
            model_tier: Optional explicit model tier from database
        """
        self.model = self.get_model_for_persona(persona, model_tier)
