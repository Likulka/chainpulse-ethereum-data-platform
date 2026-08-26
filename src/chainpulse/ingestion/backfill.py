import argparse
import asyncio
from datetime import UTC, datetime
from uuid import uuid4

from chainpulse.config import get_settings
from chainpulse.ingestion.ethereum import (
    get_finalized_block_number,
    iter_block_range,
)
from chainpulse.ingestion.events import build_events_from_block
from chainpulse.ingestion.publisher import RabbitMqPublisher
from chainpulse.ingestion.rpc import EthereumRpcClient


async def run_backfill(
    *,
    start_block: int,
    end_block: int,
    batch_size: int,
) -> None:
    settings = get_settings()

    chain_id = hex(settings.ethereum_chain_id)
    ingestion_run_id = str(uuid4())

    async with EthereumRpcClient.from_settings() as client:
        publisher = await RabbitMqPublisher.connect_from_settings()
        async with publisher:
            finalized_block = await get_finalized_block_number(client)

            if end_block > finalized_block:
                raise ValueError(
                    f"end_block {end_block} is above finalized block {finalized_block}",
                )

            blocks_count = 0
            transactions_count = 0
            events_count = 0

            async for block in iter_block_range(
                client,
                start_block,
                end_block,
                batch_size=batch_size,
            ):
                observed_at = (
                    datetime.now(UTC)
                    .isoformat()
                    .replace(
                        "+00:00",
                        "Z",
                    )
                )

                events = build_events_from_block(
                    block,
                    chain_id=chain_id,
                    observed_at=observed_at,
                    ingestion_run_id=ingestion_run_id,
                    provider="alchemy",
                )

                await publisher.publish_many(events)

                block_transactions_count = len(events) - 1

                blocks_count += 1
                transactions_count += block_transactions_count
                events_count += len(events)

                print(
                    f"Published block {block.get('number')}: "
                    f"{block_transactions_count} transactions, "
                    f"{len(events)} events",
                )

    print(f"Ingestion run: {ingestion_run_id}")
    print(
        f"Backfill completed: blocks={blocks_count}, "
        f"transactions={transactions_count}, "
        f"events={events_count}",
    )


def _parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Load Ethereum block range",
    )

    parser.add_argument(
        "--start-block",
        type=int,
        required=True,
    )
    parser.add_argument(
        "--end-block",
        type=int,
        required=True,
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=50,
    )

    return parser.parse_args()


def main() -> None:
    arguments = _parse_arguments()

    asyncio.run(
        run_backfill(
            start_block=arguments.start_block,
            end_block=arguments.end_block,
            batch_size=arguments.batch_size,
        ),
    )


if __name__ == "__main__":
    main()
