"""Circuit breaker for preventing infinite loops and runaway costs."""

import time
from collections import defaultdict


class CircuitBreaker:
    """Rule-based circuit breaker. No LLM decisions here.

    Tracks state visits, transitions, time, and cost.
    Triggers a break when any rule condition is met.
    """

    def __init__(self, config: dict):
        rules_config = config.get("circuit_breaker", {})
        self.rules = rules_config.get("rules", [])
        self.safety_limits = rules_config.get("safety_limits", {})

        self.state_visit_limit = 3
        self.transition_limit = 20
        self.timeout_seconds = 1800
        self.cost_limit = 5.00

        for rule in self.rules:
            if rule.get("name") == "state_visit_limit":
                self.state_visit_limit = rule.get("limit", 3)
            elif rule.get("name") == "transition_limit":
                self.transition_limit = rule.get("limit", 20)
            elif rule.get("name") == "timeout":
                self.timeout_seconds = rule.get("seconds", 1800)
            elif rule.get("name") == "cost_limit":
                self.cost_limit = rule.get("limit", 5.00)

        self.state_visits: dict[str, int] = defaultdict(int)
        self.transition_history: list[tuple[str, str]] = []
        self.transition_count = 0
        self.start_time = time.time()
        self.total_cost = 0.0

    def check(self, from_state: str, to_state: str) -> dict:
        """Check rules. Returns break info if triggered."""
        self.state_visits[to_state] += 1
        self.transition_count += 1
        self.transition_history.append((from_state, to_state))

        if self._check_state_visit_limit(to_state):
            return self._build_break_response("state_visit_limit")

        if self._check_cycle_detection():
            return self._build_break_response("cycle_detection")

        if self._check_transition_limit():
            return self._build_break_response("transition_limit")

        if self._check_timeout():
            return self._build_break_response("timeout")

        if self._check_cost_limit():
            return self._build_break_response("cost_limit")

        return {"triggered": False}

    def _check_state_visit_limit(self, state: str) -> bool:
        """Check if state has been visited too many times."""
        return self.state_visits[state] >= self.state_visit_limit

    def _check_cycle_detection(self) -> bool:
        """Detect A→B→A→B pattern in last 4 transitions."""
        if len(self.transition_history) < 4:
            return False
        recent = self.transition_history[-4:]
        return recent[:2] == recent[2:]

    def _check_transition_limit(self) -> bool:
        """Check if total transitions exceeded."""
        return self.transition_count >= self.transition_limit

    def _check_timeout(self) -> bool:
        """Check if workflow timed out."""
        return (time.time() - self.start_time) >= self.timeout_seconds

    def _check_cost_limit(self) -> bool:
        """Check if cost limit exceeded."""
        return self.total_cost >= self.cost_limit

    def _build_break_response(self, rule: str) -> dict:
        """Build the break response with full context."""
        return {
            "triggered": True,
            "rule": rule,
            "context": self.get_context(),
        }

    def get_context(self) -> dict:
        """Get full context for debugging or orchestrator decision."""
        return {
            "state_visits": dict(self.state_visits),
            "transition_history": self.transition_history.copy(),
            "transition_count": self.transition_count,
            "elapsed_s": time.time() - self.start_time,
            "total_cost_usd": self.total_cost,
        }

    def update_cost(self, cost_usd: float):
        """Call after each agent invocation with the cost."""
        self.total_cost += cost_usd

    def check_safety_limits(self) -> dict:
        """Check hard limits that orchestrator can't override.

        These are safety nets in case orchestrator makes bad decisions.
        """
        max_transitions = self.safety_limits.get("max_transitions_hard", 50)
        max_runtime = self.safety_limits.get("max_runtime_hard", 3600)
        max_cost = self.safety_limits.get("max_cost_hard", 10.00)

        if self.transition_count >= max_transitions:
            return {
                "triggered": True,
                "rule": "hard_transition_limit",
                "overridable": False,
                "context": self.get_context(),
            }

        elapsed = time.time() - self.start_time
        if elapsed >= max_runtime:
            return {
                "triggered": True,
                "rule": "hard_timeout",
                "overridable": False,
                "context": self.get_context(),
            }

        if self.total_cost >= max_cost:
            return {
                "triggered": True,
                "rule": "hard_cost_limit",
                "overridable": False,
                "context": self.get_context(),
            }

        return {"triggered": False}

    def reset(self):
        """Reset all tracking (for testing or new run)."""
        self.state_visits.clear()
        self.transition_history.clear()
        self.transition_count = 0
        self.start_time = time.time()
        self.total_cost = 0.0
