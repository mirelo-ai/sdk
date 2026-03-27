from __future__ import annotations

import asyncio
from typing import Any

import httpx

from . import async_http as _ahttp
from .generation import (
    TextToSfxParams,
    VideoToSfxParams,
    _parse_job_status,
)
from .types import (
    JobErrored,
    JobStatus,
    JobSucceeded,
    MireloError,
    PreflightResult,
    SyncResult,
)
from .video import Video

class AsyncJob:
    """Async variant of ``Job``. All methods are coroutines."""

    def __init__(
        self,
        job_id: str,
        estimated_ms: int,
        job_url: str,
        base_path: str,
        client: httpx.AsyncClient,
        base_url: str,
        headers: dict[str, str],
        retries: int = 0,
        backoff_ms: int = 1_000,
    ) -> None:
        self.job_id = job_id
        self.estimated_ms = estimated_ms
        self.job_url = job_url
        self._base_path = base_path
        self._client = client
        self._base_url = base_url
        self._headers = headers
        self._retries = retries
        self._backoff_ms = backoff_ms

    async def status(self) -> JobStatus:
        """Single async poll — returns the current job status without blocking."""
        raw = await _ahttp.request(
            self._client,
            "GET",
            f"{self._base_url}{self._base_path}/jobs/{self.job_id}",
            headers=self._headers,
            retries=self._retries,
            backoff_ms=self._backoff_ms,
        )
        return _parse_job_status(raw)

    async def wait(self, poll_interval_ms: int = 500) -> SyncResult:
        """Poll on a fixed interval until the job succeeds or errors. Raises ``MireloError`` on failure."""
        timeout_ms = max(self.estimated_ms * 3, 5 * 60 * 1_000)
        deadline = asyncio.get_event_loop().time() + timeout_ms / 1_000

        while asyncio.get_event_loop().time() < deadline:
            s = await self.status()

            if isinstance(s, JobSucceeded):
                return SyncResult(result_urls=s.result_urls)
            if isinstance(s, JobErrored):
                raise MireloError(s.message, s.code, s.http_status)

            await asyncio.sleep(poll_interval_ms / 1_000)

        raise MireloError(
            f"Job {self.job_id} did not complete within the timeout",
            "timeout",
            408,
        )

class AsyncGenerationRequest:
    """
    Returned by every ``AsyncMireloClient`` generation method.
    Call ``await preflight()``, ``await sync_i_accept_http_timeout_risk()``, or ``await submit_job()``.
    """

    def __init__(
        self,
        base_path: str,
        params: (
            TextToSfxParams
            | VideoToSfxParams
        ),
        client: httpx.AsyncClient,
        base_url: str,
        headers: dict[str, str],
        video: Video | None = None,
        timeout_ms: int = 600_000,
        retries: int = 0,
        backoff_ms: int = 1_000,
    ) -> None:
        self._base_path = base_path
        self._params = params
        self._client = client
        self._base_url = base_url
        self._headers = headers
        self._video = video
        self._timeout_ms = timeout_ms
        self._retries = retries
        self._backoff_ms = backoff_ms

    async def _build_body(self) -> dict[str, Any]:
        p = self._params
        body: dict[str, Any] = {}

        if isinstance(p, TextToSfxParams):
            body["prompt"] = p.prompt
            body["duration_ms"] = p.duration_ms
            body["num_samples"] = p.num_samples
        elif isinstance(p, VideoToSfxParams):
            body["duration_ms"] = p.duration_ms
            if p.start_offset_ms:
                body["start_offset_ms"] = p.start_offset_ms
            body["num_samples"] = p.num_samples
            body["output"] = p.output

        if self._video is not None:
            body["video"] = await self._video.resolve_async(
                self._client,
                self._base_url,
                self._headers,
                self._timeout_ms,
                self._retries,
                self._backoff_ms,
            )

        return body

    async def preflight(self) -> PreflightResult:
        """Check credit cost and estimated time without generating anything."""
        p = self._params
        query_parts: list[str] = [f"duration_ms={p.duration_ms}"]
        if hasattr(p, "num_samples"):
            query_parts.append(f"num_samples={p.num_samples}")
        query = "&".join(query_parts)
        url = f"{self._base_url}{self._base_path}/preflight?{query}"

        raw = await _ahttp.request(
            self._client,
            "GET",
            url,
            headers=self._headers,
            retries=self._retries,
            backoff_ms=self._backoff_ms,
        )
        return PreflightResult(credits=raw["credits"], estimated_ms=raw["estimated_ms"])

    async def sync_i_accept_http_timeout_risk(self) -> SyncResult:
        """
        Call the synchronous endpoint.

        WARNING: this is a long-blocking HTTP call. Any proxy or load balancer
        with a timeout shorter than the generation time will cut this off.
        Use ``submit_job()`` for production workloads.
        """
        body = await self._build_body()
        raw = await _ahttp.request(
            self._client,
            "POST",
            f"{self._base_url}{self._base_path}/sync",
            headers=self._headers,
            json=body,
            retries=self._retries,
            backoff_ms=self._backoff_ms,
        )
        return SyncResult(result_urls=raw["result_urls"])

    async def submit_job(self) -> AsyncJob:
        """Submit a background job and return an ``AsyncJob`` object for polling."""
        body = await self._build_body()
        raw = await _ahttp.request(
            self._client,
            "POST",
            f"{self._base_url}{self._base_path}/jobs",
            headers=self._headers,
            json=body,
            retries=self._retries,
            backoff_ms=self._backoff_ms,
        )
        return AsyncJob(
            job_id=raw["job_id"],
            estimated_ms=raw["estimated_ms"],
            job_url=raw["job_url"],
            base_path=self._base_path,
            client=self._client,
            base_url=self._base_url,
            headers=self._headers,
            retries=self._retries,
            backoff_ms=self._backoff_ms,
        )
