"""SQLModel-backed workflow persistence helpers."""

from __future__ import annotations

from typing import Optional, Union
from uuid import UUID

from sqlalchemy import text

from runner.db.engine import get_session
from runner.content.ids import normalize_user_id
from runner.content.repository import (
    WorkflowRunRepository,
    WorkflowOutputRepository,
    WorkflowPersonaRepository,
    WorkflowSessionRepository,
    WorkflowStateMetricRepository,
)


class WorkflowStore:
    """SQLModel-backed workflow store with ContentDatabase-compatible methods."""

    def __init__(self, user_id: Union[UUID, str, None] = None):
        self.user_id = normalize_user_id(user_id)

    # ---------------------------------------------------------------------
    # Workflow runs
    # ---------------------------------------------------------------------
    def create_workflow_run(
        self, user_id, run_id: str, story: str, workspace_id: Optional[UUID] = None
    ):
        with get_session() as session:
            repo = WorkflowRunRepository(session)
            data = {
                "user_id": normalize_user_id(user_id),
                "run_id": run_id,
                "story": story,
            }
            if workspace_id:
                data["workspace_id"] = workspace_id
            return repo.create(repo.model.model_validate(data))

    def update_workflow_run(self, run_id: str, **kwargs) -> bool:
        with get_session() as session:
            repo = WorkflowRunRepository(session)
            record = repo.get_by_run_id(run_id)
            if not record:
                return False
            for key, value in kwargs.items():
                if hasattr(record, key):
                    setattr(record, key, value)
            session.add(record)
            session.commit()
            session.refresh(record)
            return True

    def get_workflow_run(self, run_id: str):
        with get_session() as session:
            repo = WorkflowRunRepository(session)
            return repo.get_by_run_id(run_id)

    def get_workflow_runs_for_user(self, user_id, limit: int = 50):
        with get_session() as session:
            repo = WorkflowRunRepository(session)
            return repo.list_by_user(normalize_user_id(user_id), limit=limit)

    def get_latest_workflow_run_for_story(self, user_id, story: str):
        """Get the latest workflow run for a story."""
        with get_session() as session:
            repo = WorkflowRunRepository(session)
            return repo.get_latest_by_story(normalize_user_id(user_id), story)

    def get_latest_workflow_run_with_final(self, user_id, story: str):
        """Get the latest workflow run that has a 'final' output."""
        with get_session() as session:
            repo = WorkflowRunRepository(session)
            return repo.get_latest_with_final_output(normalize_user_id(user_id), story)

    # ---------------------------------------------------------------------
    # Workflow outputs
    # ---------------------------------------------------------------------
    def save_workflow_output(
        self,
        run_id: str,
        state_name: str,
        output_type: str,
        content: str,
        agent: Optional[str] = None,
    ):
        with get_session() as session:
            repo = WorkflowOutputRepository(session)
            return repo.create(
                repo.model.model_validate(
                    {
                        "run_id": run_id,
                        "state_name": state_name,
                        "output_type": output_type,
                        "content": content,
                        "agent": agent,
                    }
                )
            )

    def get_workflow_outputs(self, run_id: str):
        with get_session() as session:
            repo = WorkflowOutputRepository(session)
            return repo.list_by_run(run_id)

    def get_workflow_outputs_by_type(self, run_id: str, output_type: str):
        with get_session() as session:
            repo = WorkflowOutputRepository(session)
            return repo.list_by_type(run_id, output_type)

    # ---------------------------------------------------------------------
    # Workflow state metrics
    # ---------------------------------------------------------------------
    def save_state_metrics(
        self,
        run_id: str,
        state_name: str,
        agent: str,
        tokens_input: int = 0,
        tokens_output: int = 0,
        cost_usd: float = 0.0,
        duration_s: float = 0.0,
    ):
        with get_session() as session:
            repo = WorkflowStateMetricRepository(session)
            return repo.create(
                repo.model.model_validate(
                    {
                        "run_id": run_id,
                        "state_name": state_name,
                        "agent": agent,
                        "tokens_input": tokens_input,
                        "tokens_output": tokens_output,
                        "cost_usd": cost_usd,
                        "duration_s": duration_s,
                    }
                )
            )

    def get_state_metrics_by_agent(self, run_id: str) -> dict:
        with get_session() as session:
            rows = session.exec(
                text(
                    """
                    SELECT agent,
                           SUM(tokens_input) AS total_input,
                           SUM(tokens_output) AS total_output,
                           SUM(cost_usd) AS total_cost
                    FROM workflow_state_metrics
                    WHERE run_id = :run_id
                    GROUP BY agent
                    """
                ),
                {"run_id": run_id},
            ).all()
        return {
            row[0]: {
                "input": row[1] or 0,
                "output": row[2] or 0,
                "total": (row[1] or 0) + (row[2] or 0),
                "cost_usd": row[3] or 0,
            }
            for row in rows
        }

    def get_state_metrics_by_state(self, run_id: str) -> dict:
        with get_session() as session:
            rows = session.exec(
                text(
                    """
                    SELECT state_name,
                           SUM(tokens_input + tokens_output) AS total_tokens,
                           SUM(cost_usd) AS total_cost
                    FROM workflow_state_metrics
                    WHERE run_id = :run_id
                    GROUP BY state_name
                    """
                ),
                {"run_id": run_id},
            ).all()
        return {
            row[0]: {
                "tokens": row[1] or 0,
                "cost_usd": row[2] or 0,
            }
            for row in rows
        }

    # ---------------------------------------------------------------------
    # Workflow sessions
    # ---------------------------------------------------------------------
    def save_workflow_session(
        self,
        user_id,
        agent_name: str,
        session_id: str,
        run_id: Optional[str] = None,
    ):
        with get_session() as session:
            repo = WorkflowSessionRepository(session)
            return repo.upsert_session(
                user_id=normalize_user_id(user_id),
                agent_name=agent_name,
                session_id=session_id,
                run_id=run_id,
            )

    def get_workflow_session(
        self,
        user_id,
        agent_name: str,
        run_id: Optional[str] = None,
    ):
        with get_session() as session:
            repo = WorkflowSessionRepository(session)
            return repo.get_by_agent(
                user_id=normalize_user_id(user_id),
                agent_name=agent_name,
                run_id=run_id,
            )

    def delete_workflow_session(
        self,
        user_id,
        agent_name: str,
        run_id: Optional[str] = None,
    ) -> bool:
        with get_session() as session:
            repo = WorkflowSessionRepository(session)
            return repo.delete_by_agent(
                user_id=normalize_user_id(user_id),
                agent_name=agent_name,
                run_id=run_id,
            )

    # ---------------------------------------------------------------------
    # Personas
    # ---------------------------------------------------------------------
    def get_workflow_persona_by_slug(self, user_id, slug: str):
        with get_session() as session:
            repo = WorkflowPersonaRepository(session)
            return repo.get_by_slug(normalize_user_id(user_id), slug)

    @staticmethod
    def _parse_frontmatter(content: str) -> tuple[dict, str]:
        """Parse YAML frontmatter from template content.

        Returns (frontmatter_dict, body) where body has frontmatter stripped.
        """
        if not content.startswith("---"):
            return {}, content

        end = content.find("---", 3)
        if end == -1:
            return {}, content

        frontmatter_raw = content[3:end].strip()
        body = content[end + 3 :].strip()

        # Simple key: value parser (avoids PyYAML dependency for 2 fields)
        fm = {}
        for line in frontmatter_raw.splitlines():
            line = line.strip()
            if ":" in line:
                key, value = line.split(":", 1)
                value = value.strip()
                if value.lower() in ("true", "false"):
                    value = value.lower() == "true"
                fm[key.strip()] = value
        return fm, body

    @staticmethod
    def compose_persona_prompt(
        persona_slug: str,
        voice_profile_slug: str = "servant-leader",
    ) -> str:
        """Compose a full persona prompt from rules + voice_profile + template.

        Reads frontmatter from the template to decide which components to include:
        - needs_voice: true|false — include voice profile (default true)
        - needs_rules: full|core|none — which rules tier (default full)
        """
        import os

        base_dir = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        prompts_dir = os.path.join(base_dir, "prompts")

        # Load template first to read frontmatter
        filename_slug = persona_slug.replace("-", "_")
        template_path = os.path.join(prompts_dir, "templates", f"{filename_slug}.md")
        template_content = ""
        if os.path.exists(template_path):
            with open(template_path) as f:
                template_content = f.read().strip()

        fm, template_body = WorkflowStore._parse_frontmatter(template_content)
        needs_voice = fm.get("needs_voice", True)
        needs_rules = fm.get("needs_rules", "full")

        parts = []

        # Include rules based on frontmatter
        if needs_rules == "full":
            # core + writing rules
            core_path = os.path.join(prompts_dir, "rules", "core.md")
            writing_path = os.path.join(prompts_dir, "rules", "writing.md")
            for rpath in (core_path, writing_path):
                if os.path.exists(rpath):
                    with open(rpath) as f:
                        parts.append(f.read().strip())
            # Fallback to universal_rules.md if split files don't exist yet
            if not parts:
                universal_path = os.path.join(prompts_dir, "universal_rules.md")
                if os.path.exists(universal_path):
                    with open(universal_path) as f:
                        parts.append(f.read().strip())
        elif needs_rules == "core":
            core_path = os.path.join(prompts_dir, "rules", "core.md")
            if os.path.exists(core_path):
                with open(core_path) as f:
                    parts.append(f.read().strip())
            else:
                # Fallback to universal_rules.md if core.md doesn't exist yet
                universal_path = os.path.join(prompts_dir, "universal_rules.md")
                if os.path.exists(universal_path):
                    with open(universal_path) as f:
                        parts.append(f.read().strip())
        # needs_rules == "none" -> skip rules entirely

        # Include voice profile if needed
        if needs_voice:
            voice_path = os.path.join(
                prompts_dir, "voice_profiles", f"{voice_profile_slug}.md"
            )
            if os.path.exists(voice_path):
                with open(voice_path) as f:
                    parts.append(f.read().strip())

        # Append template body (frontmatter stripped)
        if template_body:
            parts.append(template_body)

        return "\n\n".join(parts)
