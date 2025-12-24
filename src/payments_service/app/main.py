import asyncio
from contextlib import asynccontextmanager
from decimal import Decimal

from fastapi import Depends, FastAPI, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from .config import settings
from .crud import create_account, get_balance, topup
from .db import get_session, init_db
from .messaging import RabbitMQ
from .outbox import outbox_dispatcher
from .consumer import payment_requested_consumer
from .schemas import BalanceResponse, CreateAccountResponse, TopUpRequest, TopUpResponse


rmq = RabbitMQ(settings.rabbitmq_url)


async def _require_user_id(x_user_id: str | None = Header(default=None, alias="X-User-Id")) -> str:
    if not x_user_id:
        raise HTTPException(status_code=400, detail="X-User-Id header is required")
    return x_user_id


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    await rmq.connect()

    tasks: list[asyncio.Task] = []
    tasks.append(asyncio.create_task(outbox_dispatcher(rmq)))
    tasks.append(asyncio.create_task(payment_requested_consumer(rmq)))

    try:
        yield
    finally:
        for t in tasks:
            t.cancel()
        await rmq.close()


app = FastAPI(
    title="Payments Service",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/payments/docs",
    openapi_url="/payments/openapi.json",
)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/accounts", response_model=CreateAccountResponse)
async def api_create_account(
    user_id: str = Depends(_require_user_id),
    session: AsyncSession = Depends(get_session),
):
    async with session.begin():
        acc = await create_account(session, user_id=user_id)
    return {"user_id": acc.user_id, "balance": f"{acc.balance:.2f}"}


@app.get("/accounts/balance", response_model=BalanceResponse)
async def api_balance(
    user_id: str = Depends(_require_user_id),
    session: AsyncSession = Depends(get_session),
):
    acc = await get_balance(session, user_id=user_id)
    if not acc:
        return {"user_id": user_id, "balance": "0.00"}
    return {"user_id": acc.user_id, "balance": f"{acc.balance:.2f}"}


@app.post("/accounts/topup", response_model=TopUpResponse)
async def api_topup(
    body: TopUpRequest,
    user_id: str = Depends(_require_user_id),
    session: AsyncSession = Depends(get_session),
):
    amount = Decimal(body.amount)
    async with session.begin():
        acc = await topup(session, user_id=user_id, amount=amount)
    return {"user_id": acc.user_id, "balance": f"{acc.balance:.2f}"}
