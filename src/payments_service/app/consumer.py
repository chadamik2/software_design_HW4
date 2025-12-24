import json
from decimal import Decimal
from typing import Any

from .config import settings
from .crud import process_payment_requested
from .db import SessionLocal
from .messaging import RabbitMQ


def _parse_message(body: bytes) -> dict[str, Any]:
    return json.loads(body.decode("utf-8"))


async def payment_requested_consumer(rmq: RabbitMQ) -> None:
    queue = await rmq.declare_payments_requests_queue()

    async with queue.iterator() as q:
        async for msg in q:
            try:
                await _handle_payment_requested(msg=msg)
                await msg.ack()
            except Exception:
                await msg.nack(requeue=True)


async def _handle_payment_requested(*, msg) -> None:
    message_id = msg.message_id or ""
    envelope = _parse_message(msg.body)
    payload = envelope.get("payload", {})

    order_id = payload.get("order_id")
    user_id = payload.get("user_id")
    amount_raw = payload.get("amount")

    if not order_id or not user_id or not amount_raw:
        return

    amount = Decimal(str(amount_raw))

    async with SessionLocal() as session:
        async with session.begin():
            outbox_event = await process_payment_requested(
                session,
                message_id=message_id,
                order_id=order_id,
                user_id=user_id,
                amount=amount,
                producer=settings.service_name,
            )
            session.add(outbox_event)
