"""WebSocket connection manager for real-time updates."""

import json
from typing import Optional
from fastapi import WebSocket


class ConnectionManager:
    """Manages WebSocket connections and broadcasts."""

    def __init__(self):
        # Connections subscribed to a specific run
        self.run_connections: dict[str, set[WebSocket]] = {}
        # Global connections (receive all events)
        self.global_connections: set[WebSocket] = set()

    async def connect(self, websocket: WebSocket, run_id: Optional[str] = None):
        """Accept a new WebSocket connection."""
        await websocket.accept()
        if run_id:
            if run_id not in self.run_connections:
                self.run_connections[run_id] = set()
            self.run_connections[run_id].add(websocket)
        else:
            self.global_connections.add(websocket)

    def disconnect(self, websocket: WebSocket, run_id: Optional[str] = None):
        """Remove a WebSocket connection."""
        self.global_connections.discard(websocket)
        if run_id and run_id in self.run_connections:
            self.run_connections[run_id].discard(websocket)
            if not self.run_connections[run_id]:
                del self.run_connections[run_id]
        # Also check all run connections
        for run_sockets in self.run_connections.values():
            run_sockets.discard(websocket)

    async def subscribe(self, websocket: WebSocket, run_id: str):
        """Subscribe a connection to a specific run."""
        self.global_connections.discard(websocket)
        if run_id not in self.run_connections:
            self.run_connections[run_id] = set()
        self.run_connections[run_id].add(websocket)

    async def unsubscribe(self, websocket: WebSocket):
        """Unsubscribe from specific runs, become global listener."""
        for run_sockets in self.run_connections.values():
            run_sockets.discard(websocket)
        self.global_connections.add(websocket)

    async def broadcast(self, event: dict, run_id: Optional[str] = None):
        """Broadcast event to subscribers.

        If run_id is provided, sends to run subscribers + global.
        Otherwise, sends only to global subscribers.
        """
        message = json.dumps(event)
        targets = self.global_connections.copy()

        if run_id and run_id in self.run_connections:
            targets.update(self.run_connections[run_id])

        dead_connections = []
        for connection in targets:
            try:
                await connection.send_text(message)
            except Exception:
                dead_connections.append(connection)

        # Clean up dead connections
        for conn in dead_connections:
            self.disconnect(conn)

    async def send_personal(self, websocket: WebSocket, event: dict):
        """Send event to a specific connection."""
        try:
            await websocket.send_text(json.dumps(event))
        except Exception:
            self.disconnect(websocket)


# Global instance
manager = ConnectionManager()
