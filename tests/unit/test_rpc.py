import asyncio
import time

import httpx
import pytest
from aiolimiter import AsyncLimiter

import chainpulse.ingestion.rpc as rpc_module
from chainpulse.ingestion.rpc import (
    EthereumRpcClient,
    JsonRpcError,
    RpcHttpError,
    RpcProtocolError,
    RpcTransportError,
    _call_rpc_with_client,
    _parse_rpc_response,
)


def test_parse_successful_response() -> None:
    response = httpx.Response(
        status_code=200,
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "result": "0x18a2af8",
        },
    )

    result = _parse_rpc_response(response)

    assert result == "0x18a2af8"


def test_parse_http_error() -> None:
    response = httpx.Response(
        status_code=503,
        json={"message": "Service unavailable"},
    )

    with pytest.raises(RpcHttpError) as captured_error:
        _parse_rpc_response(response)

    assert captured_error.value.status_code == 503


def test_parse_json_rpc_error() -> None:
    error_data = {
        "code": -32601,
        "message": "Method not found",
    }

    response = httpx.Response(
        status_code=200,
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "error": error_data,
        },
    )

    with pytest.raises(JsonRpcError) as captured_error:
        _parse_rpc_response(response)

    assert captured_error.value.error_data == error_data


def test_parse_invalid_json() -> None:
    response = httpx.Response(
        status_code=200,
        text="this is not JSON",
    )

    with pytest.raises(
        RpcProtocolError,
        match="not valid JSON",
    ):
        _parse_rpc_response(response)


def test_parse_non_object_json() -> None:
    response = httpx.Response(
        status_code=200,
        json=["unexpected", "list"],
    )

    with pytest.raises(
        RpcProtocolError,
        match="must be an object",
    ):
        _parse_rpc_response(response)


def test_parse_response_without_result() -> None:
    response = httpx.Response(
        status_code=200,
        json={
            "jsonrpc": "2.0",
            "id": 1,
        },
    )

    with pytest.raises(
        RpcProtocolError,
        match="has no result",
    ):
        _parse_rpc_response(response)


_TEST_PAYLOAD: dict[str, object] = {
    "jsonrpc": "2.0",
    "method": "eth_blockNumber",
    "params": [],
    "id": 1,
}


def disable_retry_delay(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        rpc_module,
        "_retry_delay_seconds",
        lambda retry_number: 0.0,
    )


