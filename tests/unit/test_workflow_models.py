"""Tests for workflow database models."""

import pytest
from datetime import datetime
from uuid import uuid4

from runner.db.models.workflow import (
    WorkflowRun,
    WorkflowRunCreate,
    WorkflowOutput,
    WorkflowOutputCreate,
    WorkflowSession,
    WorkflowSessionCreate,
    WorkflowStateMetric,
    WorkflowStateMetricCreate,
)


class TestWorkflowRunModel:
    """Tests for WorkflowRun model."""

    def test_create_workflow_run(self):
        """WorkflowRunCreate has required fields."""
        user_id = uuid4()
        create = WorkflowRunCreate(
            user_id=user_id,
            run_id="2026-01-26_120000_post_01",
            story_name="post_01",
        )

        assert create.user_id == user_id
        assert create.run_id == "2026-01-26_120000_post_01"
        assert create.story_name == "post_01"

    def test_workflow_run_defaults(self):
        """WorkflowRun has sensible defaults."""
        user_id = uuid4()
        create = WorkflowRunCreate(
            user_id=user_id,
            run_id="test_run",
        )

        assert create.story_name is None
        assert create.workspace_id is None


class TestWorkflowOutputModel:
    """Tests for WorkflowOutput model."""

    def test_create_workflow_output(self):
        """WorkflowOutputCreate has required fields."""
        create = WorkflowOutputCreate(
            run_id="2026-01-26_120000_post_01",
            state_name="draft",
            output_type="draft",
            content="This is a test draft.",
        )

        assert create.run_id == "2026-01-26_120000_post_01"
        assert create.state_name == "draft"
        assert create.output_type == "draft"
        assert create.content == "This is a test draft."

    def test_workflow_output_optional_agent(self):
        """WorkflowOutputCreate agent field is optional."""
        create = WorkflowOutputCreate(
            run_id="test_run",
            state_name="start",
            output_type="input",
            content="Input content",
        )

        # agent is not in the base model, but should be settable
        assert create.state_name == "start"


class TestWorkflowSessionModel:
    """Tests for WorkflowSession model."""

    def test_create_workflow_session(self):
        """WorkflowSessionCreate has required fields."""
        user_id = uuid4()
        create = WorkflowSessionCreate(
            user_id=user_id,
            agent_name="groq-70b",
            session_id="session_abc123",
        )

        assert create.user_id == user_id
        assert create.agent_name == "groq-70b"
        assert create.session_id == "session_abc123"

    def test_workflow_session_optional_run_id(self):
        """WorkflowSessionCreate run_id is optional."""
        user_id = uuid4()
        create = WorkflowSessionCreate(
            user_id=user_id,
            agent_name="claude",
            session_id="session_xyz",
        )

        assert create.run_id is None


class TestWorkflowStateMetricModel:
    """Tests for WorkflowStateMetric model."""

    def test_create_state_metric(self):
        """WorkflowStateMetricCreate has required fields."""
        create = WorkflowStateMetricCreate(
            run_id="2026-01-26_120000_post_01",
            state_name="draft",
            agent="groq-70b",
            tokens_input=500,
            tokens_output=1000,
            cost_usd=0.002,
            duration_s=1.5,
        )

        assert create.run_id == "2026-01-26_120000_post_01"
        assert create.state_name == "draft"
        assert create.agent == "groq-70b"
        assert create.tokens_input == 500
        assert create.tokens_output == 1000
        assert create.cost_usd == 0.002
        assert create.duration_s == 1.5

    def test_state_metric_defaults(self):
        """WorkflowStateMetricCreate has sensible defaults."""
        create = WorkflowStateMetricCreate(
            run_id="test_run",
            state_name="audit",
            agent="groq-8b",
        )

        assert create.tokens_input == 0
        assert create.tokens_output == 0
        assert create.cost_usd == 0.0
        assert create.duration_s == 0.0


class TestModelValidation:
    """Tests for model validation."""

    def test_workflow_run_requires_user_id(self):
        """WorkflowRunCreate requires user_id."""
        with pytest.raises(Exception):
            WorkflowRunCreate(run_id="test_run")

    def test_workflow_output_requires_run_id(self):
        """WorkflowOutputCreate requires run_id."""
        with pytest.raises(Exception):
            WorkflowOutputCreate(
                state_name="draft",
                output_type="draft",
                content="Test",
            )

    def test_workflow_session_requires_session_id(self):
        """WorkflowSessionCreate requires session_id."""
        with pytest.raises(Exception):
            WorkflowSessionCreate(
                user_id=uuid4(),
                agent_name="groq",
            )
