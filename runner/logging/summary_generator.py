"""Generate human-readable run summaries."""

import os
from typing import Optional

from runner.models import RunManifest
from runner.metrics import RunTokenSummary
from runner.logging.state_logger import StateLogger


class SummaryGenerator:
    """Generates markdown summaries for workflow runs."""

    def __init__(self, run_dir: str, run_id: str):
        self.run_dir = run_dir
        self.run_id = run_id
        self.summary_file = os.path.join(run_dir, "run_summary.md")
        os.makedirs(run_dir, exist_ok=True)

    def generate(
        self,
        manifest: RunManifest,
        token_summary: Optional[RunTokenSummary] = None,
        state_logger: Optional[StateLogger] = None,
    ) -> str:
        """Generate full run summary."""
        lines = []

        lines.append(f"# Workflow Run: {self.run_id}")
        lines.append("")
        lines.append(f"**Story:** {manifest.story}")
        lines.append(f"**Status:** {manifest.status}")

        if manifest.started_at:
            lines.append(f"**Started:** {manifest.started_at.isoformat()}")

        if manifest.completed_at:
            duration = (manifest.completed_at - manifest.started_at).total_seconds()
            lines.append(f"**Duration:** {self._format_duration(duration)}")

        if manifest.final_state:
            lines.append(f"**Final State:** {manifest.final_state}")

        lines.append("")
        lines.append("---")
        lines.append("")

        if token_summary:
            lines.extend(self._generate_token_section(token_summary))

        if state_logger:
            lines.extend(self._generate_state_section(state_logger))

        summary = "\n".join(lines)

        with open(self.summary_file, "w") as f:
            f.write(summary)

        return summary

    def _generate_token_section(self, summary: RunTokenSummary) -> list[str]:
        """Generate token usage section."""
        lines = [
            "## Token Usage Summary",
            "",
            "| Agent | Input | Output | Total | Cost |",
            "|-------|-------|--------|-------|------|",
        ]

        for agent, session in summary.by_agent.items():
            lines.append(
                f"| {agent} | {session.cumulative_input:,} | "
                f"{session.cumulative_output:,} | {session.cumulative_total:,} | "
                f"${session.total_cost_usd:.3f} |"
            )

        lines.append(
            f"| **Total** | **{summary.total_input_tokens:,}** | "
            f"**{summary.total_output_tokens:,}** | **{summary.total_tokens:,}** | "
            f"**${summary.total_cost_usd:.3f}** |"
        )

        lines.append("")
        lines.append("### Context Window Status")
        lines.append("")
        lines.append("| Agent | Used | Max | % Used | Status |")
        lines.append("|-------|------|-----|--------|--------|")

        for agent, session in summary.by_agent.items():
            percent = session.context_used_percent
            status = (
                "Healthy"
                if percent < 60
                else ("Warning" if percent < 80 else "Critical")
            )
            lines.append(
                f"| {agent} | {session.cumulative_total:,} | "
                f"{session.context_window_max:,} | {percent:.1f}% | {status} |"
            )

        lines.append("")
        lines.append("---")
        lines.append("")

        return lines

    def _generate_state_section(self, logger: StateLogger) -> list[str]:
        """Generate state transitions section."""
        lines = [
            "## State Transitions",
            "",
        ]

        entries = logger.read_log()
        transitions = [e for e in entries if e.get("event") == "transition"]

        if transitions:
            lines.append("```")
            for t in transitions:
                lines.append(f"{t['from_state']} → {t['to_state']}")
            lines.append("```")
        else:
            lines.append("*No transitions recorded*")

        lines.append("")

        errors = [e for e in entries if e.get("event") == "error"]
        if errors:
            lines.append("### Errors")
            lines.append("")
            for err in errors:
                lines.append(
                    f"- **{err.get('state', 'unknown')}**: {err.get('error', 'Unknown error')}"
                )
            lines.append("")

        circuit_breaks = [e for e in entries if e.get("event") == "circuit_break"]
        if circuit_breaks:
            lines.append("### Circuit Breaks")
            lines.append("")
            for cb in circuit_breaks:
                lines.append(f"- **Rule:** {cb.get('rule')}")
                ctx = cb.get("context", {})
                lines.append(f"  - Transitions: {ctx.get('transition_count', 0)}")
                lines.append(f"  - Cost: ${ctx.get('total_cost_usd', 0):.2f}")
            lines.append("")

        return lines

    def _format_duration(self, seconds: float) -> str:
        """Format duration in human-readable format."""
        if seconds < 60:
            return f"{seconds:.1f}s"
        elif seconds < 3600:
            minutes = int(seconds // 60)
            secs = int(seconds % 60)
            return f"{minutes}m {secs}s"
        else:
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            return f"{hours}h {minutes}m"
