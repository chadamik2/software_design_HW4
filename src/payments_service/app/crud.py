import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from .models import (
    Account,
    BalanceTransaction,
    InboxMessage,
    OutboxEvent,
    Payment,
    PaymentStatus,
    TxKind,
)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def create_account(session: AsyncSession, *, user_id: str) -> Account:
    stmt = insert(Account).values(user_id=user_id, balance=0).on_conflict_do_nothing(
        index_elements=[Account.user_id]
    )
    await session.execute(stmt)
    res = await session.execute(select(Account).where(Account.user_id == user_id))
    return res.scalar_one()


async def get_account_for_update(session: AsyncSession, *, user_id: str) -> Account | None:
    res = await session.execute(
        select(Account).where(Account.user_id == user_id).with_for_update()
    )
    return res.scalar_one_or_none()


async def topup(session: AsyncSession, *, user_id: str, amount: Decimal) -> Account:
    acc = await get_account_for_update(session, user_id=user_id)
    if not acc:
        acc = await create_account(session, user_id=user_id)
        acc = await get_account_for_update(session, user_id=user_id)

    acc.balance = Decimal(acc.balance) + amount
    session.add(BalanceTransaction(
        user_id=user_id,
        kind=TxKind.topup,
        amount=amount,
        order_id=None,
    ))
    return acc


async def get_balance(session: AsyncSession, *, user_id: str) -> Account | None:
    res = await session.execute(select(Account).where(Account.user_id == user_id))
    return res.scalar_one_or_none()


async def try_insert_inbox(session: AsyncSession, *, message_id: str) -> bool:
    stmt = insert(InboxMessage).values(message_id=message_id).on_conflict_do_nothing(
        index_elements=[InboxMessage.message_id]
    )
    res = await session.execute(stmt)
    return (res.rowcount or 0) > 0


async def process_payment_requested(
    session: AsyncSession,
    *,
    message_id: str,
    order_id: str,
    user_id: str,
    amount: Decimal,
    producer: str,
) -> OutboxEvent:
    await try_insert_inbox(session, message_id=message_id)

    payment_id = uuid.uuid4()
    pay_stmt = insert(Payment).values(
        id=payment_id,
        order_id=order_id,
        user_id=user_id,
        amount=amount,
        status=PaymentStatus.failed,
        reason="",
    ).on_conflict_do_nothing(index_elements=[Payment.order_id])

    res = await session.execute(pay_stmt)
    created_new = (res.rowcount or 0) > 0

    if not created_new:
        existing = (await session.execute(select(Payment).where(Payment.order_id == order_id))).scalar_one()
        status = existing.status.value
        reason = existing.reason
        return _make_payment_result_outbox(
            order_id=order_id,
            user_id=user_id,
            amount=amount,
            payment_status=status,
            reason=reason,
            producer=producer,
        )

    acc = await get_account_for_update(session, user_id=user_id)
    if not acc:
        status = PaymentStatus.failed
        reason = "AccountNotFound"
    else:
        current = Decimal(acc.balance)
        if current >= amount:
            acc.balance = current - amount
            session.add(BalanceTransaction(
                user_id=user_id,
                kind=TxKind.order_debit,
                amount=-amount,
                order_id=order_id,
            ))
            status = PaymentStatus.succeeded
            reason = None
        else:
            status = PaymentStatus.failed
            reason = "InsufficientFunds"

    payment = (await session.execute(select(Payment).where(Payment.order_id == order_id))).scalar_one()
    payment.status = status
    payment.reason = reason

    return _make_payment_result_outbox(
        order_id=order_id,
        user_id=user_id,
        amount=amount,
        payment_status=status.value,
        reason=reason,
        producer=producer,
    )


def _make_payment_result_outbox(
    *,
    order_id: str,
    user_id: str,
    amount: Decimal,
    payment_status: str,
    reason: str | None,
    producer: str,
) -> OutboxEvent:
    event_id = uuid.uuid4()
    envelope = {
        "event_id": str(event_id),
        "event_type": "PaymentResult",
        "producer": producer,
        "occurred_at": _utc_now_iso(),
        "payload": {
            "order_id": order_id,
            "user_id": user_id,
            "amount": str(amount),
            "payment_status": payment_status,
            "reason": reason,
        },
    }

    return OutboxEvent(
        id=event_id,
        event_type="PaymentResult",
        aggregate_type="Payment",
        aggregate_id=order_id,
        payload=envelope,
    )
