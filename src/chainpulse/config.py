from __future__ import annotations

from functools import lru_cache

from pydantic import (
    AnyHttpUrl,
    Field,
    Secret,
    SecretStr,
    ValidationError,
    field_validator,
)
from pydantic_settings import BaseSettings, SettingsConfigDict

SecretHttpUrl = Secret[AnyHttpUrl]


class ConfigurationError(RuntimeError):
    """Raised when the application configuration is invalid."""


class Settings(BaseSettings):
    """Validated ChainPulse application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    ethereum_rpc_url: SecretHttpUrl = Field(validation_alias="ETHEREUM_RPC_URL")
    ethereum_chain_id: int = Field(
        gt=0,
        validation_alias="ETHEREUM_CHAIN_ID",
    )

    rpc_requests_per_second: float = Field(
        gt=0,
        validation_alias="RPC_REQUESTS_PER_SECOND",
    )
    rpc_max_concurrency: int = Field(
        gt=0,
        validation_alias="RPC_MAX_CONCURRENCY",
    )
    rpc_timeout_seconds: float = Field(
        gt=0,
        validation_alias="RPC_TIMEOUT_SECONDS",
    )
    rpc_max_retries: int = Field(
        ge=0,
        validation_alias="RPC_MAX_RETRIES",
    )

    postgres_host: str = Field(
        min_length=1,
        validation_alias="POSTGRES_HOST",
    )
    postgres_port: int = Field(
        ge=1,
        le=65535,
        validation_alias="POSTGRES_PORT",
    )
    postgres_db: str = Field(
        min_length=1,
        validation_alias="POSTGRES_DB",
    )
    postgres_user: str = Field(
        min_length=1,
        validation_alias="POSTGRES_USER",
    )
    postgres_password: SecretStr = Field(
        min_length=1,
        validation_alias="POSTGRES_PASSWORD",
    )

    rabbitmq_host: str = Field(
        min_length=1,
        validation_alias="RABBITMQ_HOST",
    )

    rabbitmq_default_user: str = Field(
        min_length=1,
        validation_alias="RABBITMQ_DEFAULT_USER",
    )
    rabbitmq_default_pass: SecretStr = Field(
        min_length=1,
        validation_alias="RABBITMQ_DEFAULT_PASS",
    )
    rabbitmq_default_vhost: str = Field(
        min_length=1,
        validation_alias="RABBITMQ_DEFAULT_VHOST",
    )
    rabbitmq_amqp_port: int = Field(
        ge=1,
        le=65535,
        validation_alias="RABBITMQ_AMQP_PORT",
    )
    rabbitmq_management_port: int = Field(
        ge=1,
        le=65535,
        validation_alias="RABBITMQ_MANAGEMENT_PORT",
    )

    @field_validator("ethereum_rpc_url")
    @classmethod
    def reject_example_rpc_url(
        cls,
        value: SecretHttpUrl,
    ) -> SecretHttpUrl:
        raw_url = str(value.get_secret_value())

        if "replace-with-api-key" in raw_url:
            raise ValueError("replace the example RPC API key with a real value")

        return value

    @field_validator(
        "postgres_password",
        "rabbitmq_default_pass",
    )
    @classmethod
    def reject_placeholder_secret(
        cls,
        value: SecretStr,
    ) -> SecretStr:
        if value.get_secret_value().startswith("replace-with-"):
            raise ValueError("replace the example placeholder with a real secret")

        return value


def load_settings(
    *,
    env_file: str | None = ".env",
) -> Settings:
    """Load settings and return a safe, readable error."""

    try:
        return Settings(_env_file=env_file)  # type: ignore[call-arg]
    except ValidationError as error:
        details = "\n".join(
            (f"- {'.'.join(str(part) for part in item['loc'])}: {item['msg']}")
            for item in error.errors(
                include_url=False,
                include_input=False,
            )
        )

        raise ConfigurationError(
            f"Invalid ChainPulse configuration:\n{details}"
        ) from None


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Load and cache application settings."""

    return load_settings()
