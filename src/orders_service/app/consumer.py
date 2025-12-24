import json
from typing import Any

from sqlalchemy.dialects.postgresql import insert

from .db import SessionLocal
from .models import InboxMessage, OrderStatus
from .crud import update_order_status
from .messaging import RabbitMQ
from .redis_pubsub import publish_order_status


def _parse_message(body: bytes) -> dict[str, Any]:
    return json.loads(body.decode("utf-8"))


async def payment_result_consumer(rmq: RabbitMQ, redis_url: str) -> None:
    queue = await rmq.declare_orders_payment_results_queue()

    async with queue.iterator() as q:
        async for msg in q:
            try:
                await _handle_payment_result(msg=msg, redis_url=redis_url)
                await msg.ack()
            except Exception:
                await msg.nack(requeue=True)


async def _handle_payment_result(*, msg, redis_url: str) -> None:
    message_id = msg.message_id or ""
    envelope = _parse_message(msg.body)

    payload = envelope.get("payload", {})
    order_id = payload.get("order_id")
    payment_status = payload.get("payment_status")
    if not order_id or payment_status not in ("succeeded", "failed"):
        return

    new_status = OrderStatus.FINISHED if payment_status == "succeeded" else OrderStatus.CANCELLED

    async with SessionLocal() as session:
        async with session.begin():
            stmt = insert(InboxMessage).values(message_id=message_id).on_conflict_do_nothing(
                index_elements=[InboxMessage.message_id]
            )
            res = await session.execute(stmt)
            inserted = (res.rowcount or 0) > 0

            if inserted:
                await update_order_status(session, order_id=order_id, new_status=new_status)

        await publish_order_status(redis_url, {
            "type": "update",
            "order_id": order_id,
            "status": new_status.value,
            "payment_status": payment_status,
            "reason": payload.get("reason"),
        })
