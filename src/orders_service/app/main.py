import asyncio
from contextlib import asynccontextmanager
from decimal import Decimal

from fastapi import Depends, FastAPI, Header, HTTPException, WebSocket, WebSocketDisconnect, status
from sqlalchemy.ext.asyncio import AsyncSession

from .config import settings
from .crud import create_order_with_outbox, get_order, list_orders
from .db import get_session, init_db
from .messaging import RabbitMQ
from .outbox import outbox_dispatcher
from .consumer import payment_result_consumer
from .redis_pubsub import redis_listener
from .schemas import CreateOrderRequest, OrderListResponse, OrderResponse
from .websocket_manager import WebSocketManager


ws_manager = WebSocketManager()
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
    tasks.append(asyncio.create_task(payment_result_consumer(rmq, settings.redis_url)))
    tasks.append(asyncio.create_task(redis_listener(settings.redis_url, ws_manager)))

    try:
        yield
    finally:
        for t in tasks:
            t.cancel()
        await rmq.close()


app = FastAPI(
    title="Orders Service",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/orders/docs",
    openapi_url="/orders/openapi.json",
)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/orders", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def create_order(
    body: CreateOrderRequest,
    user_id: str = Depends(_require_user_id),
    session: AsyncSession = Depends(get_session),
):
    amount = Decimal(body.amount)

    async with session.begin():
        order = await create_order_with_outbox(
            session,
            user_id=user_id,
            amount=amount,
            description=body.description,
            producer=settings.service_name,
        )

    return order


@app.get("/orders", response_model=OrderListResponse)
async def get_orders(
    user_id: str = Depends(_require_user_id),
    session: AsyncSession = Depends(get_session),
):
    orders = await list_orders(session, user_id=user_id)
    return {"orders": orders}


@app.get("/orders/{order_id}", response_model=OrderResponse)
async def get_order_status(
    order_id: str,
    user_id: str = Depends(_require_user_id),
    session: AsyncSession = Depends(get_session),
):
    order = await get_order(session, user_id=user_id, order_id=order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


@app.websocket("/ws/orders/{order_id}")
async def ws_order_status(ws: WebSocket, order_id: str, user_id: str | None = None):
    if not user_id:
        await ws.close(code=1008)
        return

    from .db import SessionLocal
    async with SessionLocal() as session:
        order = await get_order(session, user_id=user_id, order_id=order_id)
        if not order:
            await ws.close(code=1008)
            return

    await ws_manager.connect(order_id, ws)

    await ws.send_json({
        "type": "snapshot",
        "order_id": order_id,
        "status": order.status.value,
        "amount": order.amount,
    })

    try:
        while True:
            _ = await ws.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        await ws_manager.disconnect(order_id, ws)
