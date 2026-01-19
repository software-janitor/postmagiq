"""SQLModel-backed workflow persistence helpers."""

from __future__ import annotations

from datetime import datetime
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
    def create_workflow_run(self, user_id, run_id: str, story: str):
        with get_session() as session:
            repo = WorkflowRunRepository(session)
            return repo.create(
                repo.model.model_validate(
                    {
                        "user_id": normalize_user_id(user_id),
                        "run_id": run_id,
                        "story": story,
                    }
                )
            )

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
    def compose_persona_prompt(
        persona_slug: str,
        voice_profile_slug: str = "matthew-garcia",
    ) -> str:
        """Compose a full persona prompt from universal_rules + voice_profile + template."""
        import os

        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        prompts_dir = os.path.join(base_dir, "prompts")

        parts = []
        universal_path = os.path.join(prompts_dir, "universal_rules.md")
        if os.path.exists(universal_path):
            with open(universal_path) as f:
                parts.append(f.read().strip())

        voice_path = os.path.join(prompts_dir, "voice_profiles", f"{voice_profile_slug}.md")
        if os.path.exists(voice_path):
            with open(voice_path) as f:
                parts.append(f.read().strip())

        filename_slug = persona_slug.replace("-", "_")
        template_path = os.path.join(prompts_dir, "templates", f"{filename_slug}.md")
        if os.path.exists(template_path):
            with open(template_path) as f:
                parts.append(f.read().strip())
        else:
            legacy_path = os.path.join(prompts_dir, f"{filename_slug}_persona.md")
            if os.path.exists(legacy_path):
                with open(legacy_path) as f:
                    parts.append(f.read().strip())

        return "\n\n".join(parts)
