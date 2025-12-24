import asyncio
from collections import defaultdict
from typing import Any

from fastapi import WebSocket


class WebSocketManager:
    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._connections: dict[str, set[WebSocket]] = defaultdict(set)

    async def connect(self, order_id: str, ws: WebSocket) -> None:
        await ws.accept()
        async with self._lock:
            self._connections[order_id].add(ws)

    async def disconnect(self, order_id: str, ws: WebSocket) -> None:
        async with self._lock:
            self._connections[order_id].discard(ws)
            if not self._connections[order_id]:
                self._connections.pop(order_id, None)

    async def broadcast(self, order_id: str, message: dict[str, Any]) -> None:
        async with self._lock:
            targets = list(self._connections.get(order_id, set()))

        dead: list[WebSocket] = []
        for ws in targets:
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)

        if dead:
            async with self._lock:
                for ws in dead:
                    self._connections.get(order_id, set()).discard(ws)
