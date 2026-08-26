from typing import cast


class RawEventBuildError(ValueError):
    """Raw Ethereum event cannot be created."""


def _require_string(
    source: dict[str, object],
    field_name: str,
) -> str:
    value = source.get(field_name)

    if not isinstance(value, str) or not value:
        raise RawEventBuildError(
            f"Required string field is missing: {field_name}",
        )

    return value


def _get_transactions(
    block: dict[str, object],
) -> list[dict[str, object]]:
    value = block.get("transactions")

    if not isinstance(value, list):
        raise RawEventBuildError(
            "Block transactions must be an array",
        )

    transactions: list[dict[str, object]] = []

    for transaction in value:
        if not isinstance(transaction, dict):
            raise RawEventBuildError(
                "Full transaction objects were not requested",
            )

        transactions.append(
            cast(dict[str, object], transaction),
        )

    return transactions


def _build_envelope(
    *,
    event_id: str,
    event_type: str,
    chain_id: str,
    observed_at: str,
    ingestion_run_id: str,
    provider: str,
    payload: dict[str, object],
) -> dict[str, object]:
    return {
        "event_id": event_id,
        "event_type": event_type,
        "schema_version": 1,
        "chain_id": chain_id,
        "observed_at": observed_at,
        "ingestion_run_id": ingestion_run_id,
        "source": {
            "provider": provider,
            "rpc_method": "eth_getBlockByNumber",
        },
        "payload": payload,
    }


def build_events_from_block(
    block: dict[str, object],
    *,
    chain_id: str,
    observed_at: str,
    ingestion_run_id: str,
    provider: str,
) -> list[dict[str, object]]:
    block_hash = _require_string(
        block,
        "hash",
    )
    transactions = _get_transactions(block)

    transaction_hashes: list[str] = []
    transaction_events: list[dict[str, object]] = []

    for transaction in transactions:
        transaction_hash = _require_string(
            transaction,
            "hash",
        )
        transaction_block_hash = _require_string(
            transaction,
            "blockHash",
        )

        if transaction_block_hash != block_hash:
            raise RawEventBuildError(
                "Transaction blockHash does not match block hash",
            )

        transaction_hashes.append(transaction_hash)

        transaction_events.append(
            _build_envelope(
                event_id=(f"{chain_id}:transaction:{block_hash}:{transaction_hash}"),
                event_type="chainpulse.raw.transaction",
                chain_id=chain_id,
                observed_at=observed_at,
                ingestion_run_id=ingestion_run_id,
                provider=provider,
                payload=dict(transaction),
            ),
        )

    block_payload = dict(block)
    block_payload["transactions"] = transaction_hashes

    block_event = _build_envelope(
        event_id=f"{chain_id}:block:{block_hash}",
        event_type="chainpulse.raw.block",
        chain_id=chain_id,
        observed_at=observed_at,
        ingestion_run_id=ingestion_run_id,
        provider=provider,
        payload=block_payload,
    )

    return [
        block_event,
        *transaction_events,
    ]
