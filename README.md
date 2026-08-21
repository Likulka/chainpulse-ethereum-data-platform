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


## Repository structure

```text
src/chainpulse/
├── ingestion/          # Ethereum JSON-RPC ingestion
├── consumers/          # RabbitMQ consumers
└── api/                # FastAPI application

airflow/dags/            # Airflow DAGs
dbt/                     # dbt project
infra/                   # Infrastructure configuration
tests/unit/              # Unit tests
tests/integration/       # Integration tests
docs/adr/                # Architecture decisions
pyproject.toml           # Python project configuration
```

Directories and configuration files will be introduced when their first
working component is implemented. Empty architecture is intentionally not
scaffolded in advance.

## Quick start

Requirements:

- Python 3.11.9
- uv
- Docker with Docker Compose

Clone the repository and install the Python environment:

```bash
git clone https://github.com/Likulka/chainpulse-ethereum-data-platform.git
cd chainpulse-ethereum-data-platform
uv sync
```

Application setup, tests, and shutdown commands will be documented here as
soon as the corresponding files exist.

## Development checks

Install dependencies and Git hooks:

```bash
uv sync
uv run pre-commit install
```

Run all checks:

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run pre-commit run --all-files
```

Apply automatic formatting and fixes:

```bash
uv run ruff check --fix .
uv run ruff format .
```

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
