"""State transition logging with database persistence."""

import json
import os
from datetime import datetime
from typing import Optional, TYPE_CHECKING, Union
from uuid import UUID

if TYPE_CHECKING:
    from runner.content.workflow_store import WorkflowStore

from runner.content.ids import normalize_user_id


class StateLogger:
    """Logs state transitions to both JSONL file and database.

    JSONL provides detailed audit trail for debugging.
    Database provides queryable run data for the API.
    """

    def __init__(
        self,
        run_dir: str,
        run_id: str,
        db: Optional["WorkflowStore"] = None,
        user_id: Union[UUID, str, None] = None,
    ):
        self.run_dir = run_dir
        self.run_id = run_id
        self.db = db
        self.user_id = normalize_user_id(user_id) if db else user_id
        self.log_file = os.path.join(run_dir, "state_log.jsonl")
        os.makedirs(run_dir, exist_ok=True)

        # Track accumulated metrics
        self._total_tokens = 0
        self._total_cost = 0.0

    def log(self, event: dict):
        """Append event to state log (JSONL)."""
        entry = {
            "ts": datetime.utcnow().isoformat() + "Z",
            "run_id": self.run_id,
            **event,
        }
        with open(self.log_file, "a") as f:
            f.write(json.dumps(entry) + "\n")

    def log_start(self, story: str, config_hash: Optional[str] = None):
        """Log workflow start."""
        self.log(
            {
                "event": "workflow_start",
                "story": story,
                "config_hash": config_hash,
            }
        )

        # Create database record
        if self.db:
            try:
                self.db.create_workflow_run(self.user_id, self.run_id, story)
            except Exception as e:
                # Log but don't fail - JSONL is the fallback
                self.log(
                    {"event": "db_error", "error": str(e), "operation": "create_run"}
                )

    def log_state_enter(self, state: str, state_type: str, has_feedback: bool = False):
        """Log entering a state."""
        self.log(
            {
                "event": "state_enter",
                "state": state,
                "type": state_type,
                "has_retry_feedback": has_feedback,
            }
        )

        # Update current state in database
        if self.db:
            try:
                self.db.update_workflow_run(self.run_id, current_state=state)
            except Exception:
                pass  # Non-critical update

    def log_state_complete(
        self,
        state: str,
        transition: str,
        duration_s: float,
        outputs: Optional[dict] = None,
    ):
        """Log state completion."""
        entry = {
            "event": "state_complete",
            "state": state,
            "transition": transition,
            "duration_s": round(duration_s, 2),
        }

        # Extract and accumulate tokens/cost from outputs
        state_tokens = 0
        state_cost = 0.0

        if outputs:
            entry["outputs"] = {}
            for agent, result in outputs.items():
                tokens_data = result.get("tokens", {})
                if isinstance(tokens_data, dict):
                    inp = tokens_data.get("input", 0) or 0
                    out = tokens_data.get("output", 0) or 0
                    total = inp + out
                else:
                    total = tokens_data or 0
                    inp = total // 2
                    out = total - inp

                state_tokens += total

                # Extract cost if available
                cost = result.get("cost", 0.0) or 0.0
                state_cost += cost

                entry["outputs"][agent] = {
                    "status": result.get("status"),
                    "tokens": tokens_data,
                }

                # Save per-agent metrics to database
                if self.db:
                    try:
                        self.db.save_state_metrics(
                            run_id=self.run_id,
                            state_name=state,
                            agent=agent,
                            tokens_input=inp,
                            tokens_output=out,
                            cost_usd=cost,
                            duration_s=duration_s,
                        )
                    except Exception:
                        pass  # Non-critical

        self._total_tokens += state_tokens
        self._total_cost += state_cost

        self.log(entry)

        # Update database with accumulated totals
        if self.db:
            try:
                self.db.update_workflow_run(
                    self.run_id,
                    total_tokens=self._total_tokens,
                    total_cost_usd=round(self._total_cost, 6),
                )
            except Exception:
                pass  # Non-critical update

    def log_transition(self, from_state: str, to_state: str):
        """Log state transition."""
        self.log(
            {
                "event": "transition",
                "from_state": from_state,
                "to_state": to_state,
            }
        )

    def log_circuit_break(self, rule: str, context: dict):
        """Log circuit breaker trigger."""
        self.log(
            {
                "event": "circuit_break",
                "rule": rule,
                "context": context,
            }
        )

        # Update database with aborted status
        if self.db:
            try:
                self.db.update_workflow_run(
                    self.run_id,
                    status="aborted",
                    error=f"Circuit break: {rule}",
                    completed_at=datetime.utcnow().isoformat() + "Z",
                )
            except Exception:
                pass

    def log_error(self, state: str, error: str):
        """Log error in state."""
        self.log(
            {
                "event": "error",
                "state": state,
                "error": error,
            }
        )

        # Update database with error status
        if self.db:
            try:
                self.db.update_workflow_run(
                    self.run_id,
                    status="error",
                    error=error,
                    completed_at=datetime.utcnow().isoformat() + "Z",
                )
            except Exception:
                pass

    def log_complete(self, final_state: str, total_duration_s: float):
        """Log workflow completion."""
        self.log(
            {
                "event": "workflow_complete",
                "final_state": final_state,
                "duration_s": round(total_duration_s, 2),
            }
        )

        # Update database with completion
        if self.db:
            try:
                self.db.update_workflow_run(
                    self.run_id,
                    status="complete",
                    final_state=final_state,
                    completed_at=datetime.utcnow().isoformat() + "Z",
                    total_tokens=self._total_tokens,
                    total_cost_usd=round(self._total_cost, 6),
                )
            except Exception:
                pass

    def save_output(
        self,
        state_name: str,
        output_type: str,
        content: str,
        agent: Optional[str] = None,
    ):
        """Save a workflow output to the database.

        Args:
            state_name: The workflow state (e.g., "draft", "audit")
            output_type: Type of output (e.g., "draft", "audit", "final")
            content: The actual content
            agent: Optional agent name that produced this output
        """
        if self.db:
            try:
                self.db.save_workflow_output(
                    run_id=self.run_id,
                    state_name=state_name,
                    output_type=output_type,
                    content=content,
                    agent=agent,
                )
            except Exception as e:
                self.log(
                    {"event": "db_error", "error": str(e), "operation": "save_output"}
                )

    def read_log(self) -> list[dict]:
        """Read all log entries from JSONL."""
        if not os.path.exists(self.log_file):
            return []

        entries = []
        with open(self.log_file) as f:
            for line in f:
                if line.strip():
                    entries.append(json.loads(line))
        return entries
