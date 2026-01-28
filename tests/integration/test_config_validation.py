"""Integration tests: validate workflow configs against agent factory and persona loader.

These tests catch configuration issues like:
- Agent names that don't resolve through the factory (e.g. missing ollama- prefix)
- Persona slugs that don't map to template files
- Fan-out states with audit output_type but missing audit transitions
- States referencing agents not defined in the config

No external services required — reads YAML configs and validates against code.
"""

import os
import glob
import pytest
import yaml

from runner.agents.factory import (
    create_agent, _lazy_load_registries, _get_base_agent,
    CLI_AGENT_REGISTRY, API_AGENT_REGISTRY,
)


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _agent_resolves(name: str, agent_type: str = "") -> bool:
    """Check if agent name resolves via CLI or API registry.

    Args:
        name: Agent name to resolve.
        agent_type: Optional type hint from config (e.g. 'api', 'ollama').
    """
    _lazy_load_registries()
    if _get_base_agent(name, CLI_AGENT_REGISTRY) is not None:
        return True
    if _get_base_agent(name, API_AGENT_REGISTRY) is not None:
        return True
    return False


def _load_all_configs() -> list[tuple[str, dict]]:
    """Load all workflow_config*.yaml files."""
    pattern = os.path.join(PROJECT_ROOT, "workflow_config*.yaml")
    configs = []
    for path in sorted(glob.glob(pattern)):
        with open(path) as f:
            config = yaml.safe_load(f)
        name = os.path.basename(path)
        configs.append((name, config))
    return configs


ALL_CONFIGS = _load_all_configs()


@pytest.fixture(params=ALL_CONFIGS, ids=[c[0] for c in ALL_CONFIGS])
def workflow_config(request):
    """Parametrized fixture yielding (config_name, config_dict) for each YAML."""
    return request.param


class TestAgentResolution:
    """Every agent referenced in states must resolve through the factory."""

    def test_all_state_agents_resolve(self, workflow_config):
        """Every agent name used in states resolves to a valid agent class."""
        config_name, config = workflow_config

        states = config.get("states", {})
        failures = []

        for state_name, state in states.items():
            state_type = state.get("type", "single")

            if state_type == "fan-out":
                agent_names = state.get("agents", [])
            elif state_type in ("single", "orchestrator-task"):
                agent_name = state.get("agent")
                agent_names = [agent_name] if agent_name else []
            else:
                continue

            for agent_name in agent_names:
                if not _agent_resolves(agent_name):
                    failures.append(
                        f"  state '{state_name}': agent '{agent_name}' "
                        f"does not resolve to any registered agent type"
                    )

        assert not failures, (
            f"{config_name}: agent resolution failures:\n" + "\n".join(failures)
        )

    def test_all_config_agents_resolve(self, workflow_config):
        """Every agent defined in the agents section resolves through the factory."""
        config_name, config = workflow_config

        agent_configs = config.get("agents", {})
        failures = []

        for agent_name in agent_configs:
            if not _agent_resolves(agent_name):
                failures.append(
                    f"  agent '{agent_name}' does not resolve to any registered type"
                )

        assert not failures, (
            f"{config_name}: agent definition failures:\n" + "\n".join(failures)
        )

    def test_state_agents_defined_in_config(self, workflow_config):
        """Every agent used in states has a matching entry in agents section."""
        config_name, config = workflow_config
        agent_configs = config.get("agents", {})
        states = config.get("states", {})
        failures = []

        for state_name, state in states.items():
            state_type = state.get("type", "single")

            if state_type == "fan-out":
                agent_names = state.get("agents", [])
            elif state_type in ("single", "orchestrator-task"):
                agent_name = state.get("agent")
                agent_names = [agent_name] if agent_name else []
            else:
                continue

            for agent_name in agent_names:
                if agent_name and agent_name not in agent_configs:
                    failures.append(
                        f"  state '{state_name}': agent '{agent_name}' "
                        f"not in agents config (available: {list(agent_configs.keys())})"
                    )

        assert not failures, (
            f"{config_name}: missing agent definitions:\n" + "\n".join(failures)
        )


class TestPersonaResolution:
    """Every persona referenced in states must have a template file."""

    def test_all_personas_have_templates(self, workflow_config):
        """Every persona slug maps to an existing template file."""
        config_name, config = workflow_config
        states = config.get("states", {})
        prompts_dir = os.path.join(PROJECT_ROOT, "prompts", "templates")
        failures = []

        for state_name, state in states.items():
            # Collect all persona slugs from this state
            slugs = []

            # Shared persona
            shared = state.get("persona")
            if shared:
                slugs.append((shared, "persona"))

            # Per-agent persona map (fan-out)
            personas_map = state.get("personas", {})
            for agent_name, slug in personas_map.items():
                slugs.append((slug, f"personas[{agent_name}]"))

            for slug, source in slugs:
                filename = slug.replace("-", "_") + ".md"
                template_path = os.path.join(prompts_dir, filename)
                if not os.path.exists(template_path):
                    failures.append(
                        f"  state '{state_name}' {source}: "
                        f"persona '{slug}' -> template '{filename}' not found"
                    )

        assert not failures, (
            f"{config_name}: missing persona templates:\n" + "\n".join(failures)
        )

    def test_personas_section_matches_templates(self, workflow_config):
        """Every persona in the personas section has a template file."""
        config_name, config = workflow_config
        personas = config.get("personas", {})
        failures = []

        for slug, path in personas.items():
            full_path = os.path.join(PROJECT_ROOT, path)
            if not os.path.exists(full_path):
                failures.append(
                    f"  persona '{slug}': path '{path}' does not exist"
                )

        assert not failures, (
            f"{config_name}: missing persona files:\n" + "\n".join(failures)
        )


