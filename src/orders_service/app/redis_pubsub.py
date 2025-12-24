import json
from typing import Any

import redis.asyncio as redis

from .websocket_manager import WebSocketManager

CHANNEL_ORDER_STATUS = "order_status"


async def publish_order_status(redis_url: str, message: dict[str, Any]) -> None:
    r = redis.from_url(redis_url, decode_responses=True)
    try:
        await r.publish(CHANNEL_ORDER_STATUS, json.dumps(message))
    finally:
        await r.close()


async def redis_listener(redis_url: str, ws_manager: WebSocketManager) -> None:
    r = redis.from_url(redis_url, decode_responses=True)
    pubsub = r.pubsub()
    await pubsub.subscribe(CHANNEL_ORDER_STATUS)
    try:
        async for item in pubsub.listen():
            if item is None:
                continue
            if item.get("type") != "message":
                continue
            data_raw = item.get("data")
            try:
                message = json.loads(data_raw)
                order_id = message.get("order_id")
                if order_id:
                    await ws_manager.broadcast(order_id, message)
            except Exception:
                continue
    finally:
        try:
            await pubsub.close()
        finally:
            await r.close()
