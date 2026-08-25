import asyncio
from types import TracebackType
from typing import Self

import httpx
from aiolimiter import AsyncLimiter

from chainpulse.config import get_settings

_RETRYABLE_HTTP_STATUSES = {
    429,
    500,
    502,
    503,
    504,
}


class RpcClientError(RuntimeError):
    """Base error for Ethereum JSON-RPC client."""


class RpcHttpError(RpcClientError):
    """HTTP request completed with an error status."""

    def __init__(self, status_code: int) -> None:
        self.status_code = status_code

        super().__init__(f"RPC HTTP error: {status_code}")


class JsonRpcError(RpcClientError):
    """Server returned a JSON-RPC error."""

    def __init__(self, error_data: object) -> None:
        self.error_data = error_data

        super().__init__(f"JSON-RPC error: {error_data}")


class RpcProtocolError(RpcClientError):
    """Response does not follow the expected JSON-RPC format."""


class RpcTransportError(RpcClientError):
    """Network connection or timeout error."""

    def __init__(self, attempts_count: int) -> None:
        self.attempts_count = attempts_count

        super().__init__(f"RPC transport error after {attempts_count} attempts")


class EthereumRpcClient:
    """Reusable rate-limited Ethereum JSON-RPC client."""

    def __init__(
        self,
        *,
        rpc_url: str,
        timeout_seconds: float,
        max_retries: int,
        requests_per_second: float,
        max_concurrency: int,
    ) -> None:
        self._rpc_url = rpc_url
        self._max_retries = max_retries
        self._next_request_id = 1

        self._http_client = httpx.AsyncClient(
            timeout=timeout_seconds,
        )
        self._rate_limiter = AsyncLimiter(
            max_rate=requests_per_second,
            time_period=1,
        )
        self._concurrency_limiter = asyncio.Semaphore(
            max_concurrency,
        )

    @classmethod
    def from_settings(cls) -> Self:
        settings = get_settings()

        return cls(
            rpc_url=str(settings.ethereum_rpc_url.get_secret_value()),
            timeout_seconds=settings.rpc_timeout_seconds,
            max_retries=settings.rpc_max_retries,
            requests_per_second=settings.rpc_requests_per_second,
            max_concurrency=settings.rpc_max_concurrency,
        )

    async def call(
        self,
        method: str,
        params: list[object] | None = None,
    ) -> object:
        request_id = self._next_request_id
        self._next_request_id += 1

        payload: dict[str, object] = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params if params is not None else [],
            "id": request_id,
        }

        return await _call_rpc_with_client(
            self._http_client,
            rpc_url=self._rpc_url,
            payload=payload,
            max_retries=self._max_retries,
            rate_limiter=self._rate_limiter,
            concurrency_limiter=self._concurrency_limiter,
        )

    async def aclose(self) -> None:
        await self._http_client.aclose()

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exception_type: type[BaseException] | None,
        exception: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        await self.aclose()


def _parse_rpc_response(response: httpx.Response) -> object:
    if response.status_code >= 400:
        raise RpcHttpError(response.status_code)

    try:
        body: object = response.json()
    except ValueError as error:
        raise RpcProtocolError("JSON-RPC response is not valid JSON") from error

    if not isinstance(body, dict):
        raise RpcProtocolError(f"JSON-RPC response must be an object: {body}")

    if "error" in body:
        raise JsonRpcError(body["error"])

    if "result" not in body:
        raise RpcProtocolError(f"JSON-RPC response has no result: {body}")

    return body["result"]


def _retry_delay_seconds(retry_number: int) -> float:
    return float(2**retry_number)


async def call_rpc(
    method: str,
    params: list[object] | None = None,
) -> object:
    """Make one RPC call; use EthereumRpcClient for batch ingestion."""

    async with EthereumRpcClient.from_settings() as client:
        return await client.call(method, params)


async def _call_rpc_with_client(
    client: httpx.AsyncClient,
    *,
    rpc_url: str,
    payload: dict[str, object],
    max_retries: int,
    rate_limiter: AsyncLimiter | None = None,
    concurrency_limiter: asyncio.Semaphore | None = None,
) -> object:
    retry_number = 0

    while True:
        try:
            if rate_limiter is not None and concurrency_limiter is not None:
                async with concurrency_limiter, rate_limiter:
                    response = await client.post(
                        url=rpc_url,
                        json=payload,
                    )
            else:
                response = await client.post(
                    url=rpc_url,
                    json=payload,
                )

            return _parse_rpc_response(response)

        except RpcHttpError as error:
            is_retryable = error.status_code in _RETRYABLE_HTTP_STATUSES

            if not is_retryable or retry_number >= max_retries:
                raise

        except httpx.TransportError as error:
            if retry_number >= max_retries:
                raise RpcTransportError(
                    attempts_count=retry_number + 1,
                ) from error

        delay_seconds = _retry_delay_seconds(retry_number)

        await asyncio.sleep(delay_seconds)

        retry_number += 1
