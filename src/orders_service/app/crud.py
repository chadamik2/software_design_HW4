import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import Order, OrderStatus, OutboxEvent


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def create_order_with_outbox(
    session: AsyncSession,
    *,
    user_id: str,
    amount: Decimal,
    description: str,
    producer: str,
) -> Order:
    order = Order(
        user_id=user_id,
        amount=str(amount),
        description=description,
        status=OrderStatus.NEW,
    )
    session.add(order)
    await session.flush()

    event_id = uuid.uuid4()
    envelope = {
        "event_id": str(event_id),
        "event_type": "PaymentRequested",
        "producer": producer,
        "occurred_at": _utc_now_iso(),
        "payload": {
            "order_id": str(order.id),
            "user_id": user_id,
            "amount": str(amount),
            "description": description,
        },
    }

    outbox = OutboxEvent(
        id=event_id,
        event_type="PaymentRequested",
        aggregate_type="Order",
        aggregate_id=str(order.id),
        payload=envelope,
    )
    session.add(outbox)
    return order


async def list_orders(session: AsyncSession, *, user_id: str) -> list[Order]:
    res = await session.execute(
        select(Order).where(Order.user_id == user_id).order_by(Order.created_at.desc())
    )
    return list(res.scalars().all())


async def get_order(session: AsyncSession, *, user_id: str, order_id: str) -> Order | None:
    res = await session.execute(
        select(Order).where(Order.id == order_id, Order.user_id == user_id)
    )
    return res.scalar_one_or_none()


async def update_order_status(session: AsyncSession, *, order_id: str, new_status: OrderStatus) -> None:
    order = await session.get(Order, order_id)
    if not order:
        return
    if order.status in (OrderStatus.FINISHED, OrderStatus.CANCELLED):
        return
    order.status = new_status
