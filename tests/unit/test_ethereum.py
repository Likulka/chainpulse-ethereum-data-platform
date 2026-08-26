from unittest.mock import AsyncMock

import pytest

from chainpulse.ingestion.ethereum import (
    BlockNotFoundError,
    get_block_by_number,
    get_finalized_block_number,
    iter_block_range,
)
from chainpulse.ingestion.rpc import EthereumRpcClient, RpcProtocolError


@pytest.mark.asyncio
async def test_get_block_by_number() -> None:
    client = AsyncMock(spec=EthereumRpcClient)
    client.call.return_value = {
        "number": "0x10",
        "hash": "0xabc",
        "transactions": [],
    }

    block = await get_block_by_number(
        client,
        16,
    )

    assert block["number"] == "0x10"

    client.call.assert_awaited_once_with(
        "eth_getBlockByNumber",
        [
            "0x10",
            True,
        ],
    )


@pytest.mark.asyncio
async def test_get_block_without_full_transactions() -> None:
    client = AsyncMock(spec=EthereumRpcClient)
    client.call.return_value = {
        "number": "0x10",
        "transactions": ["0xtransaction"],
    }

    await get_block_by_number(
        client,
        16,
        full_transactions=False,
    )

    client.call.assert_awaited_once_with(
        "eth_getBlockByNumber",
        [
            "0x10",
            False,
        ],
    )


@pytest.mark.asyncio
async def test_missing_block() -> None:
    client = AsyncMock(spec=EthereumRpcClient)
    client.call.return_value = None

    with pytest.raises(BlockNotFoundError):
        await get_block_by_number(
            client,
            16,
        )


@pytest.mark.asyncio
async def test_get_finalized_block_number() -> None:
    client = AsyncMock(spec=EthereumRpcClient)
    client.call.return_value = {
        "number": "0x10",
        "hash": "0xabc",
    }

    block_number = await get_finalized_block_number(client)

    assert block_number == 16

    client.call.assert_awaited_once_with(
        "eth_getBlockByNumber",
        [
            "finalized",
            False,
        ],
    )


@pytest.mark.asyncio
async def test_invalid_finalized_block_number() -> None:
    client = AsyncMock(spec=EthereumRpcClient)
    client.call.return_value = {
        "number": "not-hex",
    }

    with pytest.raises(RpcProtocolError):
        await get_finalized_block_number(client)


@pytest.mark.asyncio
async def test_iter_block_range_is_inclusive() -> None:
    client = AsyncMock(spec=EthereumRpcClient)
    client.call.side_effect = [
        {
            "number": "0xa",
            "transactions": [],
        },
        {
            "number": "0xb",
            "transactions": [],
        },
        {
            "number": "0xc",
            "transactions": [],
        },
    ]

    blocks = [
        block
        async for block in iter_block_range(
            client,
            10,
            12,
            batch_size=2,
        )
    ]

    assert [block["number"] for block in blocks] == [
        "0xa",
        "0xb",
        "0xc",
    ]

    assert client.call.await_count == 3


@pytest.mark.asyncio
async def test_iter_block_range_rejects_invalid_range() -> None:
    client = AsyncMock(spec=EthereumRpcClient)

    with pytest.raises(ValueError):
        _ = [
            block
            async for block in iter_block_range(
                client,
                12,
                10,
            )
        ]


@pytest.mark.asyncio
async def test_iter_block_range_rejects_invalid_batch_size() -> None:
    client = AsyncMock(spec=EthereumRpcClient)

    with pytest.raises(ValueError):
        _ = [
            block
            async for block in iter_block_range(
                client,
                10,
                12,
                batch_size=0,
            )
        ]
