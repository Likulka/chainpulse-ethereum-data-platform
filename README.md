# ChainPulse

ChainPulse is an educational, production-style data platform for collecting and
analysing Ethereum Mainnet activity.

The project demonstrates the complete data-engineering lifecycle: ingestion
from Ethereum JSON-RPC, reliable event delivery, operational and analytical
storage, SQL transformations, orchestration, API access, data quality, and BI.

## Project status

The project is under active development. The architecture and MVP boundaries
have been agreed. Executable services will be added incrementally.

Current milestone: **repository bootstrap**.

## MVP

The first version will:

- ingest a configurable range of at least 10,000 consecutive Ethereum Mainnet
  blocks and then continue incrementally;
- collect blocks, transactions, receipts, and contract logs;
- derive ERC-20 token transfers from `Transfer` logs;
- deliver events through RabbitMQ using at-least-once delivery;
- store hot analytical data in ClickHouse;
- store historical data and analytical marts in BigQuery;
- store checkpoints, ingestion runs, and tracked addresses in PostgreSQL;
- transform and test warehouse data with dbt;
- orchestrate backfills and quality checks with Airflow;
- provide analytical access through FastAPI and Looker Studio.

The MVP does not include a full Ethereum history backfill, other blockchains,
mempool or MEV analytics, NFT decoding, contract traces, transaction signing,
or private-key storage.

## Architecture

```text
Ethereum JSON-RPC
        |
        v
Python ingestion ---> PostgreSQL
        |              checkpoints, runs, watchlist
        v
RabbitMQ topic exchange
        |
        +---------------------------+
        |                           |
        v                           v
ClickHouse queue               BigQuery queue
        |                           |
        v                           v
Batch consumer                Batch consumer
        |                           |
        v                           v
ClickHouse                    BigQuery ---> dbt ---> Looker Studio
        |
        v
FastAPI

Airflow: backfills, reconciliation, dbt runs, and data-quality checks
```

## Technology stack

| Component | Responsibility |
| --- | --- |
| Python | Ethereum ingestion and consumers |
| Ethereum JSON-RPC | Source of blockchain data |
| RabbitMQ | Durable event delivery and buffering |
| PostgreSQL | Operational metadata and control plane |
| ClickHouse | Hot analytical storage |
| BigQuery | Historical warehouse |
| dbt | SQL transformations, tests, and documentation |
| Airflow | Batch orchestration and reconciliation |
| FastAPI | Data access API |
| Looker Studio | Historical BI dashboard |
| Docker Compose | Reproducible local environment |

## Planned repository structure

```text
chainpulse/
├── src/chainpulse/       # Python application code
├── tests/                # Unit and integration tests
├── dags/                 # Airflow DAGs
├── dbt/                  # dbt project
├── infra/                # Infrastructure configuration
├── docs/adr/             # Architecture decision records
├── .env.example          # Safe configuration template
├── compose.yaml          # Local services
└── README.md
```

Directories and configuration files will be introduced when their first
working component is implemented. Empty architecture is intentionally not
scaffolded in advance.

## Quick start

There is no runnable pipeline at the repository-bootstrap milestone yet.
After the local infrastructure task is completed, the canonical workflow will
be:

```bash
cp .env.example .env
docker compose up -d
docker compose ps
```

Application setup, tests, and shutdown commands will be documented here as
soon as the corresponding files exist.

## Delivery guarantees

The pipeline uses:

```text
at-least-once delivery
+ deterministic row keys
+ idempotent processing
+ deduplication
```

RabbitMQ messages are acknowledged only after the target storage confirms a
successful write.

## Documentation

Architecture decisions will be stored in [`docs/adr`](docs/adr). Each ADR will
record the decision, context, alternatives, and accepted trade-offs.

## License

This project is licensed under the [MIT License](LICENSE).

