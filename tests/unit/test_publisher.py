import json
from unittest.mock import AsyncMock

import pytest
from aio_pika import DeliveryMode
from aio_pika.abc import (
    AbstractExchange,
    AbstractRobustConnection,
)

from chainpulse.ingestion.publisher import (
    MessagePublishError,
    RabbitMqPublisher,
)


def _make_event() -> dict[str, object]:
    return {
        "event_id": "0x1:block:0xabc",
        "event_type": "chainpulse.raw.block",
        "schema_version": 1,
        "chain_id": "0x1",
        "payload": {
            "hash": "0xabc",
        },
    }


@pytest.mark.asyncio
async def test_publishes_persistent_json_message() -> None:
    connection = AsyncMock(spec=AbstractRobustConnection)
    exchange = AsyncMock(spec=AbstractExchange)

    publisher = RabbitMqPublisher(
        connection=connection,
        exchange=exchange,
    )

    event = _make_event()

    await publisher.publish(event)

    exchange.publish.assert_awaited_once()

    call = exchange.publish.await_args
    message = call.args[0]

    assert json.loads(message.body) == event
    assert message.content_type == "application/json"
    assert message.delivery_mode == DeliveryMode.PERSISTENT
    assert message.message_id == "0x1:block:0xabc"

    assert call.kwargs["routing_key"] == "chainpulse.raw.block"
    assert call.kwargs["mandatory"] is True


@pytest.mark.asyncio
async def test_rejects_event_without_event_id() -> None:
    connection = AsyncMock(spec=AbstractRobustConnection)
    exchange = AsyncMock(spec=AbstractExchange)

    publisher = RabbitMqPublisher(
        connection=connection,
        exchange=exchange,
    )

    event = _make_event()
    event.pop("event_id")

    with pytest.raises(
        MessagePublishError,
        match="event_id",
    ):
        await publisher.publish(event)

    exchange.publish.assert_not_awaited()


@pytest.mark.asyncio
async def test_closes_connection() -> None:
    connection = AsyncMock(spec=AbstractRobustConnection)
    exchange = AsyncMock(spec=AbstractExchange)

    publisher = RabbitMqPublisher(
        connection=connection,
        exchange=exchange,
    )

    await publisher.aclose()

    connection.close.assert_awaited_once()
