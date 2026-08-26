import asyncio
import json
from types import TracebackType
from typing import Self

import aio_pika
from aio_pika import DeliveryMode, ExchangeType, Message
from aio_pika.abc import (
    AbstractExchange,
    AbstractRobustConnection,
)

from chainpulse.config import get_settings

_EXCHANGE_NAME = "chainpulse.raw"

_QUEUE_NAMES = (
    "chainpulse.clickhouse.raw",
    "chainpulse.bigquery.raw",
)

_BINDING_KEY = "chainpulse.raw.#"


class MessagePublishError(RuntimeError):
    """Raw event cannot be published."""


class RabbitMqPublisher:
    """Publish raw ChainPulse events to RabbitMQ."""

    def __init__(
        self,
        *,
        connection: AbstractRobustConnection,
        exchange: AbstractExchange,
    ) -> None:
        self._connection = connection
        self._exchange = exchange

    @classmethod
    async def connect_from_settings(cls) -> Self:
        settings = get_settings()

        connection = await aio_pika.connect_robust(
            host=settings.rabbitmq_host,
            port=settings.rabbitmq_amqp_port,
            login=settings.rabbitmq_default_user,
            password=settings.rabbitmq_default_pass.get_secret_value(),
            virtualhost=settings.rabbitmq_default_vhost,
        )

        try:
            channel = await connection.channel(
                publisher_confirms=True,
                on_return_raises=True,
            )

            exchange = await channel.declare_exchange(
                _EXCHANGE_NAME,
                ExchangeType.TOPIC,
                durable=True,
            )

            for queue_name in _QUEUE_NAMES:
                queue = await channel.declare_queue(
                    queue_name,
                    durable=True,
                )

                await queue.bind(
                    exchange,
                    routing_key=_BINDING_KEY,
                )

        except BaseException:
            await connection.close()
            raise

        return cls(
            connection=connection,
            exchange=exchange,
        )

    async def publish(
        self,
        event: dict[str, object],
    ) -> None:
        event_id = event.get("event_id")
        event_type = event.get("event_type")

        if not isinstance(event_id, str) or not event_id:
            raise MessagePublishError(
                "Event has no valid event_id",
            )

        if not isinstance(event_type, str) or not event_type:
            raise MessagePublishError(
                "Event has no valid event_type",
            )

        body = json.dumps(
            event,
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")

        schema_version = event.get("schema_version")

        if not isinstance(schema_version, int) or isinstance(schema_version, bool):
            raise MessagePublishError(
                "Event has no valid schema_version",
            )

        message = Message(
            body=body,
            content_type="application/json",
            content_encoding="utf-8",
            delivery_mode=DeliveryMode.PERSISTENT,
            message_id=event_id,
            type=event_type,
            headers={
                "schema_version": schema_version,
            },
        )

        await self._exchange.publish(
            message,
            routing_key=event_type,
            mandatory=True,
        )

    async def publish_many(
        self,
        events: list[dict[str, object]],
    ) -> None:
        await asyncio.gather(
            *(self.publish(event) for event in events),
        )

    async def aclose(self) -> None:
        await self._connection.close()

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exception_type: type[BaseException] | None,
        exception: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        await self.aclose()
