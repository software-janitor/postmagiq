"""Main entry point for workflow orchestration."""

import argparse
import hashlib
import os
import shutil
import sys
import yaml
from datetime import datetime
from typing import Optional

from runner.models import RunManifest
from runner.state_machine import StateMachine
from runner.logging import StateLogger, AgentLogger, SummaryGenerator
from runner.content.ids import get_system_user_id
from runner.content.workflow_store import WorkflowStore


class WorkflowRunner:
    """Main workflow runner that coordinates all components."""

    def __init__(self, config_path: str, working_dir: str = "workflow"):
        self.config_path = config_path
        self.working_dir = working_dir
        self.config = self._load_config()
        self.runs_dir = os.path.join(working_dir, "runs")

        # Initialize database-backed workflow store (primary storage)
        self.db = WorkflowStore(get_system_user_id())

    def _load_config(self) -> dict:
        """Load and validate config file."""
        with open(self.config_path) as f:
            config = yaml.safe_load(f)

        required_sections = ["states"]
        for section in required_sections:
            if section not in config:
                raise ValueError(f"Missing required config section: {section}")

        return config

    def _get_config_hash(self) -> str:
        """Get hash of config for tracking."""
        with open(self.config_path, "rb") as f:
            return hashlib.md5(f.read()).hexdigest()[:8]

    def _generate_run_id(self, story: str) -> str:
        """Generate unique run ID."""
        timestamp = datetime.utcnow().strftime("%Y-%m-%d_%H%M%S")
        return f"{timestamp}_{story}"

    def _resolve_story_input(
        self, story: str, input_path: Optional[str] = None, interactive: bool = False,
        run_dir: Optional[str] = None
    ) -> str:
        """Resolve story to input file and copy to run-specific directory.

        Search order:
        1. Explicit input_path if provided
        2. ../story_bank/processed/{story}.md
        3. ../story_bank/raw/{story}.txt
        4. If interactive=True, prompt user to paste content

        Returns path to the input file.
        """
        input_dir = os.path.join(run_dir or self.working_dir, "input")
        os.makedirs(input_dir, exist_ok=True)
        dest_path = os.path.join(input_dir, "story_input.md")

        if input_path:
            if not os.path.exists(input_path):
                raise FileNotFoundError(f"Input file not found: {input_path}")
            shutil.copy(input_path, dest_path)
            return dest_path

        search_paths = [
            f"../story_bank/processed/{story}.md",
            f"../story_bank/raw/{story}.txt",
            f"story_bank/processed/{story}.md",
            f"story_bank/raw/{story}.txt",
        ]

        for path in search_paths:
            if os.path.exists(path):
                shutil.copy(path, dest_path)
                print(f"Using story from: {path}")
                return dest_path

        if interactive:
            return self._prompt_for_content(dest_path, story)

        raise FileNotFoundError(
            f"Story not found. Searched:\n" +
            "\n".join(f"  - {p}" for p in search_paths) +
            f"\n\nOptions:\n" +
            f"  --input PATH   Provide explicit file path\n" +
            f"  --interactive  Paste content directly"
        )

    def _prompt_for_content(self, dest_path: str, story: str) -> str:
        """Prompt user to paste story content."""
        print(f"\n{'='*60}")
        print(f"PASTE STORY CONTENT FOR: {story}")
        print(f"{'='*60}")
        print("Paste your raw story content below.")
        print("When done, enter a blank line followed by 'END' on its own line.")
        print(f"{'='*60}\n")

        lines = []
        blank_seen = False
        try:
            while True:
                line = input()
                if blank_seen and line.strip().upper() == "END":
                    break
                if line == "":
                    blank_seen = True
                else:
                    blank_seen = False
                lines.append(line)
        except EOFError:
            pass

        content = "\n".join(lines).strip()

        if not content:
            raise ValueError("No content provided")

        with open(dest_path, "w") as f:
            f.write(content)

        print(f"\nSaved {len(content)} characters to {dest_path}")
        return dest_path

    def run(
        self,
        story: str,
        input_path: Optional[str] = None,
        start_state: str = "start",
        step: Optional[str] = None,
        interactive: bool = False,
        run_id: Optional[str] = None,
        approval_callback: Optional[callable] = None,
        log_callback: Optional[callable] = None,
    ) -> dict:
        """Execute a workflow run.

        Args:
            story: Story identifier (e.g., "post_03")
            input_path: Optional explicit path to story file
            start_state: State to start from (default: "start")
            step: Optional single step to execute
            interactive: Prompt for content paste if story not found
            run_id: Optional run ID (generated if not provided)
            approval_callback: Called when human approval is needed (API mode)
            log_callback: External callback for workflow events (API mode)

        Returns:
            dict with run results
        """
        run_id = run_id or self._generate_run_id(story)
        run_dir = os.path.join(self.runs_dir, run_id)
        session_dir = os.path.join(self.working_dir, "sessions")

        os.makedirs(run_dir, exist_ok=True)
        os.makedirs(session_dir, exist_ok=True)

        self._resolve_story_input(story, input_path, interactive, run_dir)

        state_logger = StateLogger(run_dir, run_id, db=self.db)
        agent_logger = AgentLogger(run_dir)
        summary_generator = SummaryGenerator(run_dir, run_id)

        manifest = RunManifest(
            run_id=run_id,
            story=story,
            started_at=datetime.utcnow(),
            config_hash=self._get_config_hash(),
        )

        state_logger.log_start(story, manifest.config_hash)

        # External callback passed from API
        external_log_callback = log_callback

        def internal_log_callback(event: dict):
            event_type = event.get("event") or event.get("type")
            if event_type == "state_enter":
                state_logger.log_state_enter(
                    event["state"],
                    event.get("type", "unknown"),
                    event.get("has_feedback", False),
                )
            elif event_type == "state_complete":
                # Convert agent_metrics to outputs format for StateLogger
                outputs = None
                agent_metrics = event.get("agent_metrics")
                if agent_metrics:
                    outputs = {}
                    for agent, metrics in agent_metrics.items():
                        outputs[agent] = {
                            "tokens": {
                                "input": metrics.get("tokens_input", 0),
                                "output": metrics.get("tokens_output", 0),
                            },
                            "cost": metrics.get("cost_usd", 0),
                            "status": "success",
                        }
                state_logger.log_state_complete(
                    event["state"],
                    event["transition"],
                    event["duration_s"],
                    outputs,
                )
            elif event_type == "transition":
                state_logger.log_transition(event["from"], event["to"])
            elif event_type == "circuit_break":
                state_logger.log_circuit_break(event["rule"], event["context"])
            elif event_type in ("error", "state_error"):
                state_logger.log_error(event.get("state", "unknown"), event.get("error", ""))

            # Also call external callback if provided
            if external_log_callback:
                external_log_callback(event)

        state_machine = StateMachine(
            self.config,
            session_dir=session_dir,
            log_callback=internal_log_callback,
            run_dir=run_dir,
            agent_logger=agent_logger,
            approval_callback=approval_callback,
            database=self.db,  # Primary storage
        )
        state_machine.initialize(run_id)

        # Save initial story input to database
        story_input_path = os.path.join(run_dir, "input", "story_input.md")
        if os.path.exists(story_input_path):
            with open(story_input_path) as f:
                story_content = f.read()
            self.db.save_workflow_output(
                run_id=run_id,
                state_name="start",
                output_type="input",
                content=story_content,
                agent=None,
            )

        error = None
        if step:
            state_config = self.config["states"].get(step)
            if not state_config:
                raise ValueError(f"Unknown state: {step}")
            state_result = state_machine.execute_state(step, state_config)
            final_state = state_result.transition
        else:
            run_result = state_machine.run(start_state)
            final_state = run_result.get("final_state")
            error = run_result.get("error")

        manifest.completed_at = datetime.utcnow()
        if final_state == "complete":
            manifest.status = "complete"
        elif final_state == "halt":
            manifest.status = "halted"
        else:
            manifest.status = "failed"
        manifest.final_state = final_state

        if state_machine.token_tracker:
            summary = state_machine.token_tracker.get_summary()
            manifest.total_tokens = summary.total_tokens
            manifest.total_cost_usd = summary.total_cost_usd

        duration = (manifest.completed_at - manifest.started_at).total_seconds()
        state_logger.log_complete(final_state, duration)

        summary_generator.generate(
            manifest,
            token_summary=state_machine.token_tracker.get_summary() if state_machine.token_tracker else None,
            state_logger=state_logger,
        )

        self._save_manifest(run_dir, manifest)

        return {
            "run_id": run_id,
            "run_dir": run_dir,
            "final_state": final_state,
            "duration_s": duration,
            "total_tokens": manifest.total_tokens,
            "total_cost_usd": manifest.total_cost_usd,
            "error": error,
        }

    def _save_manifest(self, run_dir: str, manifest: RunManifest):
        """Save run manifest to YAML (atomic write)."""
        manifest_path = os.path.join(run_dir, "run_manifest.yaml")
        tmp_path = manifest_path + ".tmp"
        with open(tmp_path, "w") as f:
            yaml.dump(manifest.model_dump(mode="json"), f, default_flow_style=False)
        os.replace(tmp_path, manifest_path)

    def list_runs(self) -> list[dict]:
        """List all runs."""
        if not os.path.exists(self.runs_dir):
            return []

        runs = []
        for run_id in sorted(os.listdir(self.runs_dir), reverse=True):
            manifest_path = os.path.join(self.runs_dir, run_id, "run_manifest.yaml")
            if os.path.exists(manifest_path):
                with open(manifest_path) as f:
                    runs.append(yaml.safe_load(f))
        return runs

    def get_run(self, run_id: str) -> Optional[dict]:
        """Get details for a specific run."""
        manifest_path = os.path.join(self.runs_dir, run_id, "run_manifest.yaml")
        if not os.path.exists(manifest_path):
            return None

        with open(manifest_path) as f:
            return yaml.safe_load(f)


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Workflow Orchestrator")
    parser.add_argument(
        "--config",
        "-c",
        default="workflow_config.yaml",
        help="Path to workflow config",
    )
    parser.add_argument(
        "--story",
        "-s",
        help="Story identifier (e.g., post_03)",
    )
    parser.add_argument(
        "--input",
        "-i",
        help="Explicit path to story input file",
    )
    parser.add_argument(
        "--step",
        help="Execute single step instead of full workflow",
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Prompt to paste content if story not found",
    )
    parser.add_argument(
        "--list-runs",
        action="store_true",
        help="List all runs",
    )
    parser.add_argument(
        "--working-dir",
        "-w",
        default="workflow",
        help="Working directory",
    )

    args = parser.parse_args()

    if not os.path.exists(args.config):
        print(f"Error: Config file not found: {args.config}", file=sys.stderr)
        sys.exit(1)

    runner = WorkflowRunner(args.config, args.working_dir)

    if args.list_runs:
        runs = runner.list_runs()
        if not runs:
            print("No runs found.")
        else:
            print(f"{'Run ID':<35} {'Status':<10} {'Story':<15} {'Cost'}")
            print("-" * 70)
            for run in runs:
                cost = run.get("total_cost_usd", 0)
                print(
                    f"{run['run_id']:<35} {run.get('status', 'unknown'):<10} "
                    f"{run.get('story', ''):<15} ${cost:.3f}"
                )
        return

    if not args.story:
        parser.error("--story is required unless using --list-runs")

    try:
        result = runner.run(
            args.story,
            input_path=args.input,
            step=args.step,
            interactive=args.interactive,
        )

        print(f"\nRun complete: {result['run_id']}")
        print(f"Final state: {result['final_state']}")
        print(f"Duration: {result['duration_s']:.1f}s")
        print(f"Tokens: {result['total_tokens']:,}")
        print(f"Cost: ${result['total_cost_usd']:.3f}")

        if result.get("error"):
            print(f"Error: {result['error']}", file=sys.stderr)
            sys.exit(1)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
