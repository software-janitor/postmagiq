"""Tests for circuit breaker."""

import pytest
import time
from runner.circuit_breaker import CircuitBreaker


@pytest.fixture
def breaker():
    config = {
        "circuit_breaker": {
            "rules": [
                {"name": "state_visit_limit", "limit": 3},
                {"name": "cycle_detection"},
                {"name": "transition_limit", "limit": 20},
                {"name": "timeout", "seconds": 1800},
                {"name": "cost_limit", "limit": 5.00},
            ],
            "safety_limits": {
                "max_transitions_hard": 50,
                "max_runtime_hard": 3600,
                "max_cost_hard": 10.00,
            },
        }
    }
    return CircuitBreaker(config)


class TestCircuitBreaker:
    def test_no_trigger_initially(self, breaker):
        result = breaker.check("start", "draft")
        assert result["triggered"] is False

    def test_state_visit_limit_triggers(self, breaker):
        breaker.check("start", "draft")
        breaker.check("draft", "check")
        breaker.check("check", "draft")
        breaker.check("draft", "check")
        result = breaker.check("check", "draft")

        assert result["triggered"] is True
        assert result["rule"] == "state_visit_limit"
        assert "context" in result

    def test_cycle_detection_triggers(self, breaker):
        # Need A→B→A→B pattern in last 4 transitions
        breaker.check("A", "B")  # transition 1
        breaker.check("B", "A")  # transition 2
        breaker.check("A", "B")  # transition 3
        result = breaker.check("B", "A")  # transition 4 - completes A→B→A→B

        assert result["triggered"] is True
        assert result["rule"] == "cycle_detection"

    def test_cycle_detection_no_false_positive(self, breaker):
        breaker.check("start", "A")
        breaker.check("A", "B")
        breaker.check("B", "C")
        result = breaker.check("C", "D")

        assert result["triggered"] is False

    def test_transition_limit_triggers(self, breaker):
        for i in range(19):
            result = breaker.check(f"state_{i}", f"state_{i+1}")
            if i < 18:
                assert result["triggered"] is False

        result = breaker.check("state_19", "state_20")
        assert result["triggered"] is True
        assert result["rule"] == "transition_limit"

    def test_cost_tracking(self, breaker):
        breaker.update_cost(2.50)
        assert breaker.total_cost == 2.50

        breaker.update_cost(1.50)
        assert breaker.total_cost == 4.00

    def test_cost_limit_triggers(self, breaker):
        breaker.update_cost(4.00)
        result = breaker.check("a", "b")
        assert result["triggered"] is False

        breaker.update_cost(1.50)
        result = breaker.check("b", "c")
        assert result["triggered"] is True
        assert result["rule"] == "cost_limit"

    def test_get_context(self, breaker):
        breaker.check("start", "draft")
        breaker.check("draft", "audit")
        breaker.update_cost(0.50)

        context = breaker.get_context()

        assert context["state_visits"]["draft"] == 1
        assert context["state_visits"]["audit"] == 1
        assert context["transition_count"] == 2
        assert context["total_cost_usd"] == 0.50
        assert len(context["transition_history"]) == 2

    def test_safety_limit_transitions(self, breaker):
        for i in range(49):
            breaker.check(f"s{i}", f"s{i+1}")

        result = breaker.check_safety_limits()
        assert result["triggered"] is False

        breaker.check("s49", "s50")
        result = breaker.check_safety_limits()
        assert result["triggered"] is True
        assert result["rule"] == "hard_transition_limit"
        assert result["overridable"] is False

    def test_safety_limit_cost(self, breaker):
        breaker.update_cost(9.99)
        result = breaker.check_safety_limits()
        assert result["triggered"] is False

        breaker.update_cost(0.02)
        result = breaker.check_safety_limits()
        assert result["triggered"] is True
        assert result["rule"] == "hard_cost_limit"

    def test_reset(self, breaker):
        breaker.check("a", "b")
        breaker.check("b", "c")
        breaker.update_cost(1.00)

        breaker.reset()

        assert breaker.transition_count == 0
        assert breaker.total_cost == 0.0
        assert len(breaker.state_visits) == 0
        assert len(breaker.transition_history) == 0


class TestCircuitBreakerDefaults:
    def test_default_limits(self):
        breaker = CircuitBreaker({})

        assert breaker.state_visit_limit == 3
        assert breaker.transition_limit == 20
        assert breaker.cost_limit == 5.00

    def test_custom_limits(self):
        config = {
            "circuit_breaker": {
                "rules": [
                    {"name": "state_visit_limit", "limit": 5},
                    {"name": "transition_limit", "limit": 30},
                    {"name": "cost_limit", "limit": 10.00},
                ]
            }
        }
        breaker = CircuitBreaker(config)

        assert breaker.state_visit_limit == 5
        assert breaker.transition_limit == 30
        assert breaker.cost_limit == 10.00
