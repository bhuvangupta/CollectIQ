"""WebSocket connection manager for real-time updates."""

from typing import Dict, List, Any, Optional
from fastapi import WebSocket
import json


class ConnectionManager:
    """Manage WebSocket connections for real-time updates."""

    def __init__(self):
        # General connections (for dashboard, etc.)
        self.active_connections: List[WebSocket] = []

        # Call-specific connections (for live call monitoring)
        self.call_connections: Dict[str, List[WebSocket]] = {}

        # User-specific connections
        self.user_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, call_id: Optional[str] = None):
        """Accept a new WebSocket connection."""
        await websocket.accept()

        if call_id:
            if call_id not in self.call_connections:
                self.call_connections[call_id] = []
            self.call_connections[call_id].append(websocket)
        else:
            self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

        # Remove from call-specific connections
        for call_id, connections in list(self.call_connections.items()):
            if websocket in connections:
                connections.remove(websocket)
                if not connections:
                    del self.call_connections[call_id]

        # Remove from user-specific connections
        for user_id, connections in list(self.user_connections.items()):
            if websocket in connections:
                connections.remove(websocket)
                if not connections:
                    del self.user_connections[user_id]

    async def connect_user(self, websocket: WebSocket, user_id: str):
        """Connect a user-specific WebSocket."""
        await websocket.accept()

        if user_id not in self.user_connections:
            self.user_connections[user_id] = []
        self.user_connections[user_id].append(websocket)

    async def broadcast(self, message: Dict[str, Any]):
        """Broadcast message to all connected clients."""
        disconnected = []

        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.append(connection)

        # Clean up disconnected
        for conn in disconnected:
            self.disconnect(conn)

    async def broadcast_to_call(self, call_id: str, message: Dict[str, Any]):
        """Broadcast message to all clients monitoring a specific call."""
        if call_id not in self.call_connections:
            return

        disconnected = []
        for connection in self.call_connections[call_id]:
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.append(connection)

        for conn in disconnected:
            self.disconnect(conn)

    async def send_to_user(self, user_id: str, message: Dict[str, Any]):
        """Send message to a specific user's connections."""
        if user_id not in self.user_connections:
            return

        disconnected = []
        for connection in self.user_connections[user_id]:
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.append(connection)

        for conn in disconnected:
            self.disconnect(conn)

    async def send_audio(self, websocket: WebSocket, audio_data: bytes):
        """Send audio data to a WebSocket connection."""
        try:
            await websocket.send_bytes(audio_data)
        except Exception:
            self.disconnect(websocket)

    def get_connection_stats(self) -> Dict[str, Any]:
        """Get connection statistics."""
        return {
            "total_connections": len(self.active_connections),
            "call_connections": {
                call_id: len(conns)
                for call_id, conns in self.call_connections.items()
            },
            "user_connections": {
                user_id: len(conns)
                for user_id, conns in self.user_connections.items()
            }
        }
