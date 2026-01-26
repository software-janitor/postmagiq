"""Service for workflow execution with WebSocket events."""

import asyncio
import logging
import os
import tempfile
from datetime import datetime
from typing import Optional, Any
from threading import Thread

from api.models.api_models import WorkflowStatus
from api.services.config_service import get_default_config_path
from api.websocket.manager import manager
from runner.content.ids import normalize_user_id
from runner.content.repository import PostRepository
from runner.content.workflow_store import WorkflowStore
from runner.db.engine import get_session
from runner.config import WORKING_DIR


def _broadcast_from_thread(loop: asyncio.AbstractEventLoop, coro):
    """Schedule a coroutine on the main event loop from a background thread."""
    future = asyncio.run_coroutine_threadsafe(coro, loop)
    try:
        # Wait for result with timeout to catch errors
        future.result(timeout=5.0)
    except Exception as e:
        logging.warning(f"Broadcast failed: {e}")


class WorkflowService:
    """Service for controlling workflow execution."""

    def __init__(self, config_path: str = None):
        # Use LLM_PROVIDER-based config selection if no explicit path provided
        self.config_path = config_path or get_default_config_path()
        self.current_run_id: Optional[str] = None
        self.current_story: Optional[str] = None
        self.current_user_id: Optional[str] = None  # Set during execute()
        self.started_at: Optional[datetime] = None
        self.running = False
        self.awaiting_approval = False
        self._thread: Optional[Thread] = None
        self._state_machine: Optional[Any] = None  # Reference to StateMachine for approval
        self._approval_content: Optional[str] = None  # Content awaiting approval
        self._store: Optional[WorkflowStore] = None  # Created during execute()

    def get_status(self) -> WorkflowStatus:
        """Get current workflow status."""
        return WorkflowStatus(
            running=self.running,
            run_id=self.current_run_id,
            current_state=None,  # Would need state machine access
            story=self.current_story,
            started_at=self.started_at,
            awaiting_approval=self.awaiting_approval,
        )

    async def execute(
        self,
        story: str,
        user_id: str,
        input_path: Optional[str] = None,
        content: Optional[str] = None,
        config: Optional[str] = None,
    ) -> dict:
        """Start workflow execution in background.

        Args:
            story: Story identifier (e.g., "post_04")
            user_id: User ID who is executing the workflow
            input_path: Optional path to input file
            content: Optional input content
            config: Optional workflow config slug (e.g., "groq-production")
        """
        if self.running:
            return {"error": "Workflow already running", "run_id": self.current_run_id}

        self.current_story = story
        self.current_user_id = user_id
        uid = normalize_user_id(user_id)
        if not uid:
            return {"error": "Invalid user ID"}
        self._store = WorkflowStore(uid)
        self.started_at = datetime.utcnow()
        self.running = True
        self._state_machine = None
        self._approval_content = None

        # Capture the main event loop for thread-safe broadcasts
        main_loop = asyncio.get_running_loop()

        # Import here to avoid circular imports
        from runner.runner import WorkflowRunner
        from runner.config import resolve_workflow_config

        # Use provided config or fall back to default
        config_path = resolve_workflow_config(config) if config else self.config_path
        runner = WorkflowRunner(config_path, working_dir=WORKING_DIR)

        # Generate run_id
        self.current_run_id = runner._generate_run_id(story)

        # Create workflow run in database
        self._store.create_workflow_run(self.current_user_id, self.current_run_id, story)

        # Save content to database (primary) and try file (secondary)
        if content:
            # PRIMARY: Save to database
            self._store.save_workflow_output(
                run_id=self.current_run_id,
                state_name="start",
                output_type="input",
                content=content,
                agent=None,
            )

            # SECONDARY: Try to write to file (may fail due to permissions, that's OK)
            try:
                input_dir = "/tmp/workflow/input"
                os.makedirs(input_dir, exist_ok=True)
                input_path = os.path.join(input_dir, f"{story}_input.md")
                with open(input_path, "w") as f:
                    f.write(content)
            except (OSError, PermissionError) as e:
                import logging
                logging.warning(f"File write failed for {story}_input.md: {e}. Content saved to database.")
                input_path = None  # File write failed, but database has content

        # Create approval callback that broadcasts to WebSocket
        def approval_callback(approval_info: dict):
            self.awaiting_approval = True
            self._approval_content = approval_info.get("content")
            # Store state_machine reference (passed via closure from runner)
            # We need to get it from the runner - will be set after StateMachine init
            _broadcast_from_thread(
                main_loop,
                manager.broadcast(
                    {
                        "type": "approval:requested",
                        "run_id": self.current_run_id,
                        "input_path": approval_info.get("input_path"),
                        "content": approval_info.get("content"),
                        "prompt": approval_info.get("prompt"),
                        "timestamp": datetime.utcnow().isoformat(),
                    },
                    self.current_run_id,
                )
            )

        # Broadcast start event
        await manager.broadcast(
            {
                "type": "workflow:started",
                "run_id": self.current_run_id,
                "story": story,
                "timestamp": datetime.utcnow().isoformat(),
            },
            self.current_run_id,
        )

        # Run in background thread (sync code)
        run_id = self.current_run_id
        service = self  # Capture for closure

        # Create log callback that broadcasts events
        def log_callback(event: dict):
            # State machine uses "event" key, some events use "type" key
            event_type = event.get("event") or event.get("type", "")

            # Broadcast state transitions
            if event_type == "state_enter":
                _broadcast_from_thread(
                    main_loop,
                    manager.broadcast(
                        {
                            "type": "state:enter",
                            "run_id": run_id,
                            "current_state": event.get("state"),
                            "timestamp": datetime.utcnow().isoformat(),
                        },
                        run_id,
                    )
                )
            elif event_type == "state_exit":
                _broadcast_from_thread(
                    main_loop,
                    manager.broadcast(
                        {
                            "type": "state:exit",
                            "run_id": run_id,
                            "previous_state": event.get("state"),
                            "timestamp": datetime.utcnow().isoformat(),
                        },
                        run_id,
                    )
                )
            elif event_type == "state_complete":
                # Broadcast state completion with per-agent metrics
                agent_metrics = event.get("agent_metrics", {})
                if agent_metrics:
                    _broadcast_from_thread(
                        main_loop,
                        manager.broadcast(
                            {
                                "type": "metrics:update",
                                "run_id": run_id,
                                "state": event.get("state"),
                                "agent_metrics": agent_metrics,
                                "timestamp": datetime.utcnow().isoformat(),
                            },
                            run_id,
                        )
                    )
            elif event_type == "agent_complete":
                # Broadcast agent completion with output preview
                output_preview = event.get("output", "")[:500] if event.get("output") else None
                _broadcast_from_thread(
                    main_loop,
                    manager.broadcast(
                        {
                            "type": "agent:complete",
                            "run_id": run_id,
                            "agent": event.get("agent"),
                            "output_preview": output_preview,
                            "timestamp": datetime.utcnow().isoformat(),
                        },
                        run_id,
                    )
                )
            elif event_type == "output_written":
                # Broadcast output events based on state
                state = event.get("state", "")
                content = event.get("content", "")
                agent = event.get("agent")
                output_type = None
                db_output_type = None

                if "review" in state:
                    output_type = "output:review"
                    db_output_type = "review"
                elif "process" in state:
                    output_type = "output:processed"
                    db_output_type = "processed"
                elif state == "draft":
                    output_type = "output:draft"
                    db_output_type = "draft"
                elif state == "final-audit":
                    # Distinguish final audit from cross-audit
                    output_type = "output:final-audit"
                    db_output_type = "final_audit"
                elif "audit" in state:
                    output_type = "output:audit"
                    db_output_type = "audit"
                elif "synthesize" in state or "final" in event.get("output_path", ""):
                    output_type = "output:final"
                    db_output_type = "final"

                if output_type and db_output_type:
                    # Save to database
                    service._store.save_workflow_output(
                        run_id=run_id,
                        state_name=state,
                        output_type=db_output_type,
                        content=content,
                        agent=agent,
                    )

                    # Broadcast via WebSocket
                    _broadcast_from_thread(
                        main_loop,
                        manager.broadcast(
                            {
                                "type": output_type,
                                "run_id": run_id,
                                "agent": agent,
                                "content": content,
                                "timestamp": datetime.utcnow().isoformat(),
                            },
                            run_id,
                        )
                    )
            elif event_type == "circuit_break_auto_skip":
                # Notify user that we auto-proceeded due to high score
                _broadcast_from_thread(
                    main_loop,
                    manager.broadcast(
                        {
                            "type": "circuit_break:auto_skip",
                            "run_id": run_id,
                            "reason": event.get("reason"),
                            "skip_to": event.get("skip_to"),
                            "timestamp": datetime.utcnow().isoformat(),
                        },
                        run_id,
                    )
                )
            elif event_type == "circuit_break":
                # Log circuit break detection
                _broadcast_from_thread(
                    main_loop,
                    manager.broadcast(
                        {
                            "type": "circuit_break:detected",
                            "run_id": run_id,
                            "rule": event.get("rule"),
                            "last_score": event.get("last_audit_score"),
                            "timestamp": datetime.utcnow().isoformat(),
                        },
                        run_id,
                    )
                )
            elif event_type in ("session_resume", "session_new"):
                # Log session info for feedback
                _broadcast_from_thread(
                    main_loop,
                    manager.broadcast(
                        {
                            "type": f"session:{event_type.split('_')[1]}",
                            "run_id": run_id,
                            "state": event.get("state"),
                            "session_id": event.get("session_id"),
                            "message": event.get("message"),
                            "timestamp": datetime.utcnow().isoformat(),
                        },
                        run_id,
                    )
                )

        def run_workflow():
            try:
                # We need to capture state_machine from runner
                from runner.state_machine import StateMachine

                # Monkey-patch to capture state_machine
                original_init = StateMachine.initialize

                def capturing_init(sm_self, rid):
                    service._state_machine = sm_self
                    return original_init(sm_self, rid)

                StateMachine.initialize = capturing_init
                try:
                    result = runner.run(
                        story,
                        input_path=input_path,
                        run_id=run_id,
                        approval_callback=approval_callback,
                        log_callback=log_callback,
                    )
                finally:
                    StateMachine.initialize = original_init

                _broadcast_from_thread(main_loop, service._on_complete(result))
            except Exception as e:
                _broadcast_from_thread(main_loop, service._on_error(str(e)))

        self._thread = Thread(target=run_workflow, daemon=True)
        self._thread.start()

        return {"run_id": self.current_run_id, "status": "started"}

    async def execute_step(self, story: str, step: str, run_id: Optional[str] = None) -> dict:
        """Execute a single workflow step."""
        if self.running:
            return {"error": "Workflow already running"}

        from runner.runner import WorkflowRunner

        runner = WorkflowRunner(self.config_path, working_dir=WORKING_DIR)

        # Generate run_id if not provided
        if not run_id:
            run_id = runner._generate_run_id(story)

        try:
            result = runner.run(story, step=step, run_id=run_id)
            return {"run_id": result["run_id"], "result": result}
        except Exception as e:
            return {"error": str(e)}

    async def abort(self) -> dict:
        """Abort running workflow."""
        if not self.running:
            return {"error": "No workflow running"}

        # Note: actual abort logic would need to be added to runner
        self.running = False
        await manager.broadcast(
            {
                "type": "workflow:aborted",
                "run_id": self.current_run_id,
                "timestamp": datetime.utcnow().isoformat(),
            },
            self.current_run_id,
        )
        return {"status": "aborted", "run_id": self.current_run_id}

    async def submit_approval(self, decision: str, feedback: Optional[str] = None) -> dict:
        """Submit human approval response."""
        if not self.awaiting_approval:
            return {"error": "Not awaiting approval"}

        if not self._state_machine:
            return {"error": "No state machine available"}

        # Submit to state machine (unblocks the waiting thread)
        accepted = self._state_machine.submit_approval(decision, feedback)
        if not accepted:
            return {"error": "Approval not accepted (may have timed out)"}

        self.awaiting_approval = False

        await manager.broadcast(
            {
                "type": "approval:received",
                "decision": decision,
                "feedback": feedback,
                "timestamp": datetime.utcnow().isoformat(),
            },
            self.current_run_id,
        )

        return {"status": "submitted"}

    async def pause(self) -> dict:
        """Pause the running workflow at the next checkpoint."""
        if not self.running:
            return {"error": "No workflow running"}

        if not self._state_machine:
            return {"error": "No state machine available"}

        paused = self._state_machine.pause()
        if not paused:
            return {"error": "Could not pause workflow"}

        await manager.broadcast(
            {
                "type": "workflow:paused",
                "run_id": self.current_run_id,
                "current_state": self._state_machine.current_state,
                "timestamp": datetime.utcnow().isoformat(),
            },
            self.current_run_id,
        )

        return {"status": "paused", "current_state": self._state_machine.current_state}

    async def resume(self) -> dict:
        """Resume a paused workflow."""
        if not self.running:
            return {"error": "No workflow running"}

        if not self._state_machine:
            return {"error": "No state machine available"}

        resumed = self._state_machine.resume()
        if not resumed:
            return {"error": "Workflow is not paused"}

        await manager.broadcast(
            {
                "type": "workflow:resumed",
                "run_id": self.current_run_id,
                "current_state": self._state_machine.current_state,
                "timestamp": datetime.utcnow().isoformat(),
            },
            self.current_run_id,
        )

        return {"status": "resumed", "current_state": self._state_machine.current_state}

    def is_paused(self) -> bool:
        """Check if workflow is paused."""
        if not self._state_machine:
            return False
        return self._state_machine.is_paused()

    async def _on_complete(self, result: dict):
        """Handle workflow completion."""
        self.running = False

        # Update workflow run in database
        self._store.update_workflow_run(
            self.current_run_id,
            status="complete",
            final_state=result.get("final_state"),
            total_tokens=result.get("total_tokens", 0),
            total_cost_usd=result.get("total_cost_usd", 0),
            completed_at=datetime.utcnow(),
        )

        # Update post status to "ready" if workflow completed successfully
        if self.current_story and result.get("final_state") == "complete":
            try:
                # Parse post number from story (e.g., "post_04" -> 4)
                import re
                match = re.search(r"post_(\d+)", self.current_story)
                if match:
                    post_number = int(match.group(1))
                    uid = normalize_user_id(self.current_user_id)
                    if uid:
                        with get_session() as session:
                            post_repo = PostRepository(session)
                            post = post_repo.get_by_number(uid, post_number)
                            if post:
                                post.status = "ready"
                                session.add(post)
                                session.commit()
                                logging.info(f"Updated post {post_number} status to 'ready'")
            except Exception as e:
                logging.warning(f"Failed to update post status: {e}")

        await manager.broadcast(
            {
                "type": "workflow:complete",
                "run_id": self.current_run_id,
                "final_state": result.get("final_state"),
                "duration_s": result.get("duration_s"),
                "total_tokens": result.get("total_tokens"),
                "total_cost_usd": result.get("total_cost_usd"),
                "error": result.get("error"),  # Include error if workflow halted
                "timestamp": datetime.utcnow().isoformat(),
            },
            self.current_run_id,
        )

    async def _on_error(self, error: str):
        """Handle workflow error."""
        self.running = False

        # Update workflow run in database
        self._store.update_workflow_run(
            self.current_run_id,
            status="error",
            error=error,
            completed_at=datetime.utcnow(),
        )

        await manager.broadcast(
            {
                "type": "workflow:error",
                "run_id": self.current_run_id,
                "error": error,
                "timestamp": datetime.utcnow().isoformat(),
            },
            self.current_run_id,
        )


# Global instance
workflow_service = WorkflowService()
