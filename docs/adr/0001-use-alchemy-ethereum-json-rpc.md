# ADR 0001: Use Alchemy as Ethereum JSON-RPC provider

## Status

Accepted

## Context

ChainPulse needs access to Ethereum Mainnet blocks, transactions, receipts, logs and account code. Running and maintaining a local Ethereum node is outside
the MVP scope.

## Decision

Use an Alchemy Ethereum Mainnet HTTPS endpoint.

The endpoint is provided through the `ETHEREUM_RPC_URL` environment variable. The real value is stored only in the local `.env` file. A safe template is stored in `.env.example`.

## Free plan limits

Limits verified on 2026-08-21:

- 30 million Compute Units per month;
- pricing page advertises up to 25 requests per second;
- effective throughput also depends on method Compute Units;
- full archive data is available;
- Debug and Trace APIs are not required for the MVP.

Relevant method costs:

| Method | Compute Units |
| --- | ---: |
| eth_chainId | 0 |
| eth_blockNumber | 10 |
| eth_getBlockByNumber | 20 |
| eth_getBlockReceipts | 20 |
| eth_getTransactionReceipt | 20 |
| eth_getLogs | 60 |
| eth_getCode | 20 |

## Usage policy

- Start with a limit of 5 requests per second.
- Use no more than 2 concurrent RPC requests initially.
- Set a request timeout of 30 seconds.
- Retry temporary errors and HTTP 429/5xx with exponential backoff and jitter.
- Do not retry invalid parameters or other deterministic request errors.
- Inspect JSON-RPC `error` even when the HTTP response status is 200.
- Stop optional backfills after consuming 80% of the monthly quota.
- Do not repeatedly download an already completed block range without a reason.
- Prefer `eth_getBlockReceipts` over one receipt request per transaction.
- Split large `eth_getLogs` ranges into controlled chunks.
- Never log or commit the complete RPC endpoint.
- Match JSON-RPC batch responses by `id`, not by response order.

## Alternatives

### Public RPC endpoint

Rejected for the main pipeline because availability, limits and historical access are less predictable.

### Local Ethereum node

Rejected for the MVP because it requires substantial disk space, synchronization time and operational maintenance.

### Infura or QuickNode

Valid alternatives. The provider is hidden behind `ETHEREUM_RPC_URL`, so it can be replaced without changing ingestion code.

## Consequences

ChainPulse depends on an external provider and its limits. The ingestion client must implement timeouts, retries, rate limiting and usage metrics.

The project avoids the cost and operational complexity of maintaining its own Ethereum node.
