import pytest

from chainpulse.config import (
    ConfigurationError,
    load_settings,
)

VALID_ENV = {
    "ETHEREUM_RPC_URL": ("https://eth-mainnet.g.alchemy.com/v2/test-api-key"),
    "ETHEREUM_CHAIN_ID": "1",
    "RPC_REQUESTS_PER_SECOND": "5",
    "RPC_MAX_CONCURRENCY": "2",
    "RPC_TIMEOUT_SECONDS": "30",
    "RPC_MAX_RETRIES": "5",
    "POSTGRES_HOST": "127.0.0.1",
    "POSTGRES_PORT": "5432",
    "POSTGRES_DB": "chainpulse",
    "POSTGRES_USER": "chainpulse",
    "POSTGRES_PASSWORD": "postgres-test-secret",
    "RABBITMQ_DEFAULT_USER": "chainpulse",
    "RABBITMQ_DEFAULT_PASS": "rabbitmq-test-secret",
    "RABBITMQ_DEFAULT_VHOST": "chainpulse",
    "RABBITMQ_AMQP_PORT": "5672",
    "RABBITMQ_MANAGEMENT_PORT": "15672",
}


@pytest.fixture
def valid_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for name, value in VALID_ENV.items():
        monkeypatch.setenv(name, value)


def test_valid_configuration_loads(
    valid_environment: None,
) -> None:
    settings = load_settings(env_file=None)

    assert settings.ethereum_chain_id == 1
    assert settings.rpc_max_concurrency == 2
    assert settings.postgres_port == 5432

    rendered_settings = repr(settings)

    assert "test-api-key" not in rendered_settings
    assert "postgres-test-secret" not in rendered_settings
    assert "rabbitmq-test-secret" not in rendered_settings


def test_missing_required_value_fails(
    valid_environment: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("ETHEREUM_RPC_URL")

    with pytest.raises(
        ConfigurationError,
        match="ETHEREUM_RPC_URL",
    ):
        load_settings(env_file=None)


def test_invalid_numeric_value_fails(
    valid_environment: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("RPC_MAX_CONCURRENCY", "0")

    with pytest.raises(
        ConfigurationError,
        match="RPC_MAX_CONCURRENCY",
    ):
        load_settings(env_file=None)


def test_placeholder_secret_fails_without_leaking_it(
    valid_environment: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    placeholder = "replace-with-local-password"
    monkeypatch.setenv("POSTGRES_PASSWORD", placeholder)

    with pytest.raises(ConfigurationError) as error:
        load_settings(env_file=None)

    error_message = str(error.value)

    assert "POSTGRES_PASSWORD" in error_message
    assert placeholder not in error_message
