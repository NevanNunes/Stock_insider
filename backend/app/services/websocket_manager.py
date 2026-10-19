"""
app/services/websocket_manager.py
───────────────────────────────────
Manages active WebSocket connections from Admin Dashboard clients.

When the anomaly worker detects a HIGH or MEDIUM risk trade, it calls
`broadcast_alert()` which pushes the alert JSON to every connected admin
client instantly — no page refresh needed.

Falls back gracefully if no clients are connected.
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Thread-safe WebSocket connection pool for admin alert broadcasts."""

    def __init__(self):
        self.active_connections: list[WebSocket] = []
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self.active_connections.append(websocket)
        logger.info("Admin WS connected — total connections: %d", len(self.active_connections))

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)
        logger.info("Admin WS disconnected — total connections: %d", len(self.active_connections))

    async def broadcast_alert(self, data: dict[str, Any]) -> None:
        """Push an alert to all connected admin clients."""
        if not self.active_connections:
            return

        message = json.dumps(data)
        dead: list[WebSocket] = []

        async with self._lock:
            connections = list(self.active_connections)

        for ws in connections:
            try:
                await ws.send_text(message)
            except Exception as exc:
                logger.warning("WS send failed (%s) — removing dead connection", exc)
                dead.append(ws)

        for ws in dead:
            await self.disconnect(ws)

    @property
    def connection_count(self) -> int:
        return len(self.active_connections)


# Singleton instance used across the entire application
ws_manager = ConnectionManager()
