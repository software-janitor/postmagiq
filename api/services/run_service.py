"""Service for reading and listing workflow runs.

Primary source: Database (workflow_runs, workflow_outputs tables)
Fallback: Filesystem (workflow/runs/) for legacy runs
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

import yaml

logger = logging.getLogger(__name__)

from api.models.api_models import (
    RunSummary,
    StateLogEntry,
    TokenBreakdown,
    ArtifactInfo,
)
from api.utils.credits import cost_to_credits
from runner.content.ids import normalize_user_id
from runner.content.workflow_store import WorkflowStore
from runner.db.models import WorkflowRun, WorkflowOutput


class RunService:
    """Service for accessing workflow run data."""

    def __init__(
        self,
        runs_dir: str = "workflow/runs",
        store: Optional[WorkflowStore] = None,
    ):
        self.runs_dir = Path(runs_dir)
        self.store = store or WorkflowStore()

    def list_runs(self, user_id: str, limit: int = 50) -> list[RunSummary]:
        """List all runs for a user, sorted by newest first.

        Only returns database runs that belong to the user.
        Filesystem runs are legacy and not shown to regular users.

        Args:
            user_id: User ID (required for multi-tenancy)
            limit: Maximum number of runs to return
        """
        runs = []

        # Get runs from database (properly filtered by user_id)
        uid = normalize_user_id(user_id)
        if not uid:
            return []  # Invalid user_id, return empty list

        db_runs = self.store.get_workflow_runs_for_user(uid, limit=limit)
        for run in db_runs:
            runs.append(self._db_run_to_summary(run))

        # NOTE: Filesystem scan removed for security.
        # Legacy runs on filesystem are not associated with users and
        # should only be accessible to the system owner via direct DB query.

        # Sort by start time descending
        runs.sort(key=lambda r: r.started_at or datetime.min, reverse=True)
        return runs[:limit]

    def get_run(self, run_id: str) -> Optional[RunSummary]:
        """Get a specific run by ID (no auth check - use get_run_for_user instead)."""
        # Try database first
        db_run = self.store.get_workflow_run(run_id)
        if db_run:
            return self._db_run_to_summary(db_run)

        # Fallback to filesystem (legacy runs - no user filtering)
        run_dir = self.runs_dir / run_id
        if run_dir.exists():
            return self._load_manifest_from_filesystem(run_dir)

        return None

    def get_run_for_user(self, run_id: str, user_id: str) -> Optional[RunSummary]:
        """Get a specific run by ID, verifying ownership.

        Args:
            run_id: The run ID to fetch
            user_id: The user ID requesting access

        Returns:
            RunSummary if found and user has access, None otherwise
        """
        uid = normalize_user_id(user_id)
        if not uid:
            return None

        # Try database first
        db_run = self.store.get_workflow_run(run_id)
        if db_run:
            # Verify ownership
            if db_run.user_id != uid:
                return None  # User doesn't own this run
            return self._db_run_to_summary(db_run)

        # Filesystem fallback is only for legacy runs - they belong to system owner
        # Regular users cannot access filesystem runs (they should be in DB)
        return None

    def get_state_log(self, run_id: str) -> list[StateLogEntry]:
        """Get state log entries for a run.

        Reads from JSONL file (detailed event log).
        """
        log_path = self.runs_dir / run_id / "state_log.jsonl"
        if not log_path.exists():
            return []

        entries = []
        with open(log_path) as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        data = json.loads(line)
                        entries.append(StateLogEntry(**data))
                    except (json.JSONDecodeError, ValueError):
                        continue
        return entries

    def get_outputs(self, run_id: str) -> list[WorkflowOutput]:
        """Get all outputs for a run from database."""
        return self.store.get_workflow_outputs(run_id)

    def get_outputs_by_type(self, run_id: str, output_type: str) -> list[WorkflowOutput]:
        """Get outputs of a specific type from database."""
        return self.store.get_workflow_outputs_by_type(run_id, output_type)

    def get_summary(self, run_id: str) -> Optional[str]:
        """Get run summary markdown."""
        summary_path = self.runs_dir / run_id / "run_summary.md"
        if not summary_path.exists():
            return None
        return summary_path.read_text()

    def get_token_breakdown(self, run_id: str) -> Optional[TokenBreakdown]:
        """Get token usage breakdown.

        Primary source: Database (workflow_state_metrics table)
        Fallback: State log file parsing (for legacy runs)
        """
        db_run = self.store.get_workflow_run(run_id)
        if not db_run:
            return None

        breakdown = TokenBreakdown()
        breakdown.total_cost_usd = db_run.total_cost_usd or 0

        # Try database metrics first (new runs)
        by_agent = self.store.get_state_metrics_by_agent(run_id)
        by_state = self.store.get_state_metrics_by_state(run_id)

        if by_agent:
            # Database has metrics - use them
            for agent, metrics in by_agent.items():
                breakdown.by_agent[agent] = {
                    "input": metrics["input"],
                    "output": metrics["output"],
                    "total": metrics["total"],
                    "cost_usd": metrics.get("cost_usd", 0),
                }
                breakdown.total_input += metrics["input"]
                breakdown.total_output += metrics["output"]

            for state, metrics in by_state.items():
                breakdown.by_state[state] = {
                    "tokens": metrics["tokens"],
                    "cost_usd": metrics.get("cost_usd", 0),
                }

            return breakdown

        # Fallback: Parse state log for legacy runs
        entries = self.get_state_log(run_id)
        if not entries:
            return breakdown

        for entry in entries:
            if entry.event == "state_complete" and entry.outputs:
                state = entry.state or "unknown"
                state_tokens = 0
                for agent, output in entry.outputs.items():
                    if isinstance(output, dict):
                        tokens = output.get("tokens", 0)
                        if isinstance(tokens, dict):
                            inp = tokens.get("input", 0) or 0
                            out = tokens.get("output", 0) or 0
                            total = inp + out
                        else:
                            total = tokens or 0
                            inp = total // 2
                            out = total - inp

                        state_tokens += total
                        if agent not in breakdown.by_agent:
                            breakdown.by_agent[agent] = {
                                "input": 0,
                                "output": 0,
                                "total": 0,
                            }
                        breakdown.by_agent[agent]["input"] += inp
                        breakdown.by_agent[agent]["output"] += out
                        breakdown.by_agent[agent]["total"] += total
                        breakdown.total_input += inp
                        breakdown.total_output += out

                if state not in breakdown.by_state:
                    breakdown.by_state[state] = {"tokens": 0, "cost_usd": 0}
                breakdown.by_state[state]["tokens"] += state_tokens
                # Legacy runs don't have per-state cost, leave at 0

        return breakdown

    def list_artifacts(self, run_id: str) -> list[ArtifactInfo]:
        """List all artifacts for a specific run.

        Combines database outputs with filesystem artifacts.
        Database outputs take priority (newer runs), filesystem is fallback.
        Deduplicates by artifact name to prevent duplicates.
        """
        artifacts = []
        seen_names = set()
        run_path = self.runs_dir / run_id

        # Get artifacts from database (preferred, takes priority)
        db_outputs = self.store.get_workflow_outputs(run_id)
        for output in db_outputs:
            name = f"{output.state_name}_{output.output_type}.md"
            if name not in seen_names:
                seen_names.add(name)
                artifacts.append(
                    ArtifactInfo(
                        path=f"db://{run_id}/{output.state_name}/{output.output_type}",
                        name=name,
                        type=output.output_type,
                        size_bytes=len(output.content.encode("utf-8")),
                        modified_at=output.created_at or datetime.now(),
                    )
                )

        # Also check filesystem for legacy artifacts (skip if already in DB)
        if run_path.exists():
            artifact_dirs = {
                "drafts": "draft",
                "audits": "audit",
                "final": "final",
                "input": "input",
            }

            for subdir, artifact_type in artifact_dirs.items():
                path = run_path / subdir
                if not path.exists():
                    continue
                for file in path.iterdir():
                    if file.is_file() and not file.name.startswith("."):
                        if file.name not in seen_names:
                            seen_names.add(file.name)
                            stat = file.stat()
                            artifacts.append(
                                ArtifactInfo(
                                    path=str(file),
                                    name=file.name,
                                    type=artifact_type,
                                    size_bytes=stat.st_size,
                                    modified_at=datetime.fromtimestamp(stat.st_mtime),
                                )
                            )

        return artifacts

    def get_artifact_content(self, run_id: str, path: str) -> Optional[str]:
        """Get content of an artifact.

        Handles both database paths (db://...) and filesystem paths.
        """
        # Check for database artifact path
        if path.startswith("db://"):
            # Parse db://run_id/state_name/output_type
            parts = path[5:].split("/")
            if len(parts) >= 3:
                _, state_name, output_type = parts[0], parts[1], parts[2]
                outputs = self.store.get_workflow_outputs_by_type(run_id, output_type)
                for output in outputs:
                    if output.state_name == state_name:
                        return output.content
            return None

        # Filesystem path
        run_path = self.runs_dir / run_id
        if not run_path.exists():
            return None

        file_path = Path(path)

        # Security: ensure path is within the specific run directory
        try:
            resolved = file_path.resolve()
            resolved.relative_to(run_path.resolve())
        except ValueError:
            return None

        if not file_path.exists():
            return None

        return file_path.read_text()

    def _db_run_to_summary(self, run: WorkflowRun) -> RunSummary:
        """Convert database record to API summary."""
        started_at = run.started_at or datetime.now()
        completed_at = run.completed_at
        cost_usd = run.total_cost_usd or 0.0
        return RunSummary(
            run_id=run.run_id,
            story=run.story or "unknown",
            status=run.status,
            started_at=started_at,
            completed_at=completed_at,
            total_tokens=run.total_tokens,
            total_cost_usd=cost_usd,
            credits=cost_to_credits(cost_usd),
            final_state=run.final_state,
            config_hash=None,  # Not stored in DB yet
        )

    def _load_manifest_from_filesystem(self, run_dir: Path) -> Optional[RunSummary]:
        """Load run manifest from filesystem (legacy support)."""
        manifest_path = run_dir / "run_manifest.yaml"
        if not manifest_path.exists():
            return None

        try:
            with open(manifest_path) as f:
                data = yaml.safe_load(f)

            # Parse datetime strings
            started_at = data.get("started_at")
            if isinstance(started_at, str):
                started_at = datetime.fromisoformat(started_at.replace("Z", "+00:00"))

            completed_at = data.get("completed_at")
            if isinstance(completed_at, str):
                completed_at = datetime.fromisoformat(completed_at.replace("Z", "+00:00"))

            cost_usd = data.get("total_cost_usd", 0.0)
            return RunSummary(
                run_id=data.get("run_id", run_dir.name),
                story=data.get("story", ""),
                status=data.get("status", "unknown"),
                started_at=started_at or datetime.now(),
                completed_at=completed_at,
                total_tokens=data.get("total_tokens", 0),
                total_cost_usd=cost_usd,
                credits=cost_to_credits(cost_usd),
                final_state=data.get("final_state"),
                config_hash=data.get("config_hash"),
            )
        except Exception as e:
            logger.warning(f"Failed to load manifest from {manifest_path}: {e}")
            return None
