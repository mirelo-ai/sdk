from __future__ import annotations

from types import TracebackType
from typing import Literal

import httpx

from . import async_http as _ahttp
from .async_generation import AsyncGenerationRequest
from .generation import (
    TextToSfxParams,
    VideoToSfxParams,
)
from .types import MeResult
from .video import Video

class AsyncMireloClient:
    """
    Async Mirelo API client. All methods are coroutines.

    Use as an async context manager::

        async with AsyncMireloClient("sk-...") as client:
            job = await client.text_to_sfx("thunder").submit_job()
            result = await job.wait()
    """

    def __init__(
        self,
        api_key: str,
        *,
        base_url: str | None = None,
        host: str = "api.mirelo.ai",
        timeout_ms: int = 600_000,
        retries: int = 0,
        backoff_ms: int = 1_000,
        extra_headers: dict[str, str] | None = None,
    ) -> None:
        self._base_url = base_url if base_url is not None else f"https://{host}"
        self._timeout_ms = timeout_ms
        self._retries = retries
        self._backoff_ms = backoff_ms
        self._headers: dict[str, str] = {"Authorization": f"Bearer {api_key}"}
        if extra_headers:
            self._headers.update(extra_headers)
        self._client = httpx.AsyncClient(timeout=timeout_ms / 1_000)

    async def aclose(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> AsyncMireloClient:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        await self.aclose()

    async def me(self) -> MeResult:
        """Return account information including available credits."""
        raw = await _ahttp.request(
            self._client,
            "GET",
            f"{self._base_url}/v2/me",
            headers=self._headers,
            retries=self._retries,
            backoff_ms=self._backoff_ms,
        )
        return MeResult(
            id=raw["id"],
            email=raw["email"],
            credits_available=raw["credits_available"],
            overage_enabled=raw["overage_enabled"],
        )

    def text_to_sfx(
        self,
        prompt: str,
        *,
        duration_ms: int = 10_000,
        num_samples: int = 1,
    ) -> AsyncGenerationRequest:
        return AsyncGenerationRequest(
            base_path="/v2/text-to-sfx/v1.5",
            params=TextToSfxParams(prompt=prompt, duration_ms=duration_ms, num_samples=num_samples),
            client=self._client,
            base_url=self._base_url,
            headers=self._headers,
            timeout_ms=self._timeout_ms,
            retries=self._retries,
            backoff_ms=self._backoff_ms,
        )

    def video_to_sfx(
        self,
        video: Video,
        *,
        duration_ms: int,
        start_offset_ms: int = 0,
        num_samples: int = 1,
        output: Literal["audio", "video"] = "audio",
    ) -> AsyncGenerationRequest:
        return AsyncGenerationRequest(
            base_path="/v2/video-to-sfx/v1.5",
            params=VideoToSfxParams(
                duration_ms=duration_ms,
                start_offset_ms=start_offset_ms,
                num_samples=num_samples,
                output=output,
            ),
            client=self._client,
            base_url=self._base_url,
            headers=self._headers,
            video=video,
            timeout_ms=self._timeout_ms,
            retries=self._retries,
            backoff_ms=self._backoff_ms,
        )