@pytest.mark.asyncio
async def test_retryable_http_error_is_retried(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    disable_retry_delay(monkeypatch)

    attempts_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts_count
        attempts_count += 1

        if attempts_count == 1:
            return httpx.Response(
                status_code=503,
                request=request,
            )

        return httpx.Response(
            status_code=200,
            json={"result": "0x1"},
            request=request,
        )

    transport = httpx.MockTransport(handler)

    async with httpx.AsyncClient(transport=transport) as client:
        result = await _call_rpc_with_client(
            client,
            rpc_url="https://rpc.example",
            payload=_TEST_PAYLOAD,
            max_retries=2,
        )

    assert result == "0x1"
    assert attempts_count == 2


@pytest.mark.asyncio
async def test_permanent_http_error_is_not_retried(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    disable_retry_delay(monkeypatch)

    attempts_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts_count
        attempts_count += 1

        return httpx.Response(
            status_code=400,
            request=request,
        )

    transport = httpx.MockTransport(handler)

    async with httpx.AsyncClient(transport=transport) as client:
        with pytest.raises(RpcHttpError):
            await _call_rpc_with_client(
                client,
                rpc_url="https://rpc.example",
                payload=_TEST_PAYLOAD,
                max_retries=5,
            )

    assert attempts_count == 1


@pytest.mark.asyncio
async def test_retry_stops_after_max_retries(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    disable_retry_delay(monkeypatch)

    attempts_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts_count
        attempts_count += 1

        return httpx.Response(
            status_code=503,
            request=request,
        )

    transport = httpx.MockTransport(handler)

    async with httpx.AsyncClient(transport=transport) as client:
        with pytest.raises(RpcHttpError):
            await _call_rpc_with_client(
                client,
                rpc_url="https://rpc.example",
                payload=_TEST_PAYLOAD,
                max_retries=2,
            )

    assert attempts_count == 3


@pytest.mark.asyncio
async def test_transport_error_is_retried(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    disable_retry_delay(monkeypatch)

    attempts_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts_count
        attempts_count += 1

        if attempts_count == 1:
            raise httpx.ConnectError(
                "Connection failed",
                request=request,
            )

        return httpx.Response(
            status_code=200,
            json={"result": "0x1"},
            request=request,
        )

    transport = httpx.MockTransport(handler)

    async with httpx.AsyncClient(transport=transport) as client:
        result = await _call_rpc_with_client(
            client,
            rpc_url="https://rpc.example",
            payload=_TEST_PAYLOAD,
            max_retries=2,
        )

    assert result == "0x1"
    assert attempts_count == 2


@pytest.mark.asyncio
async def test_transport_error_after_all_attempts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    disable_retry_delay(monkeypatch)

    attempts_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts_count
        attempts_count += 1

        raise httpx.ConnectError(
            "Connection failed",
            request=request,
        )

    transport = httpx.MockTransport(handler)

    async with httpx.AsyncClient(transport=transport) as client:
        with pytest.raises(RpcTransportError) as captured_error:
            await _call_rpc_with_client(
                client,
                rpc_url="https://rpc.example",
                payload=_TEST_PAYLOAD,
                max_retries=2,
            )

    assert attempts_count == 3
    assert captured_error.value.attempts_count == 3


@pytest.mark.asyncio
async def test_concurrency_limit_is_respected() -> None:
    active_requests = 0
    maximum_active_requests = 0

    async def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        nonlocal active_requests
        nonlocal maximum_active_requests

        active_requests += 1
        maximum_active_requests = max(
            maximum_active_requests,
            active_requests,
        )

        await asyncio.sleep(0.01)

        active_requests -= 1

        return httpx.Response(
            status_code=200,
            json={"result": "0x1"},
            request=request,
        )

    transport = httpx.MockTransport(handler)
    rate_limiter = AsyncLimiter(
        max_rate=1000,
        time_period=1,
    )
    concurrency_limiter = asyncio.Semaphore(2)

    async with httpx.AsyncClient(
        transport=transport,
    ) as client:
        await asyncio.gather(
            *(
                _call_rpc_with_client(
                    client,
                    rpc_url="https://rpc.example",
                    payload=_TEST_PAYLOAD,
                    max_retries=0,
                    rate_limiter=rate_limiter,
                    concurrency_limiter=concurrency_limiter,
                )
                for _ in range(5)
            )
        )

    assert maximum_active_requests == 2


@pytest.mark.asyncio
async def test_rate_limit_is_respected() -> None:
    request_start_times: list[float] = []

    def handler(request: httpx.Request) -> httpx.Response:
        request_start_times.append(time.perf_counter())

        return httpx.Response(
            status_code=200,
            json={"result": "0x1"},
            request=request,
        )

    transport = httpx.MockTransport(handler)
    rate_limiter = AsyncLimiter(
        max_rate=1,
        time_period=0.05,
    )
    concurrency_limiter = asyncio.Semaphore(10)

    async with httpx.AsyncClient(
        transport=transport,
    ) as client:
        await asyncio.gather(
            _call_rpc_with_client(
                client,
                rpc_url="https://rpc.example",
                payload=_TEST_PAYLOAD,
                max_retries=0,
                rate_limiter=rate_limiter,
                concurrency_limiter=concurrency_limiter,
            ),
            _call_rpc_with_client(
                client,
                rpc_url="https://rpc.example",
                payload=_TEST_PAYLOAD,
                max_retries=0,
                rate_limiter=rate_limiter,
                concurrency_limiter=concurrency_limiter,
            ),
        )

    interval = request_start_times[1] - request_start_times[0]

    assert interval >= 0.04


@pytest.mark.asyncio
async def test_client_context_manager_closes_http_client() -> None:
    client = EthereumRpcClient(
        rpc_url="https://rpc.example",
        timeout_seconds=1,
        max_retries=0,
        requests_per_second=1,
        max_concurrency=1,
    )

    assert not client._http_client.is_closed

    async with client as opened_client:
        assert opened_client is client
        assert not client._http_client.is_closed

    assert client._http_client.is_closed
