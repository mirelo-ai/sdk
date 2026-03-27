from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Literal

import httpx

from . import http as _http
from .types import (
    JobErrored,
    JobProcessing,
    JobStatus,
    JobSucceeded,
    MireloError,
    PreflightResult,
    SyncResult,
)
from .video import Video

def _parse_job_status(raw: dict[str, Any]) -> JobStatus:
    status = raw.get("status")
    if status == "processing":
        return JobProcessing(
            status="processing",
            progress_percent=raw.get("progress_percent", 0),
            estimated_completion_at=raw.get("estimated_completion_at", ""),
        )
    if status == "succeeded":
        result = raw.get("result") or {}
        return JobSucceeded(
            status="succeeded",
            result_urls=result.get("result_urls", []),
        )
    if status == "errored":
        error = raw.get("error") or {}
        return JobErrored(
            status="errored",
            code=error.get("code", "generation_failed"),
            http_status=error.get("http_status", 502),
            message=error.get("message", "Generation failed"),
        )
    raise MireloError(f"Unexpected job status: {status}", "server_error", 500)

class Job:
    """A background generation job. Poll with ``status()`` or block with ``wait()``."""

    def __init__(
        self,
        job_id: str,
        estimated_ms: int,
        job_url: str,
        base_path: str,
        client: httpx.Client,
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

    def status(self) -> JobStatus:
        """Single poll — returns the current job status without blocking."""
        raw = _http.request(
            self._client,
            "GET",
            f"{self._base_url}{self._base_path}/jobs/{self.job_id}",
            headers=self._headers,
            retries=self._retries,
            backoff_ms=self._backoff_ms,
        )
        return _parse_job_status(raw)

    def wait(self, poll_interval_ms: int = 500) -> SyncResult:
        """Poll on a fixed interval until the job succeeds or errors. Raises ``MireloError`` on failure."""
        timeout_ms = max(self.estimated_ms * 3, 5 * 60 * 1_000)
        deadline = time.monotonic() + timeout_ms / 1_000

        while time.monotonic() < deadline:
            s = self.status()

            if isinstance(s, JobSucceeded):
                return SyncResult(result_urls=s.result_urls)
            if isinstance(s, JobErrored):
                raise MireloError(s.message, s.code, s.http_status)

            time.sleep(poll_interval_ms / 1_000)

        raise MireloError(
            f"Job {self.job_id} did not complete within the timeout",
            "timeout",
            408,
        )

@dataclass
class TextToSfxParams:
    prompt: str
    duration_ms: int = 10_000
    num_samples: int = 1

@dataclass
class VideoToSfxParams:
    duration_ms: int
    start_offset_ms: int = 0
    num_samples: int = 1
    output: Literal["audio", "video"] = "audio"

class GenerationRequest:
    """
    Returned by every ``MireloClient`` generation method.
    Call ``preflight()``, ``sync_i_accept_http_timeout_risk()``, or ``submit_job()``.
    """

    def __init__(
        self,
        base_path: str,
        params: (
            TextToSfxParams
            | VideoToSfxParams
        ),
        client: httpx.Client,
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

    def _build_body(self) -> dict[str, Any]:
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
            body["video"] = self._video.resolve_sync(
                self._client,
                self._base_url,
                self._headers,
                self._timeout_ms,
                self._retries,
                self._backoff_ms,
            )

        return body

    def preflight(self) -> PreflightResult:
        """Check credit cost and estimated time without generating anything."""
        p = self._params
        query_parts: list[str] = [f"duration_ms={p.duration_ms}"]
        if hasattr(p, "num_samples"):
            query_parts.append(f"num_samples={p.num_samples}")
        query = "&".join(query_parts)
        url = f"{self._base_url}{self._base_path}/preflight?{query}"

        raw = _http.request(
            self._client,
            "GET",
            url,
            headers=self._headers,
            retries=self._retries,
            backoff_ms=self._backoff_ms,
        )
        return PreflightResult(credits=raw["credits"], estimated_ms=raw["estimated_ms"])

    def sync_i_accept_http_timeout_risk(self) -> SyncResult:
        """
        Call the synchronous endpoint.

        WARNING: this is a long-blocking HTTP call. Any proxy or load balancer
        with a timeout shorter than the generation time will cut this off.
        Use ``submit_job()`` for production workloads.
        """
        body = self._build_body()
        raw = _http.request(
            self._client,
            "POST",
            f"{self._base_url}{self._base_path}/sync",
            headers=self._headers,
            json=body,
            retries=self._retries,
            backoff_ms=self._backoff_ms,
        )
        return SyncResult(result_urls=raw["result_urls"])

    def submit_job(self) -> Job:
        """Submit a background job and return a ``Job`` object for polling."""
        body = self._build_body()
        raw = _http.request(
            self._client,
            "POST",
            f"{self._base_url}{self._base_path}/jobs",
            headers=self._headers,
            json=body,
            retries=self._retries,
            backoff_ms=self._backoff_ms,
        )
        return Job(
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
