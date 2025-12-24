import asyncio
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .config import settings
from .db import SessionLocal
from .messaging import RK_PAYMENT_RESULT, RabbitMQ
from .models import OutboxEvent


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


async def outbox_dispatcher(rmq: RabbitMQ) -> None:
    while True:
        try:
            async with SessionLocal() as session:
                await _dispatch_batch(session=session, rmq=rmq)
        except Exception:
            pass

        await asyncio.sleep(settings.outbox_poll_interval)


async def _dispatch_batch(*, session: AsyncSession, rmq: RabbitMQ) -> None:
    stmt = (
        select(OutboxEvent)
        .where(OutboxEvent.published_at.is_(None))
        .order_by(OutboxEvent.created_at.asc())
        .limit(settings.outbox_batch_size)
    )
    res = await session.execute(stmt)
    events = list(res.scalars().all())
    if not events:
        return

    for ev in events:
        try:
            await rmq.publish_json(
                routing_key=RK_PAYMENT_RESULT,
                body=ev.payload,
                message_id=str(ev.id),
                correlation_id=ev.aggregate_id,
                headers={"event_type": ev.event_type},
            )
            ev.published_at = _utc_now()
        except Exception as e:
            ev.attempts += 1
            ev.last_error = str(e)[:1000]

    await session.commit()
