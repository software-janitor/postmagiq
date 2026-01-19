"""Cost calculation utilities."""

from runner.models import TokenUsage

DEFAULT_COSTS = {
    "claude": {"input": 0.003, "output": 0.015},
    "gemini": {"input": 0.00125, "output": 0.005},
    "codex": {"input": 0.005, "output": 0.015},
}


def calculate_cost(tokens: TokenUsage, cost_per_1k: dict[str, float]) -> float:
    """Calculate cost in USD for given token usage."""
    input_cost = (tokens.input_tokens / 1000) * cost_per_1k.get("input", 0)
    output_cost = (tokens.output_tokens / 1000) * cost_per_1k.get("output", 0)
    return input_cost + output_cost


def get_default_cost(agent: str) -> dict[str, float]:
    """Get default cost per 1k tokens for an agent."""
    return DEFAULT_COSTS.get(agent, {"input": 0, "output": 0})


def format_cost(cost_usd: float) -> str:
    """Format cost as a readable string."""
    if cost_usd < 0.01:
        return f"${cost_usd:.4f}"
    return f"${cost_usd:.2f}"


def estimate_run_cost(
    states: list[str],
    agents: list[str],
    tokens_per_state: int = 2000,
) -> dict:
    """Estimate total cost for a workflow run.

    Args:
        states: List of state names in the workflow
        agents: List of agents used in fan-out states
        tokens_per_state: Estimated tokens per state invocation

    Returns:
        dict with estimated costs by agent and total
    """
    estimates = {}
    total = 0.0

    for agent in agents:
        cost_per_1k = get_default_cost(agent)
        tokens = TokenUsage(
            input_tokens=tokens_per_state * len(states),
            output_tokens=int(tokens_per_state * len(states) * 0.3),
        )
        agent_cost = calculate_cost(tokens, cost_per_1k)
        estimates[agent] = {
            "tokens": tokens.total,
            "cost_usd": agent_cost,
        }
        total += agent_cost

    return {
        "by_agent": estimates,
        "total_cost_usd": total,
        "formatted": format_cost(total),
    }
