import asyncio
from collections.abc import AsyncIterator
from typing import cast

from chainpulse.ingestion.rpc import EthereumRpcClient, RpcProtocolError


class BlockNotFoundError(RuntimeError):
    """Ethereum block was not found."""


def _require_object(
    value: object,
    *,
    object_name: str,
) -> dict[str, object]:
    if not isinstance(value, dict):
        raise RpcProtocolError(
            f"{object_name} must be a JSON object: {value}",
        )

    return cast(dict[str, object], value)


def _parse_hex_quantity(
    value: object,
    *,
    field_name: str,
) -> int:
    if not isinstance(value, str) or not value.startswith("0x"):
        raise RpcProtocolError(
            f"{field_name} must be a hex quantity: {value}",
        )

    try:
        return int(value, 16)
    except ValueError as error:
        raise RpcProtocolError(
            f"{field_name} contains invalid hex: {value}",
        ) from error


async def get_block_by_number(
    client: EthereumRpcClient,
    block_number: int,
    *,
    full_transactions: bool = True,
) -> dict[str, object]:
    if block_number < 0:
        raise ValueError("block_number must not be negative")

    result = await client.call(
        "eth_getBlockByNumber",
        [
            hex(block_number),
            full_transactions,
        ],
    )

    if result is None:
        raise BlockNotFoundError(
            f"Ethereum block {block_number} was not found",
        )

    return _require_object(
        result,
        object_name="Ethereum block",
    )


async def get_finalized_block_number(
    client: EthereumRpcClient,
) -> int:
    result = await client.call(
        "eth_getBlockByNumber",
        [
            "finalized",
            False,
        ],
    )

    if result is None:
        raise BlockNotFoundError(
            "Finalized Ethereum block was not found",
        )

    block = _require_object(
        result,
        object_name="Finalized Ethereum block",
    )

    return _parse_hex_quantity(
        block.get("number"),
        field_name="block.number",
    )


async def iter_block_range(
    client: EthereumRpcClient,
    start_block: int,
    end_block: int,
    *,
    batch_size: int = 50,
) -> AsyncIterator[dict[str, object]]:
    if start_block < 0:
        raise ValueError("start_block must not be negative")

    if end_block < start_block:
        raise ValueError(
            "end_block must be greater than or equal to start_block",
        )

    if batch_size <= 0:
        raise ValueError("batch_size must be greater than zero")

    for batch_start in range(
        start_block,
        end_block + 1,
        batch_size,
    ):
        batch_end = min(
            batch_start + batch_size - 1,
            end_block,
        )

        blocks = await asyncio.gather(
            *(
                get_block_by_number(
                    client,
                    block_number,
                    full_transactions=True,
                )
                for block_number in range(
                    batch_start,
                    batch_end + 1,
                )
            ),
        )

        for block in blocks:
            yield block
