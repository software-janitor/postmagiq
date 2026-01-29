"""State machine for workflow execution."""

import os
import time
import subprocess
import threading
from copy import deepcopy
from typing import Optional, Callable
from concurrent.futures import ThreadPoolExecutor, as_completed

from runner.models import (
    AgentResult,
    TokenUsage,
    FanOutResult,
    StateResult,
    AuditResult,
)
from runner.agents import create_agent, BaseAgent
from runner.metrics import TokenTracker
from runner.circuit_breaker import CircuitBreaker


class StateMachine:
    """Executes workflow states with agent invocations."""

    def __init__(
        self,
        config: dict,
        agents: Optional[dict[str, BaseAgent]] = None,
        session_dir: str = "workflow/sessions",
        log_callback: Optional[Callable] = None,
        run_dir: Optional[str] = None,
        agent_logger=None,
        approval_callback: Optional[Callable[[dict], None]] = None,
        database=None,  # Database for primary storage
        dev_logger=None,  # Dev logger for LLM message visibility
    ):
        self.config = config
        self.states = config.get("states", {})
        self.settings = config.get("settings", {})
        self.session_dir = session_dir
        self.log_callback = log_callback or (lambda x: None)
        self.run_dir = run_dir
        self.agent_logger = agent_logger
        self.approval_callback = approval_callback
        self.db = database  # Primary storage
        self.dev_logger = dev_logger  # Dev logger for LLM visibility

        self.agents = agents or {}
        self._agent_configs = config.get("agents", {})

        self.circuit_breaker = CircuitBreaker(config)
        self.token_tracker: Optional[TokenTracker] = None
        self.retry_feedback: dict[str, str] = {}
        self.current_state: Optional[str] = None
        self.last_audit_score: Optional[int] = None  # Track last audit score for circuit breaker decisions
        self.run_id: Optional[str] = None

        # Approval flow state (for API-driven approval)
        self._approval_event = threading.Event()
        self._approval_response: Optional[dict] = None
        self._approval_lock = threading.Lock()
        self.awaiting_approval = False

        # Pause/resume state (for checkpoint functionality)
        self._paused = False
        self._pause_event = threading.Event()
        self._pause_event.set()  # Start unpaused (event is set = continue)

        # Abort state
        self._aborted = False

    def initialize(self, run_id: str):
        """Initialize for a new run."""
        self.run_id = run_id
        self.token_tracker = TokenTracker(run_id)
        self.circuit_breaker.reset()
        self.retry_feedback.clear()
        # Reset approval state
        self._approval_event.clear()
        self._approval_response = None
        self.awaiting_approval = False
        # Reset pause state
        self._paused = False
        self._pause_event.set()
        # Reset abort state
        self._aborted = False

    def pause(self) -> bool:
        """Pause execution at the next state checkpoint.

        Returns:
            True if paused, False if not running.
        """
        if not self.current_state:
            return False
        self._paused = True
        self._pause_event.clear()
        return True

    def resume(self) -> bool:
        """Resume execution from paused state.

        Returns:
            True if resumed, False if not paused.
        """
        if not self._paused:
            return False
        self._paused = False
        self._pause_event.set()
        return True

    def is_paused(self) -> bool:
        """Check if workflow is paused."""
        return self._paused

    def abort(self):
        """Abort execution. Unblocks pause and approval waits so the main loop exits."""
        self._aborted = True
        # Unblock pause wait if paused
        self._pause_event.set()
        # Unblock approval wait if waiting
        self._approval_event.set()

    def submit_approval(self, decision: str, feedback: Optional[str] = None) -> bool:
        """Submit approval response from API.

        Args:
            decision: One of 'approved', 'feedback', 'abort', 'force_complete'
            feedback: Optional feedback text (used when decision='feedback')

        Returns:
            True if approval was pending and response was accepted, False otherwise.
        """
        with self._approval_lock:
            if not self.awaiting_approval:
                return False
            self._approval_response = {
                "decision": decision,
                "feedback": feedback,
            }
            self._approval_event.set()
            return True

    def _resolve_output_path(self, path_template: str, **kwargs) -> str:
        """Resolve output path, namespacing under run_dir if set.

        Converts paths like 'workflow/drafts/{agent}_draft.md' to
        '{run_dir}/drafts/{agent}_draft.md' when run_dir is set.
        """
        formatted = path_template.format(**kwargs)

        if self.run_dir:
            if formatted.startswith("workflow/"):
                formatted = formatted[len("workflow/"):]
            return os.path.join(self.run_dir, formatted)

        return formatted

    def get_agent(self, name: str) -> BaseAgent:
        """Get or create an agent by name."""
        if name in self.agents:
            return self.agents[name]

        agent_config = self._agent_configs.get(name, {})
        agent = create_agent(name, agent_config, self.session_dir)
        self.agents[name] = agent
        return agent

    def run(self, start_state: str = "start") -> dict:
        """Run the workflow from start to completion."""
        self.current_state = start_state
        final_state = None
        error = None

        while True:
            # Check for abort
            if self._aborted:
                self.log_callback({
                    "event": "aborted",
                    "state": self.current_state,
                })
                return {
                    "final_state": "halt",
                    "error": "Aborted by user",
                }

            # Check for pause checkpoint
            if self._paused:
                self.log_callback({
                    "event": "paused",
                    "state": self.current_state,
                })
                # Wait for resume (blocks until _pause_event is set)
                self._pause_event.wait()
                # Check if we were unblocked by abort rather than resume
                if self._aborted:
                    self.log_callback({
                        "event": "aborted",
                        "state": self.current_state,
                    })
                    return {
                        "final_state": "halt",
                        "error": "Aborted by user",
                    }
                self.log_callback({
                    "event": "resumed",
                    "state": self.current_state,
                })

            safety_check = self.circuit_breaker.check_safety_limits()
            if safety_check["triggered"]:
                self.log_callback({
                    "event": "hard_limit",
                    "rule": safety_check["rule"],
                    "context": safety_check["context"],
                })
                return {
                    "final_state": "halt",
                    "error": f"Hard limit triggered: {safety_check['rule']}",
                    "context": safety_check["context"],
                }

            state_config = self.states.get(self.current_state)
            if not state_config:
                return {
                    "final_state": "halt",
                    "error": f"Unknown state: {self.current_state}",
                }

            state_type = state_config.get("type", "single")

            if state_type == "terminal":
                final_state = self.current_state
                break

            try:
                result = self.execute_state(self.current_state, state_config)
            except Exception as e:
                error = str(e)
                self.log_callback({
                    "event": "state_error",
                    "state": self.current_state,
                    "error": error,
                })
                final_state = "halt"
                break

            next_state = self._get_next_state(state_config, result)

            if next_state is None:
                final_state = "halt"
                # Extract actual error from agent outputs if available
                agent_errors = [
                    out.error for out in result.outputs.values()
                    if hasattr(out, 'error') and out.error
                ]
                if agent_errors:
                    error = agent_errors[0]  # Use first agent error
                else:
                    error = f"No valid transition '{result.transition}' from {self.current_state}"
                break

            breaker_check = self.circuit_breaker.check(self.current_state, next_state)
            if breaker_check["triggered"]:
                rule = breaker_check["rule"]
                ctx = breaker_check["context"]
                AUTO_PROCEED_THRESHOLD = 8

                self.log_callback({
                    "event": "circuit_break",
                    "rule": rule,
                    "context": ctx,
                    "last_audit_score": self.last_audit_score,
                })

                # If last audit score >= 8, auto-proceed (story is good enough)
                if self.last_audit_score is not None and self.last_audit_score >= AUTO_PROCEED_THRESHOLD:
                    # Look for success/proceed transition (different states use different names)
                    transitions = self._get_transitions(state_config)
                    skip_target = transitions.get("success") or transitions.get("proceed")
                    if skip_target:
                        self.log_callback({
                            "event": "circuit_break_auto_skip",
                            "reason": f"Score {self.last_audit_score} >= {AUTO_PROCEED_THRESHOLD}, auto-proceeding",
                            "skip_to": skip_target,
                        })
                        next_state = skip_target
                    # Continue to next iteration with new next_state
                elif self.approval_callback:
                    # Score < 8, show quality feedback and ask user what to do
                    audit_results = self._collect_audit_results()

                    # Build user-friendly content with audit feedback
                    content_parts = []
                    content_parts.append(f"Quality Score: {self.last_audit_score or 'N/A'}/10\n")

                    if audit_results:
                        content_parts.append("Auditor Feedback:\n")
                        for ar in audit_results:
                            auditor = ar.get("agent", "Unknown")
                            score = ar.get("score", "N/A")
                            feedback = ar.get("feedback", "No feedback")
                            content_parts.append(f"• {auditor}: {score}/10 - {feedback}\n")
                    else:
                        content_parts.append("No audit feedback available.\n")

                    content_parts.append("\nThe post needs improvement to reach the quality threshold (8/10).")

                    self.approval_callback({
                        "type": "circuit_break",
                        "content": "".join(content_parts),
                        "prompt": "Review the feedback above and provide guidance to improve the post, or choose to publish as-is.",
                        "audit_results": audit_results,
                    })

                    # Wait for user decision
                    decision, user_feedback = self._wait_for_approval()

                    if decision == "approved":
                        # User wants to publish as-is - skip forward
                        transitions = self._get_transitions(state_config)
                        skip_target = transitions.get("success") or transitions.get("proceed")
                        if skip_target:
                            self.log_callback({
                                "event": "circuit_break_skip",
                                "skipped_state": next_state,
                                "skip_to": skip_target,
                            })
                            next_state = skip_target
                        else:
                            self.log_callback({
                                "event": "circuit_break_continue",
                                "continuing_to": next_state,
                            })
                    elif decision == "feedback":
                        # User wants to try again with guidance - loop back to synthesize
                        self.log_callback({
                            "event": "circuit_break_retry",
                            "user_feedback": user_feedback,
                        })
                        # Reset circuit breaker to allow more iterations
                        self.circuit_breaker.reset()
                        # Store user feedback for synthesizer
                        if user_feedback:
                            self.retry_feedback["synthesize"] = f"## USER FEEDBACK — MUST INCORPORATE\n\n{user_feedback}"
                        # Go back to synthesize
                        next_state = "synthesize"
                    else:
                        # User chose to abort
                        return {
                            "final_state": "halt",
                            "circuit_break": True,
                            "rule": rule,
                            "context": ctx,
                            "user_aborted": True,
                        }
                else:
                    # No approval callback, auto-halt as before
                    return {
                        "final_state": "halt",
                        "circuit_break": True,
                        "rule": rule,
                        "context": ctx,
                    }

            self.log_callback({
                "event": "transition",
                "from": self.current_state,
                "to": next_state,
            })
            self.current_state = next_state

        return {
            "final_state": final_state,
            "error": error,
            "token_summary": self.token_tracker.get_summary() if self.token_tracker else None,
        }

    def execute_state(self, state_name: str, state_config: dict) -> StateResult:
        """Execute a single state."""
        state = deepcopy(state_config)
        state_type = state.get("type", "single")

        feedback = self.retry_feedback.pop(state_name, None)
        if feedback:
            # If feedback already has structured markers (from human approval),
            # preserve them. Otherwise wrap audit feedback with a marker so
            # _build_prompt places it after input files in the user message.
            if "## USER FEEDBACK" in feedback or "## Reviewer Context" in feedback:
                state["context"] = feedback
            else:
                state["context"] = (
                    f"## USER FEEDBACK — MUST INCORPORATE\n\n"
                    f"Previous attempt feedback:\n{feedback}"
                )

        self.log_callback({
            "event": "state_enter",
            "state": state_name,
            "type": state_type,
            "has_feedback": feedback is not None,
        })

        start_time = time.time()

        if state_type == "initial":
            result = self._execute_initial(state)
        elif state_type == "fan-out":
            result = self._execute_fanout(state_name, state)
        elif state_type == "single":
            result = self._execute_single(state_name, state)
        elif state_type == "orchestrator-task":
            result = self._execute_orchestrator_task(state_name, state)
        elif state_type == "human-approval":
            result = self._execute_human_approval(state)
        else:
            raise ValueError(f"Unknown state type: {state_type}")

        result.duration_s = time.time() - start_time

        # Build per-agent metrics for the event
        agent_metrics = {}
        for agent_name, agent_result in result.outputs.items():
            tokens = agent_result.tokens
            agent_metrics[agent_name] = {
                "tokens": tokens.total if tokens else 0,
                "tokens_input": tokens.input_tokens if tokens else 0,
                "tokens_output": tokens.output_tokens if tokens else 0,
                "cost_usd": agent_result.cost_usd if hasattr(agent_result, 'cost_usd') else 0,
            }

        self.log_callback({
            "event": "state_complete",
            "state": state_name,
            "transition": result.transition,
            "duration_s": result.duration_s,
            "agent_metrics": agent_metrics,
        })

        return result

    def _execute_initial(self, state: dict) -> StateResult:
        """Execute initial state (validation only)."""
        return StateResult(
            state_name="start",
            transition="success",
        )

    def _execute_fanout(self, state_name: str, state: dict) -> StateResult:
        """Execute fan-out state with parallel agents."""
        agent_names = state.get("agents", [])
        input_path = state.get("input", "")
        output_template = state.get("output", "output/{agent}.md")
        timeout = self.settings.get("timeout_per_agent", 300)
        context = state.get("context", "")

        # Get original input specs from config (for database lookup)
        input_specs = []
        if isinstance(input_path, list):
            input_specs = input_path
        elif input_path:
            input_specs = [input_path]

        input_files = self._resolve_input_files(input_path)

        # Per-agent persona mapping (falls back to shared persona)
        personas_map = state.get("personas", {})
        shared_persona = state.get("persona", "")

        # For draft state, include audit feedback from previous iteration if available
        if state_name == "draft":
            audit_feedback = self._get_audit_feedback_for_writers()
            if audit_feedback:
                if context:
                    context = f"{context}\n\n{audit_feedback}"
                else:
                    context = audit_feedback

        # Build per-agent prompts
        agent_prompts: dict[str, str] = {}
        for agent_name in agent_names:
            persona_slug = personas_map.get(agent_name, shared_persona)
            persona_content = self._load_persona(persona_slug)
            agent_prompts[agent_name] = self._build_prompt(
                persona_content, input_files, context, input_specs=input_specs
            )

        outputs: dict[str, FanOutResult] = {}
        total_tokens = TokenUsage(input_tokens=0, output_tokens=0)
        total_cost = 0.0

        parallel = self.settings.get("parallel_fanout", True)

        if parallel and len(agent_names) > 1:
            with ThreadPoolExecutor(max_workers=len(agent_names)) as executor:
                futures = {}
                for agent_name in agent_names:
                    output_path = self._resolve_output_path(output_template, agent=agent_name)
                    future = executor.submit(
                        self._invoke_agent, agent_name, agent_prompts[agent_name], output_path, state_name
                    )
                    futures[future] = agent_name

                try:
                    for future in as_completed(futures, timeout=timeout):
                        agent_name = futures[future]
                        try:
                            result = future.result(timeout=timeout)
                            outputs[agent_name] = result
                            if result.tokens:
                                total_tokens.input_tokens += result.tokens.input_tokens
                                total_tokens.output_tokens += result.tokens.output_tokens
                        except TimeoutError:
                            outputs[agent_name] = FanOutResult(
                                agent=agent_name,
                                status="failed",
                                error=f"Agent timed out after {timeout}s",
                                duration_s=timeout,
                            )
                except TimeoutError:
                    for future, agent_name in futures.items():
                        if agent_name not in outputs:
                            future.cancel()
                            # Kill the actual subprocess (future.cancel doesn't stop running tasks)
                            agent = self.agents.get(agent_name)
                            if agent and hasattr(agent, "kill"):
                                agent.kill()
                            outputs[agent_name] = FanOutResult(
                                agent=agent_name,
                                status="failed",
                                error=f"Agent timed out after {timeout}s",
                                duration_s=timeout,
                            )
        else:
            for agent_name in agent_names:
                output_path = self._resolve_output_path(output_template, agent=agent_name)
                result = self._invoke_agent(agent_name, agent_prompts[agent_name], output_path, state_name)
                outputs[agent_name] = result
                if result.tokens:
                    total_tokens.input_tokens += result.tokens.input_tokens
                    total_tokens.output_tokens += result.tokens.output_tokens

        success_count = sum(1 for r in outputs.values() if r.status == "success")
        total_count = len(agent_names)

        # For audit-type fan-outs, parse and aggregate audit results
        output_type = state.get("output_type", "")
        if output_type in ("audit", "review", "final_audit") and success_count > 0:
            audit_results = []
            for name, fan_result in outputs.items():
                if fan_result.status == "success":
                    audit = self._parse_audit_result(fan_result)
                    if audit:
                        audit_results.append((name, audit))

            if audit_results:
                transition, feedback = self._aggregate_audit_results(audit_results, state)
                return StateResult(
                    state_name=state_name,
                    transition=transition,
                    outputs=outputs,
                    total_tokens=total_tokens,
                    total_cost_usd=total_cost,
                )

        if success_count == total_count:
            transition = "all_success"
        elif success_count > 0:
            transition = "partial_success"
        else:
            transition = "all_failure"

        return StateResult(
            state_name=state_name,
            transition=transition,
            outputs=outputs,
            total_tokens=total_tokens,
            total_cost_usd=total_cost,
        )

    def _execute_single(self, state_name: str, state: dict) -> StateResult:
        """Execute single agent state (quality gates)."""
        agent_name = state.get("agent", "claude")
        input_path = state.get("input", "")
        output_template = state.get("output", f"output/{state_name}.md")
        context = state.get("context", "")

        input_files = self._resolve_input_files(input_path)
        persona_content = self._load_persona(state.get("persona", ""))
        prompt = self._build_prompt(persona_content, input_files, context)

        output_path = self._resolve_output_path(output_template)
        result = self._invoke_agent(agent_name, prompt, output_path, state_name)

        if result.status == "success":
            # Only parse as audit result for audit/review output types
            output_type = state.get("output_type", "")
            if output_type in ("audit", "review", "final_audit"):
                audit = self._parse_audit_result(result)
                if audit:
                    if audit.decision == "retry":
                        target = self._get_transitions(state).get("retry")
                        if target:
                            self.retry_feedback[target] = audit.feedback
                    return StateResult(
                        state_name=state_name,
                        transition=audit.decision,
                        outputs={agent_name: result},
                        total_tokens=result.tokens,
                    )

        transition = "success" if result.status == "success" else "failure"
        return StateResult(
            state_name=state_name,
            transition=transition,
            outputs={agent_name: result},
            total_tokens=result.tokens,
        )

    def _execute_orchestrator_task(self, state_name: str, state: dict) -> StateResult:
        """Execute orchestrator task with session context.

        The orchestrator maintains session state across calls, allowing it to
        make intelligent decisions based on previous iterations.
        """
        agent_name = state.get("agent", "orchestrator")
        prompt_template = state.get("prompt", "")
        input_config = state.get("input", "")
        output_template = state.get("output", "")

        # Handle input as string or list of paths/patterns
        input_paths = []
        if input_config:
            if isinstance(input_config, list):
                input_paths = input_config
            else:
                input_paths = [input_config]

        # Resolve input files (supports glob patterns)
        resolved_input_files = []
        for path_pattern in input_paths:
            resolved = self._resolve_output_path(path_pattern)
            resolved_input_files.extend(self._resolve_input_files(resolved))

        output_path = self._resolve_output_path(output_template, agent=agent_name)

        # Load persona if specified
        persona_content = self._load_persona(state.get("persona", ""))

        # Build context for orchestrator
        context = {
            "run_id": self.run_id,
            "current_state": state_name,
            "circuit_breaker": self.circuit_breaker.get_context(),
            "retry_feedback": self.retry_feedback,
        }

        # For synthesize state, include final audit feedback if available
        final_audit_feedback = None
        if state_name == "synthesize":
            final_audit_feedback = self._get_final_audit_feedback_for_synthesizer()

        # Build prompt: preamble + persona + prompt_template (with context) + input files
        prompt_parts = []

        # Always start with strict enforcement preamble
        prompt_parts.append(self.PROMPT_PREAMBLE)

        if persona_content:
            prompt_parts.append(persona_content)

        if prompt_template:
            template_prompt = prompt_template
            if "{context}" in template_prompt:
                import json
                template_prompt = template_prompt.replace("{context}", json.dumps(context, indent=2))
            prompt_parts.append(template_prompt)

        # Read input files and append to prompt
        input_content = ""
        for input_file in resolved_input_files:
            if os.path.exists(input_file):
                with open(input_file) as f:
                    content = f.read()
                input_content += f"\n\n## File: {os.path.basename(input_file)}\n\n{content}"

        if input_content:
            prompt_parts.append(f"## Input Files\n{input_content}")

        # Add final audit feedback for synthesizer revisions
        if final_audit_feedback:
            prompt_parts.append(final_audit_feedback)

        # Include user feedback from human-approval state if present
        # (This is set by execute_state() from retry_feedback before calling us)
        user_feedback = state.get("context", "")
        if user_feedback:
            # When we have user feedback, ONLY send the feedback as a follow-up
            # The session already has context from the previous iteration
            # Don't rebuild the entire prompt - just send the revision request
            prompt = f"""## Revision Request

{user_feedback}

Please make ONLY the requested changes. Do not rewrite the entire post. Keep everything else exactly as it was in your previous output."""
        else:
            prompt = "\n\n".join(prompt_parts)

        start_time = time.time()
        agent = self.get_agent(agent_name)

        # Log session info - especially useful when resuming with feedback
        actual_session_id = agent.session_manager.session_id if hasattr(agent, 'session_manager') else None
        if user_feedback and actual_session_id:
            self.log_callback({
                "event": "session_resume",
                "state": state_name,
                "session_id": actual_session_id,
                "message": f"Providing feedback to session {actual_session_id}",
            })
        elif user_feedback:
            self.log_callback({
                "event": "session_new",
                "state": state_name,
                "message": "Starting new session (no previous session found)",
            })

        # Set dev logger for LLM visibility (if enabled)
        if self.dev_logger and self.run_id:
            agent.set_dev_logger(self.dev_logger, self.run_id, state_name)

        # Use session ID based on run_id for continuity
        session_id = f"orchestrator_{self.run_id}"
        result = agent.invoke_with_session(session_id, prompt)

        # Clear dev logger after invocation
        if self.dev_logger:
            agent.clear_dev_logger()

        duration = time.time() - start_time

        if result.success and output_path:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            tmp_path = output_path + ".tmp"
            with open(tmp_path, "w") as f:
                f.write(result.content)
            os.replace(tmp_path, output_path)

            # Emit output_written event
            self.log_callback({
                "type": "output_written",
                "state": state_name,
                "agent": agent_name,
                "output_path": output_path,
                "content": result.content,
            })

        if result.cost_usd:
            self.circuit_breaker.update_cost(result.cost_usd)

        fan_out_result = FanOutResult(
            agent=agent_name,
            status="success" if result.success else "failed",
            content=result.content,
            tokens=result.tokens,
            duration_s=duration,
            error=result.error,
        )

        transition = "success" if result.success else "failure"
        return StateResult(
            state_name=state_name,
            transition=transition,
            outputs={agent_name: fan_out_result},
            total_tokens=result.tokens,
        )

    def _wait_for_approval(self, timeout: int = 3600) -> tuple[str, Optional[str]]:
        """Wait for approval response from API.

        Sets up the approval event, waits for submit_approval() to be called,
        and returns the decision and optional feedback.

        Args:
            timeout: Max seconds to wait for approval response.

        Returns:
            Tuple of (decision, feedback). Decision is one of 'approved',
            'feedback', 'abort', 'force_complete'. Returns ('abort', None)
            on timeout.
        """
        with self._approval_lock:
            self._approval_event.clear()
            self._approval_response = None
            self.awaiting_approval = True

        got_response = self._approval_event.wait(timeout=timeout)

        with self._approval_lock:
            self.awaiting_approval = False
            # If aborted, return abort regardless of approval state
            if self._aborted:
                return ("abort", None)
            if not got_response:
                return ("abort", None)
            decision = self._approval_response.get("decision", "abort")
            feedback = self._approval_response.get("feedback")
            return (decision, feedback)

    def _execute_human_approval(self, state: dict) -> StateResult:
        """Execute human approval state.

        If approval_callback is set (API mode), waits for submit_approval() call.
        Otherwise falls back to CLI input() for interactive mode.
        """
        input_path = state.get("input", "")
        prompt_text = state.get("prompt", "Approve? (yes/no/feedback)")
        timeout = state.get("timeout", 3600)  # Default 1 hour for approval

        # Resolve input path if run_dir is set
        if input_path and self.run_dir:
            if input_path.startswith("workflow/"):
                input_path = input_path[len("workflow/"):]
            input_path = os.path.join(self.run_dir, input_path)

        # Read content for approval - try primary path first, then fallbacks
        content = None
        actual_path = None

        # Try the configured input path first
        if input_path and os.path.exists(input_path):
            actual_path = input_path
        elif self.run_dir:
            # Fallback paths for post content (when audit passes without revise)
            fallback_paths = [
                os.path.join(self.run_dir, "final/final_post.md"),
                os.path.join(self.run_dir, "drafts/draft.md"),
            ]
            for fallback in fallback_paths:
                if os.path.exists(fallback):
                    actual_path = fallback
                    break

        if actual_path:
            with open(actual_path) as f:
                content = f.read()

        if self.approval_callback:
            # API mode: notify callback and wait for submit_approval()
            callback_data = {
                "input_path": actual_path or input_path,
                "content": content,
                "prompt": prompt_text,
                "run_id": self.run_id,
            }
            # Include reviewer context for feedback states
            if state.get("type") == "human-approval" and content:
                callback_data["reviewer_context"] = content

            # Include audit results so the UI can display scores/feedback
            audit_results = self._collect_audit_results()
            if audit_results:
                callback_data["audit_results"] = audit_results

            self.approval_callback(callback_data)

            decision, feedback = self._wait_for_approval(timeout=timeout)
        else:
            # CLI mode: use interactive input
            print(f"\n{'='*60}")
            print("HUMAN APPROVAL REQUIRED")
            print(f"{'='*60}")

            if content:
                display_path = actual_path or input_path
                print(f"\n--- {display_path} ---")
                print(content)
                print(f"--- end {display_path} ---\n")

            print(prompt_text)

            try:
                response = input("\n> ").strip()
            except EOFError:
                response = "abort"

            if response.lower() == "yes":
                decision = "approved"
                feedback = None
            elif response.lower() == "abort":
                decision = "abort"
                feedback = None
            else:
                decision = "feedback"
                feedback = response

        # Store feedback for retry state if applicable
        if decision == "feedback" and feedback:
            target = self._get_transitions(state).get("feedback")
            if target:
                # Combine reviewer context with user answers for stronger signal
                combined = f"## USER FEEDBACK — MUST INCORPORATE\n\n{feedback}"
                if content:
                    combined = (
                        f"## Reviewer Context\n\n{content}\n\n"
                        f"## USER FEEDBACK — MUST INCORPORATE\n\n{feedback}"
                    )
                self.retry_feedback[target] = combined

        self.log_callback({
            "event": "human_approval",
            "decision": decision,
            "feedback": feedback if decision == "feedback" else None,
        })

        return StateResult(
            state_name="human-approval",
            transition=decision,
        )

    def _state_to_output_type(self, state: str) -> str:
        """Get output type from state config.

        Reads output_type from workflow config state definition.
        Falls back to state name if not configured.
        """
        state_config = self.states.get(state, {})
        return state_config.get("output_type", state)

    def _invoke_agent(
        self, agent_name: str, prompt: str, output_path: str, state: str
    ) -> FanOutResult:
        """Invoke an agent and save output to database (primary) and file (secondary)."""
        start_time = time.time()

        if self.agent_logger:
            self.agent_logger.log_invoke(
                agent=agent_name,
                state=state,
                prompt=prompt,
            )

        try:
            agent = self.get_agent(agent_name)

            # Set dev logger for LLM visibility (if enabled)
            if self.dev_logger and self.run_id:
                agent.set_dev_logger(self.dev_logger, self.run_id, state)

            result = agent.invoke(prompt)

            # Clear dev logger after invocation
            if self.dev_logger:
                agent.clear_dev_logger()
            duration = time.time() - start_time

            if result.success:
                # Determine output type from state name
                output_type = self._state_to_output_type(state)

                # PRIMARY: Save to database
                if self.db and self.run_id:
                    self.db.save_workflow_output(
                        run_id=self.run_id,
                        state_name=state,
                        output_type=output_type,
                        content=result.content,
                        agent=agent_name,
                    )

                # SECONDARY: Try to save to file (optional, may fail due to permissions)
                try:
                    os.makedirs(os.path.dirname(output_path), exist_ok=True)
                    tmp_path = output_path + ".tmp"
                    with open(tmp_path, "w") as f:
                        f.write(result.content)
                    os.replace(tmp_path, output_path)
                except (OSError, PermissionError) as e:
                    # File write failed, but database has the content - log and continue
                    self.log_callback({
                        "type": "file_write_failed",
                        "state": state,
                        "agent": agent_name,
                        "output_path": output_path,
                        "error": str(e),
                        "note": "Content saved to database, file write optional",
                    })

                # Emit output_written event
                self.log_callback({
                    "type": "output_written",
                    "state": state,
                    "agent": agent_name,
                    "output_path": output_path,
                    "content": result.content,
                })

                if self.token_tracker:
                    self.token_tracker.record(
                        agent=agent_name,
                        state=state,
                        tokens=result.tokens,
                        cost=result.cost_usd or 0,
                        context_window=agent.context_window,
                    )

                if result.cost_usd:
                    self.circuit_breaker.update_cost(result.cost_usd)

                if self.agent_logger:
                    self.agent_logger.log_complete(
                        agent=agent_name,
                        state=state,
                        success=True,
                        duration_s=duration,
                        output_path=output_path,
                        output=result.content,
                        tokens=result.tokens,
                        cost_usd=result.cost_usd,
                    )

                return FanOutResult(
                    agent=agent_name,
                    status="success",
                    output_path=output_path,
                    content=result.content,
                    tokens=result.tokens,
                    cost_usd=result.cost_usd or 0.0,
                    duration_s=duration,
                )
            else:
                if self.agent_logger:
                    self.agent_logger.log_complete(
                        agent=agent_name,
                        state=state,
                        success=False,
                        duration_s=duration,
                        error=result.error,
                    )

                return FanOutResult(
                    agent=agent_name,
                    status="failed",
                    duration_s=duration,
                    error=result.error,
                )

        except Exception as e:
            duration = time.time() - start_time
            if self.agent_logger:
                self.agent_logger.log_complete(
                    agent=agent_name,
                    state=state,
                    success=False,
                    duration_s=duration,
                    error=str(e),
                )

            return FanOutResult(
                agent=agent_name,
                status="failed",
                duration_s=duration,
                error=str(e),
            )

    def _get_transitions(self, state_config: dict) -> dict:
        """Get transitions for a state, merging with defaults.

        Default transitions from config are used as base, then
        state-specific transitions override them.
        """
        # Get default transitions from config (if defined)
        defaults = self.config.get("default_transitions", {})
        # Get state-specific transitions
        state_transitions = state_config.get("transitions", {})
        # Merge: state-specific overrides defaults
        return {**defaults, **state_transitions}

    def _get_next_state(self, state_config: dict, result: StateResult) -> Optional[str]:
        """Determine next state from transitions.

        For states with explicit transitions: use merged transitions (state overrides defaults)
        For states without explicit transitions: use 'next' field first, then defaults
        """
        next_state = state_config.get("next")
        has_explicit_transitions = "transitions" in state_config

        if has_explicit_transitions:
            # Use merged transitions (state overrides defaults)
            transitions = self._get_transitions(state_config)
            if result.transition in transitions:
                return transitions[result.transition]
            # Fall back to next if transition not found
            if next_state:
                return next_state
        else:
            # No explicit transitions - check 'next' first (for initial states)
            if next_state:
                return next_state
            # Then check defaults
            defaults = self.config.get("default_transitions", {})
            if result.transition in defaults:
                return defaults[result.transition]

        return None

    def _resolve_input_files(self, input_spec: str) -> list[str]:
        """Resolve input file specification to list of paths.

        Checks run_dir first for run-specific inputs, then falls back
        to original paths for shared resources like personas.
        """
        if not input_spec:
            return []

        if isinstance(input_spec, list):
            files = []
            for spec in input_spec:
                files.extend(self._resolve_input_files(spec))
            return files

        run_spec = self._make_run_relative(input_spec)

        if "*" in input_spec:
            import glob
            run_files = sorted(glob.glob(run_spec)) if self.run_dir else []
            if run_files:
                return run_files
            return sorted(glob.glob(input_spec))

        if self.run_dir and os.path.exists(run_spec):
            return [run_spec]

        if os.path.exists(input_spec):
            return [input_spec]

        return []

    def _make_run_relative(self, path: str) -> str:
        """Convert a workflow path to be relative to run_dir."""
        if not self.run_dir:
            return path
        if path.startswith("workflow/"):
            return os.path.join(self.run_dir, path[len("workflow/"):])
        return path

    def _load_persona(self, persona_ref: str) -> str:
        """Load composed persona prompt from universal_rules + voice_profile + template.

        Composes the full prompt at runtime by combining:
        1. prompts/universal_rules.md - Rules that apply to all personas
        2. prompts/voice_profiles/{voice_profile}.md - User's voice characteristics
        3. prompts/templates/{persona}.md - Persona-specific template

        Falls back to database content if compose_persona_prompt returns empty.
        Returns empty string if persona not found (will cause state to fail).
        """
        if not persona_ref:
            return ""

        try:
            from runner.content.ids import get_system_user_id
            from runner.content.workflow_store import WorkflowStore

            store = self.db or WorkflowStore(get_system_user_id())

            # Try composed prompt first (universal_rules + voice_profile + template)
            composed = WorkflowStore.compose_persona_prompt(persona_ref)
            if composed:
                return composed

            # Fall back to database content if composition failed
            persona = store.get_workflow_persona_by_slug(get_system_user_id(), persona_ref)
            if persona:
                return persona.content
        except Exception as e:
            self.log_callback({
                "event": "persona_load_error",
                "persona": persona_ref,
                "error": str(e),
            })

        return ""

    # Strict enforcement preamble - prepended to ALL agent prompts
    PROMPT_PREAMBLE = """⚠️ CRITICAL INSTRUCTION ⚠️

Read your persona below and follow ALL rules STRICTLY. You are being monitored and audited.

- Any deviation from your persona rules will be flagged and rejected
- ANY fabrication of details not in the source material is FORBIDDEN
- If the source doesn't say it, you CANNOT add it
- Vague is better than invented

Your output will be cross-checked against source material. Fabrications = automatic rejection.

---

"""

    def _get_content_from_db(self, output_type: str) -> Optional[str]:
        """Get content from database by output type.

        Returns only the latest record for this output type to avoid
        duplicate content from re-runs or multiple submissions.
        """
        if not self.db or not self.run_id:
            return None
        try:
            outputs = self.db.get_workflow_outputs_by_type(self.run_id, output_type)
            if outputs:
                # Use only the latest record to avoid duplicate content
                return outputs[-1].content
        except Exception:
            pass
        return None

    def _get_audit_feedback(self, audit_type: str = "audit") -> Optional[str]:
        """Get audit feedback from previous iteration.

        Args:
            audit_type: Type of audit - "audit" for cross-audit, "final" for final-audit

        Returns formatted feedback from all auditors if available.
        """
        audit_feedback_parts = []

        # Determine file pattern based on audit type
        if audit_type == "final":
            file_pattern = "final/*_final_audit.json"
            db_type = "final_audit"  # Matches _state_to_output_type("final-audit")
            header = "Previous Final Audit Feedback"
            intro = "You received the following feedback from final auditors on your synthesized post."
        else:
            file_pattern = "audits/*_audit.json"
            db_type = "audit"
            header = "Previous Auditor Feedback"
            intro = "You received the following feedback from auditors on your previous draft."

        # Try database first
        if self.db and self.run_id:
            try:
                outputs = self.db.get_workflow_outputs_by_type(self.run_id, db_type)
                if outputs:
                    for output in outputs:
                        agent_name = output.agent or "Auditor"
                        audit_feedback_parts.append(
                            f"### Feedback from {agent_name.title()}\n\n{output.content}"
                        )
            except Exception:
                pass

        # Fall back to files if database didn't have content
        if not audit_feedback_parts and self.run_dir:
            import glob
            audit_pattern = os.path.join(self.run_dir, file_pattern)
            audit_files = glob.glob(audit_pattern)

            for audit_file in sorted(audit_files):
                try:
                    with open(audit_file) as f:
                        content = f.read()
                    # Extract agent name from filename
                    basename = os.path.basename(audit_file)
                    agent_name = basename.replace("_final_audit.json", "").replace("_audit.json", "").title()
                    audit_feedback_parts.append(
                        f"### Feedback from {agent_name}\n\n{content}"
                    )
                except Exception:
                    pass

        if audit_feedback_parts:
            return (
                f"## {header}\n\n"
                f"{intro} "
                "Consider this feedback when writing your revision:\n\n"
                + "\n\n".join(audit_feedback_parts)
            )

        return None

    def _get_audit_feedback_for_writers(self) -> Optional[str]:
        """Get cross-audit feedback for writers."""
        return self._get_audit_feedback("audit")

    def _get_final_audit_feedback_for_synthesizer(self) -> Optional[str]:
        """Get final audit feedback for synthesizer."""
        return self._get_audit_feedback("final")

    def _collect_audit_results(self) -> list[dict]:
        """Collect parsed audit results from database or files for UI display.

        Returns a list of dicts with keys: agent, score, decision, feedback.
        Tries final_audit first, falls back to cross-audit.
        """
        import json as _json

        results = []

        for audit_type, db_type, file_pattern in [
            ("final_audit", "final_audit", "final/*_final_audit.json"),
            ("audit", "audit", "audits/*_audit.json"),
        ]:
            # Try database first
            if self.db and self.run_id:
                try:
                    outputs = self.db.get_workflow_outputs_by_type(self.run_id, db_type)
                    for output in outputs:
                        parsed = self._try_parse_audit_json(output.content)
                        if parsed:
                            parsed["agent"] = output.agent or "auditor"
                            parsed["audit_type"] = audit_type
                            results.append(parsed)
                except Exception:
                    pass

            # Fall back to files
            if not results and self.run_dir:
                import glob
                pattern = os.path.join(self.run_dir, file_pattern)
                for audit_file in sorted(glob.glob(pattern)):
                    try:
                        with open(audit_file) as f:
                            content = f.read()
                        parsed = self._try_parse_audit_json(content)
                        if parsed:
                            basename = os.path.basename(audit_file)
                            agent_name = basename.replace("_final_audit.json", "").replace("_audit.json", "")
                            parsed["agent"] = agent_name
                            parsed["audit_type"] = audit_type
                            results.append(parsed)
                    except Exception:
                        pass

            if results:
                return results

        return results

    def _try_parse_audit_json(self, content: str) -> Optional[dict]:
        """Try to parse audit JSON content, returning score/decision/feedback dict."""
        import json as _json

        json_str = self._extract_json(content)
        if not json_str:
            return None
        try:
            data = _json.loads(json_str)
            return {
                "score": data.get("score"),
                "decision": data.get("decision"),
                "feedback": data.get("feedback"),
            }
        except Exception:
            return None

    def _path_to_output_type(self, path: str) -> Optional[str]:
        """Map file path to database output type."""
        if "processed" in path:
            return "processed"
        elif "draft" in path:
            return "draft"
        elif "audit" in path:
            return "audit"
        elif "input" in path or "story_input" in path:
            return "input"
        elif "review" in path:
            return "review"
        elif "final" in path:
            return "final"
        return None

    def _build_prompt(
        self, persona: str, input_files: list[str], context: str = "",
        input_specs: list[str] = None
    ) -> str:
        """Build full prompt from persona, database content, and files.

        Layout: [preamble] [persona] [input files] [feedback context]

        Feedback context is placed AFTER input files so the Ollama agent's
        message split logic puts it in the user message (not system).
        Non-feedback context goes before input files.

        Args:
            input_files: Resolved file paths that exist on disk
            input_specs: Original input specs from config (for database lookup even if files don't exist)
        """
        parts = []

        # Always start with strict enforcement preamble
        parts.append(self.PROMPT_PREAMBLE)

        if persona:
            parts.append(persona)

        # Separate feedback context from regular context.
        # Feedback markers (from retry_feedback) go AFTER input files
        # so the Ollama split puts them in the user message.
        feedback_context = None
        regular_context = context
        if context and ("## USER FEEDBACK" in context or "## Reviewer Context" in context):
            feedback_context = context
            regular_context = None

        if regular_context:
            parts.append(f"## Context\n\n{regular_context}")

        # Collect all paths to try (both resolved files and original specs)
        paths_to_try = list(input_files) if input_files else []
        if input_specs:
            # Add specs that aren't already in resolved files
            for spec in input_specs:
                if spec not in paths_to_try:
                    paths_to_try.append(spec)

        if paths_to_try:
            parts.append("## Input Files\n")
            seen_types = set()  # Avoid duplicate database content

            for path in paths_to_try:
                content = None
                source = path

                # PRIMARY: Try database first
                output_type = self._path_to_output_type(path)
                if output_type and output_type not in seen_types:
                    content = self._get_content_from_db(output_type)
                    if content:
                        source = f"[database:{output_type}]"
                        seen_types.add(output_type)

                # SECONDARY: Fall back to file
                if not content and os.path.exists(path):
                    with open(path) as f:
                        content = f.read()

                if content:
                    parts.append(f"### {source}\n\n{content}")

        # Feedback context goes AFTER input files so Ollama splits it into
        # the user message (split markers: ## Reviewer Context, ## USER FEEDBACK)
        if feedback_context:
            parts.append(feedback_context)

        return "\n\n".join(parts)

    def _aggregate_audit_results(
        self, audit_results: list[tuple[str, AuditResult]], state: dict
    ) -> tuple[str, str]:
        """Aggregate multiple audit results — strictest decision wins.

        Returns:
            (transition, combined_feedback) tuple.
        """
        decisions = [ar.decision for _, ar in audit_results]
        scores = [ar.score for _, ar in audit_results]

        # Track minimum score for circuit breaker
        self.last_audit_score = min(scores)

        # Strictest wins: halt > retry > proceed
        if "halt" in decisions:
            transition = "halt"
        elif "retry" in decisions:
            transition = "retry"
        else:
            transition = "proceed"

        # Combine feedback from all auditors
        feedback_parts = []
        for name, audit in audit_results:
            feedback_parts.append(
                f"### {name} (score: {audit.score}, decision: {audit.decision})\n\n"
                f"{audit.feedback}"
            )
        combined_feedback = "\n\n".join(feedback_parts)

        # Store feedback for retry target
        if transition == "retry":
            target = self._get_transitions(state).get("retry")
            if target:
                self.retry_feedback[target] = combined_feedback

        return transition, combined_feedback

    def _parse_audit_result(self, result: FanOutResult) -> Optional[AuditResult]:
        """Try to parse agent output as audit result.

        Extracts JSON from markdown fences if present. Returns a retry
        decision on parse failure (fail-closed behavior) only if content
        looks like it was intended to be JSON.
        """
        # Try content field first, then fall back to file
        content = result.content
        if not content:
            if not result.output_path or not os.path.exists(result.output_path):
                return None
            with open(result.output_path) as f:
                content = f.read()

        import json

        json_str = self._extract_json(content)

        if not json_str:
            return None

        try:
            data = json.loads(json_str)

            # Track last audit score for circuit breaker decisions
            score = data.get("score", 0)
            self.last_audit_score = score

            # Server-side enforcement: if score < 9 and there are questions,
            # force retry so user can answer them. Circuit breaker will auto-skip
            # at score >= 8 if we loop too many times.
            questions = data.get("questions", [])
            if score < 9 and questions and len(questions) > 0:
                data["decision"] = "retry"

            audit = AuditResult.model_validate(data)
            return audit
        except json.JSONDecodeError as e:
            return AuditResult(
                score=1,
                decision="retry",
                feedback=f"Invalid JSON in audit output: {e}. Please output valid JSON only.",
            )
        except Exception as e:
            return AuditResult(
                score=1,
                decision="retry",
                feedback=f"Audit validation failed: {e}. Ensure output matches schema.",
            )

    def _extract_json(self, content: str) -> Optional[str]:
        """Extract JSON from content, handling markdown fences and extra braces."""
        import re
        import json as _json

        content = content.strip()

        # Try markdown fence extraction first
        fence_pattern = r"```(?:json)?\s*\n?(.*?)\n?```"
        match = re.search(fence_pattern, content, re.DOTALL)
        if match:
            content = match.group(1).strip()

        # Find first { and work from there
        brace_start = content.find("{")
        if brace_start == -1:
            return None

        # Try progressively shorter substrings from the end
        # to handle extra trailing braces like }}}
        candidate = content[brace_start:]
        while candidate.endswith("}"):
            try:
                _json.loads(candidate)
                return candidate
            except _json.JSONDecodeError:
                # Strip one trailing brace and retry
                candidate = candidate[:-1]
                if not candidate.endswith("}"):
                    break

        # Fallback: return from first { to last }
        brace_end = content.rfind("}")
        if brace_start != -1 and brace_end > brace_start:
            return content[brace_start:brace_end + 1]

        return None
