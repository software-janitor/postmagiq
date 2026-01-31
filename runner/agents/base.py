"""Abstract base class for all agent implementations."""

from abc import ABC, abstractmethod
from typing import Optional, TYPE_CHECKING

from runner.models import AgentResult, TokenUsage

if TYPE_CHECKING:
    from runner.logging.dev_logger import DevLogger


class BaseAgent(ABC):
    """Abstract base for all agent implementations."""

    def __init__(self, config: dict):
        self.config = config
        self.name = config.get("name", "unknown")
        self.context_window = config.get("context_window", 100000)
        self.cost_per_1k = config.get("cost_per_1k", {"input": 0.0, "output": 0.0})

        # Dev logging (set externally when DEV_MODE is enabled)
        self._dev_logger: Optional["DevLogger"] = None
        self._current_run_id: Optional[str] = None
        self._current_state: Optional[str] = None

    def set_dev_logger(
        self,
        dev_logger: "DevLogger",
        run_id: str,
        state: str,
    ) -> None:
        """Set dev logger for request/response visibility.

        Args:
            dev_logger: DevLogger instance
            run_id: Current workflow run ID
            state: Current state name
        """
        self._dev_logger = dev_logger
        self._current_run_id = run_id
        self._current_state = state

    def clear_dev_logger(self) -> None:
        """Clear dev logger reference."""
        self._dev_logger = None
        self._current_run_id = None
        self._current_state = None

    @abstractmethod
    def invoke(
        self, prompt: str, input_files: Optional[list[str]] = None
    ) -> AgentResult:
        """One-shot invocation (stateless)."""
        pass

    @abstractmethod
    def invoke_with_session(
        self, session_id: str, prompt: str, input_files: Optional[list[str]] = None
    ) -> AgentResult:
        """Invocation with session context (stateful)."""
        pass

    @abstractmethod
    def extract_tokens(self, raw_response: str) -> TokenUsage:
        """Extract token counts from agent response."""
        pass

    @abstractmethod
    def supports_native_session(self) -> bool:
        """Does this agent have native session support?"""
        pass

    @property
    @abstractmethod
    def session_type(self) -> str:
        """'native', 'file', or 'none'."""
        pass

    def calculate_cost(self, tokens: TokenUsage) -> float:
        """Calculate cost in USD."""
        input_cost = (tokens.input_tokens / 1000) * self.cost_per_1k["input"]
        output_cost = (tokens.output_tokens / 1000) * self.cost_per_1k["output"]
        return input_cost + output_cost

    def calculate_context_usage(self, tokens: TokenUsage) -> dict:
        """Calculate context window usage."""
        total = tokens.total
        return {
            "max": self.context_window,
            "used": total,
            "percent": (total / self.context_window) * 100
            if self.context_window > 0
            else 0,
        }
