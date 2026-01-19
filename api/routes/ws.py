"""WebSocket route for real-time updates."""

import json
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from api.websocket.manager import manager

router = APIRouter()


@router.websocket("")
async def websocket_endpoint(websocket: WebSocket, run_id: Optional[str] = None):
    """WebSocket endpoint for real-time workflow updates.

    Query params:
        run_id: Optional run ID to subscribe to specific run events
    """
    await manager.connect(websocket, run_id)

    try:
        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                await handle_client_message(websocket, message)
            except json.JSONDecodeError:
                await manager.send_personal(
                    websocket, {"type": "error", "message": "Invalid JSON"}
                )
    except WebSocketDisconnect:
        manager.disconnect(websocket, run_id)


async def handle_client_message(websocket: WebSocket, message: dict):
    """Handle incoming client messages."""
    msg_type = message.get("type")

    if msg_type == "subscribe":
        run_id = message.get("run_id")
        if run_id:
            await manager.subscribe(websocket, run_id)
            await manager.send_personal(
                websocket, {"type": "subscribed", "run_id": run_id}
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
