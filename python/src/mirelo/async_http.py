from __future__ import annotations

import asyncio
from typing import Any

import httpx

from .types import MireloError

def _parse_error(response: httpx.Response) -> MireloError:
    code = "server_error"
    message = response.reason_phrase or "Server error"
    try:
        data = response.json()
        err = data.get("error", {})
        code = err.get("code", code)
        message = err.get("message", message)
    except Exception:
        pass
    return MireloError(message, code, response.status_code)

async def request(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    *,
    headers: dict[str, str],
    json: Any = None,
    retries: int = 0,
    backoff_ms: int = 1_000,
) -> Any:
    last_error: MireloError | None = None

    for attempt in range(retries + 1):
        if attempt > 0:
            await asyncio.sleep(backoff_ms * (2 ** (attempt - 1)) / 1_000)

        try:
            response = await client.request(method, url, headers=headers, json=json)

            if not response.is_success:
                err = _parse_error(response)
                if 400 <= response.status_code < 500:
                    raise err
                last_error = err
                continue

            return response.json()

        except MireloError:
            raise
        except httpx.TimeoutException:
            last_error = MireloError("Request timed out", "timeout", 408)
        except httpx.NetworkError as exc:
            last_error = MireloError(str(exc), "network_error", 0)

    assert last_error is not None
    raise last_error

async def put_bytes(
    upload_url: str,
    data: bytes,
    content_type: str,
    timeout_ms: int,
) -> None:
    try:
        async with httpx.AsyncClient(timeout=timeout_ms / 1_000) as client:
            response = await client.put(
                upload_url,
                content=data,
                headers={"Content-Type": content_type},
            )
            if not response.is_success:
                raise MireloError(
                    f"Upload failed: {response.reason_phrase}",
                    "upload_failed",
                    response.status_code,
                )
    except MireloError:
        raise
    except httpx.TimeoutException:
        raise MireloError("Upload timed out", "timeout", 408)
    except httpx.NetworkError as exc:
        raise MireloError(str(exc), "upload_failed", 0)
