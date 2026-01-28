"""Unit tests for credit deduction on workflow completion."""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from uuid import uuid4


def _make_service(workspace_id=None, run_id="run-123", story="post_01"):
    """Create a WorkflowService with mocked internals."""
    with patch("api.services.workflow_service.get_default_config_path", return_value="/tmp/fake.yaml"):
        from api.services.workflow_service import WorkflowService
        svc = WorkflowService(config_path="/tmp/fake.yaml")
    svc.current_workspace_id = workspace_id
    svc.current_run_id = run_id
    svc.current_story = story
    svc.current_user_id = "user-abc"
    svc._store = MagicMock()
    return svc


@pytest.mark.asyncio
async def test_credit_deducted_on_complete():
    """reserve_credit + confirm_usage called when final_state == complete."""
    ws_id = uuid4()
    svc = _make_service(workspace_id=ws_id, run_id="run-42")

    mock_usage_svc = MagicMock()

    with patch("api.services.workflow_service.manager") as mock_mgr, \
         patch("api.services.usage_service.UsageService", return_value=mock_usage_svc):
        mock_mgr.broadcast = AsyncMock()
        await svc._on_complete({"final_state": "complete", "total_tokens": 100, "total_cost_usd": 0.5})

    mock_usage_svc.reserve_credit.assert_called_once_with(
        workspace_id=ws_id,
        resource_type="post",
        idempotency_key="workflow-run:run-42",
        amount=1,
    )
    mock_usage_svc.confirm_usage.assert_called_once_with("workflow-run:run-42")


@pytest.mark.asyncio
async def test_no_credit_on_halt():
    """No credit deducted when final_state == halt."""
    ws_id = uuid4()
    svc = _make_service(workspace_id=ws_id)

    mock_usage_svc = MagicMock()

    with patch("api.services.workflow_service.manager") as mock_mgr, \
         patch("api.services.usage_service.UsageService", return_value=mock_usage_svc):
        mock_mgr.broadcast = AsyncMock()
        await svc._on_complete({"final_state": "halt"})

    mock_usage_svc.reserve_credit.assert_not_called()
    mock_usage_svc.confirm_usage.assert_not_called()


@pytest.mark.asyncio
async def test_no_credit_when_no_workspace():
    """No credit deducted when workspace_id is None."""
    svc = _make_service(workspace_id=None)

    mock_usage_svc = MagicMock()

    with patch("api.services.workflow_service.manager") as mock_mgr, \
         patch("api.services.usage_service.UsageService", return_value=mock_usage_svc):
        mock_mgr.broadcast = AsyncMock()
        await svc._on_complete({"final_state": "complete"})

    mock_usage_svc.reserve_credit.assert_not_called()
    mock_usage_svc.confirm_usage.assert_not_called()


@pytest.mark.asyncio
async def test_credit_error_logged_not_raised():
    """UsageLimitExceeded is caught and logged, doesn't crash workflow."""
    from api.services.usage_service import UsageLimitExceeded

    ws_id = uuid4()
    svc = _make_service(workspace_id=ws_id, run_id="run-err")

    mock_usage_svc = MagicMock()
    mock_usage_svc.reserve_credit.side_effect = UsageLimitExceeded("post", 10, 10)

    with patch("api.services.workflow_service.manager") as mock_mgr, \
         patch("api.services.usage_service.UsageService", return_value=mock_usage_svc), \
         patch("api.services.workflow_service.logging") as mock_log:
        mock_mgr.broadcast = AsyncMock()
        # Should not raise
        await svc._on_complete({"final_state": "complete", "total_tokens": 0, "total_cost_usd": 0})

    mock_log.warning.assert_called()
    assert "run-err" in str(mock_log.warning.call_args)