class TestAuditStateTransitions:
    """Audit-type fan-out states must have proceed/retry/halt transitions."""

    def test_audit_states_have_valid_transitions(self, workflow_config):
        """Audit-type states must have appropriate transitions for their mode.

        Fan-out audit with per-agent personas (split auditors) uses aggregated
        transitions: proceed/retry/halt.

        Fan-out audit with shared persona (legacy) uses count-based transitions:
        all_success/partial_success/all_failure.

        Single audit states need proceed/retry or success.
        """
        config_name, config = workflow_config
        states = config.get("states", {})
        failures = []

        for state_name, state in states.items():
            output_type = state.get("output_type", "")
            state_type = state.get("type", "single")

            if output_type not in ("audit", "review", "final_audit"):
                continue

            transitions = state.get("transitions", {})

            if state_type == "fan-out":
                has_personas_map = bool(state.get("personas"))
                if has_personas_map:
                    # Split-auditor mode: needs aggregated audit transitions
                    required = {"proceed", "retry"}
                    missing = required - set(transitions.keys())
                    if missing:
                        failures.append(
                            f"  state '{state_name}' (fan-out split-audit, {output_type}): "
                            f"missing transitions: {missing}"
                        )
                else:
                    # Legacy count-based mode: needs all_success or partial_success
                    has_count = "all_success" in transitions or "partial_success" in transitions
                    if not has_count:
                        failures.append(
                            f"  state '{state_name}' (fan-out, {output_type}): "
                            f"needs all_success/partial_success or personas + proceed/retry"
                        )
            elif state_type == "single":
                has_audit_trans = "proceed" in transitions or "retry" in transitions
                has_success = "success" in transitions
                if not has_audit_trans and not has_success:
                    failures.append(
                        f"  state '{state_name}' (single, {output_type}): "
                        f"needs proceed/retry or success transition"
                    )

        assert not failures, (
            f"{config_name}: audit transition issues:\n" + "\n".join(failures)
        )

    def test_transition_targets_exist(self, workflow_config):
        """Every transition target must be a defined state."""
        config_name, config = workflow_config
        states = config.get("states", {})
        failures = []

        for state_name, state in states.items():
            transitions = state.get("transitions", {})
            for trigger, target in transitions.items():
                if target not in states:
                    failures.append(
                        f"  state '{state_name}': transition '{trigger}' -> "
                        f"'{target}' (state not defined)"
                    )

            # Also check 'next' field
            next_state = state.get("next")
            if next_state and next_state not in states:
                failures.append(
                    f"  state '{state_name}': next -> '{next_state}' (state not defined)"
                )

        assert not failures, (
            f"{config_name}: broken transitions:\n" + "\n".join(failures)
        )


class TestFanOutConsistency:
    """Fan-out state config must be internally consistent."""

    def test_fanout_personas_match_agents(self, workflow_config):
        """Per-agent persona map keys must match the agents list."""
        config_name, config = workflow_config
        states = config.get("states", {})
        failures = []

        for state_name, state in states.items():
            if state.get("type") != "fan-out":
                continue

            agents = set(state.get("agents", []))
            personas_map = state.get("personas", {})

            if not personas_map:
                continue

            # Every key in personas must be a listed agent
            extra_keys = set(personas_map.keys()) - agents
            if extra_keys:
                failures.append(
                    f"  state '{state_name}': personas has keys not in agents: {extra_keys}"
                )

            # Every agent should have a persona (or shared persona exists)
            if not state.get("persona"):
                missing = agents - set(personas_map.keys())
                if missing:
                    failures.append(
                        f"  state '{state_name}': agents without persona mapping "
                        f"and no shared persona: {missing}"
                    )

        assert not failures, (
            f"{config_name}: fan-out persona mismatch:\n" + "\n".join(failures)
        )

    def test_fanout_output_has_agent_placeholder(self, workflow_config):
        """Fan-out output templates must contain {agent} placeholder."""
        config_name, config = workflow_config
        states = config.get("states", {})
        failures = []

        for state_name, state in states.items():
            if state.get("type") != "fan-out":
                continue

            output = state.get("output", "")
            agents = state.get("agents", [])

            if len(agents) > 1 and "{agent}" not in output:
                failures.append(
                    f"  state '{state_name}': output template '{output}' "
                    f"missing {{agent}} placeholder (has {len(agents)} agents)"
                )

        assert not failures, (
            f"{config_name}: fan-out output issues:\n" + "\n".join(failures)
        )
