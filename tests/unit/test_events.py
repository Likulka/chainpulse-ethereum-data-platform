import pytest

from chainpulse.ingestion.events import (
    RawEventBuildError,
    build_events_from_block,
)


def _make_block() -> dict[str, object]:
    return {
        "number": "0x10",
        "hash": "0xblock",
        "parentHash": "0xparent",
        "transactions": [
            {
                "hash": "0xtx1",
                "blockHash": "0xblock",
                "transactionIndex": "0x0",
            },
            {
                "hash": "0xtx2",
                "blockHash": "0xblock",
                "transactionIndex": "0x1",
            },
        ],
    }


def test_builds_block_and_transaction_events() -> None:
    events = build_events_from_block(
        _make_block(),
        chain_id="0x1",
        observed_at="2026-08-26T10:00:00Z",
        ingestion_run_id="run-1",
        provider="alchemy",
    )

    assert len(events) == 3

    block_event = events[0]

    assert block_event["event_id"] == "0x1:block:0xblock"
    assert block_event["event_type"] == "chainpulse.raw.block"

    block_payload = block_event["payload"]

    assert isinstance(block_payload, dict)
    assert block_payload["transactions"] == [
        "0xtx1",
        "0xtx2",
    ]

    assert events[1]["event_id"] == ("0x1:transaction:0xblock:0xtx1")
    assert events[2]["event_id"] == ("0x1:transaction:0xblock:0xtx2")


def test_event_ids_are_deterministic() -> None:
    first_run = build_events_from_block(
        _make_block(),
        chain_id="0x1",
        observed_at="2026-08-26T10:00:00Z",
        ingestion_run_id="run-1",
        provider="alchemy",
    )

    second_run = build_events_from_block(
        _make_block(),
        chain_id="0x1",
        observed_at="2026-08-26T11:00:00Z",
        ingestion_run_id="run-2",
        provider="alchemy",
    )

    first_event_ids = [event["event_id"] for event in first_run]
    second_event_ids = [event["event_id"] for event in second_run]

    assert first_event_ids == second_event_ids
    assert first_run[0]["ingestion_run_id"] != (second_run[0]["ingestion_run_id"])


def test_rejects_transaction_from_another_block() -> None:
    block = _make_block()

    transactions = block["transactions"]
    assert isinstance(transactions, list)

    transaction = transactions[0]
    assert isinstance(transaction, dict)

    transaction["blockHash"] = "0xanother-block"

    with pytest.raises(
        RawEventBuildError,
        match="does not match",
    ):
        build_events_from_block(
            block,
            chain_id="0x1",
            observed_at="2026-08-26T10:00:00Z",
            ingestion_run_id="run-1",
            provider="alchemy",
        )
