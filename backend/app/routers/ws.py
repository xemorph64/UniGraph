from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Dict
import asyncio
import json
import structlog

router = APIRouter()
logger = structlog.get_logger()


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, investigator_id: str):
        await websocket.accept()
        self.active_connections[investigator_id] = websocket

    def disconnect(self, investigator_id: str):
        self.active_connections.pop(investigator_id, None)

    async def broadcast_alert(self, alert_data: dict):
        message = json.dumps({"type": "ALERT_FIRED", **alert_data})
        if not self.active_connections:
            return

        connections = list(self.active_connections.items())
        disconnected: list[str] = []
        results = await asyncio.gather(
            *(ws.send_text(message) for _, ws in connections),
            return_exceptions=True,
        )

        for (investigator_id, _), result in zip(connections, results):
            if isinstance(result, Exception):
                logger.warning(
                    "ws_alert_send_failed",
                    investigator_id=investigator_id,
                    error=str(result),
                )
                disconnected.append(investigator_id)

        for investigator_id in disconnected:
            self.disconnect(investigator_id)

    async def send_personal(self, investigator_id: str, message: dict):
        ws = self.active_connections.get(investigator_id)
        if ws:
            await ws.send_text(json.dumps(message))


manager = ConnectionManager()


@router.websocket("/ws/alerts/{investigator_id}")
async def websocket_alerts(websocket: WebSocket, investigator_id: str):
    """WebSocket endpoint for live alert stream."""
    await manager.connect(websocket, investigator_id)
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            if message.get("type") == "ACKNOWLEDGE":
                alert_id = message.get("alert_id")
                await manager.send_personal(
                    investigator_id,
                    {
                        "type": "ACKNOWLEDGED",
                        "alert_id": alert_id,
                        "status": "acknowledged",
                    },
                )
    except WebSocketDisconnect:
        manager.disconnect(investigator_id)
