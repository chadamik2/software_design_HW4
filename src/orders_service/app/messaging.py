import json
from typing import Any
import asyncio

import aio_pika
from aio_pika import DeliveryMode, ExchangeType, Message


EXCHANGE_NAME = "events"

RK_PAYMENT_REQUESTED = "payments.payment_requested"
RK_PAYMENT_RESULT = "orders.payment_result"

QUEUE_ORDERS_PAYMENT_RESULTS = "orders.payment_results"


class RabbitMQ:
    def __init__(self, url: str):
        self.url = url
        self._conn: aio_pika.RobustConnection | None = None

        self._pub_channel: aio_pika.abc.AbstractRobustChannel | None = None
        self._pub_exchange: aio_pika.abc.AbstractRobustExchange | None = None

        self._con_channel: aio_pika.abc.AbstractRobustChannel | None = None
        self._con_exchange: aio_pika.abc.AbstractRobustExchange | None = None

    async def connect(self) -> None:
        last_err = None
        for attempt in range(1, 31):
            try:
                self._conn = await aio_pika.connect_robust(self.url)

                self._pub_channel = await self._conn.channel()
                self._pub_exchange = await self._pub_channel.declare_exchange(
                    EXCHANGE_NAME, ExchangeType.TOPIC, durable=True
                )

                self._con_channel = await self._conn.channel()
                await self._con_channel.set_qos(prefetch_count=50)
                self._con_exchange = await self._con_channel.declare_exchange(
                    EXCHANGE_NAME, ExchangeType.TOPIC, durable=True
                )
                return
            except Exception as e:
                last_err = e
                await asyncio.sleep(min(2.0, 0.2 * attempt))  

        raise RuntimeError(f"RabbitMQ connect failed after retries: {last_err}") from last_err

    async def close(self) -> None:
        if self._conn:
            await self._conn.close()

    async def publish_json(
        self,
        *,
        routing_key: str,
        body: dict[str, Any],
        message_id: str,
        correlation_id: str | None = None,
        headers: dict[str, Any] | None = None,
    ) -> None:
        assert self._pub_exchange is not None

        msg = Message(
            body=json.dumps(body).encode("utf-8"),
            content_type="application/json",
            delivery_mode=DeliveryMode.PERSISTENT,
            message_id=message_id,
            correlation_id=correlation_id,
            headers=headers or {},
        )
        await self._pub_exchange.publish(msg, routing_key=routing_key)

    async def declare_orders_payment_results_queue(self) -> aio_pika.abc.AbstractRobustQueue:
        assert self._con_channel is not None
        assert self._con_exchange is not None

        queue = await self._con_channel.declare_queue(QUEUE_ORDERS_PAYMENT_RESULTS, durable=True)
        await queue.bind(self._con_exchange, routing_key=RK_PAYMENT_RESULT)
        return queue
