"""WebSocket route for real-time updates."""

import json
import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from sqlmodel import Session

from api.auth.jwt import verify_token, VALID_ACCESS_TOKEN_TYPES
from api.websocket.manager import manager
from runner.db.engine import engine
from runner.content.repository import WorkflowRunRepository

router = APIRouter()
logger = logging.getLogger(__name__)


def _extract_token(websocket: WebSocket, token_param: Optional[str]) -> Optional[str]:
    """Extract JWT token from query param or Authorization header."""
    # Try query parameter first
    if token_param:
        return token_param

    # Try Authorization header
    auth_header = websocket.headers.get("authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header[7:]

    return None


def _verify_run_ownership(user_id: UUID, run_id: str) -> bool:
    """Check if user owns the workflow run."""
    with Session(engine) as session:
        repo = WorkflowRunRepository(session)
        run = repo.get_by_run_id(run_id)
        if not run:
            return False
        return run.user_id == user_id


@router.websocket("")
async def websocket_endpoint(
    websocket: WebSocket,
    run_id: Optional[str] = None,
    token: Optional[str] = Query(None),
):
    """WebSocket endpoint for real-time workflow updates.

    Authentication:
        - Query param: ?token=<jwt>
        - Header: Authorization: Bearer <jwt>

    Query params:
        run_id: Optional run ID to subscribe to specific run events
        token: Optional JWT token for authentication
    """
    # Extract and verify token
    jwt_token = _extract_token(websocket, token)
    if not jwt_token:
        await websocket.close(code=4001, reason="Authentication required")
        return

    payload = verify_token(jwt_token)
    if not payload:
        await websocket.close(code=4001, reason="Invalid or expired token")
        return

    # Verify token type
    token_type = payload.get("type")
    if token_type not in VALID_ACCESS_TOKEN_TYPES:
        await websocket.close(code=4001, reason="Invalid token type")
        return

    # Extract user info
    user_id_str = payload.get("sub")
    if not user_id_str:
        await websocket.close(code=4001, reason="Invalid token payload")
        return

    try:
        user_id = UUID(user_id_str)
    except ValueError:
        await websocket.close(code=4001, reason="Invalid user ID in token")
        return

    # If run_id is provided, verify ownership
    if run_id:
        if not _verify_run_ownership(user_id, run_id):
            await websocket.close(code=4003, reason="Access denied to run")
            return

    # Store user_id on websocket for later use
    websocket.state.user_id = user_id

    await manager.connect(websocket, run_id)

    try:
        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                await handle_client_message(websocket, message, user_id)
            except json.JSONDecodeError:
                await manager.send_personal(
                    websocket, {"type": "error", "message": "Invalid JSON"}
                )
    except WebSocketDisconnect:
        manager.disconnect(websocket, run_id)


async def handle_client_message(websocket: WebSocket, message: dict, user_id: UUID):
    """Handle incoming client messages.

    Args:
        websocket: The WebSocket connection
        message: Parsed JSON message from client
        user_id: Authenticated user's UUID
    """
    msg_type = message.get("type")

    if msg_type == "subscribe":
        run_id = message.get("run_id")
        if run_id:
            # Verify ownership before subscribing
            if not _verify_run_ownership(user_id, run_id):
                await manager.send_personal(
                    websocket, {"type": "error", "message": "Access denied to run"}
                )
                return
            await manager.subscribe(websocket, run_id)
            await manager.send_personal(
                websocket, {"type": "subscribed", "run_id": run_id}
            )
        else:
            await manager.send_personal(
                websocket, {"type": "error", "message": "run_id required for subscribe"}
            )

    elif msg_type == "unsubscribe":
        await manager.unsubscribe(websocket)
        await manager.send_personal(websocket, {"type": "unsubscribed"})

    elif msg_type == "ping":
        await manager.send_personal(websocket, {"type": "pong"})

    else:
        await manager.send_personal(
            websocket, {"type": "error", "message": f"Unknown message type: {msg_type}"}
        )
