"""Tests to verify SQLModel models match database schema.

These tests catch schema drift before it causes runtime errors.
"""

import pytest
from sqlmodel import SQLModel
from sqlalchemy import inspect, MetaData
from sqlalchemy.engine import Engine

from tests.db_utils import get_test_engine, skip_if_no_db


@pytest.fixture
def db_engine():
    """Get database engine, skip if not available."""
    engine = get_test_engine()
    if engine is None:
        pytest.skip("Database not available")
    return engine


@skip_if_no_db
class TestSchemaSyncWorkflowRuns:
    """Verify workflow_runs table matches WorkflowRun model."""

    def test_workflow_runs_columns_exist(self, db_engine):
        """All model columns exist in database table."""
        from runner.db.models.workflow import WorkflowRun

        inspector = inspect(db_engine)
        db_columns = {col["name"] for col in inspector.get_columns("workflow_runs")}

        # Get model columns (excluding relationship fields)
        model_columns = set()
        for field_name, field_info in WorkflowRun.model_fields.items():
            model_columns.add(field_name)

        missing_in_db = model_columns - db_columns
        assert not missing_in_db, f"Columns missing in database: {missing_in_db}"

    def test_workflow_runs_no_extra_required_columns(self, db_engine):
        """No required columns in DB that aren't in model (would cause INSERT failures)."""
        from runner.db.models.workflow import WorkflowRun

        inspector = inspect(db_engine)
        db_columns = inspector.get_columns("workflow_runs")

        model_columns = set(WorkflowRun.model_fields.keys())

        # Find required DB columns not in model
        extra_required = []
        for col in db_columns:
            if not col["nullable"] and col["default"] is None:
                if col["name"] not in model_columns:
                    extra_required.append(col["name"])

        assert not extra_required, f"Required DB columns not in model: {extra_required}"


@skip_if_no_db
class TestSchemaSyncWorkflowOutputs:
    """Verify workflow_outputs table matches WorkflowOutput model."""

    def test_workflow_outputs_columns_exist(self, db_engine):
        """All model columns exist in database table."""
        from runner.db.models.workflow import WorkflowOutput

        inspector = inspect(db_engine)
        db_columns = {col["name"] for col in inspector.get_columns("workflow_outputs")}

        model_columns = set(WorkflowOutput.model_fields.keys())

        missing_in_db = model_columns - db_columns
        assert not missing_in_db, f"Columns missing in database: {missing_in_db}"

    def test_workflow_outputs_no_extra_required_columns(self, db_engine):
        """No required columns in DB that aren't in model."""
        from runner.db.models.workflow import WorkflowOutput

        inspector = inspect(db_engine)
        db_columns = inspector.get_columns("workflow_outputs")

        model_columns = set(WorkflowOutput.model_fields.keys())

        extra_required = []
        for col in db_columns:
            if not col["nullable"] and col["default"] is None:
                if col["name"] not in model_columns:
                    extra_required.append(col["name"])

        assert not extra_required, f"Required DB columns not in model: {extra_required}"


@skip_if_no_db
class TestSchemaSyncUsers:
    """Verify users table matches User model."""

    def test_users_columns_exist(self, db_engine):
        """All model columns exist in database table."""
        from runner.db.models.user import User

        inspector = inspect(db_engine)
        db_columns = {col["name"] for col in inspector.get_columns("users")}

        model_columns = set(User.model_fields.keys())

        missing_in_db = model_columns - db_columns
        assert not missing_in_db, f"Columns missing in database: {missing_in_db}"


@skip_if_no_db
class TestSchemaSyncWorkspaces:
    """Verify workspaces table matches Workspace model."""

    def test_workspaces_columns_exist(self, db_engine):
        """All model columns exist in database table."""
        from runner.db.models.workspace import Workspace

        inspector = inspect(db_engine)
        db_columns = {col["name"] for col in inspector.get_columns("workspaces")}

        model_columns = set(Workspace.model_fields.keys())

        missing_in_db = model_columns - db_columns
        assert not missing_in_db, f"Columns missing in database: {missing_in_db}"
